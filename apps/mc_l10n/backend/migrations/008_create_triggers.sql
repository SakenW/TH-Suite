-- TH-Suite MC L10n - 触发器
-- 创建时间: 2025-09-17
-- 说明: 数据完整性触发器，自动维护时间戳、引用计数和缓存清理

-- ============================================================
-- 1. 时间戳更新触发器
-- ============================================================

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

-- ============================================================
-- 2. 缓存清理触发器
-- ============================================================

CREATE TRIGGER IF NOT EXISTS cleanup_expired_cache_scan
    AFTER INSERT ON cache_scan_results
    WHEN (SELECT COUNT(*) FROM cache_scan_results WHERE valid_until <= datetime('now')) > 100
BEGIN
    DELETE FROM cache_scan_results WHERE valid_until <= datetime('now');
END;

CREATE TRIGGER IF NOT EXISTS cleanup_expired_cache_lang
    AFTER INSERT ON cache_lang_file
    WHEN (SELECT COUNT(*) FROM cache_lang_file WHERE valid_until <= datetime('now')) > 100
BEGIN
    DELETE FROM cache_lang_file WHERE valid_until <= datetime('now');
END;

CREATE TRIGGER IF NOT EXISTS cleanup_expired_cache_entry
    AFTER INSERT ON cache_entry
    WHEN (SELECT COUNT(*) FROM cache_entry WHERE valid_until <= datetime('now')) > 500
BEGIN
    DELETE FROM cache_entry WHERE valid_until <= datetime('now');
END;

CREATE TRIGGER IF NOT EXISTS cleanup_expired_cache_stats
    AFTER INSERT ON cache_stats
    WHEN (SELECT COUNT(*) FROM cache_stats WHERE valid_until <= datetime('now')) > 50
BEGIN
    DELETE FROM cache_stats WHERE valid_until <= datetime('now');
END;

CREATE TRIGGER IF NOT EXISTS cleanup_expired_checkpoint
    AFTER INSERT ON cache_checkpoint
    WHEN (SELECT COUNT(*) FROM cache_checkpoint WHERE expires_at <= datetime('now')) > 50
BEGIN
    DELETE FROM cache_checkpoint WHERE expires_at <= datetime('now');
END;

CREATE TRIGGER IF NOT EXISTS cleanup_expired_idempotency
    AFTER INSERT ON ops_idempotency
    WHEN (SELECT COUNT(*) FROM ops_idempotency WHERE expires_at <= datetime('now')) > 100
BEGIN
    DELETE FROM ops_idempotency WHERE expires_at <= datetime('now');
END;

-- ============================================================
-- 3. 引用计数管理触发器
-- ============================================================

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

CREATE TRIGGER IF NOT EXISTS decrement_cas_ref_count
    AFTER DELETE ON ops_outbox_journal
    WHEN OLD.diff_json LIKE '%cid%'
BEGIN
    UPDATE ops_cas_objects 
    SET ref_count = ref_count - 1 
    WHERE cid IN (
        SELECT value FROM json_each(OLD.diff_json) 
        WHERE key LIKE '%cid%'
    );
    -- 清理引用计数为0的对象
    DELETE FROM ops_cas_objects WHERE ref_count <= 0;
END;

CREATE TRIGGER IF NOT EXISTS increment_content_addressed_ref_count
    AFTER INSERT ON cache_content_addressed
BEGIN
    UPDATE cache_content_addressed 
    SET last_accessed = datetime('now') 
    WHERE content_hash = NEW.content_hash;
END;

CREATE TRIGGER IF NOT EXISTS update_content_addressed_access
    AFTER UPDATE ON cache_content_addressed
    WHEN NEW.ref_count > OLD.ref_count
BEGIN
    UPDATE cache_content_addressed 
    SET last_accessed = datetime('now') 
    WHERE id = NEW.id;
END;

-- ============================================================
-- 4. 缓存命中计数触发器
-- ============================================================

CREATE TRIGGER IF NOT EXISTS update_cache_entry_hit_count
    AFTER UPDATE ON cache_entry
    WHEN NEW.hit_count > OLD.hit_count
BEGIN
    UPDATE cache_entry 
    SET valid_until = datetime('now', '+' || (NEW.hit_count * 10) || ' minutes')
    WHERE id = NEW.id;
END;

-- ============================================================
-- 5. 扫描会话状态维护触发器
-- ============================================================

CREATE TRIGGER IF NOT EXISTS update_scan_session_completed
    AFTER UPDATE ON cache_scan_sessions
    WHEN NEW.state IN ('completed', 'cancelled', 'failed') AND OLD.completed_at IS NULL
BEGIN
    UPDATE cache_scan_sessions 
    SET completed_at = datetime('now') 
    WHERE id = NEW.id;
END;