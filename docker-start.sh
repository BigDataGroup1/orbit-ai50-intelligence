#!/bin/bash

# Docker startup script for Project ORBIT
set -e

echo "========================================="
echo "  🚀 Starting ORBIT PE Dashboard"
echo "========================================="
echo ""

# Check if .env exists
if [ ! -f .env ]; then
    echo "⚠️  .env file not found!"
    echo "📝 Creating from .env.example..."
    cp .env.example .env
    echo "⚠️  Please edit .env and add your API keys!"
    exit 1
fi

# Check if data directories exist
if [ ! -d "data/dashboards" ]; then
    echo "⚠️  Dashboard data not found!"
    echo "💡 Run Labs 5-8 first to generate dashboards"
    exit 1
fi

echo "🔧 Starting in DEVELOPMENT mode..."
docker-compose up --build -d

echo ""
echo "========================================="
echo "✅ Services started successfully!"
echo "========================================="
echo ""
echo "📍 FastAPI:   http://localhost:8000"
echo "📍 API Docs:  http://localhost:8000/docs"
echo "📍 Streamlit: http://localhost:8501"
echo ""
echo "📊 View logs:"
echo "   docker-compose logs -f"
echo ""
echo "🛑 Stop services:"
echo "   docker-compose down"
echo ""
