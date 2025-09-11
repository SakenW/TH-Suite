-- TH-Suite 优化数据库架构 v2.1
-- 基于 docs/optimization/02-database-optimization.md 的细粒度版本管理和数据分层设计
-- 创建时间: 2025-09-12

-- ============================================================
-- 1. packs 表 (整合包基础信息)
-- ============================================================
CREATE TABLE IF NOT EXISTS packs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,                    -- 同步: 整合包名称
    project_type TEXT NOT NULL,            -- 同步: 项目类型
    game_type TEXT DEFAULT 'minecraft',    -- 同步: 游戏类型
    description TEXT,                      -- 同步: 描述
    author TEXT,                           -- 同步: 作者
    
    -- 🏠 仅本地数据
    path TEXT UNIQUE NOT NULL,             -- 本地: 项目路径
    sync_config TEXT,                      -- 本地: 同步配置 (JSON)
    build_config TEXT,                     -- 本地: 构建配置 (JSON)
    
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    is_active BOOLEAN DEFAULT 1
);

-- ============================================================
-- 2. pack_versions 表 (整合包版本)
-- ============================================================
CREATE TABLE IF NOT EXISTS pack_versions (
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

-- ============================================================
-- 3. mod_version_instances 表 (MOD版本实例)
-- ============================================================
CREATE TABLE IF NOT EXISTS mod_version_instances (
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

-- ============================================================
-- 4. pack_mod_relations 表 (整合包-MOD关系)
-- ============================================================
CREATE TABLE IF NOT EXISTS pack_mod_relations (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    pack_version_id INTEGER NOT NULL,      -- 整合包版本ID
    mod_instance_id INTEGER NOT NULL,      -- MOD版本实例ID
    
    -- 关系属性 (同步)
    relation_type TEXT DEFAULT 'included', -- 同步: included, optional, disabled
    load_order INTEGER,                    -- 同步: 加载顺序
    config_overrides TEXT,                 -- 同步: 配置覆盖 (JSON)
    
    -- 🏠 仅本地数据
    detected_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP, -- 本地: 检测时间
    detection_method TEXT,                 -- 本地: 检测方式
    
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    FOREIGN KEY (pack_version_id) REFERENCES pack_versions (id) ON DELETE CASCADE,
    FOREIGN KEY (mod_instance_id) REFERENCES mod_version_instances (id) ON DELETE CASCADE,
    UNIQUE(pack_version_id, mod_instance_id)
);

-- ============================================================
-- 5. content_instances 表 (统一内容实例)
-- ============================================================
CREATE TABLE IF NOT EXISTS content_instances (
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

-- 内容来源枚举说明:
-- 'mod_jar'        - MOD的JAR文件内容  
-- 'pack_resource'  - 整合包资源包
-- 'quest_pack'     - 任务包内容 (FTB/HQM等)
-- 'config_file'    - 配置文件本地化
-- 'pack_docs'      - 整合包文档
-- 'override'       - 覆盖性内容

-- ============================================================
-- 6. pack_content_relations 表 (整合包-内容关系)
-- ============================================================
CREATE TABLE IF NOT EXISTS pack_content_relations (
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

-- ============================================================
-- 性能优化索引
-- ============================================================

-- packs 表索引
CREATE INDEX IF NOT EXISTS idx_packs_path ON packs(path);
CREATE INDEX IF NOT EXISTS idx_packs_project_type ON packs(project_type);
CREATE INDEX IF NOT EXISTS idx_packs_active ON packs(is_active);

-- pack_versions 表索引
CREATE INDEX IF NOT EXISTS idx_pack_versions_pack_id ON pack_versions(pack_id);
CREATE INDEX IF NOT EXISTS idx_pack_versions_minecraft ON pack_versions(minecraft_version);
CREATE INDEX IF NOT EXISTS idx_pack_versions_loader ON pack_versions(loader_type);
CREATE INDEX IF NOT EXISTS idx_pack_versions_default ON pack_versions(is_default);

-- mod_version_instances 表索引
CREATE INDEX IF NOT EXISTS idx_mod_instances_mod_id ON mod_version_instances(mod_id);
CREATE INDEX IF NOT EXISTS idx_mod_instances_version ON mod_version_instances(mod_version);
CREATE INDEX IF NOT EXISTS idx_mod_instances_name ON mod_version_instances(mod_name);

-- pack_mod_relations 表索引
CREATE INDEX IF NOT EXISTS idx_pack_mod_relations_pack ON pack_mod_relations(pack_version_id);
CREATE INDEX IF NOT EXISTS idx_pack_mod_relations_mod ON pack_mod_relations(mod_instance_id);
CREATE INDEX IF NOT EXISTS idx_pack_mod_relations_type ON pack_mod_relations(relation_type);

-- content_instances 表索引
CREATE INDEX IF NOT EXISTS idx_content_instances_key ON content_instances(content_key);
CREATE INDEX IF NOT EXISTS idx_content_instances_source ON content_instances(content_source);
CREATE INDEX IF NOT EXISTS idx_content_instances_identifier ON content_instances(source_identifier);
CREATE INDEX IF NOT EXISTS idx_content_instances_language ON content_instances(language_code);
CREATE INDEX IF NOT EXISTS idx_content_instances_type ON content_instances(content_type);

-- pack_content_relations 表索引
CREATE INDEX IF NOT EXISTS idx_pack_content_relations_pack ON pack_content_relations(pack_version_id);
CREATE INDEX IF NOT EXISTS idx_pack_content_relations_content ON pack_content_relations(content_instance_id);
CREATE INDEX IF NOT EXISTS idx_pack_content_relations_change ON pack_content_relations(change_type);

-- ============================================================
-- 统计视图 (实时统计数据，替代冗余字段)
-- ============================================================
CREATE VIEW IF NOT EXISTS pack_version_stats AS
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

-- ============================================================
-- 数据完整性约束和触发器
-- ============================================================

-- 确保至少有一个默认版本
CREATE TRIGGER IF NOT EXISTS ensure_default_version
    AFTER UPDATE ON pack_versions
    WHEN NEW.is_default = 0
BEGIN
    UPDATE pack_versions 
    SET is_default = 1 
    WHERE pack_id = NEW.pack_id 
      AND id = (
          SELECT id FROM pack_versions 
          WHERE pack_id = NEW.pack_id 
          ORDER BY created_at ASC 
          LIMIT 1
      )
      AND NOT EXISTS (
          SELECT 1 FROM pack_versions 
          WHERE pack_id = NEW.pack_id AND is_default = 1
      );
END;

-- 更新时间戳触发器
CREATE TRIGGER IF NOT EXISTS update_packs_timestamp
    AFTER UPDATE ON packs
BEGIN
    UPDATE packs SET updated_at = CURRENT_TIMESTAMP WHERE id = NEW.id;
END;

CREATE TRIGGER IF NOT EXISTS update_pack_versions_timestamp
    AFTER UPDATE ON pack_versions
BEGIN
    UPDATE pack_versions SET updated_at = CURRENT_TIMESTAMP WHERE id = NEW.id;
END;

CREATE TRIGGER IF NOT EXISTS update_mod_instances_timestamp
    AFTER UPDATE ON mod_version_instances
BEGIN
    UPDATE mod_version_instances SET updated_at = CURRENT_TIMESTAMP WHERE id = NEW.id;
END;

CREATE TRIGGER IF NOT EXISTS update_content_instances_timestamp
    AFTER UPDATE ON content_instances
BEGIN
    UPDATE content_instances SET updated_at = CURRENT_TIMESTAMP WHERE id = NEW.id;
END;