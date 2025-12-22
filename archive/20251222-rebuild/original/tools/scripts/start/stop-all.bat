@echo off
REM ============================================
REM   MC L10n 停止所有服务脚本
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

echo INFO:     %TIMESTAMP% {"event": "Stopping MC L10n Services...", "service": "mc-l10n", "logger": "shutdown", "level": "info", "timestamp": "%TIMESTAMP%"}
echo.

REM 停止后端进程（Python/FastAPI）
echo INFO:     %TIMESTAMP% {"event": "Stopping backend server", "service": "mc-l10n", "logger": "shutdown", "level": "info", "timestamp": "%TIMESTAMP%", "port": 18000}
for /f "tokens=5" %%a in ('netstat -aon ^| findstr :18000 ^| findstr LISTENING') do (
    echo INFO:     %TIMESTAMP% {"event": "Killing process", "service": "mc-l10n", "logger": "shutdown", "level": "info", "timestamp": "%TIMESTAMP%", "pid": %%a, "type": "backend"}
    taskkill /F /PID %%a >nul 2>&1
)

REM 停止前端进程（Node.js/Vite）
echo INFO:     %TIMESTAMP% {"event": "Stopping frontend server", "service": "mc-l10n", "logger": "shutdown", "level": "info", "timestamp": "%TIMESTAMP%", "port": 15173}
for /f "tokens=5" %%a in ('netstat -aon ^| findstr :15173 ^| findstr LISTENING') do (
    echo INFO:     %TIMESTAMP% {"event": "Killing process", "service": "mc-l10n", "logger": "shutdown", "level": "info", "timestamp": "%TIMESTAMP%", "pid": %%a, "type": "frontend"}
    taskkill /F /PID %%a >nul 2>&1
)

REM 停止 Tauri 相关进程
echo INFO:     %TIMESTAMP% {"event": "Stopping Tauri processes", "service": "mc-l10n", "logger": "shutdown", "level": "info", "timestamp": "%TIMESTAMP%"}
taskkill /F /IM "th-suite-mc-l10n-frontend.exe" >nul 2>&1
taskkill /F /IM "cargo.exe" >nul 2>&1

echo.
echo INFO:     %TIMESTAMP% {"event": "All services stopped successfully", "service": "mc-l10n", "logger": "shutdown", "level": "info", "timestamp": "%TIMESTAMP%"}

pause