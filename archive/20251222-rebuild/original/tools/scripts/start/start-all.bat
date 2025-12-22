@echo off
REM ============================================
REM   MC L10n 完整应用启动脚本
REM   使用结构化日志格式
REM ============================================

setlocal enabledelayedexpansion

REM 获取当前时间
for /f "tokens=1-3 delims=:." %%a in ('echo %TIME%') do (
    set HOUR=%%a
    set MIN=%%b
    set SEC=%%c
)
for /f "tokens=1-3 delims=/" %%a in ('echo %DATE%') do (
    set YEAR=%%c
    set MONTH=%%a
    set DAY=%%b
)
set TIMESTAMP=%YEAR%-%MONTH%-%DAY% %HOUR%:%MIN%:%SEC%

echo INFO:     %TIMESTAMP% {"event": "MC L10n Full Application Starting...", "service": "mc-l10n", "logger": "startup.main", "level": "info", "timestamp": "%TIMESTAMP%"}
echo INFO:     %TIMESTAMP% {"event": "============================================", "service": "mc-l10n", "logger": "startup.main", "level": "info", "timestamp": "%TIMESTAMP%"}
echo.

REM 获取脚本所在目录
set SCRIPT_DIR=%~dp0
set APP_DIR=%SCRIPT_DIR%..

REM 启动后端服务器（新窗口）
echo INFO:     %TIMESTAMP% {"event": "[1/2] Starting backend server in new window...", "service": "mc-l10n", "logger": "startup.main", "level": "info", "timestamp": "%TIMESTAMP%"}
start "MC L10n Backend" /D "%APP_DIR%\backend" cmd /k "call %SCRIPT_DIR%start-backend.bat"

REM 等待后端启动
echo INFO:     %TIMESTAMP% {"event": "Waiting for backend server to start...", "service": "mc-l10n", "logger": "startup.main", "level": "info", "timestamp": "%TIMESTAMP%"}
timeout /t 5 /nobreak > nul

REM 检查后端是否启动成功
curl -s http://localhost:18000/health > nul 2>&1
if %errorlevel% neq 0 (
    echo WARN:     %TIMESTAMP% {"event": "Backend server may not be ready yet, continuing anyway...", "service": "mc-l10n", "logger": "startup.main", "level": "warn", "timestamp": "%TIMESTAMP%"}
) else (
    echo INFO:     %TIMESTAMP% {"event": "Backend server is running", "service": "mc-l10n", "logger": "startup.main", "level": "info", "timestamp": "%TIMESTAMP%", "backend_url": "http://localhost:18000"}
)

echo.
echo INFO:     %TIMESTAMP% {"event": "[2/2] Starting frontend application...", "service": "mc-l10n", "logger": "startup.main", "level": "info", "timestamp": "%TIMESTAMP%"}
echo.

REM 启动前端应用（当前窗口）
cd /d "%APP_DIR%\frontend"
npm run tauri:dev