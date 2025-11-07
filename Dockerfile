# Use Python 3.10 slim
FROM python:3.10-slim

# Set working directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    build-essential \
    curl \
    git \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements
COPY requirements.txt .

# Install Python dependencies
# Install torch CPU-only first, then other packages
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir \
    torch==2.1.0 \
    --index-url https://download.pytorch.org/whl/cpu && \
    pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY src/ ./src/
COPY data/qdrant_storage/ ./data/qdrant_storage/

# Create necessary directories
RUN mkdir -p data/payloads data/dashboards/rag data/dashboards/structured

# Set environment variables
ENV PYTHONUNBUFFERED=1
ENV PORT=8080

# Expose port (Cloud Run will set PORT env var)
EXPOSE 8080

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
  CMD curl -f http://localhost:${PORT}/ || exit 1

# Start FastAPI
CMD exec uvicorn src.api.main:app --host 0.0.0.0 --port ${PORT} --workers 1
