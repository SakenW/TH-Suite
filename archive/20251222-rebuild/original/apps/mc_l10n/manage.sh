#!/bin/bash

# MC L10n 服务管理脚本
# 用于启动、停止和管理开发服务器

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# 固定端口配置
FRONTEND_PORT=5173
BACKEND_PORT=18000

# 函数：检查端口是否被占用
check_port() {
    local port=$1
    if lsof -i :$port >/dev/null 2>&1; then
        echo -e "${YELLOW}端口 $port 被占用，进程信息：${NC}"
        lsof -i :$port
        return 1
    fi
    return 0
}

# 函数：杀死占用端口的进程
kill_port() {
    local port=$1
    local pids=$(lsof -t -i :$port 2>/dev/null)
    if [ -n "$pids" ]; then
        echo -e "${YELLOW}正在杀死占用端口 $port 的进程...${NC}"
        for pid in $pids; do
            kill -9 $pid 2>/dev/null && echo -e "${GREEN}已杀死进程 $pid${NC}"
        done
    fi
}

# 函数：启动后端服务
start_backend() {
    echo -e "${GREEN}检查后端端口 $BACKEND_PORT...${NC}"
    if ! check_port $BACKEND_PORT; then
        echo -e "${YELLOW}端口被占用，尝试清理...${NC}"
        kill_port $BACKEND_PORT
        sleep 1
    fi
    
    echo -e "${GREEN}启动后端服务 (端口 $BACKEND_PORT)...${NC}"
    cd backend
    poetry run python main.py &
    BACKEND_PID=$!
    echo $BACKEND_PID > /tmp/mc_l10n_backend.pid
    cd ..
    echo -e "${GREEN}后端服务已启动，PID: $BACKEND_PID${NC}"
}

# 函数：启动前端服务
start_frontend() {
    echo -e "${GREEN}检查前端端口 $FRONTEND_PORT...${NC}"
    if ! check_port $FRONTEND_PORT; then
        echo -e "${YELLOW}端口被占用，尝试清理...${NC}"
        kill_port $FRONTEND_PORT
        sleep 1
    fi
    
    echo -e "${GREEN}启动前端服务 (端口 $FRONTEND_PORT)...${NC}"
    cd frontend
    npm run dev &
    FRONTEND_PID=$!
    echo $FRONTEND_PID > /tmp/mc_l10n_frontend.pid
    cd ..
    echo -e "${GREEN}前端服务已启动，PID: $FRONTEND_PID${NC}"
}

# 函数：停止所有服务
stop_all() {
    echo -e "${YELLOW}停止所有服务...${NC}"
    
    # 停止后端
    if [ -f /tmp/mc_l10n_backend.pid ]; then
        PID=$(cat /tmp/mc_l10n_backend.pid)
        kill -9 $PID 2>/dev/null && echo -e "${GREEN}后端服务已停止${NC}"
        rm /tmp/mc_l10n_backend.pid
    fi
    
    # 停止前端
    if [ -f /tmp/mc_l10n_frontend.pid ]; then
        PID=$(cat /tmp/mc_l10n_frontend.pid)
        kill -9 $PID 2>/dev/null && echo -e "${GREEN}前端服务已停止${NC}"
        rm /tmp/mc_l10n_frontend.pid
    fi
    
    # 清理残留进程
    kill_port $BACKEND_PORT
    kill_port $FRONTEND_PORT
}

# 函数：显示服务状态
status() {
    echo -e "${GREEN}=== 服务状态 ===${NC}"
    echo ""
    echo -e "${YELLOW}前端服务 (端口 $FRONTEND_PORT):${NC}"
    if lsof -i :$FRONTEND_PORT >/dev/null 2>&1; then
        echo -e "${GREEN}✓ 运行中${NC}"
        lsof -i :$FRONTEND_PORT | head -2
    else
        echo -e "${RED}✗ 未运行${NC}"
    fi
    
    echo ""
    echo -e "${YELLOW}后端服务 (端口 $BACKEND_PORT):${NC}"
    if lsof -i :$BACKEND_PORT >/dev/null 2>&1; then
        echo -e "${GREEN}✓ 运行中${NC}"
        lsof -i :$BACKEND_PORT | head -2
    else
        echo -e "${RED}✗ 未运行${NC}"
    fi
}

# 主命令处理
case "$1" in
    start)
        echo -e "${GREEN}启动 MC L10n 服务...${NC}"
        start_backend
        sleep 2
        start_frontend
        echo ""
        echo -e "${GREEN}所有服务已启动！${NC}"
        echo -e "${GREEN}前端: http://localhost:$FRONTEND_PORT${NC}"
        echo -e "${GREEN}API文档: http://localhost:$BACKEND_PORT/docs${NC}"
        ;;
    stop)
        stop_all
        ;;
    restart)
        stop_all
        sleep 2
        $0 start
        ;;
    status)
        status
        ;;
    clean)
        echo -e "${YELLOW}清理所有端口...${NC}"
        kill_port $FRONTEND_PORT
        kill_port $BACKEND_PORT
        echo -e "${GREEN}端口已清理${NC}"
        ;;
    *)
        echo "用法: $0 {start|stop|restart|status|clean}"
        echo ""
        echo "命令说明:"
        echo "  start   - 启动前端和后端服务"
        echo "  stop    - 停止所有服务"
        echo "  restart - 重启所有服务"
        echo "  status  - 显示服务状态"
        echo "  clean   - 清理占用端口的进程"
        exit 1
        ;;
esac