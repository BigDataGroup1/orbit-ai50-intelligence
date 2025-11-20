@echo off
REM Download Daily Data from GCS (Simple - No Airflow)

cd /d "%~dp0"
echo ========================================
echo Downloading Daily Data from GCS
echo ========================================
echo.

python download_daily_from_gcs.py

echo.
if %ERRORLEVEL% EQU 0 (
    echo ========================================
    echo Download Complete!
    echo Data saved to: data\raw\
    echo ========================================
    echo.
    echo Next steps:
    echo 1. Run Lab 5: RUN_LAB5.bat
    echo 2. Run Lab 6: RUN_LAB6.bat
    echo 3. Run Lab 8: RUN_LAB8.bat
) else (
    echo ========================================
    echo Download Failed!
    echo Check credentials and try again
    echo ========================================
)

pause

