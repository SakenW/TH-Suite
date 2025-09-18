"""
V5架构 - 项目Repository
管理core_projects表的数据访问
"""

import uuid
from datetime import datetime
from typing import Optional, List
from dataclasses import dataclass

from .base_repository import BaseRepository


@dataclass
class CoreProject:
    """核心项目实体"""
    uid: str
    name: str
    description: Optional[str] = None
    created_at: Optional[str] = None
    updated_at: Optional[str] = None
    id: Optional[int] = None


class CoreProjectRepository(BaseRepository[CoreProject]):
    """项目Repository实现"""
    
    def table_name(self) -> str:
        return "core_projects"
    
    def create(self, entity: CoreProject) -> str:
        """创建项目"""
        if not entity.uid:
            entity.uid = str(uuid.uuid4())
        
        query = """
            INSERT INTO core_projects (uid, name, description)
            VALUES (?, ?, ?)
        """
        self.execute_write(query, (entity.uid, entity.name, entity.description))
        return entity.uid
    
    def get_by_uid(self, uid: str) -> Optional[CoreProject]:
        """根据UID获取项目"""
        query = """
            SELECT id, uid, name, description, created_at, updated_at
            FROM core_projects 
            WHERE uid = ?
        """
        row = self.execute_single(query, (uid,))
        return self._row_to_entity(row) if row else None
    
    def update(self, entity: CoreProject) -> bool:
        """更新项目"""
        query = """
            UPDATE core_projects 
            SET name = ?, description = ?, updated_at = datetime('now')
            WHERE uid = ?
        """
        affected = self.execute_write(query, (entity.name, entity.description, entity.uid))
        return affected > 0
    
    def delete_by_uid(self, uid: str) -> bool:
        """删除项目"""
        query = "DELETE FROM core_projects WHERE uid = ?"
        affected = self.execute_write(query, (uid,))
        return affected > 0
    
    def list_all(self, limit: Optional[int] = None, offset: int = 0) -> List[CoreProject]:
        """列出所有项目"""
        query = """
            SELECT id, uid, name, description, created_at, updated_at
            FROM core_projects 
            ORDER BY created_at DESC
        """
        if limit:
            query += f" LIMIT {limit} OFFSET {offset}"
        
        rows = self.execute_query(query)
        return [self._row_to_entity(row) for row in rows]
    
    def get_by_name(self, name: str) -> Optional[CoreProject]:
        """根据名称获取项目"""
        query = """
            SELECT id, uid, name, description, created_at, updated_at
            FROM core_projects 
            WHERE name = ?
        """
        row = self.execute_single(query, (name,))
        return self._row_to_entity(row) if row else None
    
    def search_by_name(self, name_pattern: str) -> List[CoreProject]:
        """按名称模糊搜索项目"""
        query = """
            SELECT id, uid, name, description, created_at, updated_at
            FROM core_projects 
            WHERE name LIKE ?
            ORDER BY name
        """
        rows = self.execute_query(query, (f"%{name_pattern}%",))
        return [self._row_to_entity(row) for row in rows]
    
    def get_default_project(self) -> Optional[CoreProject]:
        """获取默认项目（第一个创建的项目）"""
        query = """
            SELECT id, uid, name, description, created_at, updated_at
            FROM core_projects 
            ORDER BY created_at ASC
            LIMIT 1
        """
        row = self.execute_single(query)
        return self._row_to_entity(row) if row else None
    
    def _row_to_entity(self, row) -> CoreProject:
        """将数据库行转换为实体"""
        return CoreProject(
            id=row['id'],
            uid=row['uid'],
            name=row['name'],
            description=row['description'],
            created_at=row['created_at'],
            updated_at=row['updated_at']
        )