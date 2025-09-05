#!/bin/bash
# MC L10n 停止所有服务脚本

set -e

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

# 日志函数
log_info() {
    echo -e "${GREEN}[INFO]${NC} $(date '+%Y-%m-%d %H:%M:%S') $1"
}

log_warn() {
    echo -e "${YELLOW}[WARN]${NC} $(date '+%Y-%m-%d %H:%M:%S') $1"
}

# 端口列表
PORTS=(18000 18081 18082 5173 15173)

log_info "============================================"
log_info "   停止 MC L10n 所有服务"
log_info "============================================"

# 停止占用特定端口的进程
for port in ${PORTS[@]}; do
    if command -v lsof &> /dev/null; then
        # macOS/Linux with lsof
        pids=$(lsof -ti:$port 2>/dev/null || true)
        if [ ! -z "$pids" ]; then
            log_info "停止端口 $port 上的进程..."
            echo "$pids" | xargs kill -9 2>/dev/null || true
            log_info "端口 $port 已清理"
        fi
    elif command -v netstat &> /dev/null; then
        # Linux with netstat
        pids=$(netstat -tlnp 2>/dev/null | grep ":$port" | awk '{print $7}' | cut -d'/' -f1 || true)
        if [ ! -z "$pids" ]; then
            log_info "停止端口 $port 上的进程..."
            echo "$pids" | xargs kill -9 2>/dev/null || true
            log_info "端口 $port 已清理"
        fi
    fi
done

# 查找并停止 Python 进程
log_info "查找相关 Python 进程..."
if command -v pgrep &> /dev/null; then
    # 停止 main.py
    pids=$(pgrep -f "python.*main.py" || true)
    if [ ! -z "$pids" ]; then
        log_info "停止后端服务器..."
        echo "$pids" | xargs kill -9 2>/dev/null || true
    fi
    
    # 停止数据库查看器
    pids=$(pgrep -f "python.*db_.*\.py" || true)
    if [ ! -z "$pids" ]; then
        log_info "停止数据库查看器..."
        echo "$pids" | xargs kill -9 2>/dev/null || true
    fi
    
    # 停止审计工具
    pids=$(pgrep -f "python.*audit" || true)
    if [ ! -z "$pids" ]; then
        log_info "停止审计工具..."
        echo "$pids" | xargs kill -9 2>/dev/null || true
    fi
fi

# 查找并停止 Node 进程
log_info "查找相关 Node.js 进程..."
if command -v pgrep &> /dev/null; then
    pids=$(pgrep -f "node.*vite\|node.*tauri" || true)
    if [ ! -z "$pids" ]; then
        log_info "停止前端开发服务器..."
        echo "$pids" | xargs kill -9 2>/dev/null || true
    fi
fi

# 查找并停止 Tauri 进程
if command -v pgrep &> /dev/null; then
    pids=$(pgrep -f "mc-l10n\|mc_l10n" || true)
    if [ ! -z "$pids" ]; then
        log_info "停止 Tauri 应用..."
        echo "$pids" | xargs kill -9 2>/dev/null || true
    fi
fi

log_info "============================================"
log_info "   所有服务已停止"
log_info "============================================"