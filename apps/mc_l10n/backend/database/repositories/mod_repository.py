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
    
    async def find_mods(self, conditions: Dict[str, Any] = None, limit: int = 20, offset: int = 0) -> List[Dict[str, Any]]:
        """分页查找MOD列表"""
        if not conditions:
            conditions = {}
        
        # 构建WHERE条件
        where_clauses = []
        values = []
        
        for key, value in conditions.items():
            if value is None:
                where_clauses.append(f"{key} IS NULL")
            else:
                where_clauses.append(f"{key} = ?")
                values.append(value)
        
        where_clause = " AND ".join(where_clauses) if where_clauses else "1=1"
        sql = f"""
        SELECT * FROM core_mods 
        WHERE {where_clause}
        ORDER BY name ASC 
        LIMIT ? OFFSET ?
        """
        values.extend([limit, offset])
        
        with self.db_manager.get_connection() as conn:
            results = conn.execute(sql, values).fetchall()
            return [dict(row) for row in results]
    
    async def count_mods(self, conditions: Dict[str, Any] = None) -> int:
        """统计符合条件的MOD数量"""
        if not conditions:
            conditions = {}
        
        # 构建WHERE条件
        where_clauses = []
        values = []
        
        for key, value in conditions.items():
            if value is None:
                where_clauses.append(f"{key} IS NULL")
            else:
                where_clauses.append(f"{key} = ?")
                values.append(value)
        
        where_clause = " AND ".join(where_clauses) if where_clauses else "1=1"
        sql = f"SELECT COUNT(*) as count FROM core_mods WHERE {where_clause}"
        
        with self.db_manager.get_connection() as conn:
            result = conn.execute(sql, values).fetchone()
            return result['count']
    
    async def search_mods(self, search: str, limit: int = 20, offset: int = 0) -> List[Dict[str, Any]]:
        """根据关键词搜索MOD"""
        pattern = f"%{search}%"
        sql = """
        SELECT * FROM core_mods 
        WHERE name LIKE ? OR modid LIKE ? OR slug LIKE ?
        ORDER BY name ASC
        LIMIT ? OFFSET ?
        """
        
        with self.db_manager.get_connection() as conn:
            results = conn.execute(sql, (pattern, pattern, pattern, limit, offset)).fetchall()
            return [dict(row) for row in results]
    
    async def count_search_results(self, search: str) -> int:
        """统计搜索结果数量"""
        pattern = f"%{search}%"
        sql = """
        SELECT COUNT(*) as count FROM core_mods 
        WHERE name LIKE ? OR modid LIKE ? OR slug LIKE ?
        """
        
        with self.db_manager.get_connection() as conn:
            result = conn.execute(sql, (pattern, pattern, pattern)).fetchone()
            return result['count']
    
    async def get_mod_by_uid(self, uid: str) -> Optional[Dict[str, Any]]:
        """根据UID获取MOD"""
        mod = await self.get_by_uid(uid)
        if mod:
            return self._entity_to_dict(mod)
        return None
    
    async def create_mod(self, modid: str = None, slug: str = None, name: str = None, homepage: str = None) -> Dict[str, Any]:
        """创建MOD"""
        mod = Mod(
            uid=self._generate_uid(),
            modid=modid,
            slug=slug,
            name=name,
            homepage=homepage,
            created_at=self._get_timestamp(),
            updated_at=self._get_timestamp()
        )
        
        await self.create(mod)
        return self._entity_to_dict(mod)
    
    async def find_mod_versions(self, conditions: Dict[str, Any] = None, limit: int = 20, offset: int = 0) -> List[Dict[str, Any]]:
        """查找MOD版本"""
        if not conditions:
            return []
        
        version_repo = ModVersionRepository(self.db_manager)
        
        # 构建WHERE条件
        where_clauses = []
        values = []
        
        for key, value in conditions.items():
            if value is None:
                where_clauses.append(f"{key} IS NULL")
            else:
                where_clauses.append(f"{key} = ?")
                values.append(value)
        
        where_clause = " AND ".join(where_clauses)
        sql = f"""
        SELECT * FROM core_mod_versions 
        WHERE {where_clause}
        ORDER BY discovered_at DESC 
        LIMIT ? OFFSET ?
        """
        values.extend([limit, offset])
        
        with version_repo.db_manager.get_connection() as conn:
            results = conn.execute(sql, values).fetchall()
            return [dict(row) for row in results]
    
    async def count_mod_versions(self, conditions: Dict[str, Any] = None) -> int:
        """统计MOD版本数量"""
        if not conditions:
            return 0
        
        version_repo = ModVersionRepository(self.db_manager)
        
        # 构建WHERE条件
        where_clauses = []
        values = []
        
        for key, value in conditions.items():
            if value is None:
                where_clauses.append(f"{key} IS NULL")
            else:
                where_clauses.append(f"{key} = ?")
                values.append(value)
        
        where_clause = " AND ".join(where_clauses)
        sql = f"SELECT COUNT(*) as count FROM core_mod_versions WHERE {where_clause}"
        
        with version_repo.db_manager.get_connection() as conn:
            result = conn.execute(sql, values).fetchone()
            return result['count']
    
    async def create_mod_version(self, mod_uid: str, loader: str, mc_version: str, version: str, 
                               meta_json: Dict[str, Any] = None, source: str = None) -> Dict[str, Any]:
        """创建MOD版本"""
        version_repo = ModVersionRepository(self.db_manager)
        mod_version = ModVersion(
            uid=self._generate_uid(),
            mod_uid=mod_uid,
            loader=loader,
            mc_version=mc_version,
            version=version,
            meta_json=meta_json,
            source=source,
            discovered_at=self._get_timestamp()
        )
        
        await version_repo.create(mod_version)
        return version_repo._entity_to_dict(mod_version)
    
    async def get_compatibility_matrix(self, mod_uid: str, target_mc_version: str = None, 
                                     target_loader: str = None) -> Dict[str, Any]:
        """获取MOD兼容性矩阵"""
        version_repo = ModVersionRepository(self.db_manager)
        return await version_repo.get_version_compatibility(mod_uid)
    
    async def find_similar_mods(self, name: str, threshold: float = 0.8, limit: int = 10) -> List[Dict[str, Any]]:
        """查找相似MOD"""
        # 简单实现：使用LIKE查询，实际可以使用更复杂的相似度算法
        sql = """
        SELECT *, 
               CASE 
                   WHEN name = ? THEN 1.0
                   WHEN name LIKE ? THEN 0.9
                   WHEN name LIKE ? THEN 0.8
                   ELSE 0.7
               END as similarity
        FROM core_mods 
        WHERE name LIKE ? AND name != ?
        ORDER BY similarity DESC, name ASC
        LIMIT ?
        """
        
        exact_match = name
        starts_with = f"{name}%"
        contains = f"%{name}%"
        
        with self.db_manager.get_connection() as conn:
            results = conn.execute(sql, (exact_match, starts_with, contains, contains, exact_match, limit)).fetchall()
            return [dict(row) for row in results]


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