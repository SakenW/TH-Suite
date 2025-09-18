-- TH-Suite MC L10n - 初始配置数据
-- 创建时间: 2025-09-17
-- 说明: 系统默认配置数据，包含缓存TTL、同步参数、QA设置等

-- ============================================================
-- 默认系统配置
-- ============================================================

INSERT OR IGNORE INTO cfg_local_settings (key, value_json) VALUES 
    -- 数据库版本信息
    ('database.version', '"v5.1"'),
    ('database.migration_version', '"009"'),
    
    -- 缓存TTL设置 (秒)
    ('cache.ttl.scan_results', '3600'),     -- 扫描结果缓存1小时
    ('cache.ttl.lang_file', '1800'),        -- 语言文件缓存30分钟
    ('cache.ttl.entry', '900'),             -- 翻译条目缓存15分钟
    ('cache.ttl.stats', '300'),             -- 统计数据缓存5分钟
    ('cache.ttl.checkpoint', '1800'),       -- 检查点缓存30分钟
    
    -- 同步参数设置
    ('sync.batch_size', '1000'),            -- 批量同步大小
    ('sync.compression', '"zstd"'),         -- 压缩算法
    ('sync.compression_level', '6'),        -- 压缩级别
    ('sync.timeout_seconds', '30'),         -- 同步超时时间
    ('sync.retry_max_attempts', '3'),       -- 最大重试次数
    
    -- 工作队列设置
    ('queue.max_attempts', '3'),            -- 任务最大重试次数
    ('queue.lease_timeout', '300'),         -- 任务租约超时时间(秒)
    ('queue.batch_size', '10'),             -- 批量处理大小
    ('queue.priority_levels', '4'),         -- 优先级层级数
    
    -- 扫描系统设置
    ('scan.max_concurrent_tasks', '4'),     -- 最大并发扫描任务数
    ('scan.chunk_size', '100'),             -- 扫描分片大小
    ('scan.temp_cleanup_interval', '3600'), -- 临时文件清理间隔(秒)
    ('scan.session_timeout', '7200'),       -- 扫描会话超时时间(秒)
    ('scan.incremental_threshold', '0.1'),  -- 增量扫描阈值(10%)
    
    -- JAR处理设置
    ('jar.extraction_timeout', '60'),       -- JAR解压超时时间(秒)
    ('jar.temp_dir_cleanup', 'true'),       -- 是否自动清理临时目录
    ('jar.max_file_size_mb', '100'),        -- 最大文件处理大小(MB)
    ('jar.supported_encodings', '["utf-8", "gbk", "gb2312"]'), -- 支持的编码
    
    -- QA质量检查设置
    ('qa.check_placeholders', 'true'),      -- 检查占位符匹配
    ('qa.check_escape_sequences', 'true'),  -- 检查转义序列
    ('qa.reject_empty_strings', 'false'),   -- 拒绝空字符串
    ('qa.check_length_variance', 'true'),   -- 检查长度差异
    ('qa.max_length_ratio', '3.0'),         -- 最大长度比率
    ('qa.check_format_strings', 'true'),    -- 检查格式字符串
    
    -- 性能优化设置
    ('perf.enable_compression', 'true'),    -- 启用压缩
    ('perf.compression_threshold', '1024'), -- 压缩阈值(字节)
    ('perf.memory_limit_mb', '512'),        -- 内存限制(MB)
    ('perf.gc_threshold', '0.8'),           -- GC触发阈值
    
    -- 监控和日志设置
    ('monitor.metrics_interval', '60'),     -- 指标收集间隔(秒)
    ('monitor.log_level', '"INFO"'),        -- 日志级别
    ('monitor.enable_traces', 'false'),     -- 启用链路追踪
    ('monitor.max_log_files', '10'),        -- 最大日志文件数
    
    -- 安全设置
    ('security.max_file_path_length', '260'), -- 最大文件路径长度
    ('security.allowed_extensions', '["jar", "zip", "json", "lang", "properties", "toml"]'), -- 允许的文件扩展名
    ('security.enable_path_validation', 'true'), -- 启用路径验证
    
    -- UI设置
    ('ui.auto_refresh_interval', '5'),      -- 自动刷新间隔(秒)
    ('ui.max_entries_per_page', '50'),      -- 每页最大条目数
    ('ui.enable_animations', 'true'),       -- 启用动画效果
    ('ui.theme', '"light"'),                -- 主题模式
    
    -- 实验性功能
    ('experimental.enable_neural_translation', 'false'), -- 启用神经网络翻译
    ('experimental.enable_async_processing', 'true'),    -- 启用异步处理
    ('experimental.enable_distributed_cache', 'false'),  -- 启用分布式缓存
    
    -- 系统信息
    ('system.install_date', 'datetime("now")'),
    ('system.last_updated', 'datetime("now")'),
    ('system.feature_flags', '{"scan_v2": true, "queue_v2": true, "cache_v2": true}');