-- 扩展 ops_work_queue 任务类型支持扫描系统
-- 新增扫描任务类型：scan_enum, scan_meta, scan_lang, scan_verify
-- 创建时间: 2025-09-17

-- ============================================================
-- 1. 首先删除依赖视图，然后删除现有的类型约束
-- ============================================================

-- 删除依赖的视图
DROP VIEW IF EXISTS v_queue_status;
DROP VIEW IF EXISTS v_sync_history;

-- 创建临时表，包含扩展的类型约束
CREATE TABLE IF NOT EXISTS ops_work_queue_new (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    type TEXT CHECK(type IN (
        -- 原有类型
        'import_delta_block','export_stream','tm_index','qa_run','merge_resolve','sync_out','sync_in',
        -- 新增扫描类型
        'scan_enum','scan_meta','scan_lang','scan_verify'
    )) NOT NULL,
    payload_json TEXT CHECK(json_valid(payload_json)) NOT NULL,
    state TEXT CHECK(state IN ('pending','leased','done','err','dead')) DEFAULT 'pending',
    priority INTEGER DEFAULT 0,
    not_before TEXT,
    dedupe_key TEXT UNIQUE,
    attempt INTEGER DEFAULT 0,
    last_error TEXT,
    lease_owner TEXT,
    lease_expires_at TEXT,
    created_at TEXT NOT NULL DEFAULT (datetime('now')),
    updated_at TEXT NOT NULL DEFAULT (datetime('now'))
);

-- 如果原表存在数据，迁移到新表
INSERT INTO ops_work_queue_new 
    (id, type, payload_json, state, priority, not_before, dedupe_key, 
     attempt, last_error, lease_owner, lease_expires_at, created_at, updated_at)
SELECT 
    id, type, payload_json, state, priority, not_before, dedupe_key,
    attempt, last_error, lease_owner, lease_expires_at,
    COALESCE(created_at, datetime('now')),
    COALESCE(updated_at, datetime('now'))
FROM ops_work_queue 
WHERE EXISTS (SELECT 1 FROM sqlite_master WHERE type='table' AND name='ops_work_queue');

-- 删除原表
DROP TABLE IF EXISTS ops_work_queue;

-- 重命名新表
ALTER TABLE ops_work_queue_new RENAME TO ops_work_queue;

-- ============================================================
-- 2. 重新创建索引
-- ============================================================

-- 工作队列索引
CREATE INDEX IF NOT EXISTS idx_work_queue_state ON ops_work_queue(state, not_before, priority);
CREATE UNIQUE INDEX IF NOT EXISTS idx_work_queue_dedupe ON ops_work_queue(dedupe_key) WHERE dedupe_key IS NOT NULL;
CREATE INDEX IF NOT EXISTS idx_work_queue_type ON ops_work_queue(type, state);
CREATE INDEX IF NOT EXISTS idx_work_queue_lease ON ops_work_queue(lease_owner, state) WHERE lease_owner IS NOT NULL;

-- ============================================================
-- 3. 重新创建触发器
-- ============================================================

DROP TRIGGER IF EXISTS update_work_queue_timestamp;

CREATE TRIGGER IF NOT EXISTS update_work_queue_timestamp
    AFTER UPDATE ON ops_work_queue
BEGIN
    UPDATE ops_work_queue SET updated_at = datetime('now') WHERE id = NEW.id;
END;

-- ============================================================
-- 4. 创建扫描任务相关的便捷视图
-- ============================================================

-- 扫描任务队列状态视图
CREATE VIEW IF NOT EXISTS v_scan_queue_status AS
SELECT 
    type,
    state,
    COUNT(*) as task_count,
    AVG(priority) as avg_priority,
    MIN(created_at) as oldest_task,
    MAX(created_at) as newest_task,
    SUM(CASE WHEN attempt > 0 THEN 1 ELSE 0 END) as retry_count
FROM ops_work_queue 
WHERE type IN ('scan_enum', 'scan_meta', 'scan_lang', 'scan_verify')
GROUP BY type, state
ORDER BY type, state;

-- 活跃扫描会话视图
CREATE VIEW IF NOT EXISTS v_active_scan_sessions AS
SELECT 
    JSON_EXTRACT(payload_json, '$.session_id') as session_id,
    type,
    COUNT(*) as task_count,
    COUNT(CASE WHEN state = 'done' THEN 1 END) as completed_tasks,
    COUNT(CASE WHEN state = 'err' THEN 1 END) as failed_tasks,
    COUNT(CASE WHEN state = 'pending' THEN 1 END) as pending_tasks,
    COUNT(CASE WHEN state = 'leased' THEN 1 END) as running_tasks,
    ROUND(100.0 * COUNT(CASE WHEN state = 'done' THEN 1 END) / COUNT(*), 2) as completion_percentage,
    MIN(created_at) as session_start,
    MAX(updated_at) as last_activity
FROM ops_work_queue 
WHERE type IN ('scan_enum', 'scan_meta', 'scan_lang', 'scan_verify')
  AND JSON_EXTRACT(payload_json, '$.session_id') IS NOT NULL
GROUP BY JSON_EXTRACT(payload_json, '$.session_id'), type
HAVING session_id IS NOT NULL
ORDER BY session_start DESC;

-- ============================================================
-- 5. 创建扫描任务优先级常量参考
-- ============================================================

-- 扫描任务优先级定义（通过注释记录）
-- 100: 可见优先 - 用户当前查看的内容
-- 70:  Δ变更 - 增量扫描中检测到的变化文件  
-- 50:  RAS补完 - Recent Active Set 中的活跃文件
-- 20:  非RAS补完 - 其他文件的补完扫描

-- ============================================================
-- 6. 示例：扫描任务payload_json 结构
-- ============================================================

/*
扫描任务 payload_json 结构示例：

scan_enum (目录枚举):
{
  "session_id": "scan_abc123",
  "snapshot_id": "snap_def456", 
  "root_path": "/path/to/modpack",
  "pack_uid": "pack_xyz789",
  "resume_from": null,
  "checkpoint": {"stage": "enum", "offset": 0}
}

scan_meta (元数据解析):
{
  "session_id": "scan_abc123",
  "snapshot_id": "snap_def456",
  "file_path": "mods/example-mod.jar",
  "file_type": "jar",
  "target_info": ["modid", "version", "loader", "mc_version"],
  "checkpoint": {"stage": "meta", "last_step": "manifest_parsed"}
}

scan_lang (语言文件处理):
{
  "session_id": "scan_abc123", 
  "snapshot_id": "snap_def456",
  "lang_file_path": "assets/examplemod/lang/en_us.json",
  "format": "json",
  "encoding": "utf-8",
  "checkpoint": {"stage": "lang", "last_key": "item.example.name"}
}

scan_verify (验证和去重):
{
  "session_id": "scan_abc123",
  "snapshot_id": "snap_def456", 
  "verify_scope": "mod_conflicts",
  "affected_mods": ["mod1", "mod2"],
  "checkpoint": {"stage": "verify", "last_verified": "duplicate_keys"}
}
*/

-- ============================================================
-- 7. 重新创建原始视图（从V5架构）
-- ============================================================

-- 队列状态视图  
CREATE VIEW IF NOT EXISTS v_queue_status AS
SELECT 
    state,
    COUNT(*) as count,
    MIN(created_at) as oldest_created,
    MAX(updated_at) as latest_updated,
    AVG(attempt) as avg_attempts
FROM ops_work_queue 
GROUP BY state;

-- 同步历史视图
CREATE VIEW IF NOT EXISTS v_sync_history AS
SELECT 
    direction,
    result,
    COUNT(*) as count,
    MAX(created_at) as latest_sync,
    ROUND(AVG(
        CASE 
            WHEN completed_at IS NOT NULL AND created_at IS NOT NULL 
            THEN (julianday(completed_at) - julianday(created_at)) * 86400 
            ELSE NULL 
        END
    ), 2) as avg_duration_seconds
FROM ops_sync_log 
GROUP BY direction, result;