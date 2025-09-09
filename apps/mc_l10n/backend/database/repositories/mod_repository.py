#!/usr/bin/env python
"""
MOD Repository
提供MOD相关的数据访问操作
"""

from typing import List, Optional, Dict, Any
from dataclasses import dataclass, asdict
from packages.core.data.repositories.base_repository import JsonFieldRepository


@dataclass
class Mod:
    """MOD实体"""
    uid: str = None
    modid: str = None
    slug: str = None
    name: str = None
    homepage: str = None
    created_at: str = None
    updated_at: str = None
    id: int = None
    
    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class ModVersion:
    """MOD版本实体"""
    uid: str = None
    mod_uid: str = None
    loader: str = None
    mc_version: str = None
    version: str = None
    meta_json: Dict[str, Any] = None
    source: str = None
    discovered_at: str = None
    id: int = None
    
    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


class ModRepository(JsonFieldRepository[Mod, int]):
    """MOD Repository"""
    
    def __init__(self, db_manager):
        super().__init__(
            db_manager=db_manager,
            table_name="core_mods",
            entity_class=Mod
        )
    
    async def find_by_modid(self, modid: str) -> Optional[Mod]:
        """根据ModID查找MOD"""
        return await self.find_one_by(modid=modid)
    
    async def find_by_slug(self, slug: str) -> Optional[Mod]:
        """根据slug查找MOD"""
        return await self.find_one_by(slug=slug)
    
    async def search_by_name(self, name_pattern: str) -> List[Mod]:
        """根据名称搜索MOD"""
        sql = """
        SELECT * FROM core_mods 
        WHERE name LIKE ? OR modid LIKE ?
        ORDER BY name
        """
        
        pattern = f"%{name_pattern}%"
        with self.db_manager.get_connection() as conn:
            results = conn.execute(sql, (pattern, pattern)).fetchall()
            return [self._dict_to_entity(dict(row)) for row in results]
    
    async def get_mod_with_versions(self, mod_uid: str) -> Optional[Dict[str, Any]]:
        """获取MOD及其所有版本信息"""
        mod = await self.get_by_uid(mod_uid)
        if not mod:
            return None
        
        # 获取版本信息
        version_repo = ModVersionRepository(self.db_manager)
        versions = await version_repo.find_by_mod(mod_uid)
        
        result = self._entity_to_dict(mod)
        result['versions'] = [version_repo._entity_to_dict(v) for v in versions]
        
        return result
    
    async def get_mods_by_mc_version(self, mc_version: str) -> List[Dict[str, Any]]:
        """根据Minecraft版本获取MOD列表"""
        sql = """
        SELECT DISTINCT m.* FROM core_mods m
        JOIN core_mod_versions mv ON m.uid = mv.mod_uid
        WHERE mv.mc_version = ?
        ORDER BY m.name
        """
        
        with self.db_manager.get_connection() as conn:
            results = conn.execute(sql, (mc_version,)).fetchall()
            return [self._dict_to_entity(dict(row)) for row in results]


class ModVersionRepository(JsonFieldRepository[ModVersion, int]):
    """MOD版本Repository"""
    
    def __init__(self, db_manager):
        super().__init__(
            db_manager=db_manager,
            table_name="core_mod_versions",
            json_fields=["meta_json"],
            entity_class=ModVersion
        )
    
    async def find_by_mod(self, mod_uid: str) -> List[ModVersion]:
        """根据MOD UID查找版本"""
        sql = """
        SELECT * FROM core_mod_versions 
        WHERE mod_uid = ? 
        ORDER BY discovered_at DESC
        """
        
        with self.db_manager.get_connection() as conn:
            results = conn.execute(sql, (mod_uid,)).fetchall()
            return [self._dict_to_entity(dict(row)) for row in results]
    
    async def find_by_mc_version(self, mc_version: str) -> List[ModVersion]:
        """根据Minecraft版本查找MOD版本"""
        return await self.find_by(mc_version=mc_version)
    
    async def find_by_loader(self, loader: str) -> List[ModVersion]:
        """根据加载器查找MOD版本"""
        return await self.find_by(loader=loader)
    
    async def find_by_mod_and_mc_version(self, mod_uid: str, mc_version: str) -> List[ModVersion]:
        """根据MOD和MC版本查找版本"""
        return await self.find_by(mod_uid=mod_uid, mc_version=mc_version)
    
    async def get_latest_version(self, mod_uid: str, mc_version: str = None, loader: str = None) -> Optional[ModVersion]:
        """获取MOD最新版本"""
        conditions = ["mod_uid = ?"]
        params = [mod_uid]
        
        if mc_version:
            conditions.append("mc_version = ?")
            params.append(mc_version)
        
        if loader:
            conditions.append("loader = ?")
            params.append(loader)
        
        where_clause = " AND ".join(conditions)
        sql = f"""
        SELECT * FROM core_mod_versions 
        WHERE {where_clause}
        ORDER BY discovered_at DESC 
        LIMIT 1
        """
        
        with self.db_manager.get_connection() as conn:
            result = conn.execute(sql, params).fetchone()
            if result:
                return self._dict_to_entity(dict(result))
            return None
    
    async def get_version_compatibility(self, mod_uid: str) -> Dict[str, List[str]]:
        """获取版本兼容性矩阵"""
        sql = """
        SELECT mc_version, loader, COUNT(*) as version_count
        FROM core_mod_versions 
        WHERE mod_uid = ?
        GROUP BY mc_version, loader
        ORDER BY mc_version DESC, loader
        """
        
        with self.db_manager.get_connection() as conn:
            results = conn.execute(sql, (mod_uid,)).fetchall()
            
            compatibility = {}
            for row in results:
                mc_ver = row['mc_version']
                loader = row['loader']
                
                if mc_ver not in compatibility:
                    compatibility[mc_ver] = []
                
                compatibility[mc_ver].append({
                    'loader': loader,
                    'version_count': row['version_count']
                })
            
            return compatibility
    
    async def find_exact_version(self, mod_uid: str, loader: str, mc_version: str, version: str) -> Optional[ModVersion]:
        """查找精确版本匹配"""
        return await self.find_one_by(
            mod_uid=mod_uid,
            loader=loader,
            mc_version=mc_version,
            version=version
        )
    
    async def get_version_stats(self) -> Dict[str, Any]:
        """获取版本统计信息"""
        sql = """
        SELECT 
            COUNT(*) as total_versions,
            COUNT(DISTINCT mod_uid) as unique_mods,
            COUNT(DISTINCT mc_version) as mc_versions,
            COUNT(DISTINCT loader) as loaders,
            MAX(discovered_at) as latest_discovery
        FROM core_mod_versions
        """
        
        with self.db_manager.get_connection() as conn:
            result = conn.execute(sql).fetchone()
            return dict(result) if result else {}
    
    async def get_loader_distribution(self) -> Dict[str, int]:
        """获取加载器分布统计"""
        sql = """
        SELECT loader, COUNT(*) as count
        FROM core_mod_versions
        GROUP BY loader
        ORDER BY count DESC
        """
        
        with self.db_manager.get_connection() as conn:
            results = conn.execute(sql).fetchall()
            return {row['loader']: row['count'] for row in results}
    
    async def get_mc_version_distribution(self) -> Dict[str, int]:
        """获取Minecraft版本分布统计"""
        sql = """
        SELECT mc_version, COUNT(*) as count
        FROM core_mod_versions
        GROUP BY mc_version
        ORDER BY mc_version DESC
        """
        
        with self.db_manager.get_connection() as conn:
            results = conn.execute(sql).fetchall()
            return {row['mc_version']: row['count'] for row in results}