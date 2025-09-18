#!/bin/bash
# TH-Suite 快速设置脚本
# 用于初始化 TH-Suite 开发环境和 Claude Flow 集成

set -euo pipefail

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
PURPLE='\033[0;35m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

# 项目根目录
PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

# 日志函数
log_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

log_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

log_warn() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

log_debug() {
    echo -e "${PURPLE}[DEBUG]${NC} $1"
}

# 显示欢迎信息
show_welcome() {
    cat <<EOF
${CYAN}
╔══════════════════════════════════════════════════════════════╗
║                    TH-Suite v2.0 快速设置                     ║
║              游戏本地化工具 + Claude Flow 集成                ║
╚══════════════════════════════════════════════════════════════╝
${NC}

🎮 TH-Suite 特性:
  • Minecraft MOD 多加载器支持 (Forge/Fabric/Quilt/NeoForge)
  • 安全的 JAR 文件处理和修改
  • Trans-Hub 生态系统深度集成
  • Clean Architecture + Tauri 跨平台

🤖 Claude Flow 集成:
  • 智能代码审查和架构验证
  • 游戏文件安全扫描
  • 性能分析和优化建议
  • 自动化测试生成

EOF
}

# 检查系统要求
check_system_requirements() {
    log_info "检查系统要求..."
    
    local missing_reqs=()
    local warnings=()
    
    # 检查操作系统
    if [[ "$OSTYPE" == "linux-gnu"* ]]; then
        log_success "操作系统: Linux ✓"
    elif [[ "$OSTYPE" == "darwin"* ]]; then
        log_success "操作系统: macOS ✓"
    elif [[ "$OSTYPE" == "cygwin" ]] || [[ "$OSTYPE" == "msys" ]]; then
        log_success "操作系统: Windows ✓"
    else
        warnings+=("未知操作系统: $OSTYPE")
    fi
    
    # 检查基础工具
    if ! command -v git &> /dev/null; then
        missing_reqs+=("git")
    fi
    
    if ! command -v curl &> /dev/null && ! command -v wget &> /dev/null; then
        missing_reqs+=("curl 或 wget")
    fi
    
    if ! command -v jq &> /dev/null; then
        missing_reqs+=("jq")
    fi
    
    # 检查 Node.js 和包管理器
    if command -v node &> /dev/null; then
        local node_version=$(node --version | sed 's/v//')
        local node_major=$(echo $node_version | cut -d. -f1)
        if [ $node_major -ge 18 ]; then
            log_success "Node.js: $node_version ✓"
        else
            missing_reqs+=("Node.js >= 18.0.0 (当前: $node_version)")
        fi
    else
        missing_reqs+=("Node.js >= 18.0.0")
    fi
    
    # 推荐 pnpm
    if command -v pnpm &> /dev/null; then
        log_success "pnpm: $(pnpm --version) ✓"
    elif command -v npm &> /dev/null; then
        log_warn "建议安装 pnpm 以获得更好的性能"
        warnings+=("考虑安装 pnpm: npm install -g pnpm")
    else
        missing_reqs+=("npm 或 pnpm")
    fi
    
    # 检查 Python
    if command -v python3 &> /dev/null; then
        local python_version=$(python3 --version | cut -d' ' -f2)
        local python_major=$(echo $python_version | cut -d. -f1)
        local python_minor=$(echo $python_version | cut -d. -f2)
        if [ $python_major -eq 3 ] && [ $python_minor -ge 9 ]; then
            log_success "Python: $python_version ✓"
        else
            missing_reqs+=("Python >= 3.9.0 (当前: $python_version)")
        fi
    elif command -v python &> /dev/null; then
        local python_version=$(python --version | cut -d' ' -f2)
        if [[ $python_version == 3.* ]]; then
            log_success "Python: $python_version ✓"
        else
            missing_reqs+=("Python 3.9+ (当前: $python_version)")
        fi
    else
        missing_reqs+=("Python >= 3.9.0")
    fi
    
    # 检查 Poetry
    if command -v poetry &> /dev/null; then
        log_success "Poetry: $(poetry --version | cut -d' ' -f3) ✓"
    else
        missing_reqs+=("Poetry")
    fi
    
    # 检查 Rust (Tauri 需要)
    if command -v cargo &> /dev/null; then
        local rust_version=$(rustc --version | cut -d' ' -f2)
        log_success "Rust: $rust_version ✓"
    else
        missing_reqs+=("Rust (用于 Tauri)")
    fi
    
    # 检查推荐工具
    if command -v task &> /dev/null; then
        log_success "Task: $(task --version | head -1) ✓"
    else
        warnings+=("推荐安装 Task 工具以获得更好的开发体验")
    fi
    
    # 输出结果
    if [ ${#missing_reqs[@]} -eq 0 ]; then
        log_success "所有系统要求已满足！"
        
        if [ ${#warnings[@]} -gt 0 ]; then
            log_warn "推荐优化项:"
            for warning in "${warnings[@]}"; do
                echo "  • $warning"
            done
        fi
        
        return 0
    else
        log_error "缺少必需的系统要求:"
        for req in "${missing_reqs[@]}"; do
            echo "  ✗ $req"
        done
        echo ""
        show_installation_help
        return 1
    fi
}

# 显示安装帮助
show_installation_help() {
    cat <<EOF
${YELLOW}📦 安装缺少的依赖:${NC}

${BLUE}Ubuntu/Debian:${NC}
  sudo apt update
  sudo apt install git curl jq
  
  # Node.js (通过 NodeSource)
  curl -fsSL https://deb.nodesource.com/setup_lts.x | sudo -E bash -
  sudo apt-get install -y nodejs
  
  # Python 3.9+
  sudo apt install python3 python3-pip
  
  # Poetry
  curl -sSL https://install.python-poetry.org | python3 -
  
  # Rust
  curl --proto '=https' --tlsv1.2 -sSf https://sh.rustup.rs | sh
  
  # Task (可选)
  sudo snap install task --classic

${BLUE}macOS:${NC}
  # 使用 Homebrew
  brew install git curl jq node python@3.9 poetry rust
  brew install go-task/tap/go-task  # 可选

${BLUE}Windows:${NC}
  # 使用 Chocolatey
  choco install git curl jq nodejs python poetry rust task
  
  # 或使用 Scoop
  scoop install git curl jq nodejs python poetry rust task

${BLUE}通用 (npm/pnpm):${NC}
  npm install -g pnpm  # 推荐的包管理器
  npm install -g @tauri-apps/cli  # Tauri CLI

EOF
}

# 安装依赖
install_dependencies() {
    log_info "安装项目依赖..."
    
    cd "$PROJECT_ROOT"
    
    # 安装 Node.js 依赖
    if command -v pnpm &> /dev/null; then
        log_info "使用 pnpm 安装前端依赖..."
        pnpm install
    else
        log_info "使用 npm 安装前端依赖..."
        npm install
    fi
    
    # 安装 Python 依赖
    if [ -f "pyproject.toml" ]; then
        log_info "使用 Poetry 安装 Python 依赖..."
        poetry install
    fi
    
    # 安装应用特定依赖
    if [ -d "apps/mc_l10n/frontend" ]; then
        cd "apps/mc_l10n/frontend"
        log_info "安装 MC L10n 前端依赖..."
        if command -v pnpm &> /dev/null; then
            pnpm install
        else
            npm install
        fi
        cd "$PROJECT_ROOT"
    fi
    
    log_success "依赖安装完成！"
}

# 安装 Claude Flow
install_claude_flow() {
    log_info "安装 Claude Flow..."
    
    if command -v npx &> /dev/null && npx claude-flow@alpha --version &> /dev/null; then
        log_success "Claude Flow 已安装: $(npx claude-flow@alpha --version)"
        return 0
    fi
    
    log_info "正在安装 Claude Flow Alpha..."
    npm install -g claude-flow@alpha
    
    if npx claude-flow@alpha --version &> /dev/null; then
        log_success "Claude Flow 安装成功: $(npx claude-flow@alpha --version)"
    else
        log_error "Claude Flow 安装失败"
        return 1
    fi
}

# 初始化 Claude Flow
init_claude_flow() {
    log_info "初始化 TH-Suite Claude Flow 配置..."
    
    cd "$PROJECT_ROOT"
    
    # 检查配置文件是否存在
    if [ -f "claude-flow.config.json" ]; then
        log_success "Claude Flow 配置文件已存在"
    else
        log_warn "Claude Flow 配置文件不存在，请运行完整设置"
        return 1
    fi
    
    # 初始化 Swarm
    if npx claude-flow@alpha swarm init \
        --topology hierarchical \
        --memory-type persistent \
        --max-agents 8 \
        --auto-scale true \
        --project-type game-localization; then
        log_success "Claude Flow Swarm 初始化成功"
    else
        log_warn "Claude Flow Swarm 初始化失败，可以稍后手动初始化"
    fi
}

# 验证安装
verify_installation() {
    log_info "验证 TH-Suite 安装..."
    
    local issues=()
    
    cd "$PROJECT_ROOT"
    
    # 检查关键文件
    local required_files=(
        "package.json"
        "pyproject.toml" 
        "Taskfile.yml"
        "claude-flow.config.json"
        "apps/mc_l10n/backend/main.py"
        "apps/mc_l10n/frontend/src-tauri/tauri.conf.json"
    )
    
    for file in "${required_files[@]}"; do
        if [ -f "$file" ]; then
            log_success "✓ $file"
        else
            log_warn "✗ $file (缺失)"
            issues+=("$file")
        fi
    done
    
    # 检查依赖安装
    if [ -d "node_modules" ]; then
        log_success "✓ Node.js 依赖已安装"
    else
        log_warn "✗ Node.js 依赖未安装"
        issues+=("node_modules")
    fi
    
    if command -v poetry &> /dev/null && poetry check &> /dev/null; then
        log_success "✓ Poetry 依赖配置正确"
    else
        log_warn "✗ Poetry 依赖配置问题"
        issues+=("poetry dependencies")
    fi
    
    # 检查构建能力
    if command -v task &> /dev/null; then
        log_info "测试 Task 命令..."
        if task --list-all &> /dev/null; then
            log_success "✓ Task 工具工作正常"
        else
            log_warn "✗ Task 工具配置问题"
            issues+=("task configuration")
        fi
    fi
    
    # 检查 Claude Flow
    if command -v npx &> /dev/null && npx claude-flow@alpha --version &> /dev/null; then
        log_success "✓ Claude Flow 可用"
    else
        log_warn "✗ Claude Flow 不可用"
        issues+=("claude-flow")
    fi
    
    # 输出结果
    if [ ${#issues[@]} -eq 0 ]; then
        log_success "🎉 TH-Suite 安装验证通过！"
        return 0
    else
        log_warn "⚠️  发现 ${#issues[@]} 个问题:"
        for issue in "${issues[@]}"; do
            echo "  • $issue"
        done
        return 1
    fi
}

# 显示使用指南
show_usage_guide() {
    cat <<EOF

${GREEN}🎉 TH-Suite 安装完成！${NC}

${CYAN}常用开发命令:${NC}

${BLUE}使用 Task 工具 (推荐):${NC}
  task dev:mc                 # 启动 MC L10n 完整开发环境
  task test                   # 运行所有测试
  task lint                   # 代码质量检查
  task build:mc               # 构建 MC L10n 应用

${BLUE}使用 npm scripts:${NC}
  npm run dev:mc_l10n         # 启动 MC L10n 前端
  npm run start:mc_l10n       # 启动 MC L10n 后端
  npm run claude-flow:init    # 初始化 Claude Flow
  npm run claude-flow:review  # 运行代码审查

${BLUE}Claude Flow 集成:${NC}
  ./scripts/claude-flow-helpers.sh help    # 显示 Claude Flow 帮助
  ./scripts/claude-flow-helpers.sh init    # 初始化游戏本地化环境
  ./scripts/claude-flow-helpers.sh review  # 运行 TH-Suite 专用代码审查
  ./scripts/claude-flow-helpers.sh security-scan  # 游戏文件安全扫描

${BLUE}开发服务器地址:${NC}
  MC L10n 后端:  http://localhost:18000 (API 文档: /docs)
  MC L10n 前端:  http://localhost:18001 (开发模式)
  Tauri 桌面应用: 自动启动

${BLUE}重要文档:${NC}
  README.md                   # 项目总览
  CLAUDE.md                   # Claude Code 集成指南
  docs/architecture/          # 架构文档
  apps/mc_l10n/backend/       # 后端 Clean Architecture
  apps/mc_l10n/frontend/      # Tauri + React 前端

${YELLOW}下一步建议:${NC}
  1. 运行 'task dev:mc' 启动开发环境
  2. 浏览 API 文档: http://localhost:18000/docs  
  3. 尝试 Claude Flow 代码审查功能
  4. 查看示例项目和测试用例

${PURPLE}获取帮助:${NC}
  • GitHub Issues: https://github.com/Saken/th-suite/issues
  • 开发文档: 查看 CLAUDE.md 获取详细指南
  • Claude Flow: ./scripts/claude-flow-helpers.sh help

祝开发愉快！🚀

EOF
}

# 主函数
main() {
    local mode="${1:-full}"
    
    case "$mode" in
        "check")
            show_welcome
            check_system_requirements
            ;;
        "deps")
            install_dependencies
            ;;
        "claude-flow")
            install_claude_flow
            init_claude_flow
            ;;
        "verify")
            verify_installation
            ;;
        "full"|"")
            show_welcome
            
            if ! check_system_requirements; then
                log_error "系统要求检查失败，请先安装缺少的依赖"
                exit 1
            fi
            
            install_dependencies
            install_claude_flow
            init_claude_flow
            
            if verify_installation; then
                show_usage_guide
            else
                log_warn "安装验证发现问题，但大部分功能应该可以正常使用"
                show_usage_guide
            fi
            ;;
        "help"|"--help"|"-h")
            cat <<EOF
TH-Suite 快速设置脚本

用法: $0 [模式]

模式:
  full        完整安装 (默认)
  check       仅检查系统要求
  deps        仅安装项目依赖
  claude-flow 仅安装和配置 Claude Flow
  verify      验证安装状态
  help        显示此帮助信息

示例:
  $0                    # 完整安装
  $0 check              # 检查系统要求
  $0 claude-flow        # 安装 Claude Flow
  $0 verify             # 验证安装
EOF
            ;;
        *)
            log_error "未知模式: $mode"
            echo "使用 '$0 help' 查看可用模式"
            exit 1
            ;;
    esac
}

# 错误处理
trap 'log_error "安装脚本执行失败，行号: $LINENO"' ERR

# 运行主函数
main "$@"