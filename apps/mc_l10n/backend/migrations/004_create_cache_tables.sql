-- TH-Suite MC L10n - 缓存表
-- 创建时间: 2025-09-17
-- 说明: 多层缓存系统表，包含扫描结果、语言文件、翻译条目和统计数据缓存

-- ============================================================
-- 1. 扫描结果缓存表
-- ============================================================

CREATE TABLE IF NOT EXISTS cache_scan_results (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    scan_path TEXT NOT NULL,
    scan_hash TEXT NOT NULL,
    result_json TEXT CHECK(json_valid(result_json)) NOT NULL,
    valid_until TEXT NOT NULL,
    created_at TEXT NOT NULL DEFAULT (datetime('now')),
    UNIQUE(scan_path, scan_hash)
);

-- ============================================================
-- 2. 语言文件缓存表
-- ============================================================

CREATE TABLE IF NOT EXISTS cache_lang_file (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    file_path TEXT NOT NULL,
    file_hash TEXT NOT NULL,
    parsed_content TEXT CHECK(json_valid(parsed_content)) NOT NULL,
    valid_until TEXT NOT NULL,
    created_at TEXT NOT NULL DEFAULT (datetime('now')),
    UNIQUE(file_path, file_hash)
);

-- ============================================================
-- 3. 翻译条目缓存表
-- ============================================================

CREATE TABLE IF NOT EXISTS cache_entry (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    entry_key TEXT NOT NULL,
    language_code TEXT NOT NULL,
    cached_data TEXT CHECK(json_valid(cached_data)) NOT NULL,
    hit_count INTEGER DEFAULT 0,
    valid_until TEXT NOT NULL,
    created_at TEXT NOT NULL DEFAULT (datetime('now')),
    UNIQUE(entry_key, language_code)
);

-- ============================================================
-- 4. 统计数据缓存表
-- ============================================================

CREATE TABLE IF NOT EXISTS cache_stats (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    stats_type TEXT NOT NULL,
    stats_key TEXT NOT NULL,
    stats_data TEXT CHECK(json_valid(stats_data)) NOT NULL,
    valid_until TEXT NOT NULL,
    created_at TEXT NOT NULL DEFAULT (datetime('now')),
    UNIQUE(stats_type, stats_key)
);

-- ============================================================
-- 5. 检查点缓存表
-- ============================================================

CREATE TABLE IF NOT EXISTS cache_checkpoint (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    checkpoint_key TEXT UNIQUE NOT NULL,
    checkpoint_data TEXT CHECK(json_valid(checkpoint_data)) NOT NULL,
    expires_at TEXT NOT NULL,
    created_at TEXT NOT NULL DEFAULT (datetime('now'))
);