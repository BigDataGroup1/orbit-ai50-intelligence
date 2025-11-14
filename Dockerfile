FROM python:3.10-slim

WORKDIR /app

RUN apt-get update && apt-get install -y curl && rm -rf /var/lib/apt/lists/*

ENV PYTHONUNBUFFERED=1
ENV PORT=8080

COPY requirements.txt .

RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# Pre-download embedding model to avoid rate limits at runtime
RUN python -c "from sentence_transformers import SentenceTransformer; SentenceTransformer('all-MiniLM-L6-v2')"

COPY src/ ./src/
COPY data/dashboards/ ./data/dashboards/

RUN touch src/__init__.py src/api/__init__.py src/vectordb/__init__.py src/dashboard/__init__.py src/structured/__init__.py

RUN mkdir -p /tmp/qdrant_storage

EXPOSE 8080

CMD exec uvicorn src.api.main:app --host 0.0.0.0 --port ${PORT} --workers 1

