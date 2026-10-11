@echo off
echo ========================================================
echo Starting Second Opinion -- AI Answer Auditor Engine...
echo ========================================================

if not exist "backend\.env" (
    if exist "backend\.env.example" (
        copy "backend\.env.example" "backend\.env" >nul
        echo Created backend\.env from backend\.env.example.
        echo REMINDER: Please edit backend\.env and add your GEMINI_API_KEY for online LLM mode!
    )
)

start "Second Opinion Backend API" cmd /k "cd backend && venv\Scripts\python.exe run.py"
start "Second Opinion Frontend UI" cmd /k "cd frontend && npm run dev"

echo Second Opinion Services Started!
echo Backend API Docs: http://localhost:8000/docs
echo Frontend Web App: http://localhost:5173
