@echo off
REM ============================================
REM   MC L10n Web 前端启动脚本（仅浏览器模式）
REM ============================================

echo [%TIME%] [INFO] ============================================
echo [%TIME%] [INFO] MC L10n Web Frontend Starting...
echo [%TIME%] [INFO] ============================================
echo.

REM 切换到前端目录
cd /d "%~dp0\..\frontend"

REM 检查 Node.js 是否安装
node --version >nul 2>&1
if %errorlevel% neq 0 (
    echo [%TIME%] [ERROR] Node.js not found! Please install Node.js first.
    echo [%TIME%] [ERROR] Visit: https://nodejs.org/
    pause
    exit /b 1
)

REM 检查依赖是否安装
if not exist "node_modules" (
    echo [%TIME%] [WARN] Node modules not found, installing dependencies...
    echo [%TIME%] [INFO] Running: npm install
    npm install
    if %errorlevel% neq 0 (
        echo [%TIME%] [ERROR] Failed to install dependencies!
        pause
        exit /b 1
    )
    echo [%TIME%] [INFO] Dependencies installed successfully.
    echo.
)

echo [%TIME%] [INFO] Starting web development server...
echo [%TIME%] [INFO] Application Type: Web Browser Only
echo [%TIME%] [INFO] Access URL: http://localhost:15173
echo [%TIME%] [INFO] Network: Check console output for network URL
echo [%TIME%] [INFO] --------------------------------------------
echo.

REM 启动 Vite 开发服务器（仅 Web 模式）
npm run dev