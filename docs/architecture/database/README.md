# TH-Suite 数据库架构文档

## 📁 文档组织

### 🎯 权威设计文档
- **[v5-ssot-database-design.md](./v5-ssot-database-design.md)** - **MC L10n V5 完整架构设计 (SSOT)**
  - **状态**: 🎯 当前权威文档
  - **内容**: 16个表的完整设计（9个core + 4个ops + 2个cfg + 4个cache）
  - **用途**: 作为实现目标的权威参考

### 📚 归档文档
- **[../../archive/database-designs/v6-simplified-database-design.md](../../archive/database-designs/v6-simplified-database-design.md)** - V6简化版设计
  - **状态**: ⚠️ 已归档
  - **原因**: 实现过于简化，仅15个表，缺少完整的缓存层设计

## 🔍 当前实现状态

根据最新审查，当前实现与V5 SSOT设计存在显著差距：

### 已实现（6个表）
- ✅ `packs` (简化版)
- ✅ `pack_versions` (简化版)  
- ✅ `mod_version_instances` (简化版)
- ✅ `pack_mod_relations` (简化版)
- ✅ `content_instances` (简化版)
- ✅ `pack_content_relations` (简化版)

### 缺失实现（10个表）
- ❌ `core_projects`
- ❌ `core_pack_items`
- ❌ `core_pack_installations`
- ❌ `core_language_files`
- ❌ `ops_work_queue`
- ❌ `ops_outbox_journal` 
- ❌ `ops_sync_log`
- ❌ `ops_cas_objects`
- ❌ `cfg_local_settings`
- ❌ `cfg_file_watch`
- ❌ `cache_*` 表（4个缓存表）

## 🚀 下一步行动

1. **数据库迁移**: 将当前6个简化表升级为V5 SSOT的16个完整表
2. **代码重构**: 更新数据访问层以支持新的表结构
3. **功能扩展**: 实现工作队列、同步机制、缓存层等高级功能

---

**最后更新**: 2025-09-16  
**维护者**: TH-Suite 开发团队