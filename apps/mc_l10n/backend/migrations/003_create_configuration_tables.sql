-- TH-Suite MC L10n - 配置表
-- 创建时间: 2025-09-17
-- 说明: 系统配置表，包含本地设置和文件监控配置

-- ============================================================
-- 1. 本地设置表
-- ============================================================

CREATE TABLE IF NOT EXISTS cfg_local_settings (
    key TEXT PRIMARY KEY,
    value_json TEXT CHECK(json_valid(value_json)) NOT NULL,
    updated_at TEXT NOT NULL DEFAULT (datetime('now'))
);

-- ============================================================
-- 2. 文件监控配置表
-- ============================================================

CREATE TABLE IF NOT EXISTS cfg_file_watch (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    root_path TEXT NOT NULL,
    globs TEXT CHECK(json_valid(globs)) NOT NULL,
    active BOOLEAN DEFAULT TRUE,
    created_at TEXT NOT NULL DEFAULT (datetime('now'))
);