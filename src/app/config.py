"""
App configuration
"""
import os

# API URL - defaults to Cloud Run, can override with env var
API_URL = os.getenv('API_URL', 'https://orbit-api-667820328373.us-central1.run.app')  # FastAPI deployed URL

# Local development override
if os.getenv('ENVIRONMENT') == 'local':
    API_URL = 'http://localhost:8000'