@echo off
REM Restart Airflow Docker containers with ADC credentials

cd /d "%~dp0"
echo Current directory: %CD%

echo.
echo Stopping containers...
docker-compose -f docker-compose.airflow.yml down

echo.
echo Starting containers...
docker-compose -f docker-compose.airflow.yml up -d

echo.
echo Waiting for containers to be ready...
timeout /t 10 /nobreak >nul

echo.
echo Checking container status...
docker-compose -f docker-compose.airflow.yml ps

echo.
echo ========================================
echo Containers restarted!
echo ========================================
echo.
echo Next steps:
echo 1. Verify ADC is mounted:
echo    docker exec orbit-airflow-scheduler python -c "import os; adc = '/root/.config/gcloud/application_default_credentials.json'; print('ADC exists:', os.path.exists(adc))"
echo.
echo 2. Test ADC works:
echo    docker exec orbit-airflow-scheduler python -c "from google.auth import default; from google.cloud import storage; creds, project = default(); print('ADC Works! Project:', project)"
echo.
echo 3. Run DAG in Airflow UI: http://localhost:8080
echo.
pause

