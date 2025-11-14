FROM python:3.10-slim
WORKDIR /app
RUN apt-get update && apt-get install -y curl && rm -rf /var/lib/apt/lists/*
COPY requirements.streamlit.txt .
RUN pip install --no-cache-dir -r requirements.streamlit.txt
COPY src/app/ ./src/app/
COPY data/dashboards/ ./data/dashboards/
RUN touch src/__init__.py src/app/__init__.py
EXPOSE 8501
CMD ["streamlit", "run", "src/app/streamlit_app.py", "--server.port=8501", "--server.address=0.0.0.0", "--server.headless=true"]