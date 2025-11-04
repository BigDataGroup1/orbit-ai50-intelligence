"""
DAG 2: AI50 Daily Refresh - SMART CONDITIONAL SCRAPING
Only scrapes dynamic pages (careers, blog, news) IF they exist (200 OK)
Schedule: Daily at 3 AM UTC

DEPLOYMENT:
1. Make sure DAG 1 ran successfully first!
2. Upload this file: gsutil cp ai50_daily_refresh_dag.py gs://us-central1-orbit-airflow-e-2044600e-bucket/dags/
3. Wait 2-3 minutes
4. Enable DAG in Airflow UI
5. Test with manual trigger first
6. Then let it run automatically daily
"""

from airflow import DAG
from airflow.operators.python import PythonOperator
from datetime import datetime, timedelta
import requests
from bs4 import BeautifulSoup
import json
import logging
from pathlib import Path
import time
from google.cloud import storage

logger = logging.getLogger(__name__)

# Configuration
GCP_PROJECT_ID = 'orbit-ai50-intelligence'
GCS_RAW_BUCKET = 'orbit-raw-data-group1-2025'
GCS_PROCESSED_BUCKET = 'orbit-processed-data-group1-2025'

# ONLY dynamic pages that change frequently
DYNAMIC_PAGES = {
    'careers': ['/careers', '/jobs', '/join-us', '/opportunities', '/work-with-us'],
    'blog': ['/blog', '/news', '/newsroom', '/insights', '/press', '/media'],
    'news': ['/news', '/newsroom', '/press', '/media', '/updates'],
}

default_args = {
    'owner': 'orbit-team',
    'depends_on_past': False,
    'email_on_failure': False,
    'retries': 2,
    'retry_delay': timedelta(minutes=5),
}


def download_seed_from_gcs(**context):
    """Task 1: Download seed file from GCS."""
    logger.info("="*70)
    logger.info("TASK 1: Downloading Seed File")
    logger.info("="*70)
    
    client = storage.Client(project=GCP_PROJECT_ID)
    bucket = client.bucket(GCS_PROCESSED_BUCKET)
    
    blob = bucket.blob('data/forbes_ai50_seed.json')
    
    local_path = Path('/home/airflow/gcs/data/forbes_ai50_seed.json')
    local_path.parent.mkdir(parents=True, exist_ok=True)
    
    try:
        blob.download_to_filename(str(local_path))
        logger.info("✅ Downloaded seed from GCS")
    except Exception as e:
        logger.error(f"Failed to download seed: {e}")
        raise
    
    # Load companies
    with open(local_path, 'r') as f:
        companies = json.load(f)
    
    logger.info(f"✅ Loaded {len(companies)} companies")
    
    context['task_instance'].xcom_push(key='companies', value=companies)
    context['task_instance'].xcom_push(key='company_count', value=len(companies))
    
    return len(companies)


def smart_check_page_exists(url: str, headers: dict) -> bool:
    """
    Smart check: Does this page exist and return 200?
    Returns True if page exists, False otherwise.
    """
    try:
        response = requests.head(
            url, 
            headers=headers, 
            timeout=10, 
            allow_redirects=True
        )
        
        # Check if page exists
        if response.status_code == 200:
            return True
        
        # Some servers don't support HEAD, try GET
        if response.status_code == 405:
            response = requests.get(
                url,
                headers=headers,
                timeout=10,
                allow_redirects=True
            )
            return response.status_code == 200
        
        return False
    
    except Exception as e:
        logger.debug(f"Page check failed for {url}: {e}")
        return False


def scrape_dynamic_pages_smart(**context):
    """
    Task 2: Smart scraping - ONLY scrape pages that exist!
    
    For each company:
      1. Check if careers page exists → scrape if 200
      2. Check if blog page exists → scrape if 200
      3. Check if news page exists → scrape if 200
      
    Skip 404s automatically!
    """
    logger.info("="*70)
    logger.info("TASK 2: Smart Dynamic Page Scraping")
    logger.info("="*70)
    
    companies = context['task_instance'].xcom_pull(
        key='companies',
        task_ids='download_seed'
    )
    
    if not companies:
        raise ValueError("No companies loaded!")
    
    headers = {
        'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
    }
    
    raw_dir = Path('/home/airflow/gcs/data/raw')
    raw_dir.mkdir(parents=True, exist_ok=True)
    
    session_name = f"{datetime.now().strftime('%Y-%m-%d')}_daily"
    
    # Statistics
    stats = {
        'total_companies': len(companies),
        'companies_with_updates': 0,
        'pages_scraped': 0,
        'pages_skipped': 0,
        'page_type_counts': {
            'careers': 0,
            'blog': 0,
            'news': 0
        }
    }
    
    results = []
    
    # Scrape each company
    for i, company in enumerate(companies, 1):
        company_name = company['company_name']
        website = company.get('website', 'Not available')
        
        logger.info(f"\n[{i}/{len(companies)}] {company_name}")
        
        if not website or website == 'Not available':
            logger.info("  ⚠️  No website, skipping")
            continue
        
        # Create session directory
        company_dir = raw_dir / company_name.replace(' ', '_').replace('/', '_')
        session_dir = company_dir / session_name
        session_dir.mkdir(parents=True, exist_ok=True)
        
        company_result = {
            'company_name': company_name,
            'website': website,
            'scraped_at': datetime.now().isoformat(),
            'pages_found': []
        }
        
        # Try each dynamic page type
        for page_type, url_patterns in DYNAMIC_PAGES.items():
            
            logger.info(f"  🔍 Checking {page_type}...")
            
            # Try to find the page
            page_url = None
            for pattern in url_patterns:
                test_url = website.rstrip('/') + pattern
                
                # Smart check: does this page exist?
                if smart_check_page_exists(test_url, headers):
                    page_url = test_url
                    logger.info(f"    ✅ Found: {test_url}")
                    break
            
            if not page_url:
                logger.info(f"    ⏭️  {page_type}: not found, skipping")
                stats['pages_skipped'] += 1
                continue
            
            # Page exists! Scrape it
            try:
                logger.info(f"    📥 Scraping {page_type}...")
                
                response = requests.get(
                    page_url,
                    headers=headers,
                    timeout=30,
                    allow_redirects=True
                )
                
                if response.status_code == 200:
                    html = response.text
                    soup = BeautifulSoup(html, 'html.parser')
                    
                    # Clean HTML
                    for tag in soup(["script", "style", "nav", "footer"]):
                        tag.decompose()
                    
                    text = soup.get_text()
                    
                    # Save both HTML and text
                    (session_dir / f"{page_type}.html").write_text(html, encoding='utf-8')
                    (session_dir / f"{page_type}.txt").write_text(text, encoding='utf-8')
                    
                    company_result['pages_found'].append(page_type)
                    stats['pages_scraped'] += 1
                    stats['page_type_counts'][page_type] += 1
                    
                    logger.info(f"    ✅ Saved {page_type}")
                
                time.sleep(2)  # Rate limiting
                
            except Exception as e:
                logger.error(f"    ❌ Error scraping {page_type}: {e}")
                stats['pages_skipped'] += 1
        
        # Save metadata for this company
        if company_result['pages_found']:
            (session_dir / "metadata.json").write_text(
                json.dumps(company_result, indent=2)
            )
            stats['companies_with_updates'] += 1
        
        results.append(company_result)
        
        time.sleep(3)  # Rate limiting between companies
    
    # Summary
    logger.info("\n" + "="*70)
    logger.info("SCRAPING SUMMARY")
    logger.info("="*70)
    logger.info(f"Total companies: {stats['total_companies']}")
    logger.info(f"Companies with updates: {stats['companies_with_updates']}")
    logger.info(f"Pages scraped: {stats['pages_scraped']}")
    logger.info(f"Pages skipped (404): {stats['pages_skipped']}")
    logger.info(f"\nPage breakdown:")
    logger.info(f"  Careers: {stats['page_type_counts']['careers']}")
    logger.info(f"  Blog: {stats['page_type_counts']['blog']}")
    logger.info(f"  News: {stats['page_type_counts']['news']}")
    
    # Push stats to XCom
    context['task_instance'].xcom_push(key='stats', value=stats)
    context['task_instance'].xcom_push(key='results', value=results)
    
    return stats


def upload_daily_updates_to_gcs(**context):
    """Task 3: Upload ONLY today's scraped data to GCS."""
    logger.info("="*70)
    logger.info("TASK 3: Uploading Daily Updates")
    logger.info("="*70)
    
    client = storage.Client(project=GCP_PROJECT_ID)
    bucket = client.bucket(GCS_RAW_BUCKET)
    
    # Today's session folder
    session_name = f"{datetime.now().strftime('%Y-%m-%d')}_daily"
    raw_dir = Path('/home/airflow/gcs/data/raw')
    
    upload_count = 0
    
    if raw_dir.exists():
        for file_path in raw_dir.rglob('*'):
            if file_path.is_file() and session_name in str(file_path):
                try:
                    relative = file_path.relative_to(Path('/home/airflow/gcs/data'))
                    blob_name = f"data/{relative}"
                    
                    blob = bucket.blob(blob_name)
                    blob.upload_from_filename(str(file_path))
                    upload_count += 1
                    
                except Exception as e:
                    logger.error(f"Error uploading {file_path}: {e}")
    
    logger.info(f"✅ Uploaded {upload_count} files to gs://{GCS_RAW_BUCKET}/")
    
    context['task_instance'].xcom_push(key='files_uploaded', value=upload_count)
    
    return upload_count


def generate_daily_report(**context):
    """Task 4: Generate daily refresh report."""
    logger.info("="*70)
    logger.info("TASK 4: Generating Daily Report")
    logger.info("="*70)
    
    # Get stats from scraping task
    stats = context['task_instance'].xcom_pull(
        key='stats',
        task_ids='scrape_dynamic_pages'
    )
    
    files_uploaded = context['task_instance'].xcom_pull(
        key='files_uploaded',
        task_ids='upload_to_gcs'
    )
    
    report = {
        'dag_id': 'ai50_daily_refresh_dag',
        'execution_date': context['execution_date'].isoformat(),
        'status': 'SUCCESS',
        'total_companies': stats.get('total_companies', 0),
        'companies_with_updates': stats.get('companies_with_updates', 0),
        'pages_scraped': stats.get('pages_scraped', 0),
        'pages_skipped_404': stats.get('pages_skipped', 0),
        'page_breakdown': stats.get('page_type_counts', {}),
        'files_uploaded': files_uploaded,
        'completed_at': datetime.now().isoformat(),
    }
    
    # Save report to GCS
    client = storage.Client(project=GCP_PROJECT_ID)
    bucket = client.bucket(GCS_PROCESSED_BUCKET)
    
    report_name = f"reports/daily_refresh_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    blob = bucket.blob(report_name)
    blob.upload_from_string(json.dumps(report, indent=2))
    
    logger.info(f"✅ Report saved: gs://{GCS_PROCESSED_BUCKET}/{report_name}")
    logger.info(f"   Companies checked: {report['total_companies']}")
    logger.info(f"   Companies with updates: {report['companies_with_updates']}")
    logger.info(f"   Pages scraped: {report['pages_scraped']}")
    logger.info(f"   Pages skipped: {report['pages_skipped_404']}")
    
    return report


# Define DAG
with DAG(
    dag_id='ai50_daily_refresh_dag',
    default_args=default_args,
    description='Lab 2: Daily refresh - smart conditional scraping of dynamic pages only',
    schedule_interval='0 3 * * *',  # Daily at 3 AM UTC
    start_date=datetime(2025, 11, 3),
    catchup=False,
    tags=['orbit', 'lab2', 'daily', 'automated', 'smart-scraping'],
) as dag:
    
    # Task 1: Download seed file
    task1_download = PythonOperator(
        task_id='download_seed',
        python_callable=download_seed_from_gcs,
    )
    
    # Task 2: Smart conditional scraping
    task2_scrape = PythonOperator(
        task_id='scrape_dynamic_pages',
        python_callable=scrape_dynamic_pages_smart,
        execution_timeout=timedelta(hours=2),
    )
    
    # Task 3: Upload updates
    task3_upload = PythonOperator(
        task_id='upload_to_gcs',
        python_callable=upload_daily_updates_to_gcs,
    )
    
    # Task 4: Generate report
    task4_report = PythonOperator(
        task_id='generate_report',
        python_callable=generate_daily_report,
    )
    
    # Define execution order
    task1_download >> task2_scrape >> task3_upload >> task4_report