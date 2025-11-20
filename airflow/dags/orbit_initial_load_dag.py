"""
Orbit Initial Load DAG
Initial data load and payload assembly

This DAG orchestrates:
1. Download latest initial data from GCS bucket (not daily)
2. Structured extraction from raw scraped data
3. Payload assembly from structured data
4. Initial vector DB build
5. Upload results to GCS

Schedule: @once (manual trigger only)
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
# For Docker: /opt/airflow, for GCP: /home/airflow/gcs/dags
project_root = Path('/opt/airflow')  # Docker mount location
if not project_root.exists():
    project_root = Path('/home/airflow/gcs/dags')  # GCP fallback
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

logger = logging.getLogger(__name__)

# Configuration
GCP_PROJECT_ID = 'orbit-ai50-intelligence'
GCS_RAW_BUCKET = 'orbit-raw-data-g1-2025'
GCS_PROCESSED_BUCKET = 'orbit-processed-data-g1-2025'

# Airflow paths
# For Docker: /opt/airflow, for GCP: /home/airflow
AIRFLOW_DATA_DIR = Path('/opt/airflow/data')  # Docker mount
if not AIRFLOW_DATA_DIR.exists():
    AIRFLOW_DATA_DIR = Path('/home/airflow/data')  # GCP fallback

AIRFLOW_DAGS_DIR = Path('/opt/airflow')  # Docker mount (src/ is at /opt/airflow/src/)
if not AIRFLOW_DAGS_DIR.exists():
    AIRFLOW_DAGS_DIR = Path('/home/airflow/gcs/dags')  # GCP fallback

default_args = {
    'owner': 'orbit-team',
    'depends_on_past': False,
    'email_on_failure': False,
    'retries': 1,
    'retry_delay': timedelta(minutes=5),
}


def download_initial_data_from_gcs(**context):
    """
    Task 1: Download initial (latest) scraped data from GCS bucket.
    Downloads the latest initial data (not daily) for all companies.
    """
    logger.info("="*70)
    logger.info("TASK 1: Downloading Initial Data from GCS")
    logger.info("="*70)
    
    try:
        import os
        
        # Always try to download from GCS (user wants GCS)
        # Try Application Default Credentials first (from gcloud auth)
        # Then try service account JSON files
        
        logger.info("Checking for GCP credentials...")
        
        # Try to find credentials - check multiple sources
        credentials_path = None
        
        # Priority 1: Try ADC first (preferred method)
        adc_paths = [
            '/root/.config/gcloud/application_default_credentials.json',  # Mounted ADC
            '/opt/airflow/adc-credentials.json',  # Copied ADC file
        ]
        credentials_path = None
        for adc_path in adc_paths:
            if os.path.exists(adc_path):
                credentials_path = adc_path
                os.environ['GOOGLE_APPLICATION_CREDENTIALS'] = adc_path
                logger.info(f"✅ Found ADC at: {adc_path}")
                break
        
        # Priority 2: Check environment variable (if not ADC)
        if not credentials_path and os.getenv('GOOGLE_APPLICATION_CREDENTIALS'):
            env_path = os.getenv('GOOGLE_APPLICATION_CREDENTIALS')
            if os.path.exists(env_path):
                credentials_path = env_path
                logger.info(f"✅ Using credentials from GOOGLE_APPLICATION_CREDENTIALS: {env_path}")
        
        # Priority 3: Check common service account JSON locations (fallback)
        if not credentials_path:
            alt_paths = [
                '/opt/airflow/gcp-credentials.json',
                '/opt/airflow/gcp-service-account.json',
                '/opt/airflow/gcp-service-account.json.json',
            ]
            for path in alt_paths:
                if os.path.exists(path):
                    credentials_path = path
                    os.environ['GOOGLE_APPLICATION_CREDENTIALS'] = path
                    logger.info(f"✅ Found service account JSON at: {path}")
                    break
        
        # Try to create client
        try:
            if credentials_path:
                # Check if it's a service account JSON or ADC
                # Service account JSON files typically have 'gcp-' in path or are in /opt/airflow/
                is_service_account = (
                    credentials_path.endswith('.json') and 
                    ('/gcp-' in credentials_path or '/opt/airflow/gcp' in credentials_path)
                )
                
                if is_service_account:
                    # Service account JSON file
                    from google.oauth2 import service_account
                    credentials = service_account.Credentials.from_service_account_file(credentials_path)
                    client = storage.Client(project=GCP_PROJECT_ID, credentials=credentials)
                    logger.info(f"✅ Using service account credentials from: {credentials_path}")
                else:
                    # ADC file - set environment variable and use default
                    os.environ['GOOGLE_APPLICATION_CREDENTIALS'] = credentials_path
                    client = storage.Client(project=GCP_PROJECT_ID)
                    logger.info(f"✅ Using ADC credentials from: {credentials_path}")
            else:
                # Try default credentials (for GCP environments)
                client = storage.Client(project=GCP_PROJECT_ID)
                logger.info("✅ Using default credentials")
        except Exception as cred_error:
            logger.error(f"❌ Failed to create GCS client: {cred_error}")
            logger.error("❌ No valid credentials found!")
            logger.error("Options:")
            logger.error("  1. Run: gcloud auth application-default login (on host)")
            logger.error("  2. Mount ADC credentials in Docker (see docker-compose.airflow.yml)")
            logger.error("  3. Use service account JSON file: gcp-credentials.json")
            raise
        
        raw_bucket = client.bucket(GCS_RAW_BUCKET)
        
        # Look for initial data (not daily)
        initial_prefix = f"data/raw/"
        
        logger.info(f"Looking for initial data with prefix: {initial_prefix}")
        
        # List all blobs
        all_blobs = list(raw_bucket.list_blobs(prefix=initial_prefix))
        
        # Filter for initial data (exclude daily data)
        # Initial data: does NOT contain '_daily' in path
        initial_blobs = [b for b in all_blobs if '_daily' not in b.name]
        
        if not initial_blobs:
            logger.warning("⚠️  No initial data found in GCS bucket")
            logger.info(f"Note: Initial data should be in gs://{GCS_RAW_BUCKET}/data/raw/")
            logger.info("Make sure initial data (not daily) exists in the bucket")
            raise Exception(f"No initial data found in GCS bucket: gs://{GCS_RAW_BUCKET}/data/raw/")
        
        logger.info(f"Found {len(initial_blobs)} initial data files")
        
        # Download to local
        downloaded = 0
        for blob in initial_blobs:
            # Create local path structure
            relative_path = blob.name.replace('data/raw/', '')
            local_file = AIRFLOW_DATA_DIR / "raw" / relative_path
            local_file.parent.mkdir(parents=True, exist_ok=True)
            
            blob.download_to_filename(str(local_file))
            downloaded += 1
        
        logger.info(f"✅ Downloaded {downloaded} initial data files")
        
        context['task_instance'].xcom_push(key='files_downloaded', value=downloaded)
        
        return downloaded
    
    except Exception as e:
        logger.error(f"Error downloading initial data from GCS: {e}")
        logger.error("GCS download is required. Please check:")
        logger.error("1. GCP credentials file exists and is mounted in Docker")
        logger.error("2. GOOGLE_APPLICATION_CREDENTIALS environment variable is set")
        logger.error("3. Initial data exists in gs://{GCS_RAW_BUCKET}/data/raw/")
        import traceback
        logger.error(traceback.format_exc())
        raise


def run_structured_extraction(**context):
    """
    Task 2: Run structured extraction for all companies.
    Extracts structured data from raw scraped files.
    """
    logger.info("="*70)
    logger.info("TASK 2: Running Structured Extraction")
    logger.info("="*70)
    
    try:
        # Ensure project root is in path (src/ is at /opt/airflow/src/ in Docker)
        project_root = Path('/opt/airflow')  # Docker mount location
        if not project_root.exists():
            project_root = Path('/home/airflow/gcs/dags')  # GCP fallback
        if str(project_root) not in sys.path:
            sys.path.insert(0, str(project_root))
            logger.info(f"Added project root to path: {project_root}")
        
        from src.structured.structured_extract import StructuredExtractor
        
        # Initialize extractor
        extractor = StructuredExtractor()
        
        # Get list of companies from raw data
        raw_dir = AIRFLOW_DATA_DIR / "raw"
        if not raw_dir.exists():
            raise Exception(f"Raw data directory not found: {raw_dir}")
        
        companies = sorted([d.name.replace('_', ' ') for d in raw_dir.iterdir() if d.is_dir()])
        
        if not companies:
            raise Exception("No companies found in raw data directory")
        
        logger.info(f"Found {len(companies)} companies to process")
        
        # Process each company
        successful = 0
        failed = 0
        
        for i, company_name in enumerate(companies, 1):
            logger.info(f"[{i}/{len(companies)}] Processing: {company_name}")
            
            try:
                payload = extractor.extract_all(company_name)
                successful += 1
                logger.info(f"  ✅ Extracted: {company_name}")
            except Exception as e:
                failed += 1
                logger.warning(f"  ⚠️  Failed: {company_name} - {e}")
        
        logger.info(f"✅ Structured extraction complete: {successful} successful, {failed} failed")
        
        context['task_instance'].xcom_push(key='companies_processed', value=successful)
        context['task_instance'].xcom_push(key='companies_failed', value=failed)
        
        return successful
    
    except Exception as e:
        logger.error(f"Error in structured extraction: {e}")
        import traceback
        logger.error(traceback.format_exc())
        raise


def assemble_payloads(**context):
    """
    Task 3: Assemble payloads from structured data.
    Validates and copies structured files to payloads folder.
    """
    logger.info("="*70)
    logger.info("TASK 3: Assembling Payloads")
    logger.info("="*70)
    
    try:
        # Ensure project root is in path
        project_root = Path('/opt/airflow')  # Docker mount location
        if not project_root.exists():
            project_root = Path('/home/airflow/gcs/dags')  # GCP fallback
        if str(project_root) not in sys.path:
            sys.path.insert(0, str(project_root))
            logger.info(f"Added project root to path: {project_root}")
        
        from src.structured.structured_payload_lab6 import assemble_payloads as assemble_payloads_func
        
        # Set paths for payload assembly
        import os
        original_cwd = os.getcwd()
        try:
            # Change to project root for relative paths
            os.chdir(str(AIRFLOW_DATA_DIR.parent))
            
            # Run assembly
            assemble_payloads_func()
            
            # Count payloads created
            payloads_dir = AIRFLOW_DATA_DIR / "payloads"
            if payloads_dir.exists():
                payload_files = list(payloads_dir.glob('*.json'))
                payload_count = len(payload_files)
                logger.info(f"✅ Created {payload_count} payload files")
            else:
                payload_count = 0
                logger.warning("⚠️  Payloads directory not created")
            
            context['task_instance'].xcom_push(key='payloads_created', value=payload_count)
            
            return payload_count
            
        finally:
            os.chdir(original_cwd)
    
    except Exception as e:
        logger.error(f"Error in payload assembly: {e}")
        import traceback
        logger.error(traceback.format_exc())
        raise


def build_vector_index(**context):
    """
    Task 4: Build initial vector database index.
    Creates Qdrant vector store from scraped data.
    """
    logger.info("="*70)
    logger.info("TASK 4: Building Vector Index")
    logger.info("="*70)
    
    try:
        # Ensure project root is in path
        project_root = Path('/opt/airflow')  # Docker mount location
        if not project_root.exists():
            project_root = Path('/home/airflow/gcs/dags')  # GCP fallback
        if str(project_root) not in sys.path:
            sys.path.insert(0, str(project_root))
            logger.info(f"Added project root to path: {project_root}")
        
        from src.vectordb.build_index import build_vector_index
        
        # Build index from GCS
        logger.info("Building vector index from GCS...")
        build_vector_index(
            use_docker=False,
            clear_existing=True,
            use_gcs=True,
            bucket_name=GCS_RAW_BUCKET
        )
        
        logger.info("✅ Vector index built successfully")
        
        # Get stats
        from src.vectordb.embedder import VectorStore
        vector_store = VectorStore(use_docker=False, data_dir=AIRFLOW_DATA_DIR / "qdrant_storage")
        stats = vector_store.get_stats()
        companies = vector_store.get_companies()
        
        logger.info(f"✅ Vector store stats: {stats['total_chunks']} chunks, {len(companies)} companies")
        
        context['task_instance'].xcom_push(key='vector_chunks', value=stats['total_chunks'])
        context['task_instance'].xcom_push(key='vector_companies', value=len(companies))
        
        return stats['total_chunks']
    
    except Exception as e:
        logger.error(f"Error building vector index: {e}")
        import traceback
        logger.error(traceback.format_exc())
        raise


def upload_results_to_gcs(**context):
    """
    Task 5: Upload structured data, payloads, and vector DB to GCS.
    """
    logger.info("="*70)
    logger.info("TASK 5: Uploading Results to GCS")
    logger.info("="*70)
    
    try:
        client = storage.Client(project=GCP_PROJECT_ID)
        processed_bucket = client.bucket(GCS_PROCESSED_BUCKET)
        
        upload_count = 0
        
        # 1. Upload structured files
        structured_dir = AIRFLOW_DATA_DIR / "structured"
        if structured_dir.exists():
            logger.info("Uploading structured files...")
            for file_path in structured_dir.glob('*.json'):
                blob_name = f"data/structured/{file_path.name}"
                blob = processed_bucket.blob(blob_name)
                blob.upload_from_filename(str(file_path))
                upload_count += 1
            logger.info(f"  ✅ Uploaded {len(list(structured_dir.glob('*.json')))} structured files")
        
        # 2. Upload payloads
        payloads_dir = AIRFLOW_DATA_DIR / "payloads"
        if payloads_dir.exists():
            logger.info("Uploading payloads...")
            for file_path in payloads_dir.glob('*.json'):
                blob_name = f"data/payloads/{file_path.name}"
                blob = processed_bucket.blob(blob_name)
                blob.upload_from_filename(str(file_path))
                upload_count += 1
            logger.info(f"  ✅ Uploaded {len(list(payloads_dir.glob('*.json')))} payload files")
        
        # 3. Upload vector DB (tar and upload)
        qdrant_dir = AIRFLOW_DATA_DIR / "qdrant_storage"
        if qdrant_dir.exists():
            logger.info("Preparing vector DB for upload...")
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
            tar_path.unlink()  # Clean up
            logger.info(f"  ✅ Uploaded vector DB: {blob_name}")
        
        logger.info(f"✅ Total files uploaded: {upload_count}")
        
        context['task_instance'].xcom_push(key='files_uploaded', value=upload_count)
        
        return upload_count
    
    except Exception as e:
        logger.error(f"Error uploading to GCS: {e}")
        import traceback
        logger.error(traceback.format_exc())
        raise


def generate_report(**context):
    """
    Task 6: Generate final report.
    """
    logger.info("="*70)
    logger.info("TASK 6: Generating Report")
    logger.info("="*70)
    
    try:
        companies_processed = context['task_instance'].xcom_pull(
            key='companies_processed',
            task_ids='run_structured_extraction'
        ) or 0
        
        payloads_created = context['task_instance'].xcom_pull(
            key='payloads_created',
            task_ids='assemble_payloads'
        ) or 0
        
        vector_chunks = context['task_instance'].xcom_pull(
            key='vector_chunks',
            task_ids='build_vector_index'
        ) or 0
        
        files_uploaded = context['task_instance'].xcom_pull(
            key='files_uploaded',
            task_ids='upload_to_gcs'
        ) or 0
        
        report = {
            'dag_id': 'orbit_initial_load_dag',
            'execution_date': context['execution_date'].isoformat(),
            'status': 'SUCCESS',
            'companies_processed': companies_processed,
            'payloads_created': payloads_created,
            'vector_chunks': vector_chunks,
            'files_uploaded': files_uploaded,
            'completed_at': datetime.now().isoformat(),
            'data_locations': {
                'structured': f"gs://{GCS_PROCESSED_BUCKET}/data/structured/",
                'payloads': f"gs://{GCS_PROCESSED_BUCKET}/data/payloads/",
                'vector_db': f"gs://{GCS_PROCESSED_BUCKET}/qdrant_index/"
            }
        }
        
        # Save report to GCS
        client = storage.Client(project=GCP_PROJECT_ID)
        bucket = client.bucket(GCS_PROCESSED_BUCKET)
        
        report_name = f"airflow_reports/initial_load_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        blob = bucket.blob(report_name)
        blob.upload_from_string(json.dumps(report, indent=2))
        
        logger.info("="*70)
        logger.info("📊 FINAL REPORT")
        logger.info("="*70)
        logger.info(f"✅ Report saved: gs://{GCS_PROCESSED_BUCKET}/{report_name}")
        logger.info(f"📊 Companies processed: {companies_processed}")
        logger.info(f"📋 Payloads created: {payloads_created}")
        logger.info(f"🔍 Vector chunks: {vector_chunks}")
        logger.info(f"📁 Files uploaded: {files_uploaded}")
        logger.info("="*70)
        
        return report
    
    except Exception as e:
        logger.error(f"Error generating report: {e}")
        raise


# Define DAG
with DAG(
    dag_id='orbit_initial_load_dag',
    default_args=default_args,
    description='Orbit Initial Load: Structured extraction → Payload assembly → Vector DB build',
    schedule_interval='@once',  # Manual trigger only
    start_date=datetime(2025, 1, 1),
    catchup=False,
    tags=['orbit', 'initial-load', 'payload-assembly', 'vector-db'],
) as dag:
    
    # Task 1: Download initial data from GCS
    task1_download = PythonOperator(
        task_id='download_initial_data',
        python_callable=download_initial_data_from_gcs,
        execution_timeout=timedelta(minutes=30),
    )
    
    # Task 2: Structured extraction
    task2_extract = PythonOperator(
        task_id='run_structured_extraction',
        python_callable=run_structured_extraction,
        execution_timeout=timedelta(hours=2),
    )
    
    # Task 3: Assemble payloads
    task3_assemble = PythonOperator(
        task_id='assemble_payloads',
        python_callable=assemble_payloads,
        execution_timeout=timedelta(minutes=30),
    )
    
    # Task 4: Build vector index
    task4_vector = PythonOperator(
        task_id='build_vector_index',
        python_callable=build_vector_index,
        execution_timeout=timedelta(hours=3),
    )
    
    # Task 5: Upload to GCS
    task5_upload = PythonOperator(
        task_id='upload_to_gcs',
        python_callable=upload_results_to_gcs,
        execution_timeout=timedelta(minutes=30),
    )
    
    # Task 6: Generate report
    task6_report = PythonOperator(
        task_id='generate_report',
        python_callable=generate_report,
    )
    
    # Execution order
    task1_download >> task2_extract >> task3_assemble >> task4_vector >> task5_upload >> task6_report

