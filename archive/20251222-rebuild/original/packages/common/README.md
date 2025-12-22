# TH-Suite Common Package

**创建日期**: 2025-09-06  
**版本**: v1.0.0  
**用途**: TH-Suite项目通用功能包

## 📦 包结构

```
packages/common/
├── database/           # 数据库基础组件
│   ├── base.py        # Repository基类、Entity基类、UnitOfWork、QueryBuilder
│   ├── connection.py  # 连接池管理、数据库管理器
│   └── transaction.py # 事务管理、乐观锁、分布式锁、发件箱模式
│
├── cache/             # 缓存管理
│   └── manager.py     # CacheManager、LRU/TTL策略、缓存装饰器、多级缓存
│
├── scanner/           # 扫描框架
│   ├── base.py       # BaseScanner、增量扫描器、批量扫描器
│   └── pipeline.py   # 扫描管道、异步管道、管道构建器
│
└── sync/              # 同步框架
    ├── client.py     # SyncClient基类、增量同步、冲突检测
    └── conflict.py   # 冲突解决器、三路合并、字段级解决
```

## 🚀 核心功能

### 1. 数据库组件 (database/)

#### BaseRepository
- 提供CRUD操作的抽象接口
- 内置连接池管理
- 支持泛型类型

#### UnitOfWork
- 事务管理模式实现
- 支持多Repository协作
- 自动提交/回滚

#### QueryBuilder
- 流式API构建SQL查询
- 支持JOIN、WHERE、ORDER BY等
- 类型安全的参数绑定

#### ConnectionPool
- 线程安全的连接池
- 自动连接管理
- 性能优化（WAL模式、缓存等）

#### TransactionManager
- 事务生命周期管理
- 保存点支持
- 装饰器模式

### 2. 缓存管理 (cache/)

#### CacheManager
- 多种缓存策略（LRU、TTL）
- 统计信息收集
- get_or_set便捷方法

#### 缓存装饰器
```python
@cached(ttl=3600, key_prefix="api")
def expensive_operation():
    pass
```

#### MultiLevelCache
- 多级缓存支持
- 自动回填机制
- 统一的API接口

### 3. 扫描框架 (scanner/)

#### BaseScanner
- 文件扫描抽象基类
- 并发扫描支持
- 进度回调机制

#### IncrementalScanner
- 基于文件变化的增量扫描
- 缓存管理
- 性能优化

#### ScanPipeline
- 管道式处理流程
- 可组合的处理阶段
- 异步处理支持

### 4. 同步框架 (sync/)

#### SyncClient
- 双向同步基础实现
- 变化检测
- 冲突识别

#### ConflictResolver
- 多种冲突解决策略
- 三路合并算法
- 字段级别解决
- 链式解决器

## 💡 使用示例

### 数据库操作
```python
from packages.common.database import BaseRepository, BaseEntity

class UserRepository(BaseRepository):
    table_name = "users"
    
    def find_by_email(self, email: str):
        with self.get_connection() as conn:
            cursor = conn.execute(
                f"SELECT * FROM {self.table_name} WHERE email = ?",
                (email,)
            )
            return cursor.fetchone()
```

### 缓存使用
```python
from packages.common.cache import CacheManager, LRUCache

cache = CacheManager(strategy=LRUCache(max_size=1000))

# 存储和获取
cache.set("key", "value", ttl=3600)
value = cache.get("key", default="default")

# 获取或设置
result = cache.get_or_set(
    "expensive_key",
    lambda: expensive_computation(),
    ttl=7200
)
```

### 扫描器实现
```python
from packages.common.scanner import BaseScanner

class ModScanner(BaseScanner):
    def scan_file(self, file_path):
        # 实现具体的扫描逻辑
        result = ScanResult(
            path=str(file_path),
            file_type="mod",
            size=file_path.stat().st_size,
            content_hash=self._calculate_file_hash(file_path)
        )
        return result

# 使用
scanner = ModScanner(
    root_path="/path/to/mods",
    include_patterns=["*.jar"],
    max_workers=8
)

for result in scanner.scan():
    print(f"Scanned: {result.path}")
```

### 同步客户端
```python
from packages.common.sync import SyncClient, ConflictResolution

class MyDataSync(SyncClient):
    def get_local_items(self):
        # 返回本地数据项
        pass
    
    def get_remote_items(self, sync_token=None):
        # 返回远程数据项
        pass
    
    def push_item(self, item):
        # 推送到远程
        pass
    
    def pull_item(self, item):
        # 从远程拉取
        pass

# 执行同步
sync = MyDataSync(conflict_resolution=ConflictResolution.NEWEST)
results = sync.sync()
print(f"Synced: pushed={results['pushed']}, pulled={results['pulled']}")
```

## 🔧 配置要求

- Python 3.12+
- SQLite 3.35+（用于WAL模式）
- 线程安全支持

## 📝 注意事项

1. **线程安全**: 所有组件都设计为线程安全
2. **性能优化**: 使用连接池和缓存提升性能
3. **错误处理**: 完善的异常处理和日志记录
4. **可扩展性**: 基于抽象基类，易于扩展

## 🚦 下一步计划

- [ ] 添加单元测试
- [ ] 性能基准测试
- [ ] 文档完善
- [ ] 示例代码

## 📄 许可证

MIT License

---

**最后更新**: 2025-09-06 16:40