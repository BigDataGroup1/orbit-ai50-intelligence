@echo off
echo ========================================
echo Installing Apache Airflow...
echo ========================================
echo.
echo This may take a few minutes...
echo.

cd /d "%~dp0"

echo Step 1: Installing Airflow...
pip install apache-airflow

if %ERRORLEVEL% NEQ 0 (
    echo.
    echo ❌ Installation failed!
    echo.
    echo This might be due to Python 3.13 compatibility.
    echo Try using the standalone script instead:
    echo   python orbit_agentic_dashboard_local.py --limit 3
    pause
    exit /b 1
)

echo.
echo ✅ Airflow installed!
echo.
echo Step 2: Initializing database...
airflow db init

echo.
echo Step 3: Creating admin user...
echo (Username: admin, Password: admin)
airflow users create --username admin --firstname Admin --lastname User --role Admin --email admin@example.com --password admin

echo.
echo Step 4: Creating directories...
if not exist "%USERPROFILE%\airflow" mkdir "%USERPROFILE%\airflow"
if not exist "%USERPROFILE%\airflow\dags" mkdir "%USERPROFILE%\airflow\dags"
if not exist "%USERPROFILE%\airflow\logs" mkdir "%USERPROFILE%\airflow\logs"

echo.
echo Step 5: Copying DAG file...
copy "airflow\dags\orbit_agentic_dashboard_dag_local.py" "%USERPROFILE%\airflow\dags\"

echo.
echo ========================================
echo ✅ Installation Complete!
echo ========================================
echo.
echo Next steps:
echo 1. Open Terminal 1: airflow webserver --port 8080
echo 2. Open Terminal 2: airflow scheduler
echo 3. Open browser: http://localhost:8080
echo 4. Login: admin / admin
echo.
pause

