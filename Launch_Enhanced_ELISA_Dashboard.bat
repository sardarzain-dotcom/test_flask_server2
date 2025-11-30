@echo off
REM Enhanced ELISA Dashboard Launcher
REM Created: November 27, 2025

echo.
echo ==========================================
echo   ELISA Enhanced Dashboard Launcher
echo ==========================================
echo.
echo Starting enhanced dashboard with all features:
echo - Statistical Analysis
echo - 3D Visualizations  
echo - Animation Support
echo - Background Customization
echo - Data Management
echo.

cd /d "c:\Users\sarda\Git\test_flask_server2"

echo Checking Python environment...
python --version
if %errorlevel% neq 0 (
    echo Error: Python not found. Please install Python.
    pause
    exit /b 1
)

echo.
echo Launching Enhanced ELISA Dashboard...
echo URL will be available at: http://localhost:8507
echo Network URL: http://192.168.2.29:8507
echo.

python -m streamlit run elisa_test_dashboard.py --server.port 8507 --server.headless false

if %errorlevel% neq 0 (
    echo.
    echo Error launching dashboard. Trying alternative port...
    python -m streamlit run elisa_test_dashboard.py --server.port 8508
)

pause