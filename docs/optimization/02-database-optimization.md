# TH-Suite 数据库结构优化方案

> **文档版本**: v1.0  
> **基于**: 01-integration-analysis.md  
> **核心目标**: 分离本地构建数据与同步数据，支持多版本管理

## 🔍 问题分析

### 当前设计缺陷
```sql
-- ❌ 问题: 项目表固化版本相关数据
CREATE TABLE projects (
    total_mods INTEGER DEFAULT 0,          -- 版本敏感
    total_language_files INTEGER DEFAULT 0, -- 版本敏感
    minecraft_versions TEXT,               -- 聚合数据
    supported_languages TEXT               -- 聚合数据
);
```

**核心问题**:
- 同一项目在不同版本下 MOD 数量不同
- 聚合数据与实际数据不同步风险
- 无法按版本维度统计分析

## 🏗️ 数据分层设计

### 数据分类原则

| 数据类型 | 存储位置 | 同步到 Trans-Hub | 示例 |
|----------|----------|------------------|------|
| **项目元信息** | 本地 + 服务器 | ✅ 是 | 项目名称、描述、作者 |
| **版本信息** | 本地 + 服务器 | ✅ 是 | 版本标签、MC版本、加载器类型 |
| **翻译内容** | 本地 + 服务器 | ✅ 是 | 翻译键值对、语言代码 |
| **构建数据** | 仅本地 | ❌ 否 | 文件路径、大小、编码、哈希 |
| **临时数据** | 仅本地 | ❌ 否 | 扫描历史、错误日志、缓存 |

## 📊 最优化表结构设计

### 核心设计理念
- **最小单位管理**: 以翻译条目为最小单位追踪版本关系
- **内容来源统一**: MOD内容、整合包专属内容、任务包统一管理
- **数据分层清晰**: 本地构建数据与同步业务数据严格分离

### 1. packs 表 (整合包基础信息)
```sql
CREATE TABLE packs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,                    -- 同步: 整合包名称
    project_type TEXT NOT NULL,            -- 同步: 项目类型
    game_type TEXT DEFAULT 'minecraft',    -- 同步: 游戏类型
    description TEXT,                      -- 同步: 描述
    author TEXT,                           -- 同步: 作者
    
    -- 🏠 仅本地数据
    path TEXT UNIQUE NOT NULL,             -- 本地: 项目路径
    sync_config TEXT,                      -- 本地: 同步配置
    build_config TEXT,                     -- 本地: 构建配置
    
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    is_active BOOLEAN DEFAULT 1
);
```

### 2. pack_versions 表 (整合包版本)
```sql
CREATE TABLE pack_versions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    pack_id INTEGER NOT NULL,              -- 关联整合包
    version_tag TEXT NOT NULL,             -- 同步: 版本标签
    minecraft_version TEXT NOT NULL,       -- 同步: MC版本
    loader_type TEXT NOT NULL,             -- 同步: 加载器类型
    loader_version TEXT,                   -- 同步: 加载器版本
    
    -- 版本元信息 (同步)
    display_name TEXT,                     -- 同步: 显示名称
    changelog TEXT,                        -- 同步: 变更日志
    is_default BOOLEAN DEFAULT 0,          -- 同步: 默认版本
    is_stable BOOLEAN DEFAULT 1,           -- 同步: 稳定版本
    
    -- 🏠 仅本地数据
    local_path TEXT,                       -- 本地: 版本路径
    build_timestamp TIMESTAMP,             -- 本地: 构建时间
    
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    FOREIGN KEY (pack_id) REFERENCES packs (id) ON DELETE CASCADE,
    UNIQUE(pack_id, version_tag)
);
```

### 3. mod_version_instances 表 (MOD版本实例)
```sql
CREATE TABLE mod_version_instances (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    mod_id TEXT NOT NULL,                  -- 同步: MOD标识符
    mod_version TEXT NOT NULL,             -- 同步: MOD版本
    mod_name TEXT NOT NULL,                -- 同步: MOD显示名称
    
    -- MOD元信息 (同步)
    description TEXT,                      -- 同步: 描述
    authors TEXT,                          -- 同步: 作者列表 (JSON)
    homepage_url TEXT,                     -- 同步: 主页链接
    minecraft_versions TEXT,               -- 同步: 兼容MC版本 (JSON)
    dependencies TEXT,                     -- 同步: 依赖关系 (JSON)
    
    -- 🏠 仅本地数据
    jar_file_path TEXT,                    -- 本地: JAR文件路径
    jar_file_size INTEGER,                 -- 本地: 文件大小
    jar_file_hash TEXT,                    -- 本地: 文件哈希
    extraction_path TEXT,                  -- 本地: 解压路径
    
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    UNIQUE(mod_id, mod_version)            -- MOD ID + 版本唯一
);
```

### 4. pack_mod_relations 表 (整合包-MOD关系)
```sql
CREATE TABLE pack_mod_relations (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    pack_version_id INTEGER NOT NULL,      -- 整合包版本ID
    mod_instance_id INTEGER NOT NULL,      -- MOD版本实例ID
    
    -- 关系属性 (同步)
    relation_type TEXT DEFAULT 'included', -- 同步: included, optional, disabled
    load_order INTEGER,                    -- 同步: 加载顺序
    config_overrides TEXT,                 -- 同步: 配置覆盖 (JSON)
    
    -- 🏠 仅本地数据
    detected_at TIMESTAMP,                 -- 本地: 检测时间
    detection_method TEXT,                 -- 本地: 检测方式
    
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    FOREIGN KEY (pack_version_id) REFERENCES pack_versions (id) ON DELETE CASCADE,
    FOREIGN KEY (mod_instance_id) REFERENCES mod_version_instances (id) ON DELETE CASCADE,
    UNIQUE(pack_version_id, mod_instance_id)
);
```

### 5. content_instances 表 (统一内容实例)
```sql
CREATE TABLE content_instances (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    content_key TEXT NOT NULL,             -- 同步: 内容键
    content_source TEXT NOT NULL,          -- 同步: 内容来源
    source_identifier TEXT NOT NULL,       -- 同步: 来源标识符
    
    -- 内容数据 (同步)
    source_text TEXT NOT NULL,             -- 同步: 源文本
    language_code TEXT NOT NULL,           -- 同步: 语言代码
    content_type TEXT NOT NULL,            -- 同步: translation/quest/config
    category TEXT,                         -- 同步: item/block/gui/quest
    comment TEXT,                          -- 同步: 注释
    
    -- 🏠 仅本地数据
    file_path TEXT NOT NULL,               -- 本地: 文件路径
    file_format TEXT NOT NULL,             -- 本地: 文件格式
    line_number INTEGER,                   -- 本地: 行号
    raw_content TEXT,                      -- 本地: 原始内容
    
    -- 元信息
    priority INTEGER DEFAULT 0,            -- 同步: 优先级(覆盖用)
    is_override BOOLEAN DEFAULT 0,         -- 同步: 是否覆盖内容
    
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    UNIQUE(content_key, content_source, source_identifier, language_code)
);

-- 内容来源枚举说明
-- content_source 可选值:
-- 'mod_jar'        - MOD的JAR文件内容  
-- 'pack_resource'  - 整合包资源包
-- 'quest_pack'     - 任务包内容 (FTB/HQM等)
-- 'config_file'    - 配置文件本地化
-- 'pack_docs'      - 整合包文档
-- 'override'       - 覆盖性内容
```

### 6. pack_content_relations 表 (整合包-内容关系)
```sql
CREATE TABLE pack_content_relations (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    pack_version_id INTEGER NOT NULL,      -- 整合包版本ID
    content_instance_id INTEGER NOT NULL,  -- 内容实例ID
    
    -- 关系属性 (同步)
    inclusion_reason TEXT,                  -- 同步: direct/dependency/override
    relative_path TEXT,                     -- 同步: 相对路径
    
    -- 覆盖信息 (同步)
    overrides_content_id INTEGER,          -- 同步: 覆盖的内容ID
    override_reason TEXT,                   -- 同步: 覆盖原因
    
    -- 变更跟踪 (同步)
    first_appeared_version TEXT,           -- 同步: 首次出现版本
    last_modified_version TEXT,            -- 同步: 最后修改版本
    change_type TEXT DEFAULT 'stable',     -- 同步: stable/modified/new/removed
    
    -- 🏠 仅本地数据
    detected_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    detection_method TEXT,                 -- 本地: 检测方式
    
    FOREIGN KEY (pack_version_id) REFERENCES pack_versions (id) ON DELETE CASCADE,
    FOREIGN KEY (content_instance_id) REFERENCES content_instances (id) ON DELETE CASCADE,
    FOREIGN KEY (overrides_content_id) REFERENCES content_instances (id) ON DELETE SET NULL,
    UNIQUE(pack_version_id, content_instance_id)
);
```

## 🔍 强大的查询能力

### 细粒度版本追踪查询
```sql
-- 1. 词条跨版本追踪: "某个词条在哪些整合包版本中存在？"
SELECT 
    p.name as pack_name,
    pv.version_tag as pack_version,
    pv.minecraft_version,
    mvi.mod_id,
    mvi.mod_version,
    ci.source_text,
    pcr.change_type,
    pcr.first_appeared_version
FROM content_instances ci
JOIN pack_content_relations pcr ON ci.id = pcr.content_instance_id
JOIN pack_versions pv ON pcr.pack_version_id = pv.id  
JOIN packs p ON pv.pack_id = p.id
LEFT JOIN mod_version_instances mvi ON ci.source_identifier = mvi.mod_id
WHERE ci.content_key = 'item.jei.recipe_book'
ORDER BY pv.minecraft_version DESC, mvi.mod_version DESC;

-- 2. MOD跨整合包分布: "MOD JEI 在哪些整合包版本中？"
SELECT 
    p.name as pack_name,
    pv.version_tag as pack_version,
    pv.minecraft_version,
    mvi.mod_version,
    pmr.relation_type,
    pmr.load_order,
    COUNT(DISTINCT ci.id) as translation_count
FROM mod_version_instances mvi
JOIN pack_mod_relations pmr ON mvi.id = pmr.mod_instance_id
JOIN pack_versions pv ON pmr.pack_version_id = pv.id
JOIN packs p ON pv.pack_id = p.id
LEFT JOIN content_instances ci ON ci.source_identifier = mvi.mod_id AND ci.content_source = 'mod_jar'
WHERE mvi.mod_id = 'jei'
GROUP BY p.id, pv.id, mvi.id
ORDER BY pv.minecraft_version DESC, mvi.mod_version DESC;

-- 3. 版本差异分析: "两个整合包版本的内容差异"
WITH version_1_content AS (
    SELECT ci.content_key, ci.content_source, ci.source_identifier, ci.source_text
    FROM pack_content_relations pcr
    JOIN content_instances ci ON pcr.content_instance_id = ci.id
    WHERE pcr.pack_version_id = 1
),
version_2_content AS (
    SELECT ci.content_key, ci.content_source, ci.source_identifier, ci.source_text
    FROM pack_content_relations pcr  
    JOIN content_instances ci ON pcr.content_instance_id = ci.id
    WHERE pcr.pack_version_id = 2
)
SELECT 
    COALESCE(v1.content_key, v2.content_key) as content_key,
    COALESCE(v1.content_source, v2.content_source) as content_source,
    v1.source_text as version_1_text,
    v2.source_text as version_2_text,
    CASE 
        WHEN v1.content_key IS NULL THEN 'ADDED'
        WHEN v2.content_key IS NULL THEN 'REMOVED' 
        WHEN v1.source_text != v2.source_text THEN 'MODIFIED'
        ELSE 'UNCHANGED'
    END as change_type
FROM version_1_content v1
FULL OUTER JOIN version_2_content v2 
    ON v1.content_key = v2.content_key 
    AND v1.content_source = v2.content_source
    AND v1.source_identifier = v2.source_identifier;

-- 4. 整合包专属内容查询: "整合包的专属任务和资源"
SELECT 
    ci.content_source,
    ci.content_type,
    ci.content_key,
    ci.source_text,
    pcr.relative_path,
    pcr.override_reason
FROM content_instances ci
JOIN pack_content_relations pcr ON ci.id = pcr.content_instance_id  
JOIN pack_versions pv ON pcr.pack_version_id = pv.id
WHERE pv.id = 1 
  AND ci.content_source IN ('pack_resource', 'quest_pack', 'config_file', 'pack_docs', 'override')
ORDER BY ci.content_source, ci.content_type;

-- 5. 覆盖关系分析: "资源包覆盖了哪些MOD内容？"
SELECT 
    original.content_key,
    original.source_text as original_text,
    original.source_identifier as original_mod,
    override.source_text as override_text,
    pcr.override_reason,
    pcr.relative_path
FROM pack_content_relations pcr
JOIN content_instances original ON pcr.overrides_content_id = original.id
JOIN content_instances override ON pcr.content_instance_id = override.id
WHERE pcr.pack_version_id = 1 AND pcr.overrides_content_id IS NOT NULL;
```

### 统计视图
```sql
-- 整合包版本统计视图
CREATE VIEW pack_version_stats AS
SELECT 
    p.id as pack_id,
    p.name as pack_name,
    pv.id as version_id,
    pv.version_tag,
    pv.minecraft_version,
    
    -- MOD统计
    COUNT(DISTINCT pmr.mod_instance_id) as total_mods,
    COUNT(DISTINCT CASE WHEN pmr.relation_type = 'included' THEN pmr.mod_instance_id END) as included_mods,
    
    -- 内容统计  
    COUNT(DISTINCT pcr.content_instance_id) as total_content,
    COUNT(DISTINCT CASE WHEN ci.content_source = 'mod_jar' THEN pcr.content_instance_id END) as mod_content,
    COUNT(DISTINCT CASE WHEN ci.content_source = 'pack_resource' THEN pcr.content_instance_id END) as pack_resources,
    COUNT(DISTINCT CASE WHEN ci.content_source = 'quest_pack' THEN pcr.content_instance_id END) as quest_content,
    
    -- 语言统计
    COUNT(DISTINCT ci.language_code) as supported_languages
    
FROM packs p
JOIN pack_versions pv ON p.id = pv.pack_id
LEFT JOIN pack_mod_relations pmr ON pv.id = pmr.pack_version_id
LEFT JOIN pack_content_relations pcr ON pv.id = pcr.pack_version_id
LEFT JOIN content_instances ci ON pcr.content_instance_id = ci.id
GROUP BY p.id, pv.id;
```

## 📋 迁移检查清单

### 数据清理任务
- [ ] 识别当前冗余字段
- [ ] 备份现有数据
- [ ] 创建新表结构
- [ ] 数据迁移脚本
- [ ] 验证数据完整性

### 代码更新任务
- [ ] 更新 ORM 模型定义
- [ ] 重构统计查询逻辑
- [ ] 更新业务服务层
- [ ] 调整数据访问层
- [ ] 更新测试用例

---

*下一步: 阅读 SDK 集成改进计划*