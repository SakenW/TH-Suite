-- TH-Suite MC L10n 分层异步增量扫描架构 (基于V5 SSOT)
-- 基于 /home/saken/project/TH-Suite/扫描规则.md 和 TODO.md 规格设计
-- 创建时间: 2025-09-16
-- 目标: 实现1-2秒首屏响应、渐进式补全、中断可续扫、增量更新的扫描架构

-- ============================================================
-- PHASE 1: 快照引擎表 (Snapshot Engine)
-- ============================================================

-- cache_scan_snapshots: 文件系统快照存储
CREATE TABLE IF NOT EXISTS cache_scan_snapshots (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    snapshot_id TEXT UNIQUE NOT NULL,
    session_id TEXT NOT NULL,
    pack_uid TEXT,                           -- 关联到core_packs.uid (可选)
    pack_version_uid TEXT,                   -- 关联到core_pack_versions.uid (可选)
    root_path TEXT NOT NULL,                 -- 扫描根路径
    files_json TEXT CHECK(json_valid(files_json)) NOT NULL, -- 文件快照数据
    snapshot_hash TEXT NOT NULL,             -- 快照内容BLAKE3哈希
    file_count INTEGER DEFAULT 0,            -- 文件总数
    total_size_bytes INTEGER DEFAULT 0,      -- 总大小（字节）
    created_at TEXT NOT NULL DEFAULT (datetime('now')),
    
    -- 索引和约束
    UNIQUE(root_path, snapshot_hash)
);

-- cache_scan_delta: 增量变化记录
CREATE TABLE IF NOT EXISTS cache_scan_delta (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    snapshot_id TEXT NOT NULL REFERENCES cache_scan_snapshots(snapshot_id) ON DELETE CASCADE,
    session_id TEXT NOT NULL,
    base_snapshot_id TEXT,                   -- 基准快照ID
    delta_json TEXT CHECK(json_valid(delta_json)) NOT NULL, -- 变化数据
    delta_hash TEXT NOT NULL,                -- 变化内容BLAKE3哈希
    affected_files INTEGER DEFAULT 0,        -- 影响的文件数
    touched_mods TEXT CHECK(json_valid(touched_mods)) DEFAULT '[]', -- 受影响MOD列表
    created_at TEXT NOT NULL DEFAULT (datetime('now'))
);

-- ============================================================
-- PHASE 2: 事件流水表 (Event Log) - 可选但推荐
-- ============================================================

-- ops_event_log: 扫描事件流水，支持幂等和重放
CREATE TABLE IF NOT EXISTS ops_event_log (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    event_id TEXT UNIQUE NOT NULL,           -- 事件唯一标识
    session_id TEXT NOT NULL,                -- 扫描会话ID
    event_type TEXT CHECK(event_type IN (
        'LIST_UPSERT',     -- 列表行上屏/更新
        'FIELD_PATCH',     -- 版本/作者/loader/语言数
        'LANG_UPSERT',     -- language_file与entries增量
        'COUNT_PATCH',     -- 计数/统计更新
        'TOMB_STONE',      -- 删除/移动墓碑
        'CONFLICT',        -- 冲突标记
        'PROGRESS',        -- 会话/行内进度
        'ERROR'            -- 错误徽章与重试
    )) NOT NULL,
    entity_ref TEXT NOT NULL,                -- 实体引用 (mod_uid, file_uid等)
    stage TEXT,                              -- 处理阶段
    artifact_hash TEXT,                      -- 处理产物哈希 (可选)
    payload_json TEXT CHECK(json_valid(payload_json)) NOT NULL, -- 事件载荷
    idempotency_key TEXT UNIQUE NOT NULL,    -- 幂等键: session_id + event_type + entity_ref + stage + artifact_hash
    processed BOOLEAN DEFAULT FALSE,         -- 是否已处理
    retry_count INTEGER DEFAULT 0,           -- 重试次数
    created_at TEXT NOT NULL DEFAULT (datetime('now')),
    processed_at TEXT                        -- 处理完成时间
);

-- ============================================================
-- PHASE 3: 扩展现有ops_work_queue表类型 (不修改表结构)
-- ============================================================
-- 注意: 这里不修改ops_work_queue表结构，只是记录新增的type枚举值
-- 实际修改将在代码层面的枚举定义中进行

-- 新增扫描任务类型:
-- - 'scan_enum': 目录枚举和manifest解析
-- - 'scan_meta': MOD元数据解析 (mods.toml/fabric.mod.json/mcmod.info)
-- - 'scan_lang': 语言文件解析 (.json/.lang/.properties)
-- - 'scan_verify': 去重/冲突检测/统计/墓碑标记

-- ============================================================
-- PHASE 4: 扫描会话管理表
-- ============================================================

-- cache_scan_sessions: 扫描会话状态管理
CREATE TABLE IF NOT EXISTS cache_scan_sessions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    session_id TEXT UNIQUE NOT NULL,
    scan_type TEXT CHECK(scan_type IN ('full', 'incremental', 'delta')) DEFAULT 'full',
    root_path TEXT NOT NULL,
    snapshot_id TEXT REFERENCES cache_scan_snapshots(snapshot_id),
    state TEXT CHECK(state IN (
        'discovering',    -- 文件发现阶段
        'analyzing',      -- 文件分析阶段
        'extracting',     -- 内容提取阶段
        'processing',     -- 数据处理阶段
        'finalizing',     -- 结果整理阶段
        'completed',      -- 扫描完成
        'cancelled',      -- 用户取消
        'failed',         -- 扫描失败
        'interrupted'     -- 中断待恢复
    )) DEFAULT 'discovering',
    priority INTEGER DEFAULT 50,             -- 优先级: 可见优先(100) > Δ变更(70) > RAS补完(50) > 非RAS补完(20)
    progress_json TEXT CHECK(json_valid(progress_json)) DEFAULT '{}', -- 进度信息
    config_json TEXT CHECK(json_valid(config_json)) DEFAULT '{}',   -- 扫描配置
    checkpoint_json TEXT CHECK(json_valid(checkpoint_json)) DEFAULT '{}', -- 检查点数据
    error_info TEXT,                         -- 错误信息
    started_at TEXT NOT NULL DEFAULT (datetime('now')),
    completed_at TEXT,
    updated_at TEXT NOT NULL DEFAULT (datetime('now'))
);

-- ============================================================
-- PHASE 5: 近期活跃集 (RAS) 管理表
-- ============================================================

-- cache_recent_active_set: 近期活跃集管理
CREATE TABLE IF NOT EXISTS cache_recent_active_set (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    pack_uid TEXT,                           -- 整合包UID
    pack_version_uid TEXT,                   -- 整合包版本UID  
    entity_type TEXT CHECK(entity_type IN ('pack', 'pack_version', 'mod', 'mod_version')) NOT NULL,
    entity_uid TEXT NOT NULL,                -- 实体UID
    access_count INTEGER DEFAULT 1,          -- 访问次数
    last_accessed TEXT NOT NULL DEFAULT (datetime('now')), -- 最后访问时间
    pinned BOOLEAN DEFAULT FALSE,            -- 是否手动pin
    enabled_installation BOOLEAN DEFAULT FALSE, -- 是否存在启用安装
    created_at TEXT NOT NULL DEFAULT (datetime('now')),
    
    UNIQUE(entity_type, entity_uid)
);

-- ============================================================
-- PHASE 6: 内容寻址系统扩展
-- ============================================================

-- cache_content_addressed: 内容寻址缓存扩展
CREATE TABLE IF NOT EXISTS cache_content_addressed (
    cid TEXT PRIMARY KEY,                    -- 内容标识符 (BLAKE3)
    content_type TEXT CHECK(content_type IN ('META', 'LANG', 'STATS', 'INDEX')) NOT NULL,
    value_type TEXT,                         -- 值类型 (json, binary, text)
    size_bytes INTEGER NOT NULL,
    dict_id TEXT,                            -- 字典ID (用于压缩)
    keyset_hash TEXT,                        -- 键集指纹 (用于LANG类型)
    metadata_json TEXT CHECK(json_valid(metadata_json)) DEFAULT '{}', -- 元数据
    ref_count INTEGER DEFAULT 1,
    created_at TEXT NOT NULL DEFAULT (datetime('now')),
    last_accessed TEXT NOT NULL DEFAULT (datetime('now')),
    
    -- 关联到现有的ops_cas_objects
    FOREIGN KEY (cid) REFERENCES ops_cas_objects(cid) ON DELETE CASCADE
);

-- ============================================================
-- PHASE 7: 性能优化索引
-- ============================================================

-- 快照相关索引
CREATE INDEX IF NOT EXISTS idx_scan_snapshots_session ON cache_scan_snapshots(session_id);
CREATE INDEX IF NOT EXISTS idx_scan_snapshots_path ON cache_scan_snapshots(root_path);
CREATE INDEX IF NOT EXISTS idx_scan_snapshots_created ON cache_scan_snapshots(created_at);
CREATE INDEX IF NOT EXISTS idx_scan_snapshots_pack ON cache_scan_snapshots(pack_uid, pack_version_uid);

-- 增量变化索引
CREATE INDEX IF NOT EXISTS idx_scan_delta_snapshot ON cache_scan_delta(snapshot_id);
CREATE INDEX IF NOT EXISTS idx_scan_delta_session ON cache_scan_delta(session_id);
CREATE INDEX IF NOT EXISTS idx_scan_delta_created ON cache_scan_delta(created_at);

-- 事件流水索引
CREATE INDEX IF NOT EXISTS idx_event_log_session ON ops_event_log(session_id, created_at);
CREATE INDEX IF NOT EXISTS idx_event_log_type ON ops_event_log(event_type, entity_ref);
CREATE INDEX IF NOT EXISTS idx_event_log_processed ON ops_event_log(processed, created_at);
CREATE INDEX IF NOT EXISTS idx_event_log_idempotency ON ops_event_log(idempotency_key);

-- 扫描会话索引
CREATE INDEX IF NOT EXISTS idx_scan_sessions_state ON cache_scan_sessions(state, priority);
CREATE INDEX IF NOT EXISTS idx_scan_sessions_snapshot ON cache_scan_sessions(snapshot_id);
CREATE INDEX IF NOT EXISTS idx_scan_sessions_updated ON cache_scan_sessions(updated_at);

-- RAS索引
CREATE INDEX IF NOT EXISTS idx_ras_entity ON cache_recent_active_set(entity_type, entity_uid);
CREATE INDEX IF NOT EXISTS idx_ras_accessed ON cache_recent_active_set(last_accessed);
CREATE INDEX IF NOT EXISTS idx_ras_pinned ON cache_recent_active_set(pinned);

-- 内容寻址索引
CREATE INDEX IF NOT EXISTS idx_cas_content_type ON cache_content_addressed(content_type);
CREATE INDEX IF NOT EXISTS idx_cas_keyset ON cache_content_addressed(keyset_hash);
CREATE INDEX IF NOT EXISTS idx_cas_accessed ON cache_content_addressed(last_accessed);

-- ============================================================
-- PHASE 8: 统计视图扩展
-- ============================================================

-- 扫描会话统计视图
CREATE VIEW IF NOT EXISTS v_scan_session_statistics AS
SELECT 
    state,
    scan_type,
    COUNT(*) as count,
    AVG(CASE 
        WHEN completed_at IS NOT NULL AND started_at IS NOT NULL 
        THEN (julianday(completed_at) - julianday(started_at)) * 86400 
        ELSE NULL 
    END) as avg_duration_seconds,
    MIN(started_at) as earliest_started,
    MAX(CASE WHEN state = 'completed' THEN completed_at ELSE NULL END) as latest_completed
FROM cache_scan_sessions
GROUP BY state, scan_type;

-- 快照增量统计视图
CREATE VIEW IF NOT EXISTS v_snapshot_delta_statistics AS
SELECT 
    COUNT(DISTINCT s.snapshot_id) as total_snapshots,
    COUNT(d.id) as total_deltas,
    AVG(s.file_count) as avg_files_per_snapshot,
    AVG(s.total_size_bytes) as avg_snapshot_size_bytes,
    AVG(d.affected_files) as avg_affected_files_per_delta,
    MAX(s.created_at) as latest_snapshot,
    MAX(d.created_at) as latest_delta
FROM cache_scan_snapshots s
LEFT JOIN cache_scan_delta d ON s.snapshot_id = d.snapshot_id;

-- 事件处理统计视图
CREATE VIEW IF NOT EXISTS v_event_processing_statistics AS
SELECT 
    event_type,
    COUNT(*) as total_events,
    COUNT(CASE WHEN processed THEN 1 END) as processed_events,
    COUNT(CASE WHEN NOT processed THEN 1 END) as pending_events,
    AVG(retry_count) as avg_retry_count,
    MAX(created_at) as latest_event
FROM ops_event_log
GROUP BY event_type;

-- RAS活跃度统计视图
CREATE VIEW IF NOT EXISTS v_ras_activity_statistics AS
SELECT 
    entity_type,
    COUNT(*) as total_entities,
    COUNT(CASE WHEN pinned THEN 1 END) as pinned_entities,
    COUNT(CASE WHEN enabled_installation THEN 1 END) as installed_entities,
    COUNT(CASE WHEN last_accessed > datetime('now', '-14 days') THEN 1 END) as recently_active,
    AVG(access_count) as avg_access_count,
    MAX(last_accessed) as latest_access
FROM cache_recent_active_set
GROUP BY entity_type;

-- ============================================================
-- PHASE 9: 数据完整性触发器
-- ============================================================

-- 扫描会话更新时间戳触发器
CREATE TRIGGER IF NOT EXISTS update_scan_sessions_timestamp
    AFTER UPDATE ON cache_scan_sessions
BEGIN
    UPDATE cache_scan_sessions SET updated_at = datetime('now') WHERE id = NEW.id;
END;

-- RAS访问时间更新触发器
CREATE TRIGGER IF NOT EXISTS update_ras_access_time
    AFTER UPDATE ON cache_recent_active_set
    WHEN OLD.access_count != NEW.access_count
BEGIN
    UPDATE cache_recent_active_set 
    SET last_accessed = datetime('now')
    WHERE id = NEW.id;
END;

-- 事件日志处理状态触发器
CREATE TRIGGER IF NOT EXISTS update_event_processed_time
    AFTER UPDATE ON ops_event_log
    WHEN OLD.processed != NEW.processed AND NEW.processed = TRUE
BEGIN
    UPDATE ops_event_log 
    SET processed_at = datetime('now')
    WHERE id = NEW.id;
END;

-- 内容寻址访问时间触发器
CREATE TRIGGER IF NOT EXISTS update_cas_access_time
    AFTER UPDATE ON cache_content_addressed
    WHEN OLD.ref_count != NEW.ref_count
BEGIN
    UPDATE cache_content_addressed 
    SET last_accessed = datetime('now')
    WHERE cid = NEW.cid;
END;

-- 快照清理触发器 (保留最近50个快照)
CREATE TRIGGER IF NOT EXISTS cleanup_old_snapshots
    AFTER INSERT ON cache_scan_snapshots
    WHEN (SELECT COUNT(*) FROM cache_scan_snapshots) > 50
BEGIN
    DELETE FROM cache_scan_snapshots 
    WHERE id IN (
        SELECT id FROM cache_scan_snapshots 
        ORDER BY created_at ASC 
        LIMIT (SELECT COUNT(*) FROM cache_scan_snapshots) - 50
    );
END;

-- RAS自动清理触发器 (14天未访问且未pin的条目)
CREATE TRIGGER IF NOT EXISTS cleanup_inactive_ras
    AFTER INSERT ON cache_recent_active_set
    WHEN (SELECT COUNT(*) FROM cache_recent_active_set) > 1000
BEGIN
    DELETE FROM cache_recent_active_set 
    WHERE pinned = FALSE 
    AND enabled_installation = FALSE 
    AND last_accessed < datetime('now', '-14 days');
END;

-- ============================================================
-- PHASE 10: 初始配置扩展
-- ============================================================

-- 扩展本地配置 (增量扫描相关)
INSERT OR IGNORE INTO cfg_local_settings (key, value_json) VALUES 
    -- 快照配置
    ('scan.snapshot.max_retain', '50'),
    ('scan.snapshot.enable_delta', 'true'),
    ('scan.snapshot.hash_algorithm', '"blake3"'),
    
    -- RAS配置
    ('scan.ras.recent_days', '14'),
    ('scan.ras.min_opens', '1'),
    ('scan.ras.respect_installations', 'true'),
    ('scan.ras.auto_cleanup', 'true'),
    
    -- CAS配置
    ('scan.cas.quota_gb', '3'),
    ('scan.cas.ras_quota_gb', '1'),
    ('scan.cas.retention_days', '14'),
    ('scan.cas.enable_keyset_hash', 'true'),
    
    -- 队列配置
    ('scan.queue.resume_priority', '"visible_then_delta"'),
    ('scan.queue.max_retries', '3'),
    ('scan.queue.backoff_seconds', '[1, 3, 7]'),
    
    -- 增量扫描配置
    ('scan.delta.use_manifest_delta', 'true'),
    ('scan.delta.file_quick_check', '["size_mtime", "jar_central_crc"]'),
    ('scan.delta.use_keyset_hash', 'true');

-- ============================================================
-- 总结
-- ============================================================
-- 分层异步增量扫描架构扩展:
-- ✅ 5个新增表 (scan_snapshots, scan_delta, event_log, scan_sessions, recent_active_set)
-- ✅ 1个CAS扩展表 (content_addressed)
-- ✅ 扩展ops_work_queue类型支持 (scan_enum, scan_meta, scan_lang, scan_verify)
-- ✅ 15+个性能优化索引
-- ✅ 4个新统计视图
-- ✅ 6个数据完整性触发器
-- ✅ 增量扫描相关配置
-- 
-- 支持特性:
-- 🎯 1-2秒首屏响应 (快照缓存)
-- 🔄 渐进式补全 (事件驱动)  
-- 🛡️ 中断可续扫 (检查点机制)
-- ⚡ 增量更新 (快照-Δ模型)
-- 📦 内容寻址缓存 (CAS)
-- 🏷️ 近期活跃集 (RAS)
-- 🔧 键集指纹加速