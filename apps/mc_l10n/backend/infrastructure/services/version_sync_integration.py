"""
版本同步协议集成 - TH-Suite MC L10n
集成版本管理系统与现有的Trans-Hub同步协议
"""

import asyncio
import json
import logging
import uuid
from typing import Dict, Any, List, Optional, Tuple
from datetime import datetime, timedelta
from enum import Enum

from infrastructure.services.sync_protocol_service import (
    get_sync_protocol_service, SyncDirection, SyncStatus
)
from infrastructure.services.version_management_service import (
    get_version_management_service, EntityType
)
from infrastructure.services.version_operations_engine import get_version_operations_engine
from infrastructure.services.version_diff_engine import VersionDiffEngine, DiffType
from infrastructure.repositories.repository_factory import get_repository_factory

logger = logging.getLogger(__name__)


class VersionSyncStrategy(Enum):
    """版本同步策略枚举"""
    FULL_SNAPSHOT = "full_snapshot"      # 完整快照同步
    INCREMENTAL_DIFF = "incremental_diff"  # 增量差异同步
    SMART_MERGE = "smart_merge"          # 智能合并同步
    CONFLICT_AWARE = "conflict_aware"    # 冲突感知同步


class VersionConflictType(Enum):
    """版本冲突类型"""
    CONTENT_CONFLICT = "content_conflict"
    VERSION_CONFLICT = "version_conflict"
    METADATA_CONFLICT = "metadata_conflict"
    STRUCTURAL_CONFLICT = "structural_conflict"


class VersionSyncIntegration:
    """版本同步协议集成服务"""
    
    def __init__(self):
        self.sync_protocol_service = get_sync_protocol_service()
        self.version_service = get_version_management_service()
        self.operations_engine = get_version_operations_engine()
        self.diff_engine = VersionDiffEngine()
        self.factory = get_repository_factory()
        
        self.config = {
            "version_sync_enabled": True,
            "auto_create_repositories": True,
            "conflict_resolution_strategy": "manual",
            "max_sync_conflicts": 100,
            "version_retention_days": 90,
            "sync_batch_size": 1000,
            "enable_compression": True,
            "sync_timeout": 300
        }
    
    # ============================================================
    # 1. 版本感知同步
    # ============================================================
    
    async def sync_with_versions(self, direction: SyncDirection, 
                               project_uid: str = None,
                               strategy: VersionSyncStrategy = VersionSyncStrategy.SMART_MERGE,
                               create_version: bool = True) -> Dict[str, Any]:
        """
        执行版本感知的数据同步
        
        Args:
            direction: 同步方向
            project_uid: 项目UID
            strategy: 版本同步策略
            create_version: 是否创建版本
        """
        try:
            sync_session_uid = str(uuid.uuid4())
            
            logger.info(f"开始版本感知同步: {direction.value}, 策略: {strategy.value}")
            
            # 记录同步开始
            await self._log_version_sync_start(sync_session_uid, direction, strategy, project_uid)
            
            # 预同步阶段 - 版本状态检查
            pre_sync_result = await self._pre_sync_version_check(direction, project_uid)
            if not pre_sync_result["success"]:
                return pre_sync_result
            
            # 执行版本同步
            if direction == SyncDirection.SYNC_IN:
                result = await self._sync_in_with_versions(
                    sync_session_uid, strategy, project_uid, create_version
                )
            elif direction == SyncDirection.SYNC_OUT:
                result = await self._sync_out_with_versions(
                    sync_session_uid, strategy, project_uid, create_version
                )
            elif direction == SyncDirection.BIDIRECTIONAL:
                # 双向同步需要特殊处理
                result = await self._bidirectional_sync_with_versions(
                    sync_session_uid, strategy, project_uid, create_version
                )
            else:
                result = {
                    "success": False,
                    "message": f"不支持的同步方向: {direction.value}"
                }
            
            # 后同步阶段 - 版本整理和清理
            if result["success"]:
                cleanup_result = await self._post_sync_cleanup(sync_session_uid, project_uid)
                result["cleanup"] = cleanup_result
            
            # 记录同步完成
            await self._log_version_sync_complete(sync_session_uid, result)
            
            return result
            
        except Exception as e:
            logger.error(f"版本感知同步失败: {e}")
            await self._log_version_sync_complete(sync_session_uid, {
                "success": False, "error": str(e)
            })
            return {
                "success": False,
                "message": f"版本感知同步失败: {str(e)}"
            }
    
    async def _sync_in_with_versions(self, sync_session_uid: str, 
                                   strategy: VersionSyncStrategy,
                                   project_uid: str = None, 
                                   create_version: bool = True) -> Dict[str, Any]:
        """执行版本感知的sync_in"""
        
        # 获取远程版本信息
        remote_version_info = await self._get_remote_version_info(project_uid)
        if not remote_version_info["success"]:
            return remote_version_info
        
        # 获取本地版本信息
        local_version_info = await self._get_local_version_info(project_uid)
        
        # 比较版本差异
        version_comparison = await self._compare_versions(
            local_version_info.get("data"), remote_version_info.get("data")
        )
        
        if version_comparison["has_conflicts"]:
            # 处理版本冲突
            conflict_resolution = await self._handle_version_conflicts(
                sync_session_uid, version_comparison["conflicts"]
            )
            if not conflict_resolution["success"]:
                return conflict_resolution
        
        # 执行传统同步
        sync_result = await self.sync_protocol_service._sync_in("incremental", project_uid)
        if not sync_result["success"]:
            return sync_result
        
        # 创建本地版本提交
        if create_version and sync_result["success"]:
            version_result = await self._create_sync_version_commit(
                "sync_in", sync_session_uid, sync_result, project_uid
            )
            sync_result["version_commit"] = version_result
        
        return sync_result
    
    async def _sync_out_with_versions(self, sync_session_uid: str,
                                    strategy: VersionSyncStrategy,
                                    project_uid: str = None,
                                    create_version: bool = True) -> Dict[str, Any]:
        """执行版本感知的sync_out"""
        
        # 获取本地待同步的版本变更
        pending_changes = await self._get_pending_version_changes(project_uid)
        
        if not pending_changes["has_changes"]:
            return {
                "success": True,
                "message": "没有待同步的版本变更",
                "changes_count": 0
            }
        
        # 检查远程版本兼容性
        compatibility_check = await self._check_remote_version_compatibility(
            project_uid, pending_changes["changes"]
        )
        if not compatibility_check["compatible"]:
            return {
                "success": False,
                "message": "远程版本不兼容，无法同步",
                "compatibility_issues": compatibility_check["issues"]
            }
        
        # 执行传统同步
        sync_result = await self.sync_protocol_service._sync_out("incremental", project_uid)
        if not sync_result["success"]:
            return sync_result
        
        # 更新远程版本信息
        if sync_result["success"]:
            remote_update_result = await self._update_remote_version_info(
                project_uid, pending_changes["changes"]
            )
            sync_result["remote_version_update"] = remote_update_result
        
        # 标记本地变更已同步
        if sync_result["success"]:
            await self._mark_changes_synced(pending_changes["changes"])
        
        return sync_result
    
    async def _bidirectional_sync_with_versions(self, sync_session_uid: str,
                                              strategy: VersionSyncStrategy,
                                              project_uid: str = None,
                                              create_version: bool = True) -> Dict[str, Any]:
        """执行版本感知的双向同步"""
        
        # 首先执行sync_in
        sync_in_result = await self._sync_in_with_versions(
            sync_session_uid + "_in", strategy, project_uid, create_version
        )
        
        # 然后执行sync_out
        sync_out_result = await self._sync_out_with_versions(
            sync_session_uid + "_out", strategy, project_uid, create_version
        )
        
        # 检查是否需要合并
        if sync_in_result["success"] and sync_out_result["success"]:
            merge_result = await self._merge_bidirectional_changes(
                sync_session_uid, sync_in_result, sync_out_result, project_uid
            )
            
            return {
                "success": True,
                "message": "双向同步完成",
                "sync_in": sync_in_result,
                "sync_out": sync_out_result,
                "merge": merge_result
            }
        else:
            return {
                "success": False,
                "message": "双向同步部分失败",
                "sync_in": sync_in_result,
                "sync_out": sync_out_result
            }
    
    # ============================================================
    # 2. 版本冲突处理
    # ============================================================
    
    async def _compare_versions(self, local_data: Dict[str, Any], 
                              remote_data: Dict[str, Any]) -> Dict[str, Any]:
        """比较本地和远程版本"""
        
        conflicts = []
        
        # 检查版本号冲突
        local_version = local_data.get("version", "1.0.0")
        remote_version = remote_data.get("version", "1.0.0")
        
        if local_version != remote_version:
            conflicts.append({
                "type": VersionConflictType.VERSION_CONFLICT.value,
                "description": "版本号不匹配",
                "local_value": local_version,
                "remote_value": remote_version,
                "path": "version"
            })
        
        # 检查内容冲突
        local_content = local_data.get("content", {})
        remote_content = remote_data.get("content", {})
        
        if local_content != remote_content:
            # 使用差异引擎计算具体冲突
            diff = self.diff_engine.calculate_diff(local_content, remote_content)
            
            for operation in diff.operations:
                if operation.op.value in ["replace", "remove"]:
                    conflicts.append({
                        "type": VersionConflictType.CONTENT_CONFLICT.value,
                        "description": f"内容冲突: {operation.path}",
                        "local_value": operation.old_value,
                        "remote_value": operation.value,
                        "path": operation.path,
                        "operation": operation.op.value
                    })
        
        return {
            "has_conflicts": len(conflicts) > 0,
            "conflicts": conflicts,
            "conflicts_count": len(conflicts)
        }
    
    async def _handle_version_conflicts(self, sync_session_uid: str, 
                                      conflicts: List[Dict[str, Any]]) -> Dict[str, Any]:
        """处理版本冲突"""
        
        if self.config["conflict_resolution_strategy"] == "manual":
            # 手动冲突解决 - 记录冲突等待人工处理
            await self._record_version_conflicts(sync_session_uid, conflicts)
            return {
                "success": False,
                "message": "存在版本冲突，需要手动解决",
                "conflicts": conflicts,
                "resolution_required": True
            }
        
        elif self.config["conflict_resolution_strategy"] == "auto_local":
            # 自动使用本地版本
            resolution_result = await self._auto_resolve_conflicts(conflicts, "local")
            return {
                "success": True,
                "message": "冲突已自动解决（使用本地版本）",
                "resolution": resolution_result
            }
        
        elif self.config["conflict_resolution_strategy"] == "auto_remote":
            # 自动使用远程版本
            resolution_result = await self._auto_resolve_conflicts(conflicts, "remote")
            return {
                "success": True,
                "message": "冲突已自动解决（使用远程版本）",
                "resolution": resolution_result
            }
        
        else:
            return {
                "success": False,
                "message": f"不支持的冲突解决策略: {self.config['conflict_resolution_strategy']}"
            }
    
    async def _record_version_conflicts(self, sync_session_uid: str, 
                                      conflicts: List[Dict[str, Any]]) -> None:
        """记录版本冲突到数据库"""
        try:
            async with self.factory.get_db_connection() as conn:
                for conflict in conflicts:
                    conflict_uid = str(uuid.uuid4())
                    await conn.execute("""
                        INSERT INTO version_conflicts 
                        (uid, merge_uid, conflict_type, entity_path, 
                         base_value, source_value, target_value, created_at)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                    """, (
                        conflict_uid, sync_session_uid, conflict["type"], conflict["path"],
                        json.dumps(conflict.get("base_value")),
                        json.dumps(conflict.get("local_value")),
                        json.dumps(conflict.get("remote_value")),
                        datetime.now().isoformat()
                    ))
                
                await conn.commit()
                
        except Exception as e:
            logger.error(f"记录版本冲突失败: {e}")
    
    # ============================================================
    # 3. 版本信息管理
    # ============================================================
    
    async def _get_remote_version_info(self, project_uid: str = None) -> Dict[str, Any]:
        """获取远程版本信息"""
        try:
            # 模拟从Trans-Hub获取远程版本信息
            # 实际实现应该调用Trans-Hub API
            
            await asyncio.sleep(0.5)  # 模拟网络延迟
            
            return {
                "success": True,
                "data": {
                    "version": "2.1.5",
                    "last_commit": "abc123def456",
                    "last_sync": datetime.now().isoformat(),
                    "content": {
                        "projects": 3,
                        "translation_entries": 1250,
                        "language_files": 45
                    },
                    "metadata": {
                        "server": "trans-hub.org",
                        "api_version": "v5.2.1"
                    }
                }
            }
            
        except Exception as e:
            logger.error(f"获取远程版本信息失败: {e}")
            return {
                "success": False,
                "message": f"获取远程版本信息失败: {str(e)}"
            }
    
    async def _get_local_version_info(self, project_uid: str = None) -> Dict[str, Any]:
        """获取本地版本信息"""
        try:
            # 获取项目的版本仓库
            if project_uid:
                repository = await self.version_service._get_repository_by_entity(
                    EntityType.PROJECT, project_uid
                )
                
                if repository:
                    # 获取最新提交
                    commits_result = await self.version_service.get_commit_history(
                        repository["uid"], limit=1
                    )
                    
                    latest_commit = None
                    if commits_result["success"] and commits_result["commits"]:
                        latest_commit = commits_result["commits"][0]
                    
                    return {
                        "success": True,
                        "data": {
                            "version": "2.1.4",
                            "last_commit": latest_commit["commit_hash"] if latest_commit else None,
                            "repository_uid": repository["uid"],
                            "content": {
                                "projects": 2,
                                "translation_entries": 1180,
                                "language_files": 42
                            }
                        }
                    }
            
            # 默认版本信息
            return {
                "success": True,
                "data": {
                    "version": "2.1.4",
                    "last_commit": None,
                    "content": {}
                }
            }
            
        except Exception as e:
            logger.error(f"获取本地版本信息失败: {e}")
            return {
                "success": False,
                "message": f"获取本地版本信息失败: {str(e)}"
            }
    
    async def _create_sync_version_commit(self, sync_type: str, sync_session_uid: str,
                                        sync_result: Dict[str, Any], 
                                        project_uid: str = None) -> Dict[str, Any]:
        """创建同步版本提交"""
        try:
            # 获取或创建项目版本仓库
            if project_uid:
                repository = await self._ensure_project_repository(project_uid)
                if not repository["success"]:
                    return repository
                
                repository_uid = repository["repository_uid"]
            else:
                # 全局同步仓库
                repository_uid = await self._get_global_sync_repository()
            
            # 生成同步内容数据
            content_data = {
                "sync_type": sync_type,
                "sync_session_uid": sync_session_uid,
                "sync_result": sync_result,
                "project_uid": project_uid,
                "timestamp": datetime.now().isoformat(),
                "synced_items": sync_result.get("synced_items", {}),
                "changes": sync_result.get("changes", {})
            }
            
            # 创建提交
            commit_result = await self.version_service.create_commit(
                repository_uid=repository_uid,
                branch_name="main",
                author_name="TH-Suite Sync Service",
                message=f"同步提交: {sync_type}",
                content_data=content_data,
                description=f"自动同步提交 - 会话: {sync_session_uid}",
                metadata={
                    "sync_session_uid": sync_session_uid,
                    "sync_type": sync_type,
                    "automated": True
                }
            )
            
            return commit_result
            
        except Exception as e:
            logger.error(f"创建同步版本提交失败: {e}")
            return {
                "success": False,
                "message": f"创建同步版本提交失败: {str(e)}"
            }
    
    async def _ensure_project_repository(self, project_uid: str) -> Dict[str, Any]:
        """确保项目有版本仓库"""
        
        # 检查是否已存在
        repository = await self.version_service._get_repository_by_entity(
            EntityType.PROJECT, project_uid
        )
        
        if repository:
            return {
                "success": True,
                "repository_uid": repository["uid"]
            }
        
        # 创建新仓库
        create_result = await self.version_service.create_repository(
            EntityType.PROJECT, project_uid
        )
        
        if create_result["success"]:
            return {
                "success": True,
                "repository_uid": create_result["repository"]["uid"]
            }
        else:
            return create_result
    
    # ============================================================
    # 4. 辅助方法
    # ============================================================
    
    async def _pre_sync_version_check(self, direction: SyncDirection, 
                                    project_uid: str = None) -> Dict[str, Any]:
        """预同步版本检查"""
        try:
            # 检查版本管理服务状态
            if not self.config["version_sync_enabled"]:
                return {
                    "success": True,
                    "message": "版本同步已禁用，将使用传统同步"
                }
            
            # 检查网络连接
            connection_check = await self.sync_protocol_service.validate_connection()
            if not connection_check["success"]:
                return {
                    "success": False,
                    "message": "网络连接检查失败",
                    "details": connection_check
                }
            
            return {
                "success": True,
                "message": "预同步检查通过"
            }
            
        except Exception as e:
            logger.error(f"预同步版本检查失败: {e}")
            return {
                "success": False,
                "message": f"预同步版本检查失败: {str(e)}"
            }
    
    async def _log_version_sync_start(self, sync_session_uid: str, direction: SyncDirection,
                                    strategy: VersionSyncStrategy, project_uid: str = None) -> None:
        """记录版本同步开始"""
        try:
            async with self.factory.get_db_connection() as conn:
                await conn.execute("""
                    INSERT INTO ops_sync_log 
                    (direction, endpoint, request_meta, result, idempotency_key, created_at)
                    VALUES (?, ?, ?, ?, ?, ?)
                """, (
                    direction.value,
                    "version_sync",
                    json.dumps({
                        "sync_session_uid": sync_session_uid,
                        "strategy": strategy.value,
                        "project_uid": project_uid,
                        "version_enabled": True
                    }),
                    "pending",
                    sync_session_uid,
                    datetime.now().isoformat()
                ))
                
                await conn.commit()
                
        except Exception as e:
            logger.error(f"记录版本同步开始失败: {e}")
    
    async def _log_version_sync_complete(self, sync_session_uid: str, 
                                       result: Dict[str, Any]) -> None:
        """记录版本同步完成"""
        try:
            async with self.factory.get_db_connection() as conn:
                await conn.execute("""
                    UPDATE ops_sync_log 
                    SET result = ?, response_meta = ?
                    WHERE idempotency_key = ?
                """, (
                    "success" if result.get("success") else "fail",
                    json.dumps(result),
                    sync_session_uid
                ))
                
                await conn.commit()
                
        except Exception as e:
            logger.error(f"记录版本同步完成失败: {e}")


# 全局版本同步集成服务实例
version_sync_integration: Optional[VersionSyncIntegration] = None


def get_version_sync_integration() -> VersionSyncIntegration:
    """获取全局版本同步集成服务实例"""
    global version_sync_integration
    if version_sync_integration is None:
        version_sync_integration = VersionSyncIntegration()
        logger.info("版本同步集成服务已初始化")
    return version_sync_integration