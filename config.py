from pydantic_settings import BaseSettings
from functools import lru_cache
import os

class Settings(BaseSettings):
    # Application
    app_name: str = "ORBIT AI50 Intelligence"
    environment: str = os.getenv("ENVIRONMENT", "development")
    
    # OpenAI
    openai_api_key: str = os.getenv("OPENAI_API_KEY", "")
    openai_model: str = "gpt-4"
    
    # Qdrant
    qdrant_url: str = os.getenv("QDRANT_URL", "")
    qdrant_api_key: str = os.getenv("QDRANT_API_KEY", "")
    qdrant_collection: str = "forbes_ai50"
    
    # Google Cloud
    gcp_project_id: str = "orbit-ai50-intelligence"
    gcs_bucket_name: str = os.getenv("GCS_BUCKET_NAME", "")
    
    # API Settings
    max_query_length: int = 1000
    default_top_k: int = 5
    
    class Config:
        env_file = ".env"
        case_sensitive = False

@lru_cache()
def get_settings():
    return Settings()