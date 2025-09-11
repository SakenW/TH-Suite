# TH-Suite v2.0 数据库架构文档

> **版本**: v2.0 Core-First架构  
> **更新时间**: 2025-09-12  
> **适用范围**: Minecraft L10n、RW Studio等游戏本地化应用

## 📖 概述

TH-Suite v2.0采用SQLite数据库存储项目数据，支持加密存储（SQLCipher）。数据库设计遵循关系型设计原则，支持完整的CRUD操作、外键约束和事务管理。

### 🎯 设计原则

- **数据一致性**: 外键约束确保数据完整性
- **可扩展性**: JSON字段支持元数据存储和功能扩展
- **性能优化**: 完整的索引策略，支持快速查询
- **软删除**: 项目采用软删除策略，保留历史数据
- **审计追踪**: 完整的时间戳记录，支持数据追踪

---

## 📊 数据库表结构

### 1. projects 表 - 项目主表

**用途**: 存储游戏本地化项目的基本信息

```sql
CREATE TABLE IF NOT EXISTS projects (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,                    -- 项目名称
    path TEXT UNIQUE NOT NULL,             -- 项目路径（唯一约束）
    project_type TEXT NOT NULL,            -- 项目类型：'modpack', 'mod', 'resourcepack'
    game_type TEXT NOT NULL DEFAULT 'minecraft',  -- 游戏类型
    loader_type TEXT,                      -- 加载器类型：'forge', 'fabric', 'quilt', 'neoforge'
    minecraft_versions TEXT,               -- 支持的MC版本 (JSON数组)
    total_mods INTEGER DEFAULT 0,          -- 包含的MOD总数
    total_language_files INTEGER DEFAULT 0, -- 语言文件总数
    supported_languages TEXT,              -- 支持的语言列表 (JSON数组)
    metadata TEXT,                         -- 扩展元数据 (JSON对象)
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    last_scan_at TIMESTAMP,               -- 最后扫描时间
    is_active BOOLEAN DEFAULT 1           -- 软删除标记
);
```

**字段说明**:
- `project_type`: 区分整合包、单独MOD、资源包等项目类型
- `loader_type`: 自动检测的MOD加载器类型，影响后续处理策略
- `minecraft_versions`: JSON数组，支持多版本兼容性检查
- `supported_languages`: 从扫描结果汇总的语言支持情况
- `metadata`: 存储项目特定的配置信息和扩展属性

**索引**:
```sql
CREATE INDEX IF NOT EXISTS idx_projects_path ON projects (path);
CREATE INDEX IF NOT EXISTS idx_projects_type ON projects (project_type);
```

---

### 2. mods 表 - MOD信息表

**用途**: 存储项目中包含的MOD详细信息

```sql
CREATE TABLE IF NOT EXISTS mods (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    project_id INTEGER NOT NULL,          -- 关联项目ID
    name TEXT NOT NULL,                   -- MOD显示名称
    mod_id TEXT NOT NULL,                 -- MOD唯一标识符
    version TEXT,                         -- MOD版本号
    description TEXT,                     -- MOD描述
    authors TEXT,                         -- 作者列表 (JSON数组)
    file_path TEXT NOT NULL,              -- JAR文件路径
    file_size INTEGER DEFAULT 0,          -- 文件大小（字节）
    loader_type TEXT,                     -- MOD加载器类型
    minecraft_versions TEXT,              -- 兼容的MC版本 (JSON数组)
    dependencies TEXT,                    -- 依赖关系 (JSON对象)
    language_files_count INTEGER DEFAULT 0, -- 包含的语言文件数量
    supported_languages TEXT,             -- 支持的语言 (JSON数组)
    metadata TEXT,                        -- MOD特定元数据 (JSON对象)
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (project_id) REFERENCES projects (id) ON DELETE CASCADE
);
```

**字段说明**:
- `mod_id`: 从mods.toml、fabric.mod.json等配置文件提取的唯一ID
- `authors`: JSON数组，支持多作者情况
- `dependencies`: JSON对象，包含必需依赖、可选依赖等信息
- `loader_type`: 支持Forge、Fabric、Quilt、NeoForge等加载器
- `metadata`: 存储加载器特定的配置信息

**索引**:
```sql
CREATE INDEX IF NOT EXISTS idx_mods_project_id ON mods (project_id);
CREATE INDEX IF NOT EXISTS idx_mods_mod_id ON mods (mod_id);
```

---

### 3. language_files 表 - 语言文件表

**用途**: 存储从MOD中提取的语言文件信息

```sql
CREATE TABLE IF NOT EXISTS language_files (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    project_id INTEGER NOT NULL,          -- 关联项目ID
    mod_id INTEGER,                       -- 关联MOD ID（项目级文件可为NULL）
    file_path TEXT NOT NULL,              -- 文件相对路径
    full_path TEXT NOT NULL,              -- 文件完整路径
    language_code TEXT,                   -- 语言代码：'en_us', 'zh_cn'等
    file_format TEXT NOT NULL,            -- 文件格式：'json', 'properties', 'yaml'
    file_size INTEGER DEFAULT 0,          -- 文件大小（字节）
    is_archived BOOLEAN DEFAULT 0,        -- 是否从JAR内提取
    encoding TEXT DEFAULT 'utf-8',        -- 文件编码
    keys_count INTEGER DEFAULT 0,         -- 翻译键数量
    hash_value TEXT,                      -- 文件内容哈希（用于增量检测）
    metadata TEXT,                        -- 文件特定元数据 (JSON对象)
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (project_id) REFERENCES projects (id) ON DELETE CASCADE,
    FOREIGN KEY (mod_id) REFERENCES mods (id) ON DELETE CASCADE
);
```

**字段说明**:
- `mod_id`: NULL表示项目级资源包文件，非NULL表示MOD内语言文件
- `language_code`: 从文件名自动识别的语言代码
- `file_format`: 支持JSON、Properties、YAML、TOML等格式
- `is_archived`: 区分直接文件和JAR内文件，影响提取和修改策略
- `hash_value`: SHA256或BLAKE3哈希，用于检测文件变更
- `keys_count`: 预计算的翻译条目数量，用于统计和进度显示

**索引**:
```sql
CREATE INDEX IF NOT EXISTS idx_language_files_project_id ON language_files (project_id);
CREATE INDEX IF NOT EXISTS idx_language_files_mod_id ON language_files (mod_id);
CREATE INDEX IF NOT EXISTS idx_language_files_language ON language_files (language_code);
```

---

### 4. language_entries 表 - 翻译条目表

**用途**: 存储语言文件中的具体翻译条目（可选，用于详细翻译管理）

```sql
CREATE TABLE IF NOT EXISTS language_entries (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    language_file_id INTEGER NOT NULL,    -- 关联语言文件ID
    key_name TEXT NOT NULL,               -- 翻译键名
    value_text TEXT,                      -- 翻译值
    comment TEXT,                         -- 注释信息
    metadata TEXT,                        -- 条目元数据 (JSON对象)
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (language_file_id) REFERENCES language_files (id) ON DELETE CASCADE,
    UNIQUE(language_file_id, key_name)    -- 同一文件内键名唯一
);
```

**字段说明**:
- `key_name`: 翻译键，如"item.minecraft.apple"
- `value_text`: 对应的翻译文本
- `comment`: 从源文件提取的注释信息
- `metadata`: 存储键值对的额外信息，如占位符信息、格式化标记等

**索引**:
```sql
CREATE INDEX IF NOT EXISTS idx_language_entries_file_id ON language_entries (language_file_id);
```

---

### 5. scan_history 表 - 扫描历史表

**用途**: 记录项目扫描操作的历史和统计信息

```sql
CREATE TABLE IF NOT EXISTS scan_history (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    project_id INTEGER NOT NULL,          -- 关联项目ID
    scan_type TEXT NOT NULL,              -- 扫描类型：'full', 'incremental'
    scan_status TEXT NOT NULL,            -- 扫描状态：'success', 'failed', 'partial'
    files_scanned INTEGER DEFAULT 0,      -- 扫描的文件数量
    mods_found INTEGER DEFAULT 0,         -- 发现的MOD数量
    language_files_found INTEGER DEFAULT 0, -- 发现的语言文件数量
    errors_count INTEGER DEFAULT 0,       -- 错误数量
    duration_seconds REAL DEFAULT 0,      -- 扫描耗时（秒）
    scan_summary TEXT,                    -- 扫描摘要 (JSON对象)
    error_details TEXT,                   -- 错误详情 (JSON对象)
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (project_id) REFERENCES projects (id) ON DELETE CASCADE
);
```

**字段说明**:
- `scan_type`: 区分全量扫描和增量扫描
- `scan_status`: 跟踪扫描完成状态
- `scan_summary`: JSON对象，包含扫描统计信息和发现的问题
- `error_details`: JSON对象，记录扫描过程中的错误信息
- `duration_seconds`: 性能监控和优化参考

**索引**:
```sql
CREATE INDEX IF NOT EXISTS idx_scan_history_project_id ON scan_history (project_id);
```

---

## 🔗 关系图

```
projects (1) -----> (*) mods
    |                   |
    |                   v
    +---------------> (*) language_files
    |                   |
    |                   v
    +---------------> (*) language_entries
    |
    v
(*) scan_history
```

### 关系说明

1. **projects → mods**: 一对多，一个项目包含多个MOD
2. **projects → language_files**: 一对多，项目级语言文件（资源包）
3. **mods → language_files**: 一对多，MOD内语言文件
4. **language_files → language_entries**: 一对多，文件内翻译条目
5. **projects → scan_history**: 一对多，项目扫描历史记录

---

## 📈 性能优化

### 索引策略

| 表名 | 索引字段 | 用途 |
|------|----------|------|
| projects | path | 按路径快速查找项目 |
| projects | project_type | 按类型筛选项目 |
| mods | project_id | 查询项目MOD列表 |
| mods | mod_id | MOD去重和依赖解析 |
| language_files | project_id | 查询项目语言文件 |
| language_files | mod_id | 查询MOD语言文件 |
| language_files | language_code | 按语言筛选文件 |
| language_entries | language_file_id | 查询文件翻译条目 |
| scan_history | project_id | 查询项目扫描历史 |

### 查询优化建议

1. **分页查询**: 大量数据使用LIMIT + OFFSET
2. **条件筛选**: 优先使用索引字段过滤
3. **JSON查询**: 避免在WHERE子句中使用JSON函数
4. **批量操作**: 使用事务和批量插入提升性能

---

## 🔒 数据安全

### 加密存储

- **SQLCipher**: 数据库文件级加密
- **密码管理**: 安全的密钥派生和存储
- **备份加密**: 备份文件同样加密保护

### 数据完整性

- **外键约束**: 确保引用完整性
- **唯一约束**: 防止数据重复
- **事务管理**: 保证操作原子性
- **软删除**: 防止误删重要数据

---

## 🔄 数据迁移

### 版本升级策略

1. **向后兼容**: 新版本保持旧版本数据兼容
2. **增量更新**: ALTER TABLE添加新字段
3. **数据迁移**: 脚本化的数据格式转换
4. **备份恢复**: 升级前自动备份数据

### 迁移脚本示例

```sql
-- 添加新字段（示例）
ALTER TABLE projects ADD COLUMN sync_status TEXT DEFAULT 'pending';

-- 更新现有数据
UPDATE projects SET sync_status = 'completed' WHERE last_scan_at IS NOT NULL;

-- 创建新索引
CREATE INDEX IF NOT EXISTS idx_projects_sync_status ON projects (sync_status);
```

---

## 📝 使用示例

### 基本查询操作

```python
# 获取项目及其MOD信息
async def get_project_with_mods(project_id: int):
    project = await repository.get_project_by_id(project_id)
    mods = await repository.get_mods_by_project(project_id)
    return {"project": project, "mods": mods}

# 统计项目语言支持情况
async def get_language_stats(project_id: int):
    query = """
        SELECT language_code, COUNT(*) as file_count, SUM(keys_count) as total_keys
        FROM language_files 
        WHERE project_id = ? 
        GROUP BY language_code
        ORDER BY file_count DESC
    """
    return await db.fetch_all(query, [project_id])
```

### 事务操作示例

```python
# 原子性保存扫描结果
async def save_scan_result_atomic(project_id: int, scan_result: ProjectScanResult):
    async with MinecraftUnitOfWork(repository) as uow:
        await uow.repository.update_project(project_id, scan_result.project_info)
        await uow.repository.add_mods_bulk(project_id, scan_result.mods_info)
        await uow.repository.add_language_files_bulk(project_id, scan_result.language_files)
        await uow.commit()
```

---

## 📚 相关文档

- [TH-Suite架构设计](./architecture/overview.md)
- [Minecraft适配器实现](./adapters/minecraft-adapter.md)
- [数据库迁移指南](./migration/database-migration.md)
- [性能优化建议](./performance/database-optimization.md)

---

*文档版本: v2.0.0*  
*最后更新: 2025-09-12*  
*维护者: TH-Suite开发团队*