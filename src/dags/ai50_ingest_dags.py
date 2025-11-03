"""
DAG 1: AI50 Full Ingest - Manual Trigger
Initial complete scraping of all Forbes profiles + all website pages
Schedule: @once (manual trigger only)
"""

from airflow import DAG
from airflow.operators.python import PythonOperator
from airflow.providers.google.cloud.transfers.local_to_gcs import LocalFilesystemToGCSOperator
from datetime import datetime, timedelta
import json
import logging
from pathlib import Path
import requests
from bs4 import BeautifulSoup
import time
import re
from google.cloud import storage

# Configuration
GCP_PROJECT_ID = 'orbit-ai50-intelligence'
GCS_RAW_BUCKET = 'orbit-raw-data-at-2025'
GCS_PROCESSED_BUCKET = 'orbit-processed-data-at-2025'

logger = logging.getLogger(__name__)

default_args = {
    'owner': 'orbit-team',
    'depends_on_past': False,
    'email_on_failure': False,
    'retries': 2,
    'retry_delay': timedelta(minutes=5),
}


def scrape_all_companies(**context):
    """Scrape all 50 companies - Forbes + Websites."""
    logger.info("="*70)
    logger.info("FULL INGEST: Scraping all companies")
    logger.info("="*70)
    
    # Load seed file
    seed_path = Path('/home/airflow/gcs/data/forbes_ai50_seed.json')
    
    if not seed_path.exists():
        raise FileNotFoundError(f"Seed file not found: {seed_path}")
    
    with open(seed_path, 'r') as f:
        companies = json.load(f)
    
    logger.info(f"Loaded {len(companies)} companies")
    
    # Setup directories
    raw_dir = Path('/home/airflow/gcs/data/raw')
    raw_dir.mkdir(parents=True, exist_ok=True)
    
    session_name = f"{datetime.now().strftime('%Y-%m-%d')}_initial"
    
    all_intel = []
    successful = 0
    
    # Headers for requests
    headers = {
        'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
    }
    
    # Page patterns
    page_patterns = {
        'homepage': ['/', ''],
        'about': ['/about', '/about-us', '/company'],
        'pricing': ['/pricing', '/plans'],
        'product': ['/product', '/products', '/platform', '/solutions'],
        'careers': ['/careers', '/jobs'],
        'blog': ['/blog', '/news', '/newsroom'],
        'customers': ['/customers', '/case-studies'],
    }
    
    # Scrape each company
    for i, company in enumerate(companies, 1):
        company_name = company['company_name']
        website = company.get('website', 'Not available')
        
        logger.info(f"[{i}/{len(companies)}] {company_name}")
        
        # Skip if no website
        if not website or website == 'Not available':
            logger.warning(f"  No website for {company_name}")
            continue
        
        # Create company directory
        company_dir = raw_dir / company_name.replace(' ', '_').replace('/', '_')
        session_dir = company_dir / session_name
        session_dir.mkdir(parents=True, exist_ok=True)
        
        intel = {
            'company_name': company_name,
            'website': website,
            'scraped_at': datetime.now().isoformat(),
            'pages': {},
            'seed_data': company
        }
        
        # Scrape all pages
        for page_type, patterns in page_patterns.items():
            try:
                # Find page URL
                page_url = None
                if page_type == 'homepage':
                    page_url = website
                else:
                    for pattern in patterns:
                        test_url = website.rstrip('/') + pattern
                        try:
                            resp = requests.head(test_url, headers=headers, timeout=10)
                            if resp.status_code == 200:
                                page_url = test_url
                                break
                        except:
                            continue
                
                if not page_url:
                    intel['pages'][page_type] = {'found': False}
                    continue
                
                # Scrape page
                logger.info(f"  Scraping {page_type}: {page_url}")
                response = requests.get(page_url, headers=headers, timeout=30)
                
                if response.status_code == 200:
                    html = response.text
                    soup = BeautifulSoup(html, 'html.parser')
                    
                    # Remove scripts/styles
                    for tag in soup(["script", "style"]):
                        tag.decompose()
                    
                    text = soup.get_text()
                    
                    # Save files
                    (session_dir / f"{page_type}.html").write_text(html, encoding='utf-8')
                    (session_dir / f"{page_type}.txt").write_text(text, encoding='utf-8')
                    
                    intel['pages'][page_type] = {
                        'url': page_url,
                        'success': True,
                        'scraped_at': datetime.now().isoformat()
                    }
                    
                    logger.info(f"    ✅ Saved {page_type}")
                
                time.sleep(2)
                
            except Exception as e:
                logger.error(f"  Error scraping {page_type}: {e}")
                intel['pages'][page_type] = {'error': str(e)}
        
        # Save intelligence
        (session_dir / "intelligence.json").write_text(json.dumps(intel, indent=2))
        
        all_intel.append(intel)
        
        if any(p.get('success') for p in intel['pages'].values()):
            successful += 1
        
        # Rate limit between companies
        time.sleep(5)
    
    # Save summary
    summary = {
        'dag_id': 'ai50_full_ingest_dag',
        'execution_date': context['execution_date'].isoformat(),
        'total_companies': len(companies),
        'successful': successful,
        'scraped_at': datetime.now().isoformat(),
    }
    
    summary_path = Path('/home/airflow/gcs/data/full_ingest_summary.json')
    summary_path.write_text(json.dumps(summary, indent=2))
    
    logger.info(f"✅ Complete: {successful}/{len(companies)} companies scraped")
    
    return summary


def upload_to_gcs(**context):
    """Upload all scraped data to GCS."""
    logger.info("Uploading data to GCS")
    
    client = storage.Client(project=GCP_PROJECT_ID)
    bucket = client.bucket(GCS_RAW_BUCKET)
    
    data_dir = Path('/home/airflow/gcs/data/raw')
    upload_count = 0
    
    # Upload all files
    for file_path in data_dir.rglob('*'):
        if file_path.is_file():
            relative_path = file_path.relative_to(data_dir.parent)
            blob_name = str(relative_path)
            
            blob = bucket.blob(blob_name)
            blob.upload_from_filename(str(file_path))
            upload_count += 1
    
    logger.info(f"✅ Uploaded {upload_count} files")
    
    return upload_count


# Define DAG
with DAG(
    'ai50_full_ingest_dag',
    default_args=default_args,
    description='Lab 2: Full initial ingestion of all AI50 companies',
    schedule_interval='@once',  # Manual trigger only
    start_date=datetime(2025, 11, 3),
    catchup=False,
    tags=['orbit', 'lab2', 'full-load', 'manual'],
) as dag:
    
    scrape_task = PythonOperator(
        task_id='scrape_all_companies',
        python_callable=scrape_all_companies,
        execution_timeout=timedelta(hours=4),
    )
    
    upload_task = PythonOperator(
        task_id='upload_to_gcs',
        python_callable=upload_to_gcs,
    )
    
    scrape_task >> upload_task