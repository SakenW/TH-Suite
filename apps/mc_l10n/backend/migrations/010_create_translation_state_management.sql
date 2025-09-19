-- TH-Suite MC L10n - 翻译状态管理系统
-- 创建时间: 2025-09-20
-- 说明: 完整的翻译状态管理，支持工作流、协作和审批流程

-- ============================================================
-- 1. 翻译状态定义表
-- ============================================================

CREATE TABLE IF NOT EXISTS translation_states (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    state_key TEXT UNIQUE NOT NULL,           -- 状态键：draft, pending, translated, reviewed, approved, published, rejected, conflict, locked
    display_name TEXT NOT NULL,               -- 显示名称：草稿、待翻译、已翻译等
    description TEXT,                         -- 状态描述
    category TEXT CHECK(category IN ('translation', 'quality', 'collaboration', 'publication')) DEFAULT 'translation',
    color_hex TEXT DEFAULT '#6B7280',         -- 状态颜色（用于UI显示）
    icon_name TEXT DEFAULT 'circle',          -- 图标名称
    sort_order INTEGER DEFAULT 0,             -- 排序顺序
    is_active BOOLEAN DEFAULT TRUE,           -- 是否启用
    created_at TEXT NOT NULL DEFAULT (datetime('now')),
    updated_at TEXT NOT NULL DEFAULT (datetime('now'))
);

-- ============================================================
-- 2. 状态转换规则表
-- ============================================================

CREATE TABLE IF NOT EXISTS translation_state_transitions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    from_state TEXT NOT NULL REFERENCES translation_states(state_key),
    to_state TEXT NOT NULL REFERENCES translation_states(state_key),
    transition_name TEXT NOT NULL,            -- 转换动作名称：submit, approve, reject, lock等
    required_role TEXT,                       -- 需要的角色权限：translator, reviewer, admin
    required_permission TEXT,                 -- 需要的具体权限
    auto_trigger BOOLEAN DEFAULT FALSE,       -- 是否自动触发
    trigger_condition TEXT,                   -- 自动触发条件（JSON格式）
    validation_rules TEXT CHECK(json_valid(validation_rules)) DEFAULT '{}', -- 验证规则
    notification_template TEXT,               -- 通知模板
    sort_order INTEGER DEFAULT 0,
    is_active BOOLEAN DEFAULT TRUE,
    created_at TEXT NOT NULL DEFAULT (datetime('now')),
    UNIQUE(from_state, to_state, transition_name)
);

-- ============================================================
-- 3. 翻译状态历史表
-- ============================================================

CREATE TABLE IF NOT EXISTS translation_state_history (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    entry_uid TEXT NOT NULL REFERENCES core_translation_entries(uid) ON DELETE CASCADE,
    from_state TEXT,                          -- 原状态（NULL表示初始状态）
    to_state TEXT NOT NULL REFERENCES translation_states(state_key),
    transition_name TEXT,                     -- 执行的转换动作
    operator_id TEXT,                         -- 操作者ID
    operator_name TEXT,                       -- 操作者名称
    reason TEXT,                              -- 状态变更原因
    metadata TEXT CHECK(json_valid(metadata)) DEFAULT '{}', -- 额外元数据
    created_at TEXT NOT NULL DEFAULT (datetime('now'))
);

-- ============================================================
-- 4. 工作流规则表
-- ============================================================

CREATE TABLE IF NOT EXISTS translation_workflow_rules (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    rule_name TEXT UNIQUE NOT NULL,           -- 规则名称：standard_translation_workflow
    description TEXT,                         -- 规则描述
    target_type TEXT CHECK(target_type IN ('global', 'project', 'mod', 'category')) DEFAULT 'global',
    target_value TEXT,                        -- 目标值（项目ID、MOD ID等）
    rule_config TEXT CHECK(json_valid(rule_config)) NOT NULL, -- 规则配置（JSON格式）
    priority INTEGER DEFAULT 0,              -- 优先级（高优先级覆盖低优先级）
    is_active BOOLEAN DEFAULT TRUE,
    created_at TEXT NOT NULL DEFAULT (datetime('now')),
    updated_at TEXT NOT NULL DEFAULT (datetime('now'))
);

-- ============================================================
-- 5. 批量操作记录表
-- ============================================================

CREATE TABLE IF NOT EXISTS translation_batch_operations (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    operation_id TEXT UNIQUE NOT NULL,        -- 操作ID
    operation_type TEXT CHECK(operation_type IN ('state_change', 'assignment', 'review', 'publication')) NOT NULL,
    operation_name TEXT NOT NULL,             -- 操作名称：批量审核、批量发布等
    target_filter TEXT CHECK(json_valid(target_filter)) NOT NULL, -- 目标筛选条件
    operation_params TEXT CHECK(json_valid(operation_params)) DEFAULT '{}', -- 操作参数
    operator_id TEXT,                         -- 操作者ID
    operator_name TEXT,                       -- 操作者名称
    status TEXT CHECK(status IN ('pending', 'running', 'completed', 'failed', 'cancelled')) DEFAULT 'pending',
    total_count INTEGER DEFAULT 0,           -- 总条目数
    processed_count INTEGER DEFAULT 0,       -- 已处理数
    success_count INTEGER DEFAULT 0,         -- 成功数
    failed_count INTEGER DEFAULT 0,          -- 失败数
    error_message TEXT,                       -- 错误信息
    started_at TEXT,                          -- 开始时间
    completed_at TEXT,                        -- 完成时间
    created_at TEXT NOT NULL DEFAULT (datetime('now'))
);

-- ============================================================
-- 6. 批量操作详细记录表
-- ============================================================

CREATE TABLE IF NOT EXISTS translation_batch_operation_details (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    operation_id TEXT NOT NULL REFERENCES translation_batch_operations(operation_id) ON DELETE CASCADE,
    entry_uid TEXT NOT NULL REFERENCES core_translation_entries(uid) ON DELETE CASCADE,
    status TEXT CHECK(status IN ('pending', 'success', 'failed', 'skipped')) DEFAULT 'pending',
    from_state TEXT,                          -- 原状态
    to_state TEXT,                            -- 目标状态
    error_message TEXT,                       -- 错误信息
    processed_at TEXT,                        -- 处理时间
    UNIQUE(operation_id, entry_uid)
);

-- ============================================================
-- 7. 翻译分配表
-- ============================================================

CREATE TABLE IF NOT EXISTS translation_assignments (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    assignment_id TEXT UNIQUE NOT NULL,       -- 分配ID
    entry_uid TEXT NOT NULL REFERENCES core_translation_entries(uid) ON DELETE CASCADE,
    assignee_id TEXT,                         -- 被分配者ID
    assignee_name TEXT,                       -- 被分配者名称
    assigner_id TEXT,                         -- 分配者ID
    assigner_name TEXT,                       -- 分配者名称
    assignment_type TEXT CHECK(assignment_type IN ('translate', 'review', 'approve')) NOT NULL,
    priority TEXT CHECK(priority IN ('low', 'normal', 'high', 'urgent')) DEFAULT 'normal',
    due_date TEXT,                           -- 截止日期
    status TEXT CHECK(status IN ('active', 'completed', 'cancelled', 'overdue')) DEFAULT 'active',
    notes TEXT,                              -- 分配备注
    completed_at TEXT,                       -- 完成时间
    created_at TEXT NOT NULL DEFAULT (datetime('now')),
    updated_at TEXT NOT NULL DEFAULT (datetime('now')),
    UNIQUE(entry_uid, assignment_type, assignee_id)
);

-- ============================================================
-- 8. 翻译状态统计视图
-- ============================================================

CREATE VIEW IF NOT EXISTS translation_state_stats AS
SELECT 
    ts.state_key,
    ts.display_name,
    ts.category,
    COUNT(cte.id) as entry_count,
    COUNT(cte.id) * 100.0 / (SELECT COUNT(*) FROM core_translation_entries) as percentage
FROM translation_states ts
LEFT JOIN core_translation_entries cte ON cte.status = ts.state_key
WHERE ts.is_active = TRUE
GROUP BY ts.state_key, ts.display_name, ts.category
ORDER BY ts.sort_order;

-- ============================================================
-- 9. 进度统计视图
-- ============================================================

CREATE VIEW IF NOT EXISTS translation_progress_stats AS
SELECT 
    clf.carrier_type,
    clf.carrier_uid,
    clf.locale,
    COUNT(cte.id) as total_entries,
    COUNT(CASE WHEN cte.status IN ('translated', 'reviewed', 'approved', 'published') THEN 1 END) as translated_entries,
    COUNT(CASE WHEN cte.status IN ('reviewed', 'approved', 'published') THEN 1 END) as reviewed_entries,
    COUNT(CASE WHEN cte.status = 'published' THEN 1 END) as published_entries,
    ROUND(
        COUNT(CASE WHEN cte.status IN ('translated', 'reviewed', 'approved', 'published') THEN 1 END) * 100.0 / 
        COUNT(cte.id), 2
    ) as translation_progress,
    ROUND(
        COUNT(CASE WHEN cte.status IN ('reviewed', 'approved', 'published') THEN 1 END) * 100.0 / 
        COUNT(cte.id), 2
    ) as review_progress,
    ROUND(
        COUNT(CASE WHEN cte.status = 'published' THEN 1 END) * 100.0 / 
        COUNT(cte.id), 2
    ) as publication_progress
FROM core_language_files clf
LEFT JOIN core_translation_entries cte ON cte.language_file_uid = clf.uid
GROUP BY clf.carrier_type, clf.carrier_uid, clf.locale;

-- ============================================================
-- 10. 工作负载统计视图
-- ============================================================

CREATE VIEW IF NOT EXISTS translation_workload_stats AS
SELECT 
    ta.assignee_id,
    ta.assignee_name,
    ta.assignment_type,
    COUNT(CASE WHEN ta.status = 'active' THEN 1 END) as active_assignments,
    COUNT(CASE WHEN ta.status = 'completed' THEN 1 END) as completed_assignments,
    COUNT(CASE WHEN ta.status = 'overdue' THEN 1 END) as overdue_assignments,
    AVG(CASE 
        WHEN ta.status = 'completed' AND ta.completed_at IS NOT NULL 
        THEN julianday(ta.completed_at) - julianday(ta.created_at)
    END) as avg_completion_days
FROM translation_assignments ta
GROUP BY ta.assignee_id, ta.assignee_name, ta.assignment_type;

-- ============================================================
-- 11. 创建索引
-- ============================================================

-- 翻译状态历史索引
CREATE INDEX IF NOT EXISTS idx_translation_state_history_entry_uid ON translation_state_history(entry_uid);
CREATE INDEX IF NOT EXISTS idx_translation_state_history_to_state ON translation_state_history(to_state);
CREATE INDEX IF NOT EXISTS idx_translation_state_history_created_at ON translation_state_history(created_at);
CREATE INDEX IF NOT EXISTS idx_translation_state_history_operator ON translation_state_history(operator_id);

-- 批量操作索引
CREATE INDEX IF NOT EXISTS idx_translation_batch_operations_status ON translation_batch_operations(status);
CREATE INDEX IF NOT EXISTS idx_translation_batch_operations_operator ON translation_batch_operations(operator_id);
CREATE INDEX IF NOT EXISTS idx_translation_batch_operations_created_at ON translation_batch_operations(created_at);

-- 分配表索引
CREATE INDEX IF NOT EXISTS idx_translation_assignments_entry_uid ON translation_assignments(entry_uid);
CREATE INDEX IF NOT EXISTS idx_translation_assignments_assignee ON translation_assignments(assignee_id);
CREATE INDEX IF NOT EXISTS idx_translation_assignments_status ON translation_assignments(status);
CREATE INDEX IF NOT EXISTS idx_translation_assignments_type ON translation_assignments(assignment_type);
CREATE INDEX IF NOT EXISTS idx_translation_assignments_due_date ON translation_assignments(due_date);

-- 状态转换索引
CREATE INDEX IF NOT EXISTS idx_translation_state_transitions_from_state ON translation_state_transitions(from_state);
CREATE INDEX IF NOT EXISTS idx_translation_state_transitions_to_state ON translation_state_transitions(to_state);

-- ============================================================
-- 12. 触发器：自动记录状态变更历史
-- ============================================================

CREATE TRIGGER IF NOT EXISTS trg_translation_entry_status_history
    AFTER UPDATE OF status ON core_translation_entries
    WHEN NEW.status != OLD.status
BEGIN
    INSERT INTO translation_state_history (
        entry_uid, from_state, to_state, transition_name, 
        operator_id, operator_name, reason
    ) VALUES (
        NEW.uid, OLD.status, NEW.status, 'manual_change',
        'system', 'system', 'Status updated via direct modification'
    );
END;

-- ============================================================
-- 13. 触发器：更新批量操作进度
-- ============================================================

CREATE TRIGGER IF NOT EXISTS trg_update_batch_operation_progress
    AFTER UPDATE ON translation_batch_operation_details
    WHEN NEW.status != OLD.status AND NEW.status IN ('success', 'failed', 'skipped')
BEGIN
    UPDATE translation_batch_operations 
    SET 
        processed_count = (
            SELECT COUNT(*) FROM translation_batch_operation_details 
            WHERE operation_id = NEW.operation_id 
            AND status IN ('success', 'failed', 'skipped')
        ),
        success_count = (
            SELECT COUNT(*) FROM translation_batch_operation_details 
            WHERE operation_id = NEW.operation_id AND status = 'success'
        ),
        failed_count = (
            SELECT COUNT(*) FROM translation_batch_operation_details 
            WHERE operation_id = NEW.operation_id AND status = 'failed'
        ),
        status = CASE 
            WHEN (
                SELECT COUNT(*) FROM translation_batch_operation_details 
                WHERE operation_id = NEW.operation_id 
                AND status = 'pending'
            ) = 0 THEN 'completed'
            ELSE 'running'
        END,
        completed_at = CASE 
            WHEN (
                SELECT COUNT(*) FROM translation_batch_operation_details 
                WHERE operation_id = NEW.operation_id 
                AND status = 'pending'
            ) = 0 THEN datetime('now')
            ELSE completed_at
        END
    WHERE operation_id = NEW.operation_id;
END;

-- ============================================================
-- 14. 触发器：自动更新分配状态
-- ============================================================

CREATE TRIGGER IF NOT EXISTS trg_update_assignment_status
    AFTER UPDATE OF status ON core_translation_entries
    WHEN NEW.status IN ('translated', 'reviewed', 'approved', 'published')
BEGIN
    UPDATE translation_assignments 
    SET 
        status = 'completed',
        completed_at = datetime('now')
    WHERE entry_uid = NEW.uid 
    AND assignment_type = CASE 
        WHEN NEW.status = 'translated' THEN 'translate'
        WHEN NEW.status IN ('reviewed', 'approved') THEN 'review'
        WHEN NEW.status = 'published' THEN 'approve'
    END
    AND status = 'active';
END;