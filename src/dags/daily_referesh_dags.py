"""
DAG 2: AI50 Daily Refresh - Automated Daily
Re-scrapes ONLY dynamic pages (careers, blog, news)
Schedule: Daily at 3 AM UTC
"""

from airflow import DAG
from airflow.operators.python import PythonOperator
from datetime import datetime, timedelta
import json
import logging
from pathlib import Path
import requests
from bs4 import BeautifulSoup
import time
from google.cloud import storage

# Configuration
GCP_PROJECT_ID = 'orbit-ai50-intelligence'
GCS_RAW_BUCKET = 'orbit-raw-data-at-2025'
GCS_PROCESSED_BUCKET = 'orbit-processed-data-at-2025'

# ONLY dynamic pages that change frequently
DYNAMIC_PAGES = ['careers', 'blog', 'news']

logger = logging.getLogger(__name__)

default_args = {
    'owner': 'orbit-team',
    'depends_on_past': False,
    'email_on_failure': False,
    'retries': 2,
    'retry_delay': timedelta(minutes=5),
}


def download_seed_from_gcs(**context):
    """Download latest seed file from GCS."""
    logger.info("Downloading seed file from GCS")
    
    client = storage.Client(project=GCP_PROJECT_ID)
    bucket = client.bucket(GCS_RAW_BUCKET)
    
    # Try to download from GCS, fallback to local
    blob = bucket.blob('data/forbes_ai50_seed.json')
    
    local_path = Path('/home/airflow/gcs/data/forbes_ai50_seed.json')
    local_path.parent.mkdir(parents=True, exist_ok=True)
    
    try:
        blob.download_to_filename(str(local_path))
        logger.info(f"✅ Downloaded seed from GCS")
    except:
        logger.warning("Seed not in GCS, using local version")
    
    with open(local_path, 'r') as f:
        companies = json.load(f)
    
    logger.info(f"Loaded {len(companies)} companies")
    context['task_instance'].xcom_push(key='companies', value=companies)
    
    return len(companies)


def scrape_dynamic_pages_only(**context):
    """Scrape ONLY dynamic pages: careers, blog, news."""
    logger.info("="*70)
    logger.info("DAILY REFRESH: Scraping dynamic pages only")
    logger.info("="*70)
    
    companies = context['task_instance'].xcom_pull(key='companies', task_ids='download_seed')
    
    if not companies:
        raise ValueError("No companies loaded")
    
    logger.info(f"Scraping {len(companies)} companies")
    logger.info(f"Pages to scrape: {DYNAMIC_PAGES}")
    
    # Setup
    raw_dir = Path('/home/airflow/gcs/data/raw')
    raw_dir.mkdir(parents=True, exist_ok=True)
    
    session_name = f"{datetime.now().strftime('%Y-%m-%d')}_daily"
    
    headers = {
        'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
    }
    
    # Page URL patterns
    page_patterns = {
        'careers': ['/careers', '/jobs', '/join-us', '/opportunities'],
        'blog': ['/blog', '/news', '/newsroom', '/insights', '/press'],
        'news': ['/news', '/newsroom', '/press', '/media'],
    }
    
    all_results = []
    successful = 0
    total_pages_scraped = 0
    
    # Scrape each company
    for i, company in enumerate(companies, 1):
        company_name = company['company_name']
        website = company.get('website', 'Not available')
        
        logger.info(f"[{i}/{len(companies)}] {company_name}")
        
        if not website or website == 'Not available':
            logger.warning(f"  No website, skipping")
            continue
        
        # Create session directory
        company_dir = raw_dir / company_name.replace(' ', '_').replace('/', '_')
        session_dir = company_dir / session_name
        session_dir.mkdir(parents=True, exist_ok=True)
        
        result = {
            'company_name': company_name,
            'website': website,
            'scraped_at': datetime.now().isoformat(),
            'session': session_name,
            'pages_scraped': []
        }
        
        # Scrape only dynamic pages
        for page_type in DYNAMIC_PAGES:
            try:
                # Find page URL
                page_url = None
                patterns = page_patterns.get(page_type, [])
                
                for pattern in patterns:
                    test_url = website.rstrip('/') + pattern
                    try:
                        resp = requests.head(test_url, headers=headers, timeout=10, allow_redirects=True)
                        if resp.status_code == 200:
                            page_url = test_url
                            break
                    except:
                        continue
                
                if not page_url:
                    logger.info(f"  {page_type}: not found")
                    continue
                
                # Scrape
                logger.info(f"  Scraping {page_type}: {page_url}")
                response = requests.get(page_url, headers=headers, timeout=30, allow_redirects=True)
                
                if response.status_code == 200:
                    html = response.text
                    soup = BeautifulSoup(html, 'html.parser')
                    
                    # Clean
                    for tag in soup(["script", "style", "nav", "footer"]):
                        tag.decompose()
                    
                    text = soup.get_text()
                    
                    # Save
                    (session_dir / f"{page_type}.html").write_text(html, encoding='utf-8')
                    (session_dir / f"{page_type}.txt").write_text(text, encoding='utf-8')
                    
                    result['pages_scraped'].append(page_type)
                    total_pages_scraped += 1
                    
                    logger.info(f"    ✅ Saved")
                
                time.sleep(2)
                
            except Exception as e:
                logger.error(f"  Error scraping {page_type}: {e}")
        
        # Save metadata
        (session_dir / "metadata.json").write_text(json.dumps(result, indent=2))
        
        all_results.append(result)
        
        if result['pages_scraped']:
            successful += 1
        
        time.sleep(3)
    
    # Summary
    summary = {
        'dag_id': 'ai50_full_ingest_dag',
        'execution_date': context['execution_date'].isoformat(),
        'session': session_name,
        'total_companies': len(companies),
        'successful': successful,
        'total_pages': total_pages_scraped,
        'scraped_at': datetime.now().isoformat(),
    }
    
    logger.info(f"✅ Scraped {successful}/{len(companies)} companies, {total_pages_scraped} pages")
    
    context['task_instance'].xcom_push(key='summary', value=summary)
    
    return summary


def upload_results_to_gcs(**context):
    """Upload scraped data to GCS."""
    logger.info("Uploading to GCS")
    
    client = storage.Client(project=GCP_PROJECT_ID)
    bucket = client.bucket(GCS_RAW_BUCKET)
    
    data_dir = Path('/home/airflow/gcs/data/raw')
    
    if not data_dir.exists():
        logger.warning("No data directory found")
        return 0
    
    upload_count = 0
    
    # Upload all files
    for file_path in data_dir.rglob('*'):
        if file_path.is_file():
            try:
                relative = file_path.relative_to(data_dir.parent)
                blob_name = str(relative)
                
                blob = bucket.blob(blob_name)
                blob.upload_from_filename(str(file_path))
                
                upload_count += 1
                
            except Exception as e:
                logger.error(f"Error uploading {file_path}: {e}")
    
    logger.info(f"✅ Uploaded {upload_count} files to gs://{GCS_RAW_BUCKET}/")
    
    return upload_count


def generate_full_report(**context):
    """Generate comprehensive report."""
    logger.info("Generating report")
    
    summary = context['task_instance'].xcom_pull(key='summary', task_ids='scrape_all')
    
    if not summary:
        summary = {'error': 'No summary data'}
    
    # Save to GCS
    client = storage.Client(project=GCP_PROJECT_ID)
    bucket = client.bucket(GCS_PROCESSED_BUCKET)
    
    report_name = f"reports/full_ingest_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    blob = bucket.blob(report_name)
    blob.upload_from_string(json.dumps(summary, indent=2))
    
    logger.info(f"✅ Report saved: gs://{GCS_PROCESSED_BUCKET}/{report_name}")
    
    return report_name


# Define DAG
with DAG(
    'ai50_full_ingest_dag',
    default_args=default_args,
    description='Lab 2: Full initial ingestion - manual trigger only',
    schedule_interval='@once',
    start_date=datetime(2025, 11, 3),
    catchup=False,
    tags=['orbit', 'lab2', 'full-load', 'manual'],
) as dag:
    
    download = PythonOperator(
        task_id='download_seed',
        python_callable=download_seed_from_gcs,
    )
    
    scrape = PythonOperator(
        task_id='scrape_all',
        python_callable=scrape_all_companies,
        execution_timeout=timedelta(hours=4),
    )
    
    upload = PythonOperator(
        task_id='upload_to_gcs',
        python_callable=upload_results_to_gcs,
    )
    
    report = PythonOperator(
        task_id='generate_report',
        python_callable=generate_full_report,
    )
    
    download >> scrape >> upload >> report