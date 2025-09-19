# TH-Suite v2.0 系统架构文档

## 概览

TH-Suite v2.0 是完全重构的 Core-First 专业适配器，专为 Trans-Hub 生态系统设计的游戏本地化工具。通过投影适配器系统与 Trans-Hub Core 深度集成，删除了 15,000+ 行重复基础设施代码。

## 架构原则

### Core-First 架构
- **投影适配器系统**: Minecraft ↔ UIDA 双向转换，数据一致性保证
- **零冗余代码**: 删除 15,000+ 行重复基础设施，专注 Minecraft 特定逻辑
- **深度集成**: 与 Trans-Hub Core 原生集成，无缝数据流转

### Clean Architecture
采用六边形架构（端口和适配器模式）：
- **领域层**: 核心业务逻辑，独立于外部依赖
- **应用层**: 用例协调，领域服务编排
- **接口层**: API 控制器，UI 组件
- **基础设施层**: 数据存储，外部服务集成

## 系统组件

### 1. 前端架构

```
frontend/
├── src/
│   ├── components/           # React 组件
│   │   ├── common/          # 通用组件
│   │   ├── ui/              # UI 基础组件（基于 Ant Design）
│   │   ├── TopStatusBar.tsx # 顶部状态条
│   │   └── ProjectScan.tsx  # 项目扫描组件
│   ├── layouts/             # 布局组件
│   │   └── MainLayout.tsx   # 主布局
│   ├── pages/               # 页面组件
│   │   ├── WelcomePage.tsx  # 欢迎页
│   │   ├── ScanPage.tsx     # 扫描中心
│   │   ├── SyncPage.tsx     # 同步中心
│   │   └── SettingsPage.tsx # 设置页
│   ├── services/            # 业务逻辑服务
│   │   ├── api/             # API 服务
│   │   ├── domain/          # 领域服务
│   │   └── container/       # 依赖注入容器
│   ├── stores/              # 状态管理（Zustand）
│   ├── theme/               # 主题系统
│   │   └── minecraft.ts     # Minecraft 轻装饰主题
│   └── hooks/               # 自定义 React Hooks
```

#### 技术栈
- **UI 框架**: React 18 + TypeScript
- **UI 组件库**: Ant Design 5.x (已废弃 Material-UI)
- **状态管理**: Zustand + React Context
- **路由**: React Router v6
- **桌面端**: Tauri v1.x
- **样式**: Tailwind CSS + Ant Design Token System
- **主题**: Minecraft 轻装饰主题

#### 设计原则
1. **人话化界面**: 避免专业术语，使用通俗易懂的表达
2. **安全默认**: 默认旁路产物，破坏性操作双确认
3. **Minecraft 轻装饰**: 像素化元素仅作装饰，不影响可用性
4. **响应式设计**: 支持不同屏幕尺寸

### 2. 后端架构

```
backend/
├── api/                     # API 接口层
│   ├── routes/             # 路由定义
│   │   ├── project_routes.py
│   │   ├── scan_routes.py
│   │   ├── translation_routes.py
│   │   └── sync_routes.py
│   └── middleware/         # 中间件
│       └── compression_middleware.py
├── application/            # 应用层
│   ├── services/          # 应用服务
│   │   ├── scan_application_service.py
│   │   └── sync_application_service.py
│   ├── commands/          # 命令对象
│   └── queries/           # 查询对象
├── domain/                # 领域层
│   ├── models/           # 领域实体
│   │   ├── project.py
│   │   ├── translation_entry.py
│   │   └── scan_result.py
│   └── services/         # 领域服务
├── infrastructure/       # 基础设施层
│   ├── persistence/      # 数据持久化
│   │   ├── repositories/
│   │   └── sqlite_connection.py
│   ├── services/         # 基础设施服务
│   │   ├── minecraft_scanner.py
│   │   ├── jar_processor.py
│   │   ├── compression_service.py
│   │   └── sync_protocol_service.py
│   └── parsers/          # 文件解析器
│       ├── json_parser.py
│       └── properties_parser.py
└── core/                 # 核心配置
    ├── di_container.py   # 依赖注入容器
    └── config.py         # 配置管理
```

#### 技术栈
- **Web 框架**: FastAPI 0.115+
- **数据库**: SQLite/SQLCipher（加密存储）
- **ORM**: SQLAlchemy 2.0+
- **异步处理**: AsyncIO + Uvicorn
- **日志**: Structlog（结构化日志）
- **序列化**: Pydantic v2
- **压缩**: Zstandard（智能压缩）
- **哈希**: BLAKE3（高性能哈希）

## 核心功能模块

### 1. 项目管理系统

#### 功能特性
- **多 MOD 加载器支持**: 智能识别 Forge、Fabric、Quilt、NeoForge
- **项目类型**: 支持 MOD 项目和资源包项目
- **多语言配置**: 灵活的源语言和目标语言设置
- **项目模板**: 预设常用项目配置

#### 数据模型
```python
@dataclass
class Project:
    id: str
    name: str
    description: str
    project_type: ProjectType  # MOD, RESOURCEPACK
    project_path: Path
    source_language: str
    target_languages: List[str]
    mod_loader: Optional[ModLoader]  # FORGE, FABRIC, QUILT, NEOFORGE
    created_at: datetime
    updated_at: datetime
    status: ProjectStatus
```

### 2. 智能扫描系统

#### 扫描类型
- **完整扫描**: 扫描整个项目目录
- **增量扫描**: 仅扫描变更文件（基于文件指纹）
- **快速扫描**: 仅扫描语言文件
- **深度扫描**: 包含 JAR 文件内容提取

#### 文件识别
```python
class FileTypeDetector:
    """文件类型检测器"""
    
    LANGUAGE_FILE_PATTERNS = {
        "minecraft_lang": r"assets/.+/lang/.+\.json$",
        "minecraft_properties": r"assets/.+/lang/.+\.properties$",
        "mod_info": r"META-INF/mods\.toml$|mcmod\.info$",
        "fabric_mod": r"fabric\.mod\.json$"
    }
    
    JAR_FILE_EXTENSIONS = {".jar", ".zip"}
    RESOURCE_PACK_INDICATORS = {"pack.mcmeta", "pack.png"}
```

#### 性能优化
- **并发扫描**: 多线程文件系统遍历
- **指纹缓存**: BLAKE3 哈希缓存，避免重复处理
- **内存管理**: 流式处理大文件，恒定内存使用
- **进度追踪**: 实时进度报告和取消支持

### 3. 高级 JAR 处理系统

#### JAR 操作功能
- **安全提取**: 临时目录隔离，防止路径遍历攻击
- **内容修改**: 在内存中修改 JAR 内容
- **备份管理**: 自动备份原始文件
- **冲突解决**: 智能处理文件冲突
- **回滚机制**: 支持操作回滚

#### 安全措施
```python
class JarProcessor:
    """JAR 文件处理器"""
    
    SECURITY_CHECKS = {
        "path_traversal": True,      # 路径遍历检查
        "file_size_limit": True,     # 文件大小限制
        "extraction_timeout": True,   # 提取超时
        "malicious_paths": True      # 恶意路径检查
    }
    
    MAX_EXTRACTION_SIZE = 500 * 1024 * 1024  # 500MB
    EXTRACTION_TIMEOUT = 300  # 5分钟
```

### 4. 投影适配器系统

#### UIDA 映射
投影适配器负责 Minecraft 数据格式与 Trans-Hub UIDA（Universal Internationalization Data Adapter）格式的双向转换。

```python
class MinecraftProjectionAdapter:
    """Minecraft 投影适配器"""
    
    def to_uida(self, minecraft_data: MinecraftTranslationData) -> UIDAData:
        """转换 Minecraft 数据到 UIDA 格式"""
        return UIDAData(
            entries=[
                UIDAEntry(
                    key=entry.key,
                    source_text=entry.source_text,
                    target_text=entry.target_text,
                    context=self._extract_context(entry),
                    metadata=self._build_metadata(entry)
                )
                for entry in minecraft_data.entries
            ],
            metadata=self._build_project_metadata(minecraft_data)
        )
    
    def from_uida(self, uida_data: UIDAData) -> MinecraftTranslationData:
        """转换 UIDA 数据到 Minecraft 格式"""
        return MinecraftTranslationData(
            entries=[
                MinecraftTranslationEntry(
                    key=entry.key,
                    source_text=entry.source_text,
                    target_text=entry.target_text,
                    namespace=self._extract_namespace(entry.key),
                    category=self._categorize_key(entry.key)
                )
                for entry in uida_data.entries
            ]
        )
```

#### 数据一致性保证
- **双向验证**: 转换后数据完整性验证
- **类型映射**: 精确的数据类型映射
- **元数据保持**: 保持 Minecraft 特定元数据
- **错误恢复**: 转换失败时的回退机制

### 5. 智能压缩系统

#### Zstd 压缩
- **动态压缩级别**: Fast/Balanced/High/Max
- **Locale 字典**: 按语言训练专用字典，中文压缩率提升 20-30%
- **流式压缩**: 支持大文件流式压缩
- **压缩统计**: 实时压缩率和性能监控

```python
class ZstdCompressionService:
    """Zstd 智能压缩服务"""
    
    COMPRESSION_LEVELS = {
        "fast": 1,
        "balanced": 6,
        "high": 15,
        "max": 22
    }
    
    LOCALE_DICTIONARIES = {
        "zh_cn": "chinese_dict.zstd",
        "ja_jp": "japanese_dict.zstd",
        "ko_kr": "korean_dict.zstd"
    }
```

### 6. 同步协议系统

#### 同步类型
- **推送同步**: 本地数据推送到 Trans-Hub
- **拉取同步**: 从 Trans-Hub 拉取更新
- **双向同步**: 同时推送和拉取，智能冲突解决
- **增量同步**: 基于时间戳的增量数据同步

#### 冲突解决策略
```python
class ConflictResolutionStrategy(Enum):
    ACCEPT_LOCAL = "accept_local"      # 接受本地版本
    ACCEPT_REMOTE = "accept_remote"    # 接受远程版本
    MERGE_CONTENT = "merge_content"    # 合并内容
    MANUAL_REVIEW = "manual_review"    # 手动审查
```

#### 数据完整性
- **校验和验证**: BLAKE3 哈希校验
- **版本控制**: 细粒度版本追踪
- **原子操作**: 同步操作的原子性保证
- **回滚支持**: 同步失败时的完整回滚

## 数据库设计

### 核心表结构

#### projects 表
```sql
CREATE TABLE projects (
    id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    description TEXT,
    project_type TEXT NOT NULL,
    project_path TEXT NOT NULL,
    source_language TEXT NOT NULL,
    target_languages TEXT NOT NULL, -- JSON array
    mod_loader TEXT,
    status TEXT NOT NULL DEFAULT 'active',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

#### translation_entries 表
```sql
CREATE TABLE translation_entries (
    id TEXT PRIMARY KEY,
    project_id TEXT NOT NULL,
    key TEXT NOT NULL,
    source_text TEXT NOT NULL,
    target_text TEXT,
    source_language TEXT NOT NULL,
    target_language TEXT NOT NULL,
    namespace TEXT,
    category TEXT,
    context TEXT,
    status TEXT NOT NULL DEFAULT 'pending',
    version INTEGER DEFAULT 1,
    checksum TEXT NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (project_id) REFERENCES projects(id)
);
```

#### scan_sessions 表
```sql
CREATE TABLE scan_sessions (
    id TEXT PRIMARY KEY,
    project_id TEXT NOT NULL,
    scan_type TEXT NOT NULL,
    status TEXT NOT NULL,
    progress REAL DEFAULT 0.0,
    files_scanned INTEGER DEFAULT 0,
    entries_found INTEGER DEFAULT 0,
    started_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    completed_at TIMESTAMP,
    error_message TEXT,
    FOREIGN KEY (project_id) REFERENCES projects(id)
);
```

### 性能优化

#### 索引策略
```sql
-- 翻译条目快速查询
CREATE INDEX idx_translation_entries_project_key 
ON translation_entries(project_id, key);

CREATE INDEX idx_translation_entries_language_pair 
ON translation_entries(source_language, target_language);

CREATE INDEX idx_translation_entries_status 
ON translation_entries(status);

-- 项目查询优化
CREATE INDEX idx_projects_type_status 
ON projects(project_type, status);

-- 扫描会话查询
CREATE INDEX idx_scan_sessions_project_status 
ON scan_sessions(project_id, status);
```

#### 数据分区
- **按项目分区**: 大型项目数据物理分离
- **按语言分区**: 多语言数据分布式存储
- **时间分区**: 历史数据冷存储

## API 设计

### RESTful API 架构

#### 项目管理 API
```python
# 项目 CRUD 操作
POST   /api/v1/projects              # 创建项目
GET    /api/v1/projects              # 列出项目
GET    /api/v1/projects/{id}         # 获取项目详情
PUT    /api/v1/projects/{id}         # 更新项目
DELETE /api/v1/projects/{id}         # 删除项目

# 项目操作
POST   /api/v1/projects/{id}/scan    # 开始扫描
GET    /api/v1/projects/{id}/stats   # 获取项目统计
```

#### 扫描 API
```python
# 扫描控制
POST   /api/v1/scan/start            # 开始扫描
GET    /api/v1/scan/{id}/status      # 获取扫描状态
GET    /api/v1/scan/{id}/results     # 获取扫描结果
POST   /api/v1/scan/{id}/cancel      # 取消扫描

# 扫描历史
GET    /api/v1/scan/history          # 扫描历史
```

#### 翻译 API
```python
# 翻译条目 CRUD
POST   /api/v1/translations          # 创建翻译条目
GET    /api/v1/translations          # 查询翻译条目
PUT    /api/v1/translations/{id}     # 更新翻译
DELETE /api/v1/translations/{id}     # 删除翻译

# 批量操作
PUT    /api/v1/translations/batch    # 批量更新
POST   /api/v1/translations/import   # 导入翻译
GET    /api/v1/translations/export   # 导出翻译
```

#### 同步 API
```python
# 同步操作
POST   /api/v1/sync/start            # 开始同步
GET    /api/v1/sync/{id}/status      # 同步状态
GET    /api/v1/sync/{id}/conflicts   # 获取冲突
POST   /api/v1/sync/{id}/resolve     # 解决冲突
```

### API 安全

#### 认证和授权
- **JWT Token**: 基于 JWT 的认证机制
- **API Key**: 第三方集成的 API 密钥
- **权限控制**: 基于角色的访问控制（RBAC）

#### 数据验证
- **Pydantic 模型**: 严格的输入数据验证
- **SQL 注入防护**: 参数化查询
- **XSS 防护**: 输出数据转义
- **CSRF 防护**: CSRF Token 验证

## 性能和可扩展性

### 性能指标

#### 目标性能
- **文件扫描**: > 100 文件/秒
- **数据处理**: > 1000 条目/秒
- **内存使用**: < 10KB/条目
- **压缩比**: > 1.5:1（通用），> 2.0:1（中文）
- **并发用户**: > 50 同时用户

#### 性能优化策略
- **异步处理**: 全面使用 AsyncIO
- **连接池**: 数据库连接复用
- **缓存策略**: 多层缓存机制
- **批量操作**: 减少数据库往返
- **流式处理**: 大文件流式读写

### 可扩展性设计

#### 水平扩展
- **微服务架构**: 服务解耦，独立扩展
- **负载均衡**: API 网关负载分发
- **数据库分片**: 按项目或语言分片
- **消息队列**: 异步任务处理

#### 垂直扩展
- **多核利用**: 并发处理优化
- **内存优化**: 内存使用精细化管理
- **I/O 优化**: 异步 I/O 和缓存

## 安全架构

### 数据安全

#### 加密存储
- **数据库加密**: SQLCipher 透明加密
- **文件加密**: 敏感文件 AES 加密
- **传输加密**: HTTPS/TLS 1.3
- **密钥管理**: 安全的密钥存储和轮换

#### 访问控制
- **最小权限原则**: 用户仅获得必要权限
- **审计日志**: 完整的操作审计跟踪
- **会话管理**: 安全的会话生命周期管理

### 应用安全

#### 输入验证
```python
class SecurityValidator:
    """安全验证器"""
    
    @staticmethod
    def validate_file_path(path: str) -> bool:
        """验证文件路径安全性"""
        # 防止路径遍历攻击
        normalized = os.path.normpath(path)
        return not normalized.startswith(('..', '/', '\\'))
    
    @staticmethod
    def validate_file_size(size: int) -> bool:
        """验证文件大小"""
        return size <= MAX_FILE_SIZE
    
    @staticmethod
    def sanitize_input(text: str) -> str:
        """清理用户输入"""
        return html.escape(text.strip())
```

## 监控和维护

### 日志系统

#### 结构化日志
```python
import structlog

logger = structlog.get_logger()

# 业务日志
logger.info("项目扫描完成", 
    project_id="proj_123",
    files_scanned=150,
    entries_found=300,
    duration_ms=2500
)

# 错误日志
logger.error("文件处理失败",
    file_path="/path/to/file.jar",
    error_type="ExtractionError",
    error_message="无法解压文件"
)
```

#### 日志分类
- **访问日志**: API 请求和响应
- **业务日志**: 核心业务操作
- **错误日志**: 异常和错误信息
- **性能日志**: 性能指标和慢查询
- **安全日志**: 安全相关事件

### 监控指标

#### 系统指标
- **CPU 使用率**: 处理器负载监控
- **内存使用**: 内存消耗跟踪
- **磁盘 I/O**: 存储性能监控
- **网络流量**: 带宽使用统计

#### 应用指标
- **响应时间**: API 响应延迟
- **错误率**: 错误请求比例
- **吞吐量**: 请求处理速率
- **并发数**: 同时活跃用户

#### 业务指标
- **扫描速度**: 文件处理效率
- **翻译进度**: 翻译完成率
- **同步成功率**: 数据同步成功比例
- **用户活跃度**: 用户使用情况

### 健康检查

#### API 健康检查
```python
@app.get("/health")
async def health_check():
    """系统健康检查"""
    checks = {
        "database": await check_database_health(),
        "file_system": check_file_system_health(),
        "memory": check_memory_usage(),
        "external_services": await check_external_services()
    }
    
    overall_status = "healthy" if all(checks.values()) else "unhealthy"
    
    return {
        "status": overall_status,
        "timestamp": datetime.utcnow().isoformat(),
        "checks": checks
    }
```

## 部署架构

### 本地部署

#### 单机部署
- **桌面应用**: Tauri 打包的独立应用
- **数据存储**: 本地 SQLCipher 数据库
- **文件存储**: 本地文件系统
- **配置管理**: 配置文件 + 环境变量

#### 开发环境
- **前端开发服务器**: Vite + Tauri Dev
- **后端开发服务器**: FastAPI + Uvicorn
- **热重载**: 代码变更自动重载
- **调试支持**: 详细的调试信息

### 生产部署

#### 容器化部署
```dockerfile
# 后端容器
FROM python:3.12-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt
COPY . .
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]

# 前端构建
FROM node:18-alpine AS builder
WORKDIR /app
COPY package*.json ./
RUN npm ci
COPY . .
RUN npm run build:web

FROM nginx:alpine
COPY --from=builder /app/dist /usr/share/nginx/html
```

#### 服务编排
```yaml
# docker-compose.yml
version: '3.8'
services:
  backend:
    build: ./backend
    ports:
      - "8000:8000"
    environment:
      - DATABASE_URL=sqlite:///data/app.db
    volumes:
      - ./data:/app/data
  
  frontend:
    build: ./frontend
    ports:
      - "80:80"
    depends_on:
      - backend
```

## 总结

TH-Suite v2.0 采用现代化的软件架构设计，通过 Core-First 架构和投影适配器系统实现了与 Trans-Hub 的深度集成。系统在保持高性能和可扩展性的同时，提供了丰富的功能和良好的用户体验。

### 架构优势

1. **高度模块化**: 清晰的分层架构，便于维护和扩展
2. **性能优化**: 多项性能优化措施，确保高效运行
3. **安全可靠**: 全面的安全措施和数据保护
4. **用户友好**: 人性化的界面设计和操作流程
5. **可维护性**: 良好的代码组织和文档支持

### 技术创新

1. **投影适配器**: 创新的数据转换机制
2. **智能压缩**: 语言特定的压缩优化
3. **增量同步**: 高效的数据同步策略
4. **安全 JAR 处理**: 安全可靠的 JAR 文件操作
5. **实时监控**: 全面的系统监控和性能跟踪

该架构为 TH-Suite 的持续发展和功能扩展奠定了坚实的基础。