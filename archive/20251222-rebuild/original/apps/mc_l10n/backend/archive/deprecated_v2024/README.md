# 废弃组件归档 (2024年12月)

本目录包含已废弃的V6架构组件，这些组件已被现代化的V6架构替代。

## 废弃原因

项目存在多个冗余的数据库管理器和扫描器实例，导致架构混乱和维护困难。为了统一架构，将旧版组件迁移到此处。

## 已归档的组件

### 1. 旧版服务容器 (`src_old_container/`)
- **文件**: `src/container.py:ServiceContainer`
- **替代者**: `core/di_container.py:DIContainer`
- **废弃原因**: 架构过时，已被现代化的依赖注入容器替代

### 2. 旧版扫描服务 (`scan_service_old.py`)
- **原位置**: `services/scan_service.py:ModScanner`
- **替代者**: `core/ddd_scanner_simple.py:DDDScanner`
- **废弃原因**: 功能重复，V6架构已统一扫描逻辑

### 3. 废弃测试文件
- `test_mod_scanner.py` - 依赖已废弃的packages组件
- `test_scan_service.py` - 依赖旧版扫描服务
- `test_project_scanner.py` - 依赖已废弃的基础设施组件
- `test_architecture.py` - 依赖旧版组件架构

## 现行V6架构

### 数据库管理器
- ✅ **主要**: `database/core/manager.py:McL10nDatabaseManager`
- ✅ **适配器**: `core/di_container.py:DatabaseServiceAdapter`

### 扫描器
- ✅ **主要**: `core/ddd_scanner_simple.py:DDDScanner`
- ✅ **应用层**: `application/services/scan_application_service.py`

### 依赖注入
- ✅ **容器**: `core/di_container.py:DIContainer`

## 迁移指南

如果需要恢复某个功能，请参考现行V6架构的对应实现。不建议直接使用归档组件，而应该基于V6架构重新实现。

## 删除计划

这些组件将在2025年Q2完全删除。如有需要保留某个组件，请及时反馈。

---

*归档日期: 2024年12月*
*归档原因: V6架构统一，消除冗余组件*