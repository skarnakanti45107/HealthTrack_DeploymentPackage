@echo off
echo ===================================================
echo Starting HealthTrack Deployment Package...
echo ===================================================

echo 1. Installing required dependencies...
python -m pip install -r requirements.txt

echo 2. Starting FastAPI Backend Server...
start cmd /k "python -m uvicorn main:app --reload"

echo 3. Starting Dash Real-Time Dashboard...
timeout /t 3
start cmd /k "python dashboard.py"

echo ===================================================
echo Deployment complete! 
echo API running at http://127.0.0.1:8000/docs
echo Dashboard running at http://127.0.0.1:8050
echo ===================================================