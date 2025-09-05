@echo off
REM ============================================
REM   MC L10n 前端应用启动脚本
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

echo INFO:     %TIMESTAMP% {"event": "MC L10n Frontend Application Starting...", "service": "mc-l10n-frontend", "logger": "startup.frontend", "level": "info", "timestamp": "%TIMESTAMP%"}
echo INFO:     %TIMESTAMP% {"event": "============================================", "service": "mc-l10n-frontend", "logger": "startup.frontend", "level": "info", "timestamp": "%TIMESTAMP%"}
echo.

REM 切换到前端目录
cd /d "%~dp0\..\frontend"

REM 检查 Node.js 是否安装
node --version >nul 2>&1
if %errorlevel% neq 0 (
    echo ERROR:    %TIMESTAMP% {"event": "Node.js not found! Please install Node.js first.", "service": "mc-l10n-frontend", "logger": "startup.frontend", "level": "error", "timestamp": "%TIMESTAMP%", "details": "Visit: https://nodejs.org/"}
    pause
    exit /b 1
)

REM 检查依赖是否安装
if not exist "node_modules" (
    echo WARN:     %TIMESTAMP% {"event": "Node modules not found, installing dependencies...", "service": "mc-l10n-frontend", "logger": "startup.frontend", "level": "warn", "timestamp": "%TIMESTAMP%"}
    echo INFO:     %TIMESTAMP% {"event": "Running: npm install", "service": "mc-l10n-frontend", "logger": "startup.frontend", "level": "info", "timestamp": "%TIMESTAMP%"}
    npm install
    if %errorlevel% neq 0 (
        echo ERROR:    %TIMESTAMP% {"event": "Failed to install dependencies!", "service": "mc-l10n-frontend", "logger": "startup.frontend", "level": "error", "timestamp": "%TIMESTAMP%"}
        pause
        exit /b 1
    )
    echo INFO:     %TIMESTAMP% {"event": "Dependencies installed successfully", "service": "mc-l10n-frontend", "logger": "startup.frontend", "level": "info", "timestamp": "%TIMESTAMP%"}
    echo.
)

echo INFO:     %TIMESTAMP% {"event": "Starting Tauri development server", "service": "mc-l10n-frontend", "logger": "startup.frontend", "level": "info", "timestamp": "%TIMESTAMP%", "app_type": "Desktop (Tauri)", "dev_server": "http://localhost:15173"}
echo.

REM 启动 Tauri 开发服务器
npm run tauri:dev