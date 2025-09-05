# TH-Suite 架构重构设计 v2.0.0

## 项目定位

**TH-Suite** 是一款通用的本地化工具套件，专为 **Trans-Hub** 翻译平台设计，旨在提供跨平台的本地化解决方案。通过高度模块化与插件化架构，用户可以根据需求灵活集成和扩展工具，使得本地化流程更加高效、自动化。

本架构通过封装常见的通用功能到底层平台，简化工具层的开发，减少复杂度并提高系统的可维护性。专属业务逻辑和特定需求除外，所有通用功能都集中在底层平台，工具层仅需简单调用核心层提供的服务接口，减少重复实现。

## 架构设计特色

### 1. 严格的分层架构
通过严格的分层设计，核心功能与应用逻辑层解耦，核心层提供通用功能服务，工具层仅通过接口调用，无需关心底层实现细节。

- **分层设计**：Adapters → Application → Domain → Infrastructure → Core
- **职责分离**：每一层都明确承担特定的责任，保持低耦合性

### 2. 模块化与可插拔设计
核心功能与工具功能解耦，核心层提供了通用的功能模块，工具层通过插件化架构在此基础上扩展自己的功能。每个模块独立，工具层只需关心业务实现，无需关心底层实现细节。

### 3. 依赖注入与IoC容器
通过依赖注入（IoC容器）管理所有服务实例，工具层通过容器获取所需服务，避免硬编码依赖。核心服务的生命周期、管理和注入由容器负责。

### 4. 松耦合与事件驱动架构
核心层通过事件总线和任务调度系统实现松耦合，工具层可以注册和监听事件，任务调度则可以异步执行。通过发布和订阅机制，模块间的依赖降到最低，便于扩展和维护。

## 架构分层

### 1. Core Platform（底层架构平台）
所有工具共享的核心基础设施，位于 `packages/core/`。核心层提供通用功能模块的封装，工具层通过简洁的接口调用这些功能，确保了系统的灵活性、可扩展性和易维护性。

#### 1.1 Framework Layer（框架层）
提供依赖注入容器、配置管理、事件总线、缓存管理等基础服务。这是系统的核心基础设施层。

```
packages/core/framework/
├── __init__.py
├── container.py          # IoC容器（完整实现）
├── config/               # 配置管理
│   ├── __init__.py
│   ├── config_manager.py # 配置管理器（支持多环境、热更新）
│   ├── providers/        # 配置提供者
│   │   ├── env_provider.py    # 环境变量配置
│   │   ├── file_provider.py   # 文件配置（YAML/JSON）
│   │   └── user_provider.py   # 用户自定义配置
│   └── settings.py       # 配置定义和验证
├── events/               # 事件系统（发布订阅模式）
│   ├── __init__.py
│   ├── event_bus.py      # 事件总线
│   ├── event_handler.py  # 事件处理器
│   └── decorators.py     # 事件装饰器
├── cache/                # 缓存抽象（统一接口ICache）
│   ├── __init__.py
│   ├── cache_manager.py  # 缓存管理器
│   ├── providers/        # 缓存提供者
│   │   ├── memory_cache.py    # 内存缓存
│   │   ├── redis_cache.py     # Redis缓存
│   │   └── file_cache.py      # 文件系统缓存
│   └── decorators.py     # 缓存装饰器
├── logging/              # 日志框架（统一接口ILogger）
│   ├── __init__.py
│   ├── logger.py         # 日志管理器
│   ├── formatters/       # 格式化器
│   └── handlers/         # 处理器（控制台、文件等）
├── tasks/                # 任务调度与异步处理
│   ├── __init__.py
│   ├── task_manager.py   # 任务管理器
│   ├── task_scheduler.py # 任务调度器
│   └── decorators.py     # 任务装饰器
└── validation/           # 验证框架
    ├── __init__.py
    ├── validator.py      # 验证器
    └── rules/            # 验证规则
```

**核心特性**：
- **IoC容器**：完整的服务管理与生命周期管理，支持单例、瞬态等模式
- **配置管理**：支持多环境配置，提供统一的配置访问接口
- **事件系统**：松耦合的事件驱动架构，支持异步事件处理
- **缓存系统**：提供统一的缓存接口，支持多种缓存实现

#### 1.2 Data Layer（数据层）
数据访问层封装数据库连接、事务管理及仓储模式，简化数据库操作并确保数据一致性。

```
packages/core/data/
├── __init__.py
├── unit_of_work.py       # 工作单元模式（事务管理）
├── repositories/         # 仓储抽象
│   ├── __init__.py
│   ├── base.py          # 基础仓储接口
│   ├── repository.py    # 仓储实现基类
│   └── registry.py      # 仓储注册表
├── db/                  # 数据库相关
│   ├── __init__.py
│   ├── connection.py    # 连接管理（SQLCipher支持）
│   ├── transaction.py   # 事务管理
│   └── migration.py     # 数据迁移
└── models/              # 基础领域模型
    ├── __init__.py
    ├── base_entity.py   # 实体基类
    ├── value_object.py  # 值对象基类
    └── aggregate.py     # 聚合根基类
```

**核心特性**：
- **工作单元模式**：确保事务的一致性和完整性
- **仓储模式**：抽象数据访问，便于测试和替换数据源
- **领域驱动设计**：清晰的实体、值对象和聚合根定义
- **加密数据库**：支持SQLCipher加密数据库存储

#### 1.3 Application Layer（应用服务层）
提供业务逻辑支持，采用 **CQRS** 设计模式，处理命令与查询分离，确保系统高效、可扩展。

```
packages/core/application/
├── __init__.py
├── services/            # 应用服务基类
│   ├── __init__.py
│   ├── base_service.py
│   └── service_base.py
├── commands/            # 命令模式（写操作）
│   ├── __init__.py
│   ├── command.py       # 命令基类
│   ├── command_handler.py
│   └── command_bus.py   # 命令总线
├── queries/             # 查询模式（读操作）
│   ├── __init__.py
│   ├── query.py         # 查询基类
│   └── query_handler.py # 查询处理器
├── exceptions/          # 异常定义
│   ├── __init__.py
│   ├── base_exception.py
│   └── business_exception.py
└── dto/                 # 数据传输对象
    ├── __init__.py
    └── base_dto.py
```

**核心特性**：
- **CQRS模式**：命令查询职责分离，提高系统性能和可扩展性
- **应用服务**：封装业务逻辑，协调领域对象完成业务操作
- **异常管理**：统一的异常处理和错误响应机制
- **数据传输对象**：规范化数据传输格式

#### 1.4 Infrastructure Layer（基础设施层）
提供与外部系统的集成接口（如存储、HTTP通信、加密等），保证与外部系统的无缝对接。

```
packages/core/infrastructure/
├── __init__.py
├── storage/             # 存储抽象
│   ├── __init__.py
│   ├── storage_manager.py
│   ├── providers/
│   │   ├── local_storage.py   # 本地文件系统
│   │   ├── s3_storage.py      # AWS S3兼容存储
│   │   └── ftp_storage.py     # FTP存储
├── http/                # HTTP客户端
│   ├── __init__.py
│   ├── http_client.py         # HTTP客户端（支持Trans-Hub API）
│   └── middleware/            # 中间件（认证、重试等）
├── serialization/       # 序列化
│   ├── __init__.py
│   ├── serializer.py
│   └── formats/
│       ├── json_serializer.py # JSON序列化
│       └── yaml_serializer.py # YAML序列化
├── crypto/              # 加密服务
│   ├── __init__.py
│   ├── encryptor.py           # 加密/解密
│   └── hash.py                # 哈希算法
└── compression/         # 压缩服务
    ├── __init__.py
    ├── compressor.py
    └── formats/
        ├── zip_compressor.py   # ZIP压缩
        └── rar_compressor.py   # RAR压缩
```

**核心特性**：
- **存储抽象**：统一的存储接口，支持本地、云端等多种存储方式
- **HTTP通信**：与Trans-Hub平台的API通信，支持认证和重试机制
- **序列化支持**：多格式数据序列化，便于配置文件和数据交换
- **安全服务**：提供加密、哈希等安全功能，保护敏感数据

## 工具层与核心层的解耦

工具层只需调用核心层提供的接口，无需了解底层实现。核心层负责与外部系统（如数据库、缓存、外部API等）交互，工具层专注于实现具体的业务逻辑。

### IoC（依赖注入）设计示例

工具层通过 **IoC 容器** 获取核心功能服务，而不直接创建服务实例。核心服务的生命周期由容器管理，工具层无需处理服务的创建与管理。

```python
# Core层：日志服务接口
from abc import ABC, abstractmethod

class ILogger(ABC):
    @abstractmethod
    def log(self, message: str, level: str = "info"):
        pass

class ICache(ABC):
    @abstractmethod
    def get(self, key: str):
        pass

# Core层：具体实现
class ConsoleLogger(ILogger):
    def log(self, message: str, level: str = "info"):
        print(f"[{level.upper()}] {message}")

# 工具层：依赖注入获取服务
class McModScanner:
    def __init__(self, logger: ILogger, cache: ICache):
        self.logger = logger
        self.cache = cache

    def scan_mods(self, path: str):
        self.logger.log(f"开始扫描模组目录: {path}")
        # 业务逻辑实现
        cached_result = self.cache.get(f"scan:{path}")
        if cached_result:
            self.logger.log("使用缓存结果")
            return cached_result
        # ... 扫描逻辑

# IoC容器注册与依赖注入
from packages.core.framework.container import IoCContainer

container = IoCContainer()
container.register(ILogger, ConsoleLogger())
container.register(ICache, MemoryCache())

# 自动依赖注入
scanner = container.resolve(McModScanner)
```

### 2. Tool Layer（工具层）
每个工具的具体实现，位于 `apps/[tool-name]/`。工具层专注于业务逻辑实现，通过Core Platform提供的接口完成所需功能。

#### 2.1 MC本地化工具
```
apps/mc-l10n/
├── backend/
│   ├── domain/          # MC领域模型
│   │   ├── models/      # MC特有的实体和值对象
│   │   │   ├── mod.py           # 模组实体
│   │   │   ├── resource_pack.py # 资源包实体
│   │   │   └── translation.py   # 翻译条目
│   │   ├── repositories/# MC仓储接口
│   │   │   ├── mod_repository.py
│   │   │   └── translation_repository.py
│   │   └── services/    # MC领域服务
│   │       ├── mod_scanner.py
│   │       └── translation_extractor.py
│   ├── application/     # MC应用层
│   │   ├── services/    # MC应用服务
│   │   │   ├── mod_management_service.py
│   │   │   └── translation_service.py
│   │   ├── commands/    # MC命令
│   │   │   ├── scan_mods_command.py
│   │   │   └── extract_translations_command.py
│   │   └── queries/     # MC查询
│   │       ├── get_mods_query.py
│   │       └── get_translations_query.py
│   ├── infrastructure/  # MC基础设施
│   │   ├── repositories/# MC仓储实现
│   │   ├── scanners/    # MC扫描器
│   │   │   ├── jar_scanner.py
│   │   │   └── folder_scanner.py
│   │   └── parsers/     # MC解析器
│   │       ├── json_parser.py
│   │       └── properties_parser.py
│   └── adapters/        # MC适配器层
│       ├── api/         # API适配器（FastAPI路由）
│       │   ├── mod_routes.py
│       │   └── translation_routes.py
│       ├── cli/         # CLI适配器
│       └── plugin.py    # MC插件实现
└── frontend/            # 前端实现（Tauri + React）
    ├── src/
    │   ├── components/  # React组件
    │   ├── pages/       # 页面组件
    │   ├── stores/      # Zustand状态管理
    │   └── services/    # API调用服务
    └── src-tauri/       # Tauri配置
```

**核心特性**：
- **领域驱动设计**：清晰的领域模型和业务逻辑分离
- **依赖注入**：通过Core Platform的IoC容器管理依赖
- **插件化架构**：可扩展的扫描器和解析器
- **前后端分离**：Tauri桌面应用 + FastAPI后端服务

#### 2.2 RW本地化工具
```
apps/rw-l10n/
├── backend/
│   ├── domain/          # RW领域模型
│   │   ├── models/      # RW特有实体（地图、单位等）
│   │   └── services/    # RW领域服务
│   ├── application/     # RW应用层
│   └── adapters/        # RW适配器层
└── frontend/            # RW前端实现
```

#### 2.3 通用工具（界面、设置等）
```
apps/common/
├── theme/              # 主题管理
├── settings/           # 用户设置
├── update/             # 更新检查
└── shared/             # 共享组件
```

## 核心功能模块封装

### 1. 配置管理
核心层提供统一的配置管理模块，支持多环境配置和热更新。工具层无需关心配置的加载和管理，只需调用核心层提供的接口。

### 2. 日志系统
日志管理抽象为统一接口（ILogger），具体实现由核心层提供（如控制台日志、文件日志等）。工具层通过该接口记录日志，避免直接处理日志实现细节。

### 3. 缓存系统
提供统一的缓存接口（ICache），支持不同缓存实现（如内存、Redis、文件系统等）。工具层通过接口调用缓存服务，无需关心缓存的具体实现。

### 4. 任务调度与事件系统
通过核心层的任务调度系统与事件总线，工具层可以异步调度任务和监听事件。核心层提供统一的异步任务调度和事件总线，确保工具层无需实现复杂的任务调度逻辑。

### 5. 验证与数据传输
核心层提供所有的验证规则与数据传输对象（DTO）。工具层通过核心层提供的接口实现数据验证与传输。

## 技术栈

### 后端技术栈
- **Python 3.12+** + **FastAPI** + **SQLAlchemy** + **SQLCipher**
- **依赖注入（IoC）**：完整的服务管理和生命周期控制
- **异步处理**：Python asyncio + BackgroundTasks
- **包管理**：Poetry（Python依赖管理）

### 前端技术栈
- **Tauri** + **React** + **TypeScript** + **Tailwind CSS**
- **状态管理**：Zustand（轻量级状态管理）
- **包管理**：pnpm（Node.js包管理器）

### 数据库
- **本地数据库**：SQLCipher（加密SQLite）
- **云端数据库**：PostgreSQL（与Trans-Hub集成）

## 实现策略

### 第一阶段：构建核心服务模块
1. **实现依赖注入容器**：提供完整的服务管理与生命周期管理
2. **配置管理**：支持多环境配置，确保跨环境开发的灵活性
3. **事件总线与任务调度**：实现异步任务与事件驱动架构
4. **数据访问层**：实现数据库连接、事务管理及工作单元模式

### 第二阶段：重构工具层
1. **重构现有工具**：将现有工具迁移到新的架构，简化工具层与核心层的交互
2. **模块化开发**：优化业务逻辑，移除重复实现，确保工具层只专注于业务实现

### 第三阶段：扩展与优化
1. **新增工具模块**：基于Core Platform快速开发新工具（如歌词本地化工具、电影字幕工具等）
2. **性能优化**：优化缓存策略，提升系统响应速度，增强并发能力

## 质量保证与测试

### 单元测试与集成测试
- 核心层的模块化设计使得单元测试变得更加简单。每个模块可以独立进行单元测试，工具层则通过模拟接口进行测试。

### 代码质量与审查
- 使用 **Ruff**（Python 静态代码分析）和 **ESLint**（前端）进行代码质量检查，确保代码符合最佳实践。
- 提供严格的代码审查流程，确保代码规范性和可维护性。

## 架构优势

1. **高内聚、低耦合**：严格的分层设计确保系统的可维护性
2. **代码复用**：通用逻辑集中在Core Platform，避免重复实现
3. **一致性**：所有工具使用相同的底层架构和服务接口
4. **可扩展性**：新工具可以快速开发和集成，支持插件化架构
5. **可维护性**：清晰的分层和职责分离，便于调试和维护
6. **测试友好**：依赖注入和接口抽象便于单元测试和集成测试
7. **性能优化**：统一的缓存、任务调度等机制提升系统性能

## 下一步行动计划

### 阶段1：Core Platform基础建设（4-6周）
1. 创建Core Platform的基础架构
2. 实现IoC容器和依赖注入系统
3. 实现配置管理、日志系统、缓存系统
4. 实现事件总线和任务调度系统
5. 建立数据访问层（工作单元、仓储模式）

### 阶段2：MC工具重构（3-4周）
1. 使用新的Core Platform重构MC L10n
2. 提取MC特有的业务逻辑到工具层
3. 简化MC工具的代码，移除重复实现
4. 完善测试覆盖率

### 阶段3：架构验证与优化（2-3周）
1. 验证新架构的有效性和性能
2. 优化缓存策略和数据访问性能
3. 完善文档和开发指南
4. 为后续工具开发建立标准模板

### 阶段4：扩展新工具（按需）
基于完善的Core Platform，可以快速开发新的工具：
- RW Studio本地化工具扩展
- 其他游戏本地化工具
- 多媒体本地化工具（歌词、字幕等）

## 总结

通过本架构设计，**TH-Suite** 系统将具备高内聚、低耦合的结构，工具层开发者可以专注于业务逻辑实现，无需深入底层技术细节，提升开发效率并减少潜在的维护风险。核心层提供通用功能模块的封装，工具层通过简洁的接口调用这些功能，确保了系统的灵活性、可扩展性和易维护性。