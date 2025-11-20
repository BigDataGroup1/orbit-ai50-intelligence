"""
Simple script to download daily data from GCS
Run this before Lab 5, 6, 8
"""

from google.cloud import storage
from pathlib import Path
import os
import sys

# Configuration
GCP_PROJECT_ID = 'orbit-ai50-intelligence'
GCS_RAW_BUCKET = 'orbit-raw-data-g1-2025'

# Data directory
DATA_DIR = Path('data/raw')

def download_daily_data():
    """Download daily data from GCS"""
    print("="*70)
    print("Downloading Daily Data from GCS")
    print("="*70)
    
    # Setup credentials
    credentials_path = None
    
    # Priority 1: Try ADC
    adc_paths = [
        'adc-credentials.json',
        os.path.expanduser('~/.config/gcloud/application_default_credentials.json'),
    ]
    for adc_path in adc_paths:
        if os.path.exists(adc_path):
            os.environ['GOOGLE_APPLICATION_CREDENTIALS'] = adc_path
            credentials_path = adc_path
            print(f"[OK] Using ADC: {adc_path}")
            break
    
    # Priority 2: Try service account JSON
    if not credentials_path:
        service_account_paths = [
            'gcp-credentials.json',
            'gcp-service-account.json.json',
            'gcp-service-account.json',
        ]
        for sa_path in service_account_paths:
            if os.path.exists(sa_path):
                os.environ['GOOGLE_APPLICATION_CREDENTIALS'] = sa_path
                credentials_path = sa_path
                print(f"[OK] Using service account: {sa_path}")
                break
    
    if not credentials_path:
        print("[ERROR] No GCP credentials found!")
        print("Options:")
        print("  1. Place adc-credentials.json in project root")
        print("  2. Place gcp-credentials.json in project root")
        print("  3. Run: gcloud auth application-default login")
        return False
    
    try:
        # Create GCS client
        client = storage.Client(project=GCP_PROJECT_ID)
        bucket = client.bucket(GCS_RAW_BUCKET)
        
        # Look for both initial and daily data
        raw_prefix = "data/raw/"
        print(f"\nLooking for data with prefix: {raw_prefix}")
        
        all_blobs = list(bucket.list_blobs(prefix=raw_prefix))
        
        # Separate initial and daily blobs
        initial_blobs = [b for b in all_blobs if '_initial' in b.name]
        daily_blobs = [b for b in all_blobs if '_daily' in b.name]
        
        # Find the latest initial date
        initial_dates = set()
        for blob in initial_blobs:
            # Extract date from path like: data/raw/Company/2025-11-17_initial/file.txt
            parts = blob.name.split('/')
            for part in parts:
                if '_initial' in part:
                    date_str = part.replace('_initial', '')
                    initial_dates.add(date_str)
                    break
        
        if initial_dates:
            latest_initial_date = max(initial_dates)
            print(f"\n[INFO] Found initial data dates: {sorted(initial_dates)}")
            print(f"[INFO] Using latest initial data: {latest_initial_date}")
            
            # Filter for latest initial data only
            latest_initial_blobs = [b for b in initial_blobs if f'{latest_initial_date}_initial' in b.name]
            print(f"[INFO] Found {len(latest_initial_blobs)} files in latest initial data")
        else:
            latest_initial_blobs = []
            print("[WARNING] No initial data found")
        
        if not daily_blobs:
            print("[WARNING] No daily data found in GCS bucket")
        else:
            print(f"[INFO] Found {len(daily_blobs)} daily data files")
        
        if not latest_initial_blobs and not daily_blobs:
            print(f"[ERROR] No data found in gs://{GCS_RAW_BUCKET}/data/raw/")
            return False
        
        # Download latest initial data first
        downloaded = 0
        if latest_initial_blobs:
            print(f"\n[STEP 1] Downloading latest initial data ({latest_initial_date})...")
            for blob in latest_initial_blobs:
                relative_path = blob.name.replace('data/raw/', '')
                local_file = DATA_DIR / relative_path
                local_file.parent.mkdir(parents=True, exist_ok=True)
                
                blob.download_to_filename(str(local_file))
                downloaded += 1
                if downloaded % 50 == 0:  # Print every 50 files
                    print(f"  [OK] Downloaded {downloaded} initial files...")
            
            print(f"[OK] Downloaded {downloaded} initial data files")
        
        # Then download daily data
        daily_downloaded = 0
        if daily_blobs:
            print(f"\n[STEP 2] Downloading daily data...")
            for blob in daily_blobs:
                relative_path = blob.name.replace('data/raw/', '')
                local_file = DATA_DIR / relative_path
                local_file.parent.mkdir(parents=True, exist_ok=True)
                
                blob.download_to_filename(str(local_file))
                daily_downloaded += 1
                if daily_downloaded % 50 == 0:  # Print every 50 files
                    print(f"  [OK] Downloaded {daily_downloaded} daily files...")
            
            print(f"[OK] Downloaded {daily_downloaded} daily data files")
        
        total_downloaded = downloaded + daily_downloaded
        print(f"\n[OK] Total downloaded: {total_downloaded} files ({downloaded} initial + {daily_downloaded} daily)")
        print(f"Location: {DATA_DIR.absolute()}")
        return True
        
    except Exception as e:
        print(f"[ERROR] Error downloading daily data: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    success = download_daily_data()
    sys.exit(0 if success else 1)

