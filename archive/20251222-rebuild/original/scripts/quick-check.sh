#!/bin/bash
# TransHub Suite 快速代码质量检查脚本
# 用于开发过程中的快速验证

set -e

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# 项目根目录
PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$PROJECT_ROOT"

echo -e "${BLUE}🚀 TransHub Suite 快速质量检查${NC}"
echo "=================================================="

# 检查是否在正确的目录
if [[ ! -f "pyproject.toml" ]]; then
    echo -e "${RED}❌ 错误：请在项目根目录运行此脚本${NC}"
    exit 1
fi

# 函数：运行命令并检查结果
run_check() {
    local name="$1"
    local cmd="$2"
    local allow_failure="${3:-false}"
    
    echo -e "\n${BLUE}🔍 $name${NC}"
    echo "执行: $cmd"
    
    if eval "$cmd"; then
        echo -e "${GREEN}✅ $name 通过${NC}"
        return 0
    else
        if [[ "$allow_failure" == "true" ]]; then
            echo -e "${YELLOW}⚠️ $name 失败（允许）${NC}"
            return 0
        else
            echo -e "${RED}❌ $name 失败${NC}"
            return 1
        fi
    fi
}

# 检查Python环境
echo -e "\n${BLUE}📋 环境检查${NC}"
if command -v poetry &> /dev/null; then
    echo "✅ Poetry 已安装: $(poetry --version)"
else
    echo -e "${RED}❌ Poetry 未安装${NC}"
    exit 1
fi

# Python代码检查
echo -e "\n${BLUE}🐍 Python 代码检查${NC}"

# 安装依赖（如果需要）
if [[ ! -d ".venv" ]]; then
    echo "📦 安装Python依赖..."
    poetry install --no-interaction
fi

# Ruff检查和修复
run_check "Ruff 代码检查" "poetry run ruff check . --fix" true
run_check "Ruff 格式化" "poetry run ruff format ." true

# MyPy类型检查（允许失败）
run_check "MyPy 类型检查" "poetry run mypy packages apps --ignore-missing-imports" true

# 前端检查（如果存在）
FRONTEND_PATH="apps/mc_l10n/frontend"
if [[ -d "$FRONTEND_PATH" ]]; then
    echo -e "\n${BLUE}🌐 前端代码检查${NC}"
    
    cd "$FRONTEND_PATH"
    
    # 检查pnpm
    if command -v pnpm &> /dev/null; then
        echo "✅ pnpm 已安装: $(pnpm --version)"
        
        # 安装依赖（如果需要）
        if [[ ! -d "node_modules" ]]; then
            echo "📦 安装前端依赖..."
            pnpm install
        fi
        
        # 前端格式化和检查
        run_check "Prettier 格式化" "pnpm format" true
        run_check "ESLint 检查" "pnpm lint:fix" true
        
        cd "$PROJECT_ROOT"
    else
        echo -e "${RED}❌ pnpm 未安装，跳过前端检查${NC}"
        cd "$PROJECT_ROOT"
    fi
fi

# 架构快速检查
echo -e "\n${BLUE}🏗️ 架构快速检查${NC}"

# 检查大文件
echo "检查大文件（>500行）..."
large_files=$(find . -name "*.py" -not -path "./.*" -not -path "./tests/*" -exec wc -l {} + | awk '$1 > 500 {print $2 " (" $1 " lines)"}' | head -5)

if [[ -n "$large_files" ]]; then
    echo -e "${YELLOW}⚠️ 发现大文件:${NC}"
    echo "$large_files"
else
    echo -e "${GREEN}✅ 没有发现大文件${NC}"
fi

# 检查TODO/FIXME
echo "检查待办事项..."
todo_count=$(grep -r "TODO\|FIXME\|HACK" --include="*.py" --include="*.ts" --include="*.tsx" . | wc -l)
if [[ $todo_count -gt 0 ]]; then
    echo -e "${YELLOW}⚠️ 发现 $todo_count 个TODO/FIXME标记${NC}"
else
    echo -e "${GREEN}✅ 没有发现TODO/FIXME标记${NC}"
fi

# 最终总结
echo -e "\n${BLUE}=================================================="
echo -e "🎯 快速检查完成${NC}"
echo -e "\n💡 提示:"
echo "- 运行 'python scripts/quality-gate.py' 进行完整检查"
echo "- 运行 'task dev:mc' 启动开发服务器"
echo "- 查看 'TODO.md' 了解项目进度"

echo -e "\n${GREEN}🎉 快速检查通过！可以继续开发。${NC}"