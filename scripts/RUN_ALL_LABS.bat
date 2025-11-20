@echo off
REM Run All Labs in Sequence (Simple - No Airflow)

cd /d "%~dp0"
echo ========================================
echo Running All Labs: Download - Lab 5 - Lab 6 - Lab 8
echo ========================================
echo.

echo Step 1: Download Daily Data from GCS...
call DOWNLOAD_DAILY.bat
if %ERRORLEVEL% NEQ 0 (
    echo Download failed! Stopping.
    pause
    exit /b 1
)

echo.
echo Step 2: Lab 5 - Structured Extraction...
call RUN_LAB5.bat
if %ERRORLEVEL% NEQ 0 (
    echo Lab 5 failed! Stopping.
    pause
    exit /b 1
)

echo.
echo Step 3: Lab 6 - Payload Assembly...
call RUN_LAB6.bat
if %ERRORLEVEL% NEQ 0 (
    echo Lab 6 failed! Stopping.
    pause
    exit /b 1
)

echo.
echo Step 4: Lab 8 - Generate Dashboards...
call RUN_LAB8.bat
if %ERRORLEVEL% NEQ 0 (
    echo Lab 8 failed! Stopping.
    pause
    exit /b 1
)

echo.
echo ========================================
echo All Labs Complete!
echo ========================================
echo.
echo Results:
echo - Structured: data\structured\*.json
echo - Payloads: data\payloads\*.json
echo - Dashboards: data\dashboards\*.json
echo ========================================
pause

