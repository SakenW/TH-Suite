-- TH-Suite MC L10n - 扩展核心表支持版本管理
-- 创建时间: 2025-09-20
-- 说明: 为现有核心表添加版本管理字段，保持向后兼容

-- ============================================================
-- 1. 扩展核心翻译条目表
-- ============================================================

-- 添加版本管理字段到翻译条目表
ALTER TABLE core_translation_entries ADD COLUMN version_repository_uid TEXT 
    REFERENCES version_repositories(uid) ON DELETE SET NULL;

ALTER TABLE core_translation_entries ADD COLUMN current_commit_uid TEXT 
    REFERENCES version_commits(uid) ON DELETE SET NULL;

ALTER TABLE core_translation_entries ADD COLUMN version_number INTEGER DEFAULT 1;

ALTER TABLE core_translation_entries ADD COLUMN is_versioned BOOLEAN DEFAULT FALSE;

ALTER TABLE core_translation_entries ADD COLUMN last_version_update TEXT;

-- ============================================================
-- 2. 扩展语言文件表
-- ============================================================

-- 添加版本管理字段到语言文件表
ALTER TABLE core_language_files ADD COLUMN version_repository_uid TEXT 
    REFERENCES version_repositories(uid) ON DELETE SET NULL;

ALTER TABLE core_language_files ADD COLUMN current_commit_uid TEXT 
    REFERENCES version_commits(uid) ON DELETE SET NULL;

ALTER TABLE core_language_files ADD COLUMN file_version INTEGER DEFAULT 1;

ALTER TABLE core_language_files ADD COLUMN content_hash_b3 TEXT;

ALTER TABLE core_language_files ADD COLUMN is_versioned BOOLEAN DEFAULT FALSE;

-- ============================================================
-- 3. 扩展项目表
-- ============================================================

-- 添加版本管理字段到项目表
ALTER TABLE core_projects ADD COLUMN version_repository_uid TEXT 
    REFERENCES version_repositories(uid) ON DELETE SET NULL;

ALTER TABLE core_projects ADD COLUMN current_commit_uid TEXT 
    REFERENCES version_commits(uid) ON DELETE SET NULL;

ALTER TABLE core_projects ADD COLUMN project_version TEXT DEFAULT '1.0.0';

ALTER TABLE core_projects ADD COLUMN version_strategy TEXT 
    CHECK(version_strategy IN ('manual','auto','scheduled')) DEFAULT 'manual';

-- ============================================================
-- 4. 扩展整合包表
-- ============================================================

-- 添加版本管理字段到整合包表
ALTER TABLE core_packs ADD COLUMN version_repository_uid TEXT 
    REFERENCES version_repositories(uid) ON DELETE SET NULL;

ALTER TABLE core_packs ADD COLUMN current_commit_uid TEXT 
    REFERENCES version_commits(uid) ON DELETE SET NULL;

-- 添加版本管理字段到整合包版本表
ALTER TABLE core_pack_versions ADD COLUMN version_repository_uid TEXT 
    REFERENCES version_repositories(uid) ON DELETE SET NULL;

ALTER TABLE core_pack_versions ADD COLUMN current_commit_uid TEXT 
    REFERENCES version_commits(uid) ON DELETE SET NULL;

-- ============================================================
-- 5. 扩展MOD表
-- ============================================================

-- 添加版本管理字段到MOD表
ALTER TABLE core_mods ADD COLUMN version_repository_uid TEXT 
    REFERENCES version_repositories(uid) ON DELETE SET NULL;

ALTER TABLE core_mods ADD COLUMN current_commit_uid TEXT 
    REFERENCES version_commits(uid) ON DELETE SET NULL;

-- 添加版本管理字段到MOD版本表
ALTER TABLE core_mod_versions ADD COLUMN version_repository_uid TEXT 
    REFERENCES version_repositories(uid) ON DELETE SET NULL;

ALTER TABLE core_mod_versions ADD COLUMN current_commit_uid TEXT 
    REFERENCES version_commits(uid) ON DELETE SET NULL;

-- ============================================================
-- 6. 创建版本关联索引
-- ============================================================

-- 翻译条目版本索引
CREATE INDEX IF NOT EXISTS idx_translation_entries_version_repo 
ON core_translation_entries(version_repository_uid);

CREATE INDEX IF NOT EXISTS idx_translation_entries_current_commit 
ON core_translation_entries(current_commit_uid);

-- 语言文件版本索引
CREATE INDEX IF NOT EXISTS idx_language_files_version_repo 
ON core_language_files(version_repository_uid);

CREATE INDEX IF NOT EXISTS idx_language_files_current_commit 
ON core_language_files(current_commit_uid);

-- 项目版本索引
CREATE INDEX IF NOT EXISTS idx_projects_version_repo 
ON core_projects(version_repository_uid);

-- 整合包版本索引
CREATE INDEX IF NOT EXISTS idx_packs_version_repo 
ON core_packs(version_repository_uid);

CREATE INDEX IF NOT EXISTS idx_pack_versions_version_repo 
ON core_pack_versions(version_repository_uid);

-- MOD版本索引
CREATE INDEX IF NOT EXISTS idx_mods_version_repo 
ON core_mods(version_repository_uid);

CREATE INDEX IF NOT EXISTS idx_mod_versions_version_repo 
ON core_mod_versions(version_repository_uid);

-- ============================================================
-- 7. 创建版本关联视图
-- ============================================================

-- 翻译条目版本视图
CREATE VIEW IF NOT EXISTS view_translation_entries_with_version AS
SELECT 
    te.id,
    te.uid,
    te.language_file_uid,
    te.key,
    te.src_text,
    te.dst_text,
    te.status,
    te.qa_flags,
    te.version_number,
    te.is_versioned,
    te.last_version_update,
    vr.uid as repository_uid,
    vc.commit_hash,
    vc.author_name,
    vc.message as commit_message,
    vc.created_at as commit_created_at,
    te.updated_at
FROM core_translation_entries te
LEFT JOIN version_repositories vr ON te.version_repository_uid = vr.uid
LEFT JOIN version_commits vc ON te.current_commit_uid = vc.uid;

-- 语言文件版本视图
CREATE VIEW IF NOT EXISTS view_language_files_with_version AS
SELECT 
    lf.id,
    lf.uid,
    lf.carrier_type,
    lf.carrier_uid,
    lf.locale,
    lf.rel_path,
    lf.format,
    lf.size,
    lf.file_version,
    lf.content_hash_b3,
    lf.is_versioned,
    vr.uid as repository_uid,
    vc.commit_hash,
    vc.author_name,
    vc.message as commit_message,
    vc.created_at as commit_created_at,
    lf.discovered_at
FROM core_language_files lf
LEFT JOIN version_repositories vr ON lf.version_repository_uid = vr.uid
LEFT JOIN version_commits vc ON lf.current_commit_uid = vc.uid;

-- 项目版本视图
CREATE VIEW IF NOT EXISTS view_projects_with_version AS
SELECT 
    p.id,
    p.uid,
    p.name,
    p.description,
    p.project_version,
    p.version_strategy,
    vr.uid as repository_uid,
    vc.commit_hash,
    vc.author_name,
    vc.message as commit_message,
    vc.created_at as commit_created_at,
    COUNT(DISTINCT te.uid) as translation_entries_count,
    COUNT(DISTINCT lf.uid) as language_files_count,
    p.created_at,
    p.updated_at
FROM core_projects p
LEFT JOIN version_repositories vr ON p.version_repository_uid = vr.uid
LEFT JOIN version_commits vc ON p.current_commit_uid = vc.uid
LEFT JOIN core_language_files lf ON lf.carrier_type = 'project' -- 假设项目相关文件
LEFT JOIN core_translation_entries te ON lf.uid = te.language_file_uid
GROUP BY p.uid;

-- ============================================================
-- 8. 版本管理触发器
-- ============================================================

-- 翻译条目更新时自动更新版本信息
CREATE TRIGGER IF NOT EXISTS trigger_translation_entry_version_update
AFTER UPDATE ON core_translation_entries
FOR EACH ROW
WHEN OLD.dst_text != NEW.dst_text OR OLD.status != NEW.status
BEGIN
    UPDATE core_translation_entries 
    SET 
        version_number = version_number + 1,
        last_version_update = datetime('now')
    WHERE uid = NEW.uid;
END;

-- 语言文件更新时自动更新版本信息
CREATE TRIGGER IF NOT EXISTS trigger_language_file_version_update
AFTER UPDATE ON core_language_files
FOR EACH ROW
WHEN OLD.size != NEW.size OR OLD.content_hash_b3 != NEW.content_hash_b3
BEGIN
    UPDATE core_language_files 
    SET file_version = file_version + 1
    WHERE uid = NEW.uid;
END;