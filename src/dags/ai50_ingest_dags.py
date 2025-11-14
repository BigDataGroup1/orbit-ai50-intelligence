"""
DAG 1: AI50 Full Initial Ingest - ONE-TIME LOAD
Orchestrates: forbes_scraper.py → scraper_robust.py → GCS Upload
Schedule: @once (manual trigger only)

SIMPLE FIX: Changed paths from /home/airflow/gcs/data/ to /home/airflow/data/
(Your original scrapers use parents[2] which resolves to /home/airflow/data/)
"""

from airflow import DAG
from airflow.operators.python import PythonOperator
from datetime import datetime, timedelta
import subprocess
import json
import logging
from pathlib import Path
from google.cloud import storage

logger = logging.getLogger(__name__)

# Configuration
GCP_PROJECT_ID = 'orbit-ai50-intelligence'
GCS_RAW_BUCKET = 'orbit-raw-data-g1-2025'
GCS_PROCESSED_BUCKET = 'orbit-processed-data-g1-2025'

default_args = {
    'owner': 'orbit-team',
    'depends_on_past': False,
    'email_on_failure': False,
    'retries': 1,
    'retry_delay': timedelta(minutes=5),
}


def run_forbes_scraper(**context):
    """Task 1: Run forbes_scraper.py to generate seed file."""
    logger.info("="*70)
    logger.info("TASK 1: Running Forbes Scraper")
    logger.info("="*70)
    
    scraper_path = Path('/home/airflow/gcs/dags/forbes_scraper.py')
    
    try:
        # Run the script with --fresh flag (no resume, clean start)
        result = subprocess.run(
            ['python3', str(scraper_path), '--fresh', '--no-validate'],
            capture_output=True,
            text=True,
            timeout=1800  # 30 minutes max
        )
        
        logger.info(f"Forbes scraper output:\n{result.stdout}")
        
        if result.returncode != 0:
            logger.error(f"Forbes scraper failed:\n{result.stderr}")
            raise Exception(f"Forbes scraper failed with code {result.returncode}")
        
        # Check seed file was created - FIXED PATH
        seed_file = Path('/home/airflow/data/forbes_ai50_seed.json')
        if not seed_file.exists():
            raise Exception(f"Seed file not created at {seed_file}")
        
        # Validate it's valid JSON
        with open(seed_file, 'r') as f:
            companies = json.load(f)
        
        logger.info(f"✅ Forbes scraper completed: {len(companies)} companies")
        logger.info(f"✅ Seed file saved at: {seed_file}")
        
        context['task_instance'].xcom_push(key='seed_file', value=str(seed_file))
        context['task_instance'].xcom_push(key='company_count', value=len(companies))
        
        return len(companies)
    
    except Exception as e:
        logger.error(f"Error running Forbes scraper: {e}")
        raise


def run_full_website_scraper(**context):
    """Task 2: Run scraper_robust.py to scrape ALL pages."""
    logger.info("="*70)
    logger.info("TASK 2: Running Full Website Scraper")
    logger.info("="*70)
    
    scraper_path = Path('/home/airflow/gcs/dags/scraper_robust.py')
    
    try:
        # Run the script with BOTH inputs:
        # 1st question: "Test with first 5 companies? (y/n):" → n
        # 2nd question: "Proceed? (y/n):" → y
        result = subprocess.run(
            ['python3', str(scraper_path)],
            input='n\ny\n',  # FIXED: Two answers!
            capture_output=True,
            text=True,
            timeout=7200  # 2 hours max
        )
        
        logger.info(f"Website scraper output:\n{result.stdout}")
        
        if result.returncode != 0:
            logger.error(f"Website scraper failed:\n{result.stderr}")
            raise Exception(f"Website scraper failed with code {result.returncode}")
        
        # Verify summary file was created - FIXED PATH
        summary_file = Path('/home/airflow/data').glob('lab1_bulletproof_summary_*.json')
        summary_files = list(summary_file)
        
        if summary_files:
            logger.info(f"✅ Found summary file: {summary_files[0]}")
        else:
            logger.warning("⚠️ Summary file not found (but scraping may have completed)")
        
        logger.info("✅ Full website scraping completed")
        return "success"
    
    except Exception as e:
        logger.error(f"Error running website scraper: {e}")
        raise


def upload_all_to_gcs(**context):
    """Task 3: Upload ALL scraped data to GCS (RAW + PROCESSED buckets)."""
    logger.info("="*70)
    logger.info("TASK 3: Uploading to GCS")
    logger.info("="*70)
    
    client = storage.Client(project=GCP_PROJECT_ID)
    raw_bucket = client.bucket(GCS_RAW_BUCKET)
    processed_bucket = client.bucket(GCS_PROCESSED_BUCKET)
    
    upload_count = 0
    
    # 1. Upload seed file to BOTH buckets - FIXED PATH
    seed_file = Path('/home/airflow/data/forbes_ai50_seed.json')
    if seed_file.exists():
        # RAW bucket
        blob_raw = raw_bucket.blob('data/forbes_ai50_seed.json')
        blob_raw.upload_from_filename(str(seed_file))
        upload_count += 1
        logger.info(f"✅ Uploaded seed to RAW: gs://{GCS_RAW_BUCKET}/data/forbes_ai50_seed.json")
        
        # PROCESSED bucket
        blob_processed = processed_bucket.blob('data/forbes_ai50_seed.json')
        blob_processed.upload_from_filename(str(seed_file))
        upload_count += 1
        logger.info(f"✅ Uploaded seed to PROCESSED: gs://{GCS_PROCESSED_BUCKET}/data/forbes_ai50_seed.json")
    else:
        logger.error(f"❌ Seed file not found at {seed_file}")
    
    # 2. Upload summary file to RAW bucket - FIXED PATH
    data_dir = Path('/home/airflow/data')
    for summary_file in data_dir.glob('lab1_bulletproof_summary_*.json'):
        try:
            blob_name = f"data/{summary_file.name}"
            blob = raw_bucket.blob(blob_name)
            blob.upload_from_filename(str(summary_file))
            upload_count += 1
            logger.info(f"✅ Uploaded summary: gs://{GCS_RAW_BUCKET}/{blob_name}")
        except Exception as e:
            logger.error(f"Error uploading summary: {e}")
    
    # 3. Upload ALL raw data (HTML, TXT, intelligence.json) to RAW bucket - FIXED PATH
    raw_dir = Path('/home/airflow/data/raw')
    if raw_dir.exists():
        logger.info(f"📂 Uploading raw data from: {raw_dir}")
        
        for file_path in raw_dir.rglob('*'):
            if file_path.is_file():
                try:
                    # Create relative path: raw/Abridge/2025-11-05_initial/homepage.html
                    relative = file_path.relative_to(data_dir)
                    blob_name = f"data/{relative}"
                    
                    blob = raw_bucket.blob(blob_name)
                    blob.upload_from_filename(str(file_path))
                    upload_count += 1
                    
                    # Progress indicator
                    if upload_count % 50 == 0:
                        logger.info(f"  📤 Uploaded {upload_count} files...")
                    
                except Exception as e:
                    logger.error(f"Error uploading {file_path}: {e}")
    else:
        logger.warning(f"⚠️ Raw directory not found: {raw_dir}")
    
    logger.info("="*70)
    logger.info(f"✅ UPLOAD COMPLETE: {upload_count} files total")
    logger.info("="*70)
    logger.info(f"📦 RAW bucket: gs://{GCS_RAW_BUCKET}/data/")
    logger.info(f"   - forbes_ai50_seed.json")
    logger.info(f"   - lab1_bulletproof_summary_*.json")
    logger.info(f"   - raw/ (all company data)")
    logger.info(f"📦 PROCESSED bucket: gs://{GCS_PROCESSED_BUCKET}/data/")
    logger.info(f"   - forbes_ai50_seed.json (ONLY)")
    
    context['task_instance'].xcom_push(key='files_uploaded', value=upload_count)
    return upload_count


def generate_full_ingest_report(**context):
    """Task 4: Generate comprehensive report."""
    logger.info("="*70)
    logger.info("TASK 4: Generating Report")
    logger.info("="*70)
    
    company_count = context['task_instance'].xcom_pull(
        key='company_count',
        task_ids='run_forbes_scraper'
    )
    
    files_uploaded = context['task_instance'].xcom_pull(
        key='files_uploaded',
        task_ids='upload_to_gcs'
    )
    
    # Read the summary file for detailed stats - FIXED PATH
    data_dir = Path('/home/airflow/data')
    summary_files = list(data_dir.glob('lab1_bulletproof_summary_*.json'))
    
    summary_stats = {}
    if summary_files:
        try:
            with open(summary_files[0], 'r') as f:
                summary_data = json.load(f)
                summary_stats = summary_data.get('statistics', {})
        except Exception as e:
            logger.warning(f"Could not read summary file: {e}")
    
    report = {
        'dag_id': 'ai50_full_ingest_dag',
        'execution_date': context['execution_date'].isoformat(),
        'status': 'SUCCESS',
        'companies_scraped': company_count,
        'files_uploaded': files_uploaded,
        'scraping_stats': summary_stats,
        'data_locations': {
            'raw_bucket': f"gs://{GCS_RAW_BUCKET}/data/",
            'processed_bucket': f"gs://{GCS_PROCESSED_BUCKET}/data/forbes_ai50_seed.json",
        },
        'completed_at': datetime.now().isoformat(),
    }
    
    # Save report to PROCESSED bucket
    client = storage.Client(project=GCP_PROJECT_ID)
    bucket = client.bucket(GCS_PROCESSED_BUCKET)
    
    report_name = f"reports/full_ingest_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    blob = bucket.blob(report_name)
    blob.upload_from_string(json.dumps(report, indent=2))
    
    logger.info("="*70)
    logger.info("📊 FINAL REPORT")
    logger.info("="*70)
    logger.info(f"✅ Report saved: gs://{GCS_PROCESSED_BUCKET}/{report_name}")
    logger.info(f"📊 Companies: {company_count}")
    logger.info(f"📁 Files uploaded: {files_uploaded}")
    logger.info(f"📄 Pages scraped: {summary_stats.get('total_pages', 'N/A')}")
    logger.info(f"💰 With pricing: {summary_stats.get('with_pricing', 'N/A')}")
    logger.info(f"👥 With customers: {summary_stats.get('with_customers', 'N/A')}")
    logger.info("="*70)
    
    return report


# Define DAG
with DAG(
    dag_id='ai50_full_ingest_dag',
    default_args=default_args,
    description='Lab 2: Full initial load - Forbes scraper → Website scraper → GCS',
    schedule_interval='@once',  # Manual trigger only
    start_date=datetime(2025, 11, 3),
    catchup=False,
    tags=['orbit', 'lab2', 'full-load', 'initial', 'manual'],
) as dag:
    
    # Task 1: Run Forbes scraper (generates seed file)
    task1_forbes = PythonOperator(
        task_id='run_forbes_scraper',
        python_callable=run_forbes_scraper,
        execution_timeout=timedelta(minutes=30),
    )
    
    # Task 2: Run website scraper (reads seed, scrapes all sites)
    task2_websites = PythonOperator(
        task_id='run_website_scraper',
        python_callable=run_full_website_scraper,
        execution_timeout=timedelta(hours=2),
    )
    
    # Task 3: Upload everything to GCS
    task3_upload = PythonOperator(
        task_id='upload_to_gcs',
        python_callable=upload_all_to_gcs,
        execution_timeout=timedelta(minutes=30),
    )
    
    # Task 4: Generate final report
    task4_report = PythonOperator(
        task_id='generate_report',
        python_callable=generate_full_ingest_report,
    )
    
    # Execution order
    task1_forbes >> task2_websites >> task3_upload >> task4_report





# """
# DAG 1: AI50 Full Ingest - Fully Automated
# Scrapes Forbes → Generates Seed File → Scrapes Websites
# Schedule: @once (manual trigger)
# """

# from airflow import DAG
# from airflow.operators.python import PythonOperator
# from datetime import datetime, timedelta
# import json
# import logging
# from pathlib import Path
# import requests
# from bs4 import BeautifulSoup
# import time
# import re
# from google.cloud import storage

# # Configuration
# GCP_PROJECT_ID = 'orbit-ai50-intelligence'
# GCS_RAW_BUCKET = 'orbit-raw-data-group1-2025'
# GCS_PROCESSED_BUCKET = 'orbit-processed-data-group1-2025'

# # All 50 Forbes AI 50 companies (hardcoded)
# FORBES_AI50_COMPANIES = [
#     "Abridge", "Anthropic", "Anysphere", "Baseten", "Captions",
#     "Clay", "Coactive AI", "Cohere", "Crusoe", "Databricks",
#     "Decagon", "DeepL", "ElevenLabs", "Figure AI", "Fireworks AI",
#     "Glean", "Harvey", "Hebbia", "Hugging Face", "Lambda",
#     "LangChain", "Luminance", "Mercor", "Midjourney", "Mistral AI",
#     "Notion", "OpenAI", "OpenEvidence", "Perplexity AI", "Photoroom",
#     "Pika", "Runway", "Sakana AI", "SambaNova", "Scale AI",
#     "Sierra", "Skild AI", "Snorkel AI", "Speak", "StackBlitz",
#     "Suno", "Synthesia", "Thinking Machine Labs", "Together AI",
#     "Vannevar Labs", "VAST Data", "Windsurf", "World Labs", "Writer", "XAI"
# ]

# logger = logging.getLogger(__name__)

# default_args = {
#     'owner': 'orbit-team',
#     'depends_on_past': False,
#     'email_on_failure': False,
#     'retries': 2,
#     'retry_delay': timedelta(minutes=5),
# }


# def scrape_forbes_profiles(**context):
#     """Task 1: Scrape all 50 Forbes company profiles."""
#     logger.info("="*70)
#     logger.info("TASK 1: Scraping Forbes Profiles")
#     logger.info("="*70)
    
#     headers = {
#         'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36',
#         'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
#     }
    
#     all_profiles = []
    
#     for i, company_name in enumerate(FORBES_AI50_COMPANIES, 1):
#         logger.info(f"[{i}/{len(FORBES_AI50_COMPANIES)}] {company_name}")
        
#         try:
#             # Build Forbes URL
#             slug = company_name.lower().replace(' ', '-').replace('.', '')
#             slug = re.sub(r'[^a-z0-9-]', '', slug)
#             url = f"https://www.forbes.com/companies/{slug}/?list=ai50"
            
#             logger.info(f"  Forbes URL: {url}")
            
#             # Scrape
#             response = requests.get(url, headers=headers, timeout=30)
            
#             if response.status_code == 404:
#                 logger.warning(f"  Profile not found (404)")
#                 all_profiles.append({
#                     'company_name': company_name,
#                     'website': 'Not available',
#                     'forbes_url': url,
#                 })
#                 continue
            
#             response.raise_for_status()
#             soup = BeautifulSoup(response.text, 'html.parser')
#             text = soup.get_text()
            
#             # Extract data
#             profile = {
#                 'company_name': company_name,
#                 'forbes_url': url,
#                 'ceo': extract_ceo(soup, text),
#                 'founded_year': extract_founded(text),
#                 'hq_city': extract_hq_city(text),
#                 'hq_country': extract_hq_country(text),
#                 'employees': extract_employees(text),
#                 'industry': extract_industry(text),
#                 'description': extract_description(soup),
#                 'website': infer_website(company_name),
#                 'linkedin': f"https://www.linkedin.com/company/{company_name.lower().replace(' ', '-')}/",
#                 'category': 'general_ai',
#             }
            
#             all_profiles.append(profile)
#             logger.info(f"  ✅ Scraped: CEO={profile['ceo']}, Website={profile['website']}")
            
#         except Exception as e:
#             logger.error(f"  Error: {e}")
#             all_profiles.append({
#                 'company_name': company_name,
#                 'website': 'Not available',
#             })
        
#         time.sleep(2)
    
#     # Save seed file
#     seed_path = Path('/home/airflow/gcs/data/forbes_ai50_seed.json')
#     seed_path.parent.mkdir(parents=True, exist_ok=True)
    
#     with open(seed_path, 'w') as f:
#         json.dump(all_profiles, f, indent=2)
    
#     logger.info(f"✅ Generated seed file with {len(all_profiles)} companies")
    
#     context['task_instance'].xcom_push(key='companies', value=all_profiles)
    
#     return len(all_profiles)


# def extract_ceo(soup, text):
#     """Extract CEO name."""
#     patterns = [
#         r'CEO\s+([A-Z][a-z]+\s+[A-Z][a-z]+)',
#         r'founded by\s+([A-Z][a-z]+\s+[A-Z][a-z]+)',
#     ]
#     for pattern in patterns:
#         match = re.search(pattern, text)
#         if match:
#             return match.group(1)
#     return "Not available"


# def extract_founded(text):
#     """Extract founded year."""
#     match = re.search(r'Founded\s+(\d{4})', text)
#     if match:
#         year = int(match.group(1))
#         if 1990 <= year <= 2025:
#             return year
#     return None


# def extract_hq_city(text):
#     """Extract HQ city."""
#     match = re.search(r'Headquarters\s+([A-Z][a-z]+(?:\s+[A-Z][a-z]+)?)', text)
#     if match:
#         return match.group(1)
#     return "Not available"


# def extract_hq_country(text):
#     """Extract HQ country."""
#     if 'United Kingdom' in text or 'UK' in text:
#         return 'United Kingdom'
#     elif 'Germany' in text:
#         return 'Germany'
#     elif 'France' in text:
#         return 'France'
#     elif 'Canada' in text:
#         return 'Canada'
#     elif 'Japan' in text:
#         return 'Japan'
#     return 'United States'


# def extract_employees(text):
#     """Extract employee count."""
#     match = re.search(r'Employees\s+(\d+)', text)
#     if match:
#         return int(match.group(1))
#     return None


# def extract_industry(text):
#     """Extract industry."""
#     match = re.search(r'Industry\s+([^\n]+)', text)
#     if match:
#         return match.group(1).strip()
#     return "AI Technology"


# def extract_description(soup):
#     """Extract description."""
#     paragraphs = soup.find_all('p')
#     for p in paragraphs:
#         text = p.get_text().strip()
#         if len(text) > 100:
#             return text[:500]
#     return "Not available"


# def infer_website(company_name):
#     """Infer website from company name."""
#     manual_websites = {
#         'Anysphere': 'https://www.cursor.com',
#         'Windsurf': 'https://codeium.com',
#         'Pika': 'https://pika.art',
#         'Hugging Face': 'https://huggingface.co',
#         'Mistral AI': 'https://mistral.ai',
#         'DeepL': 'https://www.deepl.com',
#         'ElevenLabs': 'https://elevenlabs.io',
#         'Scale AI': 'https://scale.com',
#         'Anthropic': 'https://www.anthropic.com',
#         'OpenAI': 'https://www.openai.com',
#         'Databricks': 'https://www.databricks.com',
#         'Cohere': 'https://cohere.com',
#         'XAI': 'https://x.ai',
#         'Midjourney': 'https://www.midjourney.com',
#         'Notion': 'https://www.notion.so',
#         'Perplexity AI': 'https://www.perplexity.ai',
#         'Together AI': 'https://www.together.ai',
#     }
    
#     if company_name in manual_websites:
#         return manual_websites[company_name]
    
#     slug = company_name.lower().replace(' ', '').replace('.', '')
#     return f"https://{slug}.com"


# def scrape_all_websites(**context):
#     """Task 2: Scrape all company websites using generated seed."""
#     logger.info("="*70)
#     logger.info("TASK 2: Scraping Company Websites")
#     logger.info("="*70)
    
#     companies = context['task_instance'].xcom_pull(key='companies', task_ids='scrape_forbes')
    
#     if not companies:
#         raise ValueError("No companies from Forbes scraping")
    
#     logger.info(f"Scraping websites for {len(companies)} companies")
    
#     raw_dir = Path('/home/airflow/gcs/data/raw')
#     raw_dir.mkdir(parents=True, exist_ok=True)
    
#     session_name = f"{datetime.now().strftime('%Y-%m-%d')}_initial"
    
#     headers = {
#         'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36',
#     }
    
#     page_patterns = {
#         'homepage': ['/', ''],
#         'about': ['/about', '/about-us', '/company'],
#         'pricing': ['/pricing', '/plans'],
#         'product': ['/product', '/products', '/platform'],
#         'careers': ['/careers', '/jobs'],
#         'blog': ['/blog', '/news', '/newsroom'],
#         'customers': ['/customers', '/case-studies'],
#     }
    
#     successful = 0
#     total_pages = 0
    
#     for i, company in enumerate(companies, 1):
#         company_name = company['company_name']
#         website = company.get('website', 'Not available')
        
#         logger.info(f"[{i}/{len(companies)}] {company_name}")
        
#         if not website or website == 'Not available':
#             logger.warning(f"  No website")
#             continue
        
#         company_dir = raw_dir / company_name.replace(' ', '_').replace('/', '_')
#         session_dir = company_dir / session_name
#         session_dir.mkdir(parents=True, exist_ok=True)
        
#         pages_found = 0
        
#         # Scrape each page type
#         for page_type, patterns in page_patterns.items():
#             try:
#                 page_url = None
                
#                 if page_type == 'homepage':
#                     page_url = website
#                 else:
#                     for pattern in patterns:
#                         test_url = website.rstrip('/') + pattern
#                         try:
#                             resp = requests.head(test_url, headers=headers, timeout=10, allow_redirects=True)
#                             if resp.status_code == 200:
#                                 page_url = test_url
#                                 break
#                         except:
#                             continue
                
#                 if not page_url:
#                     continue
                
#                 logger.info(f"  {page_type}: {page_url}")
#                 response = requests.get(page_url, headers=headers, timeout=30, allow_redirects=True)
                
#                 if response.status_code == 200:
#                     html = response.text
#                     soup = BeautifulSoup(html, 'html.parser')
                    
#                     for tag in soup(["script", "style"]):
#                         tag.decompose()
                    
#                     text = soup.get_text()
                    
#                     (session_dir / f"{page_type}.html").write_text(html, encoding='utf-8')
#                     (session_dir / f"{page_type}.txt").write_text(text, encoding='utf-8')
                    
#                     pages_found += 1
#                     total_pages += 1
                    
#                     logger.info(f"    ✅ Saved")
                
#                 time.sleep(2)
                
#             except Exception as e:
#                 logger.error(f"  Error: {e}")
        
#         if pages_found > 0:
#             successful += 1
        
#         time.sleep(3)
    
#     summary = {
#         'total_companies': len(companies),
#         'successful': successful,
#         'total_pages': total_pages,
#     }
    
#     logger.info(f"✅ Websites: {successful}/{len(companies)} companies, {total_pages} pages")
    
#     context['task_instance'].xcom_push(key='website_summary', value=summary)
    
#     return summary


# def upload_to_gcs(**context):
#     """Task 3: Upload all data to GCS."""
#     logger.info("Uploading to GCS")
    
#     client = storage.Client(project=GCP_PROJECT_ID)
#     bucket = client.bucket(GCS_RAW_BUCKET)
    
#     # Upload seed file
#     seed_path = Path('/home/airflow/gcs/data/forbes_ai50_seed.json')
#     if seed_path.exists():
#         blob = bucket.blob('data/forbes_ai50_seed.json')
#         blob.upload_from_filename(str(seed_path))
#         logger.info("✅ Uploaded seed file")
    
#     # Upload raw data
#     data_dir = Path('/home/airflow/gcs/data/raw')
#     upload_count = 0
    
#     if data_dir.exists():
#         for file_path in data_dir.rglob('*'):
#             if file_path.is_file():
#                 try:
#                     relative = file_path.relative_to(data_dir.parent)
#                     blob_name = str(relative)
                    
#                     blob = bucket.blob(blob_name)
#                     blob.upload_from_filename(str(file_path))
#                     upload_count += 1
                    
#                 except Exception as e:
#                     logger.error(f"Error uploading {file_path}: {e}")
    
#     logger.info(f"✅ Uploaded {upload_count} files")
    
#     return upload_count


# def generate_report(**context):
#     """Task 4: Generate final report."""
#     forbes_count = context['task_instance'].xcom_pull(task_ids='scrape_forbes')
#     website_summary = context['task_instance'].xcom_pull(key='website_summary', task_ids='scrape_websites')
#     uploaded = context['task_instance'].xcom_pull(task_ids='upload_to_gcs')
    
#     report = {
#         'dag_id': 'ai50_full_ingest_dag',
#         'execution_date': context['execution_date'].isoformat(),
#         'forbes_companies_scraped': forbes_count,
#         'website_companies_scraped': website_summary.get('successful', 0) if website_summary else 0,
#         'total_pages_scraped': website_summary.get('total_pages', 0) if website_summary else 0,
#         'files_uploaded': uploaded,
#         'status': 'SUCCESS',
#         'completed_at': datetime.now().isoformat(),
#     }
    
#     # Save to GCS
#     client = storage.Client(project=GCP_PROJECT_ID)
#     bucket = client.bucket(GCS_PROCESSED_BUCKET)
    
#     report_name = f"reports/full_ingest_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
#     blob = bucket.blob(report_name)
#     blob.upload_from_string(json.dumps(report, indent=2))
    
#     logger.info(f"✅ Report: gs://{GCS_PROCESSED_BUCKET}/{report_name}")
#     logger.info(f"  Forbes companies: {report['forbes_companies_scraped']}")
#     logger.info(f"  Websites scraped: {report['website_companies_scraped']}")
#     logger.info(f"  Total pages: {report['total_pages_scraped']}")
    
#     return report


# # Define DAG
# with DAG(
#     'ai50_full_ingest_dag',
#     default_args=default_args,
#     description='Lab 2: Full automated ingestion - Forbes + Websites',
#     schedule_interval='@once',
#     start_date=datetime(2025, 11, 3),
#     catchup=False,
#     tags=['orbit', 'lab2', 'full-load', 'manual'],
# ) as dag:
    
#     task_forbes = PythonOperator(
#         task_id='scrape_forbes',
#         python_callable=scrape_forbes_profiles,
#         execution_timeout=timedelta(minutes=30),
#     )
    
#     task_websites = PythonOperator(
#         task_id='scrape_websites',
#         python_callable=scrape_all_websites,
#         execution_timeout=timedelta(hours=3),
#     )
    
#     task_upload = PythonOperator(
#         task_id='upload_to_gcs',
#         python_callable=upload_to_gcs,
#     )
    
#     task_report = PythonOperator(
#         task_id='generate_report',
#         python_callable=generate_report,
#     )
    
#     task_forbes >> task_websites >> task_upload >> task_report





# """
# DAG 1: AI50 Full Initial Ingest - ONE-TIME LOAD
# Orchestrates: forbes_scraper.py → scraper_robust.py → GCS Upload
# Schedule: @once (manual trigger only)

# DEPLOYMENT:
# 1. Upload this file: gsutil cp ai50_full_ingest_dag.py gs://us-central1-orbit-airflow-e-2044600e-bucket/dags/
# 2. Upload scrapers: gsutil cp forbes_scraper.py scraper_robust.py gs://us-central1-orbit-airflow-e-2044600e-bucket/dags/
# 3. Wait 2-3 minutes
# 4. Trigger DAG in Airflow UI
# """
# """
# DAG 1: AI50 Full Initial Ingest - ONE-TIME LOAD
# Orchestrates: forbes_scraper.py → scraper_robust.py → GCS Upload
# Schedule: @once (manual trigger only)

# DEPLOYMENT:
# 1. Upload this file: gsutil cp ai50_full_ingest_dag.py gs://us-central1-orbit-airflow-e-2044600e-bucket/dags/
# 2. Upload scrapers: gsutil cp forbes_scraper.py scraper_robust.py gs://us-central1-orbit-airflow-e-2044600e-bucket/dags/
# 3. Wait 2-3 minutes
# 4. Trigger DAG in Airflow UI
# """

# from airflow import DAG
# from airflow.operators.python import PythonOperator
# from datetime import datetime, timedelta
# import subprocess
# import json
# import logging
# from pathlib import Path
# from google.cloud import storage

# logger = logging.getLogger(__name__)

# # Configuration
# GCP_PROJECT_ID = 'orbit-ai50-intelligence'
# GCS_RAW_BUCKET = 'orbit-raw-data-group1-2025'
# GCS_PROCESSED_BUCKET = 'orbit-processed-data-group1-2025'

# default_args = {
#     'owner': 'orbit-team',
#     'depends_on_past': False,
#     'email_on_failure': False,
#     'retries': 1,
#     'retry_delay': timedelta(minutes=5),
# }


# def run_forbes_scraper(**context):
#     """Task 1: Run forbes_scraper.py to generate seed file."""
#     logger.info("="*70)
#     logger.info("TASK 1: Running Forbes Scraper")
#     logger.info("="*70)
    
#     scraper_path = Path('/home/airflow/gcs/dags/forbes_scraper.py')
    
#     try:
#         # Run the script
#         result = subprocess.run(
#             ['python3', str(scraper_path)],
#             capture_output=True,
#             text=True,
#             timeout=1800  # 30 minutes max
#         )
        
#         logger.info(f"Forbes scraper output:\n{result.stdout}")
        
#         if result.returncode != 0:
#             logger.error(f"Forbes scraper failed:\n{result.stderr}")
#             raise Exception(f"Forbes scraper failed with code {result.returncode}")
        
#         # Check seed file
#         seed_file = Path('/home/airflow/gcs/data/forbes_ai50_seed.json')
#         if not seed_file.exists():
#             raise Exception("Seed file not created!")
        
#         with open(seed_file, 'r') as f:
#             companies = json.load(f)
        
#         logger.info(f"✅ Forbes scraper completed: {len(companies)} companies")
        
#         context['task_instance'].xcom_push(key='seed_file', value=str(seed_file))
#         context['task_instance'].xcom_push(key='company_count', value=len(companies))
        
#         return len(companies)
    
#     except Exception as e:
#         logger.error(f"Error running Forbes scraper: {e}")
#         raise


# def run_full_website_scraper(**context):
#     """Task 2: Run scraper_robust.py to scrape ALL pages."""
#     logger.info("="*70)
#     logger.info("TASK 2: Running Full Website Scraper")
#     logger.info("="*70)
    
#     scraper_path = Path('/home/airflow/gcs/dags/scraper_robust.py')
    
#     try:
#         # Run the script
#         result = subprocess.run(
#             ['python3', str(scraper_path)],
#             input='n\n',  # Answer 'n' to "test with 5 companies"
#             capture_output=True,
#             text=True,
#             timeout=7200  # 2 hours max
#         )
        
#         logger.info(f"Website scraper output:\n{result.stdout}")
        
#         if result.returncode != 0:
#             logger.error(f"Website scraper failed:\n{result.stderr}")
#             raise Exception(f"Website scraper failed with code {result.returncode}")
        
#         logger.info("✅ Full website scraping completed")
#         return "success"
    
#     except Exception as e:
#         logger.error(f"Error running website scraper: {e}")
#         raise


# def upload_all_to_gcs(**context):
#     """Task 3: Upload ALL scraped data to GCS (RAW + PROCESSED buckets)."""
#     logger.info("="*70)
#     logger.info("TASK 3: Uploading to GCS")
#     logger.info("="*70)
    
#     client = storage.Client(project=GCP_PROJECT_ID)
#     raw_bucket = client.bucket(GCS_RAW_BUCKET)
#     processed_bucket = client.bucket(GCS_PROCESSED_BUCKET)
    
#     upload_count = 0
    
#     # Upload seed file to BOTH raw and processed buckets
#     seed_file = Path('/home/airflow/gcs/data/forbes_ai50_seed.json')
#     if seed_file.exists():
#         # Upload to RAW bucket
#         blob_raw = raw_bucket.blob('data/forbes_ai50_seed.json')
#         blob_raw.upload_from_filename(str(seed_file))
#         upload_count += 1
#         logger.info("✅ Uploaded seed file to RAW bucket")
        
#         # Upload to PROCESSED bucket
#         blob_processed = processed_bucket.blob('data/forbes_ai50_seed.json')
#         blob_processed.upload_from_filename(str(seed_file))
#         upload_count += 1
#         logger.info("✅ Uploaded seed file to PROCESSED bucket")
    
#     # Upload all raw data to RAW bucket
#     raw_dir = Path('/home/airflow/gcs/data/raw')
#     if raw_dir.exists():
#         for file_path in raw_dir.rglob('*'):
#             if file_path.is_file():
#                 try:
#                     relative = file_path.relative_to(Path('/home/airflow/gcs/data'))
#                     blob_name = f"data/{relative}"
                    
#                     blob = raw_bucket.blob(blob_name)
#                     blob.upload_from_filename(str(file_path))
#                     upload_count += 1
                    
#                     if upload_count % 100 == 0:
#                         logger.info(f"  Uploaded {upload_count} files...")
                    
#                 except Exception as e:
#                     logger.error(f"Error uploading {file_path}: {e}")
    
#     logger.info(f"✅ Uploaded {upload_count} files total")
#     logger.info(f"   RAW bucket: gs://{GCS_RAW_BUCKET}/")
#     logger.info(f"   PROCESSED bucket: gs://{GCS_PROCESSED_BUCKET}/data/forbes_ai50_seed.json")
    
#     context['task_instance'].xcom_push(key='files_uploaded', value=upload_count)
#     return upload_count


# def generate_full_ingest_report(**context):
#     """Task 4: Generate comprehensive report."""
#     logger.info("="*70)
#     logger.info("TASK 4: Generating Report")
#     logger.info("="*70)
    
#     company_count = context['task_instance'].xcom_pull(
#         key='company_count',
#         task_ids='run_forbes_scraper'
#     )
    
#     files_uploaded = context['task_instance'].xcom_pull(
#         key='files_uploaded',
#         task_ids='upload_to_gcs'
#     )
    
#     report = {
#         'dag_id': 'ai50_full_ingest_dag',
#         'execution_date': context['execution_date'].isoformat(),
#         'status': 'SUCCESS',
#         'companies_scraped': company_count,
#         'files_uploaded': files_uploaded,
#         'scraping_completed_at': datetime.now().isoformat(),
#         'data_location': f"gs://{GCS_RAW_BUCKET}/data/",
#     }
    
#     # Save report to GCS
#     client = storage.Client(project=GCP_PROJECT_ID)
#     bucket = client.bucket(GCS_PROCESSED_BUCKET)
    
#     report_name = f"reports/full_ingest_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
#     blob = bucket.blob(report_name)
#     blob.upload_from_string(json.dumps(report, indent=2))
    
#     logger.info(f"✅ Report saved: gs://{GCS_PROCESSED_BUCKET}/{report_name}")
#     logger.info(f"   Companies: {company_count}")
#     logger.info(f"   Files uploaded: {files_uploaded}")
    
#     return report


# # Define DAG
# with DAG(
#     dag_id='ai50_full_ingest_dag',
#     default_args=default_args,
#     description='Lab 2: Full initial load - Forbes scraper → Website scraper → GCS',
#     schedule_interval='@once',  # Manual trigger only
#     start_date=datetime(2025, 11, 3),
#     catchup=False,
#     tags=['orbit', 'lab2', 'full-load', 'initial', 'manual'],
# ) as dag:
    
#     # Task 1: Run Forbes scraper
#     task1_forbes = PythonOperator(
#         task_id='run_forbes_scraper',
#         python_callable=run_forbes_scraper,
#         execution_timeout=timedelta(minutes=30),
#     )
    
#     # Task 2: Run website scraper
#     task2_websites = PythonOperator(
#         task_id='run_website_scraper',
#         python_callable=run_full_website_scraper,
#         execution_timeout=timedelta(hours=2),
#     )
    
#     # Task 3: Upload to GCS
#     task3_upload = PythonOperator(
#         task_id='upload_to_gcs',
#         python_callable=upload_all_to_gcs,
#         execution_timeout=timedelta(minutes=30),
#     )
    
#     # Task 4: Generate report
#     task4_report = PythonOperator(
#         task_id='generate_report',
#         python_callable=generate_full_ingest_report,
#     )
    
#     # Execution order
#     task1_forbes >> task2_websites >> task3_upload >> task4_report






















































































