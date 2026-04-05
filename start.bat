@echo off
echo ================================================
echo   Nilaavathy Plastics - GST Billing System
echo ================================================
echo.

cd /d "%~dp0backend"

echo Checking Python...
python --version >nul 2>&1
if errorlevel 1 (
    echo ERROR: Python is not installed or not in PATH.
    echo Please install Python 3.9+ from https://www.python.org
    pause
    exit /b 1
)

echo Installing dependencies (first run may take a moment)...
pip install -r requirements.txt -q

echo.
echo Starting server on http://localhost:8000
echo Open your browser and go to: http://localhost:8000
echo.
echo Press Ctrl+C to stop the server.
echo.

start "" "http://localhost:8000"
python -m uvicorn main:app --host 0.0.0.0 --port 8000 --reload

pause
