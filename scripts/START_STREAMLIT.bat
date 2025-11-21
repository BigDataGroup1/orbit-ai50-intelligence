@echo off
echo ========================================
echo Starting Streamlit App...
echo ========================================
echo.
echo Streamlit will open in your browser at: http://localhost:8501
echo.
cd /d "%~dp0"
streamlit run src/app/streamlit_app.py
pause

