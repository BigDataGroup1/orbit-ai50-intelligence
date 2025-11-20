@echo off
chcp 65001 >nul
echo ========================================
echo Starting Airflow with Docker
echo ========================================
echo.
echo This will start:
echo   - PostgreSQL database
echo   - Airflow webserver (UI at http://localhost:8080)
echo   - Airflow scheduler (runs DAGs)
echo.
echo IMPORTANT: Make sure FastAPI is running first!
echo   Run: python src/api/main.py
echo.
pause

cd /d "%~dp0"

echo.
echo Starting Docker containers...
docker-compose -f docker-compose.airflow.yml up -d

if %ERRORLEVEL% NEQ 0 (
    echo.
    echo ❌ Failed to start Docker containers!
    echo.
    echo Make sure:
    echo   1. Docker Desktop is running
    echo   2. Docker is started and ready
    echo.
    pause
    exit /b 1
)

echo.
echo ✅ Docker containers started!
echo.
echo Waiting for Airflow to initialize (30 seconds)...
timeout /t 30 /nobreak >nul

echo.
echo ========================================
echo Airflow is starting...
echo ========================================
echo.
echo Access Airflow UI:
echo   URL: http://localhost:8080
echo   Username: admin
echo   Password: admin
echo.
echo To view logs:
echo   docker-compose -f docker-compose.airflow.yml logs -f
echo.
echo To stop:
echo   docker-compose -f docker-compose.airflow.yml down
echo.
pause

