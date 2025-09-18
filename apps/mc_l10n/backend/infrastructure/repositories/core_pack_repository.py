"""
V5架构 - 整合包Repository
管理core_packs表的数据访问
"""

import uuid
from typing import Optional, List
from dataclasses import dataclass
from enum import Enum

from .base_repository import BaseRepository


class PackPlatform(Enum):
    """整合包平台枚举"""
    MODRINTH = "modrinth"
    CURSEFORGE = "curseforge"
    CUSTOM = "custom"


@dataclass
class CorePack:
    """核心整合包实体"""
    uid: str
    platform: PackPlatform
    slug: str
    title: str
    author: Optional[str] = None
    homepage: Optional[str] = None
    created_at: Optional[str] = None
    updated_at: Optional[str] = None
    id: Optional[int] = None


class CorePackRepository(BaseRepository[CorePack]):
    """整合包Repository实现"""
    
    def table_name(self) -> str:
        return "core_packs"
    
    def create(self, entity: CorePack) -> str:
        """创建整合包"""
        if not entity.uid:
            entity.uid = str(uuid.uuid4())
        
        query = """
            INSERT INTO core_packs (uid, platform, slug, title, author, homepage)
            VALUES (?, ?, ?, ?, ?, ?)
        """
        self.execute_write(query, (
            entity.uid, 
            entity.platform.value, 
            entity.slug, 
            entity.title,
            entity.author,
            entity.homepage
        ))
        return entity.uid
    
    def get_by_uid(self, uid: str) -> Optional[CorePack]:
        """根据UID获取整合包"""
        query = """
            SELECT id, uid, platform, slug, title, author, homepage, created_at, updated_at
            FROM core_packs 
            WHERE uid = ?
        """
        row = self.execute_single(query, (uid,))
        return self._row_to_entity(row) if row else None
    
    def update(self, entity: CorePack) -> bool:
        """更新整合包"""
        query = """
            UPDATE core_packs 
            SET platform = ?, slug = ?, title = ?, author = ?, homepage = ?, updated_at = datetime('now')
            WHERE uid = ?
        """
        affected = self.execute_write(query, (
            entity.platform.value,
            entity.slug,
            entity.title,
            entity.author,
            entity.homepage,
            entity.uid
        ))
        return affected > 0
    
    def delete_by_uid(self, uid: str) -> bool:
        """删除整合包"""
        query = "DELETE FROM core_packs WHERE uid = ?"
        affected = self.execute_write(query, (uid,))
        return affected > 0
    
    def list_all(self, limit: Optional[int] = None, offset: int = 0) -> List[CorePack]:
        """列出所有整合包"""
        query = """
            SELECT id, uid, platform, slug, title, author, homepage, created_at, updated_at
            FROM core_packs 
            ORDER BY created_at DESC
        """
        if limit:
            query += f" LIMIT {limit} OFFSET {offset}"
        
        rows = self.execute_query(query)
        return [self._row_to_entity(row) for row in rows]
    
    def get_by_slug(self, platform: PackPlatform, slug: str) -> Optional[CorePack]:
        """根据平台和slug获取整合包"""
        query = """
            SELECT id, uid, platform, slug, title, author, homepage, created_at, updated_at
            FROM core_packs 
            WHERE platform = ? AND slug = ?
        """
        row = self.execute_single(query, (platform.value, slug))
        return self._row_to_entity(row) if row else None
    
    def list_by_platform(self, platform: PackPlatform) -> List[CorePack]:
        """按平台列出整合包"""
        query = """
            SELECT id, uid, platform, slug, title, author, homepage, created_at, updated_at
            FROM core_packs 
            WHERE platform = ?
            ORDER BY title
        """
        rows = self.execute_query(query, (platform.value,))
        return [self._row_to_entity(row) for row in rows]
    
    def search_by_title(self, title_pattern: str) -> List[CorePack]:
        """按标题模糊搜索整合包"""
        query = """
            SELECT id, uid, platform, slug, title, author, homepage, created_at, updated_at
            FROM core_packs 
            WHERE title LIKE ?
            ORDER BY title
        """
        rows = self.execute_query(query, (f"%{title_pattern}%",))
        return [self._row_to_entity(row) for row in rows]
    
    def get_stats_by_platform(self) -> List[dict]:
        """获取按平台统计的整合包数量"""
        query = """
            SELECT platform, COUNT(*) as count
            FROM core_packs 
            GROUP BY platform
            ORDER BY count DESC
        """
        rows = self.execute_query(query)
        return [{"platform": row['platform'], "count": row['count']} for row in rows]
    
    def _row_to_entity(self, row) -> CorePack:
        """将数据库行转换为实体"""
        return CorePack(
            id=row['id'],
            uid=row['uid'],
            platform=PackPlatform(row['platform']),
            slug=row['slug'],
            title=row['title'],
            author=row['author'],
            homepage=row['homepage'],
            created_at=row['created_at'],
            updated_at=row['updated_at']
        )