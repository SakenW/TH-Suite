"""
V5架构 - MOD Repository
管理core_mods和core_mod_versions表的数据访问
"""

import uuid
from typing import Optional, List
from dataclasses import dataclass
from enum import Enum

from .base_repository import BaseRepository


class ModLoader(Enum):
    """MOD加载器枚举"""
    FORGE = "forge"
    NEOFORGE = "neoforge"
    FABRIC = "fabric"
    QUILT = "quilt"
    MULTI = "multi"
    UNKNOWN = "unknown"


@dataclass
class CoreMod:
    """核心MOD实体"""
    uid: str
    modid: Optional[str]
    slug: Optional[str]
    name: str
    homepage: Optional[str] = None
    created_at: Optional[str] = None
    updated_at: Optional[str] = None
    id: Optional[int] = None


@dataclass
class CoreModVersion:
    """MOD版本实体"""
    uid: str
    mod_uid: str
    loader: ModLoader
    mc_version: str
    version: str
    meta_json: Optional[str] = None
    source: Optional[str] = None
    discovered_at: Optional[str] = None
    id: Optional[int] = None


class CoreModRepository(BaseRepository[CoreMod]):
    """MOD Repository实现"""
    
    def table_name(self) -> str:
        return "core_mods"
    
    def create(self, entity: CoreMod) -> str:
        """创建MOD"""
        if not entity.uid:
            entity.uid = str(uuid.uuid4())
        
        query = """
            INSERT INTO core_mods (uid, modid, slug, name, homepage)
            VALUES (?, ?, ?, ?, ?)
        """
        self.execute_write(query, (
            entity.uid, 
            entity.modid, 
            entity.slug, 
            entity.name,
            entity.homepage
        ))
        return entity.uid
    
    def get_by_uid(self, uid: str) -> Optional[CoreMod]:
        """根据UID获取MOD"""
        query = """
            SELECT id, uid, modid, slug, name, homepage, created_at, updated_at
            FROM core_mods 
            WHERE uid = ?
        """
        row = self.execute_single(query, (uid,))
        return self._row_to_entity(row) if row else None
    
    def update(self, entity: CoreMod) -> bool:
        """更新MOD"""
        query = """
            UPDATE core_mods 
            SET modid = ?, slug = ?, name = ?, homepage = ?, updated_at = datetime('now')
            WHERE uid = ?
        """
        affected = self.execute_write(query, (
            entity.modid,
            entity.slug,
            entity.name,
            entity.homepage,
            entity.uid
        ))
        return affected > 0
    
    def delete_by_uid(self, uid: str) -> bool:
        """删除MOD"""
        query = "DELETE FROM core_mods WHERE uid = ?"
        affected = self.execute_write(query, (uid,))
        return affected > 0
    
    def list_all(self, limit: Optional[int] = None, offset: int = 0) -> List[CoreMod]:
        """列出所有MOD"""
        query = """
            SELECT id, uid, modid, slug, name, homepage, created_at, updated_at
            FROM core_mods 
            ORDER BY name
        """
        if limit:
            query += f" LIMIT {limit} OFFSET {offset}"
        
        rows = self.execute_query(query)
        return [self._row_to_entity(row) for row in rows]
    
    def get_by_modid(self, modid: str) -> Optional[CoreMod]:
        """根据modid获取MOD"""
        query = """
            SELECT id, uid, modid, slug, name, homepage, created_at, updated_at
            FROM core_mods 
            WHERE modid = ?
        """
        row = self.execute_single(query, (modid,))
        return self._row_to_entity(row) if row else None
    
    def search_by_name(self, name_pattern: str) -> List[CoreMod]:
        """按名称模糊搜索MOD"""
        query = """
            SELECT id, uid, modid, slug, name, homepage, created_at, updated_at
            FROM core_mods 
            WHERE name LIKE ? OR modid LIKE ?
            ORDER BY name
        """
        pattern = f"%{name_pattern}%"
        rows = self.execute_query(query, (pattern, pattern))
        return [self._row_to_entity(row) for row in rows]
    
    def get_mod_versions(self, mod_uid: str) -> List[CoreModVersion]:
        """获取MOD的所有版本"""
        query = """
            SELECT id, uid, mod_uid, loader, mc_version, version, meta_json, source, discovered_at
            FROM core_mod_versions 
            WHERE mod_uid = ?
            ORDER BY discovered_at DESC
        """
        rows = self.execute_query(query, (mod_uid,))
        return [self._row_to_mod_version(row) for row in rows]
    
    def create_mod_version(self, version: CoreModVersion) -> str:
        """创建MOD版本"""
        if not version.uid:
            version.uid = str(uuid.uuid4())
        
        query = """
            INSERT INTO core_mod_versions (uid, mod_uid, loader, mc_version, version, meta_json, source)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """
        self.execute_write(query, (
            version.uid,
            version.mod_uid,
            version.loader.value,
            version.mc_version,
            version.version,
            version.meta_json,
            version.source
        ))
        return version.uid
    
    def get_version_by_uid(self, version_uid: str) -> Optional[CoreModVersion]:
        """根据UID获取MOD版本"""
        query = """
            SELECT id, uid, mod_uid, loader, mc_version, version, meta_json, source, discovered_at
            FROM core_mod_versions 
            WHERE uid = ?
        """
        row = self.execute_single(query, (version_uid,))
        return self._row_to_mod_version(row) if row else None
    
    def get_mods_with_version_count(self) -> List[dict]:
        """获取MOD及其版本数量统计"""
        query = """
            SELECT m.uid, m.name, m.modid, COUNT(v.id) as version_count
            FROM core_mods m
            LEFT JOIN core_mod_versions v ON m.uid = v.mod_uid
            GROUP BY m.uid, m.name, m.modid
            ORDER BY version_count DESC, m.name
        """
        rows = self.execute_query(query)
        return [dict(row) for row in rows]
    
    def _row_to_entity(self, row) -> CoreMod:
        """将数据库行转换为MOD实体"""
        return CoreMod(
            id=row['id'],
            uid=row['uid'],
            modid=row['modid'],
            slug=row['slug'],
            name=row['name'],
            homepage=row['homepage'],
            created_at=row['created_at'],
            updated_at=row['updated_at']
        )
    
    def _row_to_mod_version(self, row) -> CoreModVersion:
        """将数据库行转换为MOD版本实体"""
        return CoreModVersion(
            id=row['id'],
            uid=row['uid'],
            mod_uid=row['mod_uid'],
            loader=ModLoader(row['loader']),
            mc_version=row['mc_version'],
            version=row['version'],
            meta_json=row['meta_json'],
            source=row['source'],
            discovered_at=row['discovered_at']
        )