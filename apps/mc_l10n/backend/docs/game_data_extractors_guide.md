# 游戏专属数据提取器指南

## 概述

游戏专属数据提取器系统是TH-Suite v2.0的核心组件，专门用于从不同游戏的本地化文件中提取翻译数据。系统支持Minecraft、RimWorld和Factorio三种游戏，采用模块化设计，易于扩展。

## 架构设计

### 核心组件

1. **BaseGameDataExtractor**: 所有游戏提取器的基类
2. **MinecraftDataExtractor**: Minecraft专用提取器  
3. **RimWorldDataExtractor**: RimWorld专用提取器
4. **FactorioDataExtractor**: Factorio专用提取器
5. **ExtractorRegistry**: 提取器注册和管理
6. **UnifiedDataExtractionService**: 统一提取服务

### 数据流程

```
扫描结果 -> 游戏类型检测 -> 专用提取器 -> 翻译数据 -> 数据库存储 -> 事件发送
```

## 支持的游戏格式

### Minecraft

- **JSON格式** (1.13+): `assets/[namespace]/lang/[locale].json`
- **Lang格式** (1.12-): `assets/[namespace]/lang/[locale].lang`  
- **Properties格式**: 一些特殊MOD使用

**示例文件结构:**
```
mod.jar
├── assets/
│   └── testmod/
│       └── lang/
│           ├── zh_cn.json
│           └── en_us.json
└── META-INF/
    └── mods.toml
```

**JSON格式示例:**
```json
{
  "item.testmod.test_sword": "测试剑",
  "block.testmod.test_ore": "测试矿石",
  "gui.testmod.title": "测试界面"
}
```

### RimWorld

- **DefInjection XML**: `Languages/[locale]/DefInjected/[category]/[file].xml`
- **Keyed XML**: `Languages/[locale]/Keyed/[file].xml`

**示例文件结构:**
```
TestMod/
├── Languages/
│   └── ChineseSimplified/
│       ├── DefInjected/
│       │   ├── ThingDef/
│       │   │   └── Weapons.xml
│       │   └── BuildingDef/
│       │       └── Buildings.xml
│       └── Keyed/
│           └── Misc.xml
└── About/
    └── About.xml
```

**DefInjection示例:**
```xml
<?xml version="1.0" encoding="utf-8"?>
<LanguageData>
  <ThingDef.Weapon_Pistol.label>手枪</ThingDef.Weapon_Pistol.label>
  <ThingDef.Weapon_Pistol.description>一把简单的手枪</ThingDef.Weapon_Pistol.description>
</LanguageData>
```

### Factorio

- **Locale CFG格式**: `locale/[locale]/[category].cfg`

**示例文件结构:**
```
test_mod_1.0.0/
├── locale/
│   ├── zh-CN/
│   │   ├── base.cfg
│   │   └── equipment.cfg
│   └── en/
│       ├── base.cfg
│       └── equipment.cfg
└── info.json
```

**CFG格式示例:**
```ini
[entity-name]
transport-belt=传送带
inserter=机械臂

[item-name]  
iron-ore=铁矿石
copper-ore=铜矿石
```

## 使用方法

### 基本使用

```python
from infrastructure.services.unified_data_extraction_service import get_unified_extraction_service

# 获取服务实例
service = get_unified_extraction_service()

# 从扫描结果提取数据
discovered_items = [
    {
        "type": "mod",
        "mod_id": "test_mod", 
        "path": "/path/to/mod.jar",
        "language_files": [...]
    }
]

result = await service.extract_from_scan_results(discovered_items)

if result["success"]:
    print(f"提取成功: {result['statistics']['total_language_files']} 个语言文件")
    print(f"翻译条目: {result['statistics']['total_translation_entries']} 条")
```

### 性能优化提取

```python
from infrastructure.services.performance_optimized_extractor import get_performance_optimized_extractor

# 获取性能优化提取器
extractor = get_performance_optimized_extractor()

# 启用性能优化
optimization_options = {
    "max_workers": 8,
    "memory_threshold_mb": 512,
    "batch_size": 100,
    "cache_enabled": True
}

result = await extractor.extract_with_optimization(
    discovered_items, 
    optimization_options
)

# 查看性能报告
performance_report = await extractor.get_performance_report()
print(f"平均吞吐量: {performance_report['recent_performance']['average_throughput_items_per_sec']} 项目/秒")
```

### 增量提取

```python
# 首次提取
result1 = await service.extract_from_scan_results(discovered_items)

# 增量提取（只处理变更的文件）
result2 = await service.extract_incremental(discovered_items)

print(f"增量提取处理文件数: {result2['processed_files']}")
```

### 单文件提取

```python
from infrastructure.services.game_data_extractors import GameType

result = await service.extract_from_single_file(
    "/path/to/mod.jar",
    game_type=GameType.MINECRAFT,
    carrier_info={"mod_id": "test_mod", "type": "manual"}
)
```

## 缓存和优化

### 键集指纹缓存

系统使用BLAKE3哈希算法计算键集指纹，支持增量提取:

```python
from infrastructure.services.cas_keyset_cache_service import get_cas_keyset_cache_service

cache_service = get_cas_keyset_cache_service()

# 检查键集变化
changes = await cache_service.check_keyset_changes(
    carrier_uid="test_mod",
    relative_path="assets/test/lang/zh_cn.json", 
    locale="zh_cn",
    current_keys=["item.test", "block.test"]
)

if changes["has_changes"]:
    print(f"发现变更: {changes['change_type']}")
    print(f"新增键: {changes['added_keys']}")
    print(f"删除键: {changes['removed_keys']}")
```

### CAS对象存储

```python
# 存储复杂对象到CAS
object_hash = await cache_service.store_cas_object(
    object_type="extraction_result",
    content={"language_files": [...], "statistics": {...}},
    metadata={"game_type": "minecraft", "version": "1.0"}
)

# 检索对象
cas_object = await cache_service.get_cas_object(object_hash)
```

## 事件系统集成

### LANG_UPSERT事件

系统自动发送LANG_UPSERT事件用于下游处理:

```python
from infrastructure.services.lang_upsert_event_handler import get_lang_upsert_event_handler

event_handler = get_lang_upsert_event_handler()

# 处理单个事件
await event_handler.handle_lang_upsert_event(event)

# 批量处理事件
await event_handler.handle_batch_lang_upsert_events(events)
```

### 事件载荷格式

```python
{
    "language_file_uid": "lang_file_uuid",
    "locale": "zh_cn", 
    "carrier_type": "mod",
    "entry_count": 150,
    "keyset_hash": "blake3_hash_16_chars",
    "format": "json"
}
```

## 数据库集成

### Repository模式

系统使用Repository模式管理数据访问:

```python
from infrastructure.repositories.repository_factory import get_repository_factory

factory = get_repository_factory()

# 语言文件Repository
lang_file_repo = factory.get_core_language_file_repo()
lang_files = lang_file_repo.get_by_carrier("test_mod")

# 翻译条目Repository  
entry_repo = factory.get_core_translation_entry_repo()
entries = entry_repo.get_by_language_file("lang_file_uid")
```

### 批量操作

```python
# 批量插入翻译条目
translation_entries = [...]
result = entry_repo.batch_upsert(translation_entries)
print(f"创建: {result['created']}, 更新: {result['updated']}")
```

## 扩展新游戏支持

### 1. 创建游戏提取器

```python
from infrastructure.services.game_data_extractors.base_extractor import BaseGameDataExtractor, GameType, FileFormat

class NewGameDataExtractor(BaseGameDataExtractor):
    def _get_game_type(self) -> GameType:
        return GameType.NEWGAME  # 需要先在枚举中添加
    
    def _get_supported_formats(self) -> List[FileFormat]:
        return [FileFormat.XML]  # 或其他格式
    
    async def extract_from_discovered_items(self, discovered_items):
        # 实现提取逻辑
        pass
    
    async def extract_from_file(self, file_path, carrier_info):
        # 实现单文件提取
        pass
```

### 2. 注册提取器

```python
from infrastructure.services.game_data_extractors import ExtractorRegistry

# 在系统初始化时注册
ExtractorRegistry.register(GameType.NEWGAME, NewGameDataExtractor(db_path))
```

### 3. 更新游戏检测

在`ExtractorRegistry.detect_game_type`中添加新游戏的检测逻辑。

## 性能调优

### 内存优化

```python
# 内存限制提取
result = await extractor.extract_with_memory_optimization(
    discovered_items,
    memory_limit_mb=256
)
```

### 并行配置

```python
# 自定义并行工作线程数
optimization_options = {
    "max_workers": psutil.cpu_count(),  # 使用所有CPU核心
    "batch_size": 100  # 调整批次大小
}
```

### 缓存清理

```python
# 清理30天前的旧缓存
cleaned_count = await cache_service.cleanup_old_cache(days_old=30)
print(f"清理了 {cleaned_count} 条缓存记录")
```

## 监控和统计

### 提取统计

```python
stats = await service.get_extraction_statistics()
print(f"语言文件统计: {stats['language_files']}")
print(f"翻译条目统计: {stats['translation_entries']}")
```

### 缓存统计

```python
cache_stats = await cache_service.get_cache_statistics()
print(f"键集指纹数量: {cache_stats['keyset_fingerprints']['total_count']}")
print(f"CAS对象数量: {cache_stats['cas_objects']['total_count']}")
```

### 性能监控

```python
# 获取活跃会话
active_sessions = extractor.get_active_sessions()
for session_id, session_info in active_sessions.items():
    print(f"会话 {session_id}: {session_info['progress_percent']:.1f}% 完成")
```

## 故障排除

### 常见问题

1. **提取失败**: 检查文件格式和路径
2. **内存不足**: 使用内存优化模式或减少批次大小
3. **性能问题**: 启用缓存和增量提取
4. **编码问题**: 确保文件使用UTF-8编码

### 调试技巧

```python
import structlog
structlog.configure(level="DEBUG")  # 启用详细日志

# 检查游戏类型检测
detected_type = ExtractorRegistry.detect_game_type([item])
print(f"检测到游戏类型: {detected_type}")

# 验证缓存键集
cache_fingerprint = await cache_service.get_keyset_fingerprint(
    carrier_uid, relative_path, locale
)
```

## 最佳实践

1. **启用缓存**: 在生产环境中始终启用键集缓存
2. **增量提取**: 对于大型项目使用增量提取模式
3. **批量处理**: 使用批量API处理大量数据
4. **内存监控**: 监控内存使用，适时进行垃圾回收
5. **错误处理**: 实现适当的错误处理和重试机制
6. **性能测试**: 定期进行性能测试和优化

## API参考

详细的API文档请参考各个类和方法的docstring，主要包括:

- `BaseGameDataExtractor`: 基础提取器接口
- `UnifiedDataExtractionService`: 统一提取服务
- `PerformanceOptimizedExtractor`: 性能优化提取器  
- `CasKeysetCacheService`: CAS缓存服务
- `LangUpsertEventHandler`: 事件处理器

## 更新日志

- **v2.0.0**: 初始版本，支持三种游戏
- **v2.0.1**: 添加性能优化和缓存支持
- **v2.0.2**: 完善事件系统集成
- **v2.0.3**: 增强错误处理和监控功能