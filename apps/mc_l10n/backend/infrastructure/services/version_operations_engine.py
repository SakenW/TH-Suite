"""
版本操作引擎 - TH-Suite MC L10n
实现版本回滚、分支合并、标签管理等高级版本操作
"""

import asyncio
import json
import logging
import uuid
from typing import Dict, Any, List, Optional, Union
from datetime import datetime, timedelta
from enum import Enum

from infrastructure.repositories.repository_factory import get_repository_factory
from infrastructure.services.version_management_service import (
    get_version_management_service, EntityType, VersionCommit, VersionTag
)
from infrastructure.services.version_diff_engine import VersionDiffEngine, DiffType

logger = logging.getLogger(__name__)


class RollbackStrategy(Enum):
    """回滚策略枚举"""
    REVERT = "revert"        # 创建回滚提交
    RESET_SOFT = "reset_soft"    # 软重置（保留工作区）
    RESET_HARD = "reset_hard"    # 硬重置（丢弃所有更改）
    CHERRY_PICK = "cherry_pick"  # 挑选特定提交


class MergeStrategy(Enum):
    """合并策略枚举"""
    FAST_FORWARD = "fast_forward"  # 快进合并
    THREE_WAY = "three_way"        # 三路合并
    OURS = "ours"                  # 使用我们的版本
    THEIRS = "theirs"              # 使用他们的版本
    MANUAL = "manual"              # 手动解决冲突


class ConflictResolution(Enum):
    """冲突解决策略"""
    MANUAL = "manual"
    AUTO_OURS = "auto_ours"
    AUTO_THEIRS = "auto_theirs"
    AUTO_MERGE = "auto_merge"


class VersionOperationsEngine:
    """版本操作引擎"""
    
    def __init__(self):
        self.factory = get_repository_factory()
        self.version_service = get_version_management_service()
        self.diff_engine = VersionDiffEngine()
        
        self.config = {
            "max_rollback_commits": 1000,
            "auto_conflict_resolution": True,
            "backup_before_operations": True,
            "operation_timeout": 300,  # 5分钟
            "async_operations": True
        }
    
    # ============================================================
    # 1. 版本回滚操作
    # ============================================================
    
    async def rollback_to_commit(self, repository_uid: str, target_commit_uid: str,
                                strategy: RollbackStrategy = RollbackStrategy.REVERT,
                                author_name: str = "System", 
                                message: str = None) -> Dict[str, Any]:
        """
        回滚到指定提交
        
        Args:
            repository_uid: 仓库UID
            target_commit_uid: 目标提交UID
            strategy: 回滚策略
            author_name: 操作者
            message: 回滚消息
        """
        try:
            # 记录操作开始
            operation_uid = str(uuid.uuid4())
            await self._log_operation_start(operation_uid, repository_uid, "rollback", {
                "target_commit_uid": target_commit_uid,
                "strategy": strategy.value,
                "author_name": author_name
            })
            
            # 获取当前HEAD提交
            current_commit = await self._get_current_head_commit(repository_uid)
            if not current_commit:
                return {
                    "success": False,
                    "message": "无法获取当前HEAD提交"
                }
            
            # 获取目标提交
            target_commit = await self._get_commit_by_uid(target_commit_uid)
            if not target_commit:
                return {
                    "success": False,
                    "message": "目标提交不存在"
                }
            
            # 验证回滚路径
            rollback_path = await self._validate_rollback_path(
                current_commit["uid"], target_commit_uid
            )
            if not rollback_path["valid"]:
                return {
                    "success": False,
                    "message": f"无效的回滚路径: {rollback_path['reason']}"
                }
            
            # 执行回滚操作
            if strategy == RollbackStrategy.REVERT:
                result = await self._execute_revert_rollback(
                    repository_uid, current_commit, target_commit, author_name, message
                )
            elif strategy == RollbackStrategy.RESET_SOFT:
                result = await self._execute_soft_reset(
                    repository_uid, target_commit_uid, author_name
                )
            elif strategy == RollbackStrategy.RESET_HARD:
                result = await self._execute_hard_reset(
                    repository_uid, target_commit_uid, author_name
                )
            else:
                result = {
                    "success": False,
                    "message": f"不支持的回滚策略: {strategy.value}"
                }
            
            # 记录操作完成
            await self._log_operation_complete(operation_uid, result["success"], result)
            
            return result
            
        except Exception as e:
            logger.error(f"回滚操作失败: {e}")
            await self._log_operation_complete(operation_uid, False, {"error": str(e)})
            return {
                "success": False,
                "message": f"回滚操作失败: {str(e)}"
            }
    
    async def _execute_revert_rollback(self, repository_uid: str, current_commit: Dict,
                                     target_commit: Dict, author_name: str, 
                                     message: str = None) -> Dict[str, Any]:
        """执行回滚提交"""
        
        # 获取提交内容
        current_content = await self._get_commit_content(current_commit["uid"])
        target_content = await self._get_commit_content(target_commit["uid"])
        
        if not current_content["success"] or not target_content["success"]:
            return {
                "success": False,
                "message": "无法获取提交内容"
            }
        
        # 生成回滚消息
        if not message:
            message = f"回滚到提交 {target_commit['commit_hash'][:8]}: {target_commit['message']}"
        
        # 创建回滚提交
        rollback_result = await self.version_service.create_commit(
            repository_uid=repository_uid,
            branch_name="main",  # TODO: 获取当前分支
            author_name=author_name,
            message=message,
            content_data=target_content["content"],
            description=f"回滚操作: {current_commit['commit_hash'][:8]} -> {target_commit['commit_hash'][:8]}",
            metadata={
                "operation_type": "rollback",
                "rollback_from": current_commit["uid"],
                "rollback_to": target_commit["uid"],
                "strategy": "revert"
            }
        )
        
        if rollback_result["success"]:
            return {
                "success": True,
                "message": "回滚提交创建成功",
                "rollback_commit_uid": rollback_result["commit"]["uid"],
                "rollback_commit_hash": rollback_result["commit"]["commit_hash"]
            }
        else:
            return rollback_result
    
    async def _execute_soft_reset(self, repository_uid: str, target_commit_uid: str,
                                author_name: str) -> Dict[str, Any]:
        """执行软重置"""
        
        try:
            # 更新HEAD引用
            async with self.factory.get_db_connection() as conn:
                await conn.execute("""
                    UPDATE version_refs 
                    SET target_commit_uid = ?, updated_at = ?
                    WHERE repository_uid = ? AND ref_type = 'head'
                """, (target_commit_uid, datetime.now().isoformat(), repository_uid))
                
                await conn.commit()
            
            return {
                "success": True,
                "message": "软重置完成",
                "target_commit_uid": target_commit_uid
            }
            
        except Exception as e:
            logger.error(f"软重置失败: {e}")
            return {
                "success": False,
                "message": f"软重置失败: {str(e)}"
            }
    
    async def _execute_hard_reset(self, repository_uid: str, target_commit_uid: str,
                                author_name: str) -> Dict[str, Any]:
        """执行硬重置"""
        
        try:
            # 获取目标提交内容
            target_content = await self._get_commit_content(target_commit_uid)
            if not target_content["success"]:
                return target_content
            
            # 更新所有相关的数据表
            await self._update_entity_data(repository_uid, target_content["content"])
            
            # 更新HEAD引用
            async with self.factory.get_db_connection() as conn:
                await conn.execute("""
                    UPDATE version_refs 
                    SET target_commit_uid = ?, updated_at = ?
                    WHERE repository_uid = ? AND ref_type = 'head'
                """, (target_commit_uid, datetime.now().isoformat(), repository_uid))
                
                await conn.commit()
            
            return {
                "success": True,
                "message": "硬重置完成",
                "target_commit_uid": target_commit_uid
            }
            
        except Exception as e:
            logger.error(f"硬重置失败: {e}")
            return {
                "success": False,
                "message": f"硬重置失败: {str(e)}"
            }
    
    # ============================================================
    # 2. 分支合并操作
    # ============================================================
    
    async def merge_branches(self, repository_uid: str, source_branch: str, 
                           target_branch: str, strategy: MergeStrategy = MergeStrategy.THREE_WAY,
                           author_name: str = "System", message: str = None) -> Dict[str, Any]:
        """
        合并分支
        
        Args:
            repository_uid: 仓库UID
            source_branch: 源分支名
            target_branch: 目标分支名
            strategy: 合并策略
            author_name: 操作者
            message: 合并消息
        """
        try:
            # 记录合并开始
            merge_uid = str(uuid.uuid4())
            
            # 获取分支信息
            source_branch_info = await self.version_service._get_branch_by_name(
                repository_uid, source_branch
            )
            target_branch_info = await self.version_service._get_branch_by_name(
                repository_uid, target_branch
            )
            
            if not source_branch_info or not target_branch_info:
                return {
                    "success": False,
                    "message": "源分支或目标分支不存在"
                }
            
            # 获取分支HEAD提交
            source_commit_uid = await self.version_service._get_branch_head_commit(
                repository_uid, source_branch
            )
            target_commit_uid = await self.version_service._get_branch_head_commit(
                repository_uid, target_branch
            )
            
            if not source_commit_uid or not target_commit_uid:
                return {
                    "success": False,
                    "message": "无法获取分支HEAD提交"
                }
            
            # 查找共同祖先
            base_commit_uid = await self._find_common_ancestor(source_commit_uid, target_commit_uid)
            
            # 创建合并记录
            await self._create_merge_record(merge_uid, repository_uid, base_commit_uid,
                                          source_commit_uid, target_commit_uid, strategy)
            
            # 执行合并策略
            if strategy == MergeStrategy.FAST_FORWARD:
                result = await self._execute_fast_forward_merge(
                    repository_uid, source_commit_uid, target_branch, author_name
                )
            elif strategy == MergeStrategy.THREE_WAY:
                result = await self._execute_three_way_merge(
                    repository_uid, merge_uid, base_commit_uid, source_commit_uid,
                    target_commit_uid, target_branch, author_name, message
                )
            elif strategy == MergeStrategy.OURS:
                result = await self._execute_ours_merge(
                    repository_uid, target_commit_uid, target_branch, author_name, message
                )
            elif strategy == MergeStrategy.THEIRS:
                result = await self._execute_theirs_merge(
                    repository_uid, source_commit_uid, target_branch, author_name, message
                )
            else:
                result = {
                    "success": False,
                    "message": f"不支持的合并策略: {strategy.value}"
                }
            
            # 更新合并记录
            await self._update_merge_record(merge_uid, result)
            
            return result
            
        except Exception as e:
            logger.error(f"分支合并失败: {e}")
            return {
                "success": False,
                "message": f"分支合并失败: {str(e)}"
            }
    
    async def _execute_three_way_merge(self, repository_uid: str, merge_uid: str,
                                     base_commit_uid: str, source_commit_uid: str,
                                     target_commit_uid: str, target_branch: str,
                                     author_name: str, message: str) -> Dict[str, Any]:
        """执行三路合并"""
        
        # 获取三个版本的内容
        base_content = await self._get_commit_content(base_commit_uid)
        source_content = await self._get_commit_content(source_commit_uid)
        target_content = await self._get_commit_content(target_commit_uid)
        
        if not all([base_content["success"], source_content["success"], target_content["success"]]):
            return {
                "success": False,
                "message": "无法获取合并所需的提交内容"
            }
        
        # 检测冲突
        conflicts = await self._detect_merge_conflicts(
            base_content["content"], source_content["content"], target_content["content"]
        )
        
        if conflicts:
            # 有冲突，需要手动解决
            await self._record_merge_conflicts(merge_uid, conflicts)
            return {
                "success": False,
                "message": "合并存在冲突，需要手动解决",
                "merge_uid": merge_uid,
                "conflicts": conflicts,
                "conflicts_count": len(conflicts)
            }
        
        # 自动合并
        merged_content = await self._auto_merge_content(
            base_content["content"], source_content["content"], target_content["content"]
        )
        
        # 生成合并消息
        if not message:
            source_commit = await self._get_commit_by_uid(source_commit_uid)
            message = f"合并分支到 {target_branch}: {source_commit['message']}"
        
        # 创建合并提交
        merge_commit_result = await self.version_service.create_commit(
            repository_uid=repository_uid,
            branch_name=target_branch,
            author_name=author_name,
            message=message,
            content_data=merged_content,
            description=f"三路合并: {base_commit_uid[:8]} + {source_commit_uid[:8]} -> {target_commit_uid[:8]}",
            metadata={
                "operation_type": "merge",
                "merge_uid": merge_uid,
                "merge_strategy": "three_way",
                "parent_commits": [source_commit_uid, target_commit_uid]
            }
        )
        
        if merge_commit_result["success"]:
            return {
                "success": True,
                "message": "三路合并完成",
                "merge_commit_uid": merge_commit_result["commit"]["uid"],
                "merge_commit_hash": merge_commit_result["commit"]["commit_hash"]
            }
        else:
            return merge_commit_result
    
    # ============================================================
    # 3. 标签管理
    # ============================================================
    
    async def create_tag(self, repository_uid: str, tag_name: str, commit_uid: str,
                        tag_type: str = "release", description: str = None,
                        metadata: Dict[str, Any] = None) -> Dict[str, Any]:
        """
        创建版本标签
        
        Args:
            repository_uid: 仓库UID
            tag_name: 标签名称
            commit_uid: 提交UID
            tag_type: 标签类型
            description: 标签描述
            metadata: 元数据
        """
        try:
            # 检查标签是否已存在
            existing_tag = await self._get_tag_by_name(repository_uid, tag_name)
            if existing_tag:
                return {
                    "success": False,
                    "message": f"标签 {tag_name} 已存在"
                }
            
            # 验证提交存在
            commit = await self._get_commit_by_uid(commit_uid)
            if not commit:
                return {
                    "success": False,
                    "message": "指定的提交不存在"
                }
            
            tag_uid = str(uuid.uuid4())
            now = datetime.now()
            
            async with self.factory.get_db_connection() as conn:
                await conn.execute("""
                    INSERT INTO version_tags 
                    (uid, repository_uid, name, commit_uid, tag_type, description, metadata, created_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """, (tag_uid, repository_uid, tag_name, commit_uid, tag_type,
                      description, json.dumps(metadata) if metadata else None, now.isoformat()))
                
                # 创建标签引用
                await conn.execute("""
                    INSERT INTO version_refs 
                    (uid, repository_uid, ref_type, ref_name, target_commit_uid, updated_at)
                    VALUES (?, ?, 'tag', ?, ?, ?)
                """, (str(uuid.uuid4()), repository_uid, tag_name, commit_uid, now.isoformat()))
                
                await conn.commit()
            
            logger.info(f"标签创建成功: {tag_name} ({tag_uid})")
            
            return {
                "success": True,
                "message": f"标签 {tag_name} 创建成功",
                "tag": {
                    "uid": tag_uid,
                    "name": tag_name,
                    "commit_uid": commit_uid,
                    "tag_type": tag_type,
                    "description": description,
                    "created_at": now.isoformat()
                }
            }
            
        except Exception as e:
            logger.error(f"创建标签失败: {e}")
            return {
                "success": False,
                "message": f"创建标签失败: {str(e)}"
            }
    
    async def list_tags(self, repository_uid: str, tag_type: str = None) -> Dict[str, Any]:
        """列出标签"""
        try:
            conditions = ["repository_uid = ?"]
            params = [repository_uid]
            
            if tag_type:
                conditions.append("tag_type = ?")
                params.append(tag_type)
            
            async with self.factory.get_db_connection() as conn:
                cursor = await conn.execute(f"""
                    SELECT vt.*, vc.commit_hash, vc.message as commit_message, vc.author_name
                    FROM version_tags vt
                    LEFT JOIN version_commits vc ON vt.commit_uid = vc.uid
                    WHERE {' AND '.join(conditions)}
                    ORDER BY vt.created_at DESC
                """, params)
                
                rows = await cursor.fetchall()
                columns = [description[0] for description in cursor.description]
                
                tags = [dict(zip(columns, row)) for row in rows]
                
                return {
                    "success": True,
                    "tags": tags,
                    "total_count": len(tags)
                }
                
        except Exception as e:
            logger.error(f"列出标签失败: {e}")
            return {
                "success": False,
                "message": f"列出标签失败: {str(e)}"
            }
    
    # ============================================================
    # 4. 辅助方法
    # ============================================================
    
    async def _get_current_head_commit(self, repository_uid: str) -> Optional[Dict[str, Any]]:
        """获取当前HEAD提交"""
        try:
            async with self.factory.get_db_connection() as conn:
                cursor = await conn.execute("""
                    SELECT vc.* FROM version_commits vc
                    INNER JOIN version_refs vr ON vc.uid = vr.target_commit_uid
                    WHERE vr.repository_uid = ? AND vr.ref_type = 'head'
                    LIMIT 1
                """, (repository_uid,))
                
                row = await cursor.fetchone()
                if row:
                    columns = [description[0] for description in cursor.description]
                    return dict(zip(columns, row))
                return None
                
        except Exception as e:
            logger.error(f"获取HEAD提交失败: {e}")
            return None
    
    async def _get_commit_by_uid(self, commit_uid: str) -> Optional[Dict[str, Any]]:
        """根据UID获取提交"""
        try:
            async with self.factory.get_db_connection() as conn:
                cursor = await conn.execute("""
                    SELECT * FROM version_commits WHERE uid = ?
                """, (commit_uid,))
                
                row = await cursor.fetchone()
                if row:
                    columns = [description[0] for description in cursor.description]
                    return dict(zip(columns, row))
                return None
                
        except Exception as e:
            logger.error(f"获取提交失败: {e}")
            return None
    
    async def _get_commit_content(self, commit_uid: str) -> Dict[str, Any]:
        """获取提交内容"""
        try:
            async with self.factory.get_db_connection() as conn:
                cursor = await conn.execute("""
                    SELECT vs.content_cid FROM version_snapshots vs
                    WHERE vs.commit_uid = ? AND vs.content_type = 'full'
                    LIMIT 1
                """, (commit_uid,))
                
                row = await cursor.fetchone()
                if not row:
                    return {
                        "success": False,
                        "message": "未找到提交快照"
                    }
                
                content_cid = row[0]
                
                # TODO: 从CAS读取实际内容
                # 这里简化实现，返回模拟数据
                mock_content = {
                    "items": [],
                    "metadata": {"cid": content_cid}
                }
                
                return {
                    "success": True,
                    "content": mock_content
                }
                
        except Exception as e:
            logger.error(f"获取提交内容失败: {e}")
            return {
                "success": False,
                "message": f"获取提交内容失败: {str(e)}"
            }
    
    async def _validate_rollback_path(self, current_commit_uid: str, 
                                    target_commit_uid: str) -> Dict[str, Any]:
        """验证回滚路径是否有效"""
        
        # 检查目标提交是否在当前提交的历史中
        commit_path = await self._get_commit_path(current_commit_uid, target_commit_uid)
        
        if not commit_path:
            return {
                "valid": False,
                "reason": "目标提交不在当前提交的历史路径中"
            }
        
        if len(commit_path) > self.config["max_rollback_commits"]:
            return {
                "valid": False,
                "reason": f"回滚路径过长，超过限制 {self.config['max_rollback_commits']}"
            }
        
        return {
            "valid": True,
            "path": commit_path
        }
    
    async def _get_commit_path(self, from_commit_uid: str, 
                             to_commit_uid: str) -> Optional[List[str]]:
        """获取两个提交之间的路径"""
        
        # 使用广度优先搜索找到路径
        visited = set()
        queue = [(from_commit_uid, [from_commit_uid])]
        
        while queue:
            current_uid, path = queue.pop(0)
            
            if current_uid == to_commit_uid:
                return path
            
            if current_uid in visited:
                continue
            
            visited.add(current_uid)
            
            # 获取父提交
            parent_commits = await self._get_parent_commits(current_uid)
            for parent_uid in parent_commits:
                if parent_uid not in visited:
                    queue.append((parent_uid, path + [parent_uid]))
        
        return None
    
    async def _get_parent_commits(self, commit_uid: str) -> List[str]:
        """获取提交的父提交"""
        try:
            async with self.factory.get_db_connection() as conn:
                cursor = await conn.execute("""
                    SELECT parent_commit_uid FROM version_commits 
                    WHERE uid = ? AND parent_commit_uid IS NOT NULL
                """, (commit_uid,))
                
                rows = await cursor.fetchall()
                return [row[0] for row in rows]
                
        except Exception as e:
            logger.error(f"获取父提交失败: {e}")
            return []
    
    async def _log_operation_start(self, operation_uid: str, repository_uid: str,
                                 operation_type: str, operation_data: Dict[str, Any]) -> None:
        """记录操作开始"""
        try:
            now = datetime.now()
            
            async with self.factory.get_db_connection() as conn:
                await conn.execute("""
                    INSERT INTO version_operations_log 
                    (uid, repository_uid, operation_type, operation_data, status, created_at)
                    VALUES (?, ?, ?, ?, 'pending', ?)
                """, (operation_uid, repository_uid, operation_type,
                      json.dumps(operation_data), now.isoformat()))
                
                await conn.commit()
                
        except Exception as e:
            logger.error(f"记录操作开始失败: {e}")
    
    async def _log_operation_complete(self, operation_uid: str, success: bool, 
                                    result_data: Dict[str, Any]) -> None:
        """记录操作完成"""
        try:
            now = datetime.now()
            status = "success" if success else "failed"
            
            async with self.factory.get_db_connection() as conn:
                await conn.execute("""
                    UPDATE version_operations_log 
                    SET status = ?, operation_data = ?, completed_at = ?
                    WHERE uid = ?
                """, (status, json.dumps(result_data), now.isoformat(), operation_uid))
                
                await conn.commit()
                
        except Exception as e:
            logger.error(f"记录操作完成失败: {e}")
    
    async def _get_tag_by_name(self, repository_uid: str, tag_name: str) -> Optional[Dict[str, Any]]:
        """根据名称获取标签"""
        try:
            async with self.factory.get_db_connection() as conn:
                cursor = await conn.execute("""
                    SELECT * FROM version_tags 
                    WHERE repository_uid = ? AND name = ?
                """, (repository_uid, tag_name))
                
                row = await cursor.fetchone()
                if row:
                    columns = [description[0] for description in cursor.description]
                    return dict(zip(columns, row))
                return None
                
        except Exception as e:
            logger.error(f"获取标签失败: {e}")
            return None


# 全局版本操作引擎实例
version_operations_engine: Optional[VersionOperationsEngine] = None


def get_version_operations_engine() -> VersionOperationsEngine:
    """获取全局版本操作引擎实例"""
    global version_operations_engine
    if version_operations_engine is None:
        version_operations_engine = VersionOperationsEngine()
        logger.info("版本操作引擎已初始化")
    return version_operations_engine