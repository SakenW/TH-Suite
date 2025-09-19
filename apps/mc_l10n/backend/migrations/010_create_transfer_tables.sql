-- TH-Suite V6架构 - 文件传输系统表结构
-- 创建支持大文件分块传输、断点续传的数据表

-- ============================================================================
-- 传输会话表 - 管理文件上传/下载会话
-- ============================================================================

CREATE TABLE IF NOT EXISTS transfer_sessions (
    session_id TEXT PRIMARY KEY,
    session_type TEXT NOT NULL CHECK (session_type IN ('upload', 'download')),
    
    -- 文件基本信息
    file_name TEXT NOT NULL,
    file_path TEXT,  -- 目标或源文件路径
    file_size INTEGER NOT NULL,
    file_hash TEXT NOT NULL,  -- BLAKE3 文件哈希
    content_type TEXT DEFAULT 'application/octet-stream',
    
    -- 分块配置
    chunk_size INTEGER NOT NULL DEFAULT 1048576,  -- 默认1MB
    total_chunks INTEGER NOT NULL,
    completed_chunks INTEGER NOT NULL DEFAULT 0,
    
    -- 会话状态
    status TEXT NOT NULL DEFAULT 'initializing' 
        CHECK (status IN ('initializing', 'active', 'paused', 'completed', 'failed', 'cancelled')),
    
    -- 时间戳
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    expires_at TIMESTAMP NOT NULL,
    started_at TIMESTAMP,
    completed_at TIMESTAMP,
    
    -- 错误和元数据
    error_message TEXT,
    error_code TEXT,
    metadata TEXT DEFAULT '{}',  -- JSON格式的额外元数据
    
    -- 传输配置
    max_concurrent_chunks INTEGER DEFAULT 4,
    compression_enabled BOOLEAN DEFAULT FALSE,
    auto_retry BOOLEAN DEFAULT TRUE,
    max_retries INTEGER DEFAULT 3,
    
    -- 关联项目（可选）
    project_id TEXT,
    user_id TEXT,
    
    -- 索引字段
    FOREIGN KEY (project_id) REFERENCES core_projects(project_id) ON DELETE SET NULL
);

-- ============================================================================
-- 分块状态表 - 跟踪每个分块的传输状态
-- ============================================================================

CREATE TABLE IF NOT EXISTS transfer_chunks (
    session_id TEXT NOT NULL,
    chunk_index INTEGER NOT NULL,
    
    -- 分块信息
    chunk_size INTEGER NOT NULL,
    chunk_hash TEXT NOT NULL,  -- BLAKE3 分块哈希
    chunk_offset INTEGER NOT NULL,  -- 在文件中的偏移量
    
    -- 分块状态
    status TEXT NOT NULL DEFAULT 'pending' 
        CHECK (status IN ('pending', 'uploading', 'downloading', 'completed', 'failed')),
    
    -- 重试信息
    retry_count INTEGER NOT NULL DEFAULT 0,
    last_error TEXT,
    
    -- 时间戳
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    started_at TIMESTAMP,
    completed_at TIMESTAMP,
    
    -- 性能统计
    transfer_duration_ms INTEGER,
    transfer_rate_bps INTEGER,
    
    PRIMARY KEY (session_id, chunk_index),
    FOREIGN KEY (session_id) REFERENCES transfer_sessions(session_id) ON DELETE CASCADE
);

-- ============================================================================
-- 传输统计表 - 记录传输性能和统计信息
-- ============================================================================

CREATE TABLE IF NOT EXISTS transfer_stats (
    session_id TEXT PRIMARY KEY,
    
    -- 传输进度
    bytes_transferred INTEGER NOT NULL DEFAULT 0,
    percentage_completed REAL NOT NULL DEFAULT 0.0,
    
    -- 性能指标
    current_transfer_rate_bps INTEGER NOT NULL DEFAULT 0,
    average_transfer_rate_bps INTEGER NOT NULL DEFAULT 0,
    peak_transfer_rate_bps INTEGER NOT NULL DEFAULT 0,
    
    -- 时间估计
    start_time TIMESTAMP NOT NULL,
    last_update_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    estimated_completion TIMESTAMP,
    
    -- 错误统计
    error_count INTEGER NOT NULL DEFAULT 0,
    retry_count INTEGER NOT NULL DEFAULT 0,
    chunk_failures INTEGER NOT NULL DEFAULT 0,
    
    -- 网络统计
    network_timeout_count INTEGER NOT NULL DEFAULT 0,
    bytes_retransmitted INTEGER NOT NULL DEFAULT 0,
    
    -- 完成信息
    completion_time TIMESTAMP,
    final_duration_seconds REAL,
    
    FOREIGN KEY (session_id) REFERENCES transfer_sessions(session_id) ON DELETE CASCADE
);

-- ============================================================================
-- 传输事件日志表 - 记录重要的传输事件
-- ============================================================================

CREATE TABLE IF NOT EXISTS transfer_events (
    event_id TEXT PRIMARY KEY,
    session_id TEXT NOT NULL,
    
    -- 事件信息
    event_type TEXT NOT NULL CHECK (event_type IN (
        'session_created', 'session_started', 'session_paused', 'session_resumed',
        'session_completed', 'session_failed', 'session_cancelled',
        'chunk_started', 'chunk_completed', 'chunk_failed', 'chunk_retried',
        'progress_update', 'error_occurred', 'warning_issued'
    )),
    event_message TEXT,
    event_data TEXT DEFAULT '{}',  -- JSON格式的事件数据
    
    -- 分块相关（可选）
    chunk_index INTEGER,
    
    -- 时间戳
    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    -- 严重程度
    severity TEXT DEFAULT 'info' CHECK (severity IN ('debug', 'info', 'warning', 'error', 'critical')),
    
    FOREIGN KEY (session_id) REFERENCES transfer_sessions(session_id) ON DELETE CASCADE
);

-- ============================================================================
-- 传输配额表 - 管理用户传输配额和限制
-- ============================================================================

CREATE TABLE IF NOT EXISTS transfer_quotas (
    user_id TEXT PRIMARY KEY,
    
    -- 配额限制
    daily_upload_limit_mb INTEGER DEFAULT 1024,  -- 1GB每天
    daily_download_limit_mb INTEGER DEFAULT 2048,  -- 2GB每天
    concurrent_session_limit INTEGER DEFAULT 5,
    max_file_size_mb INTEGER DEFAULT 1024,  -- 1GB单文件
    
    -- 当前使用量
    daily_upload_used_mb INTEGER DEFAULT 0,
    daily_download_used_mb INTEGER DEFAULT 0,
    active_sessions_count INTEGER DEFAULT 0,
    
    -- 统计信息
    total_uploaded_mb INTEGER DEFAULT 0,
    total_downloaded_mb INTEGER DEFAULT 0,
    total_sessions INTEGER DEFAULT 0,
    
    -- 重置时间
    daily_reset_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- ============================================================================
-- 创建索引以优化查询性能
-- ============================================================================

-- 传输会话索引
CREATE INDEX IF NOT EXISTS idx_transfer_sessions_status ON transfer_sessions(status);
CREATE INDEX IF NOT EXISTS idx_transfer_sessions_created_at ON transfer_sessions(created_at);
CREATE INDEX IF NOT EXISTS idx_transfer_sessions_project_id ON transfer_sessions(project_id);
CREATE INDEX IF NOT EXISTS idx_transfer_sessions_user_id ON transfer_sessions(user_id);
CREATE INDEX IF NOT EXISTS idx_transfer_sessions_expires_at ON transfer_sessions(expires_at);

-- 分块状态索引
CREATE INDEX IF NOT EXISTS idx_transfer_chunks_status ON transfer_chunks(status);
CREATE INDEX IF NOT EXISTS idx_transfer_chunks_session_status ON transfer_chunks(session_id, status);

-- 传输统计索引
CREATE INDEX IF NOT EXISTS idx_transfer_stats_start_time ON transfer_stats(start_time);
CREATE INDEX IF NOT EXISTS idx_transfer_stats_completion_time ON transfer_stats(completion_time);

-- 传输事件索引
CREATE INDEX IF NOT EXISTS idx_transfer_events_session_id ON transfer_events(session_id);
CREATE INDEX IF NOT EXISTS idx_transfer_events_timestamp ON transfer_events(timestamp);
CREATE INDEX IF NOT EXISTS idx_transfer_events_type ON transfer_events(event_type);
CREATE INDEX IF NOT EXISTS idx_transfer_events_severity ON transfer_events(severity);

-- ============================================================================
-- 创建触发器以自动更新时间戳和统计信息
-- ============================================================================

-- 自动更新 transfer_sessions 的 updated_at 字段
CREATE TRIGGER IF NOT EXISTS update_transfer_sessions_updated_at
    AFTER UPDATE ON transfer_sessions
    FOR EACH ROW
    BEGIN
        UPDATE transfer_sessions 
        SET updated_at = CURRENT_TIMESTAMP 
        WHERE session_id = NEW.session_id;
    END;

-- 自动更新 transfer_quotas 的 updated_at 字段
CREATE TRIGGER IF NOT EXISTS update_transfer_quotas_updated_at
    AFTER UPDATE ON transfer_quotas
    FOR EACH ROW
    BEGIN
        UPDATE transfer_quotas 
        SET updated_at = CURRENT_TIMESTAMP 
        WHERE user_id = NEW.user_id;
    END;

-- 自动维护会话的 completed_chunks 计数
CREATE TRIGGER IF NOT EXISTS update_session_completed_chunks
    AFTER UPDATE OF status ON transfer_chunks
    FOR EACH ROW
    WHEN NEW.status = 'completed' AND OLD.status != 'completed'
    BEGIN
        UPDATE transfer_sessions 
        SET completed_chunks = completed_chunks + 1,
            updated_at = CURRENT_TIMESTAMP
        WHERE session_id = NEW.session_id;
    END;

-- 自动更新传输统计的最后更新时间
CREATE TRIGGER IF NOT EXISTS update_transfer_stats_last_update
    AFTER UPDATE ON transfer_stats
    FOR EACH ROW
    BEGIN
        UPDATE transfer_stats 
        SET last_update_time = CURRENT_TIMESTAMP 
        WHERE session_id = NEW.session_id;
    END;

-- ============================================================================
-- 创建视图以简化常用查询
-- ============================================================================

-- 活跃传输会话视图
CREATE VIEW IF NOT EXISTS active_transfer_sessions AS
SELECT 
    ts.*,
    tst.bytes_transferred,
    tst.percentage_completed,
    tst.current_transfer_rate_bps,
    tst.estimated_completion
FROM transfer_sessions ts
LEFT JOIN transfer_stats tst ON ts.session_id = tst.session_id
WHERE ts.status IN ('active', 'initializing');

-- 传输会话摘要视图
CREATE VIEW IF NOT EXISTS transfer_session_summary AS
SELECT 
    ts.session_id,
    ts.session_type,
    ts.file_name,
    ts.file_size,
    ts.status,
    ts.created_at,
    ts.completed_at,
    tst.percentage_completed,
    tst.average_transfer_rate_bps,
    tst.error_count,
    COUNT(tc.chunk_index) as total_chunks_tracked,
    COUNT(CASE WHEN tc.status = 'completed' THEN 1 END) as completed_chunks_tracked
FROM transfer_sessions ts
LEFT JOIN transfer_stats tst ON ts.session_id = tst.session_id
LEFT JOIN transfer_chunks tc ON ts.session_id = tc.session_id
GROUP BY ts.session_id;

-- 用户传输配额使用情况视图
CREATE VIEW IF NOT EXISTS user_quota_usage AS
SELECT 
    tq.user_id,
    tq.daily_upload_limit_mb,
    tq.daily_download_limit_mb,
    tq.daily_upload_used_mb,
    tq.daily_download_used_mb,
    tq.active_sessions_count,
    ROUND((tq.daily_upload_used_mb * 100.0 / tq.daily_upload_limit_mb), 2) as upload_usage_percent,
    ROUND((tq.daily_download_used_mb * 100.0 / tq.daily_download_limit_mb), 2) as download_usage_percent,
    tq.daily_reset_time
FROM transfer_quotas tq;

-- ============================================================================
-- 插入默认数据
-- ============================================================================

-- 插入默认的管理员配额设置
INSERT OR IGNORE INTO transfer_quotas (
    user_id, 
    daily_upload_limit_mb, 
    daily_download_limit_mb, 
    concurrent_session_limit,
    max_file_size_mb
) VALUES (
    'admin', 
    10240,  -- 10GB每天
    20480,  -- 20GB每天
    10,     -- 10个并发会话
    5120    -- 5GB单文件
);

-- 插入默认的普通用户配额设置模板
INSERT OR IGNORE INTO transfer_quotas (
    user_id, 
    daily_upload_limit_mb, 
    daily_download_limit_mb, 
    concurrent_session_limit,
    max_file_size_mb
) VALUES (
    'default_user', 
    1024,   -- 1GB每天
    2048,   -- 2GB每天
    3,      -- 3个并发会话
    1024    -- 1GB单文件
);