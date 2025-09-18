-- TH-Suite MC L10n - 索引和约束
-- 创建时间: 2025-09-17
-- 说明: 性能优化索引和数据完整性约束

-- ============================================================
-- 核心业务表索引
-- ============================================================

-- UID快速查找索引
CREATE INDEX IF NOT EXISTS idx_projects_uid ON core_projects(uid);
CREATE INDEX IF NOT EXISTS idx_packs_uid ON core_packs(uid);
CREATE INDEX IF NOT EXISTS idx_pack_versions_uid ON core_pack_versions(uid);
CREATE INDEX IF NOT EXISTS idx_pack_installations_uid ON core_pack_installations(uid);
CREATE INDEX IF NOT EXISTS idx_mods_uid ON core_mods(uid);
CREATE INDEX IF NOT EXISTS idx_mod_versions_uid ON core_mod_versions(uid);
CREATE INDEX IF NOT EXISTS idx_language_files_uid ON core_language_files(uid);
CREATE INDEX IF NOT EXISTS idx_translation_entries_uid ON core_translation_entries(uid);

-- 时间戳索引
CREATE INDEX IF NOT EXISTS idx_projects_updated ON core_projects(updated_at);
CREATE INDEX IF NOT EXISTS idx_packs_updated ON core_packs(updated_at);
CREATE INDEX IF NOT EXISTS idx_translation_entries_updated ON core_translation_entries(updated_at);

-- 核心业务查询索引
CREATE INDEX IF NOT EXISTS idx_translation_entries_file_key ON core_translation_entries(language_file_uid, key);
CREATE INDEX IF NOT EXISTS idx_language_files_carrier ON core_language_files(carrier_type, carrier_uid, locale);
CREATE INDEX IF NOT EXISTS idx_mod_versions_lookup ON core_mod_versions(mod_uid, loader, mc_version, version);
CREATE INDEX IF NOT EXISTS idx_pack_items_lookup ON core_pack_items(pack_version_uid, item_type, identity);

-- ============================================================
-- 运维操作表索引
-- ============================================================

-- 工作队列索引
CREATE INDEX IF NOT EXISTS idx_work_queue_state ON ops_work_queue(state, not_before, priority);
CREATE UNIQUE INDEX IF NOT EXISTS idx_work_queue_dedupe ON ops_work_queue(dedupe_key) WHERE dedupe_key IS NOT NULL;
CREATE INDEX IF NOT EXISTS idx_work_queue_type ON ops_work_queue(type, state);
CREATE INDEX IF NOT EXISTS idx_work_queue_lease ON ops_work_queue(lease_owner, state) WHERE lease_owner IS NOT NULL;

-- 事件日志索引
CREATE INDEX IF NOT EXISTS idx_event_log_session ON ops_event_log(session_id, created_at);
CREATE INDEX IF NOT EXISTS idx_event_log_idempotency ON ops_event_log(idempotency_key);
CREATE INDEX IF NOT EXISTS idx_event_log_processed ON ops_event_log(processed, created_at);

-- 同步相关索引
CREATE INDEX IF NOT EXISTS idx_outbox_state ON ops_outbox_journal(state, created_at);
CREATE INDEX IF NOT EXISTS idx_sync_log_created ON ops_sync_log(created_at);
CREATE INDEX IF NOT EXISTS idx_cas_objects_cid ON ops_cas_objects(cid);

-- 幂等性索引
CREATE INDEX IF NOT EXISTS idx_idempotency_expires ON ops_idempotency(expires_at);

-- ============================================================
-- 缓存表索引
-- ============================================================

-- 缓存过期清理索引
CREATE INDEX IF NOT EXISTS idx_cache_scan_valid ON cache_scan_results(valid_until);
CREATE INDEX IF NOT EXISTS idx_cache_lang_valid ON cache_lang_file(valid_until);
CREATE INDEX IF NOT EXISTS idx_cache_entry_valid ON cache_entry(valid_until);
CREATE INDEX IF NOT EXISTS idx_cache_stats_valid ON cache_stats(valid_until);
CREATE INDEX IF NOT EXISTS idx_cache_checkpoint_expires ON cache_checkpoint(expires_at);

-- 缓存查找索引
CREATE INDEX IF NOT EXISTS idx_cache_entry_hit_count ON cache_entry(hit_count DESC);

-- ============================================================
-- 扫描架构表索引
-- ============================================================

-- 快照查找索引
CREATE INDEX IF NOT EXISTS idx_scan_snapshots_session ON cache_scan_snapshots(session_id);
CREATE INDEX IF NOT EXISTS idx_scan_snapshots_root_path ON cache_scan_snapshots(root_path);
CREATE INDEX IF NOT EXISTS idx_scan_snapshots_created ON cache_scan_snapshots(created_at);

-- 增量变更索引
CREATE INDEX IF NOT EXISTS idx_scan_delta_snapshot ON cache_scan_delta(snapshot_id);
CREATE INDEX IF NOT EXISTS idx_scan_delta_session ON cache_scan_delta(session_id);

-- 会话管理索引
CREATE INDEX IF NOT EXISTS idx_scan_sessions_state ON cache_scan_sessions(state, started_at);
CREATE INDEX IF NOT EXISTS idx_scan_sessions_root_path ON cache_scan_sessions(root_path);

-- 活跃集合索引
CREATE INDEX IF NOT EXISTS idx_recent_active_session ON cache_recent_active_set(session_id);
CREATE INDEX IF NOT EXISTS idx_recent_active_accessed ON cache_recent_active_set(last_accessed);
CREATE INDEX IF NOT EXISTS idx_recent_active_priority ON cache_recent_active_set(priority_score DESC);

-- 内容寻址索引
CREATE INDEX IF NOT EXISTS idx_content_addressed_hash ON cache_content_addressed(content_hash);
CREATE INDEX IF NOT EXISTS idx_content_addressed_type ON cache_content_addressed(content_type);
CREATE INDEX IF NOT EXISTS idx_content_addressed_ref_count ON cache_content_addressed(ref_count);
CREATE INDEX IF NOT EXISTS idx_content_addressed_accessed ON cache_content_addressed(last_accessed);