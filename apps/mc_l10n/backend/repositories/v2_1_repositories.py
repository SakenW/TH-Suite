"""
TH-Suite v2.1 数据访问层 (Repository Pattern)
基于优化数据库架构的仓库模式实现

特性:
- 数据分层支持 (本地 vs 同步)
- 强大的查询能力
- 事务支持
- 缓存集成
"""

import json
import sqlite3
from abc import ABC, abstractmethod
from contextlib import asynccontextmanager
from datetime import datetime
from typing import Any, Dict, List, Optional, AsyncGenerator, Tuple

import structlog

from ..models.v2_1_models import (
    Pack, PackVersion, ModVersionInstance, PackModRelation,
    ContentInstance, PackContentRelation, PackVersionStats,
    CrossVersionTrackingResult, ModDistributionResult, ContentChangeResult,
    ModelFactory
)
from ..models.data_layer_config import DataLayerQueryHelper

logger = structlog.get_logger(__name__)


# ============================================================
# 基础仓库接口
# ============================================================

class BaseRepository(ABC):
    """基础仓库接口"""
    
    def __init__(self, db_path: str):
        self.db_path = db_path
        self._conn: Optional[sqlite3.Connection] = None
    
    @asynccontextmanager
    async def get_connection(self) -> AsyncGenerator[sqlite3.Connection, None]:
        """获取数据库连接"""
        if self._conn is None:
            self._conn = sqlite3.connect(self.db_path)
            self._conn.row_factory = sqlite3.Row
            self._conn.execute("PRAGMA foreign_keys = ON")
        
        try:
            yield self._conn
        except Exception as e:
            self._conn.rollback()
            logger.error(f"数据库操作失败: {e}")
            raise
        finally:
            if self._conn:
                self._conn.commit()
    
    async def close(self):
        """关闭连接"""
        if self._conn:
            self._conn.close()
            self._conn = None


# ============================================================
# Pack 仓库
# ============================================================

class PackRepository(BaseRepository):
    """整合包仓库"""
    
    async def create(self, pack: Pack) -> int:
        """创建整合包"""
        async with self.get_connection() as conn:
            data = pack.to_dict()
            data.pop('id', None)  # 移除ID，让数据库自动生成
            
            # 处理枚举值
            if 'project_type' in data:
                data['project_type'] = pack.project_type.value
            if 'game_type' in data:
                data['game_type'] = pack.game_type.value
            
            # 处理JSON字段
            if 'sync_config' in data:
                data['sync_config'] = json.dumps(pack.sync_config)
            if 'build_config' in data:
                data['build_config'] = json.dumps(pack.build_config)
            
            fields = list(data.keys())
            placeholders = ', '.join(['?' for _ in fields])
            values = list(data.values())
            
            cursor = conn.execute(f"""
                INSERT INTO packs ({', '.join(fields)})
                VALUES ({placeholders})
            """, values)
            
            pack_id = cursor.lastrowid
            logger.info(f"创建整合包: {pack.name} (ID: {pack_id})")
            return pack_id
    
    async def get_by_id(self, pack_id: int) -> Optional[Pack]:
        """根据ID获取整合包"""
        async with self.get_connection() as conn:
            cursor = conn.execute(
                "SELECT * FROM packs WHERE id = ? AND is_active = 1",
                (pack_id,)
            )
            row = cursor.fetchone()
            
            if not row:
                return None
            
            return ModelFactory.create_model('packs', dict(row))
    
    async def get_by_path(self, path: str) -> Optional[Pack]:
        """根据路径获取整合包"""
        async with self.get_connection() as conn:
            cursor = conn.execute(
                "SELECT * FROM packs WHERE path = ? AND is_active = 1",
                (path,)
            )
            row = cursor.fetchone()
            
            if not row:
                return None
            
            return ModelFactory.create_model('packs', dict(row))
    
    async def list_all(self, limit: int = 100, offset: int = 0) -> List[Pack]:
        """列出所有活跃的整合包"""
        async with self.get_connection() as conn:
            cursor = conn.execute("""
                SELECT * FROM packs 
                WHERE is_active = 1 
                ORDER BY updated_at DESC 
                LIMIT ? OFFSET ?
            """, (limit, offset))
            
            rows = cursor.fetchall()
            return [ModelFactory.create_model('packs', dict(row)) for row in rows]
    
    async def update(self, pack_id: int, updates: Dict[str, Any]) -> bool:
        """更新整合包"""
        if not updates:
            return False
        
        # 处理特殊字段
        processed_updates = updates.copy()
        for key, value in processed_updates.items():
            if key in ['sync_config', 'build_config'] and isinstance(value, dict):
                processed_updates[key] = json.dumps(value)
        
        set_clause = ', '.join([f"{key} = ?" for key in processed_updates.keys()])
        values = list(processed_updates.values()) + [pack_id]
        
        async with self.get_connection() as conn:
            cursor = conn.execute(f"""
                UPDATE packs SET {set_clause}, updated_at = CURRENT_TIMESTAMP
                WHERE id = ?
            """, values)
            
            return cursor.rowcount > 0
    
    async def soft_delete(self, pack_id: int) -> bool:
        """软删除整合包"""
        async with self.get_connection() as conn:
            cursor = conn.execute(
                "UPDATE packs SET is_active = 0, updated_at = CURRENT_TIMESTAMP WHERE id = ?",
                (pack_id,)
            )
            return cursor.rowcount > 0
    
    async def get_sync_data(self, pack_id: int) -> Optional[Dict[str, Any]]:
        """获取需要同步的数据"""
        pack = await self.get_by_id(pack_id)
        if not pack:
            return None
        
        return pack.get_sync_data('packs')


# ============================================================
# PackVersion 仓库
# ============================================================

class PackVersionRepository(BaseRepository):
    """整合包版本仓库"""
    
    async def create(self, version: PackVersion) -> int:
        """创建版本"""
        async with self.get_connection() as conn:
            data = version.to_dict()
            data.pop('id', None)
            
            # 处理枚举值
            if 'loader_type' in data:
                data['loader_type'] = version.loader_type.value
            
            fields = list(data.keys())
            placeholders = ', '.join(['?' for _ in fields])
            values = list(data.values())
            
            cursor = conn.execute(f"""
                INSERT INTO pack_versions ({', '.join(fields)})
                VALUES ({placeholders})
            """, values)
            
            version_id = cursor.lastrowid
            logger.info(f"创建版本: {version.version_tag} (ID: {version_id})")
            return version_id
    
    async def get_by_pack_and_tag(self, pack_id: int, version_tag: str) -> Optional[PackVersion]:
        """根据包ID和版本标签获取版本"""
        async with self.get_connection() as conn:
            cursor = conn.execute("""
                SELECT * FROM pack_versions 
                WHERE pack_id = ? AND version_tag = ?
            """, (pack_id, version_tag))
            
            row = cursor.fetchone()
            if not row:
                return None
            
            return ModelFactory.create_model('pack_versions', dict(row))
    
    async def get_default_version(self, pack_id: int) -> Optional[PackVersion]:
        """获取默认版本"""
        async with self.get_connection() as conn:
            cursor = conn.execute("""
                SELECT * FROM pack_versions 
                WHERE pack_id = ? AND is_default = 1
                ORDER BY created_at DESC LIMIT 1
            """, (pack_id,))
            
            row = cursor.fetchone()
            if not row:
                return None
            
            return ModelFactory.create_model('pack_versions', dict(row))
    
    async def list_by_pack(self, pack_id: int) -> List[PackVersion]:
        """列出包的所有版本"""
        async with self.get_connection() as conn:
            cursor = conn.execute("""
                SELECT * FROM pack_versions 
                WHERE pack_id = ?
                ORDER BY is_default DESC, created_at DESC
            """, (pack_id,))
            
            rows = cursor.fetchall()
            return [ModelFactory.create_model('pack_versions', dict(row)) for row in rows]
    
    async def set_default_version(self, pack_id: int, version_id: int) -> bool:
        """设置默认版本"""
        async with self.get_connection() as conn:
            # 先清除其他默认版本
            conn.execute("""
                UPDATE pack_versions 
                SET is_default = 0, updated_at = CURRENT_TIMESTAMP
                WHERE pack_id = ? AND id != ?
            """, (pack_id, version_id))
            
            # 设置新的默认版本
            cursor = conn.execute("""
                UPDATE pack_versions 
                SET is_default = 1, updated_at = CURRENT_TIMESTAMP
                WHERE id = ?
            """, (version_id,))
            
            return cursor.rowcount > 0


# ============================================================
# ContentInstance 仓库
# ============================================================

class ContentInstanceRepository(BaseRepository):
    """内容实例仓库"""
    
    async def create(self, content: ContentInstance) -> int:
        """创建内容实例"""
        async with self.get_connection() as conn:
            data = content.to_dict()
            data.pop('id', None)
            
            # 处理枚举值
            if 'content_source' in data:
                data['content_source'] = content.content_source.value
            if 'content_type' in data:
                data['content_type'] = content.content_type.value
            
            fields = list(data.keys())
            placeholders = ', '.join(['?' for _ in fields])
            values = list(data.values())
            
            cursor = conn.execute(f"""
                INSERT INTO content_instances ({', '.join(fields)})
                VALUES ({placeholders})
            """, values)
            
            content_id = cursor.lastrowid
            logger.info(f"创建内容: {content.content_key} (ID: {content_id})")
            return content_id
    
    async def find_by_key_and_source(
        self, 
        content_key: str, 
        content_source: str, 
        source_identifier: str,
        language_code: str = "en_us"
    ) -> Optional[ContentInstance]:
        """根据键、来源、标识符和语言查找内容"""
        async with self.get_connection() as conn:
            cursor = conn.execute("""
                SELECT * FROM content_instances 
                WHERE content_key = ? AND content_source = ? 
                  AND source_identifier = ? AND language_code = ?
            """, (content_key, content_source, source_identifier, language_code))
            
            row = cursor.fetchone()
            if not row:
                return None
            
            return ModelFactory.create_model('content_instances', dict(row))
    
    async def search_by_text(
        self, 
        search_text: str, 
        language_code: Optional[str] = None,
        content_source: Optional[str] = None,
        limit: int = 100
    ) -> List[ContentInstance]:
        """按文本搜索内容"""
        conditions = ["source_text LIKE ?"]
        params = [f"%{search_text}%"]
        
        if language_code:
            conditions.append("language_code = ?")
            params.append(language_code)
        
        if content_source:
            conditions.append("content_source = ?")
            params.append(content_source)
        
        params.append(limit)
        
        async with self.get_connection() as conn:
            cursor = conn.execute(f"""
                SELECT * FROM content_instances 
                WHERE {' AND '.join(conditions)}
                ORDER BY updated_at DESC
                LIMIT ?
            """, params)
            
            rows = cursor.fetchall()
            return [ModelFactory.create_model('content_instances', dict(row)) for row in rows]


# ============================================================
# 高级查询仓库
# ============================================================

class AdvancedQueryRepository(BaseRepository):
    """高级查询仓库"""
    
    async def get_pack_version_stats(self, pack_id: int) -> List[PackVersionStats]:
        """获取包版本统计数据"""
        async with self.get_connection() as conn:
            cursor = conn.execute("""
                SELECT * FROM pack_version_stats 
                WHERE pack_id = ?
                ORDER BY version_tag
            """, (pack_id,))
            
            rows = cursor.fetchall()
            return [PackVersionStats(**dict(row)) for row in rows]
    
    async def track_content_across_versions(
        self, 
        content_key: str,
        pack_id: Optional[int] = None
    ) -> List[CrossVersionTrackingResult]:
        """跨版本追踪内容"""
        params = [content_key]
        pack_condition = ""
        
        if pack_id:
            pack_condition = "AND p.id = ?"
            params.append(pack_id)
        
        async with self.get_connection() as conn:
            cursor = conn.execute(f"""
                SELECT 
                    p.name as pack_name,
                    pv.version_tag as pack_version,
                    pv.minecraft_version,
                    mvi.mod_id,
                    mvi.mod_version,
                    ci.source_text,
                    pcr.change_type,
                    pcr.first_appeared_version
                FROM content_instances ci
                JOIN pack_content_relations pcr ON ci.id = pcr.content_instance_id
                JOIN pack_versions pv ON pcr.pack_version_id = pv.id  
                JOIN packs p ON pv.pack_id = p.id
                LEFT JOIN mod_version_instances mvi ON ci.source_identifier = mvi.mod_id
                WHERE ci.content_key = ? {pack_condition}
                ORDER BY pv.minecraft_version DESC, mvi.mod_version DESC
            """, params)
            
            rows = cursor.fetchall()
            return [CrossVersionTrackingResult(**dict(row)) for row in rows]
    
    async def get_mod_distribution(self, mod_id: str) -> List[ModDistributionResult]:
        """获取MOD跨包分布"""
        async with self.get_connection() as conn:
            cursor = conn.execute("""
                SELECT 
                    p.name as pack_name,
                    pv.version_tag as pack_version,
                    pv.minecraft_version,
                    mvi.mod_version,
                    pmr.relation_type,
                    pmr.load_order,
                    COUNT(DISTINCT ci.id) as translation_count
                FROM mod_version_instances mvi
                JOIN pack_mod_relations pmr ON mvi.id = pmr.mod_instance_id
                JOIN pack_versions pv ON pmr.pack_version_id = pv.id
                JOIN packs p ON pv.pack_id = p.id
                LEFT JOIN content_instances ci ON ci.source_identifier = mvi.mod_id 
                    AND ci.content_source = 'mod_jar'
                WHERE mvi.mod_id = ?
                GROUP BY p.id, pv.id, mvi.id
                ORDER BY pv.minecraft_version DESC, mvi.mod_version DESC
            """, (mod_id,))
            
            rows = cursor.fetchall()
            return [ModDistributionResult(**dict(row)) for row in rows]
    
    async def compare_versions_content(
        self, 
        version_1_id: int, 
        version_2_id: int
    ) -> List[ContentChangeResult]:
        """比较两个版本的内容差异"""
        async with self.get_connection() as conn:
            cursor = conn.execute("""
                WITH version_1_content AS (
                    SELECT ci.content_key, ci.content_source, ci.source_identifier, ci.source_text
                    FROM pack_content_relations pcr
                    JOIN content_instances ci ON pcr.content_instance_id = ci.id
                    WHERE pcr.pack_version_id = ?
                ),
                version_2_content AS (
                    SELECT ci.content_key, ci.content_source, ci.source_identifier, ci.source_text
                    FROM pack_content_relations pcr  
                    JOIN content_instances ci ON pcr.content_instance_id = ci.id
                    WHERE pcr.pack_version_id = ?
                )
                SELECT 
                    COALESCE(v1.content_key, v2.content_key) as content_key,
                    COALESCE(v1.content_source, v2.content_source) as content_source,
                    v1.source_text as version_1_text,
                    v2.source_text as version_2_text,
                    CASE 
                        WHEN v1.content_key IS NULL THEN 'ADDED'
                        WHEN v2.content_key IS NULL THEN 'REMOVED' 
                        WHEN v1.source_text != v2.source_text THEN 'MODIFIED'
                        ELSE 'UNCHANGED'
                    END as change_type
                FROM version_1_content v1
                FULL OUTER JOIN version_2_content v2 
                    ON v1.content_key = v2.content_key 
                    AND v1.content_source = v2.content_source
                    AND v1.source_identifier = v2.source_identifier
                WHERE CASE 
                    WHEN v1.content_key IS NULL THEN 'ADDED'
                    WHEN v2.content_key IS NULL THEN 'REMOVED' 
                    WHEN v1.source_text != v2.source_text THEN 'MODIFIED'
                    ELSE 'UNCHANGED'
                END != 'UNCHANGED'
                ORDER BY content_key
            """, (version_1_id, version_2_id))
            
            rows = cursor.fetchall()
            return [ContentChangeResult(**dict(row)) for row in rows]
    
    async def get_pack_specific_content(self, pack_version_id: int) -> List[ContentInstance]:
        """获取整合包专属内容"""
        async with self.get_connection() as conn:
            cursor = conn.execute("""
                SELECT ci.*
                FROM content_instances ci
                JOIN pack_content_relations pcr ON ci.id = pcr.content_instance_id  
                WHERE pcr.pack_version_id = ? 
                  AND ci.content_source IN ('pack_resource', 'quest_pack', 'config_file', 'pack_docs', 'override')
                ORDER BY ci.content_source, ci.content_type
            """, (pack_version_id,))
            
            rows = cursor.fetchall()
            return [ModelFactory.create_model('content_instances', dict(row)) for row in rows]


# ============================================================
# 仓库管理器
# ============================================================

class RepositoryManager:
    """仓库管理器"""
    
    def __init__(self, db_path: str):
        self.db_path = db_path
        self._repositories = {}
    
    def get_pack_repository(self) -> PackRepository:
        """获取Pack仓库"""
        if 'pack' not in self._repositories:
            self._repositories['pack'] = PackRepository(self.db_path)
        return self._repositories['pack']
    
    def get_pack_version_repository(self) -> PackVersionRepository:
        """获取PackVersion仓库"""
        if 'pack_version' not in self._repositories:
            self._repositories['pack_version'] = PackVersionRepository(self.db_path)
        return self._repositories['pack_version']
    
    def get_content_repository(self) -> ContentInstanceRepository:
        """获取Content仓库"""
        if 'content' not in self._repositories:
            self._repositories['content'] = ContentInstanceRepository(self.db_path)
        return self._repositories['content']
    
    def get_query_repository(self) -> AdvancedQueryRepository:
        """获取高级查询仓库"""
        if 'query' not in self._repositories:
            self._repositories['query'] = AdvancedQueryRepository(self.db_path)
        return self._repositories['query']
    
    async def close_all(self):
        """关闭所有仓库连接"""
        for repo in self._repositories.values():
            await repo.close()
        self._repositories.clear()