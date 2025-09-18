# TODO: 分层异步增量扫描系统实现

基于 `/home/saken/project/TH-Suite/扫描规则.md` 规格，实现新的分层异步增量扫描架构，解决当前扫描卡顿和数据库冲突问题。

## 🎯 核心目标

**当前问题**: 扫描卡顿、UNIQUE约束冲突、用户体验差  
**预期收益**: 1-2秒首屏响应、渐进式补全、中断可续扫、增量更新  
**实施工期**: 约2周工作量、分10个阶段执行  
**风险等级**: 中等（保持V5 SSOT架构，仅增补缓存表）

## ✅ 核心设计原则

- **1-2秒首屏响应**：点击扫描后立即显示MOD列表
- **渐进式补全**：10秒内≥30%行补齐关键信息
- **中断可续扫**：异常退出后≤1秒恢复进度
- **增量扫描**：版本变更时仅处理Δ部分，耗时≤首次20%
- **保持V5 SSOT**：不改动core/ops表结构，仅增补cache表

## 📋 实施清单（按优先级排序）

### Phase 1: 数据库契约与快照引擎（0.5天 + 2天）

#### 1.1 数据库表结构设计
- [ ] **新增 `cache_scan_snapshots` 表**
  - 字段：`snapshot_id, session_id, pack_uid, pack_version_uid?, root_path, files_json, created_at`
  - 存储：文件快照（路径、大小、修改时间、JAR中央目录信息）
  - 索引：`(created_at)`, `(pack_uid, created_at)`

- [ ] **新增 `cache_scan_delta` 表**
  - 字段：`snapshot_id, session_id, delta_json{added[],modified[],moved[],removed[],touched_mods[]}, created_at`
  - 存储：两次扫描间的文件变化差异
  - 索引：`(snapshot_id)`, `(session_id, created_at)`

- [ ] **可选：`ops_event_log` 表**
  - 字段：`event_id, session_id, event_type, entity_ref, stage, artifact_hash?, payload_json, ts`
  - 存储：扫描事件流水，支持幂等和重放
  - 索引：`(session_id, ts)`, `(event_type, entity_ref)`

#### 1.2 快照构建引擎
- [ ] **实现 SnapshotBuilder 类**
  - 快速遍历目录结构（≤2秒）
  - 生成文件指纹信息：`size+mtime` → `jar_cd_entries/jar_cd_crc` → `BLAKE3`
  - 写入 `cache_scan_snapshots`
  - 支持中断恢复

- [ ] **实现 DiffEngine 类**
  - 对比当前快照与上次快照
  - 生成增量变化（added/modified/moved/removed）
  - 识别移动/重命名（hash不变仅更新路径）
  - 写入 `cache_scan_delta`

### Phase 2: 任务队列与检查点系统（2天）

#### 2.1 扩展工作队列
- [ ] **扩展 `ops_work_queue.type` 枚举**
  - 新增：`scan_enum`, `scan_meta`, `scan_lang`, `scan_verify`
  - 保持现有表结构不变，仅增加类型

- [ ] **实现检查点机制**
  - 检查点数据写入 `payload_json`：`{stage, artifact_ref, artifact_hash?, last_step, offset?}`
  - 支持任务中断后从检查点续扫
  - 指数退避重试机制

#### 2.2 扫描编排器
- [ ] **实现 ScanOrchestrator 类**
  - 协调快照→差异→任务派发流程
  - 管理扫描会话生命周期
  - 优先级调度：可见优先(100) > Δ变更(70) > RAS补完(50) > 非RAS补完(20)

### Phase 3: 单写入者与批量落库（2天）

#### 3.1 EventApplier实现
- [ ] **实现EventApplier类**
  - 单写入者模式，避免数据库锁争用
  - 批量处理：batch_size=200 或 flush_interval=500ms
  - WAL模式写入，确保数据安全
  - 支持事务回滚

#### 3.2 数据库操作优化
- [ ] **修复UNIQUE约束冲突**
  - 实现UPSERT逻辑：`INSERT ... ON CONFLICT DO UPDATE`
  - 处理重复modid的情况
  - 确保数据一致性

### Phase 4: 异步Worker系统（3天）

#### 4.1 分层Worker实现
- [ ] **ENUM Worker**
  - 处理目录枚举和manifest解析
  - 支持Modrinth/CurseForge/自定义格式
  - 产生 `LIST_UPSERT` 事件

- [ ] **META Worker**  
  - 解析MOD元数据：mods.toml/fabric.mod.json/mcmod.info
  - 提取：modid/loader/mc_version/version/作者/描述
  - 产生 `FIELD_PATCH` 事件

- [ ] **LANG Worker**
  - 解析语言文件：.json/.lang/.properties
  - 提取键值对和统计信息
  - 产生 `LANG_UPSERT` 事件

- [ ] **VERIFY Worker**
  - 处理去重/冲突检测/统计/墓碑标记
  - 产生 `CONFLICT`/`TOMB_STONE` 事件

#### 4.2 事件处理系统
- [ ] **实现Event类型定义**
  - `LIST_UPSERT`：列表行上屏/更新
  - `FIELD_PATCH`：版本/作者/loader/语言数
  - `LANG_UPSERT`：language_file与entries增量
  - `COUNT_PATCH`：计数/统计
  - `TOMB_STONE`：删除/移动墓碑
  - `CONFLICT`：冲突标记
  - `PROGRESS`：会话/行内进度
  - `ERROR`：错误徽章与重试

- [ ] **实现事件幂等机制**
  - 幂等键：`session_id + event_type + entity_ref + stage + artifact_hash`
  - 支持事件重放和会话回滚

### Phase 5: 新扫描API设计（2天）

#### 5.1 实现分层异步扫描API
- [ ] `POST /api/v6/scan/async-start`：启动异步扫描，立即返回session_id
- [ ] `GET /api/v6/scan/session/{session_id}`：获取扫描进度和结果
- [ ] `POST /api/v6/scan/session/{session_id}/cancel`：取消扫描
- [ ] `GET /api/v6/scan/snapshots`：获取历史快照

#### 5.2 WebSocket推送
- [ ] **实现实时事件推送**
  - 扫描进度推送
  - 渐进式结果更新
  - 错误和冲突通知

### Phase 6: 验收测试（1-2天）

#### 6.1 性能验收
- [ ] **A-01 首屏**：100-300 MOD，点击后≤2s出列表
- [ ] **A-02 渐进补全**：10秒内≥30%行补完关键字段  
- [ ] **A-03 中断恢复**：异常退出后≤1s恢复进度
- [ ] **A-04 版本增量**：仅10/300 MOD变化，总耗时≤首次20%
- [ ] **A-05 移动/重命名**：不触发解析，仅路径更新
- [ ] **A-06 一致性**：事件重放后DB与UI一致

#### 6.2 功能验收  
- [ ] **B-01 失败隔离**：单文件失败不拖累总进度
- [ ] **B-02 资源约束**：扫描期CPU≤60%，峰值内存≤1.5GB

## 🚧 技术风险与注意事项

1. **数据库迁移**：新增表结构需要平滑迁移，避免影响现有功能
2. **并发控制**：Worker和EventApplier的并发协调
3. **内存管理**：快照和缓存的内存使用控制
4. **向下兼容**：保持现有API的向下兼容性
5. **测试覆盖**：关键路径需要充分的单元测试和集成测试

## 📅 时间预估

- **Phase 1-2**：核心架构 - 4天
- **Phase 3-4**：Worker系统 - 5天  
- **Phase 5-6**：API和验收 - 3天

**总计：约2周工作量**

## 🎯 立即开始

建议从 **Phase 1.1 数据库表结构设计** 开始，这是整个架构的基础。完成数据库设计后，可以并行开发快照引擎和任务队列系统。

## 📚 相关文档引用

- **扫描规则原文**: [/home/saken/project/TH-Suite/扫描规则.md](/home/saken/project/TH-Suite/扫描规则.md) ⭐
- **V5 数据库设计**: [docs/architecture/database/v5-ssot-database-design.md](docs/architecture/database/v5-ssot-database-design.md)
- **扫描架构文档**: [docs/scanning/](docs/scanning/) ⭐

## ✅ 已完成工作

### 📚 扫描系统文档完善 (2025-09-16)

基于三层扫描架构的实际实现，完成了完整的技术文档编写：

#### 已创建文档
- ✅ **[三层扫描架构概览](docs/scanning/scanning-architecture-overview.md)** (新建)
  - 详细描述标准/优化/低内存三种扫描器的设计理念
  - 包含性能对比数据和实时进度系统说明
  - 统一API接口规范和错误处理机制

- ✅ **[扫描器对比使用指南](docs/scanning/scanner-comparison-guide.md)** (已存在且完善)
  - 智能选择决策树和详细性能对比表
  - 系统配置推荐和配置参数矩阵
  - 实际测试数据 (DeceasedCraft 628MOD基准)

- ✅ **[低内存优化配置指南](docs/scanning/low-memory-optimization-guide.md)** (已存在且完善)
  - 内存优化核心技术：流式处理、自动GC、分批处理
  - 4GB/8GB/16GB不同硬件配置推荐方案
  - 实时配置调优API和监控告警系统

- ✅ **[API使用示例](docs/scanning/api-usage-examples.md)** (已存在且完善)
  - 三种扫描器完整API调用示例和响应格式
  - 批量自动化脚本和实时监控工具
  - 配置文件驱动扫描和错误处理最佳实践

- ✅ **[性能测试与故障排除](docs/scanning/performance-testing-troubleshooting.md)** (已存在且完善)
  - 综合基准测试框架和自定义性能测试脚本
  - 系统诊断工具和常见问题解决方案
  - 自动化故障排除和性能优化建议

- ✅ **[扫描系统主README](docs/scanning/README.md)** (更新完成)
  - 增强了对三层架构的整体说明
  - 添加了更详细的文档结构描述和快速开始指南

#### 文档特色
- **实用性强**: 包含大量实际代码示例、配置模板和API调用样例
- **分层明确**: 针对不同硬件配置 (4GB/8GB/16GB+) 提供精准推荐
- **全面覆盖**: 从架构设计、性能优化到故障排除的完整指南
- **可操作性**: 详细的故障诊断步骤和自动化脚本

#### 解决的问题
- 为用户提供了完整的三层扫描架构使用指南
- 帮助用户根据硬件配置选择最适合的扫描方案
- 提供了详细的性能调优和问题排查方法
- 建立了统一的API使用标准和最佳实践

---

**最后更新**: 2025-09-16  
**当前状态**: 分层异步增量扫描架构规划完成，相关文档已完善
**当前问题**: UNIQUE约束冲突、扫描卡顿、用户体验差  
**解决方案**: 快照-Δ模型 + 检查点化任务DAG + 内容寻址缓存  
**下一步**: 开始实施 Phase 1.1 数据库表结构设计