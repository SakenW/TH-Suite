@echo off
echo Starting TH-Suite MC L10n Desktop Application...

REM Start backend server
echo Starting backend server...
cd apps\mc_l10n\backend
set PYTHONPATH=..\..\..\packages\core\src;%PYTHONPATH%
start cmd /k "poetry run uvicorn main:app --reload --port 8000"

REM Wait a moment for backend to start
timeout /t 3 /nobreak > nul

REM Start Tauri frontend
echo Starting Tauri desktop application...
cd ..\frontend
start cmd /k "npm run tauri:dev"

echo Applications started successfully!
echo Backend API: http://localhost:8000/docs
echo Desktop app will open automatically...