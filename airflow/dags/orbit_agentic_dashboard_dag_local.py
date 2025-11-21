"""
Orbit Agentic Dashboard DAG - Local Execution
Invokes MCP + Agentic workflow daily for all AI 50 companies

This DAG is configured for LOCAL Airflow execution (not GCP Composer).
Uses local paths instead of /home/airflow paths.

Schedule: Daily at 4 AM UTC (0 4 * * *)
Or run manually for testing
"""

from airflow import DAG
from airflow.operators.python import PythonOperator
from datetime import datetime, timedelta
import sys
import logging
import asyncio
from pathlib import Path
from google.cloud import storage
import json
import os

# Detect if running locally, in Docker, or on GCP
# Docker: Use /opt/airflow paths
# GCP: Use /home/airflow paths
# Local: Use project root paths
if os.path.exists('/opt/airflow'):
    # Running in Docker
    PROJECT_ROOT = Path('/opt/airflow')
    DATA_DIR = PROJECT_ROOT / "data"
elif os.path.exists('/home/airflow'):
    # Running on GCP Composer
    PROJECT_ROOT = Path('/home/airflow/gcs/dags')
    DATA_DIR = Path('/home/airflow/data')
else:
    # Running locally
    PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
    DATA_DIR = PROJECT_ROOT / "data"

# Add project root to path for imports
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

logger = logging.getLogger(__name__)

# Configuration
GCP_PROJECT_ID = 'orbit-ai50-intelligence'
GCS_PROCESSED_BUCKET = 'orbit-processed-data-g1-2025'

# Seed file path
SEED_FILE = DATA_DIR / "forbes_ai50_seed.json"

default_args = {
    'owner': 'orbit-team',
    'depends_on_past': False,
    'email_on_failure': False,
    'retries': 1,
    'retry_delay': timedelta(minutes=5),
}


def get_ai50_companies(**context):
    """
    Task 1: Get list of all AI 50 companies.
    """
    logger.info("="*70)
    logger.info("TASK 1: Getting AI 50 Companies List")
    logger.info("="*70)
    
    try:
        # Try local seed file first
        if not SEED_FILE.exists():
            logger.warning(f"⚠️  Seed file not found at: {SEED_FILE}")
            
            # Check if GCS download is enabled (optional)
            enable_gcs_download = os.getenv('ENABLE_GCS_DOWNLOAD', 'false').lower() == 'true'
            
            if enable_gcs_download:
                logger.info("GCS download enabled. Attempting to download from GCS...")
                try:
                    # Try to use credentials file if available
                    credentials_path = os.getenv('GOOGLE_APPLICATION_CREDENTIALS')
                    if credentials_path and os.path.exists(credentials_path):
                        from google.oauth2 import service_account
                        credentials = service_account.Credentials.from_service_account_file(credentials_path)
                        client = storage.Client(project=GCP_PROJECT_ID, credentials=credentials)
                    else:
                        client = storage.Client(project=GCP_PROJECT_ID)
                    bucket = client.bucket(GCS_PROCESSED_BUCKET)
                    blob = bucket.blob('data/forbes_ai50_seed.json')
                    
                    SEED_FILE.parent.mkdir(parents=True, exist_ok=True)
                    blob.download_to_filename(str(SEED_FILE))
                    logger.info("✅ Downloaded seed file from GCS")
                except Exception as e:
                    logger.error(f"❌ Failed to download from GCS: {e}")
                    raise FileNotFoundError(f"Seed file not found locally and GCS download failed: {e}")
            else:
                # GCS download disabled - require local file
                error_msg = f"""
                Seed file not found locally and GCS download is disabled.
                
                Please ensure seed file exists at:
                {SEED_FILE}
                
                For local development, the seed file should be in:
                data/forbes_ai50_seed.json
                """
                logger.error(error_msg)
                raise FileNotFoundError(f"Seed file not found: {SEED_FILE}. GCS download disabled.")
        else:
            logger.info(f"✅ Using local seed file: {SEED_FILE}")
        
        # Load companies
        with open(SEED_FILE, 'r', encoding='utf-8') as f:
            companies_data = json.load(f)
        
        # Extract company IDs (normalize names)
        companies = []
        for company in companies_data:
            company_name = company.get('company_name', '')
            if company_name:
                # Normalize to company_id format
                company_id = company_name.lower().replace(' ', '_').replace('.', '').replace('-', '_')
                companies.append({
                    'company_id': company_id,
                    'company_name': company_name
                })
        
        logger.info(f"✅ Found {len(companies)} companies")
        
        context['task_instance'].xcom_push(key='companies', value=companies)
        context['task_instance'].xcom_push(key='company_count', value=len(companies))
        
        return len(companies)
    
    except Exception as e:
        logger.error(f"Error getting companies: {e}")
        import traceback
        logger.error(traceback.format_exc())
        raise


def run_agentic_workflow_sync(company_id: str, company_name: str) -> dict:
    """
    Synchronous wrapper for async workflow.
    """
    from src.workflows.due_diligence_graph import run_workflow
    
    # Run async workflow in event loop
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        result = loop.run_until_complete(run_workflow(company_id, auto_approve=True))
        return result
    finally:
        loop.close()


def process_companies_workflow(**context):
    """
    Task 2: Run agentic workflow for all companies.
    """
    logger.info("="*70)
    logger.info("TASK 2: Running Agentic Workflow for All Companies")
    logger.info("="*70)
    
    try:
        companies = context['task_instance'].xcom_pull(
            key='companies',
            task_ids='get_companies'
        )
        
        if not companies:
            raise Exception("No companies found")
        
        logger.info(f"Processing {len(companies)} companies...")
        
        results = []
        successful = 0
        failed = 0
        
        for i, company_info in enumerate(companies, 1):
            company_id = company_info['company_id']
            company_name = company_info['company_name']
            
            logger.info(f"\n[{i}/{len(companies)}] Processing: {company_name} ({company_id})")
            
            try:
                # Run workflow
                result = run_agentic_workflow_sync(company_id, company_name)
                
                # Extract key info
                workflow_result = {
                    'company_id': company_id,
                    'company_name': company_name,
                    'success': not result.get('error'),
                    'branch_taken': result.get('branch_taken', 'unknown'),
                    'dashboard_score': result.get('dashboard_score', 0),
                    'risks_detected': len(result.get('risk_keywords', [])),
                    'requires_hitl': result.get('requires_hitl', False),
                    'error': result.get('error'),
                    'dashboard_file': result.get('metadata', {}).get('dashboard_file'),
                    'trace_file': result.get('metadata', {}).get('trace_file'),
                }
                
                results.append(workflow_result)
                
                if workflow_result['success']:
                    successful += 1
                    logger.info(f"  ✅ Success: {company_name}")
                    logger.info(f"     Branch: {workflow_result['branch_taken']}, Score: {workflow_result['dashboard_score']:.1f}/100")
                else:
                    failed += 1
                    logger.warning(f"  ⚠️  Failed: {company_name} - {workflow_result.get('error', 'Unknown error')}")
            
            except Exception as e:
                failed += 1
                logger.error(f"  ❌ Error processing {company_name}: {e}")
                results.append({
                    'company_id': company_id,
                    'company_name': company_name,
                    'success': False,
                    'error': str(e)
                })
        
        logger.info("\n" + "="*70)
        logger.info(f"✅ Workflow processing complete: {successful} successful, {failed} failed")
        logger.info("="*70)
        
        context['task_instance'].xcom_push(key='workflow_results', value=results)
        context['task_instance'].xcom_push(key='successful', value=successful)
        context['task_instance'].xcom_push(key='failed', value=failed)
        
        return successful
    
    except Exception as e:
        logger.error(f"Error in workflow processing: {e}")
        import traceback
        logger.error(traceback.format_exc())
        raise


def upload_dashboards_to_gcs(**context):
    """
    Task 3: Upload generated dashboards to GCS (OPTIONAL - for cloud backup/sharing).
    
    For local development, this is optional. All files are saved locally.
    GCS upload is only needed if you want cloud backup or to share with team.
    """
    logger.info("="*70)
    logger.info("TASK 3: Uploading Dashboards to GCS (Optional)")
    logger.info("="*70)
    
    # Check if GCS upload is enabled (optional)
    enable_gcs_upload = os.getenv('ENABLE_GCS_UPLOAD', 'false').lower() == 'true'
    
    if not enable_gcs_upload:
        logger.info("ℹ️  GCS upload disabled (ENABLE_GCS_UPLOAD=false)")
        logger.info("ℹ️  All files saved locally:")
        logger.info(f"    - Dashboards: {DATA_DIR / 'dashboards' / 'workflow'}")
        logger.info(f"    - Traces: {PROJECT_ROOT / 'docs'}")
        logger.info(f"    - Reports: {DATA_DIR / 'airflow_reports'}")
        logger.info("✅ Local storage sufficient for development")
        context['task_instance'].xcom_push(key='dashboards_uploaded', value=0)
        return 0
    
    # Try GCS upload if enabled
    try:
        # Try to use credentials file if available
        credentials_path = os.getenv('GOOGLE_APPLICATION_CREDENTIALS')
        if credentials_path and os.path.exists(credentials_path):
            from google.oauth2 import service_account
            credentials = service_account.Credentials.from_service_account_file(credentials_path)
            client = storage.Client(project=GCP_PROJECT_ID, credentials=credentials)
            logger.info(f"Using credentials from: {credentials_path}")
        else:
            # Fallback to default credentials
            client = storage.Client(project=GCP_PROJECT_ID)
            logger.info("Using default credentials")
        bucket = client.bucket(GCS_PROCESSED_BUCKET)
        
        # Upload workflow dashboards
        dashboard_dir = DATA_DIR / "dashboards" / "workflow"
        upload_count = 0
        
        if dashboard_dir.exists():
            logger.info("Uploading workflow dashboards...")
            for file_path in dashboard_dir.glob('*.md'):
                blob_name = f"data/dashboards/workflow/{file_path.name}"
                blob = bucket.blob(blob_name)
                blob.upload_from_filename(str(file_path))
                upload_count += 1
                logger.info(f"  ✅ Uploaded: {file_path.name}")
        
        # Upload execution traces
        trace_dir = PROJECT_ROOT / "docs"
        if trace_dir.exists():
            logger.info("Uploading execution traces...")
            for file_path in trace_dir.glob('execution_trace_*.md'):
                blob_name = f"data/execution_traces/{file_path.name}"
                blob = bucket.blob(blob_name)
                blob.upload_from_filename(str(file_path))
                upload_count += 1
        
        logger.info(f"✅ Total files uploaded: {upload_count}")
        
        context['task_instance'].xcom_push(key='dashboards_uploaded', value=upload_count)
        
        return upload_count
    
    except Exception as e:
        logger.warning(f"⚠️  GCS upload failed: {e}")
        logger.warning("Continuing without GCS upload - files saved locally")
        logger.warning("This is OK for local development!")
        import traceback
        logger.warning(traceback.format_exc())
        # Don't raise - allow DAG to continue
        # Files are still saved locally in data/dashboards/workflow/
        context['task_instance'].xcom_push(key='dashboards_uploaded', value=0)
        return 0


def generate_agentic_report(**context):
    """
    Task 4: Generate final report.
    """
    logger.info("="*70)
    logger.info("TASK 4: Generating Agentic Dashboard Report")
    logger.info("="*70)
    
    try:
        company_count = context['task_instance'].xcom_pull(
            key='company_count',
            task_ids='get_companies'
        ) or 0
        
        successful = context['task_instance'].xcom_pull(
            key='successful',
            task_ids='process_workflow'
        ) or 0
        
        failed = context['task_instance'].xcom_pull(
            key='failed',
            task_ids='process_workflow'
        ) or 0
        
        workflow_results = context['task_instance'].xcom_pull(
            key='workflow_results',
            task_ids='process_workflow'
        ) or []
        
        dashboards_uploaded = context['task_instance'].xcom_pull(
            key='dashboards_uploaded',
            task_ids='upload_dashboards'
        ) or 0
        
        # Calculate statistics
        total_score = sum(r.get('dashboard_score', 0) for r in workflow_results if r.get('success'))
        avg_score = total_score / successful if successful > 0 else 0
        
        hitl_count = sum(1 for r in workflow_results if r.get('requires_hitl'))
        normal_count = successful - hitl_count
        
        total_risks = sum(r.get('risks_detected', 0) for r in workflow_results)
        
        report = {
            'dag_id': 'orbit_agentic_dashboard_dag_local',
            'execution_date': context['execution_date'].isoformat(),
            'status': 'SUCCESS',
            'summary': {
                'total_companies': company_count,
                'successful': successful,
                'failed': failed,
                'success_rate': (successful / company_count * 100) if company_count > 0 else 0
            },
            'workflow_stats': {
                'avg_dashboard_score': round(avg_score, 2),
                'hitl_required': hitl_count,
                'normal_flow': normal_count,
                'total_risks_detected': total_risks
            },
            'dashboards_uploaded': dashboards_uploaded,
            'completed_at': datetime.now().isoformat(),
            'results': workflow_results
        }
        
        # Save report locally
        reports_dir = DATA_DIR / "airflow_reports"
        reports_dir.mkdir(parents=True, exist_ok=True)
        
        report_file = reports_dir / f"agentic_dashboard_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        with open(report_file, 'w', encoding='utf-8') as f:
            json.dump(report, f, indent=2, default=str)
        
        logger.info(f"✅ Report saved locally: {report_file}")
        
        # Also save to GCS (optional - only if enabled)
        enable_gcs_upload = os.getenv('ENABLE_GCS_UPLOAD', 'false').lower() == 'true'
        if enable_gcs_upload:
            try:
                credentials_path = os.getenv('GOOGLE_APPLICATION_CREDENTIALS')
                if credentials_path and os.path.exists(credentials_path):
                    from google.oauth2 import service_account
                    credentials = service_account.Credentials.from_service_account_file(credentials_path)
                    client = storage.Client(project=GCP_PROJECT_ID, credentials=credentials)
                else:
                    client = storage.Client(project=GCP_PROJECT_ID)
                bucket = client.bucket(GCS_PROCESSED_BUCKET)
                
                report_name = f"airflow_reports/agentic_dashboard_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
                blob = bucket.blob(report_name)
                blob.upload_from_string(json.dumps(report, indent=2, default=str))
                
                logger.info(f"✅ Report also saved to GCS: gs://{GCS_PROCESSED_BUCKET}/{report_name}")
            except Exception as e:
                logger.warning(f"⚠️  Failed to upload report to GCS: {e}")
                logger.warning("Report saved locally - this is OK for development")
        else:
            logger.info("ℹ️  GCS upload disabled - report saved locally only")
        
        logger.info("="*70)
        logger.info("📊 AGENTIC DASHBOARD REPORT")
        logger.info("="*70)
        logger.info(f"📊 Total companies: {company_count}")
        logger.info(f"✅ Successful: {successful}")
        logger.info(f"❌ Failed: {failed}")
        logger.info(f"📈 Avg dashboard score: {avg_score:.1f}/100")
        logger.info(f"🚨 HITL required: {hitl_count}")
        logger.info(f"📁 Dashboards uploaded: {dashboards_uploaded}")
        logger.info("="*70)
        
        return report
    
    except Exception as e:
        logger.error(f"Error generating report: {e}")
        import traceback
        logger.error(traceback.format_exc())
        raise


# Define DAG
with DAG(
    dag_id='orbit_agentic_dashboard_dag_local',
    default_args=default_args,
    description='Orbit Agentic Dashboard (Local): Run MCP + Agentic workflow for all AI 50 companies',
    schedule_interval='0 4 * * *',  # Daily at 4 AM UTC (or None for manual only)
    start_date=datetime(2025, 1, 1),
    catchup=False,
    tags=['orbit', 'agentic', 'mcp', 'workflow', 'dashboard', 'local'],
) as dag:
    
    # Task 1: Get companies
    task1_companies = PythonOperator(
        task_id='get_companies',
        python_callable=get_ai50_companies,
        execution_timeout=timedelta(minutes=10),
    )
    
    # Task 2: Run workflow for all companies
    task2_workflow = PythonOperator(
        task_id='process_workflow',
        python_callable=process_companies_workflow,
        execution_timeout=timedelta(hours=4),  # Long timeout for all companies
    )
    
    # Task 3: Upload dashboards
    task3_upload = PythonOperator(
        task_id='upload_dashboards',
        python_callable=upload_dashboards_to_gcs,
        execution_timeout=timedelta(minutes=30),
    )
    
    # Task 4: Generate report
    task4_report = PythonOperator(
        task_id='generate_report',
        python_callable=generate_agentic_report,
    )
    
    # Execution order
    task1_companies >> task2_workflow >> task3_upload >> task4_report

