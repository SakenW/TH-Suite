#!/usr/bin/env python
"""
整合包Repository
提供整合包相关的数据访问操作
"""

from typing import List, Optional, Dict, Any
from dataclasses import dataclass, asdict
from packages.core.data.repositories.base_repository import JsonFieldRepository


@dataclass
class Pack:
    """整合包实体"""
    uid: str = None
    platform: str = None  # modrinth, curseforge, custom
    slug: str = None
    title: str = None
    author: str = None
    homepage: str = None
    created_at: str = None
    updated_at: str = None
    id: int = None
    
    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class PackVersion:
    """整合包版本实体"""
    uid: str = None
    pack_uid: str = None
    mc_version: str = None
    loader: str = None  # forge, neoforge, fabric, quilt, multi, unknown
    manifest_json: Dict[str, Any] = None
    manifest_hash_b3: str = None
    manifest_hash_md5: str = None
    created_at: str = None
    id: int = None
    
    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class PackItem:
    """整合包清单条目实体"""
    pack_version_uid: str = None
    item_type: str = None  # mod, resourcepack, datapack, override
    source_platform: str = None  # modrinth, curseforge, url, local
    identity: str = None
    constraints: Dict[str, Any] = None
    position: int = None
    created_at: str = None
    id: int = None
    
    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class PackInstallation:
    """整合包本地实例实体"""
    uid: str = None
    pack_version_uid: str = None
    root_path: str = None
    launcher: str = None  # curseforge, modrinth, vanilla, custom
    enabled: bool = True
    created_at: str = None
    updated_at: str = None
    id: int = None
    
    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


class PackRepository(JsonFieldRepository[Pack, int]):
    """整合包Repository"""
    
    def __init__(self, db_manager):
        super().__init__(
            db_manager=db_manager,
            table_name="core_packs",
            entity_class=Pack
        )
    
    async def find_by_platform(self, platform: str) -> List[Pack]:
        """根据平台查找整合包"""
        return await self.find_by(platform=platform)
    
    async def find_by_slug(self, slug: str) -> Optional[Pack]:
        """根据slug查找整合包"""
        return await self.find_one_by(slug=slug)
    
    async def search_by_title(self, title_pattern: str) -> List[Pack]:
        """根据标题搜索整合包"""
        sql = """
        SELECT * FROM core_packs 
        WHERE title LIKE ? 
        ORDER BY title
        """
        
        with self.db_manager.get_connection() as conn:
            results = conn.execute(sql, (f"%{title_pattern}%",)).fetchall()
            return [self._dict_to_entity(dict(row)) for row in results]


class PackVersionRepository(JsonFieldRepository[PackVersion, int]):
    """整合包版本Repository"""
    
    def __init__(self, db_manager):
        super().__init__(
            db_manager=db_manager,
            table_name="core_pack_versions", 
            json_fields=["manifest_json"],
            entity_class=PackVersion
        )
    
    async def find_by_pack(self, pack_uid: str) -> List[PackVersion]:
        """根据整合包UID查找版本"""
        return await self.find_by(pack_uid=pack_uid)
    
    async def find_by_mc_version(self, mc_version: str) -> List[PackVersion]:
        """根据Minecraft版本查找整合包版本"""
        return await self.find_by(mc_version=mc_version)
    
    async def find_by_loader(self, loader: str) -> List[PackVersion]:
        """根据加载器查找整合包版本"""
        return await self.find_by(loader=loader)
    
    async def get_latest_version(self, pack_uid: str) -> Optional[PackVersion]:
        """获取整合包最新版本"""
        sql = """
        SELECT * FROM core_pack_versions 
        WHERE pack_uid = ? 
        ORDER BY created_at DESC 
        LIMIT 1
        """
        
        with self.db_manager.get_connection() as conn:
            result = conn.execute(sql, (pack_uid,)).fetchone()
            if result:
                return self._dict_to_entity(dict(result))
            return None


class PackItemRepository(JsonFieldRepository[PackItem, int]):
    """整合包清单条目Repository"""
    
    def __init__(self, db_manager):
        super().__init__(
            db_manager=db_manager,
            table_name="core_pack_items",
            json_fields=["constraints"], 
            entity_class=PackItem
        )
    
    async def find_by_pack_version(self, pack_version_uid: str) -> List[PackItem]:
        """根据整合包版本UID查找清单条目"""
        sql = """
        SELECT * FROM core_pack_items 
        WHERE pack_version_uid = ? 
        ORDER BY position, created_at
        """
        
        with self.db_manager.get_connection() as conn:
            results = conn.execute(sql, (pack_version_uid,)).fetchall()
            return [self._dict_to_entity(dict(row)) for row in results]
    
    async def find_by_item_type(self, pack_version_uid: str, item_type: str) -> List[PackItem]:
        """根据条目类型查找清单条目"""
        return await self.find_by(pack_version_uid=pack_version_uid, item_type=item_type)
    
    async def find_mods(self, pack_version_uid: str) -> List[PackItem]:
        """查找MOD条目"""
        return await self.find_by_item_type(pack_version_uid, "mod")
    
    async def get_max_position(self, pack_version_uid: str) -> int:
        """获取最大位置序号"""
        sql = """
        SELECT COALESCE(MAX(position), 0) as max_pos 
        FROM core_pack_items 
        WHERE pack_version_uid = ?
        """
        
        with self.db_manager.get_connection() as conn:
            result = conn.execute(sql, (pack_version_uid,)).fetchone()
            return result['max_pos']


class PackInstallationRepository(JsonFieldRepository[PackInstallation, int]):
    """整合包本地实例Repository"""
    
    def __init__(self, db_manager):
        super().__init__(
            db_manager=db_manager,
            table_name="core_pack_installations",
            entity_class=PackInstallation
        )
    
    async def find_by_pack_version(self, pack_version_uid: str) -> List[PackInstallation]:
        """根据整合包版本UID查找实例"""
        return await self.find_by(pack_version_uid=pack_version_uid)
    
    async def find_enabled(self) -> List[PackInstallation]:
        """查找已启用的实例"""
        return await self.find_by(enabled=True)
    
    async def find_by_launcher(self, launcher: str) -> List[PackInstallation]:
        """根据启动器查找实例"""
        return await self.find_by(launcher=launcher)
    
    async def get_by_path(self, root_path: str) -> Optional[PackInstallation]:
        """根据路径获取实例"""
        return await self.find_one_by(root_path=root_path)
    
    async def disable_all_for_pack_version(self, pack_version_uid: str) -> int:
        """禁用某个整合包版本的所有实例"""
        sql = """
        UPDATE core_pack_installations 
        SET enabled = FALSE, updated_at = ? 
        WHERE pack_version_uid = ? AND enabled = TRUE
        """
        
        with self.db_manager.get_connection() as conn:
            cursor = conn.execute(sql, (self._get_timestamp(), pack_version_uid))
            return cursor.rowcount