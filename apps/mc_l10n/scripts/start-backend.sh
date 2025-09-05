#!/bin/bash
# MC L10n 后端服务启动脚本

set -e

# 获取脚本所在目录
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
BACKEND_DIR="$SCRIPT_DIR/../backend"
PROJECT_ROOT="$SCRIPT_DIR/../../.."

# 颜色定义
GREEN='\033[0;32m'
RED='\033[0;31m'
NC='\033[0m'

# 日志函数
log_info() {
    echo -e "${GREEN}[INFO]${NC} $(date '+%Y-%m-%d %H:%M:%S') $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $(date '+%Y-%m-%d %H:%M:%S') $1"
}

# 主函数
log_info "============================================"
log_info "   MC L10n 后端服务器"
log_info "============================================"

# 检查 Poetry
if ! command -v poetry &> /dev/null; then
    log_error "Poetry 未找到！请先安装 Poetry"
    log_info "安装命令: curl -sSL https://install.python-poetry.org | python3 -"
    exit 1
fi

# 切换到后端目录
cd "$BACKEND_DIR"

# 设置环境变量
export PYTHONPATH="$PROJECT_ROOT/packages/core/src"
export ENVIRONMENT=development
export DEBUG=true
export LOG_LEVEL=INFO

log_info "环境: development"
log_info "调试模式: 已启用"
log_info "日志级别: INFO"
log_info "启动 FastAPI 服务器..."
log_info "API 地址: http://localhost:18000"
log_info "API 文档: http://localhost:18000/docs"
log_info "Redoc 文档: http://localhost:18000/redoc"
echo ""

# 启动服务器
poetry run python main.py