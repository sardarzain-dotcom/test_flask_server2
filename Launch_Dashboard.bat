@echo off
echo.
echo ================================================================
echo    🧬 ELISA BIOMARKER ANALYSIS DASHBOARD LAUNCHER
echo ================================================================
echo.
echo 🚀 Starting dashboard...
echo.
echo 📊 Dashboard will be available at:
echo    ► http://localhost:8501
echo    ► http://127.0.0.1:8501
echo.
echo 💡 The dashboard will open automatically in your default browser
echo 💡 Press Ctrl+C to stop the dashboard when finished
echo.
echo ================================================================
echo.

REM Launch the Streamlit dashboard
streamlit run elisa_streamlit_dashboard.py --server.headless false

echo.
echo Dashboard stopped.
pause