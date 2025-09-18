-- TH-Suite MC L10n - 运维操作表
-- 创建时间: 2025-09-17
-- 说明: 运维操作表，包含工作队列、同步日志、差量记录和内容寻址存储

-- ============================================================
-- 1. 工作队列表
-- ============================================================

CREATE TABLE IF NOT EXISTS ops_work_queue (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    type TEXT CHECK(type IN (
        -- 传统同步类型
        'import_delta_block','export_stream','tm_index','qa_run','merge_resolve','sync_out','sync_in',
        -- 扫描任务类型
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

-- ============================================================
-- 2. 事件流水表 (可选)
-- ============================================================

CREATE TABLE IF NOT EXISTS ops_event_log (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    event_id TEXT UNIQUE NOT NULL,
    session_id TEXT NOT NULL,
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
    entity_ref TEXT NOT NULL,
    stage TEXT,
    artifact_hash TEXT,
    payload_json TEXT CHECK(json_valid(payload_json)) NOT NULL,
    idempotency_key TEXT UNIQUE NOT NULL,
    processed BOOLEAN DEFAULT FALSE,
    retry_count INTEGER DEFAULT 0,
    created_at TEXT NOT NULL DEFAULT (datetime('now')),
    processed_at TEXT
);

-- ============================================================
-- 3. 离线变更差量记录表
-- ============================================================

CREATE TABLE IF NOT EXISTS ops_outbox_journal (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    entity_uid TEXT NOT NULL,
    entity_type TEXT NOT NULL,
    base_version TEXT,
    diff_json TEXT CHECK(json_valid(diff_json)) NOT NULL,
    idempotency_key TEXT UNIQUE NOT NULL,
    state TEXT CHECK(state IN ('pending','sent','acked','err')) DEFAULT 'pending',
    created_at TEXT NOT NULL DEFAULT (datetime('now')),
    updated_at TEXT NOT NULL DEFAULT (datetime('now'))
);

-- ============================================================
-- 4. 同步日志表
-- ============================================================

CREATE TABLE IF NOT EXISTS ops_sync_log (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    direction TEXT CHECK(direction IN ('up','down')) NOT NULL,
    endpoint TEXT NOT NULL,
    request_meta TEXT CHECK(json_valid(request_meta)),
    response_meta TEXT CHECK(json_valid(response_meta)),
    result TEXT CHECK(result IN ('success','fail','partial')) NOT NULL,
    idempotency_key TEXT,
    created_at TEXT NOT NULL DEFAULT (datetime('now'))
);

-- ============================================================
-- 5. 内容寻址存储表
-- ============================================================

CREATE TABLE IF NOT EXISTS ops_cas_objects (
    cid TEXT PRIMARY KEY,
    size INTEGER NOT NULL,
    algo TEXT CHECK(algo IN ('zstd','gzip','none')) DEFAULT 'zstd',
    dict_id TEXT,
    ref_count INTEGER DEFAULT 1,
    created_at TEXT NOT NULL DEFAULT (datetime('now'))
);

-- ============================================================
-- 6. 幂等性和去重表
-- ============================================================

CREATE TABLE IF NOT EXISTS ops_idempotency (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    key TEXT UNIQUE NOT NULL,
    result_json TEXT CHECK(json_valid(result_json)),
    expires_at TEXT NOT NULL,
    created_at TEXT NOT NULL DEFAULT (datetime('now'))
);