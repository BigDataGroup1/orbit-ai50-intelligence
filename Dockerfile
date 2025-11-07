# Dockerfile for Cloud Run - ORBIT AI50 Intelligence (API + Streamlit)
FROM python:3.10-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    curl \
    git \
    && rm -rf /var/lib/apt/lists/*

# Set environment variables (All variables consolidated here)
ENV PYTHONUNBUFFERED=1
ENV PORT=8080
# FIX: Set the Hugging Face cache directory to a writable location inside /app
ENV HF_HOME=/app/hf_cache

# Copy requirements (must be at the root of the source context)
COPY requirements.txt .

# Install PyTorch CPU-only first, then other packages
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir \
    torch==2.3.0 \
    --index-url https://download.pytorch.org/whl/cpu && \
    pip install --no-cache-dir -r requirements.txt


# Dockerfile

# ... (lines after pip install requirements.txt)

# FIX: Pre-cache the embedding model into the HF_HOME location
# The model will be available when the application starts
RUN python -c "from huggingface_hub import snapshot_download; snapshot_download(repo_id='sentence-transformers/all-MiniLM-L6-v2', cache_dir='/app/hf_cache', allow_patterns=['*.json', '*.bin', '*.txt'])"

# ... (lines before COPY src/)
# Copy application code (recursively copies all of src/)
COPY src/ ./src/

# Copy all data directories recursively (The most robust method)
# 1. Create the destination directory first
RUN mkdir -p data/

# 2. Copy the contents of the source 'data/' directory (data/.) 
#    into the destination directory ('./data/')
COPY data/. ./data/

# Create other directories (vector store built at runtime from GCS)
RUN mkdir -p data/qdrant_storage data/airflow_reports

# Expose port
EXPOSE 8080

# Default command
CMD exec uvicorn src.api.main:app --host 0.0.0.0 --port ${PORT} --workers 1