#!/bin/bash
# MC L10n 完整启动脚本（桌面应用模式）
# 启动后端服务器和 Tauri 桌面应用

set -e

# 获取脚本所在目录
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
BACKEND_DIR="$SCRIPT_DIR/../backend"
FRONTEND_DIR="$SCRIPT_DIR/../frontend"
PROJECT_ROOT="$SCRIPT_DIR/../../.."

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# 日志函数
log_info() {
    echo -e "${GREEN}[INFO]${NC} $(date '+%Y-%m-%d %H:%M:%S') $1"
}

log_warn() {
    echo -e "${YELLOW}[WARN]${NC} $(date '+%Y-%m-%d %H:%M:%S') $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $(date '+%Y-%m-%d %H:%M:%S') $1"
}

# 检查依赖
check_dependencies() {
    log_info "检查依赖..."
    
    # 检查 Python
    if ! command -v python &> /dev/null; then
        log_error "Python 未找到！请先安装 Python 3.12+"
        exit 1
    fi
    
    # 检查 Poetry
    if ! command -v poetry &> /dev/null; then
        log_error "Poetry 未找到！请先安装 Poetry"
        log_info "安装命令: curl -sSL https://install.python-poetry.org | python3 -"
        exit 1
    fi
    
    # 检查 Node.js
    if ! command -v node &> /dev/null; then
        log_error "Node.js 未找到！请先安装 Node.js 18+"
        exit 1
    fi
    
    # 检查 Rust（Tauri需要）
    if ! command -v cargo &> /dev/null; then
        log_warn "Cargo 未找到！将使用 Web 模式"
        WEB_MODE=true
    else
        WEB_MODE=false
    fi
}

# 清理函数
cleanup() {
    log_info "停止所有服务..."
    
    # 停止后端
    if [ ! -z "$BACKEND_PID" ]; then
        kill $BACKEND_PID 2>/dev/null || true
    fi
    
    # 停止前端
    if [ ! -z "$FRONTEND_PID" ]; then
        kill $FRONTEND_PID 2>/dev/null || true
    fi
    
    # 清理端口（使用正确的端口）
    if command -v lsof &> /dev/null; then
        lsof -ti:18000 | xargs kill -9 2>/dev/null || true
        lsof -ti:18001 | xargs kill -9 2>/dev/null || true
    fi
    
    log_info "所有服务已停止"
}

# 设置信号处理
trap cleanup EXIT INT TERM

# 主函数
main() {
    log_info "============================================"
    log_info "   MC L10n 应用启动器 - 完整模式"
    log_info "============================================"
    
    # 检查依赖
    check_dependencies
    
    # 启动后端
    log_info "启动后端服务器..."
    cd "$BACKEND_DIR"
    
    # 设置环境变量
    export PYTHONPATH="$PROJECT_ROOT/packages/core/src"
    export ENVIRONMENT=development
    export DEBUG=true
    export LOG_LEVEL=INFO
    
    # 后台启动后端
    poetry run python main.py &
    BACKEND_PID=$!
    
    log_info "后端服务器已启动 (PID: $BACKEND_PID)"
    log_info "API 地址: http://localhost:18000"
    log_info "API 文档: http://localhost:18000/docs"
    
    # 等待后端就绪
    log_info "等待后端服务就绪..."
    sleep 3
    
    # 检查后端是否运行
    if ! kill -0 $BACKEND_PID 2>/dev/null; then
        log_error "后端启动失败"
        exit 1
    fi
    
    # 启动前端
    log_info "启动前端应用..."
    cd "$FRONTEND_DIR"
    
    # 检查依赖是否安装
    if [ ! -d "node_modules" ]; then
        log_info "安装前端依赖..."
        npm install
    fi
    
    if [ "$WEB_MODE" = true ]; then
        log_warn "使用 Web 模式启动前端"
        npm run dev
    else
        log_info "使用 Tauri 桌面模式启动前端"
        npm run tauri:dev
    fi
}

# 运行主函数
main "$@"