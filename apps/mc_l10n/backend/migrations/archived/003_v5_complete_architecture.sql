-- TH-Suite MC L10n V5 完整架构 (SSOT)
-- 基于 /docs/architecture/database/v5-ssot-database-design.md
-- 创建时间: 2025-09-16
-- 说明: 完整实现16个表的企业级架构，支持键级差量同步、工作队列、多层缓存

-- ============================================================
-- PHASE 1: 核心域 core_* (9个表)
-- ============================================================

-- 1. core_projects (项目管理)
CREATE TABLE IF NOT EXISTS core_projects (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    uid TEXT UNIQUE NOT NULL,
    name TEXT NOT NULL,
    description TEXT,
    created_at TEXT NOT NULL DEFAULT (datetime('now')),
    updated_at TEXT NOT NULL DEFAULT (datetime('now'))
);

-- 2. core_packs (整合包)
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

-- 3. core_pack_versions (整合包版本)
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

-- 4. core_pack_items (清单条目=期望集)
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

-- 5. core_pack_installations (本地实例)
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

-- 6. core_mods (MOD管理)
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

-- 7. core_mod_versions (MOD版本)
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

-- 8. core_language_files (语言文件载体)
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

-- 9. core_translation_entries (翻译条目键级事实)
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

-- ============================================================
-- PHASE 2: 运维与同步 ops_* (4个表)
-- ============================================================

-- 10. ops_work_queue (单写入者任务队列)
CREATE TABLE IF NOT EXISTS ops_work_queue (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    type TEXT CHECK(type IN ('import_delta_block','export_stream','tm_index','qa_run','merge_resolve','sync_out','sync_in')) NOT NULL,
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

-- 11. ops_outbox_journal (离线变更键级差量)
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

-- 12. ops_sync_log (同步日志)
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

-- 13. ops_cas_objects (分片去重索引)
CREATE TABLE IF NOT EXISTS ops_cas_objects (
    cid TEXT PRIMARY KEY,
    size INTEGER NOT NULL,
    algo TEXT CHECK(algo IN ('zstd','gzip','none')) DEFAULT 'zstd',
    dict_id TEXT,
    ref_count INTEGER DEFAULT 1,
    created_at TEXT NOT NULL DEFAULT (datetime('now'))
);

-- ============================================================
-- PHASE 3: 配置与缓存 cfg_*/cache_* (6个表)
-- ============================================================

-- 14. cfg_local_settings (本地配置)
CREATE TABLE IF NOT EXISTS cfg_local_settings (
    key TEXT PRIMARY KEY,
    value_json TEXT CHECK(json_valid(value_json)) NOT NULL,
    updated_at TEXT NOT NULL DEFAULT (datetime('now'))
);

-- 15. cfg_file_watch (文件监控配置)
CREATE TABLE IF NOT EXISTS cfg_file_watch (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    root_path TEXT NOT NULL,
    globs TEXT CHECK(json_valid(globs)) NOT NULL,
    active BOOLEAN DEFAULT TRUE,
    created_at TEXT NOT NULL DEFAULT (datetime('now'))
);

-- 16. cache_scan_results (扫描结果缓存)
CREATE TABLE IF NOT EXISTS cache_scan_results (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    scan_path TEXT NOT NULL,
    scan_hash TEXT NOT NULL,
    result_json TEXT CHECK(json_valid(result_json)) NOT NULL,
    valid_until TEXT NOT NULL,
    created_at TEXT NOT NULL DEFAULT (datetime('now')),
    UNIQUE(scan_path, scan_hash)
);

-- 17. cache_lang_file (语言文件缓存)
CREATE TABLE IF NOT EXISTS cache_lang_file (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    file_path TEXT NOT NULL,
    file_hash TEXT NOT NULL,
    parsed_content TEXT CHECK(json_valid(parsed_content)) NOT NULL,
    valid_until TEXT NOT NULL,
    created_at TEXT NOT NULL DEFAULT (datetime('now')),
    UNIQUE(file_path, file_hash)
);

-- 18. cache_entry (翻译条目缓存)
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

-- 19. cache_stats (统计数据缓存)
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
-- PHASE 4: 性能优化索引 (必备8+扩展索引)
-- ============================================================

-- 核心业务索引
CREATE INDEX IF NOT EXISTS idx_translation_entries_file_key ON core_translation_entries(language_file_uid, key);
CREATE INDEX IF NOT EXISTS idx_language_files_carrier ON core_language_files(carrier_type, carrier_uid, locale);
CREATE INDEX IF NOT EXISTS idx_mod_versions_lookup ON core_mod_versions(mod_uid, loader, mc_version, version);
CREATE INDEX IF NOT EXISTS idx_pack_items_lookup ON core_pack_items(pack_version_uid, item_type, identity);

-- 工作队列索引
CREATE INDEX IF NOT EXISTS idx_work_queue_state ON ops_work_queue(state, not_before, priority);
CREATE UNIQUE INDEX IF NOT EXISTS idx_work_queue_dedupe ON ops_work_queue(dedupe_key) WHERE dedupe_key IS NOT NULL;

-- 同步索引
CREATE INDEX IF NOT EXISTS idx_outbox_state ON ops_outbox_journal(state, created_at);
CREATE INDEX IF NOT EXISTS idx_cas_objects_cid ON ops_cas_objects(cid);

-- 时间戳索引
CREATE INDEX IF NOT EXISTS idx_translation_entries_updated ON core_translation_entries(updated_at);
CREATE INDEX IF NOT EXISTS idx_projects_updated ON core_projects(updated_at);
CREATE INDEX IF NOT EXISTS idx_packs_updated ON core_packs(updated_at);

-- 缓存优化索引
CREATE INDEX IF NOT EXISTS idx_cache_scan_valid ON cache_scan_results(valid_until);
CREATE INDEX IF NOT EXISTS idx_cache_lang_valid ON cache_lang_file(valid_until);
CREATE INDEX IF NOT EXISTS idx_cache_entry_valid ON cache_entry(valid_until);
CREATE INDEX IF NOT EXISTS idx_cache_stats_valid ON cache_stats(valid_until);

-- UID快速查找索引
CREATE INDEX IF NOT EXISTS idx_projects_uid ON core_projects(uid);
CREATE INDEX IF NOT EXISTS idx_packs_uid ON core_packs(uid);
CREATE INDEX IF NOT EXISTS idx_pack_versions_uid ON core_pack_versions(uid);
CREATE INDEX IF NOT EXISTS idx_pack_installations_uid ON core_pack_installations(uid);
CREATE INDEX IF NOT EXISTS idx_mods_uid ON core_mods(uid);
CREATE INDEX IF NOT EXISTS idx_mod_versions_uid ON core_mod_versions(uid);
CREATE INDEX IF NOT EXISTS idx_language_files_uid ON core_language_files(uid);
CREATE INDEX IF NOT EXISTS idx_translation_entries_uid ON core_translation_entries(uid);

-- ============================================================
-- PHASE 5: 统计视图 (实时数据，替代冗余字段)
-- ============================================================

-- 缓存统计视图
CREATE VIEW IF NOT EXISTS v_cache_statistics AS
SELECT 
    'scan_results' as cache_type,
    COUNT(*) as total_entries,
    COUNT(CASE WHEN valid_until > datetime('now') THEN 1 END) as valid_entries,
    ROUND(AVG(LENGTH(result_json)), 2) as avg_size_bytes
FROM cache_scan_results
UNION ALL
SELECT 
    'lang_file' as cache_type,
    COUNT(*) as total_entries,
    COUNT(CASE WHEN valid_until > datetime('now') THEN 1 END) as valid_entries,
    ROUND(AVG(LENGTH(parsed_content)), 2) as avg_size_bytes
FROM cache_lang_file
UNION ALL
SELECT 
    'entry' as cache_type,
    COUNT(*) as total_entries,
    COUNT(CASE WHEN valid_until > datetime('now') THEN 1 END) as valid_entries,
    ROUND(AVG(LENGTH(cached_data)), 2) as avg_size_bytes
FROM cache_entry
UNION ALL
SELECT 
    'stats' as cache_type,
    COUNT(*) as total_entries,
    COUNT(CASE WHEN valid_until > datetime('now') THEN 1 END) as valid_entries,
    ROUND(AVG(LENGTH(stats_data)), 2) as avg_size_bytes
FROM cache_stats;

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
        CASE WHEN json_extract(response_meta, '$.duration_ms') IS NOT NULL 
        THEN CAST(json_extract(response_meta, '$.duration_ms') AS REAL)
        ELSE NULL END
    ), 2) as avg_duration_ms
FROM ops_sync_log
WHERE created_at > datetime('now', '-7 days')
GROUP BY direction, result;

-- 差量积压视图
CREATE VIEW IF NOT EXISTS v_delta_backlog AS
SELECT 
    entity_type,
    state,
    COUNT(*) as count,
    MIN(created_at) as oldest_pending,
    MAX(updated_at) as latest_updated
FROM ops_outbox_journal
GROUP BY entity_type, state;

-- 项目统计视图
CREATE VIEW IF NOT EXISTS v_project_statistics AS
SELECT 
    p.id as project_id,
    p.name as project_name,
    COUNT(DISTINCT pk.id) as pack_count,
    COUNT(DISTINCT pv.id) as version_count,
    COUNT(DISTINCT pi.id) as installation_count,
    COUNT(DISTINCT m.id) as mod_count,
    COUNT(DISTINCT mv.id) as mod_version_count,
    COUNT(DISTINCT lf.id) as language_file_count,
    COUNT(DISTINCT te.id) as translation_count,
    MAX(p.updated_at) as last_updated
FROM core_projects p
LEFT JOIN core_packs pk ON 1=1  -- 暂时没有直接关系
LEFT JOIN core_pack_versions pv ON pk.uid = pv.pack_uid
LEFT JOIN core_pack_installations pi ON pv.uid = pi.pack_version_uid
LEFT JOIN core_mods m ON 1=1  -- 暂时没有直接关系
LEFT JOIN core_mod_versions mv ON m.uid = mv.mod_uid
LEFT JOIN core_language_files lf ON mv.uid = lf.carrier_uid
LEFT JOIN core_translation_entries te ON lf.uid = te.language_file_uid
GROUP BY p.id, p.name;

-- ============================================================
-- PHASE 6: 数据完整性触发器
-- ============================================================

-- 更新时间戳触发器
CREATE TRIGGER IF NOT EXISTS update_projects_timestamp
    AFTER UPDATE ON core_projects
BEGIN
    UPDATE core_projects SET updated_at = datetime('now') WHERE id = NEW.id;
END;

CREATE TRIGGER IF NOT EXISTS update_packs_timestamp
    AFTER UPDATE ON core_packs
BEGIN
    UPDATE core_packs SET updated_at = datetime('now') WHERE id = NEW.id;
END;

CREATE TRIGGER IF NOT EXISTS update_pack_installations_timestamp
    AFTER UPDATE ON core_pack_installations
BEGIN
    UPDATE core_pack_installations SET updated_at = datetime('now') WHERE id = NEW.id;
END;

CREATE TRIGGER IF NOT EXISTS update_mods_timestamp
    AFTER UPDATE ON core_mods
BEGIN
    UPDATE core_mods SET updated_at = datetime('now') WHERE id = NEW.id;
END;

CREATE TRIGGER IF NOT EXISTS update_translation_entries_timestamp
    AFTER UPDATE ON core_translation_entries
BEGIN
    UPDATE core_translation_entries SET updated_at = datetime('now') WHERE id = NEW.id;
END;

CREATE TRIGGER IF NOT EXISTS update_work_queue_timestamp
    AFTER UPDATE ON ops_work_queue
BEGIN
    UPDATE ops_work_queue SET updated_at = datetime('now') WHERE id = NEW.id;
END;

CREATE TRIGGER IF NOT EXISTS update_outbox_journal_timestamp
    AFTER UPDATE ON ops_outbox_journal
BEGIN
    UPDATE ops_outbox_journal SET updated_at = datetime('now') WHERE id = NEW.id;
END;

CREATE TRIGGER IF NOT EXISTS update_cfg_settings_timestamp
    AFTER UPDATE ON cfg_local_settings
BEGIN
    UPDATE cfg_local_settings SET updated_at = datetime('now') WHERE key = NEW.key;
END;

-- 缓存清理触发器
CREATE TRIGGER IF NOT EXISTS cleanup_expired_cache_scan
    AFTER INSERT ON cache_scan_results
    WHEN (SELECT COUNT(*) FROM cache_scan_results WHERE valid_until <= datetime('now')) > 100
BEGIN
    DELETE FROM cache_scan_results WHERE valid_until <= datetime('now');
END;

-- CAS对象引用计数触发器
CREATE TRIGGER IF NOT EXISTS increment_cas_ref_count
    AFTER INSERT ON ops_outbox_journal
    WHEN NEW.diff_json LIKE '%cid%'
BEGIN
    UPDATE ops_cas_objects 
    SET ref_count = ref_count + 1 
    WHERE cid IN (
        SELECT value FROM json_each(NEW.diff_json) 
        WHERE key LIKE '%cid%'
    );
END;

-- ============================================================
-- PHASE 7: 初始配置数据
-- ============================================================

-- 默认本地配置
INSERT OR IGNORE INTO cfg_local_settings (key, value_json) VALUES 
    ('database.version', '"v5.0"'),
    ('cache.ttl.scan_results', '3600'),
    ('cache.ttl.lang_file', '1800'),
    ('cache.ttl.entry', '900'),
    ('cache.ttl.stats', '300'),
    ('sync.batch_size', '1000'),
    ('sync.compression', '"zstd"'),
    ('sync.compression_level', '6'),
    ('queue.max_attempts', '3'),
    ('queue.lease_timeout', '300'),
    ('qa.check_placeholders', 'true'),
    ('qa.check_escape_sequences', 'true'),
    ('qa.reject_empty_strings', 'false');

-- ============================================================
-- 总结
-- ============================================================
-- V5完整架构包含:
-- ✅ 9个core核心表 (projects, packs, pack_versions, pack_items, pack_installations, mods, mod_versions, language_files, translation_entries)
-- ✅ 4个ops运维表 (work_queue, outbox_journal, sync_log, cas_objects)  
-- ✅ 2个cfg配置表 (local_settings, file_watch)
-- ✅ 4个cache缓存表 (scan_results, lang_file, entry, stats)
-- ✅ 20+个性能索引
-- ✅ 5个统计视图
-- ✅ 8个数据完整性触发器
-- ✅ 默认配置数据
-- 
-- 总计: 19个表 + 5个视图 + 20+个索引 + 8个触发器
-- 支持: 键级差量同步、工作队列、多层缓存、内容寻址、配置管理