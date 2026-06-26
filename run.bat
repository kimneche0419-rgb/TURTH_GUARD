@echo off
echo ==================================================
echo         TruthGuard Full-Stack Dev Booter
echo ==================================================

:: 1. Check Python Virtual Environment
if not exist ".venv" (
    echo [ERROR] .venv virtual environment not found. Please setup python environment first.
    pause
    exit /b 1
)

:: 2. Check and Install Node Modules
if not exist "node_modules" (
    echo [INFO] node_modules folder not found. Running npm install...
    call npm install
    if %errorlevel% neq 0 (
        echo [ERROR] npm install failed.
        pause
        exit /b 1
    )
)

echo [SUCCESS] Dependency check passed. Starting servers...

:: 3. Start FastAPI backend in a new window
echo [INFO] Starting FastAPI backend on Port 8000...
start "TruthGuard Backend" cmd /c ".venv\Scripts\python.exe -m uvicorn truthguard_server:app --reload --port 8000"

:: 4. Start React frontend in a new window
echo [INFO] Starting React Frontend on Port 5173...
start "TruthGuard Dashboard" cmd /c "npm run dev"

echo ==================================================
echo  [SUCCESS] Both servers are starting up!
echo  - Backend URL: http://localhost:8000
echo  - Frontend URL: http://localhost:5173
echo ==================================================
echo.
