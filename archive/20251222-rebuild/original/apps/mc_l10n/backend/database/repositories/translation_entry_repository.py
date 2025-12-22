#!/usr/bin/env python
"""
翻译条目Repository
提供翻译条目相关的数据访问操作
"""

from typing import List, Optional, Dict, Any, Tuple
from dataclasses import dataclass, asdict
from packages.core.data.repositories.base_repository import JsonFieldRepository
from services.uida_service import get_uida_service
import structlog

logger = structlog.get_logger(__name__)


@dataclass
class TranslationEntry:
    """翻译条目实体"""
    uid: str = None
    language_file_uid: str = None
    key: str = None
    src_text: str = None
    dst_text: str = ""
    status: str = "new"  # new, mt, reviewed, locked, rejected, conflict
    qa_flags: Dict[str, Any] = None
    updated_at: str = None
    uida_keys_b64: Optional[str] = None
    uida_hash: Optional[str] = None
    id: int = None
    created_at: Optional[str] = None  # 添加created_at字段
    
    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)
    
    def __post_init__(self):
        if self.qa_flags is None:
            self.qa_flags = {}


class TranslationEntryRepository(JsonFieldRepository[TranslationEntry, int]):
    """翻译条目Repository"""
    
    def __init__(self, db_manager):
        super().__init__(
            db_manager=db_manager,
            table_name="core_translation_entries",
            json_fields=["qa_flags"],
            entity_class=TranslationEntry
        )
        self.uida_service = get_uida_service()
    
    async def find_by_id(self, entry_uid: str) -> Optional[TranslationEntry]:
        """根据UID查找翻译条目"""
        return await self.find_one_by(uid=entry_uid)
    
    async def find_by_language_file(self, language_file_uid: str) -> List[TranslationEntry]:
        """根据语言文件UID查找翻译条目"""
        sql = """
        SELECT * FROM core_translation_entries 
        WHERE language_file_uid = ? 
        ORDER BY key
        """
        
        with self.db_manager.get_connection() as conn:
            results = conn.execute(sql, (language_file_uid,)).fetchall()
            return [self._dict_to_entity(dict(row)) for row in results]
    
    async def find_by_status(self, status: str) -> List[TranslationEntry]:
        """根据状态查找翻译条目"""
        return await self.find_by(status=status)
    
    async def find_by_key_pattern(self, key_pattern: str) -> List[TranslationEntry]:
        """根据键模式查找翻译条目"""
        sql = """
        SELECT * FROM core_translation_entries 
        WHERE key LIKE ? 
        ORDER BY key
        """
        
        with self.db_manager.get_connection() as conn:
            results = conn.execute(sql, (f"%{key_pattern}%",)).fetchall()
            return [self._dict_to_entity(dict(row)) for row in results]
    
    async def get_entry_by_key(self, language_file_uid: str, key: str) -> Optional[TranslationEntry]:
        """根据键获取翻译条目"""
        return await self.find_one_by(language_file_uid=language_file_uid, key=key)
    
    async def find_untranslated(self, language_file_uid: str = None) -> List[TranslationEntry]:
        """查找未翻译的条目"""
        conditions = ["(dst_text IS NULL OR dst_text = '')"]
        params = []
        
        if language_file_uid:
            conditions.append("language_file_uid = ?")
            params.append(language_file_uid)
        
        where_clause = " AND ".join(conditions)
        sql = f"""
        SELECT * FROM core_translation_entries 
        WHERE {where_clause}
        ORDER BY updated_at DESC
        """
        
        with self.db_manager.get_connection() as conn:
            results = conn.execute(sql, params).fetchall()
            return [self._dict_to_entity(dict(row)) for row in results]
    
    async def find_needs_review(self, language_file_uid: str = None) -> List[TranslationEntry]:
        """查找需要审核的条目"""
        conditions = ["status IN ('new', 'mt')"]
        params = []
        
        if language_file_uid:
            conditions.append("language_file_uid = ?")
            params.append(language_file_uid)
        
        where_clause = " AND ".join(conditions)
        sql = f"""
        SELECT * FROM core_translation_entries 
        WHERE {where_clause}
        ORDER BY updated_at DESC
        """
        
        with self.db_manager.get_connection() as conn:
            results = conn.execute(sql, params).fetchall()
            return [self._dict_to_entity(dict(row)) for row in results]
    
    async def get_translation_progress(self, language_file_uid: str = None) -> Dict[str, Any]:
        """获取翻译进度统计"""
        conditions = []
        params = []
        
        if language_file_uid:
            conditions.append("language_file_uid = ?")
            params.append(language_file_uid)
        
        where_clause = " AND ".join(conditions) if conditions else "1=1"
        sql = f"""
        SELECT 
            COUNT(*) as total,
            SUM(CASE WHEN status = 'new' THEN 1 ELSE 0 END) as new_count,
            SUM(CASE WHEN status = 'mt' THEN 1 ELSE 0 END) as mt_count,
            SUM(CASE WHEN status = 'reviewed' THEN 1 ELSE 0 END) as reviewed_count,
            SUM(CASE WHEN status = 'locked' THEN 1 ELSE 0 END) as locked_count,
            SUM(CASE WHEN status = 'rejected' THEN 1 ELSE 0 END) as rejected_count,
            SUM(CASE WHEN status = 'conflict' THEN 1 ELSE 0 END) as conflict_count,
            SUM(CASE WHEN dst_text IS NOT NULL AND dst_text != '' THEN 1 ELSE 0 END) as translated_count
        FROM core_translation_entries
        WHERE {where_clause}
        """
        
        with self.db_manager.get_connection() as conn:
            result = conn.execute(sql, params).fetchone()
            
            if not result:
                return {}
            
            stats = dict(result)
            
            # 计算百分比
            total = stats['total']
            if total > 0:
                stats['completion_rate'] = round(stats['translated_count'] / total * 100, 2)
                stats['review_rate'] = round((stats['reviewed_count'] + stats['locked_count']) / total * 100, 2)
            else:
                stats['completion_rate'] = 0
                stats['review_rate'] = 0
            
            return stats
    
    async def get_status_distribution(self) -> Dict[str, int]:
        """获取状态分布统计"""
        sql = """
        SELECT status, COUNT(*) as count
        FROM core_translation_entries
        GROUP BY status
        ORDER BY count DESC
        """
        
        with self.db_manager.get_connection() as conn:
            results = conn.execute(sql).fetchall()
            return {row['status']: row['count'] for row in results}
    
    async def find_qa_issues(self, qa_flag: str = None) -> List[TranslationEntry]:
        """查找质量问题条目"""
        if qa_flag:
            sql = """
            SELECT * FROM core_translation_entries 
            WHERE json_extract(qa_flags, ?) IS NOT NULL
            ORDER BY updated_at DESC
            """
            params = [f'$.{qa_flag}']
        else:
            sql = """
            SELECT * FROM core_translation_entries 
            WHERE qa_flags != '{}' AND qa_flags IS NOT NULL
            ORDER BY updated_at DESC
            """
            params = []
        
        with self.db_manager.get_connection() as conn:
            results = conn.execute(sql, params).fetchall()
            return [self._dict_to_entity(dict(row)) for row in results]
    
    async def batch_update_status(self, entry_uids: List[str], status: str) -> int:
        """批量更新状态"""
        if not entry_uids:
            return 0
        
        placeholders = ', '.join(['?' for _ in entry_uids])
        sql = f"""
        UPDATE core_translation_entries 
        SET status = ?, updated_at = ? 
        WHERE uid IN ({placeholders})
        """
        
        params = [status, self._get_timestamp()] + entry_uids
        
        with self.db_manager.get_connection() as conn:
            cursor = conn.execute(sql, params)
            return cursor.rowcount
    
    async def batch_update_translations(self, translations: List[Tuple[str, str]]) -> int:
        """批量更新翻译内容"""
        if not translations:
            return 0
        
        updated_count = 0
        now = self._get_timestamp()
        
        with self.db_manager.get_connection() as conn:
            for uid, dst_text in translations:
                cursor = conn.execute("""
                    UPDATE core_translation_entries 
                    SET dst_text = ?, status = 'mt', updated_at = ? 
                    WHERE uid = ?
                """, (dst_text, now, uid))
                
                if cursor.rowcount > 0:
                    updated_count += 1
        
        return updated_count
    
    async def find_similar_translations(self, src_text: str, similarity_threshold: float = 0.8) -> List[TranslationEntry]:
        """查找相似的翻译条目（基于源文本）"""
        # 简单的相似性查找，基于长度和包含关系
        # 实际实现可以使用更复杂的相似性算法
        
        sql = """
        SELECT * FROM core_translation_entries 
        WHERE src_text LIKE ? 
        AND dst_text IS NOT NULL 
        AND dst_text != ''
        ORDER BY 
            CASE 
                WHEN src_text = ? THEN 0
                WHEN LENGTH(src_text) = LENGTH(?) THEN 1
                ELSE 2
            END,
            updated_at DESC
        LIMIT 10
        """
        
        pattern = f"%{src_text[:20]}%"  # 使用前20个字符作为模糊匹配
        params = [pattern, src_text, src_text]
        
        with self.db_manager.get_connection() as conn:
            results = conn.execute(sql, params).fetchall()
            return [self._dict_to_entity(dict(row)) for row in results]
    
    async def get_recent_updates(self, limit: int = 50) -> List[TranslationEntry]:
        """获取最近更新的条目"""
        sql = f"""
        SELECT * FROM core_translation_entries 
        ORDER BY updated_at DESC 
        LIMIT ?
        """
        
        with self.db_manager.get_connection() as conn:
            results = conn.execute(sql, (limit,)).fetchall()
            return [self._dict_to_entity(dict(row)) for row in results]
    
    async def find_long_translations(self, min_length: int = 100) -> List[TranslationEntry]:
        """查找长翻译文本"""
        sql = f"""
        SELECT * FROM core_translation_entries 
        WHERE LENGTH(dst_text) >= ?
        ORDER BY LENGTH(dst_text) DESC
        """
        
        with self.db_manager.get_connection() as conn:
            results = conn.execute(sql, (min_length,)).fetchall()
            return [self._dict_to_entity(dict(row)) for row in results]
    
    async def get_translator_statistics(self) -> Dict[str, Any]:
        """获取翻译统计信息"""
        sql = """
        SELECT 
            COUNT(*) as total_entries,
            COUNT(DISTINCT language_file_uid) as unique_files,
            AVG(LENGTH(src_text)) as avg_src_length,
            AVG(LENGTH(dst_text)) as avg_dst_length,
            MIN(updated_at) as earliest_update,
            MAX(updated_at) as latest_update
        FROM core_translation_entries
        WHERE dst_text IS NOT NULL AND dst_text != ''
        """
        
        with self.db_manager.get_connection() as conn:
            result = conn.execute(sql).fetchone()
            return dict(result) if result else {}
    
    async def find_duplicates(self) -> List[Dict[str, Any]]:
        """查找重复的键值对"""
        sql = """
        SELECT language_file_uid, key, COUNT(*) as count
        FROM core_translation_entries
        GROUP BY language_file_uid, key
        HAVING COUNT(*) > 1
        ORDER BY count DESC
        """
        
        with self.db_manager.get_connection() as conn:
            results = conn.execute(sql).fetchall()
            return [dict(row) for row in results]
    
    # UIDA相关方法
    async def generate_and_set_uida(self, entry: TranslationEntry, mod_id: str, locale: str) -> TranslationEntry:
        """为翻译条目生成并设置UIDA"""
        try:
            uida_components = self.uida_service.generate_translation_entry_uida(
                mod_id=mod_id,
                translation_key=entry.key,
                locale=locale
            )
            
            entry.uida_keys_b64 = uida_components.keys_b64
            entry.uida_hash = uida_components.hash_hex
            
            logger.info("为翻译条目生成UIDA", 
                       entry_uid=entry.uid, 
                       key=entry.key[:50],
                       uida_hash=entry.uida_hash[:16])
            
            return entry
            
        except Exception as e:
            logger.error("生成UIDA失败", 
                        entry_uid=entry.uid, 
                        key=entry.key, 
                        error=str(e))
            return entry
    
    async def find_by_uida_hash(self, uida_hash: str) -> List[TranslationEntry]:
        """根据UIDA哈希查找翻译条目"""
        return await self.find_by(uida_hash=uida_hash)
    
    async def find_by_uida_keys(self, uida_keys_b64: str) -> List[TranslationEntry]:
        """根据UIDA键查找翻译条目"""
        return await self.find_by(uida_keys_b64=uida_keys_b64)
    
    async def find_uida_duplicates(self) -> List[Dict[str, Any]]:
        """查找UIDA重复的条目"""
        sql = """
        SELECT 
            uida_hash,
            COUNT(*) as duplicate_count,
            GROUP_CONCAT(uid) as entry_uids,
            MIN(updated_at) as first_created,
            MAX(updated_at) as last_updated
        FROM core_translation_entries 
        WHERE uida_hash IS NOT NULL
        GROUP BY uida_hash 
        HAVING COUNT(*) > 1
        ORDER BY duplicate_count DESC
        """
        
        with self.db_manager.get_connection() as conn:
            results = conn.execute(sql).fetchall()
            return [dict(row) for row in results]
    
    async def get_uida_coverage_stats(self) -> Dict[str, Any]:
        """获取UIDA覆盖率统计"""
        sql = """
        SELECT 
            COUNT(*) as total_entries,
            COUNT(uida_keys_b64) as entries_with_uida,
            COUNT(DISTINCT uida_hash) as unique_uida_count,
            ROUND(CAST(COUNT(uida_keys_b64) AS FLOAT) / COUNT(*) * 100, 2) as uida_coverage_percent
        FROM core_translation_entries
        """
        
        with self.db_manager.get_connection() as conn:
            result = conn.execute(sql).fetchone()
            return dict(result) if result else {}
    
    async def find_entries_without_uida(self, limit: int = 100) -> List[TranslationEntry]:
        """查找没有UIDA的翻译条目"""
        sql = f"""
        SELECT * FROM core_translation_entries 
        WHERE uida_keys_b64 IS NULL OR uida_hash IS NULL
        ORDER BY updated_at DESC
        LIMIT ?
        """
        
        with self.db_manager.get_connection() as conn:
            results = conn.execute(sql, (limit,)).fetchall()
            return [self._dict_to_entity(dict(row)) for row in results]
    
    async def batch_generate_uida(self, entries_with_metadata: List[Tuple[TranslationEntry, str, str]]) -> int:
        """批量生成UIDA"""
        updated_count = 0
        now = self._get_timestamp()
        
        with self.db_manager.get_connection() as conn:
            for entry, mod_id, locale in entries_with_metadata:
                try:
                    updated_entry = await self.generate_and_set_uida(entry, mod_id, locale)
                    
                    if updated_entry.uida_keys_b64 and updated_entry.uida_hash:
                        cursor = conn.execute("""
                            UPDATE core_translation_entries 
                            SET uida_keys_b64 = ?, uida_hash = ?, updated_at = ? 
                            WHERE uid = ?
                        """, (updated_entry.uida_keys_b64, updated_entry.uida_hash, now, entry.uid))
                        
                        if cursor.rowcount > 0:
                            updated_count += 1
                            
                except Exception as e:
                    logger.error("批量生成UIDA失败", entry_uid=entry.uid, error=str(e))
                    continue
        
        logger.info("批量生成UIDA完成", updated_count=updated_count, total_count=len(entries_with_metadata))
        return updated_count