@echo off
REM Lab 8: Generate Dashboards (Simple - No Airflow)

cd /d "%~dp0"
echo ========================================
echo Lab 8: Generate Dashboards
echo ========================================
echo.

python src/structured/generate_all_dashboard.py

echo.
if %ERRORLEVEL% EQU 0 (
    echo ========================================
    echo Lab 8 Complete!
    echo Check: data\dashboards\*.json
    echo ========================================
) else (
    echo ========================================
    echo Lab 8 Failed!
    echo Check logs above
    echo ========================================
)

pause

