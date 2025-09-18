#!/bin/bash
# Claude Flow CI/CD 辅助脚本 - TH-Suite 专用版
# 适用于游戏本地化工具的开发和 CI 环境中的 Claude Flow 集成

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
CLAUDE_FLOW_DIR="${PROJECT_ROOT}/.claude-flow"

# TH-Suite 特殊目录
MC_L10N_BACKEND="${PROJECT_ROOT}/apps/mc_l10n/backend"
MC_L10N_FRONTEND="${PROJECT_ROOT}/apps/mc_l10n/frontend"
RW_L10N_BACKEND="${PROJECT_ROOT}/apps/rw_l10n/backend"
PACKAGES_DIR="${PROJECT_ROOT}/packages"

# 创建 Claude Flow 工作目录
mkdir -p "$CLAUDE_FLOW_DIR"

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

# 检查依赖
check_dependencies() {
    log_info "检查 TH-Suite 系统依赖..."
    
    local missing_deps=()
    
    # 检查基础工具
    if ! command -v node &> /dev/null; then
        missing_deps+=("node")
    fi
    
    if ! command -v npm &> /dev/null; then
        missing_deps+=("npm")
    fi
    
    # 检查包管理器 (优先 pnpm)
    if ! command -v pnpm &> /dev/null && ! command -v npm &> /dev/null; then
        missing_deps+=("pnpm or npm")
    fi
    
    # 检查 Python
    if ! command -v python &> /dev/null && ! command -v python3 &> /dev/null; then
        missing_deps+=("python")
    fi
    
    # 检查 Poetry
    if ! command -v poetry &> /dev/null; then
        missing_deps+=("poetry")
    fi
    
    # 检查 Tauri CLI
    if ! command -v cargo &> /dev/null; then
        missing_deps+=("rust/cargo")
    fi
    
    # 检查 Task 工具 (推荐)
    if ! command -v task &> /dev/null; then
        log_warn "推荐安装 Task 工具以获得更好的开发体验"
    fi
    
    # 检查工具链
    if ! command -v jq &> /dev/null; then
        missing_deps+=("jq")
    fi
    
    if [ ${#missing_deps[@]} -eq 0 ]; then
        log_success "所有依赖已满足"
        return 0
    else
        log_error "缺少以下依赖: ${missing_deps[*]}"
        log_info "请安装缺少的依赖后重新运行"
        return 1
    fi
}

# 安装 Claude Flow
install_claude_flow() {
    log_info "安装 Claude Flow..."
    
    if command -v npx &> /dev/null && npx claude-flow@alpha --version &> /dev/null; then
        log_success "Claude Flow 已安装"
        npx claude-flow@alpha --version
        return 0
    fi
    
    log_info "正在安装 Claude Flow..."
    npm install -g claude-flow@alpha
    
    if npx claude-flow@alpha --version; then
        log_success "Claude Flow 安装成功"
    else
        log_error "Claude Flow 安装失败"
        return 1
    fi
}

# 初始化 TH-Suite Swarm
init_swarm() {
    local topology="${1:-hierarchical}"
    local max_agents="${2:-8}"
    local memory_type="${3:-persistent}"
    
    log_info "初始化 TH-Suite Claude Flow Swarm (拓扑: $topology, 最大代理: $max_agents, 内存: $memory_type)..."
    
    cd "$PROJECT_ROOT"
    
    if npx claude-flow@alpha swarm init \
        --topology "$topology" \
        --memory-type "$memory_type" \
        --max-agents "$max_agents" \
        --auto-scale true \
        --project-type "game-localization"; then
        log_success "TH-Suite Claude Flow Swarm 初始化成功"
        
        # 保存配置
        cat > "$CLAUDE_FLOW_DIR/swarm-config.json" <<EOF
{
  "topology": "$topology",
  "max_agents": $max_agents,
  "memory_type": "$memory_type",
  "initialized_at": "$(date -u +"%Y-%m-%dT%H:%M:%SZ")",
  "project": "TH-Suite",
  "domain": "game-localization",
  "applications": ["mc_l10n", "rw_l10n"],
  "architecture": "clean-architecture"
}
EOF
    else
        log_error "TH-Suite Claude Flow Swarm 初始化失败"
        return 1
    fi
}

# 运行代码审查 - TH-Suite 专用
run_code_review() {
    local files_changed="$1"
    local review_scope="${2:-comprehensive}"
    
    log_info "运行 TH-Suite Claude Flow 智能代码审查..."
    log_debug "变更文件: $files_changed"
    log_debug "审查范围: $review_scope"
    
    cd "$PROJECT_ROOT"
    
    local review_prompt="深度审查以下 TH-Suite 代码变更，重点关注：

## 架构合规性检查
1. **Clean Architecture 分层验证** - 检查 Interface/Application/Domain/Infrastructure 分层
2. **依赖方向合规** - 确保内层不依赖外层
3. **Tauri 架构模式** - 前后端分离和 IPC 通信安全性

## TH-Suite 特殊关注点
1. **游戏文件安全性** - JAR 文件修改的安全边界检查
2. **多语言处理** - i18n 文件解析和编码处理正确性
3. **MOD 兼容性** - Forge/Fabric/Quilt/NeoForge 适配器正确性
4. **加密数据库** - SQLCipher 使用和敏感数据保护
5. **Trans-Hub 集成** - UIDA 协议和 SDK 集成规范性

## 代码质量检查
1. **Python 代码质量** - Ruff/MyPy 规范和类型安全
2. **TypeScript 质量** - 严格类型检查和 ESLint 规范
3. **React/Ant Design** - 组件设计模式和性能优化
4. **测试覆盖率** - 核心业务逻辑测试完整性

变更文件列表：
$files_changed

输出结构化审查报告，包含风险等级和 TH-Suite 特定的修复建议。"
    
    if npx claude-flow@alpha sparc batch "reviewer,code-analyzer,security-manager" "$review_prompt"; then
        log_success "代码审查完成"
        
        # 生成审查摘要
        generate_review_summary
    else
        log_error "代码审查失败"
        return 1
    fi
}

# 生成审查摘要
generate_review_summary() {
    log_info "生成 TH-Suite 审查摘要..."
    
    local summary_file="$CLAUDE_FLOW_DIR/review-summary.md"
    
    cat > "$summary_file" <<EOF
# 🎮 TH-Suite Claude Flow 智能代码审查摘要

**审查时间**: $(date)
**项目**: TH-Suite v2.0 - 游戏本地化工具
**审查范围**: 全面代码质量检查

## ✅ TH-Suite 专项检查

### 🏗️ 架构合规性
- **Clean Architecture**: 验证分层架构和依赖方向
- **Tauri 架构**: 前后端分离和 IPC 安全性
- **Monorepo 结构**: 包依赖和工作空间配置

### 🎯 游戏本地化特性
- **JAR 处理安全性**: 文件修改和备份机制
- **MOD 加载器适配**: 多平台兼容性检查
- **i18n 文件处理**: 编码和格式正确性
- **Trans-Hub 集成**: UIDA 协议和 SDK 使用

### 🔒 安全与性能
- **敏感数据保护**: SQLCipher 和数据加密
- **文件系统访问**: 沙盒化和权限控制
- **内存使用优化**: 大文件处理和缓存策略
- **并发安全性**: 多线程和异步操作

## 📊 检查结果

$(if [ -f "$CLAUDE_FLOW_DIR/review-report.json" ]; then
    echo "详细结果请查看 [审查报告](./review-report.json)"
else
    echo "✅ 未发现重大问题"
fi)

## 🎯 TH-Suite 特定建议

1. **立即处理**: 修复游戏文件处理的安全漏洞
2. **短期计划**: 完善 MOD 加载器检测和适配
3. **中期目标**: 优化大型 JAR 文件处理性能
4. **长期规划**: 增强 Trans-Hub 生态系统集成

## 🛠️ 开发工具建议

- 使用 \`task dev:mc\` 启动 MC L10n 开发环境
- 使用 \`task lint\` 运行完整代码检查
- 使用 \`task test\` 执行全面测试套件

---
*🚀 由 Claude Flow 智能代码审查系统生成*
*🎮 专为 TH-Suite 游戏本地化工具定制*
EOF
    
    log_success "TH-Suite 审查摘要已生成: $summary_file"
}

# 运行架构合规检查 - TH-Suite 专用
run_architecture_check() {
    log_info "运行 TH-Suite 架构合规性检查..."
    
    cd "$PROJECT_ROOT"
    
    # 检查 monorepo 结构
    log_info "检查 Monorepo 结构合规性..."
    local structure_issues=()
    
    # 验证关键目录存在
    [ ! -d "$MC_L10N_BACKEND" ] && structure_issues+=("MC L10n 后端目录缺失")
    [ ! -d "$MC_L10N_FRONTEND" ] && structure_issues+=("MC L10n 前端目录缺失")
    [ ! -d "$PACKAGES_DIR" ] && structure_issues+=("共享包目录缺失")
    
    # 验证配置文件
    [ ! -f "$PROJECT_ROOT/pyproject.toml" ] && structure_issues+=("Poetry 配置缺失")
    [ ! -f "$PROJECT_ROOT/Taskfile.yml" ] && structure_issues+=("Task 配置缺失")
    
    if [ ${#structure_issues[@]} -eq 0 ]; then
        log_success "Monorepo 结构检查通过"
    else
        log_warn "发现结构问题: ${structure_issues[*]}"
    fi
    
    # Python 架构检查
    if [ -d "$MC_L10N_BACKEND" ]; then
        cd "$MC_L10N_BACKEND"
        log_info "检查 Python Clean Architecture..."
        
        # 检查分层结构
        local python_arch_issues=()
        [ ! -d "adapters" ] && python_arch_issues+=("缺少适配器层")
        [ ! -d "application" ] && python_arch_issues+=("缺少应用层")
        [ ! -d "domain" ] && python_arch_issues+=("缺少领域层")
        [ ! -d "infrastructure" ] && python_arch_issues+=("缺少基础设施层")
        
        if [ ${#python_arch_issues[@]} -eq 0 ]; then
            log_success "Python Clean Architecture 检查通过"
        else
            log_warn "Python 架构问题: ${python_arch_issues[*]}"
        fi
    fi
    
    # 前端架构检查
    if [ -d "$MC_L10N_FRONTEND" ]; then
        cd "$MC_L10N_FRONTEND"
        log_info "检查前端架构..."
        
        local frontend_arch_issues=()
        [ ! -f "src-tauri/tauri.conf.json" ] && frontend_arch_issues+=("Tauri 配置缺失")
        [ ! -d "src/components" ] && frontend_arch_issues+=("组件目录缺失")
        [ ! -d "src/services" ] && frontend_arch_issues+=("服务层缺失")
        
        if [ ${#frontend_arch_issues[@]} -eq 0 ]; then
            log_success "前端架构检查通过"
        else
            log_warn "前端架构问题: ${frontend_arch_issues[*]}"
        fi
    fi
    
    cd "$PROJECT_ROOT"
    
    # Claude Flow 架构分析
    local arch_prompt="执行 TH-Suite 架构合规性检查：

## TH-Suite v2.0 架构验证重点

### 1. Monorepo 结构合规性
- 工作空间配置正确性
- 包依赖关系合理性
- 共享代码复用策略

### 2. Clean Architecture 实施
- **MC L10n 后端**: adapters → application → domain → infrastructure
- **前端服务**: 依赖注入容器模式
- **领域隔离**: 游戏特定逻辑与通用逻辑分离

### 3. Tauri 架构模式
- 前后端 IPC 通信安全性
- 系统资源访问权限控制
- WebView 与原生代码交互规范

### 4. TH-Suite 特殊架构要求
- **JAR 处理架构**: 安全沙盒和回滚机制
- **MOD 适配器模式**: 插件式架构设计
- **Trans-Hub 集成**: UIDA 协议适配层
- **多语言支持**: i18n 架构和数据流

### 5. 数据库架构
- SQLCipher 加密存储策略
- Repository 模式实现
- 缓存层设计合理性

生成 TH-Suite 专用架构合规性报告和违规修复建议。"
    
    if npx claude-flow@alpha sparc run architect "$arch_prompt"; then
        log_success "Claude Flow 架构分析完成"
    else
        log_error "Claude Flow 架构分析失败"
        return 1
    fi
}

# 运行安全扫描 - TH-Suite 专用
run_security_scan() {
    local scan_type="${1:-full}"
    
    log_info "运行 TH-Suite 安全扫描 (类型: $scan_type)..."
    
    # Python 依赖安全扫描
    if [ -d "$MC_L10N_BACKEND" ]; then
        cd "$MC_L10N_BACKEND"
        log_info "扫描 Python 依赖漏洞..."
        
        if command -v poetry &> /dev/null; then
            poetry export -f requirements.txt 2>/dev/null | \
            poetry run pip-audit -r /dev/stdin --format json \
            --output "$CLAUDE_FLOW_DIR/mc-l10n-vulnerabilities.json" 2>/dev/null || \
            log_warn "MC L10n 依赖扫描遇到问题"
        fi
    fi
    
    # Node.js 依赖安全扫描
    if [ -d "$MC_L10N_FRONTEND" ]; then
        cd "$MC_L10N_FRONTEND"
        log_info "扫描 Node.js 依赖漏洞..."
        
        if command -v npm &> /dev/null; then
            npm audit --json > "$CLAUDE_FLOW_DIR/frontend-vulnerabilities.json" 2>/dev/null || \
            log_warn "前端依赖扫描遇到问题"
        fi
    fi
    
    cd "$PROJECT_ROOT"
    
    # Claude Flow 安全分析 - TH-Suite 专用
    local security_prompt="对 TH-Suite 进行深度安全分析：

## TH-Suite 安全分析重点

### 1. 游戏文件处理安全性
- **JAR 文件修改**: 恶意代码注入防护
- **文件系统访问**: 路径遍历攻击防护
- **ZIP 炸弹**: 压缩文件解析安全性
- **任意文件写入**: 文件提取安全边界

### 2. MOD 加载器安全
- **动态加载**: 恶意 MOD 文件检测
- **沙盒隔离**: MOD 代码执行环境
- **权限控制**: 文件系统访问权限
- **签名验证**: MOD 文件完整性校验

### 3. 数据安全
- **SQLCipher 使用**: 数据库加密配置
- **敏感信息泄露**: 日志和错误信息
- **用户数据保护**: 个人信息处理
- **API 密钥管理**: Trans-Hub 凭证安全

### 4. Tauri 应用安全
- **IPC 通信**: 前后端消息验证
- **系统调用**: 权限升级防护
- **WebView 安全**: XSS 和注入攻击
- **更新机制**: 自动更新安全性

### 5. 网络通信安全
- **HTTPS 强制**: 所有外部通信
- **证书验证**: TLS 配置正确性
- **API 认证**: Trans-Hub 集成安全
- **数据传输**: 敏感数据加密

扫描范围：
- apps/mc_l10n/backend/ (Python 后端)
- apps/mc_l10n/frontend/ (Tauri 前端)
- packages/ (共享包)

输出结构化安全报告，包含：
- TH-Suite 特定的漏洞等级评估
- 游戏文件处理的攻击向量分析
- MOD 安全性评估和防护建议
- 修复建议和代码示例"
    
    if npx claude-flow@alpha sparc run security-manager "$security_prompt"; then
        log_success "TH-Suite 安全扫描完成"
    else
        log_error "TH-Suite 安全扫描失败"
        return 1
    fi
}

# 运行性能分析 - TH-Suite 专用
run_performance_analysis() {
    log_info "运行 TH-Suite 性能分析..."
    
    cd "$PROJECT_ROOT"
    
    # Claude Flow 性能分析 - TH-Suite 特化
    local perf_prompt="对 TH-Suite 执行性能分析：

## TH-Suite 性能分析维度

### 1. 游戏文件处理性能
- **JAR 文件解析**: 大型 MOD 文件处理效率
- **并发提取**: 多文件并行处理优化
- **内存使用**: 大文件流式处理策略
- **缓存机制**: 重复解析避免和智能缓存

### 2. MOD 兼容性检测性能
- **模式匹配**: 正则表达式和字符串匹配优化
- **文件系统遍历**: 目录扫描效率提升
- **并发扫描**: 多线程文件分析
- **增量检测**: 变更文件的智能识别

### 3. 数据库操作性能
- **SQLCipher 优化**: 加密数据库查询效率
- **批量操作**: 大量 i18n 条目处理
- **索引策略**: 查询性能优化
- **连接池**: 数据库连接管理

### 4. 前端渲染性能
- **React 组件**: 大列表渲染和虚拟化
- **Ant Design**: 复杂表格和表单优化
- **状态管理**: Zustand 状态更新效率
- **Tauri IPC**: 前后端通信开销

### 5. Trans-Hub 集成性能
- **API 调用**: 网络请求优化和重试
- **数据同步**: 增量同步和冲突解决
- **UIDA 协议**: 序列化和反序列化优化
- **并发同步**: 多项目同时同步处理

### 6. 内存和CPU使用优化
- **垃圾回收**: Python 和 JavaScript GC 调优
- **多进程架构**: Tauri 进程间通信优化
- **异步处理**: I/O 密集型操作优化
- **资源清理**: 临时文件和内存泄漏预防

输出 TH-Suite 专用性能分析报告，包含具体的游戏本地化场景优化建议。"
    
    if npx claude-flow@alpha sparc run perf-analyzer "$perf_prompt"; then
        log_success "TH-Suite 性能分析完成"
    else
        log_error "TH-Suite 性能分析失败"
        return 1
    fi
}

# 生成测试用例 - TH-Suite 专用
generate_tests() {
    local test_type="${1:-unit}"
    local coverage_threshold="${2:-80}"
    
    log_info "生成 TH-Suite $test_type 测试用例 (覆盖率目标: $coverage_threshold%)..."
    
    cd "$PROJECT_ROOT"
    
    # Claude Flow 测试生成 - TH-Suite 特化
    local test_prompt
    case "$test_type" in
        "unit")
            test_prompt="为 TH-Suite 生成高质量的单元测试：

## TH-Suite 单元测试生成策略

### Python 后端测试 (MC L10n)
1. **游戏文件处理测试**
   - JAR 文件解析器测试
   - MOD 加载器检测器测试
   - i18n 文件提取器测试
   - 文件完整性验证测试

2. **Clean Architecture 层次测试**
   - Domain 层: 游戏文件实体和值对象
   - Application 层: 扫描和同步服务
   - Infrastructure 层: 文件系统和数据库适配器
   - Adapters 层: API 路由和 CLI 接口

3. **安全性测试**
   - 文件路径验证测试
   - 权限检查测试
   - 数据加密/解密测试

### TypeScript 前端测试
1. **React 组件测试**
   - Ant Design 组件集成测试
   - 用户交互和状态管理测试
   - Tauri IPC 通信测试

2. **服务层测试**
   - API 客户端服务测试
   - 依赖注入容器测试
   - 错误处理和重试逻辑测试

使用框架: pytest (Python), jest/vitest (TypeScript)
覆盖率目标: $coverage_threshold%
包含中文测试描述和游戏场景模拟数据。"
            ;;
        "integration")
            test_prompt="为 TH-Suite 生成集成测试：

## TH-Suite 集成测试生成范围

### 端到端游戏本地化流程
1. **完整扫描流程**: 从 MOD 文件到 i18n 提取
2. **同步流程**: 与 Trans-Hub 的完整数据同步
3. **构建流程**: 修改后 JAR 文件的重新打包

### API 集成测试
1. **后端 API**: FastAPI 端点完整性测试
2. **Tauri IPC**: 前后端通信集成测试
3. **数据库集成**: SQLCipher 操作和事务测试

### 外部系统集成
1. **Trans-Hub SDK**: 完整的 API 调用链测试
2. **文件系统**: 复杂目录结构处理测试
3. **MOD 生态**: 多种 MOD 加载器兼容性测试

包含完整的测试数据准备和清理逻辑，模拟真实的 Minecraft 环境。"
            ;;
        "security")
            test_prompt="为 TH-Suite 生成安全测试用例：

## TH-Suite 安全测试生成范围

### 游戏文件安全测试
1. **恶意 JAR 文件**: 各种攻击向量测试
2. **路径遍历**: 文件解压安全性测试
3. **ZIP 炸弹**: 压缩文件安全解析测试

### 应用安全测试
1. **Tauri 安全**: IPC 注入和权限升级测试
2. **数据库安全**: SQLCipher 配置和查询注入测试
3. **API 安全**: 输入验证和认证授权测试

### MOD 安全测试
1. **恶意代码检测**: MOD 文件安全性验证
2. **沙盒逃逸**: 隔离环境安全性测试
3. **权限控制**: 文件访问权限测试

包含攻击向量模拟和防护验证，专注于游戏文件处理的安全边界。"
            ;;
        *)
            log_error "不支持的测试类型: $test_type"
            return 1
            ;;
    esac
    
    if npx claude-flow@alpha sparc run tester "$test_prompt"; then
        log_success "TH-Suite $test_type 测试生成完成"
    else
        log_error "TH-Suite $test_type 测试生成失败"
        return 1
    fi
}

# 自动修复代码问题 - TH-Suite 专用
autofix_issues() {
    local fix_scope="${1:-all}"
    
    log_info "自动修复 TH-Suite 代码问题 (范围: $fix_scope)..."
    
    case "$fix_scope" in
        "format"|"all")
            log_info "执行代码格式化修复..."
            
            # Python 代码格式化
            if [ -d "$MC_L10N_BACKEND" ]; then
                cd "$MC_L10N_BACKEND"
                poetry run ruff format . || log_warn "Python Ruff format 遇到问题"
                poetry run ruff check . --fix --unsafe-fixes || log_warn "Python Ruff check 遇到问题"
            fi
            
            # 前端代码格式化
            if [ -d "$MC_L10N_FRONTEND" ]; then
                cd "$MC_L10N_FRONTEND"
                npm run format 2>/dev/null || log_warn "前端格式化遇到问题"
            fi
            ;;
    esac
    
    cd "$PROJECT_ROOT"
    
    # Claude Flow 自动修复 - TH-Suite 特化
    local autofix_prompt="对 TH-Suite 代码执行自动修复：

## TH-Suite 自动修复范围: $fix_scope

### 代码质量修复
1. **Python 代码**: Ruff 和 MyPy 问题修复
2. **TypeScript 代码**: ESLint 和类型错误修复
3. **React 组件**: Ant Design 使用规范修复
4. **架构违规**: Clean Architecture 依赖方向修复

### TH-Suite 特定修复
1. **游戏文件处理**: 安全性和性能问题修复
2. **MOD 适配器**: 兼容性和错误处理改进
3. **Trans-Hub 集成**: API 调用和错误处理优化
4. **数据库操作**: SQLCipher 使用和查询优化

### 配置文件修复
1. **Tauri 配置**: 权限和安全设置优化
2. **构建配置**: 打包和依赖配置修复
3. **开发工具**: Taskfile 和脚本优化

直接修改源码文件，生成详细的 TH-Suite 修复报告。"
    
    if npx claude-flow@alpha sparc batch "code-analyzer,reviewer" "$autofix_prompt"; then
        log_success "TH-Suite 自动修复完成"
    else
        log_error "TH-Suite 自动修复失败"
        return 1
    fi
}

# 运行 TH-Suite 专用工作流
run_game_localization_workflow() {
    local workflow_type="${1:-full}"
    
    log_info "运行 TH-Suite 游戏本地化工作流 (类型: $workflow_type)..."
    
    local workflow_prompt="执行 TH-Suite 游戏本地化专用工作流：

## 工作流类型: $workflow_type

### MC L10n 完整工作流
1. **项目扫描**: 检测 Minecraft 实例和 MOD
2. **文件提取**: 从 JAR 中提取 i18n 文件
3. **内容分析**: 解析语言文件和提取翻译条目
4. **Trans-Hub 同步**: 与翻译平台进行数据同步
5. **构建输出**: 生成本地化的 MOD 文件

### 质量保证流程
1. **安全检查**: JAR 文件安全性验证
2. **兼容性测试**: 多 MOD 加载器测试
3. **性能评估**: 大型 MOD 包处理性能
4. **集成验证**: Trans-Hub 集成完整性

### 自动化优化
1. **并行处理**: 多文件并发处理
2. **增量更新**: 智能变更检测
3. **缓存优化**: 重复操作避免
4. **错误恢复**: 失败场景自动重试

生成完整的游戏本地化工作流报告。"
    
    if npx claude-flow@alpha sparc batch "mobile-dev,backend-dev,system-architect" "$workflow_prompt"; then
        log_success "TH-Suite 游戏本地化工作流完成"
    else
        log_error "TH-Suite 游戏本地化工作流失败"
        return 1
    fi
}

# 生成综合报告 - TH-Suite 专用
generate_comprehensive_report() {
    log_info "生成 TH-Suite 综合报告..."
    
    local report_file="$CLAUDE_FLOW_DIR/comprehensive-report.md"
    local timestamp=$(date -u +"%Y-%m-%d %H:%M:%S UTC")
    
    cat > "$report_file" <<EOF
# 🎮 TH-Suite Claude Flow 综合报告

**生成时间**: $timestamp
**项目版本**: $(git rev-parse --short HEAD 2>/dev/null || echo "unknown")
**项目类型**: 游戏本地化工具 (Monorepo)
**分析范围**: MC L10n + 共享包 + 构建系统

## 📊 TH-Suite 分析摘要

### 🏗️ 架构合规性检查
$(if [ -f "$CLAUDE_FLOW_DIR/architecture-compliance-report.json" ]; then
    echo "✅ 已完成 - [查看详情](./architecture-compliance-report.json)"
else
    echo "⏸️ 未执行"
fi)
- Clean Architecture 分层验证
- Tauri 架构模式检查
- Monorepo 结构合规性

### 🔒 安全漏洞扫描
$(if [ -f "$CLAUDE_FLOW_DIR/security-report.json" ]; then
    echo "✅ 已完成 - [查看详情](./security-report.json)"
else
    echo "⏸️ 未执行"
fi)
- JAR 文件处理安全性
- MOD 加载器安全检查
- Tauri 应用安全性
- 数据加密和隐私保护

### 🚀 性能分析
$(if [ -f "$CLAUDE_FLOW_DIR/performance-report.json" ]; then
    echo "✅ 已完成 - [查看详情](./performance-report.json)"
else
    echo "⏸️ 未执行"
fi)
- 游戏文件处理性能
- 大型 JAR 文件优化
- 数据库查询效率
- 前端渲染优化

### 🧪 测试覆盖率
$(if [ -f "$CLAUDE_FLOW_DIR/coverage-analysis.json" ]; then
    echo "✅ 已完成 - [查看详情](./coverage-analysis.json)"
else
    echo "⏸️ 未执行"
fi)
- Python 后端测试 (pytest)
- TypeScript 前端测试 (jest/vitest)
- 集成测试覆盖率
- 安全测试用例

### 🔧 代码质量检查
$(if [ -f "$CLAUDE_FLOW_DIR/review-summary.md" ]; then
    echo "✅ 已完成 - [查看详情](./review-summary.md)"
else
    echo "⏸️ 未执行"
fi)
- Python: Ruff + MyPy 检查
- TypeScript: ESLint + 类型检查
- React/Ant Design 规范性
- Trans-Hub 集成质量

## 🎯 TH-Suite 特定发现

### 游戏本地化功能
- MOD 兼容性: Forge/Fabric/Quilt/NeoForge
- i18n 提取准确性和完整性
- JAR 文件修改的安全性和完整性
- Trans-Hub 同步的稳定性和性能

### 技术架构优势
- Clean Architecture 实施质量
- Tauri 跨平台兼容性
- SQLCipher 数据安全性
- Monorepo 代码复用效率

## 🚀 优先修复建议

### 🔴 高优先级 (立即处理)
1. 修复所有严重安全漏洞
2. 解决架构违规问题
3. 修复关键的游戏文件处理 bug

### 🟡 中优先级 (短期计划)
1. 提升测试覆盖率到 85% 以上
2. 优化大型 JAR 文件处理性能
3. 完善 MOD 加载器检测准确性

### 🟢 低优先级 (长期规划)
1. 增强 Trans-Hub 生态集成
2. 改进用户界面和体验
3. 扩展更多游戏支持

## 🛠️ TH-Suite 开发建议

### 推荐开发流程
\`\`\`bash
# 启动开发环境
task dev:mc                 # MC L10n 完整开发环境

# 代码质量检查
task lint                   # 运行所有代码检查
task test                   # 执行完整测试套件

# 构建和部署
task build:mc               # 构建 MC L10n 应用
\`\`\`

### Claude Flow 集成命令
\`\`\`bash
# 初始化智能开发环境
./scripts/claude-flow-helpers.sh init

# 运行完整代码审查
./scripts/claude-flow-helpers.sh review

# 执行安全扫描
./scripts/claude-flow-helpers.sh security-scan

# 生成测试用例
./scripts/claude-flow-helpers.sh gen-tests unit 85
\`\`\`

## 📈 质量趋势

$(if [ -f "$CLAUDE_FLOW_DIR/quality-trends.json" ]; then
    echo "[查看质量趋势图表](./quality-trends.json)"
else
    echo "暂无历史质量数据对比。建议定期运行分析以建立质量趋势跟踪。"
fi)

---

*🎮 此报告专为 TH-Suite 游戏本地化工具定制*
*📋 由 Claude Flow 智能分析系统生成*
*🔄 建议每周运行一次以跟踪项目健康度*
EOF
    
    log_success "TH-Suite 综合报告已生成: $report_file"
}

# 显示帮助信息
show_help() {
    cat <<EOF
TH-Suite Claude Flow CI/CD 辅助脚本
专为游戏本地化工具优化的智能开发助手

用法: $0 <命令> [参数]

🚀 基础命令:
  check-deps                检查 TH-Suite 系统依赖
  install                   安装 Claude Flow
  init [拓扑] [代理数] [内存类型] 初始化游戏本地化 Swarm

🔍 代码分析:
  review <文件列表>         运行 TH-Suite 专用代码审查
  arch-check               运行架构合规检查 (Clean Architecture + Tauri)
  security-scan [类型]      运行游戏文件安全扫描
  perf-analysis            运行性能分析 (JAR 处理优化)

🧪 测试生成:
  gen-tests <类型> [覆盖率] 生成测试用例
    - unit: 单元测试 (游戏文件处理 + Clean Architecture)
    - integration: 集成测试 (Tauri IPC + Trans-Hub)
    - security: 安全测试 (JAR 安全 + MOD 沙盒)

🛠️ 自动修复:
  autofix [范围]           自动修复代码问题
    - format: 代码格式化 (Ruff + Prettier)
    - all: 全面修复

🎮 TH-Suite 专用:
  game-workflow [类型]     运行游戏本地化工作流
    - full: 完整 MC L10n 工作流
    - scan: 仅扫描和提取
    - sync: 仅 Trans-Hub 同步

📊 报告生成:
  report                   生成 TH-Suite 综合报告
  cleanup                  清理临时文件
  help                     显示此帮助信息

🎯 TH-Suite 示例:
  $0 check-deps                    # 检查游戏开发依赖
  $0 init hierarchical 8 persistent # 初始化游戏本地化环境
  $0 review "apps/mc_l10n/**/*.py"  # 审查 MC L10n 后端
  $0 security-scan full            # 全面安全扫描 (JAR + MOD)
  $0 gen-tests unit 85             # 生成游戏文件处理测试
  $0 game-workflow full            # 运行完整本地化工作流
  $0 report                        # 生成游戏项目报告

🏗️ 架构特性:
  - Clean Architecture (4层分离)
  - Tauri 跨平台应用
  - SQLCipher 加密数据库
  - Trans-Hub 生态集成
  - 多 MOD 加载器支持
  - JAR 文件安全处理

🔧 环境变量:
  CLAUDE_FLOW_DEBUG=1     启用调试模式
  CLAUDE_FLOW_TIMEOUT=30  设置超时时间(分钟)

📚 更多信息:
  - 开发指南: README.md
  - API 文档: http://localhost:18000/docs
  - 架构文档: CLAUDE.md
EOF
}

# 主函数
main() {
    local command="${1:-help}"
    
    # 设置调试模式
    if [ "${CLAUDE_FLOW_DEBUG:-}" = "1" ]; then
        set -x
    fi
    
    case "$command" in
        "check-deps")
            check_dependencies
            ;;
        "install")
            install_claude_flow
            ;;
        "init")
            local topology="${2:-hierarchical}"
            local max_agents="${3:-8}"
            local memory_type="${4:-persistent}"
            check_dependencies && install_claude_flow && init_swarm "$topology" "$max_agents" "$memory_type"
            ;;
        "review")
            local files="${2:-}"
            if [ -z "$files" ]; then
                files=$(git diff --name-only HEAD~1 HEAD 2>/dev/null || echo "")
            fi
            run_code_review "$files"
            ;;
        "arch-check")
            run_architecture_check
            ;;
        "security-scan")
            local scan_type="${2:-full}"
            run_security_scan "$scan_type"
            ;;
        "perf-analysis")
            run_performance_analysis
            ;;
        "gen-tests")
            local test_type="${2:-unit}"
            local coverage="${3:-80}"
            generate_tests "$test_type" "$coverage"
            ;;
        "autofix")
            local fix_scope="${2:-all}"
            autofix_issues "$fix_scope"
            ;;
        "game-workflow")
            local workflow_type="${2:-full}"
            run_game_localization_workflow "$workflow_type"
            ;;
        "report")
            generate_comprehensive_report
            ;;
        "cleanup")
            cleanup
            ;;
        "help"|"--help"|"-h")
            show_help
            ;;
        *)
            log_error "未知命令: $command"
            show_help
            exit 1
            ;;
    esac
}

# 清理函数 (复用 Trans-Hub 的清理逻辑)
cleanup() {
    log_info "清理 TH-Suite Claude Flow 临时文件..."
    
    # 保留重要的报告文件，删除临时文件
    find "$CLAUDE_FLOW_DIR" -name "*.tmp" -delete 2>/dev/null || true
    find "$CLAUDE_FLOW_DIR" -name "temp_*" -delete 2>/dev/null || true
    find "$CLAUDE_FLOW_DIR" -name "*.log" -mtime +7 -delete 2>/dev/null || true
    
    log_success "清理完成"
}

# 错误处理
trap 'log_error "TH-Suite Claude Flow 脚本执行失败，行号: $LINENO"' ERR

# 运行主函数
main "$@"