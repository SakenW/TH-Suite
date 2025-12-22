#!/bin/bash
# MC L10n 后端启动脚本
# 自动清理旧进程并启动新实例

# 设置颜色
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

echo -e "${GREEN}==================================${NC}"
echo -e "${GREEN}   MC L10n Backend Starter${NC}"
echo -e "${GREEN}==================================${NC}"

# 默认参数
KILL_ALL=false
PORT=18000
HOST="127.0.0.1"

# 解析命令行参数
while [[ $# -gt 0 ]]; do
    case $1 in
        --kill-all)
            KILL_ALL=true
            shift
            ;;
        --port)
            PORT="$2"
            shift 2
            ;;
        --host)
            HOST="$2"
            shift 2
            ;;
        --help)
            echo "使用方法: $0 [选项]"
            echo ""
            echo "选项:"
            echo "  --kill-all    终止所有现有的Python main.py进程"
            echo "  --port PORT   指定端口 (默认: 18000)"
            echo "  --host HOST   指定主机 (默认: 127.0.0.1)"
            echo "  --help        显示此帮助信息"
            exit 0
            ;;
        *)
            echo -e "${RED}未知参数: $1${NC}"
            echo "使用 --help 查看帮助"
            exit 1
            ;;
    esac
done

# 清理旧进程
if [ "$KILL_ALL" = true ]; then
    echo -e "${YELLOW}正在清理所有旧进程...${NC}"
    pkill -f "python.*main.py" 2>/dev/null
    sleep 1
    echo -e "${GREEN}旧进程已清理${NC}"
fi

# 检查是否已有进程在运行
if [ -f "mc_l10n.pid" ]; then
    OLD_PID=$(cat mc_l10n.pid)
    if ps -p $OLD_PID > /dev/null 2>&1; then
        echo -e "${YELLOW}发现运行中的进程 (PID: $OLD_PID)${NC}"
        echo -e "${YELLOW}正在终止...${NC}"
        kill $OLD_PID 2>/dev/null
        sleep 2
    fi
fi

# 设置环境变量
export HOST=$HOST
export PORT=$PORT

echo -e "${GREEN}启动配置:${NC}"
echo -e "  主机: ${HOST}"
echo -e "  端口: ${PORT}"
echo ""

# 启动应用
echo -e "${GREEN}正在启动 MC L10n 后端服务...${NC}"
if [ "$KILL_ALL" = true ]; then
    poetry run python main.py --kill-all
else
    poetry run python main.py
fi