@echo off
chcp 65001 >nul
echo ========================================
echo Running Agentic Dashboard DAG
echo ========================================
echo.
echo This will run workflows for all AI 50 companies
echo Auto-approve mode: ENABLED
echo.
cd /d "%~dp0"
python orbit_agentic_dashboard_local.py --auto-approve
pause

