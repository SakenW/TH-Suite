"""
V5架构 - 翻译条目Repository
管理core_translation_entries表的数据访问
"""

import uuid
from datetime import datetime
from typing import Optional, List, Dict, Any
from dataclasses import dataclass

from .base_repository import BaseRepository


@dataclass
class CoreTranslationEntry:
    """核心翻译条目实体"""
    uid: str
    language_file_uid: str
    key: str
    src_text: str
    dst_text: str = ""
    status: str = "new"  # new, mt, reviewed, locked, rejected, conflict
    qa_flags: str = "{}"  # JSON格式的质检标记
    updated_at: Optional[str] = None
    id: Optional[int] = None


class CoreTranslationEntryRepository(BaseRepository[CoreTranslationEntry]):
    """翻译条目Repository实现"""
    
    def table_name(self) -> str:
        return "core_translation_entries"
    
    def create(self, entity: CoreTranslationEntry) -> str:
        """创建翻译条目"""
        if not entity.uid:
            entity.uid = str(uuid.uuid4())
        
        query = """
            INSERT INTO core_translation_entries (
                uid, language_file_uid, key, src_text, dst_text, status, qa_flags
            )
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """
        self.execute_write(query, (
            entity.uid, entity.language_file_uid, entity.key,
            entity.src_text, entity.dst_text, entity.status, entity.qa_flags
        ))
        return entity.uid
    
    def get_by_uid(self, uid: str) -> Optional[CoreTranslationEntry]:
        """根据UID获取翻译条目"""
        query = """
            SELECT id, uid, language_file_uid, key, src_text, dst_text, 
                   status, qa_flags, updated_at
            FROM core_translation_entries 
            WHERE uid = ?
        """
        row = self.execute_single(query, (uid,))
        return self._row_to_entity(row) if row else None
    
    def update(self, entity: CoreTranslationEntry) -> bool:
        """更新翻译条目"""
        query = """
            UPDATE core_translation_entries 
            SET language_file_uid = ?, key = ?, src_text = ?, dst_text = ?, 
                status = ?, qa_flags = ?, updated_at = datetime('now')
            WHERE uid = ?
        """
        affected = self.execute_write(query, (
            entity.language_file_uid, entity.key, entity.src_text,
            entity.dst_text, entity.status, entity.qa_flags, entity.uid
        ))
        return affected > 0
    
    def delete_by_uid(self, uid: str) -> bool:
        """删除翻译条目"""
        query = "DELETE FROM core_translation_entries WHERE uid = ?"
        affected = self.execute_write(query, (uid,))
        return affected > 0
    
    def list_all(self, limit: Optional[int] = None, offset: int = 0) -> List[CoreTranslationEntry]:
        """列出所有翻译条目"""
        query = """
            SELECT id, uid, language_file_uid, key, src_text, dst_text, 
                   status, qa_flags, updated_at
            FROM core_translation_entries 
            ORDER BY updated_at DESC
        """
        if limit:
            query += f" LIMIT {limit} OFFSET {offset}"
        
        rows = self.execute_query(query)
        return [self._row_to_entity(row) for row in rows]
    
    def get_by_language_file(self, language_file_uid: str) -> List[CoreTranslationEntry]:
        """根据语言文件UID获取翻译条目"""
        query = """
            SELECT id, uid, language_file_uid, key, src_text, dst_text, 
                   status, qa_flags, updated_at
            FROM core_translation_entries 
            WHERE language_file_uid = ?
            ORDER BY key
        """
        rows = self.execute_query(query, (language_file_uid,))
        return [self._row_to_entity(row) for row in rows]
    
    def find_by_key(self, language_file_uid: str, key: str) -> Optional[CoreTranslationEntry]:
        """根据语言文件和键查找翻译条目"""
        query = """
            SELECT id, uid, language_file_uid, key, src_text, dst_text, 
                   status, qa_flags, updated_at
            FROM core_translation_entries 
            WHERE language_file_uid = ? AND key = ?
        """
        row = self.execute_single(query, (language_file_uid, key))
        return self._row_to_entity(row) if row else None
    
    def upsert_entry(self, entity: CoreTranslationEntry) -> str:
        """插入或更新翻译条目（基于language_file_uid + key的唯一性）"""
        existing = self.find_by_key(entity.language_file_uid, entity.key)
        
        if existing:
            # 更新现有条目
            entity.uid = existing.uid
            self.update(entity)
            return existing.uid
        else:
            # 创建新条目
            return self.create(entity)
    
    def batch_upsert(self, entries: List[CoreTranslationEntry]) -> Dict[str, Any]:
        """批量插入或更新翻译条目"""
        created_count = 0
        updated_count = 0
        
        with self.get_transaction() as conn:
            cursor = conn.cursor()
            
            for entry in entries:
                # 检查是否存在
                cursor.execute(
                    "SELECT uid FROM core_translation_entries WHERE language_file_uid = ? AND key = ?",
                    (entry.language_file_uid, entry.key)
                )
                existing = cursor.fetchone()
                
                if existing:
                    # 更新
                    cursor.execute("""
                        UPDATE core_translation_entries 
                        SET src_text = ?, dst_text = ?, status = ?, qa_flags = ?, updated_at = datetime('now')
                        WHERE language_file_uid = ? AND key = ?
                    """, (
                        entry.src_text, entry.dst_text, entry.status, entry.qa_flags,
                        entry.language_file_uid, entry.key
                    ))
                    updated_count += 1
                else:
                    # 插入
                    if not entry.uid:
                        entry.uid = str(uuid.uuid4())
                    
                    cursor.execute("""
                        INSERT INTO core_translation_entries (
                            uid, language_file_uid, key, src_text, dst_text, status, qa_flags
                        ) VALUES (?, ?, ?, ?, ?, ?, ?)
                    """, (
                        entry.uid, entry.language_file_uid, entry.key,
                        entry.src_text, entry.dst_text, entry.status, entry.qa_flags
                    ))
                    created_count += 1
        
        return {
            "created": created_count,
            "updated": updated_count,
            "total": created_count + updated_count
        }
    
    def get_by_status(self, status: str) -> List[CoreTranslationEntry]:
        """根据状态获取翻译条目"""
        query = """
            SELECT id, uid, language_file_uid, key, src_text, dst_text, 
                   status, qa_flags, updated_at
            FROM core_translation_entries 
            WHERE status = ?
            ORDER BY updated_at DESC
        """
        rows = self.execute_query(query, (status,))
        return [self._row_to_entity(row) for row in rows]
    
    def search_by_text(self, search_text: str, search_in: str = "both") -> List[CoreTranslationEntry]:
        """根据文本搜索翻译条目"""
        if search_in == "source":
            query = """
                SELECT id, uid, language_file_uid, key, src_text, dst_text, 
                       status, qa_flags, updated_at
                FROM core_translation_entries 
                WHERE src_text LIKE ?
                ORDER BY key
            """
        elif search_in == "target":
            query = """
                SELECT id, uid, language_file_uid, key, src_text, dst_text, 
                       status, qa_flags, updated_at
                FROM core_translation_entries 
                WHERE dst_text LIKE ?
                ORDER BY key
            """
        else:  # both
            query = """
                SELECT id, uid, language_file_uid, key, src_text, dst_text, 
                       status, qa_flags, updated_at
                FROM core_translation_entries 
                WHERE src_text LIKE ? OR dst_text LIKE ?
                ORDER BY key
            """
        
        search_pattern = f"%{search_text}%"
        params = (search_pattern, search_pattern) if search_in == "both" else (search_pattern,)
        
        rows = self.execute_query(query, params)
        return [self._row_to_entity(row) for row in rows]
    
    def get_statistics(self) -> Dict[str, Any]:
        """获取翻译条目统计信息"""
        stats = {}
        
        # 按状态统计
        query = """
            SELECT status, COUNT(*) as count
            FROM core_translation_entries 
            GROUP BY status
        """
        rows = self.execute_query(query)
        stats['by_status'] = {row['status']: row['count'] for row in rows}
        
        # 总数统计
        stats['total_entries'] = self.count()
        
        # 已翻译条目统计
        query = """
            SELECT COUNT(*) as count
            FROM core_translation_entries 
            WHERE dst_text IS NOT NULL AND dst_text != ''
        """
        row = self.execute_single(query)
        stats['translated_count'] = row['count'] if row else 0
        
        # 计算翻译完成率
        if stats['total_entries'] > 0:
            stats['completion_rate'] = stats['translated_count'] / stats['total_entries']
        else:
            stats['completion_rate'] = 0
        
        return stats
    
    def delete_by_language_file(self, language_file_uid: str) -> int:
        """删除指定语言文件的所有翻译条目"""
        query = "DELETE FROM core_translation_entries WHERE language_file_uid = ?"
        return self.execute_write(query, (language_file_uid,))
    
    def cleanup_orphaned_entries(self) -> int:
        """清理孤立的翻译条目（语言文件不存在的条目）"""
        query = """
            DELETE FROM core_translation_entries 
            WHERE language_file_uid NOT IN (
                SELECT uid FROM core_language_files
            )
        """
        return self.execute_write(query)
    
    def _row_to_entity(self, row) -> CoreTranslationEntry:
        """将数据库行转换为实体"""
        return CoreTranslationEntry(
            id=row['id'],
            uid=row['uid'],
            language_file_uid=row['language_file_uid'],
            key=row['key'],
            src_text=row['src_text'],
            dst_text=row['dst_text'] or "",
            status=row['status'],
            qa_flags=row['qa_flags'] or "{}",
            updated_at=row['updated_at']
        )