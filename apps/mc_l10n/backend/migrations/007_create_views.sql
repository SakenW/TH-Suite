-- TH-Suite MC L10n - 视图
-- 创建时间: 2025-09-17
-- 说明: 统计和监控视图，提供实时数据汇总

-- ============================================================
-- 1. 缓存统计视图
-- ============================================================

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

-- ============================================================
-- 2. 工作队列状态视图
-- ============================================================

CREATE VIEW IF NOT EXISTS v_queue_status AS
SELECT 
    state,
    COUNT(*) as count,
    MIN(created_at) as oldest_created,
    MAX(updated_at) as latest_updated,
    AVG(attempt) as avg_attempts
FROM ops_work_queue 
GROUP BY state;

-- ============================================================
-- 3. 扫描任务队列状态视图
-- ============================================================

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

-- ============================================================
-- 4. 活跃扫描会话视图
-- ============================================================

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
-- 5. 同步历史视图
-- ============================================================

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

-- ============================================================
-- 6. 差量积压视图
-- ============================================================

CREATE VIEW IF NOT EXISTS v_delta_backlog AS
SELECT 
    entity_type,
    state,
    COUNT(*) as count,
    MIN(created_at) as oldest_pending,
    MAX(updated_at) as latest_updated
FROM ops_outbox_journal
GROUP BY entity_type, state;

-- ============================================================
-- 7. 项目统计视图
-- ============================================================

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
-- 8. 扫描会话状态视图
-- ============================================================

CREATE VIEW IF NOT EXISTS v_scan_session_status AS
SELECT 
    session_id,
    state,
    scan_type,
    root_path,
    JSON_EXTRACT(stats_json, '$.files_discovered') as files_discovered,
    JSON_EXTRACT(stats_json, '$.files_processed') as files_processed,
    JSON_EXTRACT(stats_json, '$.mods_found') as mods_found,
    JSON_EXTRACT(stats_json, '$.language_files_found') as language_files_found,
    JSON_EXTRACT(progress_json, '$.percentage') as progress_percentage,
    started_at,
    completed_at,
    CASE 
        WHEN completed_at IS NOT NULL 
        THEN ROUND((julianday(completed_at) - julianday(started_at)) * 86400, 2)
        ELSE NULL 
    END as duration_seconds
FROM cache_scan_sessions
ORDER BY started_at DESC;