#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Update Vector DB Workflow
Builds vector index locally, uploads to GCS, and reloads Cloud Run - all in one go.
"""
import subprocess
import sys
import os
from pathlib import Path
import requests
import time

# Set UTF-8 encoding for Windows console compatibility
if sys.platform == 'win32':
    os.environ['PYTHONIOENCODING'] = 'utf-8'
    if hasattr(sys.stdout, 'reconfigure'):
        sys.stdout.reconfigure(encoding='utf-8')
    if hasattr(sys.stderr, 'reconfigure'):
        sys.stderr.reconfigure(encoding='utf-8')

# Configuration
PROJECT_ROOT = Path(__file__).resolve().parent
VECTORDB_DIR = PROJECT_ROOT / "src" / "vectordb"
DATA_DIR = PROJECT_ROOT / "data" / "qdrant_storage"
GCS_BUCKET = "gs://orbit-processed-data-g1-2025/qdrant_index/"
API_URL = "https://orbit-api-667820328373.us-central1.run.app"

def run_command(cmd, cwd=None, check=True):
    """Run a shell command and return the result."""
    print(f"\n{'='*70}")
    print(f"Running: {' '.join(cmd) if isinstance(cmd, list) else cmd}")
    print(f"{'='*70}\n")
    
    # Set UTF-8 encoding environment for subprocess
    env = os.environ.copy()
    env['PYTHONIOENCODING'] = 'utf-8'
    
    if isinstance(cmd, str):
        result = subprocess.run(cmd, shell=True, cwd=cwd, check=check, 
                              capture_output=True, text=True, encoding='utf-8', env=env)
    else:
        result = subprocess.run(cmd, cwd=cwd, check=check, 
                              capture_output=True, text=True, encoding='utf-8', env=env)
    
    if result.stdout:
        print(result.stdout)
    if result.stderr:
        print(f"\n⚠️  STDERR:\n{result.stderr}", file=sys.stderr)
    
    return result

def step1_build_index():
    """Step 1: Build vector index locally from GCS."""
    print("\n" + "="*70)
    print("STEP 1: Building Vector Index from GCS")
    print("="*70)
    
    try:
        result = run_command(
            [sys.executable, "build_index.py", "--gcs"],
            cwd=VECTORDB_DIR,
            check=False  # Don't raise exception, check return code manually
        )
        
        if result.returncode != 0:
            print(f"\n❌ Failed to build vector index (exit code: {result.returncode})")
            if result.stderr:
                print(f"\nFull error output:\n{result.stderr}")
            return False
        
        print("\n✅ Vector index built successfully!")
        return True
    except Exception as e:
        print(f"\n❌ Failed to build vector index: {e}")
        import traceback
        traceback.print_exc()
        return False

def step2_upload_to_gcs():
    """Step 2: Upload vector DB to GCS."""
    print("\n" + "="*70)
    print("STEP 2: Uploading Vector DB to GCS")
    print("="*70)
    
    if not DATA_DIR.exists():
        print(f"❌ Vector DB directory not found: {DATA_DIR}")
        return False
    
    # Check if storage.sqlite exists
    sqlite_file = DATA_DIR / "collection" / "pe_companies" / "storage.sqlite"
    if not sqlite_file.exists():
        print(f"❌ Vector DB file not found: {sqlite_file}")
        return False
    
    try:
        # Upload all files
        cmd = f'gsutil -m cp -r "{DATA_DIR}\\*" {GCS_BUCKET}'
        result = run_command(cmd, cwd=PROJECT_ROOT)
        print("\n✅ Vector DB uploaded to GCS successfully!")
        return True
    except subprocess.CalledProcessError as e:
        print(f"\n❌ Failed to upload to GCS: {e}")
        return False

def step3_reload_cloud_run():
    """Step 3: Reload vector store in Cloud Run."""
    print("\n" + "="*70)
    print("STEP 3: Reloading Vector Store in Cloud Run")
    print("="*70)
    
    reload_url = f"{API_URL}/admin/reload-vector-store"
    
    try:
        print(f"Calling: {reload_url}")
        response = requests.post(reload_url, timeout=60)
        response.raise_for_status()
        
        result = response.json()
        print(f"\n✅ Reload response: {result.get('message', 'Success')}")
        
        if 'stats' in result:
            stats = result['stats']
            print(f"   Total Companies: {stats.get('total_companies', 0)}")
            print(f"   Total Chunks: {stats.get('total_chunks', 0)}")
            print(f"   Vector Dimension: {stats.get('vector_dimension', 0)}")
        
        return True
    except requests.exceptions.RequestException as e:
        print(f"\n❌ Failed to reload Cloud Run: {e}")
        return False

def step4_verify():
    """Step 4: Verify the update worked."""
    print("\n" + "="*70)
    print("STEP 4: Verifying Update")
    print("="*70)
    
    stats_url = f"{API_URL}/stats"
    
    try:
        print(f"Checking: {stats_url}")
        # Wait a moment for reload to complete
        time.sleep(2)
        
        response = requests.get(stats_url, timeout=10)
        response.raise_for_status()
        
        result = response.json()
        
        chunks = result.get('total_chunks', 0)
        companies = result.get('total_companies', 0)
        
        print(f"\n✅ Verification Results:")
        print(f"   Total Chunks: {chunks}")
        print(f"   Total Companies: {companies}")
        
        if chunks > 0 and companies > 0:
            print("\n🎉 SUCCESS! Vector DB is updated and loaded in Cloud Run!")
            return True
        else:
            print("\n⚠️  Warning: Vector DB shows 0 chunks/companies")
            return False
            
    except requests.exceptions.RequestException as e:
        print(f"\n❌ Failed to verify: {e}")
        return False

def main():
    """Main workflow."""
    print("\n" + "="*70)
    print("🚀 VECTOR DB UPDATE WORKFLOW")
    print("="*70)
    print(f"Project Root: {PROJECT_ROOT}")
    print(f"GCS Bucket: {GCS_BUCKET}")
    print(f"API URL: {API_URL}")
    
    # Step 1: Build index
    if not step1_build_index():
        print("\n❌ Workflow failed at Step 1")
        sys.exit(1)
    
    # Step 2: Upload to GCS
    if not step2_upload_to_gcs():
        print("\n❌ Workflow failed at Step 2")
        sys.exit(1)
    
    # Step 3: Reload Cloud Run
    if not step3_reload_cloud_run():
        print("\n❌ Workflow failed at Step 3")
        sys.exit(1)
    
    # Step 4: Verify
    if not step4_verify():
        print("\n⚠️  Workflow completed but verification failed")
        sys.exit(1)
    
    print("\n" + "="*70)
    print("✅ ALL STEPS COMPLETED SUCCESSFULLY!")
    print("="*70)
    print("\nYour vector DB has been updated in Cloud Run without redeployment.")
    print(f"Check the API: {API_URL}/stats")

if __name__ == "__main__":
    main()

