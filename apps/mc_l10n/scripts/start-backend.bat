@echo off
REM ============================================
REM   MC L10n 后端服务启动脚本
REM   使用结构化日志格式
REM ============================================

setlocal enabledelayedexpansion

REM 获取当前时间函数
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

REM 切换到脚本目录
cd /d "%~dp0"

REM 输出启动日志
echo INFO:     %TIMESTAMP% {"event": "MC L10n Backend Server Starting...", "service": "mc-l10n-backend", "logger": "startup.backend", "level": "info", "timestamp": "%TIMESTAMP%"}
echo INFO:     %TIMESTAMP% {"event": "============================================", "service": "mc-l10n-backend", "logger": "startup.backend", "level": "info", "timestamp": "%TIMESTAMP%"}
echo.

REM 切换到后端目录
cd /d "%~dp0\..\backend"

REM 设置环境变量
set PYTHONPATH=..\..\..\packages\core\src;%PYTHONPATH%
set ENVIRONMENT=development
set DEBUG=true
set LOG_LEVEL=INFO

echo INFO:     %TIMESTAMP% {"event": "Environment: development, Debug: true, LogLevel: INFO", "service": "mc-l10n-backend", "logger": "startup.backend", "level": "info", "timestamp": "%TIMESTAMP%"}

REM 检查 Poetry 是否安装
poetry --version >nul 2>&1
if %errorlevel% neq 0 (
    echo ERROR:    %TIMESTAMP% {"event": "Poetry not found! Please install Poetry first.", "service": "mc-l10n-backend", "logger": "startup.backend", "level": "error", "timestamp": "%TIMESTAMP%", "details": "Visit: https://python-poetry.org/docs/#installation"}
    pause
    exit /b 1
)

echo INFO:     %TIMESTAMP% {"event": "Starting FastAPI server on http://localhost:18000", "service": "mc-l10n-backend", "logger": "startup.backend", "level": "info", "timestamp": "%TIMESTAMP%", "endpoints": {"api": "http://localhost:18000", "docs": "http://localhost:18000/docs", "redoc": "http://localhost:18000/redoc"}}
echo.

REM 启动后端服务
poetry run python main.py