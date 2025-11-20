@echo off
REM Lab 5: Run Structured Extraction (Simple - No Airflow)

cd /d "%~dp0"
echo ========================================
echo Lab 5: Structured Extraction
echo ========================================
echo.

python src/structured/structured_extract.py --all

echo.
if %ERRORLEVEL% EQU 0 (
    echo ========================================
    echo Lab 5 Complete!
    echo Check: data\structured\*.json
    echo ========================================
) else (
    echo ========================================
    echo Lab 5 Failed!
    echo Check logs above
    echo ========================================
)

pause
