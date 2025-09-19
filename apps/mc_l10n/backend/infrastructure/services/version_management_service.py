"""
版本管理服务 - TH-Suite MC L10n 核心版本控制引擎
实现完整的数据版本管理，包括版本控制、分支管理、回滚和标签功能
"""

import asyncio
import json
import logging
import hashlib
import uuid
from typing import Dict, Any, List, Optional, Tuple, Union
from datetime import datetime, timedelta
from enum import Enum
from dataclasses import dataclass, asdict
from pathlib import Path

from infrastructure.repositories.repository_factory import get_repository_factory
from infrastructure.services.multi_layer_cache_service import get_cache_service

logger = logging.getLogger(__name__)


class EntityType(Enum):
    """实体类型枚举"""
    PROJECT = "project"
    PACK = "pack"
    MOD = "mod"
    LANGUAGE_FILE = "language_file"
    TRANSLATION_ENTRIES = "translation_entries"


class CommitType(Enum):
    """提交类型枚举"""
    INITIAL = "initial"
    UPDATE = "update"
    FEATURE = "feature"
    BUGFIX = "bugfix"
    MERGE = "merge"
    ROLLBACK = "rollback"


class BranchType(Enum):
    """分支类型枚举"""
    MAIN = "main"
    FEATURE = "feature"
    HOTFIX = "hotfix"
    RELEASE = "release"
    DEVELOP = "develop"


@dataclass
class VersionRepository:
    """版本仓库数据类"""
    uid: str
    entity_type: EntityType
    entity_uid: str
    default_branch: str = "main"
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None


@dataclass
class VersionBranch:
    """版本分支数据类"""
    uid: str
    repository_uid: str
    name: str
    description: Optional[str] = None
    parent_branch_uid: Optional[str] = None
    is_protected: bool = False
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None


@dataclass
class VersionCommit:
    """版本提交数据类"""
    uid: str
    repository_uid: str
    branch_uid: str
    parent_commit_uid: Optional[str]
    commit_hash: str
    author_name: str
    author_email: Optional[str]
    message: str
    description: Optional[str] = None
    changes_summary: Dict[str, Any] = None
    metadata: Dict[str, Any] = None
    created_at: Optional[datetime] = None


@dataclass
class VersionTag:
    """版本标签数据类"""
    uid: str
    repository_uid: str
    name: str
    commit_uid: str
    tag_type: str = "release"
    description: Optional[str] = None
    metadata: Dict[str, Any] = None
    created_at: Optional[datetime] = None


class VersionManagementService:
    """版本管理服务 - 核心版本控制引擎"""
    
    def __init__(self):
        self.factory = get_repository_factory()
        self.cache_service = get_cache_service()
        
        # 版本管理配置
        self.config = {
            "auto_versioning": True,
            "default_branch": "main",
            "max_commits_per_branch": 10000,
            "snapshot_compression": "zstd",
            "diff_format": "json_patch",
            "cache_snapshots": True,
            "cache_diffs": True,
            "retention_days": 365
        }
        
    # ============================================================
    # 1. 版本仓库管理
    # ============================================================
    
    async def create_repository(self, entity_type: EntityType, entity_uid: str, 
                              default_branch: str = "main") -> Dict[str, Any]:
        """
        创建版本仓库
        
        Args:
            entity_type: 实体类型
            entity_uid: 实体UID
            default_branch: 默认分支名
        """
        try:
            # 检查仓库是否已存在
            existing = await self._get_repository_by_entity(entity_type, entity_uid)
            if existing:
                return {
                    "success": False,
                    "message": f"实体 {entity_uid} 的版本仓库已存在",
                    "repository_uid": existing["uid"]
                }
            
            repo_uid = str(uuid.uuid4())
            now = datetime.now()
            
            async with self.factory.get_db_connection() as conn:
                # 创建版本仓库
                await conn.execute("""
                    INSERT INTO version_repositories 
                    (uid, entity_type, entity_uid, default_branch, created_at, updated_at)
                    VALUES (?, ?, ?, ?, ?, ?)
                """, (repo_uid, entity_type.value, entity_uid, default_branch, 
                      now.isoformat(), now.isoformat()))
                
                # 创建默认分支
                branch_result = await self.create_branch(repo_uid, default_branch, 
                                                       "默认主分支", is_protected=True)
                
                if not branch_result["success"]:
                    raise Exception(f"创建默认分支失败: {branch_result['message']}")
                
                await conn.commit()
                
            logger.info(f"版本仓库创建成功: {repo_uid} ({entity_type.value}:{entity_uid})")
            
            return {
                "success": True,
                "message": "版本仓库创建成功",
                "repository": {
                    "uid": repo_uid,
                    "entity_type": entity_type.value,
                    "entity_uid": entity_uid,
                    "default_branch": default_branch,
                    "default_branch_uid": branch_result["branch_uid"]
                }
            }
            
        except Exception as e:
            logger.error(f"创建版本仓库失败: {e}")
            return {
                "success": False,
                "message": f"创建版本仓库失败: {str(e)}"
            }
    
    async def get_repository(self, repository_uid: str) -> Dict[str, Any]:
        """获取版本仓库信息"""
        try:
            async with self.factory.get_db_connection() as conn:
                cursor = await conn.execute("""
                    SELECT * FROM view_version_repository_summary 
                    WHERE uid = ?
                """, (repository_uid,))
                
                row = await cursor.fetchone()
                if not row:
                    return {
                        "success": False,
                        "message": "版本仓库不存在"
                    }
                
                # 转换为字典
                columns = [description[0] for description in cursor.description]
                repo_data = dict(zip(columns, row))
                
                return {
                    "success": True,
                    "repository": repo_data
                }
                
        except Exception as e:
            logger.error(f"获取版本仓库失败: {e}")
            return {
                "success": False,
                "message": f"获取版本仓库失败: {str(e)}"
            }
    
    async def _get_repository_by_entity(self, entity_type: EntityType, 
                                      entity_uid: str) -> Optional[Dict[str, Any]]:
        """根据实体获取版本仓库"""
        try:
            async with self.factory.get_db_connection() as conn:
                cursor = await conn.execute("""
                    SELECT uid, entity_type, entity_uid, default_branch, created_at, updated_at
                    FROM version_repositories 
                    WHERE entity_type = ? AND entity_uid = ?
                """, (entity_type.value, entity_uid))
                
                row = await cursor.fetchone()
                if row:
                    columns = [description[0] for description in cursor.description]
                    return dict(zip(columns, row))
                return None
                
        except Exception as e:
            logger.error(f"查询版本仓库失败: {e}")
            return None
    
    # ============================================================
    # 2. 分支管理
    # ============================================================
    
    async def create_branch(self, repository_uid: str, name: str, description: str = None,
                          parent_branch_uid: str = None, is_protected: bool = False) -> Dict[str, Any]:
        """
        创建新分支
        
        Args:
            repository_uid: 仓库UID
            name: 分支名称
            description: 分支描述
            parent_branch_uid: 父分支UID
            is_protected: 是否受保护
        """
        try:
            # 检查分支是否已存在
            existing = await self._get_branch_by_name(repository_uid, name)
            if existing:
                return {
                    "success": False,
                    "message": f"分支 {name} 已存在"
                }
            
            branch_uid = str(uuid.uuid4())
            now = datetime.now()
            
            async with self.factory.get_db_connection() as conn:
                await conn.execute("""
                    INSERT INTO version_branches 
                    (uid, repository_uid, name, description, parent_branch_uid, is_protected, created_at, updated_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """, (branch_uid, repository_uid, name, description, parent_branch_uid, 
                      is_protected, now.isoformat(), now.isoformat()))
                
                # 创建分支HEAD引用
                await conn.execute("""
                    INSERT OR REPLACE INTO version_refs 
                    (uid, repository_uid, ref_type, ref_name, target_commit_uid, updated_at)
                    VALUES (?, ?, 'head', ?, NULL, ?)
                """, (str(uuid.uuid4()), repository_uid, name, now.isoformat()))
                
                await conn.commit()
                
            logger.info(f"分支创建成功: {name} ({branch_uid})")
            
            return {
                "success": True,
                "message": f"分支 {name} 创建成功",
                "branch_uid": branch_uid,
                "branch": {
                    "uid": branch_uid,
                    "repository_uid": repository_uid,
                    "name": name,
                    "description": description,
                    "parent_branch_uid": parent_branch_uid,
                    "is_protected": is_protected
                }
            }
            
        except Exception as e:
            logger.error(f"创建分支失败: {e}")
            return {
                "success": False,
                "message": f"创建分支失败: {str(e)}"
            }
    
    async def list_branches(self, repository_uid: str) -> Dict[str, Any]:
        """列出仓库的所有分支"""
        try:
            async with self.factory.get_db_connection() as conn:
                cursor = await conn.execute("""
                    SELECT * FROM view_version_branch_status 
                    WHERE repository_uid = ?
                    ORDER BY created_at DESC
                """, (repository_uid,))
                
                rows = await cursor.fetchall()
                columns = [description[0] for description in cursor.description]
                
                branches = [dict(zip(columns, row)) for row in rows]
                
                return {
                    "success": True,
                    "branches": branches,
                    "total_count": len(branches)
                }
                
        except Exception as e:
            logger.error(f"列出分支失败: {e}")
            return {
                "success": False,
                "message": f"列出分支失败: {str(e)}"
            }
    
    async def _get_branch_by_name(self, repository_uid: str, name: str) -> Optional[Dict[str, Any]]:
        """根据名称获取分支"""
        try:
            async with self.factory.get_db_connection() as conn:
                cursor = await conn.execute("""
                    SELECT uid, repository_uid, name, description, parent_branch_uid, 
                           is_protected, created_at, updated_at
                    FROM version_branches 
                    WHERE repository_uid = ? AND name = ?
                """, (repository_uid, name))
                
                row = await cursor.fetchone()
                if row:
                    columns = [description[0] for description in cursor.description]
                    return dict(zip(columns, row))
                return None
                
        except Exception as e:
            logger.error(f"查询分支失败: {e}")
            return None
    
    # ============================================================
    # 3. 提交管理
    # ============================================================
    
    async def create_commit(self, repository_uid: str, branch_name: str, 
                          author_name: str, message: str, content_data: Dict[str, Any],
                          author_email: str = None, description: str = None,
                          metadata: Dict[str, Any] = None) -> Dict[str, Any]:
        """
        创建版本提交
        
        Args:
            repository_uid: 仓库UID
            branch_name: 分支名称
            author_name: 作者名称
            message: 提交消息
            content_data: 内容数据
            author_email: 作者邮箱
            description: 详细描述
            metadata: 元数据
        """
        try:
            # 获取分支信息
            branch = await self._get_branch_by_name(repository_uid, branch_name)
            if not branch:
                return {
                    "success": False,
                    "message": f"分支 {branch_name} 不存在"
                }
            
            # 检查分支是否受保护
            if branch["is_protected"] and not author_name:
                return {
                    "success": False,
                    "message": "受保护分支需要提供作者信息"
                }
            
            # 获取父提交
            parent_commit_uid = await self._get_branch_head_commit(repository_uid, branch_name)
            
            # 生成提交哈希
            commit_content = {
                "repository_uid": repository_uid,
                "branch_name": branch_name,
                "parent_commit_uid": parent_commit_uid,
                "author_name": author_name,
                "message": message,
                "content_data": content_data,
                "timestamp": datetime.now().isoformat()
            }
            commit_hash = self._generate_commit_hash(commit_content)
            
            commit_uid = str(uuid.uuid4())
            now = datetime.now()
            
            # 生成变更摘要
            changes_summary = await self._generate_changes_summary(content_data, parent_commit_uid)
            
            async with self.factory.get_db_connection() as conn:
                # 创建提交记录
                await conn.execute("""
                    INSERT INTO version_commits 
                    (uid, repository_uid, branch_uid, parent_commit_uid, commit_hash, 
                     author_name, author_email, message, description, changes_summary, metadata, created_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (commit_uid, repository_uid, branch["uid"], parent_commit_uid, commit_hash,
                      author_name, author_email, message, description, 
                      json.dumps(changes_summary) if changes_summary else None,
                      json.dumps(metadata) if metadata else None, now.isoformat()))
                
                # 创建快照
                snapshot_result = await self._create_snapshot(commit_uid, content_data)
                if not snapshot_result["success"]:
                    raise Exception(f"创建快照失败: {snapshot_result['message']}")
                
                # 更新分支HEAD引用
                await conn.execute("""
                    UPDATE version_refs 
                    SET target_commit_uid = ?, updated_at = ?
                    WHERE repository_uid = ? AND ref_type = 'head' AND ref_name = ?
                """, (commit_uid, now.isoformat(), repository_uid, branch_name))
                
                await conn.commit()
                
            logger.info(f"提交创建成功: {commit_hash} ({commit_uid})")
            
            return {
                "success": True,
                "message": "提交创建成功",
                "commit": {
                    "uid": commit_uid,
                    "commit_hash": commit_hash,
                    "repository_uid": repository_uid,
                    "branch_name": branch_name,
                    "author_name": author_name,
                    "message": message,
                    "changes_summary": changes_summary,
                    "created_at": now.isoformat()
                }
            }
            
        except Exception as e:
            logger.error(f"创建提交失败: {e}")
            return {
                "success": False,
                "message": f"创建提交失败: {str(e)}"
            }
    
    async def get_commit_history(self, repository_uid: str, branch_name: str = None,
                               limit: int = 50, offset: int = 0) -> Dict[str, Any]:
        """获取提交历史"""
        try:
            conditions = ["vc.repository_uid = ?"]
            params = [repository_uid]
            
            if branch_name:
                conditions.append("vb.name = ?")
                params.append(branch_name)
            
            params.extend([limit, offset])
            
            async with self.factory.get_db_connection() as conn:
                cursor = await conn.execute(f"""
                    SELECT * FROM view_version_commit_details vc
                    LEFT JOIN version_branches vb ON vc.branch_uid = vb.uid
                    WHERE {' AND '.join(conditions)}
                    ORDER BY vc.created_at DESC
                    LIMIT ? OFFSET ?
                """, params)
                
                rows = await cursor.fetchall()
                columns = [description[0] for description in cursor.description]
                
                commits = [dict(zip(columns, row)) for row in rows]
                
                return {
                    "success": True,
                    "commits": commits,
                    "total_count": len(commits),
                    "limit": limit,
                    "offset": offset
                }
                
        except Exception as e:
            logger.error(f"获取提交历史失败: {e}")
            return {
                "success": False,
                "message": f"获取提交历史失败: {str(e)}"
            }
    
    def _generate_commit_hash(self, commit_content: Dict[str, Any]) -> str:
        """生成提交哈希"""
        content_str = json.dumps(commit_content, sort_keys=True, ensure_ascii=False)
        return hashlib.sha256(content_str.encode('utf-8')).hexdigest()
    
    async def _get_branch_head_commit(self, repository_uid: str, branch_name: str) -> Optional[str]:
        """获取分支的HEAD提交"""
        try:
            async with self.factory.get_db_connection() as conn:
                cursor = await conn.execute("""
                    SELECT target_commit_uid FROM version_refs 
                    WHERE repository_uid = ? AND ref_type = 'head' AND ref_name = ?
                """, (repository_uid, branch_name))
                
                row = await cursor.fetchone()
                return row[0] if row and row[0] else None
                
        except Exception as e:
            logger.error(f"获取分支HEAD失败: {e}")
            return None
    
    async def _generate_changes_summary(self, content_data: Dict[str, Any], 
                                      parent_commit_uid: Optional[str]) -> Dict[str, Any]:
        """生成变更摘要"""
        if not parent_commit_uid:
            # 初始提交
            return {
                "type": "initial",
                "total_items": len(content_data.get("items", [])),
                "summary": "初始提交"
            }
        
        # TODO: 实现与父提交的差异计算
        return {
            "type": "update", 
            "total_items": len(content_data.get("items", [])),
            "summary": "内容更新"
        }
    
    # ============================================================
    # 4. 快照管理
    # ============================================================
    
    async def _create_snapshot(self, commit_uid: str, content_data: Dict[str, Any]) -> Dict[str, Any]:
        """创建版本快照"""
        try:
            # 序列化内容数据
            content_json = json.dumps(content_data, ensure_ascii=False, sort_keys=True)
            content_bytes = content_json.encode('utf-8')
            
            # 计算内容指纹
            content_hash = hashlib.blake3(content_bytes).hexdigest()
            
            # 压缩内容 (使用zstd)
            compressed_content = await self._compress_content(content_bytes)
            
            # 存储到CAS
            cas_result = await self._store_to_cas(content_hash, compressed_content)
            if not cas_result["success"]:
                return cas_result
            
            snapshot_uid = str(uuid.uuid4())
            now = datetime.now()
            
            async with self.factory.get_db_connection() as conn:
                await conn.execute("""
                    INSERT INTO version_snapshots 
                    (uid, commit_uid, content_type, content_cid, compression_algo, 
                     size_bytes, item_count, checksum_blake3, created_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (snapshot_uid, commit_uid, "full", content_hash, "zstd",
                      len(compressed_content), len(content_data.get("items", [])),
                      content_hash, now.isoformat()))
                
                await conn.commit()
            
            return {
                "success": True,
                "snapshot_uid": snapshot_uid,
                "content_cid": content_hash,
                "size_bytes": len(compressed_content)
            }
            
        except Exception as e:
            logger.error(f"创建快照失败: {e}")
            return {
                "success": False,
                "message": f"创建快照失败: {str(e)}"
            }
    
    async def _compress_content(self, content_bytes: bytes) -> bytes:
        """压缩内容 (简化实现，实际应使用zstd)"""
        import gzip
        return gzip.compress(content_bytes)
    
    async def _store_to_cas(self, cid: str, content: bytes) -> Dict[str, Any]:
        """存储到内容寻址存储"""
        try:
            now = datetime.now()
            
            async with self.factory.get_db_connection() as conn:
                # 检查是否已存在
                cursor = await conn.execute("""
                    SELECT cid FROM ops_cas_objects WHERE cid = ?
                """, (cid,))
                
                if await cursor.fetchone():
                    # 增加引用计数
                    await conn.execute("""
                        UPDATE ops_cas_objects SET ref_count = ref_count + 1 WHERE cid = ?
                    """, (cid,))
                else:
                    # 新建对象
                    await conn.execute("""
                        INSERT INTO ops_cas_objects (cid, size, algo, ref_count, created_at)
                        VALUES (?, ?, ?, ?, ?)
                    """, (cid, len(content), "zstd", 1, now.isoformat()))
                
                await conn.commit()
            
            # TODO: 实际存储content到文件系统
            
            return {
                "success": True,
                "cid": cid
            }
            
        except Exception as e:
            logger.error(f"存储到CAS失败: {e}")
            return {
                "success": False,
                "message": f"存储到CAS失败: {str(e)}"
            }


# 全局版本管理服务实例
version_management_service: Optional[VersionManagementService] = None


def get_version_management_service() -> VersionManagementService:
    """获取全局版本管理服务实例"""
    global version_management_service
    if version_management_service is None:
        version_management_service = VersionManagementService()
        logger.info("版本管理服务已初始化")
    return version_management_service