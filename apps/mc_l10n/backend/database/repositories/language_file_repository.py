#!/usr/bin/env python
"""
语言文件Repository
提供语言文件相关的数据访问操作
"""

from typing import List, Optional, Dict, Any
from dataclasses import dataclass, asdict
from packages.core.data.repositories.base_repository import BaseRepository
from services.uida_service import get_uida_service
import structlog

logger = structlog.get_logger(__name__)


@dataclass
class LanguageFile:
    """语言文件实体"""
    uid: str = None
    carrier_type: str = None  # mod, resource_pack, data_pack, override
    carrier_uid: str = None
    locale: str = None
    rel_path: str = None
    format: str = None  # json, lang, properties
    size: int = 0
    discovered_at: str = None
    uida_keys_b64: Optional[str] = None
    uida_hash: Optional[str] = None
    id: int = None
    
    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


class LanguageFileRepository(BaseRepository[LanguageFile, int]):
    """语言文件Repository"""
    
    def __init__(self, db_manager):
        super().__init__(
            db_manager=db_manager,
            table_name="core_language_files",
            entity_class=LanguageFile
        )
        self.uida_service = get_uida_service()
    
    async def find_by_carrier(self, carrier_type: str, carrier_uid: str) -> List[LanguageFile]:
        """根据载体查找语言文件"""
        return await self.find_by(carrier_type=carrier_type, carrier_uid=carrier_uid)
    
    async def find_by_locale(self, locale: str) -> List[LanguageFile]:
        """根据语言代码查找语言文件"""
        return await self.find_by(locale=locale)
    
    async def find_by_format(self, format: str) -> List[LanguageFile]:
        """根据文件格式查找语言文件"""
        return await self.find_by(format=format)
    
    async def find_mod_language_files(self, mod_uid: str, locale: str = None) -> List[LanguageFile]:
        """查找MOD的语言文件"""
        conditions = {
            "carrier_type": "mod",
            "carrier_uid": mod_uid
        }
        
        if locale:
            conditions["locale"] = locale
        
        return await self.find_by(**conditions)
    
    async def get_language_file_by_path(self, carrier_uid: str, locale: str, rel_path: str) -> Optional[LanguageFile]:
        """根据路径获取语言文件"""
        return await self.find_one_by(
            carrier_uid=carrier_uid,
            locale=locale,
            rel_path=rel_path
        )
    
    async def get_supported_locales(self, carrier_type: str = None, carrier_uid: str = None) -> List[str]:
        """获取支持的语言列表"""
        conditions = []
        params = []
        
        if carrier_type:
            conditions.append("carrier_type = ?")
            params.append(carrier_type)
        
        if carrier_uid:
            conditions.append("carrier_uid = ?")
            params.append(carrier_uid)
        
        where_clause = " AND ".join(conditions) if conditions else "1=1"
        sql = f"""
        SELECT DISTINCT locale 
        FROM core_language_files 
        WHERE {where_clause}
        ORDER BY locale
        """
        
        with self.db_manager.get_connection() as conn:
            results = conn.execute(sql, params).fetchall()
            return [row['locale'] for row in results]
    
    async def get_carrier_stats(self, carrier_type: str = None) -> Dict[str, Any]:
        """获取载体统计信息"""
        conditions = []
        params = []
        
        if carrier_type:
            conditions.append("carrier_type = ?")
            params.append(carrier_type)
        
        where_clause = " AND ".join(conditions) if conditions else "1=1"
        sql = f"""
        SELECT 
            carrier_type,
            COUNT(*) as file_count,
            COUNT(DISTINCT carrier_uid) as unique_carriers,
            COUNT(DISTINCT locale) as unique_locales,
            SUM(size) as total_size,
            AVG(size) as avg_size
        FROM core_language_files 
        WHERE {where_clause}
        GROUP BY carrier_type
        ORDER BY file_count DESC
        """
        
        with self.db_manager.get_connection() as conn:
            results = conn.execute(sql, params).fetchall()
            
            stats = {}
            for row in results:
                stats[row['carrier_type']] = {
                    'file_count': row['file_count'],
                    'unique_carriers': row['unique_carriers'],
                    'unique_locales': row['unique_locales'],
                    'total_size': row['total_size'],
                    'avg_size': round(row['avg_size'], 2) if row['avg_size'] else 0
                }
            
            return stats
    
    async def get_locale_coverage(self, carrier_type: str = None) -> Dict[str, Dict[str, Any]]:
        """获取语言覆盖率统计"""
        conditions = []
        params = []
        
        if carrier_type:
            conditions.append("carrier_type = ?")
            params.append(carrier_type)
        
        where_clause = " AND ".join(conditions) if conditions else "1=1"
        sql = f"""
        SELECT 
            locale,
            COUNT(*) as file_count,
            COUNT(DISTINCT carrier_uid) as carrier_count,
            SUM(size) as total_size,
            COUNT(DISTINCT format) as format_count
        FROM core_language_files 
        WHERE {where_clause}
        GROUP BY locale
        ORDER BY file_count DESC
        """
        
        with self.db_manager.get_connection() as conn:
            results = conn.execute(sql, params).fetchall()
            
            coverage = {}
            for row in results:
                coverage[row['locale']] = {
                    'file_count': row['file_count'],
                    'carrier_count': row['carrier_count'],
                    'total_size': row['total_size'],
                    'format_count': row['format_count']
                }
            
            return coverage
    
    async def get_format_distribution(self) -> Dict[str, int]:
        """获取文件格式分布"""
        sql = """
        SELECT format, COUNT(*) as count
        FROM core_language_files
        GROUP BY format
        ORDER BY count DESC
        """
        
        with self.db_manager.get_connection() as conn:
            results = conn.execute(sql).fetchall()
            return {row['format']: row['count'] for row in results}
    
    async def find_large_files(self, min_size: int = 10000) -> List[LanguageFile]:
        """查找大文件"""
        sql = f"""
        SELECT * FROM core_language_files 
        WHERE size >= ?
        ORDER BY size DESC
        """
        
        with self.db_manager.get_connection() as conn:
            results = conn.execute(sql, (min_size,)).fetchall()
            return [self._dict_to_entity(dict(row)) for row in results]
    
    async def find_empty_files(self) -> List[LanguageFile]:
        """查找空文件"""
        return await self.find_by(size=0)
    
    async def get_recent_discoveries(self, limit: int = 50) -> List[LanguageFile]:
        """获取最近发现的文件"""
        sql = f"""
        SELECT * FROM core_language_files 
        ORDER BY discovered_at DESC 
        LIMIT ?
        """
        
        with self.db_manager.get_connection() as conn:
            results = conn.execute(sql, (limit,)).fetchall()
            return [self._dict_to_entity(dict(row)) for row in results]
    
    async def get_carrier_localization_status(self, carrier_uid: str) -> Dict[str, Any]:
        """获取载体本地化状态"""
        sql = """
        SELECT 
            locale,
            COUNT(*) as file_count,
            SUM(size) as total_size,
            COUNT(DISTINCT format) as format_count
        FROM core_language_files 
        WHERE carrier_uid = ?
        GROUP BY locale
        ORDER BY file_count DESC
        """
        
        with self.db_manager.get_connection() as conn:
            results = conn.execute(sql, (carrier_uid,)).fetchall()
            
            status = {}
            for row in results:
                status[row['locale']] = {
                    'file_count': row['file_count'],
                    'total_size': row['total_size'],
                    'format_count': row['format_count']
                }
            
            return status
    
    # UIDA相关方法
    async def generate_and_set_uida(self, language_file: LanguageFile) -> LanguageFile:
        """为语言文件生成并设置UIDA"""
        try:
            uida_components = self.uida_service.generate_language_file_uida(
                carrier_type=language_file.carrier_type,
                carrier_uid=language_file.carrier_uid,
                locale=language_file.locale,
                file_path=language_file.rel_path
            )
            
            language_file.uida_keys_b64 = uida_components.keys_b64
            language_file.uida_hash = uida_components.hash_hex
            
            logger.info("为语言文件生成UIDA",
                       file_uid=language_file.uid,
                       carrier_type=language_file.carrier_type,
                       locale=language_file.locale,
                       uida_hash=language_file.uida_hash[:16])
            
            return language_file
            
        except Exception as e:
            logger.error("生成语言文件UIDA失败",
                        file_uid=language_file.uid,
                        carrier_uid=language_file.carrier_uid,
                        locale=language_file.locale,
                        error=str(e))
            return language_file
    
    async def find_by_uida_hash(self, uida_hash: str) -> List[LanguageFile]:
        """根据UIDA SHA256查找语言文件"""
        return await self.find_by(uida_hash=uida_hash)
    
    async def find_by_uida_keys(self, uida_keys_b64: str) -> List[LanguageFile]:
        """根据UIDA键查找语言文件"""
        return await self.find_by(uida_keys_b64=uida_keys_b64)
    
    async def get_uida_coverage_stats(self) -> Dict[str, Any]:
        """获取语言文件UIDA覆盖率统计"""
        sql = """
        SELECT 
            COUNT(*) as total_files,
            COUNT(uida_keys_b64) as files_with_uida,
            COUNT(DISTINCT uida_hash) as unique_uida_count,
            ROUND(CAST(COUNT(uida_keys_b64) AS FLOAT) / COUNT(*) * 100, 2) as uida_coverage_percent
        FROM core_language_files
        """
        
        with self.db_manager.get_connection() as conn:
            result = conn.execute(sql).fetchone()
            return dict(result) if result else {}
    
    async def find_files_without_uida(self, limit: int = 100) -> List[LanguageFile]:
        """查找没有UIDA的语言文件"""
        sql = f"""
        SELECT * FROM core_language_files 
        WHERE uida_keys_b64 IS NULL OR uida_hash IS NULL
        ORDER BY discovered_at DESC
        LIMIT ?
        """
        
        with self.db_manager.get_connection() as conn:
            results = conn.execute(sql, (limit,)).fetchall()
            return [self._dict_to_entity(dict(row)) for row in results]
    
    async def batch_generate_uida(self, language_files: List[LanguageFile]) -> int:
        """批量生成语言文件UIDA"""
        updated_count = 0
        now = self._get_timestamp()
        
        with self.db_manager.get_connection() as conn:
            for language_file in language_files:
                try:
                    updated_file = await self.generate_and_set_uida(language_file)
                    
                    if updated_file.uida_keys_b64 and updated_file.uida_hash:
                        cursor = conn.execute("""
                            UPDATE core_language_files 
                            SET uida_keys_b64 = ?, uida_hash = ?, discovered_at = ? 
                            WHERE uid = ?
                        """, (updated_file.uida_keys_b64, updated_file.uida_hash, now, language_file.uid))
                        
                        if cursor.rowcount > 0:
                            updated_count += 1
                            
                except Exception as e:
                    logger.error("批量生成语言文件UIDA失败", file_uid=language_file.uid, error=str(e))
                    continue
        
        logger.info("批量生成语言文件UIDA完成", updated_count=updated_count, total_count=len(language_files))
        return updated_count