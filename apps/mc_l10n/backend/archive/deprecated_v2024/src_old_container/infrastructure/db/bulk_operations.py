"""
数据库批量操作优化器
提供高效的批量数据库操作
"""

import logging
import sqlite3
from contextlib import contextmanager
from typing import Any, Iterator, List, Protocol, Tuple

logger = logging.getLogger(__name__)


class BulkOperationResult:
    """批量操作结果"""
    
    def __init__(self):
        self.successful_count = 0
        self.failed_count = 0
        self.errors: List[Tuple[Any, Exception]] = []
        self.execution_time = 0.0
    
    @property
    def total_count(self) -> int:
        return self.successful_count + self.failed_count
    
    @property
    def success_rate(self) -> float:
        if self.total_count == 0:
            return 1.0
        return self.successful_count / self.total_count


class BulkInsertable(Protocol):
    """批量插入接口"""
    
    def to_insert_tuple(self) -> Tuple:
        """转换为插入元组"""
        ...


@contextmanager
def bulk_transaction(db_path: str, batch_size: int = 1000) -> Iterator[sqlite3.Connection]:
    """批量事务上下文管理器"""
    conn = sqlite3.connect(db_path)
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA synchronous=NORMAL")
    conn.execute("PRAGMA cache_size=20000")
    
    try:
        conn.execute("BEGIN IMMEDIATE")
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


class BulkDatabaseOperations:
    """数据库批量操作器"""
    
    def __init__(self, db_path: str, batch_size: int = 1000):
        self.db_path = db_path
        self.batch_size = batch_size
    
    def bulk_insert_mods(self, mods: List[BulkInsertable]) -> BulkOperationResult:
        """批量插入模组"""
        import time
        start_time = time.time()
        result = BulkOperationResult()
        
        try:
            with bulk_transaction(self.db_path) as conn:
                # 分批处理数据
                for i in range(0, len(mods), self.batch_size):
                    batch = mods[i:i + self.batch_size]
                    batch_data = [mod.to_insert_tuple() for mod in batch]
                    
                    try:
                        conn.executemany(
                            """
                            INSERT OR REPLACE INTO mods (
                                mod_id, name, version, authors, description,
                                minecraft_version, loader_type, file_path,
                                scan_status, last_scanned, content_hash, metadata,
                                created_at, updated_at
                            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                            """,
                            batch_data
                        )
                        result.successful_count += len(batch)
                        logger.debug(f"Successfully inserted batch {i//self.batch_size + 1}")
                        
                    except Exception as e:
                        result.failed_count += len(batch)
                        result.errors.append((batch, e))
                        logger.error(f"Failed to insert batch {i//self.batch_size + 1}: {e}")
                        
        except Exception as e:
            logger.error(f"Bulk insert transaction failed: {e}")
            result.failed_count = len(mods)
            result.errors.append((mods, e))
        
        result.execution_time = time.time() - start_time
        logger.info(
            f"Bulk insert completed: {result.successful_count}/{len(mods)} success, "
            f"took {result.execution_time:.2f}s"
        )
        
        return result
    
    def bulk_update_scan_status(
        self, mod_ids: List[str], status: str
    ) -> BulkOperationResult:
        """批量更新扫描状态"""
        import time
        start_time = time.time()
        result = BulkOperationResult()
        
        try:
            with bulk_transaction(self.db_path) as conn:
                update_data = [(status, mod_id) for mod_id in mod_ids]
                
                conn.executemany(
                    """
                    UPDATE mods 
                    SET scan_status = ?, updated_at = CURRENT_TIMESTAMP
                    WHERE mod_id = ?
                    """,
                    update_data
                )
                
                result.successful_count = len(mod_ids)
                
        except Exception as e:
            logger.error(f"Bulk update failed: {e}")
            result.failed_count = len(mod_ids)
            result.errors.append((mod_ids, e))
        
        result.execution_time = time.time() - start_time
        return result
    
    def bulk_insert_translations(
        self, mod_id: str, language: str, translations: dict[str, str]
    ) -> BulkOperationResult:
        """批量插入翻译"""
        import time
        start_time = time.time()
        result = BulkOperationResult()
        
        try:
            with bulk_transaction(self.db_path) as conn:
                translation_data = [
                    (mod_id, language, key, value, 'pending')
                    for key, value in translations.items()
                ]
                
                # 分批插入
                for i in range(0, len(translation_data), self.batch_size):
                    batch = translation_data[i:i + self.batch_size]
                    
                    try:
                        conn.executemany(
                            """
                            INSERT OR REPLACE INTO translations
                            (mod_id, language, key, translated, status, updated_at)
                            VALUES (?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
                            """,
                            batch
                        )
                        result.successful_count += len(batch)
                        
                    except Exception as e:
                        result.failed_count += len(batch)
                        result.errors.append((batch, e))
                        
        except Exception as e:
            logger.error(f"Bulk translation insert failed: {e}")
            result.failed_count = len(translations)
            result.errors.append((translations, e))
        
        result.execution_time = time.time() - start_time
        return result
    
    def cleanup_old_data(self, days: int = 30) -> BulkOperationResult:
        """清理旧数据"""
        import time
        start_time = time.time()
        result = BulkOperationResult()
        
        try:
            with bulk_transaction(self.db_path) as conn:
                # 清理旧的扫描结果
                cursor = conn.execute(
                    """
                    DELETE FROM scan_results 
                    WHERE created_at < datetime('now', '-' || ? || ' days')
                    """,
                    (days,)
                )
                deleted_scans = cursor.rowcount
                
                # 清理失效的模组记录
                cursor = conn.execute(
                    """
                    DELETE FROM mods 
                    WHERE scan_status = 'failed' 
                    AND updated_at < datetime('now', '-' || ? || ' days')
                    """,
                    (days,)
                )
                deleted_mods = cursor.rowcount
                
                # 真空数据库以回收空间
                conn.execute("VACUUM")
                
                result.successful_count = deleted_scans + deleted_mods
                logger.info(
                    f"Cleaned up {deleted_scans} scan results and {deleted_mods} failed mods"
                )
                
        except Exception as e:
            logger.error(f"Cleanup failed: {e}")
            result.failed_count = 1
            result.errors.append(("cleanup", e))
        
        result.execution_time = time.time() - start_time
        return result
    
    def optimize_database(self) -> BulkOperationResult:
        """优化数据库"""
        import time
        start_time = time.time()
        result = BulkOperationResult()
        
        try:
            with sqlite3.connect(self.db_path) as conn:
                # 分析表统计信息
                conn.execute("ANALYZE")
                
                # 重建索引
                conn.execute("REINDEX")
                
                # 整理数据库
                conn.execute("VACUUM")
                
                result.successful_count = 1
                logger.info("Database optimization completed")
                
        except Exception as e:
            logger.error(f"Database optimization failed: {e}")
            result.failed_count = 1
            result.errors.append(("optimization", e))
        
        result.execution_time = time.time() - start_time
        return result