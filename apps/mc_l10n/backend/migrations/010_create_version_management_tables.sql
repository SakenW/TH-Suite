-- TH-Suite MC L10n - 版本管理表
-- 创建时间: 2025-09-20
-- 说明: 完整的数据版本管理系统，支持版本控制、分支管理、回滚和标签

-- ============================================================
-- 1. 版本管理核心表
-- ============================================================

-- 版本仓库表 - 每个实体的版本仓库
CREATE TABLE IF NOT EXISTS version_repositories (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    uid TEXT UNIQUE NOT NULL,
    entity_type TEXT CHECK(entity_type IN ('project','pack','mod','language_file','translation_entries')) NOT NULL,
    entity_uid TEXT NOT NULL,
    default_branch TEXT DEFAULT 'main',
    created_at TEXT NOT NULL DEFAULT (datetime('now')),
    updated_at TEXT NOT NULL DEFAULT (datetime('now')),
    UNIQUE(entity_type, entity_uid)
);

-- 版本分支表
CREATE TABLE IF NOT EXISTS version_branches (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    uid TEXT UNIQUE NOT NULL,
    repository_uid TEXT NOT NULL REFERENCES version_repositories(uid) ON DELETE CASCADE,
    name TEXT NOT NULL,
    description TEXT,
    parent_branch_uid TEXT REFERENCES version_branches(uid),
    is_protected BOOLEAN DEFAULT FALSE,
    created_at TEXT NOT NULL DEFAULT (datetime('now')),
    updated_at TEXT NOT NULL DEFAULT (datetime('now')),
    UNIQUE(repository_uid, name)
);

-- 版本提交表 - 核心版本记录
CREATE TABLE IF NOT EXISTS version_commits (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    uid TEXT UNIQUE NOT NULL,
    repository_uid TEXT NOT NULL REFERENCES version_repositories(uid) ON DELETE CASCADE,
    branch_uid TEXT NOT NULL REFERENCES version_branches(uid) ON DELETE CASCADE,
    parent_commit_uid TEXT REFERENCES version_commits(uid),
    commit_hash TEXT UNIQUE NOT NULL,
    author_name TEXT NOT NULL,
    author_email TEXT,
    message TEXT NOT NULL,
    description TEXT,
    changes_summary TEXT CHECK(json_valid(changes_summary)) DEFAULT '{}',
    metadata TEXT CHECK(json_valid(metadata)) DEFAULT '{}',
    created_at TEXT NOT NULL DEFAULT (datetime('now'))
);

-- ============================================================
-- 2. 版本内容存储表
-- ============================================================

-- 版本快照表 - 存储完整版本快照
CREATE TABLE IF NOT EXISTS version_snapshots (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    uid TEXT UNIQUE NOT NULL,
    commit_uid TEXT NOT NULL REFERENCES version_commits(uid) ON DELETE CASCADE,
    content_type TEXT CHECK(content_type IN ('full','incremental','compressed')) NOT NULL,
    content_cid TEXT NOT NULL REFERENCES ops_cas_objects(cid),
    compression_algo TEXT CHECK(compression_algo IN ('zstd','gzip','none')) DEFAULT 'zstd',
    size_bytes INTEGER NOT NULL,
    item_count INTEGER DEFAULT 0,
    checksum_blake3 TEXT NOT NULL,
    created_at TEXT NOT NULL DEFAULT (datetime('now')),
    UNIQUE(commit_uid, content_type)
);

-- 版本差异表 - 存储增量变更
CREATE TABLE IF NOT EXISTS version_diffs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    uid TEXT UNIQUE NOT NULL,
    from_commit_uid TEXT REFERENCES version_commits(uid) ON DELETE CASCADE,
    to_commit_uid TEXT NOT NULL REFERENCES version_commits(uid) ON DELETE CASCADE,
    diff_type TEXT CHECK(diff_type IN ('forward','reverse','three_way')) NOT NULL,
    diff_cid TEXT NOT NULL REFERENCES ops_cas_objects(cid),
    diff_format TEXT CHECK(diff_format IN ('json_patch','git_diff','custom')) DEFAULT 'json_patch',
    operations_count INTEGER DEFAULT 0,
    size_bytes INTEGER NOT NULL,
    created_at TEXT NOT NULL DEFAULT (datetime('now')),
    UNIQUE(from_commit_uid, to_commit_uid, diff_type)
);

-- ============================================================
-- 3. 版本标签和引用管理
-- ============================================================

-- 版本标签表
CREATE TABLE IF NOT EXISTS version_tags (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    uid TEXT UNIQUE NOT NULL,
    repository_uid TEXT NOT NULL REFERENCES version_repositories(uid) ON DELETE CASCADE,
    name TEXT NOT NULL,
    commit_uid TEXT NOT NULL REFERENCES version_commits(uid) ON DELETE CASCADE,
    tag_type TEXT CHECK(tag_type IN ('release','milestone','hotfix','feature')) DEFAULT 'release',
    description TEXT,
    metadata TEXT CHECK(json_valid(metadata)) DEFAULT '{}',
    created_at TEXT NOT NULL DEFAULT (datetime('now')),
    UNIQUE(repository_uid, name)
);

-- 版本引用表 - 分支头指针和其他引用
CREATE TABLE IF NOT EXISTS version_refs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    uid TEXT UNIQUE NOT NULL,
    repository_uid TEXT NOT NULL REFERENCES version_repositories(uid) ON DELETE CASCADE,
    ref_type TEXT CHECK(ref_type IN ('head','tag','remote','stash')) NOT NULL,
    ref_name TEXT NOT NULL,
    target_commit_uid TEXT NOT NULL REFERENCES version_commits(uid),
    updated_at TEXT NOT NULL DEFAULT (datetime('now')),
    UNIQUE(repository_uid, ref_type, ref_name)
);

-- ============================================================
-- 4. 版本合并和冲突管理
-- ============================================================

-- 版本合并表
CREATE TABLE IF NOT EXISTS version_merges (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    uid TEXT UNIQUE NOT NULL,
    repository_uid TEXT NOT NULL REFERENCES version_repositories(uid) ON DELETE CASCADE,
    base_commit_uid TEXT NOT NULL REFERENCES version_commits(uid),
    source_commit_uid TEXT NOT NULL REFERENCES version_commits(uid),
    target_commit_uid TEXT NOT NULL REFERENCES version_commits(uid),
    merge_commit_uid TEXT REFERENCES version_commits(uid),
    merge_strategy TEXT CHECK(merge_strategy IN ('fast_forward','three_way','ours','theirs','manual')) NOT NULL,
    status TEXT CHECK(status IN ('pending','in_progress','completed','failed','aborted')) DEFAULT 'pending',
    conflicts_count INTEGER DEFAULT 0,
    created_at TEXT NOT NULL DEFAULT (datetime('now')),
    completed_at TEXT
);

-- 版本冲突表
CREATE TABLE IF NOT EXISTS version_conflicts (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    uid TEXT UNIQUE NOT NULL,
    merge_uid TEXT NOT NULL REFERENCES version_merges(uid) ON DELETE CASCADE,
    conflict_type TEXT CHECK(conflict_type IN ('content','metadata','structural','deletion')) NOT NULL,
    entity_path TEXT NOT NULL,
    base_value TEXT,
    source_value TEXT,
    target_value TEXT,
    resolution_strategy TEXT CHECK(resolution_strategy IN ('manual','auto_ours','auto_theirs','auto_merge')) DEFAULT 'manual',
    resolved_value TEXT,
    resolved_by TEXT,
    resolved_at TEXT,
    created_at TEXT NOT NULL DEFAULT (datetime('now'))
);

-- ============================================================
-- 5. 版本历史和审计
-- ============================================================

-- 版本操作日志表
CREATE TABLE IF NOT EXISTS version_operations_log (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    uid TEXT UNIQUE NOT NULL,
    repository_uid TEXT NOT NULL REFERENCES version_repositories(uid) ON DELETE CASCADE,
    operation_type TEXT CHECK(operation_type IN (
        'commit','branch_create','branch_delete','branch_merge',
        'tag_create','tag_delete','rollback','revert',
        'cherry_pick','rebase','stash'
    )) NOT NULL,
    operation_data TEXT CHECK(json_valid(operation_data)) NOT NULL,
    user_id TEXT,
    user_name TEXT,
    client_info TEXT CHECK(json_valid(client_info)) DEFAULT '{}',
    status TEXT CHECK(status IN ('pending','success','failed','cancelled')) DEFAULT 'pending',
    error_message TEXT,
    created_at TEXT NOT NULL DEFAULT (datetime('now')),
    completed_at TEXT
);

-- 版本访问日志表
CREATE TABLE IF NOT EXISTS version_access_log (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    repository_uid TEXT NOT NULL REFERENCES version_repositories(uid) ON DELETE CASCADE,
    commit_uid TEXT REFERENCES version_commits(uid),
    access_type TEXT CHECK(access_type IN ('read','write','clone','compare','download')) NOT NULL,
    user_id TEXT,
    client_ip TEXT,
    user_agent TEXT,
    accessed_at TEXT NOT NULL DEFAULT (datetime('now'))
);

-- ============================================================
-- 6. 版本同步和远程管理
-- ============================================================

-- 远程版本仓库表
CREATE TABLE IF NOT EXISTS version_remotes (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    uid TEXT UNIQUE NOT NULL,
    repository_uid TEXT NOT NULL REFERENCES version_repositories(uid) ON DELETE CASCADE,
    name TEXT NOT NULL,
    url TEXT NOT NULL,
    auth_type TEXT CHECK(auth_type IN ('none','token','oauth','ssh_key')) DEFAULT 'none',
    auth_config TEXT CHECK(json_valid(auth_config)) DEFAULT '{}',
    sync_strategy TEXT CHECK(sync_strategy IN ('manual','auto','scheduled')) DEFAULT 'manual',
    last_sync_at TEXT,
    created_at TEXT NOT NULL DEFAULT (datetime('now')),
    updated_at TEXT NOT NULL DEFAULT (datetime('now')),
    UNIQUE(repository_uid, name)
);

-- 版本同步状态表
CREATE TABLE IF NOT EXISTS version_sync_status (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    uid TEXT UNIQUE NOT NULL,
    remote_uid TEXT NOT NULL REFERENCES version_remotes(uid) ON DELETE CASCADE,
    local_commit_uid TEXT REFERENCES version_commits(uid),
    remote_commit_uid TEXT,
    sync_direction TEXT CHECK(sync_direction IN ('push','pull','both')) NOT NULL,
    status TEXT CHECK(status IN ('idle','syncing','conflict','error','success')) DEFAULT 'idle',
    progress_percent REAL DEFAULT 0.0,
    error_message TEXT,
    last_attempt_at TEXT,
    next_sync_at TEXT,
    created_at TEXT NOT NULL DEFAULT (datetime('now')),
    updated_at TEXT NOT NULL DEFAULT (datetime('now'))
);

-- ============================================================
-- 7. 性能优化索引
-- ============================================================

-- 版本提交索引
CREATE INDEX IF NOT EXISTS idx_version_commits_repository_branch 
ON version_commits(repository_uid, branch_uid);

CREATE INDEX IF NOT EXISTS idx_version_commits_parent 
ON version_commits(parent_commit_uid);

CREATE INDEX IF NOT EXISTS idx_version_commits_hash 
ON version_commits(commit_hash);

-- 版本快照索引
CREATE INDEX IF NOT EXISTS idx_version_snapshots_commit 
ON version_snapshots(commit_uid);

CREATE INDEX IF NOT EXISTS idx_version_snapshots_cid 
ON version_snapshots(content_cid);

-- 版本差异索引
CREATE INDEX IF NOT EXISTS idx_version_diffs_commits 
ON version_diffs(from_commit_uid, to_commit_uid);

-- 版本操作日志索引
CREATE INDEX IF NOT EXISTS idx_version_operations_repository_type 
ON version_operations_log(repository_uid, operation_type);

CREATE INDEX IF NOT EXISTS idx_version_operations_created 
ON version_operations_log(created_at);

-- ============================================================
-- 8. 版本管理视图
-- ============================================================

-- 版本仓库汇总视图
CREATE VIEW IF NOT EXISTS view_version_repository_summary AS
SELECT 
    vr.uid,
    vr.entity_type,
    vr.entity_uid,
    vr.default_branch,
    COUNT(DISTINCT vb.uid) as branch_count,
    COUNT(DISTINCT vc.uid) as commit_count,
    COUNT(DISTINCT vt.uid) as tag_count,
    MAX(vc.created_at) as last_commit_at,
    vr.created_at,
    vr.updated_at
FROM version_repositories vr
LEFT JOIN version_branches vb ON vr.uid = vb.repository_uid
LEFT JOIN version_commits vc ON vr.uid = vc.repository_uid
LEFT JOIN version_tags vt ON vr.uid = vt.repository_uid
GROUP BY vr.uid;

-- 分支状态视图
CREATE VIEW IF NOT EXISTS view_version_branch_status AS
SELECT 
    vb.uid,
    vb.repository_uid,
    vb.name,
    vb.description,
    vb.is_protected,
    COUNT(vc.uid) as commit_count,
    MAX(vc.created_at) as last_commit_at,
    vref.target_commit_uid as head_commit_uid,
    vb.created_at,
    vb.updated_at
FROM version_branches vb
LEFT JOIN version_commits vc ON vb.uid = vc.branch_uid
LEFT JOIN version_refs vref ON vb.repository_uid = vref.repository_uid 
    AND vref.ref_type = 'head' 
    AND vref.ref_name = vb.name
GROUP BY vb.uid;

-- 提交详情视图
CREATE VIEW IF NOT EXISTS view_version_commit_details AS
SELECT 
    vc.uid,
    vc.repository_uid,
    vc.branch_uid,
    vc.parent_commit_uid,
    vc.commit_hash,
    vc.author_name,
    vc.author_email,
    vc.message,
    vc.description,
    vc.changes_summary,
    vc.metadata,
    vs.size_bytes as snapshot_size,
    vs.item_count,
    vb.name as branch_name,
    vc.created_at
FROM version_commits vc
LEFT JOIN version_snapshots vs ON vc.uid = vs.commit_uid AND vs.content_type = 'full'
LEFT JOIN version_branches vb ON vc.branch_uid = vb.uid;