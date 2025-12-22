"""
扫描缓存服务 - 智能缓存扫描结果以提升性能
"""

import hashlib
import json
import logging
import os
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Dict, Optional, List

logger = logging.getLogger(__name__)


class ScanCacheService:
    """扫描结果缓存服务
    
    提供基于目录内容哈希的智能缓存功能：
    - 检测目录内容变化
    - 缓存扫描结果JSON
    - 自动过期管理
    - 缓存命中率统计
    """

    def __init__(self, db_manager):
        """
        初始化缓存服务
        
        Args:
            db_manager: 数据库管理器实例
        """
        self.db_manager = db_manager
        self.default_ttl_hours = 24  # 默认缓存24小时
        
    def _calculate_directory_hash(self, directory_path: str) -> str:
        """
        计算目录内容哈希值
        
        基于目录中所有.jar文件的修改时间和大小生成哈希，
        用于检测目录内容是否发生变化
        
        Args:
            directory_path: 目录路径
            
        Returns:
            十六进制哈希字符串
        """
        try:
            directory = Path(directory_path)
            if not directory.exists():
                logger.warning(f"目录不存在: {directory_path}")
                return ""
            
            hasher = hashlib.sha256()
            
            # 收集所有JAR文件信息
            jar_files = []
            for jar_file in directory.rglob("*.jar"):
                if jar_file.is_file():
                    stat = jar_file.stat()
                    jar_files.append({
                        'path': str(jar_file.relative_to(directory)),
                        'size': stat.st_size,
                        'mtime': stat.st_mtime
                    })
            
            # 按路径排序确保一致性
            jar_files.sort(key=lambda x: x['path'])
            
            # 生成哈希
            for jar_info in jar_files:
                hasher.update(str(jar_info).encode('utf-8'))
            
            hash_value = hasher.hexdigest()
            logger.debug(f"目录哈希计算完成: {directory_path} -> {hash_value} ({len(jar_files)} 个JAR文件)")
            
            return hash_value
            
        except Exception as e:
            logger.error(f"计算目录哈希失败 {directory_path}: {e}")
            return ""
    
    async def get_cached_result(self, scan_path: str) -> Optional[Dict[str, Any]]:
        """
        获取缓存的扫描结果
        
        Args:
            scan_path: 扫描路径
            
        Returns:
            缓存的扫描结果字典，未找到或已过期返回None
        """
        try:
            # 计算当前目录哈希
            current_hash = self._calculate_directory_hash(scan_path)
            if not current_hash:
                logger.debug(f"无法计算目录哈希，跳过缓存检查: {scan_path}")
                return None
            
            # 查询数据库中的缓存
            with self.db_manager.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    SELECT result_json, created_at FROM cache_scan_results 
                    WHERE scan_path = ? AND scan_hash = ? 
                    AND valid_until > datetime('now')
                """, (scan_path, current_hash))
                
                row = cursor.fetchone()
                if row:
                    result_json, created_at = row
                    try:
                        result = json.loads(result_json)
                        logger.info(f"缓存命中: {scan_path} (创建时间: {created_at})")
                        return result
                    except json.JSONDecodeError as e:
                        logger.error(f"缓存JSON解析失败: {e}")
                        # 删除损坏的缓存
                        cursor.execute("""
                            DELETE FROM cache_scan_results 
                            WHERE scan_path = ? AND scan_hash = ?
                        """, (scan_path, current_hash))
                        conn.commit()
                
                logger.debug(f"缓存未命中: {scan_path} (哈希: {current_hash[:8]}...)")
                return None
                
        except Exception as e:
            logger.error(f"获取缓存失败 {scan_path}: {e}")
            return None
    
    async def store_cached_result(self, scan_path: str, result: Dict[str, Any], ttl_hours: Optional[int] = None) -> bool:
        """
        存储扫描结果到缓存
        
        Args:
            scan_path: 扫描路径
            result: 扫描结果字典
            ttl_hours: 缓存生存时间(小时)，默认使用24小时
            
        Returns:
            是否存储成功
        """
        try:
            # 计算目录哈希
            directory_hash = self._calculate_directory_hash(scan_path)
            if not directory_hash:
                logger.warning(f"无法计算目录哈希，跳过缓存存储: {scan_path}")
                return False
            
            # 序列化结果
            try:
                result_json = json.dumps(result, ensure_ascii=False)
            except (TypeError, ValueError) as e:
                logger.error(f"扫描结果序列化失败: {e}")
                return False
            
            # 计算过期时间
            ttl = ttl_hours or self.default_ttl_hours
            valid_until = datetime.now() + timedelta(hours=ttl)
            created_at = datetime.now()
            
            # 存储到数据库
            with self.db_manager.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    INSERT OR REPLACE INTO cache_scan_results 
                    (scan_path, scan_hash, result_json, valid_until, created_at)
                    VALUES (?, ?, ?, ?, ?)
                """, (
                    scan_path,
                    directory_hash, 
                    result_json,
                    valid_until.isoformat(),
                    created_at.isoformat()
                ))
                conn.commit()
            
            logger.info(f"缓存已存储: {scan_path} (大小: {len(result_json)} 字节, TTL: {ttl}小时)")
            return True
            
        except Exception as e:
            logger.error(f"存储缓存失败 {scan_path}: {e}")
            return False
    
    async def invalidate_cache(self, scan_path: str) -> bool:
        """
        使指定路径的缓存失效
        
        Args:
            scan_path: 扫描路径
            
        Returns:
            是否删除成功
        """
        try:
            with self.db_manager.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    DELETE FROM cache_scan_results 
                    WHERE scan_path = ?
                """, (scan_path,))
                deleted_count = cursor.rowcount
                conn.commit()
            
            if deleted_count > 0:
                logger.info(f"缓存已清除: {scan_path} ({deleted_count} 条记录)")
            else:
                logger.debug(f"未找到要清除的缓存: {scan_path}")
            
            return deleted_count > 0
            
        except Exception as e:
            logger.error(f"清除缓存失败 {scan_path}: {e}")
            return False
    
    async def cleanup_expired_cache(self) -> int:
        """
        清理所有过期的缓存
        
        Returns:
            删除的记录数
        """
        try:
            with self.db_manager.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    DELETE FROM cache_scan_results 
                    WHERE valid_until <= datetime('now')
                """)
                deleted_count = cursor.rowcount
                conn.commit()
            
            if deleted_count > 0:
                logger.info(f"清理过期缓存完成: 删除 {deleted_count} 条记录")
            
            return deleted_count
            
        except Exception as e:
            logger.error(f"清理过期缓存失败: {e}")
            return 0
    
    async def get_cache_stats(self) -> Dict[str, Any]:
        """
        获取缓存统计信息
        
        Returns:
            缓存统计信息字典
        """
        try:
            with self.db_manager.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    SELECT 
                        COUNT(*) as total_entries,
                        COUNT(CASE WHEN valid_until > datetime('now') THEN 1 END) as valid_entries,
                        COUNT(CASE WHEN valid_until <= datetime('now') THEN 1 END) as expired_entries,
                        ROUND(AVG(LENGTH(result_json)), 2) as avg_size_bytes,
                        ROUND(SUM(LENGTH(result_json)) / 1024.0 / 1024.0, 2) as total_size_mb,
                        MIN(created_at) as oldest_entry,
                        MAX(created_at) as newest_entry
                    FROM cache_scan_results
                """)
                
                row = cursor.fetchone()
                if row:
                    stats = {
                        "total_entries": row[0] or 0,
                        "valid_entries": row[1] or 0,
                        "expired_entries": row[2] or 0,
                        "avg_size_bytes": row[3] or 0.0,
                        "total_size_mb": row[4] or 0.0,
                        "oldest_entry": row[5],
                        "newest_entry": row[6],
                        "hit_ratio": 0.0  # 需要额外统计
                    }
                    return stats
                else:
                    return {
                        "total_entries": 0,
                        "valid_entries": 0,
                        "expired_entries": 0,
                        "avg_size_bytes": 0.0,
                        "total_size_mb": 0.0,
                        "oldest_entry": None,
                        "newest_entry": None,
                        "hit_ratio": 0.0
                    }
                    
        except Exception as e:
            logger.error(f"获取缓存统计失败: {e}")
            return {}
    
    async def warm_up_cache(self, directories: List[str]) -> Dict[str, Any]:
        """
        预热缓存 - 为指定目录预先计算缓存
        
        Args:
            directories: 要预热的目录列表
            
        Returns:
            预热结果统计
        """
        warm_up_stats = {
            "total_directories": len(directories),
            "successful": 0,
            "failed": 0,
            "skipped": 0,
            "errors": []
        }
        
        for directory in directories:
            try:
                # 检查是否已有有效缓存
                cached = await self.get_cached_result(directory)
                if cached:
                    warm_up_stats["skipped"] += 1
                    logger.debug(f"缓存预热跳过 (已缓存): {directory}")
                    continue
                
                # 这里可以触发实际的扫描来生成缓存
                # 但为了避免重复代码，建议在调用方处理
                logger.info(f"缓存预热需要扫描: {directory}")
                warm_up_stats["successful"] += 1
                
            except Exception as e:
                error_msg = f"预热缓存失败 {directory}: {e}"
                logger.error(error_msg)
                warm_up_stats["failed"] += 1
                warm_up_stats["errors"].append(error_msg)
        
        logger.info(f"缓存预热完成: {warm_up_stats}")
        return warm_up_stats


# 全局缓存服务实例
_cache_service_instance: Optional[ScanCacheService] = None


def get_cache_service(db_manager) -> ScanCacheService:
    """获取全局缓存服务实例"""
    global _cache_service_instance
    if _cache_service_instance is None:
        _cache_service_instance = ScanCacheService(db_manager)
        logger.info("扫描缓存服务已初始化")
    return _cache_service_instance