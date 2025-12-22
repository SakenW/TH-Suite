#!/bin/bash

# MC L10n 数据库管理工具启动脚本

# 获取脚本所在目录
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
PROJECT_ROOT="$SCRIPT_DIR/../.."

# 切换到项目根目录
cd "$PROJECT_ROOT"

# 默认参数
PORT=18081
MODE="web"
DB_PATH=""

# 解析命令行参数
while [[ $# -gt 0 ]]; do
    case $1 in
        --port)
            PORT="$2"
            shift 2
            ;;
        --mode)
            MODE="$2"
            shift 2
            ;;
        --db)
            DB_PATH="$2"
            shift 2
            ;;
        -h|--help)
            echo "使用方法: $0 [选项]"
            echo "选项:"
            echo "  --port PORT  指定端口 (默认: 18081)"
            echo "  --mode MODE  运行模式: web 或 cli (默认: web)"
            echo "  --db PATH    数据库文件路径"
            echo "  -h, --help   显示帮助信息"
            exit 0
            ;;
        *)
            echo "未知选项: $1"
            exit 1
            ;;
    esac
done

# 启动数据库管理器
echo "🚀 启动 MC L10n 数据库管理器..."

if [ -n "$DB_PATH" ]; then
    poetry run python "$SCRIPT_DIR/viewer/mc_db_manager.py" --port "$PORT" --mode "$MODE" --db "$DB_PATH"
else
    poetry run python "$SCRIPT_DIR/viewer/mc_db_manager.py" --port "$PORT" --mode "$MODE"
fi