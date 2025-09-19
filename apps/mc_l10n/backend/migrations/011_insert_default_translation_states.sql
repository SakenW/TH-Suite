-- TH-Suite MC L10n - 默认翻译状态数据
-- 创建时间: 2025-09-20
-- 说明: 插入默认的翻译状态、转换规则和工作流配置

-- ============================================================
-- 1. 插入默认翻译状态
-- ============================================================

INSERT OR REPLACE INTO translation_states (
    state_key, display_name, description, category, color_hex, icon_name, sort_order
) VALUES 
-- 翻译流程状态
('draft', '草稿', '刚创建或编辑中的翻译条目', 'translation', '#9CA3AF', 'edit', 10),
('pending', '待翻译', '等待翻译的条目', 'translation', '#F59E0B', 'clock', 20),
('translated', '已翻译', '已完成翻译但未审核', 'translation', '#3B82F6', 'check', 30),

-- 质量控制状态
('under_review', '审核中', '正在进行质量审核', 'quality', '#8B5CF6', 'eye', 40),
('reviewed', '已审核', '已通过质量审核', 'quality', '#10B981', 'check-circle', 50),
('needs_revision', '需修改', '审核发现问题，需要修改', 'quality', '#F97316', 'alert-triangle', 45),

-- 发布流程状态
('approved', '已批准', '已批准可以发布', 'publication', '#059669', 'thumbs-up', 60),
('published', '已发布', '已发布到生产环境', 'publication', '#065F46', 'check-circle-2', 70),
('archived', '已归档', '已归档的历史版本', 'publication', '#6B7280', 'archive', 80),

-- 协作状态
('assigned', '已分配', '已分配给特定译者', 'collaboration', '#7C3AED', 'user-check', 25),
('locked', '已锁定', '被锁定编辑的条目', 'collaboration', '#DC2626', 'lock', 90),
('conflict', '冲突中', '存在冲突需要解决', 'collaboration', '#EF4444', 'alert-circle', 95),

-- 特殊状态
('rejected', '已拒绝', '被拒绝的翻译', 'quality', '#B91C1C', 'x-circle', 85),
('on_hold', '暂停', '暂时停止处理', 'collaboration', '#6B7280', 'pause', 92);

-- ============================================================
-- 2. 插入状态转换规则
-- ============================================================

-- 基础翻译流程转换
INSERT OR REPLACE INTO translation_state_transitions (
    from_state, to_state, transition_name, required_role, auto_trigger, sort_order
) VALUES 
-- 从草稿开始
('draft', 'pending', 'submit_for_translation', 'contributor', FALSE, 10),
('draft', 'assigned', 'assign_translator', 'coordinator', FALSE, 11),
('draft', 'translated', 'direct_translate', 'translator', FALSE, 12),

-- 待翻译状态转换
('pending', 'assigned', 'assign_translator', 'coordinator', FALSE, 20),
('pending', 'translated', 'complete_translation', 'translator', FALSE, 21),
('pending', 'on_hold', 'put_on_hold', 'coordinator', FALSE, 22),

-- 已分配状态转换
('assigned', 'translated', 'complete_translation', 'translator', FALSE, 30),
('assigned', 'pending', 'unassign', 'coordinator', FALSE, 31),
('assigned', 'on_hold', 'put_on_hold', 'coordinator', FALSE, 32),

-- 已翻译状态转换
('translated', 'under_review', 'submit_for_review', 'translator', TRUE, 40),
('translated', 'reviewed', 'quick_approve', 'senior_reviewer', FALSE, 41),
('translated', 'needs_revision', 'request_revision', 'reviewer', FALSE, 42),
('translated', 'rejected', 'reject_translation', 'reviewer', FALSE, 43),

-- 审核中状态转换
('under_review', 'reviewed', 'approve_translation', 'reviewer', FALSE, 50),
('under_review', 'needs_revision', 'request_revision', 'reviewer', FALSE, 51),
('under_review', 'rejected', 'reject_translation', 'reviewer', FALSE, 52),

-- 需修改状态转换
('needs_revision', 'translated', 'complete_revision', 'translator', FALSE, 60),
('needs_revision', 'under_review', 'resubmit_for_review', 'translator', FALSE, 61),
('needs_revision', 'rejected', 'abandon_translation', 'translator', FALSE, 62),

-- 已审核状态转换
('reviewed', 'approved', 'approve_for_publication', 'admin', FALSE, 70),
('reviewed', 'published', 'publish_directly', 'admin', FALSE, 71),
('reviewed', 'needs_revision', 'request_final_revision', 'admin', FALSE, 72),

-- 已批准状态转换
('approved', 'published', 'publish_translation', 'admin', FALSE, 80),
('approved', 'archived', 'archive_translation', 'admin', FALSE, 81),

-- 已发布状态转换
('published', 'archived', 'archive_published', 'admin', FALSE, 90),
('published', 'needs_revision', 'request_hotfix', 'admin', FALSE, 91),

-- 特殊状态转换
('rejected', 'draft', 'restart_translation', 'translator', FALSE, 100),
('rejected', 'pending', 'requeue_translation', 'coordinator', FALSE, 101),

('on_hold', 'pending', 'resume_translation', 'coordinator', FALSE, 110),
('on_hold', 'assigned', 'resume_assigned', 'coordinator', FALSE, 111),

('conflict', 'translated', 'resolve_conflict', 'coordinator', FALSE, 120),
('conflict', 'needs_revision', 'mark_for_revision', 'coordinator', FALSE, 121),

-- 锁定/解锁转换
('locked', 'translated', 'unlock_and_approve', 'admin', FALSE, 130),
('locked', 'pending', 'unlock_and_reset', 'admin', FALSE, 131),
('translated', 'locked', 'lock_translation', 'admin', FALSE, 132),
('under_review', 'locked', 'lock_under_review', 'admin', FALSE, 133);

-- ============================================================
-- 3. 插入默认工作流规则
-- ============================================================

INSERT OR REPLACE INTO translation_workflow_rules (
    rule_name, description, target_type, rule_config, priority
) VALUES 

-- 标准翻译工作流
('standard_translation_workflow', '标准翻译工作流：翻译→审核→发布', 'global', json('
{
  "name": "标准翻译工作流",
  "description": "适用于大多数翻译项目的标准流程",
  "stages": [
    {
      "name": "翻译阶段",
      "states": ["draft", "pending", "assigned", "translated"],
      "required_roles": ["translator"],
      "auto_transitions": [
        {"from": "translated", "to": "under_review", "condition": "auto_review_enabled"}
      ]
    },
    {
      "name": "审核阶段", 
      "states": ["under_review", "reviewed", "needs_revision"],
      "required_roles": ["reviewer"],
      "quality_gates": [
        {"type": "completeness_check", "threshold": 0.95},
        {"type": "terminology_check", "enabled": true},
        {"type": "format_validation", "enabled": true}
      ]
    },
    {
      "name": "发布阶段",
      "states": ["approved", "published"],
      "required_roles": ["admin"],
      "approval_required": true
    }
  ],
  "notifications": {
    "translation_completed": {"template": "translation_ready_for_review", "recipients": ["reviewers"]},
    "review_completed": {"template": "review_completed", "recipients": ["translators", "admins"]},
    "publication_ready": {"template": "ready_for_publication", "recipients": ["admins"]}
  }
}'), 100),

-- 快速发布工作流
('rapid_deployment_workflow', '快速发布工作流：跳过部分审核步骤', 'global', json('
{
  "name": "快速发布工作流",
  "description": "用于紧急修复或简单翻译的快速流程",
  "stages": [
    {
      "name": "翻译阶段",
      "states": ["draft", "pending", "translated"],
      "required_roles": ["senior_translator"],
      "auto_transitions": [
        {"from": "translated", "to": "approved", "condition": "senior_translator_mode"}
      ]
    },
    {
      "name": "发布阶段",
      "states": ["approved", "published"],
      "required_roles": ["admin"],
      "approval_required": false
    }
  ],
  "quality_gates": [
    {"type": "basic_validation", "enabled": true},
    {"type": "security_check", "enabled": true}
  ]
}'), 80),

-- 协作翻译工作流
('collaborative_workflow', '协作翻译工作流：支持多人协作和冲突解决', 'global', json('
{
  "name": "协作翻译工作流",
  "description": "支持多人协作翻译的复杂流程",
  "features": {
    "assignment_system": true,
    "conflict_detection": true,
    "peer_review": true,
    "version_control": true
  },
  "stages": [
    {
      "name": "分配阶段",
      "states": ["draft", "pending", "assigned"],
      "required_roles": ["coordinator"],
      "assignment_rules": {
        "auto_assign": true,
        "load_balancing": true,
        "skill_matching": true
      }
    },
    {
      "name": "协作翻译",
      "states": ["assigned", "translated", "conflict"],
      "required_roles": ["translator"],
      "conflict_resolution": {
        "detection_enabled": true,
        "auto_merge": false,
        "escalation_timeout": "72h"
      }
    },
    {
      "name": "同行审核",
      "states": ["under_review", "reviewed", "needs_revision"],
      "required_roles": ["peer_reviewer"],
      "peer_review_rules": {
        "min_reviewers": 2,
        "consensus_threshold": 0.8
      }
    },
    {
      "name": "最终发布",
      "states": ["approved", "published"],
      "required_roles": ["admin"],
      "final_checks": ["cross_reference", "consistency", "completeness"]
    }
  ]
}'), 90),

-- 质量优先工作流
('quality_first_workflow', '质量优先工作流：严格的质量控制流程', 'global', json('
{
  "name": "质量优先工作流",
  "description": "适用于高质量要求项目的严格流程",
  "quality_controls": {
    "multi_stage_review": true,
    "terminology_validation": true,
    "consistency_check": true,
    "linguistic_review": true
  },
  "stages": [
    {
      "name": "初译阶段",
      "states": ["draft", "pending", "translated"],
      "required_roles": ["translator"],
      "quality_gates": [
        {"type": "completeness_check", "threshold": 1.0},
        {"type": "basic_validation", "enabled": true}
      ]
    },
    {
      "name": "技术审核",
      "states": ["under_review"],
      "required_roles": ["technical_reviewer"],
      "review_criteria": ["terminology", "technical_accuracy", "context_appropriateness"]
    },
    {
      "name": "语言审核",
      "states": ["reviewed"],
      "required_roles": ["linguistic_reviewer"], 
      "review_criteria": ["grammar", "style", "readability", "cultural_adaptation"]
    },
    {
      "name": "最终审批",
      "states": ["approved"],
      "required_roles": ["quality_manager"],
      "approval_criteria": ["overall_quality", "consistency", "completeness"]
    },
    {
      "name": "发布验证",
      "states": ["published"],
      "required_roles": ["admin"],
      "post_publication_checks": ["format_validation", "integration_test"]
    }
  ]
}'), 95);

-- ============================================================
-- 4. 插入默认通知模板配置
-- ============================================================

INSERT OR REPLACE INTO translation_workflow_rules (
    rule_name, description, target_type, rule_config, priority
) VALUES 
('notification_templates', '系统通知模板配置', 'global', json('
{
  "templates": {
    "translation_ready_for_review": {
      "subject": "翻译已完成，等待审核",
      "body": "翻译条目 {entry_key} 已完成翻译，请及时进行审核。\\n翻译者：{translator}\\n完成时间：{completed_at}",
      "channels": ["email", "in_app"]
    },
    "review_completed": {
      "subject": "审核已完成", 
      "body": "翻译条目 {entry_key} 的审核已完成。\\n审核结果：{review_result}\\n审核者：{reviewer}\\n审核时间：{reviewed_at}",
      "channels": ["email", "in_app"]
    },
    "ready_for_publication": {
      "subject": "翻译准备发布",
      "body": "翻译条目 {entry_key} 已通过所有审核，可以发布。\\n项目：{project_name}\\n完成度：{completion_rate}%",
      "channels": ["email", "in_app"]
    },
    "assignment_notification": {
      "subject": "新的翻译任务分配",
      "body": "您有新的翻译任务：{entry_key}\\n任务类型：{assignment_type}\\n截止时间：{due_date}\\n优先级：{priority}",
      "channels": ["email", "in_app", "push"]
    },
    "conflict_detected": {
      "subject": "检测到翻译冲突",
      "body": "翻译条目 {entry_key} 存在冲突，需要手动解决。\\n冲突类型：{conflict_type}\\n涉及译者：{contributors}",
      "channels": ["email", "in_app"],
      "priority": "high"
    },
    "batch_operation_completed": {
      "subject": "批量操作已完成",
      "body": "批量操作 {operation_name} 已完成。\\n处理总数：{total_count}\\n成功：{success_count}\\n失败：{failed_count}",
      "channels": ["email", "in_app"]
    }
  }
}'), 0);

-- ============================================================
-- 5. 更新core_translation_entries的状态到新系统
-- ============================================================

-- 将现有的旧状态映射到新的状态系统
UPDATE core_translation_entries SET status = 'pending' WHERE status = 'new';
UPDATE core_translation_entries SET status = 'translated' WHERE status = 'mt';
-- 其他状态保持不变：reviewed, locked, rejected, conflict