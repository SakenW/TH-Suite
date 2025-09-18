-- 检查点和幂等性表
-- 支持任务中断恢复和事件去重
-- 创建时间: 2025-09-17

-- ============================================================
-- 1. 检查点表
-- ============================================================

-- 检查点存储表
CREATE TABLE IF NOT EXISTS cache_checkpoint (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    checkpoint_id TEXT UNIQUE NOT NULL,
    session_id TEXT NOT NULL,
    task_type TEXT CHECK(task_type IN ('scan_enum','scan_meta','scan_lang','scan_verify')) NOT NULL,
    entity_ref TEXT NOT NULL,  -- 实体引用（文件路径、MOD ID等）
    stage TEXT NOT NULL,       -- 当前阶段
    artifact_ref TEXT NOT NULL, -- 工件引用（快照ID、文件哈希等）
    artifact_hash TEXT,        -- 工件哈希
    last_step TEXT NOT NULL,   -- 最后完成的步骤
    offset INTEGER,            -- 处理偏移量（如文件索引、行号等）
    context_json TEXT CHECK(json_valid(context_json)) DEFAULT '{}', -- 上下文数据
    created_at TEXT NOT NULL DEFAULT (datetime('now')),
    updated_at TEXT NOT NULL DEFAULT (datetime('now'))
);

-- ============================================================
-- 2. 幂等性表
-- ============================================================

-- 幂等性记录表
CREATE TABLE IF NOT EXISTS ops_idempotency (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    idempotent_key TEXT UNIQUE NOT NULL,
    event_data TEXT CHECK(json_valid(event_data)) NOT NULL,
    created_at TEXT NOT NULL DEFAULT (datetime('now'))
);

-- ============================================================
-- 3. 索引
-- ============================================================

-- 检查点索引
CREATE INDEX IF NOT EXISTS idx_checkpoint_session ON cache_checkpoint(session_id, task_type);
CREATE INDEX IF NOT EXISTS idx_checkpoint_entity ON cache_checkpoint(session_id, task_type, entity_ref);
CREATE INDEX IF NOT EXISTS idx_checkpoint_updated ON cache_checkpoint(updated_at);

-- 幂等性索引
CREATE UNIQUE INDEX IF NOT EXISTS idx_idempotency_key ON ops_idempotency(idempotent_key);
CREATE INDEX IF NOT EXISTS idx_idempotency_created ON ops_idempotency(created_at);

-- ============================================================
-- 4. 触发器
-- ============================================================

-- 检查点更新时间触发器
CREATE TRIGGER IF NOT EXISTS update_checkpoint_timestamp
    AFTER UPDATE ON cache_checkpoint
BEGIN
    UPDATE cache_checkpoint SET updated_at = datetime('now') WHERE id = NEW.id;
END;

-- ============================================================
-- 5. 清理视图
-- ============================================================

-- 检查点统计视图
CREATE VIEW IF NOT EXISTS v_checkpoint_stats AS
SELECT 
    session_id,
    task_type,
    COUNT(*) as checkpoint_count,
    MIN(created_at) as earliest_checkpoint,
    MAX(updated_at) as latest_checkpoint,
    COUNT(DISTINCT entity_ref) as unique_entities
FROM cache_checkpoint 
GROUP BY session_id, task_type
ORDER BY latest_checkpoint DESC;

-- 幂等性统计视图
CREATE VIEW IF NOT EXISTS v_idempotency_stats AS
SELECT 
    DATE(created_at) as date,
    COUNT(*) as processed_events,
    COUNT(DISTINCT SUBSTR(idempotent_key, 1, INSTR(idempotent_key, '|') - 1)) as unique_sessions
FROM ops_idempotency 
GROUP BY DATE(created_at)
ORDER BY date DESC;