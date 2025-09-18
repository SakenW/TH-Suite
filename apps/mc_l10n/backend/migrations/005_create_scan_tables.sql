-- TH-Suite MC L10n - 扫描架构表
-- 创建时间: 2025-09-17
-- 说明: 分层异步增量扫描架构表，支持文件快照、增量变更、会话管理和内容寻址

-- ============================================================
-- 1. 扫描快照表
-- ============================================================

CREATE TABLE IF NOT EXISTS cache_scan_snapshots (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    snapshot_id TEXT UNIQUE NOT NULL,
    session_id TEXT NOT NULL,
    pack_uid TEXT,
    pack_version_uid TEXT,
    root_path TEXT NOT NULL,
    files_json TEXT CHECK(json_valid(files_json)) NOT NULL,
    snapshot_hash TEXT NOT NULL,
    file_count INTEGER DEFAULT 0,
    total_size_bytes INTEGER DEFAULT 0,
    created_at TEXT NOT NULL DEFAULT (datetime('now')),
    UNIQUE(root_path, snapshot_hash)
);

-- ============================================================
-- 2. 扫描增量变更表
-- ============================================================

CREATE TABLE IF NOT EXISTS cache_scan_delta (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    snapshot_id TEXT NOT NULL REFERENCES cache_scan_snapshots(snapshot_id) ON DELETE CASCADE,
    session_id TEXT NOT NULL,
    base_snapshot_id TEXT,
    delta_json TEXT CHECK(json_valid(delta_json)) NOT NULL,
    delta_hash TEXT NOT NULL,
    affected_files INTEGER DEFAULT 0,
    touched_mods TEXT CHECK(json_valid(touched_mods)) DEFAULT '[]',
    created_at TEXT NOT NULL DEFAULT (datetime('now'))
);

-- ============================================================
-- 3. 扫描会话管理表
-- ============================================================

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
        'failed'          -- 扫描失败
    )) DEFAULT 'discovering',
    progress_json TEXT CHECK(json_valid(progress_json)) DEFAULT '{}',
    stats_json TEXT CHECK(json_valid(stats_json)) DEFAULT '{}',
    error_message TEXT,
    started_at TEXT NOT NULL DEFAULT (datetime('now')),
    completed_at TEXT,
    last_checkpoint TEXT
);

-- ============================================================
-- 4. 最近活跃集合表
-- ============================================================

CREATE TABLE IF NOT EXISTS cache_recent_active_set (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    session_id TEXT NOT NULL,
    file_path TEXT NOT NULL,
    file_hash TEXT NOT NULL,
    last_accessed TEXT NOT NULL DEFAULT (datetime('now')),
    access_frequency INTEGER DEFAULT 1,
    priority_score REAL DEFAULT 0.0,
    UNIQUE(session_id, file_path)
);

-- ============================================================
-- 5. 内容寻址缓存表
-- ============================================================

CREATE TABLE IF NOT EXISTS cache_content_addressed (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    content_hash TEXT UNIQUE NOT NULL,
    content_type TEXT CHECK(content_type IN (
        'lang_file',      -- 语言文件内容
        'manifest',       -- 清单文件内容
        'mod_metadata',   -- MOD元数据
        'scan_result'     -- 扫描结果
    )) NOT NULL,
    compressed_data BLOB NOT NULL,
    compression_algo TEXT CHECK(compression_algo IN ('zstd','gzip','none')) DEFAULT 'zstd',
    original_size INTEGER NOT NULL,
    compressed_size INTEGER NOT NULL,
    ref_count INTEGER DEFAULT 1,
    created_at TEXT NOT NULL DEFAULT (datetime('now')),
    last_accessed TEXT NOT NULL DEFAULT (datetime('now'))
);