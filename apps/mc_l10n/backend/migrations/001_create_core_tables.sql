-- TH-Suite MC L10n - 核心业务表
-- 创建时间: 2025-09-17
-- 说明: 核心域表，包含项目、整合包、MOD、语言文件和翻译条目管理

-- ============================================================
-- 1. 项目管理
-- ============================================================

CREATE TABLE IF NOT EXISTS core_projects (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    uid TEXT UNIQUE NOT NULL,
    name TEXT NOT NULL,
    description TEXT,
    created_at TEXT NOT NULL DEFAULT (datetime('now')),
    updated_at TEXT NOT NULL DEFAULT (datetime('now'))
);

-- ============================================================
-- 2. 整合包管理
-- ============================================================

CREATE TABLE IF NOT EXISTS core_packs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    uid TEXT UNIQUE NOT NULL,
    platform TEXT CHECK(platform IN ('modrinth','curseforge','custom')) NOT NULL,
    slug TEXT NOT NULL,
    title TEXT NOT NULL,
    author TEXT,
    homepage TEXT,
    created_at TEXT NOT NULL DEFAULT (datetime('now')),
    updated_at TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS core_pack_versions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    uid TEXT UNIQUE NOT NULL,
    pack_uid TEXT NOT NULL REFERENCES core_packs(uid) ON DELETE CASCADE,
    mc_version TEXT NOT NULL,
    loader TEXT CHECK(loader IN ('forge','neoforge','fabric','quilt','multi','unknown')) NOT NULL,
    manifest_json TEXT CHECK(json_valid(manifest_json)),
    manifest_hash_b3 TEXT NOT NULL,
    manifest_hash_md5 TEXT,
    created_at TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS core_pack_items (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    pack_version_uid TEXT NOT NULL REFERENCES core_pack_versions(uid) ON DELETE CASCADE,
    item_type TEXT CHECK(item_type IN ('mod','resourcepack','datapack','override')) NOT NULL,
    source_platform TEXT CHECK(source_platform IN ('modrinth','curseforge','url','local')) NOT NULL,
    identity TEXT NOT NULL,
    constraints TEXT CHECK(json_valid(constraints)) DEFAULT '{}',
    position INTEGER NOT NULL,
    created_at TEXT NOT NULL DEFAULT (datetime('now')),
    UNIQUE(pack_version_uid, item_type, identity)
);

CREATE TABLE IF NOT EXISTS core_pack_installations (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    uid TEXT UNIQUE NOT NULL,
    pack_version_uid TEXT NOT NULL REFERENCES core_pack_versions(uid) ON DELETE CASCADE,
    root_path TEXT,
    launcher TEXT CHECK(launcher IN ('curseforge','modrinth','vanilla','custom')),
    enabled BOOLEAN DEFAULT TRUE,
    created_at TEXT NOT NULL DEFAULT (datetime('now')),
    updated_at TEXT NOT NULL DEFAULT (datetime('now'))
);

-- ============================================================
-- 3. MOD管理
-- ============================================================

CREATE TABLE IF NOT EXISTS core_mods (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    uid TEXT UNIQUE NOT NULL,
    modid TEXT UNIQUE,
    slug TEXT,
    name TEXT NOT NULL,
    homepage TEXT,
    created_at TEXT NOT NULL DEFAULT (datetime('now')),
    updated_at TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS core_mod_versions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    uid TEXT UNIQUE NOT NULL,
    mod_uid TEXT NOT NULL REFERENCES core_mods(uid) ON DELETE CASCADE,
    loader TEXT NOT NULL,
    mc_version TEXT NOT NULL,
    version TEXT NOT NULL,
    meta_json TEXT CHECK(json_valid(meta_json)) DEFAULT '{}',
    source TEXT,
    discovered_at TEXT NOT NULL DEFAULT (datetime('now')),
    UNIQUE(mod_uid, loader, mc_version, version)
);

-- ============================================================
-- 4. 语言文件和翻译条目
-- ============================================================

CREATE TABLE IF NOT EXISTS core_language_files (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    uid TEXT UNIQUE NOT NULL,
    carrier_type TEXT CHECK(carrier_type IN ('mod','resource_pack','data_pack','override')) NOT NULL,
    carrier_uid TEXT NOT NULL,
    locale TEXT NOT NULL,
    rel_path TEXT NOT NULL,
    format TEXT CHECK(format IN ('json','lang','properties')) NOT NULL,
    size INTEGER DEFAULT 0,
    discovered_at TEXT NOT NULL DEFAULT (datetime('now')),
    UNIQUE(carrier_uid, locale, rel_path)
);

CREATE TABLE IF NOT EXISTS core_translation_entries (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    uid TEXT UNIQUE NOT NULL,
    language_file_uid TEXT NOT NULL REFERENCES core_language_files(uid) ON DELETE CASCADE,
    key TEXT NOT NULL,
    src_text TEXT NOT NULL,
    dst_text TEXT DEFAULT '',
    status TEXT CHECK(status IN ('new','mt','reviewed','locked','rejected','conflict')) DEFAULT 'new',
    qa_flags TEXT CHECK(json_valid(qa_flags)) DEFAULT '{}',
    updated_at TEXT NOT NULL DEFAULT (datetime('now')),
    UNIQUE(language_file_uid, key)
);