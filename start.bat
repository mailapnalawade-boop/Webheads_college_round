@echo off
echo ========================================================
echo Starting Second Opinion -- AI Answer Auditor Engine...
echo ========================================================

start "Second Opinion Backend API" cmd /k "cd backend && venv\Scripts\python.exe run.py"
start "Second Opinion Frontend UI" cmd /k "cd frontend && npm run dev"

echo Second Opinion Services Started!
echo Backend API Docs: http://localhost:8000/docs
echo Frontend Web App: http://localhost:5173
