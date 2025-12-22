@echo off
echo ========================================
echo   MC L10n Database Audit Tool
echo ========================================
echo.

cd /d "%~dp0\.."
echo Working directory: %CD%
echo.

REM 检查并关闭占用8889端口的进程
echo Checking port 8889...
for /f "tokens=5" %%a in ('netstat -ano ^| findstr :8889 ^| findstr LISTENING') do (
    echo Found process using port 8889: PID %%a
    tasklist /FI "PID eq %%a" | findstr python >nul 2>&1
    if %errorlevel% == 0 (
        echo Terminating old Python process...
        taskkill /F /PID %%a >nul 2>&1
        echo Old process terminated.
        timeout /t 1 /nobreak >nul
    )
)

echo Starting database audit server...
poetry run python scripts/db_audit.py

pause