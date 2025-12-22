-- MC L10n V6 数据库UIDA支持扩展
-- 为核心表添加UIDA字段以支持统一标识符架构

-- 1. 为翻译条目表添加UIDA字段
ALTER TABLE core_translation_entries 
ADD COLUMN uida_keys_b64 TEXT;

ALTER TABLE core_translation_entries 
ADD COLUMN uida_sha256_hex TEXT;

-- 2. 为语言文件表添加UIDA字段  
ALTER TABLE core_language_files
ADD COLUMN uida_keys_b64 TEXT;

ALTER TABLE core_language_files
ADD COLUMN uida_sha256_hex TEXT;

-- 3. 为MOD表添加UIDA字段
ALTER TABLE core_mods
ADD COLUMN uida_keys_b64 TEXT;

ALTER TABLE core_mods
ADD COLUMN uida_sha256_hex TEXT;

-- 4. 为MOD版本表添加UIDA字段
ALTER TABLE core_mod_versions
ADD COLUMN uida_keys_b64 TEXT;

ALTER TABLE core_mod_versions
ADD COLUMN uida_sha256_hex TEXT;

-- 5. 创建UIDA索引以支持高效查询
CREATE INDEX idx_translation_entries_uida_b64 
ON core_translation_entries(uida_keys_b64) 
WHERE uida_keys_b64 IS NOT NULL;

CREATE INDEX idx_translation_entries_uida_sha256 
ON core_translation_entries(uida_sha256_hex) 
WHERE uida_sha256_hex IS NOT NULL;

CREATE INDEX idx_language_files_uida_b64 
ON core_language_files(uida_keys_b64) 
WHERE uida_keys_b64 IS NOT NULL;

CREATE INDEX idx_language_files_uida_sha256 
ON core_language_files(uida_sha256_hex) 
WHERE uida_sha256_hex IS NOT NULL;

CREATE INDEX idx_mods_uida_b64 
ON core_mods(uida_keys_b64) 
WHERE uida_keys_b64 IS NOT NULL;

CREATE INDEX idx_mod_versions_uida_b64 
ON core_mod_versions(uida_keys_b64) 
WHERE uida_keys_b64 IS NOT NULL;

-- 6. 创建UIDA去重视图
CREATE VIEW v_duplicate_translation_entries AS
SELECT 
    uida_sha256_hex,
    COUNT(*) as duplicate_count,
    GROUP_CONCAT(uid) as entry_uids,
    MIN(created_at) as first_created,
    MAX(updated_at) as last_updated
FROM core_translation_entries 
WHERE uida_sha256_hex IS NOT NULL
GROUP BY uida_sha256_hex 
HAVING COUNT(*) > 1;

-- 7. 创建UIDA统计视图
CREATE VIEW v_uida_statistics AS
SELECT 
    'translation_entries' as table_name,
    COUNT(*) as total_entries,
    COUNT(uida_keys_b64) as entries_with_uida,
    COUNT(DISTINCT uida_sha256_hex) as unique_uida_count,
    ROUND(CAST(COUNT(uida_keys_b64) AS FLOAT) / COUNT(*) * 100, 2) as uida_coverage_percent
FROM core_translation_entries
UNION ALL
SELECT 
    'language_files' as table_name,
    COUNT(*) as total_entries,
    COUNT(uida_keys_b64) as entries_with_uida,
    COUNT(DISTINCT uida_sha256_hex) as unique_uida_count,
    ROUND(CAST(COUNT(uida_keys_b64) AS FLOAT) / COUNT(*) * 100, 2) as uida_coverage_percent
FROM core_language_files
UNION ALL
SELECT 
    'mods' as table_name,
    COUNT(*) as total_entries,
    COUNT(uida_keys_b64) as entries_with_uida,
    COUNT(DISTINCT uida_sha256_hex) as unique_uida_count,
    ROUND(CAST(COUNT(uida_keys_b64) AS FLOAT) / COUNT(*) * 100, 2) as uida_coverage_percent
FROM core_mods;

-- 8. 创建翻译记忆库查询视图 (基于UIDA)
CREATE VIEW v_translation_memory AS
SELECT DISTINCT
    t1.uida_sha256_hex,
    t1.src_text,
    t1.dst_text,
    t1.status,
    COUNT(*) OVER (PARTITION BY t1.uida_sha256_hex) as usage_count,
    MAX(t1.updated_at) OVER (PARTITION BY t1.uida_sha256_hex) as last_used,
    GROUP_CONCAT(DISTINCT lf.locale) OVER (PARTITION BY t1.uida_sha256_hex) as available_locales
FROM core_translation_entries t1
JOIN core_language_files lf ON t1.language_file_uid = lf.uid
WHERE t1.uida_sha256_hex IS NOT NULL 
  AND t1.status IN ('reviewed', 'locked')
  AND t1.dst_text != '';

-- 9. 添加约束和触发器（SQLite不支持复杂触发器，这里用注释说明）
-- 注意：在实际应用中需要在应用层确保UIDA字段的一致性

-- 10. 创建UIDA命名空间统计
CREATE VIEW v_uida_namespace_stats AS
SELECT 
    json_extract(uida_keys_b64, '$.namespace') as namespace,
    COUNT(*) as count,
    COUNT(DISTINCT uida_sha256_hex) as unique_count
FROM (
    SELECT uida_keys_b64, uida_sha256_hex 
    FROM core_translation_entries 
    WHERE uida_keys_b64 IS NOT NULL
    UNION ALL
    SELECT uida_keys_b64, uida_sha256_hex 
    FROM core_language_files 
    WHERE uida_keys_b64 IS NOT NULL
    UNION ALL
    SELECT uida_keys_b64, uida_sha256_hex 
    FROM core_mods 
    WHERE uida_keys_b64 IS NOT NULL
    UNION ALL
    SELECT uida_keys_b64, uida_sha256_hex 
    FROM core_mod_versions 
    WHERE uida_keys_b64 IS NOT NULL
)
WHERE json_extract(uida_keys_b64, '$.namespace') IS NOT NULL
GROUP BY json_extract(uida_keys_b64, '$.namespace')
ORDER BY count DESC;