@echo off
REM Lab 6: Run Payload Assembly (Simple - No Airflow)

cd /d "%~dp0"
echo ========================================
echo Lab 6: Payload Assembly
echo ========================================
echo.

python src/structured/structured_payload_lab6.py

echo.
if %ERRORLEVEL% EQU 0 (
    echo ========================================
    echo Lab 6 Complete!
    echo Check: data\payloads\*.json
    echo ========================================
) else (
    echo ========================================
    echo Lab 6 Failed!
    echo Check logs above
    echo ========================================
)

pause

