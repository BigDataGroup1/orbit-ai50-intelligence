@echo off
chcp 65001 >nul
echo ========================================
echo Stopping Airflow Docker Containers
echo ========================================
echo.

cd /d "%~dp0"

docker-compose -f docker-compose.airflow.yml down

if %ERRORLEVEL% EQU 0 (
    echo.
    echo ✅ Airflow stopped successfully!
) else (
    echo.
    echo ⚠️  Some containers may not have stopped
)

echo.
pause

