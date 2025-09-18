"""
V5架构 - 多层缓存系统
提供内存缓存、数据库缓存和文件缓存的多层次性能优化
"""

import asyncio
import json
import logging
import hashlib
import time
from typing import Dict, Any, Optional, Union, List
from datetime import datetime, timedelta
from enum import Enum
from dataclasses import dataclass, asdict
import weakref

from infrastructure.repositories.repository_factory import get_repository_factory

logger = logging.getLogger(__name__)


class CacheLevel(Enum):
    """缓存级别枚举"""
    MEMORY = "memory"      # L1: 内存缓存 (最快)
    DATABASE = "database"  # L2: 数据库缓存 (中等)
    FILE = "file"          # L3: 文件缓存 (较慢)


class CacheType(Enum):
    """缓存类型枚举"""
    TRANSLATION = "translation"  # 翻译缓存
    METADATA = "metadata"        # 元数据缓存
    FILE_CONTENT = "file"        # 文件缓存
    INDEX = "index"             # 索引缓存


@dataclass
class CacheEntry:
    """缓存条目数据类"""
    key: str
    value: Any
    cache_type: CacheType
    created_at: datetime
    expires_at: Optional[datetime] = None
    access_count: int = 0
    last_accessed: Optional[datetime] = None
    size_bytes: int = 0
    
    def is_expired(self) -> bool:
        """检查是否过期"""
        if self.expires_at is None:
            return False
        return datetime.now() > self.expires_at
        
    def touch(self):
        """更新访问时间和计数"""
        self.last_accessed = datetime.now()
        self.access_count += 1


class MemoryCache:
    """L1: 内存缓存实现"""
    
    def __init__(self, max_size: int = 1000, ttl_seconds: int = 3600):
        self.cache: Dict[str, CacheEntry] = {}
        self.max_size = max_size
        self.ttl_seconds = ttl_seconds
        self._size_bytes = 0
        self._hits = 0
        self._misses = 0
        
    def get(self, key: str) -> Optional[Any]:
        """获取缓存值"""
        if key not in self.cache:
            self._misses += 1
            return None
            
        entry = self.cache[key]
        if entry.is_expired():
            del self.cache[key]
            self._size_bytes -= entry.size_bytes
            self._misses += 1
            return None
            
        entry.touch()
        self._hits += 1
        return entry.value
        
    def set(self, key: str, value: Any, cache_type: CacheType, ttl: Optional[int] = None) -> bool:
        """设置缓存值"""
        # 清理过期条目
        self._cleanup_expired()
        
        # 如果达到最大大小，清理最少使用的条目
        if len(self.cache) >= self.max_size:
            self._evict_lru()
            
        # 计算大小
        size_bytes = len(str(value).encode('utf-8'))
        
        expires_at = None
        if ttl or self.ttl_seconds:
            expires_at = datetime.now() + timedelta(seconds=ttl or self.ttl_seconds)
            
        entry = CacheEntry(
            key=key,
            value=value,
            cache_type=cache_type,
            created_at=datetime.now(),
            expires_at=expires_at,
            size_bytes=size_bytes
        )
        
        # 移除旧条目（如果存在）
        if key in self.cache:
            self._size_bytes -= self.cache[key].size_bytes
            
        self.cache[key] = entry
        self._size_bytes += size_bytes
        
        return True
        
    def delete(self, key: str) -> bool:
        """删除缓存条目"""
        if key in self.cache:
            self._size_bytes -= self.cache[key].size_bytes
            del self.cache[key]
            return True
        return False
        
    def clear(self, cache_type: Optional[CacheType] = None):
        """清空缓存"""
        if cache_type is None:
            self.cache.clear()
            self._size_bytes = 0
        else:
            keys_to_remove = [k for k, v in self.cache.items() if v.cache_type == cache_type]
            for key in keys_to_remove:
                self._size_bytes -= self.cache[key].size_bytes
                del self.cache[key]
                
    def _cleanup_expired(self):
        """清理过期条目"""
        expired_keys = [k for k, v in self.cache.items() if v.is_expired()]
        for key in expired_keys:
            self._size_bytes -= self.cache[key].size_bytes
            del self.cache[key]
            
    def _evict_lru(self):
        """淘汰最少使用的条目"""
        if not self.cache:
            return
            
        # 找到最少访问的条目
        lru_key = min(self.cache.keys(), 
                     key=lambda k: (self.cache[k].access_count, self.cache[k].last_accessed or datetime.min))
        
        self._size_bytes -= self.cache[lru_key].size_bytes
        del self.cache[lru_key]
        
    def get_stats(self) -> Dict[str, Any]:
        """获取缓存统计"""
        total_requests = self._hits + self._misses
        hit_rate = self._hits / total_requests if total_requests > 0 else 0
        
        return {
            "level": "memory",
            "entries": len(self.cache),
            "size_bytes": self._size_bytes,
            "max_size": self.max_size,
            "hits": self._hits,
            "misses": self._misses,
            "hit_rate": hit_rate,
            "ttl_seconds": self.ttl_seconds
        }


class DatabaseCache:
    """L2: 数据库缓存实现"""
    
    def __init__(self):
        self.factory = get_repository_factory()
        self._hits = 0
        self._misses = 0
        
    async def get(self, key: str, cache_type: CacheType) -> Optional[Any]:
        """从数据库缓存获取值"""
        try:
            # 根据缓存类型选择对应的缓存表
            table_name = self._get_cache_table(cache_type)
            
            query = f"""
                SELECT value_json, expires_at 
                FROM {table_name} 
                WHERE cache_key = ? AND (expires_at IS NULL OR expires_at > datetime('now'))
            """
            
            # 简化实现：直接执行SQL查询
            import sqlite3
            db_path = self.factory.db_path
            
            with sqlite3.connect(str(db_path)) as conn:
                conn.row_factory = sqlite3.Row
                cursor = conn.execute(query, (key,))
                row = cursor.fetchone()
                
                if row:
                    # 更新访问统计
                    conn.execute(f"""
                        UPDATE {table_name} 
                        SET access_count = access_count + 1, last_accessed = datetime('now')
                        WHERE cache_key = ?
                    """, (key,))
                    conn.commit()
                    
                    self._hits += 1
                    return json.loads(row['value_json'])
                else:
                    self._misses += 1
                    return None
                    
        except Exception as e:
            logger.error(f"数据库缓存获取失败: {e}")
            self._misses += 1
            return None
            
    async def set(self, key: str, value: Any, cache_type: CacheType, ttl: Optional[int] = None) -> bool:
        """设置数据库缓存值"""
        try:
            table_name = self._get_cache_table(cache_type)
            value_json = json.dumps(value, ensure_ascii=False)
            size_bytes = len(value_json.encode('utf-8'))
            
            expires_at = None
            if ttl:
                expires_at = (datetime.now() + timedelta(seconds=ttl)).isoformat()
                
            query = f"""
                INSERT OR REPLACE INTO {table_name} 
                (cache_key, value_json, cache_type, size_bytes, expires_at, created_at, access_count, last_accessed)
                VALUES (?, ?, ?, ?, ?, datetime('now'), 0, datetime('now'))
            """
            
            import sqlite3
            db_path = self.factory.db_path
            
            with sqlite3.connect(str(db_path)) as conn:
                conn.execute(query, (key, value_json, cache_type.value, size_bytes, expires_at))
                conn.commit()
                
            return True
            
        except Exception as e:
            logger.error(f"数据库缓存设置失败: {e}")
            return False
            
    async def delete(self, key: str, cache_type: CacheType) -> bool:
        """删除数据库缓存条目"""
        try:
            table_name = self._get_cache_table(cache_type)
            
            import sqlite3
            db_path = self.factory.db_path
            
            with sqlite3.connect(str(db_path)) as conn:
                cursor = conn.execute(f"DELETE FROM {table_name} WHERE cache_key = ?", (key,))
                conn.commit()
                return cursor.rowcount > 0
                
        except Exception as e:
            logger.error(f"数据库缓存删除失败: {e}")
            return False
            
    async def clear(self, cache_type: Optional[CacheType] = None):
        """清空数据库缓存"""
        try:
            import sqlite3
            db_path = self.factory.db_path
            
            with sqlite3.connect(str(db_path)) as conn:
                if cache_type is None:
                    # 清空所有缓存表
                    for ct in CacheType:
                        table_name = self._get_cache_table(ct)
                        conn.execute(f"DELETE FROM {table_name}")
                else:
                    table_name = self._get_cache_table(cache_type)
                    conn.execute(f"DELETE FROM {table_name}")
                    
                conn.commit()
                
        except Exception as e:
            logger.error(f"数据库缓存清空失败: {e}")
            
    def _get_cache_table(self, cache_type: CacheType) -> str:
        """根据缓存类型获取对应的表名"""
        table_mapping = {
            CacheType.TRANSLATION: "cache_translation_cache",
            CacheType.METADATA: "cache_metadata_cache", 
            CacheType.FILE_CONTENT: "cache_file_cache",
            CacheType.INDEX: "cache_index_cache"
        }
        return table_mapping[cache_type]
        
    async def get_stats(self) -> Dict[str, Any]:
        """获取数据库缓存统计"""
        try:
            import sqlite3
            db_path = self.factory.db_path
            
            stats = {
                "level": "database",
                "hits": self._hits,
                "misses": self._misses,
                "hit_rate": self._hits / (self._hits + self._misses) if (self._hits + self._misses) > 0 else 0,
                "tables": {}
            }
            
            with sqlite3.connect(str(db_path)) as conn:
                conn.row_factory = sqlite3.Row
                
                for cache_type in CacheType:
                    table_name = self._get_cache_table(cache_type)
                    
                    # 获取表统计
                    cursor = conn.execute(f"""
                        SELECT 
                            COUNT(*) as entries,
                            SUM(size_bytes) as total_size,
                            AVG(access_count) as avg_access
                        FROM {table_name}
                        WHERE expires_at IS NULL OR expires_at > datetime('now')
                    """)
                    
                    row = cursor.fetchone()
                    stats["tables"][cache_type.value] = {
                        "entries": row['entries'] or 0,
                        "total_size": row['total_size'] or 0,
                        "avg_access": row['avg_access'] or 0
                    }
                    
            return stats
            
        except Exception as e:
            logger.error(f"获取数据库缓存统计失败: {e}")
            return {"level": "database", "error": str(e)}


class FileCache:
    """L3: 文件缓存实现"""
    
    def __init__(self, cache_dir: str = "data/file_cache"):
        import os
        self.cache_dir = cache_dir
        os.makedirs(cache_dir, exist_ok=True)
        self._hits = 0
        self._misses = 0
        
    async def initialize(self):
        """初始化文件缓存"""
        import os
        os.makedirs(self.cache_dir, exist_ok=True)
        logger.info(f"文件缓存初始化完成: {self.cache_dir}")
        
    async def cleanup(self):
        """清理文件缓存"""
        try:
            import shutil
            import os
            if os.path.exists(self.cache_dir):
                shutil.rmtree(self.cache_dir)
                logger.info(f"文件缓存目录已清理: {self.cache_dir}")
        except Exception as e:
            logger.warning(f"清理文件缓存目录失败: {e}")
        
    async def get(self, key: str) -> Optional[Any]:
        """从文件缓存获取值"""
        try:
            file_path = self._get_file_path(key)
            
            if not file_path.exists():
                self._misses += 1
                return None
                
            # 检查文件修改时间（简单的TTL实现）
            import os
            stat = os.stat(file_path)
            file_age = time.time() - stat.st_mtime
            
            # 24小时TTL
            if file_age > 24 * 3600:
                file_path.unlink()
                self._misses += 1
                return None
                
            with open(file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
                
            self._hits += 1
            return data
            
        except Exception as e:
            logger.error(f"文件缓存获取失败: {e}")
            self._misses += 1
            return None
            
    async def set(self, key: str, value: Any) -> bool:
        """设置文件缓存值"""
        try:
            file_path = self._get_file_path(key)
            file_path.parent.mkdir(parents=True, exist_ok=True)
            
            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(value, f, ensure_ascii=False, indent=2)
                
            return True
            
        except Exception as e:
            logger.error(f"文件缓存设置失败: {e}")
            return False
            
    async def delete(self, key: str) -> bool:
        """删除文件缓存条目"""
        try:
            file_path = self._get_file_path(key)
            if file_path.exists():
                file_path.unlink()
                return True
            return False
            
        except Exception as e:
            logger.error(f"文件缓存删除失败: {e}")
            return False
            
    async def clear(self):
        """清空文件缓存"""
        try:
            import shutil
            from pathlib import Path
            
            cache_path = Path(self.cache_dir)
            if cache_path.exists():
                shutil.rmtree(cache_path)
                cache_path.mkdir(parents=True, exist_ok=True)
                
        except Exception as e:
            logger.error(f"文件缓存清空失败: {e}")
            
    def _get_file_path(self, key: str):
        """根据key生成文件路径"""
        from pathlib import Path
        
        # 使用key的hash作为文件名，避免特殊字符问题
        key_hash = hashlib.md5(key.encode('utf-8')).hexdigest()
        
        # 创建两级目录结构避免单个目录文件过多
        dir1 = key_hash[:2]
        dir2 = key_hash[2:4]
        filename = key_hash[4:] + '.json'
        
        return Path(self.cache_dir) / dir1 / dir2 / filename
        
    async def get_stats(self) -> Dict[str, Any]:
        """获取文件缓存统计"""
        try:
            import os
            from pathlib import Path
            
            cache_path = Path(self.cache_dir)
            if not cache_path.exists():
                return {
                    "level": "file",
                    "entries": 0,
                    "total_size": 0,
                    "hits": self._hits,
                    "misses": self._misses,
                    "hit_rate": 0
                }
                
            entries = 0
            total_size = 0
            
            for file_path in cache_path.rglob('*.json'):
                entries += 1
                total_size += file_path.stat().st_size
                
            return {
                "level": "file",
                "entries": entries,
                "total_size": total_size,
                "hits": self._hits,
                "misses": self._misses,
                "hit_rate": self._hits / (self._hits + self._misses) if (self._hits + self._misses) > 0 else 0,
                "cache_dir": self.cache_dir
            }
            
        except Exception as e:
            logger.error(f"获取文件缓存统计失败: {e}")
            return {"level": "file", "error": str(e)}


class MultiLayerCacheService:
    """多层缓存服务 - V5架构核心缓存引擎"""
    
    def __init__(self):
        self.memory_cache = MemoryCache(max_size=2000, ttl_seconds=1800)  # 30分钟
        self.database_cache = DatabaseCache()
        self.file_cache = FileCache()
        
        # 缓存策略配置
        self.cache_strategy = {
            CacheType.TRANSLATION: [CacheLevel.MEMORY, CacheLevel.DATABASE],
            CacheType.METADATA: [CacheLevel.MEMORY, CacheLevel.DATABASE, CacheLevel.FILE],
            CacheType.FILE_CONTENT: [CacheLevel.FILE, CacheLevel.DATABASE],
            CacheType.INDEX: [CacheLevel.MEMORY, CacheLevel.DATABASE]
        }
        
        self._initialized = False
        
    async def initialize(self):
        """初始化缓存服务"""
        if self._initialized:
            return
            
        try:
            # 初始化文件缓存目录
            await self.file_cache.initialize()
            self._initialized = True
            logger.info("多层缓存服务初始化完成")
        except Exception as e:
            logger.error(f"多层缓存服务初始化失败: {e}")
            raise
            
    async def cleanup(self):
        """清理缓存服务"""
        try:
            # 清理内存缓存
            self.memory_cache.clear()
            # 清理文件缓存目录（可选）
            await self.file_cache.cleanup()
            self._initialized = False
            logger.info("多层缓存服务清理完成")
        except Exception as e:
            logger.error(f"多层缓存服务清理失败: {e}")
            raise
            
    def get_statistics(self) -> Dict[str, Any]:
        """获取多层缓存统计信息"""
        try:
            # 获取各层缓存统计
            memory_stats = self.memory_cache.get_stats()
            
            stats = {
                "summary": {
                    "total_hits": memory_stats.get("hits", 0),
                    "total_misses": memory_stats.get("misses", 0),
                    "hit_rate": memory_stats.get("hit_rate", 0),
                    "cache_levels": len(self.cache_strategy)
                },
                "layers": {
                    "memory": memory_stats,
                    "database": {
                        "level": "database",
                        "status": "operational",
                        "note": "V5 cache tables"
                    },
                    "file": {
                        "level": "file",
                        "status": "operational", 
                        "directory": "data/file_cache"
                    }
                },
                "strategy": {
                    cache_type.value: [level.value for level in levels] 
                    for cache_type, levels in self.cache_strategy.items()
                }
            }
            
            return stats
            
        except Exception as e:
            logger.error(f"获取缓存统计失败: {e}")
            return {
                "error": str(e),
                "summary": {"total_hits": 0, "total_misses": 0, "hit_rate": 0}
            }
        
    async def get(self, key: str, cache_type: CacheType) -> Optional[Any]:
        """多层缓存获取 - 按优先级依次查找"""
        levels = self.cache_strategy.get(cache_type, [CacheLevel.MEMORY])
        
        for level in levels:
            try:
                if level == CacheLevel.MEMORY:
                    value = self.memory_cache.get(key)
                elif level == CacheLevel.DATABASE:
                    value = await self.database_cache.get(key, cache_type)
                elif level == CacheLevel.FILE:
                    value = await self.file_cache.get(key)
                else:
                    continue
                    
                if value is not None:
                    # 缓存击中，回填到更高层级的缓存
                    await self._backfill_cache(key, value, cache_type, level)
                    return value
                    
            except Exception as e:
                logger.warning(f"缓存层 {level.value} 获取失败: {e}")
                continue
                
        return None
        
    async def set(self, key: str, value: Any, cache_type: CacheType, ttl: Optional[int] = None) -> bool:
        """多层缓存设置 - 写入所有配置的层级"""
        levels = self.cache_strategy.get(cache_type, [CacheLevel.MEMORY])
        success = False
        
        for level in levels:
            try:
                if level == CacheLevel.MEMORY:
                    result = self.memory_cache.set(key, value, cache_type, ttl)
                elif level == CacheLevel.DATABASE:
                    result = await self.database_cache.set(key, value, cache_type, ttl)
                elif level == CacheLevel.FILE:
                    result = await self.file_cache.set(key, value)
                else:
                    continue
                    
                if result:
                    success = True
                    
            except Exception as e:
                logger.warning(f"缓存层 {level.value} 设置失败: {e}")
                continue
                
        return success
        
    async def delete(self, key: str, cache_type: CacheType) -> bool:
        """多层缓存删除 - 从所有层级删除"""
        levels = self.cache_strategy.get(cache_type, [CacheLevel.MEMORY])
        success = False
        
        for level in levels:
            try:
                if level == CacheLevel.MEMORY:
                    result = self.memory_cache.delete(key)
                elif level == CacheLevel.DATABASE:
                    result = await self.database_cache.delete(key, cache_type)
                elif level == CacheLevel.FILE:
                    result = await self.file_cache.delete(key)
                else:
                    continue
                    
                if result:
                    success = True
                    
            except Exception as e:
                logger.warning(f"缓存层 {level.value} 删除失败: {e}")
                continue
                
        return success
        
    async def clear(self, cache_type: Optional[CacheType] = None, level: Optional[CacheLevel] = None):
        """清空缓存"""
        if level is not None:
            # 清空指定层级
            if level == CacheLevel.MEMORY:
                self.memory_cache.clear(cache_type)
            elif level == CacheLevel.DATABASE:
                await self.database_cache.clear(cache_type)
            elif level == CacheLevel.FILE:
                await self.file_cache.clear()
        else:
            # 清空所有层级
            self.memory_cache.clear(cache_type)
            await self.database_cache.clear(cache_type)
            if cache_type is None:  # 只有全清理时才清理文件缓存
                await self.file_cache.clear()
                
    async def _backfill_cache(self, key: str, value: Any, cache_type: CacheType, found_level: CacheLevel):
        """回填缓存到更高层级"""
        levels = self.cache_strategy.get(cache_type, [])
        
        # 找到发现值的层级索引
        try:
            found_index = levels.index(found_level)
        except ValueError:
            return
            
        # 回填到更高优先级的层级
        for i in range(found_index):
            level = levels[i]
            try:
                if level == CacheLevel.MEMORY:
                    self.memory_cache.set(key, value, cache_type)
                elif level == CacheLevel.DATABASE:
                    await self.database_cache.set(key, value, cache_type)
                # 文件缓存不进行回填，避免过度写入
                    
            except Exception as e:
                logger.warning(f"缓存回填到 {level.value} 失败: {e}")
                
    async def get_stats(self) -> Dict[str, Any]:
        """获取所有缓存层级的统计信息"""
        memory_stats = self.memory_cache.get_stats()
        database_stats = await self.database_cache.get_stats()
        file_stats = await self.file_cache.get_stats()
        
        return {
            "service": "multi_layer_cache",
            "strategy": {ct.value: [level.value for level in levels] 
                        for ct, levels in self.cache_strategy.items()},
            "levels": {
                "memory": memory_stats,
                "database": database_stats,
                "file": file_stats
            },
            "total_stats": {
                "memory_entries": memory_stats["entries"],
                "database_entries": sum(table["entries"] for table in database_stats.get("tables", {}).values()),
                "file_entries": file_stats["entries"],
                "total_hits": memory_stats["hits"] + database_stats["hits"] + file_stats["hits"],
                "total_misses": memory_stats["misses"] + database_stats["misses"] + file_stats["misses"]
            }
        }


# 全局多层缓存服务实例
multi_layer_cache_service: Optional[MultiLayerCacheService] = None


def get_multi_layer_cache_service() -> MultiLayerCacheService:
    """获取全局多层缓存服务实例"""
    global multi_layer_cache_service
    if multi_layer_cache_service is None:
        multi_layer_cache_service = MultiLayerCacheService()
        logger.info("多层缓存服务已初始化")
    return multi_layer_cache_service


async def initialize_cache_service():
    """初始化缓存服务（用于应用启动时调用）"""
    cache_service = get_multi_layer_cache_service()
    await cache_service.initialize()
    logger.info("多层缓存服务初始化完成")


async def cleanup_cache_service():
    """清理缓存服务（用于应用关闭时调用）"""
    global multi_layer_cache_service
    if multi_layer_cache_service:
        await multi_layer_cache_service.cleanup()
        logger.info("多层缓存服务清理完成")