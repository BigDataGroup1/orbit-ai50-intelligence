@echo off
echo ========================================
echo Starting FastAPI Server...
echo ========================================
echo.
echo FastAPI will run on: http://localhost:8000
echo Keep this window open!
echo.
cd /d "%~dp0"
python src/api/main.py
pause

