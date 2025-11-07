# """
# Daily Update Scheduler for ORBIT
# Runs post-processing after GCP Airflow scraping completes
# Author: Tapas
# """
# from apscheduler.schedulers.blocking import BlockingScheduler
# from datetime import datetime
# import subprocess
# from pathlib import Path
# import logging
# import time
# import sys
# import os

# # Fix Windows console encoding
# os.environ['PYTHONIOENCODING'] = 'utf-8'

# # Configure logging WITHOUT emojis for Windows compatibility
# logging.basicConfig(
#     level=logging.INFO,
#     format='%(asctime)s - %(levelname)s - %(message)s',
#     handlers=[
#         logging.FileHandler('scheduler.log', encoding='utf-8'),
#         logging.StreamHandler(sys.stdout)
#     ]
# )
# logger = logging.getLogger(__name__)

# project_root = Path(__file__).resolve().parents[2]


# def run_post_processing():
#     """
#     Run post-processing after GCP Airflow scraping.
    
#     Steps:
#     1. Extract structured data from GCS
#     2. Rebuild vector index from GCS (skipped - needs sentence_transformers)
#     3. Regenerate dashboards (skipped - depends on vector index)
#     """
#     logger.info("="*70)
#     logger.info(f"STARTING POST-PROCESSING - {datetime.now()}")
#     logger.info("="*70)
    
#     # Define tasks (ONLY structured extraction for now)
#     tasks = [
#         {
#             'name': 'Extracting Structured Data',
#             'command': ["python", "src/structured/structured_extract_gcp.py", "--all"],
#             'timeout': 1800,
#             'critical': True  # Must succeed
#         },
#         # NOTE: Vector index and dashboard generation require sentence_transformers
#         # which is only installed in Docker. Run those in Docker instead:
#         # docker exec -it orbit-api python src/vectordb/build_index.py --gcs --no-clear
#         # docker exec -it orbit-api python src/dashboard/generate_dashboards.py
#     ]
    
#     results = {
#         'started_at': datetime.now().isoformat(),
#         'completed_tasks': 0,
#         'failed_tasks': 0,
#         'task_results': []
#     }
    
#     # Run each task sequentially
#     for i, task in enumerate(tasks, 1):
#         logger.info(f"\n[{i}/{len(tasks)}] {task['name']}...")
#         logger.info("-" * 70)
        
#         task_start = time.time()
        
#         try:
#             result = subprocess.run(
#                 task['command'],
#                 cwd=str(project_root),
#                 capture_output=True,
#                 text=True,
#                 timeout=task['timeout'],
#                 env={**os.environ, 'PYTHONIOENCODING': 'utf-8'}  # Fix encoding
#             )
            
#             task_elapsed = time.time() - task_start
            
#             if result.returncode == 0:
#                 logger.info(f"SUCCESS: {task['name']} completed ({task_elapsed:.1f}s)")
#                 results['completed_tasks'] += 1
#                 results['task_results'].append({
#                     'task': task['name'],
#                     'status': 'success',
#                     'duration_seconds': task_elapsed
#                 })
#             else:
#                 logger.error(f"FAILED: {task['name']}")
#                 logger.error(f"Error output: {result.stderr[:500]}")
#                 results['failed_tasks'] += 1
#                 results['task_results'].append({
#                     'task': task['name'],
#                     'status': 'failed',
#                     'error': result.stderr[:500],
#                     'duration_seconds': task_elapsed
#                 })
                
#                 # Stop if critical task fails
#                 if task.get('critical'):
#                     logger.error("CRITICAL TASK FAILED - Stopping post-processing")
#                     break
        
#         except subprocess.TimeoutExpired:
#             logger.error(f"TIMEOUT: {task['name']} exceeded {task['timeout']}s")
#             results['failed_tasks'] += 1
#             results['task_results'].append({
#                 'task': task['name'],
#                 'status': 'timeout',
#                 'timeout_seconds': task['timeout']
#             })
        
#         except Exception as e:
#             logger.error(f"ERROR: {task['name']} - {e}")
#             results['failed_tasks'] += 1
#             results['task_results'].append({
#                 'task': task['name'],
#                 'status': 'error',
#                 'error': str(e)
#             })
    
#     # Run Docker tasks if structured extraction succeeded
#     if results['completed_tasks'] > 0:
#         logger.info("\n" + "="*70)
#         logger.info("RUNNING DOCKER TASKS")
#         logger.info("="*70)
        
#         docker_tasks = [
#             {
#                 'name': 'Vector Index (Docker)',
#                 'command': ['docker', 'exec', 'orbit-api', 'bash', '-c', 
#                            'cd /app/src/vectordb && python build_index.py --gcs --no-clear']
#             },
#             {
#                 'name': 'Generate Dashboards (Docker)',
#                 'command': ['docker', 'exec', 'orbit-api', 'python', 
#                            'src/dashboard/generate_dashboards.py']
#             }
#         ]
        
#         for task in docker_tasks:
#             logger.info(f"\nRunning: {task['name']}...")
#             try:
#                 result = subprocess.run(
#                     task['command'],
#                     capture_output=True,
#                     text=True,
#                     timeout=1800
#                 )
                
#                 if result.returncode == 0:
#                     logger.info(f"SUCCESS: {task['name']}")
#                     results['completed_tasks'] += 1
#                 else:
#                     logger.error(f"FAILED: {task['name']}")
#                     logger.error(result.stderr[:500])
#                     results['failed_tasks'] += 1
            
#             except Exception as e:
#                 logger.error(f"ERROR: {task['name']} - {e}")
#                 results['failed_tasks'] += 1
    
#     # Summary
#     results['completed_at'] = datetime.now().isoformat()
#     results['total_duration_seconds'] = time.time() - time.mktime(
#         datetime.fromisoformat(results['started_at']).timetuple()
#     )
    
#     logger.info("\n" + "="*70)
#     logger.info("POST-PROCESSING SUMMARY")
#     logger.info("="*70)
#     logger.info(f"Completed: {results['completed_tasks']} tasks")
#     logger.info(f"Failed: {results['failed_tasks']} tasks")
#     logger.info(f"Total time: {results['total_duration_seconds']:.1f}s")
    
#     # Save results
#     import json
#     results_file = project_root / "data" / f"update_results_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
#     results_file.parent.mkdir(exist_ok=True)
    
#     with open(results_file, 'w', encoding='utf-8') as f:
#         json.dump(results, f, indent=2)
    
#     logger.info(f"Results saved: {results_file}")
    
#     # Notify if failures
#     if results['failed_tasks'] > 0:
#         logger.warning(f"WARNING: {results['failed_tasks']} tasks failed - check logs!")
    
#     logger.info("="*70)
    
#     return results


# def test_run():
#     """Test post-processing workflow (run immediately)"""
#     logger.info("TEST RUN - Running post-processing now...")
#     result = run_post_processing()
#     return result


# def main():
#     """Main scheduler - runs daily at 4 AM (1 hour after GCP Airflow)"""
    
#     # Check for test mode
#     if '--test' in sys.argv:
#         logger.info("Running in TEST mode (immediate execution)")
#         test_run()
#         return
    
#     if '--once' in sys.argv:
#         logger.info("Running ONCE (immediate execution, then exit)")
#         test_run()
#         return
    
#     # Production mode - scheduled
#     scheduler = BlockingScheduler()
    
#     # Schedule daily at 4 AM (1 hour after GCP Airflow finishes scraping)
#     scheduler.add_job(
#         run_post_processing,
#         'cron',
#         hour=4,
#         minute=0,
#         id='daily_post_processing',
#         name='ORBIT Daily Post-Processing'
#     )
    
#     logger.info("="*70)
#     logger.info("ORBIT DAILY UPDATE SCHEDULER")
#     logger.info("="*70)
#     logger.info("Schedule: Daily at 4:00 AM")
#     logger.info("Tasks:")
#     logger.info("   1. Extract structured data from GCS")
#     logger.info("   2. Rebuild vector index (Docker)")
#     logger.info("   3. Regenerate dashboards (Docker)")
#     logger.info("")
#     logger.info("Note: Assumes GCP Airflow scraping completes by 4 AM")
#     logger.info("Logs: scheduler.log")
#     logger.info("")
#     logger.info("Press Ctrl+C to stop")
#     logger.info("="*70)
    
#     try:
#         scheduler.start()
#     except KeyboardInterrupt:
#         logger.info("\nScheduler stopped")


# if __name__ == "__main__":
#     main()

"""
Daily Update Scheduler for ORBIT
Runs post-processing after GCP Airflow scraping completes
Downloads Airflow reports and updates app data
Author: Tapas
"""
from apscheduler.schedulers.blocking import BlockingScheduler
from datetime import datetime
import subprocess
from pathlib import Path
import logging
import time
import sys
import os

# Fix Windows console encoding
os.environ['PYTHONIOENCODING'] = 'utf-8'
if sys.platform == 'win32':
    os.environ['PYTHONUTF8'] = '1'

# Configure logging WITHOUT emojis for Windows
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('scheduler.log', encoding='utf-8'),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)

project_root = Path(__file__).resolve().parents[2]


def download_airflow_reports():
    """Download latest Airflow reports from GCS"""
    logger.info("="*70)
    logger.info("STEP 1: DOWNLOADING AIRFLOW REPORTS")
    logger.info("="*70)
    
    try:
        from google.cloud import storage
        import json
        from dotenv import load_dotenv
        
        load_dotenv()
        
        bucket_name = os.getenv('GCS_PROCESSED_BUCKET', 'orbit-processed-data-group1-2025')
        
        logger.info(f"Connecting to gs://{bucket_name}...")
        client = storage.Client()
        bucket = client.bucket(bucket_name)
        
        # Create reports directory
        reports_dir = project_root / "data" / "airflow_reports"
        reports_dir.mkdir(parents=True, exist_ok=True)
        
        # Get all reports
        logger.info("Fetching report list...")
        blobs = list(bucket.list_blobs(prefix='reports/'))
        
        if not blobs:
            logger.warning("No reports found in GCS!")
            return False
        
        # Separate by type
        ingest_reports = [b for b in blobs if 'full_ingest' in b.name]
        daily_reports = [b for b in blobs if 'daily_refresh' in b.name]
        
        logger.info(f"Found {len(ingest_reports)} ingest reports")
        logger.info(f"Found {len(daily_reports)} daily refresh reports")
        
        # Download latest ingest report
        if ingest_reports:
            latest_ingest = max(ingest_reports, key=lambda b: b.time_created)
            local_path = reports_dir / "latest_full_ingest.json"
            latest_ingest.download_to_filename(str(local_path))
            
            with open(local_path, 'r') as f:
                data = json.load(f)
            
            logger.info(f"\nLatest Ingest Report:")
            logger.info(f"  File: {latest_ingest.name}")
            logger.info(f"  Created: {latest_ingest.time_created}")
            logger.info(f"  Companies: {data.get('companies_scraped', 'N/A')}")
            logger.info(f"  Files uploaded: {data.get('files_uploaded', 'N/A')}")
            logger.info(f"  Saved to: {local_path}")
        
        # Download latest daily refresh report
        if daily_reports:
            latest_daily = max(daily_reports, key=lambda b: b.time_created)
            local_path = reports_dir / "latest_daily_refresh.json"
            latest_daily.download_to_filename(str(local_path))
            
            with open(local_path, 'r') as f:
                data = json.load(f)
            
            logger.info(f"\nLatest Daily Refresh Report:")
            logger.info(f"  File: {latest_daily.name}")
            logger.info(f"  Created: {latest_daily.time_created}")
            logger.info(f"  Companies updated: {data.get('companies_with_updates', 'N/A')}")
            logger.info(f"  Pages scraped: {data.get('pages_scraped', 'N/A')}")
            logger.info(f"  Saved to: {local_path}")
        
        # Download last 10 daily reports for history
        all_daily_dir = reports_dir / "daily_history"
        all_daily_dir.mkdir(exist_ok=True)
        
        count = 0
        for blob in sorted(daily_reports, key=lambda b: b.time_created, reverse=True)[:10]:
            filename = blob.name.split('/')[-1]
            local_path = all_daily_dir / filename
            blob.download_to_filename(str(local_path))
            count += 1
        
        logger.info(f"\nDownloaded {count} daily reports to: {all_daily_dir}")
        logger.info("="*70)
        logger.info("REPORTS DOWNLOADED SUCCESSFULLY")
        logger.info("="*70)
        
        return True
        
    except Exception as e:
        logger.error(f"Failed to download reports: {e}")
        import traceback
        traceback.print_exc()
        return False


def run_post_processing():
    """Run post-processing after GCP Airflow scraping"""
    
    logger.info("="*70)
    logger.info(f"STARTING POST-PROCESSING - {datetime.now()}")
    logger.info("="*70)
    
    results = {
        'started_at': datetime.now().isoformat(),
        'completed_tasks': 0,
        'failed_tasks': 0,
        'task_results': []
    }
    
    # STEP 1: Download Airflow reports
    if download_airflow_reports():
        results['completed_tasks'] += 1
        results['task_results'].append({'task': 'Download Reports', 'status': 'success'})
    else:
        results['failed_tasks'] += 1
        results['task_results'].append({'task': 'Download Reports', 'status': 'failed'})
    
    # STEP 2: Extract structured data from GCS
    logger.info("\n" + "="*70)
    logger.info("STEP 2: EXTRACTING STRUCTURED DATA")
    logger.info("="*70)
    
    task_start = time.time()
    
    try:
        result = subprocess.run(
            ["python", "src/structured/structured_extract_gcp.py", "--all"],
            cwd=str(project_root),
            capture_output=True,
            timeout=1800,
            env={**os.environ, 'PYTHONIOENCODING': 'utf-8', 'PYTHONUTF8': '1'},
            encoding='utf-8',
            errors='replace'  # Replace problematic characters
        )
        
        task_elapsed = time.time() - task_start
        
        if result.returncode == 0:
            logger.info(f"SUCCESS: Structured extraction ({task_elapsed:.1f}s)")
            results['completed_tasks'] += 1
            results['task_results'].append({
                'task': 'Extract Structured Data',
                'status': 'success',
                'duration_seconds': task_elapsed
            })
        else:
            logger.error(f"FAILED: Structured extraction")
            results['failed_tasks'] += 1
            results['task_results'].append({
                'task': 'Extract Structured Data',
                'status': 'failed',
                'duration_seconds': task_elapsed
            })
    
    except Exception as e:
        logger.error(f"ERROR: {e}")
        results['failed_tasks'] += 1
    
    # STEP 3 & 4: Docker tasks (skip if extraction failed)
    if 'Extract Structured Data' in [r['task'] for r in results['task_results'] if r['status'] == 'success']:
        
        # STEP 3: Rebuild vector index in Docker
        logger.info("\n" + "="*70)
        logger.info("STEP 3: REBUILDING VECTOR INDEX (DOCKER)")
        logger.info("="*70)
        
        try:
            # Check if Docker is running
            docker_check = subprocess.run(
                ['docker', 'ps'],
                capture_output=True,
                timeout=5
            )
            
            if docker_check.returncode != 0:
                logger.error("Docker is not running! Start Docker first.")
                results['failed_tasks'] += 1
            else:
                # Run vector index build
                result = subprocess.run(
                    ['docker', 'exec', 'orbit-api', 'bash', '-c', 
                     'cd /app/src/vectordb && python build_index.py --gcs --no-clear'],
                    capture_output=True,
                    text=True,
                    timeout=1800,
                    encoding='utf-8',
                    errors='replace'
                )
                
                if result.returncode == 0:
                    logger.info("SUCCESS: Vector index rebuilt")
                    results['completed_tasks'] += 1
                else:
                    logger.error("FAILED: Vector index build")
                    logger.error(f"Check Docker logs: docker logs orbit-api")
                    results['failed_tasks'] += 1
        
        except Exception as e:
            logger.error(f"ERROR: Vector index - {e}")
            results['failed_tasks'] += 1
        
        # STEP 4: Generate dashboards in Docker
        logger.info("\n" + "="*70)
        logger.info("STEP 4: GENERATING DASHBOARDS (DOCKER)")
        logger.info("="*70)
        
        try:
            result = subprocess.run(
                ['docker', 'exec', 'orbit-api', 'python', 
                 'src/dashboard/generate_dashboards.py'],
                capture_output=True,
                text=True,
                timeout=3600,
                encoding='utf-8',
                errors='replace'
            )
            
            if result.returncode == 0:
                logger.info("SUCCESS: Dashboards generated")
                results['completed_tasks'] += 1
            else:
                logger.error("FAILED: Dashboard generation")
                results['failed_tasks'] += 1
        
        except Exception as e:
            logger.error(f"ERROR: Dashboard generation - {e}")
            results['failed_tasks'] += 1
    
    # Summary
    results['completed_at'] = datetime.now().isoformat()
    results['total_duration_seconds'] = time.time() - time.mktime(
        datetime.fromisoformat(results['started_at']).timetuple()
    )
    
    logger.info("\n" + "="*70)
    logger.info("POST-PROCESSING SUMMARY")
    logger.info("="*70)
    logger.info(f"Completed: {results['completed_tasks']} tasks")
    logger.info(f"Failed: {results['failed_tasks']} tasks")
    logger.info(f"Total time: {results['total_duration_seconds']:.1f}s")
    
    # Save results
    import json
    results_file = project_root / "data" / f"update_results_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    
    with open(results_file, 'w', encoding='utf-8') as f:
        json.dump(results, f, indent=2)
    
    logger.info(f"Results saved: {results_file}")
    
    if results['failed_tasks'] > 0:
        logger.warning(f"WARNING: {results['failed_tasks']} tasks failed")
    
    logger.info("="*70)
    
    return results


def test_run():
    """Test run"""
    logger.info("TEST RUN - Running post-processing now...")
    return run_post_processing()


def main():
    """Main scheduler"""
    
    if '--test' in sys.argv or '--once' in sys.argv:
        logger.info("Running ONCE (immediate execution, then exit)")
        test_run()
        return
    
    if '--download-only' in sys.argv:
        logger.info("DOWNLOAD ONLY - Fetching Airflow reports")
        download_airflow_reports()
        return
    
    # Scheduled mode
    scheduler = BlockingScheduler()
    
    scheduler.add_job(
        run_post_processing,
        'cron',
        hour=4,
        minute=0,
        id='daily_post_processing'
    )
    
    logger.info("="*70)
    logger.info("ORBIT DAILY SCHEDULER - Running at 4:00 AM daily")
    logger.info("="*70)
    logger.info("Press Ctrl+C to stop")
    
    try:
        scheduler.start()
    except KeyboardInterrupt:
        logger.info("\nScheduler stopped")


if __name__ == "__main__":
    main()