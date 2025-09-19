# 翻译状态管理系统

## 系统概述

本系统实现了完整的翻译状态管理，支持翻译工作流和协作功能。系统基于Clean Architecture架构设计，采用领域驱动设计（DDD）和依赖注入模式，提供了强大的状态管理、批量操作、统计分析和权限控制能力。

## 核心功能

### 1. 状态管理
- **14种状态类型**：草稿、待翻译、已分配、已翻译、审核中、已审核、需修改、已批准、已发布、已拒绝、已锁定、冲突中、暂停、已归档
- **4种状态分类**：翻译流程、质量控制、协作管理、发布流程
- **状态转换规则**：支持权限控制、自动触发、验证规则和前置条件
- **工作流引擎**：支持多种工作流模式（标准、快速、协作、质量优先）

### 2. 批量操作
- **状态变更**：批量修改翻译条目状态
- **任务分配**：批量分配翻译和审核任务
- **审核操作**：批量审核、批准或拒绝翻译
- **发布管理**：批量发布和清理操作
- **并发处理**：支持多线程并发执行，可配置并发数

### 3. 统计分析
- **实时统计**：状态分布、进度统计、完成率分析
- **趋势分析**：30天内的状态变更趋势
- **性能指标**：翻译效率、审核速度、质量指标
- **瓶颈识别**：自动识别工作流瓶颈并提供建议
- **工作负载分析**：团队和个人工作量统计

### 4. 权限控制
- **基于角色的访问控制（RBAC）**：9种用户角色，40+项权限
- **角色层次结构**：支持权限继承和层级管理
- **上下文权限**：基于项目、资源所有权的细粒度权限控制
- **工作流权限**：不同状态转换需要不同角色权限

### 5. 事件通知
- **实时事件系统**：状态变更、批量操作完成等事件
- **多渠道通知**：应用内通知、邮件、Webhook
- **事件处理器**：可扩展的事件处理机制
- **通知模板**：支持自定义通知模板和内容

## 技术架构

### 数据库设计

#### 核心表结构
```sql
-- 翻译状态定义
translation_states
- state_key (状态键)
- display_name (显示名称)
- category (状态分类)
- color_hex (颜色)
- icon_name (图标)

-- 状态转换规则
translation_state_transitions
- from_state, to_state (状态转换)
- transition_name (转换名称)
- required_role (所需角色)
- auto_trigger (自动触发)
- validation_rules (验证规则)

-- 状态历史记录
translation_state_history
- entry_uid (条目ID)
- from_state, to_state (状态变更)
- operator_id, operator_name (操作者)
- reason (变更原因)
- metadata (元数据)

-- 批量操作记录
translation_batch_operations
- operation_id (操作ID)
- operation_type (操作类型)
- total_count, success_count, failed_count (统计)
- status (操作状态)

-- 任务分配
translation_assignments
- assignment_id (分配ID)
- entry_uid (条目ID)
- assignee_id, assignee_name (被分配者)
- assignment_type (分配类型)
- priority (优先级)
```

#### 视图和统计
```sql
-- 状态统计视图
translation_state_stats
- 各状态的条目数量和百分比

-- 进度统计视图
translation_progress_stats
- 按MOD/项目的翻译进度

-- 工作负载统计视图
translation_workload_stats
- 个人工作量和完成时间
```

### 领域模型

#### 核心实体
- **TranslationState**: 翻译状态定义
- **StateTransition**: 状态转换规则
- **WorkflowRule**: 工作流规则
- **StateHistory**: 状态历史记录
- **TranslationStateMachine**: 状态机

#### 领域服务
- **TranslationStateService**: 状态管理核心逻辑
- **TranslationPermissionService**: 权限验证服务
- **TranslationEventService**: 事件处理服务

#### 应用服务
- **TranslationStateApplicationService**: 状态管理应用服务
- **TranslationBatchOperationService**: 批量操作服务
- **TranslationStateStatisticsService**: 统计分析服务

### API接口

#### 状态管理接口
```
GET  /api/v1/translation/states/list                    # 获取所有状态
POST /api/v1/translation/states/change                  # 变更状态
GET  /api/v1/translation/states/actions/{entry_uid}     # 获取可用动作
GET  /api/v1/translation/states/history/{entry_uid}     # 获取状态历史
POST /api/v1/translation/states/auto-transition/{entry_uid}  # 自动转换
```

#### 批量操作接口
```
POST /api/v1/translation/states/batch/state-change     # 批量状态变更
POST /api/v1/translation/states/batch/assignment       # 批量分配
POST /api/v1/translation/states/batch/review          # 批量审核
GET  /api/v1/translation/states/batch/operations      # 获取操作列表
GET  /api/v1/translation/states/batch/operations/{id} # 获取操作状态
```

#### 统计报表接口
```
GET  /api/v1/translation/states/statistics                    # 基础统计
GET  /api/v1/translation/states/statistics/comprehensive      # 综合统计
POST /api/v1/translation/states/reports/progress             # 进度报告
GET  /api/v1/translation/states/reports/performance          # 性能分析
GET  /api/v1/translation/states/reports/quality              # 质量仪表板
GET  /api/v1/translation/states/reports/workload             # 工作负载报告
```

## 使用示例

### 1. 状态变更
```python
# 变更翻译条目状态
success, error_msg = state_service.change_translation_state(
    entry_uid="entry_123",
    target_state="translated",
    operator_id="user_1",
    operator_name="翻译者1",
    reason="完成翻译"
)
```

### 2. 批量操作
```python
# 批量状态变更配置
config = BatchOperationConfig(
    operation_type=BatchOperationType.STATE_CHANGE,
    operation_name="批量标记为已翻译",
    target_filter={"status": "pending"},
    operation_params={"target_state": "translated"},
    operator_id="admin",
    operator_name="管理员"
)

# 执行批量操作
result = await batch_service.execute_batch_operation(config)
```

### 3. 权限验证
```python
# 检查用户权限
has_permission = permission_service.check_permission(
    user_id="translator1",
    permission=Permission.CHANGE_STATE,
    project_id="project_123"
)
```

### 4. 事件处理
```python
# 发出状态变更事件
await event_service.emit_state_change_event(state_history, {
    "entry_key": "test.greeting",
    "project_name": "我的世界翻译项目"
})
```

## 性能特性

- **状态变更响应时间**: < 500ms
- **批量操作性能**: 1000条目批量变更 < 5秒
- **统计查询性能**: < 2秒
- **并发支持**: 可配置5-16个并发线程
- **事件处理**: 异步事件队列，支持高并发

## 扩展性

### 1. 自定义状态
- 支持添加新的状态类型
- 可配置状态属性（颜色、图标、权限等）
- 支持状态分类和排序

### 2. 工作流定制
- 支持多种工作流模式
- 可配置转换规则和验证条件
- 支持自动触发和手动操作

### 3. 权限扩展
- 支持自定义角色和权限
- 可配置权限继承关系
- 支持项目级权限控制

### 4. 事件处理
- 可扩展的事件处理器
- 支持自定义通知渠道
- 可配置通知模板

## 监控和维护

### 1. 日志记录
- 结构化日志记录所有操作
- 支持日志级别配置
- 包含性能指标和错误追踪

### 2. 健康检查
- 数据库连接状态检查
- 事件队列状态监控
- 批量操作进度跟踪

### 3. 数据维护
- 自动清理历史记录
- 数据库索引优化
- 统计数据缓存

## 集成指南

### 1. 依赖注入
系统已集成到现有的依赖注入容器中，可通过以下方式获取服务：

```python
from core.di_container import get_dependency

# 获取状态管理服务
state_service = get_dependency(TranslationStateApplicationService)

# 获取批量操作服务
batch_service = get_dependency(TranslationBatchOperationService)

# 获取统计服务
stats_service = get_dependency(TranslationStateStatisticsService)
```

### 2. 数据库迁移
系统包含两个迁移脚本：
- `010_create_translation_state_management.sql`: 创建表结构
- `011_insert_default_translation_states.sql`: 插入默认数据

### 3. API集成
API路由已注册到主应用程序中：
```python
app.include_router(translation_state_router)  # 翻译状态管理
```

## 最佳实践

### 1. 状态设计
- 保持状态数量合理（10-20个）
- 明确定义状态转换路径
- 设置合理的权限要求

### 2. 批量操作
- 设置适当的并发数（5-10）
- 添加操作超时限制
- 提供详细的错误信息

### 3. 权限管理
- 定期审查用户权限
- 使用最小权限原则
- 记录敏感操作日志

### 4. 性能优化
- 合理使用批量操作
- 定期清理历史数据
- 监控数据库性能

## 故障排除

### 常见问题
1. **状态转换失败**: 检查权限配置和验证规则
2. **批量操作超时**: 调整并发数和超时设置
3. **统计数据不准确**: 检查数据库索引和触发器
4. **通知发送失败**: 检查事件服务配置和通知渠道

### 调试工具
- 查看状态历史记录
- 检查批量操作详情
- 分析统计报表
- 查看事件日志

## 未来扩展

### 计划功能
1. **AI辅助审核**: 基于机器学习的质量检测
2. **高级工作流**: 支持条件分支和并行处理
3. **实时协作**: WebSocket实时状态同步
4. **移动端支持**: 移动设备状态管理
5. **集成第三方工具**: 支持外部翻译工具集成

### 技术改进
1. **缓存优化**: Redis缓存提升性能
2. **消息队列**: 使用消息队列处理事件
3. **微服务拆分**: 将状态管理独立为微服务
4. **GraphQL支持**: 提供GraphQL API

---

该翻译状态管理系统为TH-Suite MC L10n提供了企业级的状态管理能力，支持大规模翻译项目的协作和管理。系统设计遵循最佳实践，具备良好的扩展性和维护性。