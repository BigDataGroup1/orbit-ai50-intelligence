#!/bin/bash

echo "========================================="
echo "  🔧 Initializing ORBIT with GCS Data"
echo "========================================="
echo ""

# Check GCP credentials
if [ ! -f gcp-service-account.json ]; then
    echo "❌ GCP service account key not found!"
    echo "📝 Please add gcp-service-account.json to project root"
    exit 1
fi

# Start containers
echo "🚀 Starting Docker containers..."
docker-compose up --build -d

# Wait for API to be ready
echo "⏳ Waiting for API to start..."
sleep 10

# Build vector index from GCS
echo "📊 Building vector index from GCS..."
docker exec -it orbit-api bash -c "cd /app/src/vectordb && python build_index.py --gcs"

# Restart API to load new index
echo "🔄 Restarting API..."
docker-compose restart api

echo ""
echo "========================================="
echo "✅ ORBIT initialized with GCS data!"
echo "========================================="
echo ""
echo "📍 FastAPI:   http://localhost:8000"
echo "📍 Streamlit: http://localhost:8501"
echo ""