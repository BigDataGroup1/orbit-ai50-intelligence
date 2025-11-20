@echo off
chcp 65001 >nul
echo ========================================
echo Running Agentic Dashboard DAG (TEST - 3 companies)
echo ========================================
echo.
echo This will run workflows for 3 companies (testing)
echo Auto-approve mode: ENABLED
echo.
cd /d "%~dp0"
python orbit_agentic_dashboard_local.py --limit 3 --auto-approve
pause

