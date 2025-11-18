"""
ORBIT Structured Pipeline Daily Update (TAPAS ONLY)
Runs ONLY structured extraction + structured dashboards
Author: Tapas (November 2025)

Usage:
    python src/scheduler/scheduler_structured_only.py --test    # Test now
    python src/scheduler/scheduler_structured_only.py           # Run at 4 AM UTC
"""
from apscheduler.schedulers.blocking import BlockingScheduler
from google.cloud import storage
from datetime import datetime, timedelta, timezone
import subprocess
import logging
import sys
import os
import json
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

# Project Configuration
PROJECT_ROOT = Path(__file__).resolve().parents[2]
GCP_PROJECT_ID = os.getenv("GCP_PROJECT_ID", "orbit-ai50-intelligence-477922")
RAW_BUCKET = os.getenv("GCS_RAW_BUCKET", "orbit-raw-data-g1-2025")
PROCESSED_BUCKET = os.getenv("GCS_PROCESSED_BUCKET", "orbit-processed-data-g1-2025")

# Logging Setup
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(PROJECT_ROOT / 'scheduler_structured.log', encoding='utf-8'),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)


def check_daily_data_exists():
    """Check if daily scrape data exists in GCS."""
    logger.info("Checking for daily data in GCS...")
    
    try:
        client = storage.Client(project=GCP_PROJECT_ID)
        bucket = client.bucket(RAW_BUCKET)
        
        daily_prefix = "data/raw/"
        blobs = bucket.list_blobs(prefix=daily_prefix)
        
        companies_with_daily = set()
        today = datetime.now(timezone.utc).strftime('%Y-%m-%d')
        yesterday = (datetime.now(timezone.utc) - timedelta(days=1)).strftime('%Y-%m-%d')
        
        for blob in blobs:
            parts = blob.name.split('/')
            if len(parts) >= 4 and '_daily' in parts[3]:
                session_date = parts[3].split('_')[0]
                
                # Accept data from last 24 hours
                if session_date >= yesterday:
                    company = parts[2]
                    companies_with_daily.add(company)
        
        if companies_with_daily:
            logger.info(f"Found daily data for {len(companies_with_daily)} companies")
            return True, sorted(list(companies_with_daily))
        else:
            logger.warning("No daily data found")
            return False, []
    
    except Exception as e:
        logger.error(f"Error checking GCS: {e}")
        return False, []


def run_task(name, command, timeout=3600):
    """Run a single task with timeout and logging."""
    logger.info(f"\n{'='*70}")
    logger.info(f"TASK: {name}")
    logger.info(f"Command: {' '.join(command)}")
    logger.info(f"{'='*70}")
    
    start_time = datetime.now()
    
    try:
        env = os.environ.copy()
        env.update({
            'GCP_PROJECT_ID': GCP_PROJECT_ID,
            'GCS_RAW_BUCKET': RAW_BUCKET,
            'GCS_PROCESSED_BUCKET': PROCESSED_BUCKET,
            'GCP_BUCKET_NAME': RAW_BUCKET,
            'PYTHONIOENCODING': 'utf-8'
        })
        
        result = subprocess.run(
        command,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        timeout=timeout,
        cwd=str(PROJECT_ROOT)
    )
        
        duration = (datetime.now() - start_time).total_seconds()
        
        if result.returncode == 0:
            logger.info(f"SUCCESS: {name} ({duration:.1f}s)")
            logger.info(f"Output preview: {result.stdout[:200]}")
            return True, duration, None
        else:
            error = result.stderr[-500:] if result.stderr else "Unknown error"
            logger.error(f"FAILED: {name}")
            logger.error(f"Error: {error}")
            return False, duration, error
    
    except subprocess.TimeoutExpired:
        duration = timeout
        logger.error(f"TIMEOUT: {name} exceeded {timeout}s")
        return False, duration, f"Timeout after {timeout}s"
    
    except Exception as e:
        duration = (datetime.now() - start_time).total_seconds()
        logger.error(f"ERROR: {name} - {e}")
        return False, duration, str(e)


def run_structured_pipeline():
    """
    STRUCTURED PIPELINE ONLY (Tapas's Work)
    Extract → Generate Dashboards
    """
    logger.info("\n" + "="*70)
    logger.info("ORBIT STRUCTURED PIPELINE - DAILY UPDATE")
    logger.info("="*70)
    logger.info(f"Time: {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S')} UTC")
    logger.info(f"Project: {GCP_PROJECT_ID}")
    logger.info(f"Raw Bucket: {RAW_BUCKET}")
    logger.info(f"Processed Bucket: {PROCESSED_BUCKET}")
    logger.info("="*70)
    
    pipeline_start = datetime.now()
    
    # Step 0: Verify daily data exists
    has_daily, companies = check_daily_data_exists()
    
    if not has_daily:
        logger.warning("No daily data found - skipping pipeline")
        return {
            'status': 'skipped',
            'reason': 'No daily data available',
            'timestamp': datetime.now(timezone.utc).isoformat()
        }
    
    logger.info(f"Companies with new data: {', '.join(companies[:10])}")
    if len(companies) > 10:
        logger.info(f"   ... and {len(companies) - 10} more")
    
    # ONLY YOUR TASKS (Lab 5 + Lab 8)
    tasks = [
        {
            'name': 'Lab 5: Extract Structured Data from GCS',
            'command': ['python', 'src/structured/structured_extract_gcp.py', '--all'],
            'timeout': 7200,  # 120 min (increased for 42 companies)
            'critical': True
        },
        {
            'name': 'Lab 8: Generate Structured Dashboards',
            'command': ['python', 'src/structured/generate_all_dashboard.py'],
            'timeout': 3600,  # 60 min
            'critical': False
        }
    ]
    
    # Run pipeline
    results = {
        'started_at': pipeline_start.isoformat(),
        'pipeline_type': 'STRUCTURED_ONLY',
        'bucket': RAW_BUCKET,
        'companies_updated': len(companies),
        'tasks': []
    }
    
    for i, task in enumerate(tasks, 1):
        logger.info(f"\n{'#'*70}")
        logger.info(f"STEP {i}/{len(tasks)}: {task['name']}")
        logger.info(f"{'#'*70}")
        
        success, duration, error = run_task(
            name=task['name'],
            command=task['command'],
            timeout=task['timeout']
        )
        
        results['tasks'].append({
            'name': task['name'],
            'success': success,
            'duration_seconds': duration,
            'error': error
        })
        
        # Stop if critical task fails
        if not success and task.get('critical'):
            logger.error("Critical task failed - stopping pipeline")
            break
    
    # Calculate summary
    pipeline_duration = (datetime.now() - pipeline_start).total_seconds()
    successful = sum(1 for t in results['tasks'] if t['success'])
    failed = len(results['tasks']) - successful
    
    results['completed_at'] = datetime.now().isoformat()
    results['total_duration_seconds'] = pipeline_duration
    results['successful_tasks'] = successful
    results['failed_tasks'] = failed
    results['status'] = 'completed' if failed == 0 else 'partial'
    
    # Log summary
    logger.info("\n" + "="*70)
    logger.info("STRUCTURED PIPELINE SUMMARY")
    logger.info("="*70)
    logger.info(f"Status: {results['status'].upper()}")
    logger.info(f"Duration: {pipeline_duration/60:.1f} minutes")
    logger.info(f"Successful: {successful}/{len(tasks)} tasks")
    logger.info(f"Failed: {failed} tasks")
    logger.info(f"Companies updated: {len(companies)}")
    
    # Save results
    results_file = PROJECT_ROOT / "data" / f"structured_update_{datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')}.json"
    results_file.parent.mkdir(exist_ok=True, parents=True)
    
    with open(results_file, 'w', encoding='utf-8') as f:
        json.dump(results, f, indent=2)
    
    logger.info(f"\nResults saved: {results_file.name}")
    logger.info("="*70)
    logger.info("PIPELINE COMPLETE")
    logger.info("="*70 + "\n")
    
    return results


def main():
    """Main entry point"""
    
    # Check for test/immediate mode
    if '--test' in sys.argv or '--now' in sys.argv:
        logger.info("TEST MODE - Running immediately")
        run_structured_pipeline()
        return
    
    # Production mode - schedule for 4 AM UTC daily
    scheduler = BlockingScheduler(timezone='UTC')
    
    scheduler.add_job(
        run_structured_pipeline,
        'cron',
        hour=4,
        minute=0,
        id='orbit_structured_update',
        name='ORBIT Structured Pipeline Update',
        timezone='UTC'
    )
    
    logger.info("\n" + "="*70)
    logger.info("ORBIT STRUCTURED PIPELINE SCHEDULER")
    logger.info("="*70)
    logger.info(f"Schedule: Daily at 4:00 AM UTC")
    logger.info(f"Project: {GCP_PROJECT_ID}")
    logger.info(f"Raw Bucket: {RAW_BUCKET}")
    logger.info("")
    logger.info("Pipeline Steps (STRUCTURED ONLY):")
    logger.info("  1. Check for new daily data in GCS")
    logger.info("  2. Extract structured data (Lab 5)")
    logger.info("  3. Generate structured dashboards (Lab 8)")
    logger.info("")
    logger.info("Note: RAG pipeline (Lab 4 + 7) runs separately by teammate")
    logger.info("")
    logger.info(f"Log file: scheduler_structured.log")
    logger.info("Press Ctrl+C to stop")
    logger.info("="*70 + "\n")
    
    try:
        scheduler.start()
    except KeyboardInterrupt:
        logger.info("\nScheduler stopped by user")


if __name__ == "__main__":
    main()