"""
App configuration
"""
import os

# API URL - defaults to Cloud Run, can override with env var
API_URL = os.getenv('API_URL', 'https://orbit-api-823575734493.us-central1.run.app')

# Local development override
if os.getenv('ENVIRONMENT') == 'local':
    API_URL = 'http://localhost:8000'