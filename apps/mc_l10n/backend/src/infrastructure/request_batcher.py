"""
请求批处理器
合并相似请求以提高性能
"""

from typing import Dict, List, Any, Callable, Optional, Set
from dataclasses import dataclass, field
from datetime import datetime, timedelta
import asyncio
import hashlib
import json
import logging
from collections import defaultdict
from threading import Lock
import time

logger = logging.getLogger(__name__)


@dataclass
class BatchRequest:
    """批处理请求"""
    request_id: str
    key: str
    params: Dict[str, Any]
    callback: asyncio.Future
    timestamp: datetime = field(default_factory=datetime.now)
    
    def __hash__(self):
        return hash(self.request_id)


class RequestBatcher:
    """请求批处理器
    
    将多个相似请求合并为一个批处理请求，
    减少重复计算和数据库查询
    """
    
    def __init__(
        self,
        batch_window: float = 0.1,  # 批处理窗口（秒）
        max_batch_size: int = 100,   # 最大批大小
        dedup_enabled: bool = True   # 是否去重
    ):
        """初始化批处理器
        
        Args:
            batch_window: 批处理时间窗口
            max_batch_size: 最大批处理大小
            dedup_enabled: 是否启用请求去重
        """
        self.batch_window = batch_window
        self.max_batch_size = max_batch_size
        self.dedup_enabled = dedup_enabled
        
        self._batches: Dict[str, List[BatchRequest]] = defaultdict(list)
        self._processors: Dict[str, Callable] = {}
        self._timers: Dict[str, asyncio.Task] = {}
        self._request_cache: Dict[str, Any] = {}
        self._lock = asyncio.Lock()
        
        # 统计信息
        self._stats = {
            'total_requests': 0,
            'batched_requests': 0,
            'duplicate_requests': 0,
            'batch_count': 0,
            'avg_batch_size': 0
        }
    
    def register_processor(
        self,
        batch_key: str,
        processor: Callable[[List[Dict]], List[Any]]
    ):
        """注册批处理器
        
        Args:
            batch_key: 批处理键
            processor: 处理函数，接收请求列表，返回结果列表
        """
        self._processors[batch_key] = processor
        logger.info(f"Registered processor for batch key: {batch_key}")
    
    async def submit(
        self,
        batch_key: str,
        params: Dict[str, Any],
        request_id: Optional[str] = None
    ) -> Any:
        """提交请求
        
        Args:
            batch_key: 批处理键
            params: 请求参数
            request_id: 请求ID（用于去重）
            
        Returns:
            请求结果
        """
        if batch_key not in self._processors:
            raise ValueError(f"No processor registered for batch key: {batch_key}")
        
        # 生成请求ID
        if request_id is None:
            request_id = self._generate_request_id(batch_key, params)
        
        # 检查缓存（去重）
        if self.dedup_enabled and request_id in self._request_cache:
            async with self._lock:
                self._stats['duplicate_requests'] += 1
            return self._request_cache[request_id]
        
        # 创建future
        future = asyncio.Future()
        
        # 创建批请求
        batch_request = BatchRequest(
            request_id=request_id,
            key=batch_key,
            params=params,
            callback=future
        )
        
        async with self._lock:
            self._stats['total_requests'] += 1
            
            # 添加到批次
            self._batches[batch_key].append(batch_request)
            
            # 检查是否需要立即处理
            if len(self._batches[batch_key]) >= self.max_batch_size:
                await self._process_batch(batch_key)
            else:
                # 启动定时器
                if batch_key not in self._timers or self._timers[batch_key].done():
                    self._timers[batch_key] = asyncio.create_task(
                        self._batch_timer(batch_key)
                    )
        
        # 等待结果
        return await future
    
    async def _batch_timer(self, batch_key: str):
        """批处理定时器"""
        await asyncio.sleep(self.batch_window)
        async with self._lock:
            await self._process_batch(batch_key)
    
    async def _process_batch(self, batch_key: str):
        """处理批次"""
        if batch_key not in self._batches or not self._batches[batch_key]:
            return
        
        # 获取批次
        batch = self._batches[batch_key]
        self._batches[batch_key] = []
        
        # 取消定时器
        if batch_key in self._timers:
            self._timers[batch_key].cancel()
            del self._timers[batch_key]
        
        # 更新统计
        self._stats['batch_count'] += 1
        self._stats['batched_requests'] += len(batch)
        
        # 获取处理器
        processor = self._processors[batch_key]
        
        try:
            # 准备请求数据
            request_data = [req.params for req in batch]
            
            # 执行批处理
            if asyncio.iscoroutinefunction(processor):
                results = await processor(request_data)
            else:
                results = await asyncio.get_event_loop().run_in_executor(
                    None, processor, request_data
                )
            
            # 分发结果
            for i, req in enumerate(batch):
                if i < len(results):
                    result = results[i]
                    # 缓存结果
                    if self.dedup_enabled:
                        self._request_cache[req.request_id] = result
                    # 完成future
                    req.callback.set_result(result)
                else:
                    req.callback.set_exception(
                        IndexError("Result index out of range")
                    )
            
            logger.debug(f"Processed batch of {len(batch)} requests for {batch_key}")
            
        except Exception as e:
            logger.error(f"Batch processing error: {e}")
            # 设置异常
            for req in batch:
                if not req.callback.done():
                    req.callback.set_exception(e)
    
    def _generate_request_id(self, batch_key: str, params: Dict[str, Any]) -> str:
        """生成请求ID"""
        # 序列化参数
        param_str = json.dumps(params, sort_keys=True, default=str)
        # 生成哈希
        hash_obj = hashlib.md5(f"{batch_key}:{param_str}".encode())
        return hash_obj.hexdigest()
    
    def clear_cache(self):
        """清除缓存"""
        self._request_cache.clear()
        logger.info("Request cache cleared")
    
    def get_stats(self) -> Dict[str, Any]:
        """获取统计信息"""
        stats = dict(self._stats)
        if stats['batch_count'] > 0:
            stats['avg_batch_size'] = stats['batched_requests'] / stats['batch_count']
        stats['cache_size'] = len(self._request_cache)
        stats['active_batches'] = len(self._batches)
        return stats


class QueryBatcher:
    """数据库查询批处理器
    
    专门用于批处理数据库查询
    """
    
    def __init__(self, connection_pool, batch_window: float = 0.05):
        """初始化查询批处理器
        
        Args:
            connection_pool: 数据库连接池
            batch_window: 批处理窗口
        """
        self.connection_pool = connection_pool
        self.batcher = RequestBatcher(
            batch_window=batch_window,
            max_batch_size=50
        )
        
        # 注册常见查询处理器
        self._register_processors()
    
    def _register_processors(self):
        """注册查询处理器"""
        
        # 批量查询MOD
        async def batch_get_mods(requests: List[Dict]) -> List[Any]:
            mod_ids = [req['mod_id'] for req in requests]
            
            with self.connection_pool.get_connection() as conn:
                cursor = conn.cursor()
                placeholders = ','.join('?' * len(mod_ids))
                query = f"""
                    SELECT * FROM mods 
                    WHERE mod_id IN ({placeholders})
                """
                cursor.execute(query, mod_ids)
                rows = cursor.fetchall()
                
                # 转换为字典
                mod_dict = {row[0]: row for row in rows}
                
                # 按请求顺序返回
                return [mod_dict.get(mod_id) for mod_id in mod_ids]
        
        self.batcher.register_processor('get_mods', batch_get_mods)
        
        # 批量查询翻译
        async def batch_get_translations(requests: List[Dict]) -> List[Any]:
            results = []
            
            with self.connection_pool.get_connection() as conn:
                cursor = conn.cursor()
                
                for req in requests:
                    mod_id = req['mod_id']
                    language = req.get('language')
                    
                    if language:
                        query = """
                            SELECT * FROM translations 
                            WHERE mod_id = ? AND language = ?
                        """
                        cursor.execute(query, (mod_id, language))
                    else:
                        query = """
                            SELECT * FROM translations 
                            WHERE mod_id = ?
                        """
                        cursor.execute(query, (mod_id,))
                    
                    results.append(cursor.fetchall())
            
            return results
        
        self.batcher.register_processor('get_translations', batch_get_translations)
    
    async def get_mod(self, mod_id: str) -> Optional[Any]:
        """获取MOD（批处理）"""
        return await self.batcher.submit(
            'get_mods',
            {'mod_id': mod_id}
        )
    
    async def get_translations(
        self,
        mod_id: str,
        language: Optional[str] = None
    ) -> List[Any]:
        """获取翻译（批处理）"""
        return await self.batcher.submit(
            'get_translations',
            {'mod_id': mod_id, 'language': language}
        )


class RateLimiter:
    """请求速率限制器"""
    
    def __init__(
        self,
        max_requests: int = 100,
        time_window: int = 60  # 秒
    ):
        """初始化速率限制器
        
        Args:
            max_requests: 时间窗口内最大请求数
            time_window: 时间窗口（秒）
        """
        self.max_requests = max_requests
        self.time_window = time_window
        self._requests: Dict[str, List[float]] = defaultdict(list)
        self._lock = Lock()
    
    def is_allowed(self, key: str) -> bool:
        """检查是否允许请求
        
        Args:
            key: 限制键（如用户ID、IP地址等）
            
        Returns:
            是否允许请求
        """
        now = time.time()
        
        with self._lock:
            # 清理过期请求
            self._requests[key] = [
                timestamp for timestamp in self._requests[key]
                if now - timestamp < self.time_window
            ]
            
            # 检查是否超限
            if len(self._requests[key]) >= self.max_requests:
                return False
            
            # 记录请求
            self._requests[key].append(now)
            return True
    
    def get_remaining(self, key: str) -> int:
        """获取剩余请求数
        
        Args:
            key: 限制键
            
        Returns:
            剩余请求数
        """
        now = time.time()
        
        with self._lock:
            # 清理过期请求
            self._requests[key] = [
                timestamp for timestamp in self._requests[key]
                if now - timestamp < self.time_window
            ]
            
            return self.max_requests - len(self._requests[key])
    
    def reset(self, key: str):
        """重置限制
        
        Args:
            key: 限制键
        """
        with self._lock:
            self._requests.pop(key, None)