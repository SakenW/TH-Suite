# 通用文件传输基础服务

TH-Suite的通用文件传输基础服务实现，为多游戏支持提供统一、高效、安全的文件处理能力。

## 🚀 核心特性

### 高性能文件传输
- **分块传输**：支持大文件分块上传/下载，内存效率优化
- **断点续传**：网络中断后自动恢复传输
- **并发控制**：智能并发管理，充分利用网络带宽
- **多种协议**：HTTP、WebSocket、流式传输等策略

### 实时进度监控
- **多任务监控**：并行追踪多个任务进度
- **WebSocket推送**：实时进度更新到前端
- **层次化任务**：支持主任务和子任务的进度管理
- **性能指标**：传输速度、ETA计算、里程碑通知

### 智能压缩服务
- **多算法支持**：Zstd、LZ4、Gzip、Brotli等
- **语言特化字典**：针对不同语言优化压缩率
- **自适应选择**：根据文件类型和网络条件智能选择算法
- **流式处理**：支持大文件流式压缩，避免内存溢出

### 安全验证框架
- **完整性验证**：BLAKE3哈希验证，确保数据完整性
- **权限控制**：细粒度访问控制和角色管理
- **会话管理**：安全会话生命周期管理
- **审计日志**：完整的安全操作记录

### 服务容器架构
- **依赖注入**：统一的服务管理和依赖注入
- **作用域管理**：单例、瞬时、作用域服务支持
- **配置管理**：类型安全的配置系统
- **生命周期管理**：服务启动、运行、关闭的完整生命周期

## 📁 模块结构

```
packages/core/
├── file-transfer/          # 文件传输引擎
│   ├── core.py            # 传输引擎核心
│   ├── strategies.py      # 传输策略实现
│   ├── config.py          # 传输配置
│   └── errors.py          # 传输异常
├── progress-tracking/      # 进度监控系统
│   ├── core.py            # 进度追踪核心
│   ├── websocket.py       # WebSocket推送
│   ├── aggregator.py      # 进度聚合
│   └── config.py          # 进度配置
├── compression/           # 压缩服务
│   ├── core.py            # 压缩引擎
│   ├── algorithms.py      # 压缩算法
│   ├── dictionary.py      # 字典管理
│   └── streaming.py       # 流式压缩
├── security/              # 安全框架
│   ├── core.py            # 安全管理器
│   ├── integrity.py       # 完整性验证
│   ├── auth.py            # 认证授权
│   └── audit.py           # 安全审计
├── file_transfer_interfaces.py  # 标准接口定义
├── service_container.py    # 服务容器
└── tests/                 # 完整测试套件
```

## 🛠️ 快速开始

### 基本用法

```python
from packages.core import (
    create_default_host,
    FileTransferEngine, 
    ProgressManager,
    CompressionEngine,
    SecurityManager
)

# 创建服务主机
host = create_default_host()
await host.start_async()

# 获取服务
transfer_engine = host.get_required_service(FileTransferEngine)
progress_manager = host.get_required_service(ProgressManager)
```

### 文件传输示例

```python
from pathlib import Path
from packages.core.file_transfer import (
    FileTransferEngine, TransferTask, TransferConfig
)
from packages.core.file_transfer.strategies import HttpUploadStrategy

# 配置传输引擎
config = TransferConfig()
config.max_concurrent_chunks = 8
config.chunk_config.size = 8 * 1024 * 1024  # 8MB

engine = FileTransferEngine(config)
engine.set_strategy(HttpUploadStrategy())

# 创建传输任务
task = TransferTask(
    id="upload_game_data",
    source_path=Path("game_data.zip"),
    target_url="https://api.example.com/upload",
    file_size=Path("game_data.zip").stat().st_size
)

# 执行传输
result = await engine.start_transfer(task)
print(f"传输完成: {result.success}, 耗时: {result.total_time}")
```

### 进度监控示例

```python
from packages.core.progress_tracking import ProgressManager, ProgressConfig

# 配置进度管理器
config = ProgressConfig()
config.websocket_enabled = True
config.websocket_port = 8001

manager = ProgressManager(config)

# 创建进度任务
progress = await manager.create_and_start_task(
    task_id="process_files",
    title="处理游戏文件",
    total_value=100.0
)

# 更新进度
for i in range(1, 11):
    await manager.update_task("process_files", increment=10.0)
    await asyncio.sleep(1)

await manager.tracker.complete_task("process_files")
```

### 压缩服务示例

```python
from packages.core.compression import (
    CompressionEngine, CompressionConfig, CompressionLevel
)

# 配置压缩引擎
config = CompressionConfig()
config.default_algorithm = "zstd"
config.enable_dictionaries = True

engine = CompressionEngine(config)

# 压缩文件
result = await engine.compress_file(
    input_path=Path("large_game_file.dat"),
    output_path=Path("large_game_file.zst"),
    level=CompressionLevel.BALANCED
)

print(f"压缩完成: 原始 {result.original_size} bytes, "
      f"压缩后 {result.compressed_size} bytes, "
      f"压缩比 {result.compression_ratio:.3f}")
```

### 安全验证示例

```python
from packages.core.security import (
    SecurityManager, SecurityConfig, ActionType
)

# 配置安全管理器
config = SecurityConfig()
config.verify_file_integrity = True
config.enable_audit_logging = True

manager = SecurityManager(config)

# 创建用户会话
context = await manager.create_session(
    user_id="game_user",
    ip_address="192.168.1.100",
    user_agent="game-client",
    permissions={"file:read", "file:write"}
)

# 注册文件资源
manager.register_resource(
    resource_id="game_save.dat",
    resource_type="file",
    owner_id="game_user"
)

# 检查访问权限
can_access = await manager.check_permission(
    context.session_id, "game_save.dat", ActionType.READ
)
```

## 🧪 测试

项目包含完整的测试套件，覆盖所有核心功能：

```bash
# 运行所有测试
pytest packages/core/tests/ -v

# 运行特定模块测试
pytest packages/core/tests/test_file_transfer.py -v
pytest packages/core/tests/test_progress_tracking.py -v
pytest packages/core/tests/test_compression.py -v
pytest packages/core/tests/test_security.py -v
pytest packages/core/tests/test_service_container.py -v

# 生成测试覆盖率报告
pytest packages/core/tests/ --cov=packages/core --cov-report=html
```

## 📊 性能特性

### 文件传输性能
- **并发传输**：支持最多8个分块同时传输
- **自适应分块**：根据文件大小智能调整分块大小
- **网络优化**：根据带宽和延迟自动优化传输策略
- **断点续传**：支持中断后从断点继续传输

### 压缩性能
- **Zstd优化**：相比gzip提升20-30%的压缩率
- **语言字典**：针对不同语言的专用压缩字典
- **流式处理**：支持GB级大文件压缩，内存使用恒定
- **并行压缩**：多线程并行处理，充分利用CPU资源

### 安全性能
- **BLAKE3哈希**：比SHA256快3-5倍的哈希计算
- **增量验证**：支持增量文件完整性验证
- **缓存优化**：智能缓存机制减少重复计算
- **批量验证**：支持目录级批量完整性检查

## 🔧 配置选项

### 传输配置模板

```python
from packages.core.file_transfer.config import ConfigTemplates

# 快速本地传输
fast_config = ConfigTemplates.fast_local()

# 可靠远程传输
reliable_config = ConfigTemplates.reliable_remote()

# 低带宽网络优化
low_bandwidth_config = ConfigTemplates.low_bandwidth()

# 高性能传输
high_perf_config = ConfigTemplates.high_performance()
```

### 进度配置模板

```python
from packages.core.progress_tracking.config import ProgressConfigTemplates

# 开发环境配置
dev_config = ProgressConfigTemplates.development()

# 生产环境配置
prod_config = ProgressConfigTemplates.production()

# 高性能配置
perf_config = ProgressConfigTemplates.high_performance()
```

### 安全配置模板

```python
from packages.core.security.config import SecurityConfigTemplates

# 开发环境安全配置
dev_security = SecurityConfigTemplates.development()

# 生产环境安全配置
prod_security = SecurityConfigTemplates.production()

# 高安全级别配置
high_security = SecurityConfigTemplates.high_security()
```

## 🌟 高级特性

### 游戏适配器接口

```python
from packages.core.file_transfer_interfaces import (
    GameAdapter, BaseGameAdapter, ResourceType, GameType
)

class MinecraftAdapter(BaseGameAdapter):
    def __init__(self):
        super().__init__(GameType.MINECRAFT)
        self.add_supported_type(ResourceType.MOD)
        self.add_supported_type(ResourceType.RESOURCE_PACK)
    
    async def _detect_resource_type(self, file_path: Path) -> Optional[ResourceType]:
        if file_path.suffix == '.jar':
            return ResourceType.MOD
        elif file_path.suffix == '.zip':
            return ResourceType.RESOURCE_PACK
        return None
```

### 自定义传输策略

```python
from packages.core.file_transfer.strategies import BaseTransferStrategy

class S3UploadStrategy(BaseTransferStrategy):
    async def upload_chunk(self, chunk_data, chunk_info, task):
        # 实现S3分块上传逻辑
        pass
    
    async def verify_chunk(self, chunk_info, task):
        # 实现S3分块验证逻辑
        pass
```

### WebSocket实时推送

```python
from packages.core.progress_tracking.websocket import ProgressWebSocketClient

# 前端WebSocket客户端
client = ProgressWebSocketClient("ws://localhost:8001/ws/progress")
await client.connect()

# 订阅任务进度
await client.subscribe(["task1", "task2"])

# 处理进度事件
client.on_message("progress_event", lambda data: print(f"进度更新: {data}"))
```

## 🚀 多游戏支持

该基础服务设计为通用架构，可轻松扩展支持多种游戏：

- **Minecraft**：MOD、资源包、数据包处理
- **Rusted Warfare**：地图、MOD、翻译文件
- **自定义游戏**：通过GameAdapter接口扩展

每个游戏只需实现特定的适配器逻辑，核心传输、压缩、安全功能完全复用。

## 📈 监控和指标

系统提供丰富的监控指标：

- **传输指标**：速度、成功率、错误类型统计
- **进度指标**：任务完成情况、平均处理时间
- **压缩指标**：压缩率、算法性能对比
- **安全指标**：认证成功率、权限检查统计

## 🔒 安全考虑

- **数据完整性**：所有传输文件强制BLAKE3哈希验证
- **访问控制**：基于角色和权限的细粒度访问控制
- **会话安全**：安全的会话管理和自动过期机制
- **审计日志**：完整的操作审计和安全事件记录
- **加密传输**：支持传输过程中的数据加密

## 🤝 贡献指南

1. 所有新功能需要完整的单元测试覆盖
2. 遵循现有的代码风格和注释规范
3. 确保向后兼容性
4. 更新相关文档

## 📝 许可证

本项目遵循TH-Suite项目许可证。

---

通过这个通用文件传输基础服务，TH-Suite为多游戏本地化工具提供了强大、可靠、高效的底层支撑，确保在处理各种游戏资源时都能获得一致的高质量体验。