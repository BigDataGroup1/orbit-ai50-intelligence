"""
GCP Storage Helper Functions
Author: Tapas
Download company data from GCP bucket with priority logic
"""

from google.cloud import storage
from pathlib import Path
import os

def get_gcp_client():
    """Get GCP storage client with credentials."""
    credentials_path = os.getenv('GOOGLE_APPLICATION_CREDENTIALS')
    
    # If credentials path is set and not empty, use it
    if credentials_path and credentials_path.strip():
        return storage.Client.from_service_account_json(credentials_path)
    
    # Otherwise, use application default credentials (gcloud auth)
    return storage.Client()

def list_companies_in_bucket(bucket_name: str = None):
    """List all companies in GCP bucket"""
    if not bucket_name:
        bucket_name = os.getenv('GCP_BUCKET_NAME')
    
    client = get_gcp_client()
    bucket = client.bucket(bucket_name)
    
    # List all company folders
    iterator = bucket.list_blobs(prefix='data/raw/', delimiter='/')
    
    # Consume the iterator to populate prefixes
    list(iterator)
    
    companies = set()
    for prefix in iterator.prefixes:
        # Extract company name from path: data/raw/CompanyName/
        parts = prefix.split('/')
        if len(parts) >= 3:
            companies.add(parts[2])
    
    return sorted(list(companies))

def get_latest_session_path(bucket_name: str, company_name: str):
    """
    Get latest session path for a company
    Priority: daily → initial
    """
    if not bucket_name:
        bucket_name = os.getenv('GCP_BUCKET_NAME')
    
    client = get_gcp_client()
    bucket = client.bucket(bucket_name)
    
    prefix = f'data/raw/{company_name}/'
    
    # Get all blobs to find session folders
    iterator = bucket.list_blobs(prefix=prefix, delimiter='/')
    list(iterator)  # Consume iterator
    
    sessions = []
    for blob_prefix in iterator.prefixes:
        session = blob_prefix.rstrip('/').split('/')[-1]
        if '_daily' in session or '_initial' in session:
            sessions.append(session)
    
    if not sessions:
        return None
    
    # Sort by date, prefer daily over initial
    sessions.sort(reverse=True)
    
    # Prefer latest daily if exists
    daily_sessions = [s for s in sessions if '_daily' in s]
    if daily_sessions:
        return f'{prefix}{daily_sessions[0]}/'
    
    # Otherwise use latest initial
    initial_sessions = [s for s in sessions if '_initial' in s]
    if initial_sessions:
        return f'{prefix}{initial_sessions[0]}/'
    
    return None

def download_company_files(bucket_name: str, company_name: str):
    """
    Download company files from GCP - HYBRID APPROACH
    - intelligence.json: Always from initial
    - Text files: Prefer daily, fallback to initial
    """
    if not bucket_name:
        bucket_name = os.getenv('GCP_BUCKET_NAME')
    
    client = get_gcp_client()
    bucket = client.bucket(bucket_name)
    
    # Get both session paths
    prefix = f'data/raw/{company_name}/'
    iterator = bucket.list_blobs(prefix=prefix, delimiter='/')
    list(iterator)
    
    sessions = {}
    for blob_prefix in iterator.prefixes:
        session = blob_prefix.rstrip('/').split('/')[-1]
        if '_daily' in session:
            sessions['daily'] = blob_prefix
        elif '_initial' in session:
            sessions['initial'] = blob_prefix
    
    if not sessions.get('initial'):
        raise FileNotFoundError(f"No initial data found for {company_name}")
    
    print(f"  📂 Using: {sessions.get('daily', sessions['initial']).split('/')[-2]} for content")
    print(f"  📂 Using: {sessions['initial'].split('/')[-2]} for intelligence")
    
    # Download text files from daily if exists, otherwise initial
    texts = {}
    content_path = sessions.get('daily', sessions['initial'])
    
    blobs = bucket.list_blobs(prefix=content_path)
    for blob in blobs:
        filename = blob.name.split('/')[-1]
        
        if filename.endswith('.txt'):
            content = blob.download_as_text()
            if content.strip():
                texts[filename.replace('.txt', '')] = content
                print(f"    ✅ {filename} ({len(content)} chars)")
    
    # ALWAYS load intelligence from initial
    intel = {}
    intel_blob = bucket.blob(f'{sessions["initial"]}intelligence.json')
    
    if intel_blob.exists():
        import json
        intel = json.loads(intel_blob.download_as_text())
        print(f"    ✅ intelligence.json (from initial)")
    
    # Extract folder name for metadata
    content_folder_name = content_path.split('/')[-2] 
    return {
        'texts': texts,
        'intelligence': intel,
        'company_name': company_name,
        'source_folder': content_folder_name,  # NEW!
        'data_files_used': list(texts.keys())  # NEW! e.g., ["blog", "careers", "news"]
    }