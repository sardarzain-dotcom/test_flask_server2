@echo off
echo.
echo 🚀 STARTING ELISA DASHBOARD - STABLE VERSION
echo ==========================================
echo.

cd /d "c:\Users\sarda\Git\test_flask_server2"

echo 📁 Current Directory: %cd%
echo 🐍 Activating Python Environment...
call conda activate base

echo.
echo 📊 Starting ELISA Dashboard...
echo ⏰ Please wait for the URLs to appear...
echo.

REM Clear any existing streamlit processes
taskkill /f /im streamlit.exe 2>nul

REM Start streamlit with stable settings
streamlit run elisa_streamlit_dashboard.py --server.port 8506 --server.headless false --server.runOnSave false --browser.gatherUsageStats false

echo.
echo 🔗 If the above didn't work, try these URLs manually:
echo    http://localhost:8506
echo    http://127.0.0.1:8506
echo.
pause