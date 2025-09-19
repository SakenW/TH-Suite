"""
CAS键集缓存服务
基于内容寻址存储(CAS)实现键集指纹的缓存和优化
支持增量提取和性能优化
"""

import hashlib
import json
import sqlite3
import structlog
import time
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Any, Optional, Set, Tuple

logger = structlog.get_logger(__name__)


class CasKeysetCacheService:
    """CAS键集缓存服务"""
    
    def __init__(self, db_path: str = "data/mc_l10n.db"):
        self.db_path = Path(db_path)
        self._ensure_cache_tables()
        
        logger.info("CAS键集缓存服务已初始化")
    
    def _ensure_cache_tables(self):
        """确保缓存表存在"""
        try:
            with sqlite3.connect(str(self.db_path)) as conn:
                cursor = conn.cursor()
                
                # 创建键集缓存表
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS cache_keyset_fingerprints (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        content_hash TEXT UNIQUE NOT NULL,
                        carrier_uid TEXT NOT NULL,
                        relative_path TEXT NOT NULL,
                        locale TEXT NOT NULL,
                        keyset_hash TEXT NOT NULL,
                        key_count INTEGER DEFAULT 0,
                        keys_json TEXT CHECK(json_valid(keys_json)),
                        last_accessed TEXT NOT NULL DEFAULT (datetime('now')),
                        created_at TEXT NOT NULL DEFAULT (datetime('now')),
                        UNIQUE(carrier_uid, relative_path, locale)
                    )
                """)
                
                # 创建CAS对象存储表（如果不存在）
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS ops_cas_objects (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        object_hash TEXT UNIQUE NOT NULL,
                        object_type TEXT NOT NULL,
                        size_bytes INTEGER DEFAULT 0,
                        content_json TEXT CHECK(json_valid(content_json)),
                        metadata_json TEXT CHECK(json_valid(metadata_json)) DEFAULT '{}',
                        created_at TEXT NOT NULL DEFAULT (datetime('now')),
                        accessed_at TEXT NOT NULL DEFAULT (datetime('now'))
                    )
                """)
                
                # 创建性能优化索引
                cursor.execute("CREATE INDEX IF NOT EXISTS idx_keyset_carrier_path ON cache_keyset_fingerprints(carrier_uid, relative_path)")
                cursor.execute("CREATE INDEX IF NOT EXISTS idx_keyset_hash ON cache_keyset_fingerprints(keyset_hash)")
                cursor.execute("CREATE INDEX IF NOT EXISTS idx_cas_hash ON ops_cas_objects(object_hash)")
                cursor.execute("CREATE INDEX IF NOT EXISTS idx_cas_type ON ops_cas_objects(object_type)")
                
                conn.commit()
                
        except Exception as e:
            logger.error(f"缓存表初始化失败: {e}")
    
    async def get_keyset_fingerprint(
        self, 
        carrier_uid: str, 
        relative_path: str, 
        locale: str
    ) -> Optional[Dict[str, Any]]:
        """获取键集指纹"""
        try:
            with sqlite3.connect(str(self.db_path)) as conn:
                conn.row_factory = sqlite3.Row
                cursor = conn.cursor()
                
                cursor.execute("""
                    SELECT content_hash, keyset_hash, key_count, keys_json, 
                           last_accessed, created_at
                    FROM cache_keyset_fingerprints
                    WHERE carrier_uid = ? AND relative_path = ? AND locale = ?
                """, (carrier_uid, relative_path, locale))
                
                row = cursor.fetchone()
                if row:
                    # 更新访问时间
                    cursor.execute("""
                        UPDATE cache_keyset_fingerprints 
                        SET last_accessed = datetime('now')
                        WHERE carrier_uid = ? AND relative_path = ? AND locale = ?
                    """, (carrier_uid, relative_path, locale))
                    conn.commit()
                    
                    return {
                        "content_hash": row["content_hash"],
                        "keyset_hash": row["keyset_hash"],
                        "key_count": row["key_count"],
                        "keys": json.loads(row["keys_json"]) if row["keys_json"] else [],
                        "last_accessed": row["last_accessed"],
                        "created_at": row["created_at"]
                    }
                
                return None
                
        except Exception as e:
            logger.error(f"键集指纹获取失败: {e}")
            return None
    
    async def store_keyset_fingerprint(
        self, 
        carrier_uid: str, 
        relative_path: str, 
        locale: str,
        keys: List[str],
        content_hash: str = None
    ) -> str:
        """存储键集指纹"""
        try:
            # 计算键集哈希
            keyset_hash = self._calculate_keyset_hash(keys)
            
            # 如果没有提供内容哈希，使用键集哈希作为内容哈希
            if not content_hash:
                content_hash = keyset_hash
            
            with sqlite3.connect(str(self.db_path)) as conn:
                cursor = conn.cursor()
                
                # 插入或更新键集指纹
                cursor.execute("""
                    INSERT OR REPLACE INTO cache_keyset_fingerprints 
                    (content_hash, carrier_uid, relative_path, locale, keyset_hash, 
                     key_count, keys_json, last_accessed)
                    VALUES (?, ?, ?, ?, ?, ?, ?, datetime('now'))
                """, (
                    content_hash, carrier_uid, relative_path, locale, 
                    keyset_hash, len(keys), json.dumps(keys, ensure_ascii=False)
                ))
                
                conn.commit()
                
                logger.debug(f"键集指纹已存储: {carrier_uid}:{relative_path} ({len(keys)} 键)")
                return keyset_hash
                
        except Exception as e:
            logger.error(f"键集指纹存储失败: {e}")
            return ""
    
    async def check_keyset_changes(
        self, 
        carrier_uid: str, 
        relative_path: str, 
        locale: str,
        current_keys: List[str]
    ) -> Dict[str, Any]:
        """检查键集变化"""
        current_keyset_hash = self._calculate_keyset_hash(current_keys)
        
        # 获取缓存的指纹
        cached_fingerprint = await self.get_keyset_fingerprint(carrier_uid, relative_path, locale)
        
        if not cached_fingerprint:
            return {
                "has_changes": True,
                "change_type": "new",
                "current_hash": current_keyset_hash,
                "cached_hash": None,
                "added_keys": current_keys,
                "removed_keys": [],
                "key_count_change": len(current_keys)
            }
        
        cached_hash = cached_fingerprint["keyset_hash"]
        cached_keys = set(cached_fingerprint["keys"])
        current_keys_set = set(current_keys)
        
        if current_keyset_hash == cached_hash:
            return {
                "has_changes": False,
                "change_type": "none",
                "current_hash": current_keyset_hash,
                "cached_hash": cached_hash,
                "added_keys": [],
                "removed_keys": [],
                "key_count_change": 0
            }
        
        # 计算变更详情
        added_keys = list(current_keys_set - cached_keys)
        removed_keys = list(cached_keys - current_keys_set)
        
        change_type = "modified"
        if not cached_keys:
            change_type = "new"
        elif not current_keys_set:
            change_type = "deleted"
        
        return {
            "has_changes": True,
            "change_type": change_type,
            "current_hash": current_keyset_hash,
            "cached_hash": cached_hash,
            "added_keys": sorted(added_keys),
            "removed_keys": sorted(removed_keys),
            "key_count_change": len(current_keys) - len(cached_keys)
        }
    
    async def store_cas_object(
        self, 
        object_type: str, 
        content: Dict[str, Any],
        metadata: Dict[str, Any] = None
    ) -> str:
        """存储CAS对象"""
        try:
            # 计算对象哈希
            content_str = json.dumps(content, sort_keys=True, ensure_ascii=False)
            object_hash = hashlib.blake3(content_str.encode('utf-8')).hexdigest()
            
            if not metadata:
                metadata = {}
            
            with sqlite3.connect(str(self.db_path)) as conn:
                cursor = conn.cursor()
                
                # 检查对象是否已存在
                cursor.execute(
                    "SELECT object_hash FROM ops_cas_objects WHERE object_hash = ?",
                    (object_hash,)
                )
                
                if cursor.fetchone():
                    # 更新访问时间
                    cursor.execute("""
                        UPDATE ops_cas_objects 
                        SET accessed_at = datetime('now')
                        WHERE object_hash = ?
                    """, (object_hash,))
                else:
                    # 插入新对象
                    cursor.execute("""
                        INSERT INTO ops_cas_objects 
                        (object_hash, object_type, size_bytes, content_json, metadata_json)
                        VALUES (?, ?, ?, ?, ?)
                    """, (
                        object_hash, object_type, len(content_str),
                        content_str, json.dumps(metadata, ensure_ascii=False)
                    ))
                
                conn.commit()
                return object_hash
                
        except Exception as e:
            logger.error(f"CAS对象存储失败: {e}")
            return ""
    
    async def get_cas_object(self, object_hash: str) -> Optional[Dict[str, Any]]:
        """获取CAS对象"""
        try:
            with sqlite3.connect(str(self.db_path)) as conn:
                conn.row_factory = sqlite3.Row
                cursor = conn.cursor()
                
                cursor.execute("""
                    SELECT object_type, content_json, metadata_json, 
                           size_bytes, created_at, accessed_at
                    FROM ops_cas_objects
                    WHERE object_hash = ?
                """, (object_hash,))
                
                row = cursor.fetchone()
                if row:
                    # 更新访问时间
                    cursor.execute("""
                        UPDATE ops_cas_objects 
                        SET accessed_at = datetime('now')
                        WHERE object_hash = ?
                    """, (object_hash,))
                    conn.commit()
                    
                    return {
                        "object_hash": object_hash,
                        "object_type": row["object_type"],
                        "content": json.loads(row["content_json"]),
                        "metadata": json.loads(row["metadata_json"]) if row["metadata_json"] else {},
                        "size_bytes": row["size_bytes"],
                        "created_at": row["created_at"],
                        "accessed_at": row["accessed_at"]
                    }
                
                return None
                
        except Exception as e:
            logger.error(f"CAS对象获取失败: {e}")
            return None
    
    async def get_bulk_keyset_cache(
        self, 
        requests: List[Tuple[str, str, str]]
    ) -> Dict[str, Optional[Dict[str, Any]]]:
        """批量获取键集缓存"""
        results = {}
        
        try:
            with sqlite3.connect(str(self.db_path)) as conn:
                conn.row_factory = sqlite3.Row
                cursor = conn.cursor()
                
                # 构建批量查询
                placeholders = ",".join(["(?,?,?)"] * len(requests))
                query = f"""
                    SELECT carrier_uid, relative_path, locale, content_hash, 
                           keyset_hash, key_count, keys_json
                    FROM cache_keyset_fingerprints
                    WHERE (carrier_uid, relative_path, locale) IN ({placeholders})
                """
                
                # 展平参数
                params = []
                for carrier_uid, relative_path, locale in requests:
                    params.extend([carrier_uid, relative_path, locale])
                
                cursor.execute(query, params)
                
                # 处理结果
                for row in cursor.fetchall():
                    key = f"{row['carrier_uid']}:{row['relative_path']}:{row['locale']}"
                    results[key] = {
                        "content_hash": row["content_hash"],
                        "keyset_hash": row["keyset_hash"],
                        "key_count": row["key_count"],
                        "keys": json.loads(row["keys_json"]) if row["keys_json"] else []
                    }
                
                # 为未找到的请求添加None值
                for carrier_uid, relative_path, locale in requests:
                    key = f"{carrier_uid}:{relative_path}:{locale}"
                    if key not in results:
                        results[key] = None
                
                return results
                
        except Exception as e:
            logger.error(f"批量键集缓存获取失败: {e}")
            return {}
    
    async def cleanup_old_cache(self, days_old: int = 30) -> int:
        """清理旧缓存"""
        try:
            cutoff_date = datetime.now() - timedelta(days=days_old)
            
            with sqlite3.connect(str(self.db_path)) as conn:
                cursor = conn.cursor()
                
                # 清理旧的键集指纹
                cursor.execute("""
                    DELETE FROM cache_keyset_fingerprints
                    WHERE last_accessed < ?
                """, (cutoff_date.isoformat(),))
                
                keyset_cleaned = cursor.rowcount
                
                # 清理旧的CAS对象
                cursor.execute("""
                    DELETE FROM ops_cas_objects
                    WHERE accessed_at < ?
                """, (cutoff_date.isoformat(),))
                
                cas_cleaned = cursor.rowcount
                
                conn.commit()
                
                total_cleaned = keyset_cleaned + cas_cleaned
                logger.info(f"缓存清理完成: 键集指纹 {keyset_cleaned} 条, CAS对象 {cas_cleaned} 条")
                
                return total_cleaned
                
        except Exception as e:
            logger.error(f"缓存清理失败: {e}")
            return 0
    
    async def get_cache_statistics(self) -> Dict[str, Any]:
        """获取缓存统计信息"""
        try:
            with sqlite3.connect(str(self.db_path)) as conn:
                cursor = conn.cursor()
                
                # 键集指纹统计
                cursor.execute("SELECT COUNT(*) FROM cache_keyset_fingerprints")
                keyset_count = cursor.fetchone()[0]
                
                cursor.execute("SELECT AVG(key_count) FROM cache_keyset_fingerprints")
                avg_key_count = cursor.fetchone()[0] or 0
                
                # CAS对象统计
                cursor.execute("SELECT COUNT(*) FROM ops_cas_objects")
                cas_count = cursor.fetchone()[0]
                
                cursor.execute("SELECT SUM(size_bytes) FROM ops_cas_objects")
                total_size = cursor.fetchone()[0] or 0
                
                # 按类型统计CAS对象
                cursor.execute("""
                    SELECT object_type, COUNT(*) as count
                    FROM ops_cas_objects
                    GROUP BY object_type
                """)
                cas_by_type = {row[0]: row[1] for row in cursor.fetchall()}
                
                return {
                    "keyset_fingerprints": {
                        "total_count": keyset_count,
                        "average_key_count": round(avg_key_count, 2)
                    },
                    "cas_objects": {
                        "total_count": cas_count,
                        "total_size_bytes": total_size,
                        "by_type": cas_by_type
                    }
                }
                
        except Exception as e:
            logger.error(f"缓存统计获取失败: {e}")
            return {}
    
    def _calculate_keyset_hash(self, keys: List[str]) -> str:
        """计算键集哈希"""
        sorted_keys = sorted(keys)
        key_string = '|'.join(sorted_keys)
        return hashlib.blake3(key_string.encode('utf-8')).hexdigest()[:16]


# 全局服务实例
_cas_keyset_cache_service: CasKeysetCacheService = None


def get_cas_keyset_cache_service(db_path: str = "data/mc_l10n.db") -> CasKeysetCacheService:
    """获取CAS键集缓存服务实例"""
    global _cas_keyset_cache_service
    if _cas_keyset_cache_service is None:
        _cas_keyset_cache_service = CasKeysetCacheService(db_path)
    return _cas_keyset_cache_service