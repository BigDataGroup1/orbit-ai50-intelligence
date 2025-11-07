#!/bin/bash

echo "========================================="
echo "  🔧 ORBIT GCS Setup"
echo "========================================="
echo ""

# 1. Check GCP credentials
if [ ! -f gcp-service-account.json ]; then
    echo "❌ GCP service account key not found!"
    echo ""
    echo "📝 To set up:"
    echo "   1. Download service account JSON from GCP Console"
    echo "   2. Save as gcp-service-account.json in project root"
    echo "   3. Run this script again"
    exit 1
fi

echo "✅ GCP credentials found"

# 2. Check .env file
if [ ! -f .env ]; then
    echo "📝 Creating .env file..."
    cat > .env << 'EOF'
# OpenAI API Key
OPENAI_API_KEY=your-key-here

# GCP Configuration
GOOGLE_APPLICATION_CREDENTIALS=./gcp-service-account.json
GCP_PROJECT_ID=orbit-ai50-intelligence
GCP_BUCKET_NAME=orbit-raw-data-group1-2025
EOF
    echo "⚠️  Please edit .env and add your OPENAI_API_KEY"
    exit 1
fi

echo "✅ .env file exists"

# 3. Build vector index from GCS (local, not Docker yet)
echo ""
echo "📊 Building vector index from GCS..."
python src/vectordb/build_index.py --gcs

# 4. Generate structured dashboards
echo ""
echo "📊 Generating structured dashboards..."
python src/structured/generate_eval_structured.py

# 5. Generate RAG dashboards
echo ""
echo "📊 Generating RAG dashboards..."
python src/dashboard/generate_eval_dashboard.py

# 6. Generate evaluation report
echo ""
echo "📊 Generating evaluation report..."
python src/evaluation/generate_eval_report.py

echo ""
echo "========================================="
echo "✅ Setup Complete!"
echo "========================================="
echo ""
echo "📋 Generated:"
echo "   - Vector index from GCS"
echo "   - RAG dashboards (6 companies)"
echo "   - Structured dashboards (6 companies)"
echo "   - EVAL.md comparison report"
echo ""
echo "🚀 Next: Start Docker services"
echo "   ./docker-init.sh"
echo ""