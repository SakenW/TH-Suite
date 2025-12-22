@echo off
REM ============================================
REM   MC L10n Web模式完整启动脚本
REM   启动后端 + Web前端（浏览器访问）
REM ============================================

echo [%TIME%] [INFO] ============================================
echo [%TIME%] [INFO] MC L10n Web Mode Starting...
echo [%TIME%] [INFO] ============================================
echo.

REM 获取脚本所在目录
set SCRIPT_DIR=%~dp0
set APP_DIR=%SCRIPT_DIR%..

REM 启动后端服务器（新窗口）
echo [%TIME%] [INFO] [1/2] Starting backend server in new window...
start "MC L10n Backend" /D "%APP_DIR%\backend" cmd /k "call %SCRIPT_DIR%start-backend.bat"

REM 等待后端启动
echo [%TIME%] [INFO] Waiting for backend server to start...
timeout /t 5 /nobreak > nul

REM 检查后端是否启动成功
curl -s http://localhost:18000/health > nul 2>&1
if %errorlevel% neq 0 (
    echo [%TIME%] [WARN] Backend server may not be ready yet, continuing anyway...
) else (
    echo [%TIME%] [INFO] Backend server is running at http://localhost:18000
)

echo.
echo [%TIME%] [INFO] [2/2] Starting web frontend...
echo [%TIME%] [INFO] --------------------------------------------
echo.

REM 启动Web前端（当前窗口）
cd /d "%APP_DIR%\frontend"
npm run dev