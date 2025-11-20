"""
Orbit Daily Update DAG
Incremental updates of snapshots and vector DB

This DAG orchestrates:
1. Process daily scraped data
2. Update structured data with new snapshots
3. Reassemble payloads
4. Update vector DB with new chunks

Schedule: Daily at 3 AM UTC (0 3 * * *)
"""

from airflow import DAG
from airflow.operators.python import PythonOperator
from datetime import datetime, timedelta
import sys
import logging
from pathlib import Path
from google.cloud import storage
import json

# Add project root to path for imports
project_root = Path('/home/airflow/gcs/dags')
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

logger = logging.getLogger(__name__)

# Configuration
GCP_PROJECT_ID = 'orbit-ai50-intelligence'
GCS_RAW_BUCKET = 'orbit-raw-data-g1-2025'
GCS_PROCESSED_BUCKET = 'orbit-processed-data-g1-2025'

# Airflow paths
AIRFLOW_DATA_DIR = Path('/home/airflow/data')
AIRFLOW_DAGS_DIR = Path('/home/airflow/gcs/dags')

default_args = {
    'owner': 'orbit-team',
    'depends_on_past': False,
    'email_on_failure': False,
    'retries': 2,
    'retry_delay': timedelta(minutes=5),
}


def download_daily_data_from_gcs(**context):
    """
    Task 1: Download today's daily scraped data from GCS.
    """
    logger.info("="*70)
    logger.info("TASK 1: Downloading Daily Data from GCS")
    logger.info("="*70)
    
    try:
        client = storage.Client(project=GCP_PROJECT_ID)
        raw_bucket = client.bucket(GCS_RAW_BUCKET)
        
        # Get today's date for session name
        today = datetime.now().strftime('%Y-%m-%d')
        daily_prefix = f"data/raw/"
        
        logger.info(f"Looking for daily data with prefix: {daily_prefix}")
        
        # List all blobs with daily session
        blobs = list(raw_bucket.list_blobs(prefix=daily_prefix))
        
        # Filter for today's data (contains today's date in path)
        daily_blobs = [b for b in blobs if today in b.name or '_daily' in b.name]
        
        if not daily_blobs:
            logger.warning(f"⚠️  No daily data found for {today}")
            logger.info("Checking for any recent daily data...")
            # Get all blobs and find most recent daily session
            all_blobs = list(raw_bucket.list_blobs(prefix=daily_prefix))
            daily_blobs = [b for b in all_blobs if '_daily' in b.name]
        
        if not daily_blobs:
            logger.warning("⚠️  No daily data found. Skipping update.")
            context['task_instance'].xcom_push(key='has_daily_data', value=False)
            return 0
        
        logger.info(f"Found {len(daily_blobs)} daily data files")
        
        # Download to local
        downloaded = 0
        for blob in daily_blobs:
            # Create local path structure
            relative_path = blob.name.replace('data/raw/', '')
            local_file = AIRFLOW_DATA_DIR / "raw" / relative_path
            local_file.parent.mkdir(parents=True, exist_ok=True)
            
            blob.download_to_filename(str(local_file))
            downloaded += 1
        
        logger.info(f"✅ Downloaded {downloaded} files")
        
        context['task_instance'].xcom_push(key='has_daily_data', value=True)
        context['task_instance'].xcom_push(key='files_downloaded', value=downloaded)
        
        return downloaded
    
    except Exception as e:
        logger.error(f"Error downloading daily data: {e}")
        import traceback
        logger.error(traceback.format_exc())
        raise


def update_structured_data(**context):
    """
    Task 2: Update structured data with new snapshots from daily data.
    """
    logger.info("="*70)
    logger.info("TASK 2: Updating Structured Data")
    logger.info("="*70)
    
    has_daily_data = context['task_instance'].xcom_pull(
        key='has_daily_data',
        task_ids='download_daily_data'
    )
    
    if not has_daily_data:
        logger.info("⚠️  No daily data available. Skipping structured update.")
        context['task_instance'].xcom_push(key='companies_updated', value=0)
        return 0
    
    try:
        # Import structured extractor
        sys.path.insert(0, str(AIRFLOW_DAGS_DIR))
        from src.structured.structured_extract import StructuredExtractor
        
        # Initialize extractor
        extractor = StructuredExtractor()
        
        # Get companies with daily data
        raw_dir = AIRFLOW_DATA_DIR / "raw"
        companies_with_daily = []
        
        for company_dir in raw_dir.iterdir():
            if company_dir.is_dir():
                # Check for daily session
                sessions = [s for s in company_dir.iterdir() if s.is_dir() and '_daily' in s.name]
                if sessions:
                    companies_with_daily.append(company_dir.name.replace('_', ' '))
        
        if not companies_with_daily:
            logger.info("⚠️  No companies with daily data found")
            context['task_instance'].xcom_push(key='companies_updated', value=0)
            return 0
        
        logger.info(f"Found {len(companies_with_daily)} companies with daily updates")
        
        # Update each company
        updated = 0
        for i, company_name in enumerate(companies_with_daily, 1):
            logger.info(f"[{i}/{len(companies_with_daily)}] Updating: {company_name}")
            
            try:
                # Extract with new data (will merge with existing)
                payload = extractor.extract_all(company_name)
                updated += 1
                logger.info(f"  ✅ Updated: {company_name}")
            except Exception as e:
                logger.warning(f"  ⚠️  Failed: {company_name} - {e}")
        
        logger.info(f"✅ Updated {updated} companies")
        
        context['task_instance'].xcom_push(key='companies_updated', value=updated)
        
        return updated
    
    except Exception as e:
        logger.error(f"Error updating structured data: {e}")
        import traceback
        logger.error(traceback.format_exc())
        raise


def reassemble_payloads(**context):
    """
    Task 3: Reassemble payloads with updated structured data.
    """
    logger.info("="*70)
    logger.info("TASK 3: Reassembling Payloads")
    logger.info("="*70)
    
    companies_updated = context['task_instance'].xcom_pull(
        key='companies_updated',
        task_ids='update_structured_data'
    ) or 0
    
    if companies_updated == 0:
        logger.info("⚠️  No companies updated. Skipping payload reassembly.")
        context['task_instance'].xcom_push(key='payloads_reassembled', value=0)
        return 0
    
    try:
        # Import payload assembly function
        sys.path.insert(0, str(AIRFLOW_DAGS_DIR))
        from src.structured.structured_payload_lab6 import assemble_payloads as assemble_payloads_func
        
        # Set paths for payload assembly
        import os
        original_cwd = os.getcwd()
        try:
            os.chdir(str(AIRFLOW_DATA_DIR.parent))
            assemble_payloads_func()
            
            # Count payloads
            payloads_dir = AIRFLOW_DATA_DIR / "payloads"
            if payloads_dir.exists():
                payload_files = list(payloads_dir.glob('*.json'))
                payload_count = len(payload_files)
                logger.info(f"✅ Reassembled {payload_count} payload files")
            else:
                payload_count = 0
            
            context['task_instance'].xcom_push(key='payloads_reassembled', value=payload_count)
            
            return payload_count
            
        finally:
            os.chdir(original_cwd)
    
    except Exception as e:
        logger.error(f"Error reassembling payloads: {e}")
        import traceback
        logger.error(traceback.format_exc())
        raise


def update_vector_db(**context):
    """
    Task 4: Update vector DB with new chunks from daily data.
    """
    logger.info("="*70)
    logger.info("TASK 4: Updating Vector DB")
    logger.info("="*70)
    
    has_daily_data = context['task_instance'].xcom_pull(
        key='has_daily_data',
        task_ids='download_daily_data'
    )
    
    if not has_daily_data:
        logger.info("⚠️  No daily data available. Skipping vector DB update.")
        context['task_instance'].xcom_push(key='new_chunks_added', value=0)
        return 0
    
    try:
        # Import vector index builder
        sys.path.insert(0, str(AIRFLOW_DAGS_DIR))
        from src.vectordb.build_index import build_vector_index
        from src.vectordb.embedder import VectorStore
        
        # Build/update index (incremental - don't clear existing)
        logger.info("Updating vector index with daily data...")
        build_vector_index(
            use_docker=False,
            clear_existing=False,  # Incremental update
            use_gcs=True,
            bucket_name=GCS_RAW_BUCKET
        )
        
        logger.info("✅ Vector index updated")
        
        # Get stats
        vector_store = VectorStore(use_docker=False, data_dir=AIRFLOW_DATA_DIR / "qdrant_storage")
        stats = vector_store.get_stats()
        
        logger.info(f"✅ Vector store stats: {stats['total_chunks']} total chunks")
        
        # Estimate new chunks (rough estimate)
        new_chunks = stats.get('total_chunks', 0)  # In real scenario, compare with previous
        
        context['task_instance'].xcom_push(key='new_chunks_added', value=new_chunks)
        context['task_instance'].xcom_push(key='total_chunks', value=stats['total_chunks'])
        
        return stats['total_chunks']
    
    except Exception as e:
        logger.error(f"Error updating vector DB: {e}")
        import traceback
        logger.error(traceback.format_exc())
        raise


def upload_updates_to_gcs(**context):
    """
    Task 5: Upload updated structured data, payloads, and vector DB to GCS.
    """
    logger.info("="*70)
    logger.info("TASK 5: Uploading Updates to GCS")
    logger.info("="*70)
    
    try:
        client = storage.Client(project=GCP_PROJECT_ID)
        processed_bucket = client.bucket(GCS_PROCESSED_BUCKET)
        
        upload_count = 0
        
        # 1. Upload updated structured files
        structured_dir = AIRFLOW_DATA_DIR / "structured"
        if structured_dir.exists():
            logger.info("Uploading updated structured files...")
            for file_path in structured_dir.glob('*.json'):
                blob_name = f"data/structured/{file_path.name}"
                blob = processed_bucket.blob(blob_name)
                blob.upload_from_filename(str(file_path))
                upload_count += 1
        
        # 2. Upload updated payloads
        payloads_dir = AIRFLOW_DATA_DIR / "payloads"
        if payloads_dir.exists():
            logger.info("Uploading updated payloads...")
            for file_path in payloads_dir.glob('*.json'):
                blob_name = f"data/payloads/{file_path.name}"
                blob = processed_bucket.blob(blob_name)
                blob.upload_from_filename(str(file_path))
                upload_count += 1
        
        # 3. Upload updated vector DB
        qdrant_dir = AIRFLOW_DATA_DIR / "qdrant_storage"
        if qdrant_dir.exists():
            logger.info("Uploading updated vector DB...")
            import tarfile
            import tempfile
            
            with tempfile.NamedTemporaryFile(suffix='.tar.gz', delete=False) as tmp_file:
                tar_path = Path(tmp_file.name)
            
            with tarfile.open(tar_path, 'w:gz') as tar:
                tar.add(qdrant_dir, arcname='qdrant_storage')
            
            blob_name = "qdrant_index/qdrant_storage.tar.gz"
            blob = processed_bucket.blob(blob_name)
            blob.upload_from_filename(str(tar_path))
            upload_count += 1
            tar_path.unlink()
            logger.info(f"  ✅ Uploaded vector DB: {blob_name}")
        
        logger.info(f"✅ Total files uploaded: {upload_count}")
        
        context['task_instance'].xcom_push(key='files_uploaded', value=upload_count)
        
        return upload_count
    
    except Exception as e:
        logger.error(f"Error uploading to GCS: {e}")
        import traceback
        logger.error(traceback.format_exc())
        raise


def generate_daily_report(**context):
    """
    Task 6: Generate daily update report.
    """
    logger.info("="*70)
    logger.info("TASK 6: Generating Daily Report")
    logger.info("="*70)
    
    try:
        has_daily_data = context['task_instance'].xcom_pull(
            key='has_daily_data',
            task_ids='download_daily_data'
        ) or False
        
        companies_updated = context['task_instance'].xcom_pull(
            key='companies_updated',
            task_ids='update_structured_data'
        ) or 0
        
        payloads_reassembled = context['task_instance'].xcom_pull(
            key='payloads_reassembled',
            task_ids='reassemble_payloads'
        ) or 0
        
        total_chunks = context['task_instance'].xcom_pull(
            key='total_chunks',
            task_ids='update_vector_db'
        ) or 0
        
        files_uploaded = context['task_instance'].xcom_pull(
            key='files_uploaded',
            task_ids='upload_to_gcs'
        ) or 0
        
        report = {
            'dag_id': 'orbit_daily_update_dag',
            'execution_date': context['execution_date'].isoformat(),
            'status': 'SUCCESS',
            'has_daily_data': has_daily_data,
            'companies_updated': companies_updated,
            'payloads_reassembled': payloads_reassembled,
            'total_vector_chunks': total_chunks,
            'files_uploaded': files_uploaded,
            'completed_at': datetime.now().isoformat(),
        }
        
        # Save report to GCS
        client = storage.Client(project=GCP_PROJECT_ID)
        bucket = client.bucket(GCS_PROCESSED_BUCKET)
        
        report_name = f"airflow_reports/daily_update_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        blob = bucket.blob(report_name)
        blob.upload_from_string(json.dumps(report, indent=2))
        
        logger.info("="*70)
        logger.info("📊 DAILY UPDATE REPORT")
        logger.info("="*70)
        logger.info(f"✅ Report saved: gs://{GCS_PROCESSED_BUCKET}/{report_name}")
        logger.info(f"📊 Companies updated: {companies_updated}")
        logger.info(f"📋 Payloads reassembled: {payloads_reassembled}")
        logger.info(f"🔍 Total vector chunks: {total_chunks}")
        logger.info(f"📁 Files uploaded: {files_uploaded}")
        logger.info("="*70)
        
        return report
    
    except Exception as e:
        logger.error(f"Error generating report: {e}")
        raise


# Define DAG
with DAG(
    dag_id='orbit_daily_update_dag',
    default_args=default_args,
    description='Orbit Daily Update: Process daily data → Update structured → Reassemble payloads → Update vector DB',
    schedule_interval='0 3 * * *',  # Daily at 3 AM UTC
    start_date=datetime(2025, 1, 1),
    catchup=False,
    tags=['orbit', 'daily-update', 'incremental', 'vector-db'],
) as dag:
    
    # Task 1: Download daily data
    task1_download = PythonOperator(
        task_id='download_daily_data',
        python_callable=download_daily_data_from_gcs,
        execution_timeout=timedelta(minutes=30),
    )
    
    # Task 2: Update structured data
    task2_update = PythonOperator(
        task_id='update_structured_data',
        python_callable=update_structured_data,
        execution_timeout=timedelta(hours=1),
    )
    
    # Task 3: Reassemble payloads
    task3_reassemble = PythonOperator(
        task_id='reassemble_payloads',
        python_callable=reassemble_payloads,
        execution_timeout=timedelta(minutes=30),
    )
    
    # Task 4: Update vector DB
    task4_vector = PythonOperator(
        task_id='update_vector_db',
        python_callable=update_vector_db,
        execution_timeout=timedelta(hours=2),
    )
    
    # Task 5: Upload to GCS
    task5_upload = PythonOperator(
        task_id='upload_to_gcs',
        python_callable=upload_updates_to_gcs,
        execution_timeout=timedelta(minutes=30),
    )
    
    # Task 6: Generate report
    task6_report = PythonOperator(
        task_id='generate_report',
        python_callable=generate_daily_report,
    )
    
    # Execution order
    task1_download >> task2_update >> task3_reassemble >> task4_vector >> task5_upload >> task6_report

