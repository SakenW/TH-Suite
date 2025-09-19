"""
V5架构 - 语言文件Repository
管理core_language_files表的数据访问
"""

import uuid
from datetime import datetime
from typing import Optional, List
from dataclasses import dataclass

from .base_repository import BaseRepository


@dataclass
class CoreLanguageFile:
    """核心语言文件实体"""
    uid: str
    carrier_type: str  # mod, resource_pack, data_pack, override
    carrier_uid: str
    locale: str
    rel_path: str
    format: str  # json, lang, properties, xml, cfg
    size: int = 0
    discovered_at: Optional[str] = None
    id: Optional[int] = None


class CoreLanguageFileRepository(BaseRepository[CoreLanguageFile]):
    """语言文件Repository实现"""
    
    def table_name(self) -> str:
        return "core_language_files"
    
    def create(self, entity: CoreLanguageFile) -> str:
        """创建语言文件"""
        if not entity.uid:
            entity.uid = str(uuid.uuid4())
        
        query = """
            INSERT INTO core_language_files (
                uid, carrier_type, carrier_uid, locale, rel_path, format, size
            )
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """
        self.execute_write(query, (
            entity.uid, entity.carrier_type, entity.carrier_uid,
            entity.locale, entity.rel_path, entity.format, entity.size
        ))
        return entity.uid
    
    def get_by_uid(self, uid: str) -> Optional[CoreLanguageFile]:
        """根据UID获取语言文件"""
        query = """
            SELECT id, uid, carrier_type, carrier_uid, locale, rel_path, 
                   format, size, discovered_at
            FROM core_language_files 
            WHERE uid = ?
        """
        row = self.execute_single(query, (uid,))
        return self._row_to_entity(row) if row else None
    
    def update(self, entity: CoreLanguageFile) -> bool:
        """更新语言文件"""
        query = """
            UPDATE core_language_files 
            SET carrier_type = ?, carrier_uid = ?, locale = ?, 
                rel_path = ?, format = ?, size = ?
            WHERE uid = ?
        """
        affected = self.execute_write(query, (
            entity.carrier_type, entity.carrier_uid, entity.locale,
            entity.rel_path, entity.format, entity.size, entity.uid
        ))
        return affected > 0
    
    def delete_by_uid(self, uid: str) -> bool:
        """删除语言文件"""
        query = "DELETE FROM core_language_files WHERE uid = ?"
        affected = self.execute_write(query, (uid,))
        return affected > 0
    
    def list_all(self, limit: Optional[int] = None, offset: int = 0) -> List[CoreLanguageFile]:
        """列出所有语言文件"""
        query = """
            SELECT id, uid, carrier_type, carrier_uid, locale, rel_path, 
                   format, size, discovered_at
            FROM core_language_files 
            ORDER BY discovered_at DESC
        """
        if limit:
            query += f" LIMIT {limit} OFFSET {offset}"
        
        rows = self.execute_query(query)
        return [self._row_to_entity(row) for row in rows]
    
    def get_by_carrier(self, carrier_uid: str) -> List[CoreLanguageFile]:
        """根据载体UID获取语言文件"""
        query = """
            SELECT id, uid, carrier_type, carrier_uid, locale, rel_path, 
                   format, size, discovered_at
            FROM core_language_files 
            WHERE carrier_uid = ?
            ORDER BY locale, rel_path
        """
        rows = self.execute_query(query, (carrier_uid,))
        return [self._row_to_entity(row) for row in rows]
    
    def get_by_locale(self, locale: str) -> List[CoreLanguageFile]:
        """根据语言代码获取语言文件"""
        query = """
            SELECT id, uid, carrier_type, carrier_uid, locale, rel_path, 
                   format, size, discovered_at
            FROM core_language_files 
            WHERE locale = ?
            ORDER BY carrier_uid, rel_path
        """
        rows = self.execute_query(query, (locale,))
        return [self._row_to_entity(row) for row in rows]
    
    def find_by_carrier_and_path(
        self, 
        carrier_uid: str, 
        rel_path: str, 
        locale: str = None
    ) -> Optional[CoreLanguageFile]:
        """根据载体和路径查找语言文件"""
        if locale:
            query = """
                SELECT id, uid, carrier_type, carrier_uid, locale, rel_path, 
                       format, size, discovered_at
                FROM core_language_files 
                WHERE carrier_uid = ? AND rel_path = ? AND locale = ?
            """
            row = self.execute_single(query, (carrier_uid, rel_path, locale))
        else:
            query = """
                SELECT id, uid, carrier_type, carrier_uid, locale, rel_path, 
                       format, size, discovered_at
                FROM core_language_files 
                WHERE carrier_uid = ? AND rel_path = ?
            """
            row = self.execute_single(query, (carrier_uid, rel_path))
        
        return self._row_to_entity(row) if row else None
    
    def get_statistics(self) -> dict:
        """获取语言文件统计信息"""
        stats = {}
        
        # 按载体类型统计
        query = """
            SELECT carrier_type, COUNT(*) as count
            FROM core_language_files 
            GROUP BY carrier_type
        """
        rows = self.execute_query(query)
        stats['by_carrier_type'] = {row['carrier_type']: row['count'] for row in rows}
        
        # 按语言统计
        query = """
            SELECT locale, COUNT(*) as count
            FROM core_language_files 
            GROUP BY locale
            ORDER BY count DESC
        """
        rows = self.execute_query(query)
        stats['by_locale'] = {row['locale']: row['count'] for row in rows}
        
        # 按格式统计
        query = """
            SELECT format, COUNT(*) as count
            FROM core_language_files 
            GROUP BY format
        """
        rows = self.execute_query(query)
        stats['by_format'] = {row['format']: row['count'] for row in rows}
        
        # 总数统计
        stats['total_files'] = self.count()
        
        return stats
    
    def cleanup_orphaned_files(self) -> int:
        """清理孤立的语言文件（载体不存在的文件）"""
        query = """
            DELETE FROM core_language_files 
            WHERE carrier_uid NOT IN (
                SELECT uid FROM core_mods
                UNION
                SELECT uid FROM core_packs
            )
        """
        return self.execute_write(query)
    
    def _row_to_entity(self, row) -> CoreLanguageFile:
        """将数据库行转换为实体"""
        return CoreLanguageFile(
            id=row['id'],
            uid=row['uid'],
            carrier_type=row['carrier_type'],
            carrier_uid=row['carrier_uid'],
            locale=row['locale'],
            rel_path=row['rel_path'],
            format=row['format'],
            size=row['size'],
            discovered_at=row['discovered_at']
        )