# TH-Suite 开发者指南

本文档为 TH-Suite 项目的开发者提供详细的开发指南，涵盖环境搭建、开发流程、代码规范等内容。

## 📋 环境准备

### 必需软件

| 软件 | 最低版本 | 推荐版本 | 用途 |
|------|----------|----------|------|
| **Python** | 3.12 | 3.12+ | 后端开发 |
| **Node.js** | 18.0 | 20.0+ | 前端开发 |
| **Rust** | 1.77 | 最新稳定版 | Tauri 构建 |
| **Git** | 2.40 | 最新版 | 版本控制 |

### 包管理器

| 包管理器 | 用途 | 安装方式 |
|----------|------|----------|
| **Poetry** | Python 依赖管理 | `curl -sSL https://install.python-poetry.org \| python3 -` |
| **pnpm** | Node.js 包管理 | `npm install -g pnpm` |
| **Task** | 任务运行器 | [官方安装指南](https://taskfile.dev/installation/) |

### IDE 配置

#### VS Code (推荐)

安装以下扩展：

```json
{
  "recommendations": [
    "ms-python.python",
    "ms-python.black-formatter", 
    "ms-python.mypy-type-checker",
    "charliermarsh.ruff",
    "bradlc.vscode-tailwindcss",
    "esbenp.prettier-vscode",
    "ms-vscode.vscode-typescript-next",
    "tauri-apps.tauri-vscode"
  ]
}
```

配置文件 (`.vscode/settings.json`)：

```json
{
  "python.defaultInterpreterPath": "./.venv/bin/python",
  "python.formatting.provider": "black",
  "python.linting.enabled": true,
  "python.linting.mypyEnabled": true,
  "python.linting.ruffEnabled": true,
  "typescript.preferences.importModuleSpecifier": "relative",
  "editor.formatOnSave": true,
  "editor.codeActionsOnSave": {
    "source.fixAll.eslint": "explicit",
    "source.fixAll.ruff": "explicit"
  }
}
```

## 🏗️ 项目设置

### 1. 克隆仓库

```bash
git clone https://github.com/your-username/th-suite.git
cd th-suite
```

### 2. 环境配置

```bash
# 复制环境变量模板
cp .env.example .env

# 编辑配置文件
vim .env
```

环境变量说明：

```bash
# 开发模式
DEBUG=true
LOG_LEVEL=DEBUG

# 数据库配置
DATABASE_URL=sqlite:///data/dev.db
DATABASE_ENCRYPTION_KEY=your-secret-key

# Trans-Hub 集成
TRANS_HUB_API_URL=https://api.trans-hub.net
TRANS_HUB_API_KEY=your-api-key

# 端口配置
MC_L10N_BACKEND_PORT=18000
MC_L10N_FRONTEND_PORT=18001
RW_STUDIO_BACKEND_PORT=8002
```

### 3. 依赖安装

#### 使用 Task (推荐)

```bash
task install
```

#### 手动安装

```bash
# Python 依赖
poetry install

# Node.js 依赖  
cd apps/mc_l10n/frontend && pnpm install
cd ../../../

# 验证安装
poetry run python --version
pnpm --version
```

### 4. 数据库初始化

```bash
# 创建数据库
task db:init

# 或手动执行
cd apps/mc_l10n/backend
poetry run python -c "
from container import get_container
container = get_container()
container.initialize()
"
```

## 🚀 开发工作流

### 启动开发服务

```bash
# 启动所有服务
task dev

# 或单独启动
task dev:mc         # MC L10n 全栈
task dev:mc:backend # 仅后端
task dev:mc:frontend # 仅前端
task dev:rw         # RW Studio
```

### 开发服务器地址

| 服务 | 地址 | 说明 |
|------|------|------|
| **MC L10n Backend** | http://localhost:18000 | FastAPI 后端 |
| **MC L10n Frontend** | http://localhost:18001 | Vite 开发服务器 |
| **MC L10n Desktop** | - | Tauri 桌面应用 |
| **RW Studio Backend** | http://localhost:8002 | FastAPI 后端 |
| **API 文档** | http://localhost:18000/docs | OpenAPI 文档 |

### 代码质量检查

```bash
# 运行所有检查
task lint

# 单独检查
task lint:python    # Python 代码检查
task lint:frontend  # 前端代码检查
task format         # 自动格式化
task type-check     # 类型检查
```

### 测试

```bash
# 运行所有测试
task test

# 分类测试
task test:python    # Python 单元测试
task test:frontend  # 前端测试
task test:e2e       # 端到端测试

# 测试覆盖率
task test:coverage
```

## 📁 项目结构详解

### 后端目录结构

```
apps/mc_l10n/backend/
├── src/                        # 源代码
│   ├── domain/                 # 领域层
│   │   ├── models/            # 聚合根和实体
│   │   │   ├── mod.py         # Mod 聚合根
│   │   │   └── translation_project.py
│   │   ├── value_objects.py   # 值对象
│   │   ├── events.py          # 领域事件
│   │   ├── services/          # 领域服务
│   │   └── repositories.py    # 仓储接口
│   ├── application/           # 应用层
│   │   ├── services/          # 应用服务
│   │   ├── commands/          # 命令对象
│   │   ├── queries/           # 查询对象
│   │   └── dto.py             # DTO
│   ├── adapters/              # 适配器层
│   │   ├── api/               # REST API
│   │   └── cli/               # 命令行
│   ├── infrastructure/        # 基础设施层
│   │   ├── persistence/       # 数据持久化
│   │   ├── parsers/           # 文件解析
│   │   └── external/          # 外部集成
│   ├── facade/                # 门面层
│   │   ├── mc_l10n_facade.py  # 主门面
│   │   ├── client_sdk.py      # 客户端SDK
│   │   └── sdk_examples.py    # 使用示例
│   └── container.py           # 依赖注入容器
├── tests/                     # 测试代码
│   ├── unit/                  # 单元测试
│   ├── integration/           # 集成测试
│   └── fixtures/              # 测试数据
├── data/                      # 数据目录
├── logs/                      # 日志目录
├── main.py                    # 应用入口
├── pyproject.toml             # Poetry 配置
└── README.md                  # 文档
```

### 前端目录结构

```
apps/mc_l10n/frontend/
├── src/                       # 源代码
│   ├── components/            # React 组件
│   │   ├── common/           # 通用组件
│   │   ├── business/         # 业务组件
│   │   └── layout/           # 布局组件
│   ├── pages/                # 页面组件
│   ├── hooks/                # 自定义 Hooks
│   ├── services/             # 服务层
│   │   ├── domain/           # 领域服务
│   │   ├── infrastructure/   # 基础设施服务
│   │   └── container/        # 服务容器
│   ├── stores/               # 状态管理
│   ├── config/               # 配置
│   ├── types/                # TypeScript 类型
│   ├── utils/                # 工具函数
│   └── assets/               # 静态资源
├── src-tauri/                # Tauri 配置
│   ├── src/                  # Rust 代码
│   ├── icons/                # 应用图标
│   └── tauri.conf.json       # Tauri 配置
├── public/                   # 公共资源
├── dist/                     # 构建输出
├── package.json              # npm 配置
├── vite.config.ts           # Vite 配置
└── tailwind.config.js       # Tailwind 配置
```

## 🎯 开发规范

### Git 工作流

#### 分支命名规范

```bash
# 功能分支
feature/add-translation-editor
feature/improve-scan-performance

# 修复分支
fix/translation-key-validation
fix/memory-leak-in-scanner

# 文档分支
docs/update-api-documentation
docs/add-development-guide

# 重构分支
refactor/simplify-domain-models
refactor/extract-common-services
```

#### 提交信息规范

使用 [Conventional Commits](https://conventionalcommits.org/) 格式：

```bash
# 功能
feat(scan): add batch processing for large modpacks
feat(ui): implement real-time progress indicator

# 修复
fix(parser): handle malformed JSON files gracefully
fix(api): resolve memory leak in WebSocket connections

# 文档
docs(readme): update installation instructions
docs(api): add examples for scan endpoints

# 样式
style(frontend): apply consistent component spacing
style(backend): format code with ruff

# 重构
refactor(domain): extract translation aggregate
refactor(infra): simplify repository implementations

# 测试
test(scan): add unit tests for mod scanner
test(integration): add API endpoint tests

# 构建
build(deps): upgrade fastapi to 0.115.0
build(ci): add automated testing pipeline
```

### 代码规范

#### Python 代码规范

```python
# 使用类型注解
def scan_mod(mod_path: Path) -> ScanResult:
    """扫描单个MOD文件
    
    Args:
        mod_path: MOD文件路径
        
    Returns:
        扫描结果对象
        
    Raises:
        ScanError: 扫描失败时抛出
    """
    pass

# 使用数据类
@dataclass
class ModInfo:
    """MOD信息"""
    mod_id: str
    name: str
    version: str
    description: Optional[str] = None
    
# 异步函数
async def process_translation(
    text: str, 
    source_lang: LanguageCode, 
    target_lang: LanguageCode
) -> TranslationResult:
    """处理翻译请求"""
    pass
```

#### TypeScript 代码规范

```typescript
// 使用接口定义类型
interface ScanProgress {
  taskId: string;
  status: ScanStatus;
  progress: number;
  currentStep: string;
  errorMessage?: string;
}

// 使用函数式组件和 Hooks
const ScanProgressIndicator: React.FC<ScanProgressProps> = ({ 
  taskId 
}) => {
  const { data: progress, isLoading } = useScanProgress(taskId);
  
  return (
    <div className="scan-progress">
      {/* 组件内容 */}
    </div>
  );
};

// 使用自定义 Hook 封装逻辑
const useScanProgress = (taskId: string) => {
  return useQuery({
    queryKey: ['scan', 'progress', taskId],
    queryFn: () => scanService.getProgress(taskId),
    refetchInterval: 1000,
  });
};
```

### 测试规范

#### 单元测试

```python
# tests/unit/domain/test_mod.py
class TestMod:
    """MOD 聚合根单元测试"""
    
    def test_create_mod_with_valid_data(self):
        """测试创建有效MOD"""
        mod = Mod.create(
            name="Test Mod",
            version="1.0.0",
            file_path=Path("/test/mod.jar")
        )
        
        assert mod.name == "Test Mod"
        assert mod.version == "1.0.0"
        assert mod.scan_status == ScanStatus.PENDING
    
    def test_scan_mod_updates_status(self):
        """测试扫描更新状态"""
        mod = Mod.create("Test Mod", "1.0.0", Path("/test/mod.jar"))
        
        mod.start_scan()
        assert mod.scan_status == ScanStatus.SCANNING
        
        mod.complete_scan(language_files=[], segments_count=100)
        assert mod.scan_status == ScanStatus.COMPLETED
```

#### 集成测试

```python
# tests/integration/test_scan_api.py
class TestScanAPI:
    """扫描API集成测试"""
    
    async def test_start_scan_returns_task_id(
        self, 
        client: TestClient,
        sample_mod_path: Path
    ):
        """测试启动扫描返回任务ID"""
        response = client.post(
            "/api/scan/start",
            json={"path": str(sample_mod_path)}
        )
        
        assert response.status_code == 200
        data = response.json()
        assert "task_id" in data
        assert len(data["task_id"]) == 36  # UUID 长度
```

### 文档规范

#### API 文档

```python
@router.post("/scan/start", response_model=ScanStartResponse)
async def start_scan(
    request: ScanRequest,
    scan_service: ScanApplicationService = Depends(get_scan_service)
) -> ScanStartResponse:
    """启动MOD扫描任务
    
    ## 描述
    开始扫描指定路径的MOD或整合包，返回任务ID用于跟踪进度。
    
    ## 参数
    - **path**: 要扫描的文件或目录路径
    - **recursive**: 是否递归扫描子目录 (默认: true)
    - **extract_archives**: 是否提取压缩文件 (默认: true)
    
    ## 响应
    - **task_id**: 扫描任务唯一标识符
    - **message**: 操作结果消息
    
    ## 错误
    - **400**: 路径无效或不存在
    - **500**: 服务器内部错误
    
    ## 示例
    ```python
    response = requests.post('/api/scan/start', json={
        'path': '/path/to/mod.jar',
        'recursive': True
    })
    task_id = response.json()['task_id']
    ```
    """
    pass
```

## 🔧 调试和故障排除

### 常见问题

#### 1. 端口被占用

```bash
# 查看端口占用
lsof -i :18000

# 杀死进程
kill -9 <PID>

# 或使用不同端口
export MC_L10N_BACKEND_PORT=18010
```

#### 2. Poetry 依赖冲突

```bash
# 清理缓存
poetry cache clear pypi --all

# 重建环境
rm -rf .venv
poetry install
```

#### 3. 前端构建错误

```bash
# 清理 node_modules
rm -rf node_modules pnpm-lock.yaml

# 重新安装
pnpm install

# 清理 Vite 缓存
rm -rf .vite
```

#### 4. 数据库锁定

```bash
# 检查数据库文件权限
ls -la data/

# 停止所有相关进程
pkill -f "mc_l10n"

# 重建数据库
rm data/dev.db
task db:init
```

### 调试技巧

#### 后端调试

```python
# 添加调试日志
import structlog
logger = structlog.get_logger()

async def debug_function():
    logger.debug(
        "Function called",
        param1="value1",
        param2="value2"
    )
```

#### 前端调试

```typescript
// 使用 React DevTools
const DebugComponent: React.FC = () => {
  const debug = useDebugValue("Component state");
  
  useEffect(() => {
    console.log("Component mounted", { debug });
  }, [debug]);
  
  return <div>Debug Component</div>;
};
```

### 性能分析

#### 后端性能

```bash
# 安装性能分析工具
poetry add --group dev py-spy

# 分析运行中的进程
py-spy record -o profile.svg -d 30 -p <PID>
```

#### 前端性能

```typescript
// 使用 React Profiler
import { Profiler } from 'react';

const onRenderCallback = (id, phase, actualDuration) => {
  console.log('Render performance', {
    id,
    phase,
    actualDuration
  });
};

<Profiler id="ScanPage" onRender={onRenderCallback}>
  <ScanPage />
</Profiler>
```

## 📦 构建和部署

### 开发构建

```bash
# 构建所有组件
task build

# 单独构建
task build:mc:backend
task build:mc:frontend
```

### 生产构建

```bash
# 设置生产环境
export NODE_ENV=production
export DEBUG=false

# 构建生产版本
task build:prod

# 构建 Docker 镜像
task docker:build
```

### 部署检查清单

- [ ] 环境变量配置正确
- [ ] 数据库迁移已执行
- [ ] 静态资源已优化
- [ ] 日志级别设置为 INFO
- [ ] 健康检查端点可访问
- [ ] 安全配置已启用
- [ ] 备份策略已制定

## 🎯 贡献流程

### 1. 创建 Issue

在开始开发前，请先创建或认领一个 Issue，说明要解决的问题或添加的功能。

### 2. 创建分支

```bash
git checkout -b feature/your-feature-name
```

### 3. 开发和测试

```bash
# 开发过程中持续运行
task dev
task lint
task test
```

### 4. 提交代码

```bash
git add .
git commit -m "feat(component): add new feature"
git push origin feature/your-feature-name
```

### 5. 创建 Pull Request

提供详细的 PR 描述，包括：
- 解决的问题或添加的功能
- 测试覆盖情况
- 破坏性更改（如有）
- 相关的 Issue 链接

### 6. 代码审查

PR 需要至少一名维护者的审查通过才能合并。

### 7. 合并和部署

合并后，CI/CD 流水线会自动构建和部署。

## 📚 学习资源

### 架构模式
- [六边形架构](https://alistair.cockburn.us/hexagonal-architecture/)
- [领域驱动设计](https://www.domainlanguage.com/ddd/)
- [CQRS 模式](https://docs.microsoft.com/en-us/azure/architecture/patterns/cqrs)

### 技术文档
- [FastAPI 官方文档](https://fastapi.tiangolo.com/)
- [React 官方文档](https://react.dev/)
- [Tauri 官方文档](https://tauri.app/)
- [TypeScript 官方文档](https://www.typescriptlang.org/)

### 代码质量
- [Python 类型注解](https://docs.python.org/3/library/typing.html)
- [ESLint 规则](https://eslint.org/docs/rules/)
- [Prettier 配置](https://prettier.io/docs/en/configuration.html)

---

欢迎加入 TH-Suite 开发者社区！如有问题，请在 GitHub Issues 中提出。