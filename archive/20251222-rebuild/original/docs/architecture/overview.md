# TH Suite 架构文档

## 📋 目录

1. [系统架构概览](#系统架构概览)
2. [核心设计模式](#核心设计模式)
3. [后端架构](#后端架构)
4. [前端架构](#前端架构)
5. [数据模型](#数据模型)
6. [技术栈详解](#技术栈详解)
7. [性能优化](#性能优化)

## 系统架构概览

TH Suite 采用分层架构设计，实现了关注点分离和高度模块化：

```
┌─────────────────────────────────────────────────────────┐
│                     用户界面层                           │
│         Tauri Desktop App (React + TypeScript)          │
├─────────────────────────────────────────────────────────┤
│                      API 网关层                          │
│                  FastAPI REST/WebSocket                  │
├─────────────────────────────────────────────────────────┤
│                     应用服务层                           │
│              Business Logic & Use Cases                  │
├─────────────────────────────────────────────────────────┤
│                      领域层                              │
│           Domain Models & Domain Services                │
├─────────────────────────────────────────────────────────┤
│                    基础设施层                            │
│        Database, File System, External APIs              │
└─────────────────────────────────────────────────────────┘
```

## 核心设计模式

### 1. Clean Architecture (后端)

```python
# 领域层 - 纯业务逻辑
packages/localization-kit/models/
├── artifact.py       # 物理载体实体
├── container.py      # 逻辑容器实体
├── blob.py          # 内容存储实体
└── patch.py         # 补丁实体

# 应用层 - 用例编排
packages/localization-kit/services/
├── scan_service.py   # 扫描服务
├── blob_service.py   # Blob管理服务
├── patch_service.py  # 补丁服务
└── sync_service.py   # 同步服务

# 基础设施层 - 技术实现
packages/localization-kit/infrastructure/
├── database/         # 数据持久化
├── parsers/         # 文件解析器
└── scanners/        # 文件扫描器
```

### 2. 依赖注入 (DI)

```python
# 后端 DI 容器
from fastapi import Depends

class ServiceContainer:
    def __init__(self):
        self.db_session = create_session()
        self.scan_service = ScanService(self.db_session)
        self.blob_service = BlobService(self.db_session)
        
    @classmethod
    def get_instance(cls):
        return cls()

# 使用依赖注入
@router.post("/scan")
async def scan_project(
    path: str,
    container: ServiceContainer = Depends(ServiceContainer.get_instance)
):
    return await container.scan_service.scan(path)
```

### 3. Repository Pattern

```python
# 数据访问抽象
class BlobRepository:
    def __init__(self, session: Session):
        self.session = session
    
    def find_by_hash(self, blob_hash: str) -> Optional[Blob]:
        return self.session.query(BlobTable).filter_by(
            blob_hash=blob_hash
        ).first()
    
    def save(self, blob: Blob) -> None:
        self.session.add(blob)
        self.session.commit()
```

### 4. Observer Pattern (前端)

```typescript
// 实时进度更新
class ProgressObserver {
    private listeners: Set<(progress: Progress) => void> = new Set();
    
    subscribe(callback: (progress: Progress) => void) {
        this.listeners.add(callback);
        return () => this.listeners.delete(callback);
    }
    
    notify(progress: Progress) {
        this.listeners.forEach(callback => callback(progress));
    }
}
```

## 后端架构

### 领域模型设计

#### Artifact/Container 双层模型

```python
# 物理载体 - 对应实际文件
class Artifact:
    artifact_id: str        # 唯一标识
    artifact_type: str      # mod_jar, modpack_dir, resource_pack
    file_path: str         # 文件路径
    content_hash: str      # 内容哈希
    containers: List[Container]  # 包含的逻辑容器

# 逻辑容器 - 翻译单元
class Container:
    container_id: str      # 唯一标识
    container_type: str    # MOD, PACK_MODULE, OVERLAY
    namespace: str         # 命名空间
    display_name: str      # 显示名称
    language_files: List[LanguageFile]  # 语言文件
```

#### Blob 内容寻址存储

```python
class Blob:
    blob_hash: str         # SHA256 哈希
    blob_size: int        # 大小
    entry_count: int      # 条目数
    reference_count: int  # 引用计数
    entries: Dict[str, str]  # 实际内容
    
    @classmethod
    def from_entries(cls, entries: Dict[str, str]) -> 'Blob':
        # 规范化 JSON 确保相同内容产生相同哈希
        canonical_json = json.dumps(entries, sort_keys=True, ensure_ascii=False)
        blob_hash = hashlib.sha256(canonical_json.encode('utf-8')).hexdigest()
        return cls(blob_hash=blob_hash, entries=entries)
```

#### 补丁系统

```python
class PatchSet:
    patch_set_id: str
    name: str
    version: str
    patch_items: List[PatchItem]
    signature: str  # 数字签名
    
class PatchItem:
    patch_item_id: str
    container_id: str
    locale: str
    namespace: str
    policy: PatchPolicy  # OVERLAY, REPLACE, MERGE, CREATE_IF_MISSING
    content: Dict[str, str]
```

### 服务层架构

```python
# 扫描服务 - 协调扫描流程
class ScanService:
    async def scan_directory(self, path: str) -> ScanResult:
        # 1. 识别 Artifact 类型
        artifacts = await self.artifact_scanner.scan(path)
        
        # 2. 提取 Container
        containers = await self.container_extractor.extract(artifacts)
        
        # 3. 解析语言文件
        language_files = await self.language_parser.parse(containers)
        
        # 4. 生成 Blob
        blobs = await self.blob_generator.generate(language_files)
        
        # 5. 计算统计信息
        stats = await self.stats_calculator.calculate(blobs)
        
        return ScanResult(artifacts, containers, blobs, stats)
```

### 质量门禁系统

```python
# 验证器架构
class QualityValidator(ABC):
    @abstractmethod
    def validate(self, key: str, source: str, target: str) -> ValidationResult:
        pass

# 具体验证器
class PlaceholderValidator(QualityValidator):
    def validate(self, key: str, source: str, target: str) -> ValidationResult:
        source_placeholders = re.findall(r'%\w+%', source)
        target_placeholders = re.findall(r'%\w+%', target)
        
        if set(source_placeholders) != set(target_placeholders):
            return ValidationResult(
                passed=False,
                level=ValidationLevel.ERROR,
                message="占位符不匹配"
            )
        return ValidationResult(passed=True)
```

## 前端架构

### Minecraft 主题系统

```typescript
// 颜色系统
export const minecraftColors = {
  primary: {
    grass: '#5EBA3A',      // 草方块绿
    diamond: '#5ECFCF',    // 钻石青
    gold: '#FDD835',       // 金色
    redstone: '#AA0000',   // 红石红
    netherite: '#4D494D',  // 下界合金黑
  },
  ui: {
    background: {
      primary: '#C6C6C6',  // 石头材质色
      tooltip: '#100010',  // 工具提示背景
    },
    border: {
      light: '#FFFFFF',    // 亮边框
      dark: '#373737',     // 暗边框
    }
  },
  rarity: {
    common: '#FFFFFF',     // 普通
    uncommon: '#FFFF55',   // 罕见
    rare: '#55FFFF',       // 稀有
    epic: '#FF55FF',       // 史诗
    legendary: '#FF5555',  // 传奇
  }
};

// 纹理系统
export const textures = {
  stone: `repeating-linear-gradient(...)`,
  dirt: `repeating-linear-gradient(...)`,
  planks: `repeating-linear-gradient(...)`,
  inventory: `linear-gradient(...)`,
};
```

### 组件架构

```tsx
// MC 风格组件
interface MCComponentProps {
  variant?: 'default' | 'primary' | 'success' | 'danger' | 'enchanted';
  size?: 'small' | 'medium' | 'large';
  disabled?: boolean;
  sound?: boolean;  // 音效支持
}

// 组件实现
const MCButton: React.FC<MCButtonProps> = ({
  children,
  variant = 'default',
  onClick,
  ...props
}) => {
  const [isPressed, setIsPressed] = useState(false);
  const borderStyles = get3DBorder(!isPressed);
  
  return (
    <motion.button
      style={{
        ...borderStyles,
        backgroundColor: getVariantColor(variant),
        imageRendering: 'pixelated',
      }}
      whileHover={{ scale: 1.02 }}
      whileTap={{ scale: 0.98 }}
      onClick={onClick}
    >
      {children}
    </motion.button>
  );
};
```

### 服务容器模式

```typescript
// 前端服务管理
class ServiceContainer {
  private static instance: ServiceContainer;
  private services: Map<string, any> = new Map();
  
  static getInstance(): ServiceContainer {
    if (!this.instance) {
      this.instance = new ServiceContainer();
    }
    return this.instance;
  }
  
  register<T>(name: string, service: T): void {
    this.services.set(name, service);
  }
  
  get<T>(name: string): T {
    return this.services.get(name);
  }
}

// 使用示例
const container = ServiceContainer.getInstance();
container.register('scanService', new ScanService());
container.register('projectService', new ProjectService());
```

## 数据模型

### 数据库架构 (SQLAlchemy)

```sql
-- 物理载体表
CREATE TABLE artifacts (
    artifact_id TEXT PRIMARY KEY,
    artifact_type TEXT NOT NULL,
    file_path TEXT NOT NULL,
    content_hash TEXT,
    metadata JSON,
    created_at TIMESTAMP,
    updated_at TIMESTAMP
);

-- 逻辑容器表
CREATE TABLE containers (
    container_id TEXT PRIMARY KEY,
    artifact_id TEXT REFERENCES artifacts(artifact_id),
    container_type TEXT NOT NULL,
    namespace TEXT,
    display_name TEXT,
    metadata JSON
);

-- 语言文件表
CREATE TABLE language_files (
    file_id TEXT PRIMARY KEY,
    container_id TEXT REFERENCES containers(container_id),
    locale TEXT NOT NULL,
    namespace TEXT,
    content_hash TEXT REFERENCES blobs(blob_hash),
    file_path TEXT
);

-- Blob 存储表
CREATE TABLE blobs (
    blob_hash TEXT PRIMARY KEY,
    blob_size INTEGER,
    entry_count INTEGER,
    reference_count INTEGER DEFAULT 1,
    compressed_data BLOB,
    created_at TIMESTAMP
);

-- 补丁集表
CREATE TABLE patch_sets (
    patch_set_id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    version TEXT,
    status TEXT,
    signature TEXT,
    created_at TIMESTAMP,
    published_at TIMESTAMP
);

-- 补丁项表
CREATE TABLE patch_items (
    patch_item_id TEXT PRIMARY KEY,
    patch_set_id TEXT REFERENCES patch_sets(patch_set_id),
    container_id TEXT,
    locale TEXT,
    namespace TEXT,
    policy TEXT,
    content JSON,
    expected_hash TEXT
);
```

## 技术栈详解

### 后端技术栈

- **FastAPI**: 高性能异步 Web 框架
- **SQLAlchemy**: ORM 和数据库抽象
- **SQLCipher**: 加密 SQLite 数据库
- **Pydantic**: 数据验证和序列化
- **asyncio**: 异步 I/O 支持
- **structlog**: 结构化日志
- **aiohttp**: 异步 HTTP 客户端

### 前端技术栈

- **React 18**: UI 框架
- **TypeScript**: 类型安全
- **Tauri**: 桌面应用框架
- **Framer Motion**: 动画库
- **i18next**: 国际化
- **Zustand**: 状态管理
- **Tailwind CSS**: 样式框架

## 性能优化

### 1. 内容去重

```python
# Blob 去重减少存储
def deduplicate_content(entries: Dict[str, str]) -> str:
    blob = Blob.from_entries(entries)
    existing = blob_repository.find_by_hash(blob.blob_hash)
    
    if existing:
        existing.reference_count += 1
        return existing.blob_hash
    else:
        blob_repository.save(blob)
        return blob.blob_hash
```

### 2. 增量扫描

```python
# 基于指纹的增量扫描
class IncrementalScanner:
    def scan(self, path: str) -> ScanResult:
        current_fingerprint = self.calculate_fingerprint(path)
        cached_result = self.cache.get(current_fingerprint)
        
        if cached_result:
            return cached_result
        
        # 只扫描变化的部分
        changed_files = self.detect_changes(path)
        partial_result = self.scan_files(changed_files)
        
        # 合并结果
        return self.merge_results(cached_result, partial_result)
```

### 3. 流式处理

```python
# NDJSON 流式传输
async def stream_upload(entries: AsyncIterator[Dict]):
    async with aiohttp.ClientSession() as session:
        async with session.post('/upload', 
                               headers={'Content-Type': 'application/x-ndjson'}) as resp:
            async for entry in entries:
                line = json.dumps(entry) + '\n'
                await resp.write(line.encode())
```

### 4. 并发优化

```typescript
// 并行处理多个文件
async function processFiles(files: File[]): Promise<Result[]> {
    const chunks = chunkArray(files, 10);
    const results = await Promise.all(
        chunks.map(chunk => processChunk(chunk))
    );
    return results.flat();
}
```

## 监控与观测

### 链路追踪

```python
# 全链路追踪实现
with tracer.trace("scan_operation", path=scan_path) as trace:
    with tracer.span("parse_files"):
        files = parse_files(scan_path)
    
    with tracer.span("extract_content"):
        content = extract_content(files)
    
    with tracer.span("generate_blobs"):
        blobs = generate_blobs(content)
```

### 指标收集

```python
# 关键指标监控
metrics.record("dedup_ratio", calculate_dedup_ratio())
metrics.record("translation_coverage", calculate_coverage())
metrics.record("scan_duration", scan_timer.elapsed())
metrics.record("patch_conflicts", count_conflicts())
```

---

最后更新: 2024-01-20
作者: TH Suite Team