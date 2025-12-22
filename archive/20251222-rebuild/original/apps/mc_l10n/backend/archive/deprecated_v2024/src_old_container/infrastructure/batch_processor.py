"""
批处理优化器
提高大量数据处理的性能
"""

import asyncio
import logging
from collections.abc import Callable
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass
from datetime import datetime
from threading import Lock
from typing import Any, TypeVar

logger = logging.getLogger(__name__)

T = TypeVar("T")
R = TypeVar("R")


@dataclass
class BatchResult[R]:
    """批处理结果"""

    successful: list[R]
    failed: list[tuple[Any, Exception]]
    total_time: float

    @property
    def success_rate(self) -> float:
        total = len(self.successful) + len(self.failed)
        return len(self.successful) / total if total > 0 else 0.0


class BatchProcessor[T, R]:
    """批处理器

    用于高效处理大量数据项
    """

    def __init__(
        self, batch_size: int = 100, max_workers: int = 4, timeout: float | None = None
    ):
        """初始化批处理器

        Args:
            batch_size: 每批处理的项目数
            max_workers: 最大工作线程数
            timeout: 单个任务超时时间（秒）
        """
        self.batch_size = batch_size
        self.max_workers = max_workers
        self.timeout = timeout
        self._lock = Lock()
        self._progress = 0
        self._total = 0

    def process(
        self,
        items: list[T],
        processor: Callable[[T], R],
        progress_callback: Callable[[int, int], None] | None = None,
    ) -> BatchResult[R]:
        """处理项目列表

        Args:
            items: 要处理的项目列表
            processor: 处理函数
            progress_callback: 进度回调函数

        Returns:
            批处理结果
        """
        start_time = datetime.now()
        successful = []
        failed = []

        self._total = len(items)
        self._progress = 0

        # 分批处理
        batches = self._create_batches(items)

        with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            # 提交所有批次
            futures = []
            for batch in batches:
                future = executor.submit(self._process_batch, batch, processor)
                futures.append(future)

            # 收集结果
            for future in as_completed(futures):
                try:
                    batch_successful, batch_failed = future.result(timeout=self.timeout)
                    successful.extend(batch_successful)
                    failed.extend(batch_failed)

                    # 更新进度
                    with self._lock:
                        self._progress += len(batch_successful) + len(batch_failed)
                        if progress_callback:
                            progress_callback(self._progress, self._total)

                except Exception as e:
                    logger.error(f"Batch processing failed: {e}")
                    # 将整批标记为失败
                    batch_size = self.batch_size
                    failed.extend([(None, e)] * batch_size)

        total_time = (datetime.now() - start_time).total_seconds()

        return BatchResult(successful=successful, failed=failed, total_time=total_time)

    async def process_async(
        self,
        items: list[T],
        processor: Callable[[T], R],
        progress_callback: Callable[[int, int], None] | None = None,
    ) -> BatchResult[R]:
        """异步处理项目列表

        Args:
            items: 要处理的项目列表
            processor: 异步处理函数
            progress_callback: 进度回调函数

        Returns:
            批处理结果
        """
        start_time = datetime.now()
        successful = []
        failed = []

        self._total = len(items)
        self._progress = 0

        # 创建批次
        batches = self._create_batches(items)

        # 并发处理所有批次
        tasks = []
        for batch in batches:
            task = self._process_batch_async(batch, processor, progress_callback)
            tasks.append(task)

        # 等待所有任务完成
        results = await asyncio.gather(*tasks, return_exceptions=True)

        # 收集结果
        for result in results:
            if isinstance(result, Exception):
                logger.error(f"Batch processing failed: {result}")
                failed.extend([(None, result)] * self.batch_size)
            else:
                batch_successful, batch_failed = result
                successful.extend(batch_successful)
                failed.extend(batch_failed)

        total_time = (datetime.now() - start_time).total_seconds()

        return BatchResult(successful=successful, failed=failed, total_time=total_time)

    def _create_batches(self, items: list[T]) -> list[list[T]]:
        """创建批次"""
        batches = []
        for i in range(0, len(items), self.batch_size):
            batch = items[i : i + self.batch_size]
            batches.append(batch)
        return batches

    def _process_batch(
        self, batch: list[T], processor: Callable[[T], R]
    ) -> tuple[list[R], list[tuple[T, Exception]]]:
        """处理单个批次"""
        successful = []
        failed = []

        for item in batch:
            try:
                result = processor(item)
                successful.append(result)
            except Exception as e:
                logger.debug(f"Failed to process item: {e}")
                failed.append((item, e))

        return successful, failed

    async def _process_batch_async(
        self,
        batch: list[T],
        processor: Callable[[T], R],
        progress_callback: Callable[[int, int], None] | None = None,
    ) -> tuple[list[R], list[tuple[T, Exception]]]:
        """异步处理单个批次"""
        successful = []
        failed = []

        # 创建任务
        tasks = []
        for item in batch:
            if asyncio.iscoroutinefunction(processor):
                task = processor(item)
            else:
                task = asyncio.to_thread(processor, item)
            tasks.append((item, task))

        # 执行任务
        for item, task in tasks:
            try:
                result = await task
                successful.append(result)
            except Exception as e:
                logger.debug(f"Failed to process item: {e}")
                failed.append((item, e))

            # 更新进度
            with self._lock:
                self._progress += 1
                if progress_callback:
                    progress_callback(self._progress, self._total)

        return successful, failed


class BulkOperationOptimizer:
    """批量操作优化器

    用于优化数据库批量操作
    """

    @staticmethod
    def chunk_inserts(items: list[Any], chunk_size: int = 1000) -> list[list[Any]]:
        """将插入操作分块

        Args:
            items: 要插入的项目
            chunk_size: 每块大小

        Returns:
            分块后的列表
        """
        chunks = []
        for i in range(0, len(items), chunk_size):
            chunk = items[i : i + chunk_size]
            chunks.append(chunk)
        return chunks

    @staticmethod
    def optimize_queries(queries: list[str]) -> list[str]:
        """优化查询列表

        Args:
            queries: SQL查询列表

        Returns:
            优化后的查询列表
        """
        # 合并相似查询
        optimized = []
        seen = set()

        for query in queries:
            # 简单去重
            query_hash = hash(query.strip().lower())
            if query_hash not in seen:
                seen.add(query_hash)
                optimized.append(query)

        return optimized

    @staticmethod
    def batch_update(
        connection, table: str, updates: list[dict[str, Any]], key_field: str = "id"
    ) -> int:
        """批量更新

        Args:
            connection: 数据库连接
            table: 表名
            updates: 更新数据列表
            key_field: 主键字段名

        Returns:
            更新的行数
        """
        if not updates:
            return 0

        updated = 0

        # 构建批量更新SQL
        for update_data in updates:
            key_value = update_data.pop(key_field)

            set_clause = ", ".join([f"{k} = ?" for k in update_data.keys()])
            values = list(update_data.values()) + [key_value]

            sql = f"UPDATE {table} SET {set_clause} WHERE {key_field} = ?"

            cursor = connection.execute(sql, values)
            updated += cursor.rowcount

        connection.commit()
        return updated


class AsyncBatchQueue:
    """异步批处理队列

    累积项目并批量处理
    """

    def __init__(
        self,
        processor: Callable[[list[Any]], None],
        batch_size: int = 100,
        flush_interval: float = 1.0,
    ):
        """初始化批处理队列

        Args:
            processor: 批处理函数
            batch_size: 批大小
            flush_interval: 刷新间隔（秒）
        """
        self.processor = processor
        self.batch_size = batch_size
        self.flush_interval = flush_interval
        self._queue = []
        self._lock = Lock()
        self._timer = None
        self._running = True

    def add(self, item: Any):
        """添加项目到队列"""
        with self._lock:
            self._queue.append(item)

            # 如果达到批大小，立即处理
            if len(self._queue) >= self.batch_size:
                self._flush()
            else:
                # 启动定时器
                self._start_timer()

    def _flush(self):
        """刷新队列"""
        if not self._queue:
            return

        # 获取当前批次
        batch = self._queue[: self.batch_size]
        self._queue = self._queue[self.batch_size :]

        # 处理批次
        try:
            self.processor(batch)
        except Exception as e:
            logger.error(f"Batch processing failed: {e}")

    def _start_timer(self):
        """启动刷新定时器"""
        if self._timer:
            self._timer.cancel()

        if self._running:
            import threading

            self._timer = threading.Timer(self.flush_interval, self._timeout_flush)
            self._timer.start()

    def _timeout_flush(self):
        """定时刷新"""
        with self._lock:
            self._flush()

    def flush_all(self):
        """刷新所有待处理项目"""
        with self._lock:
            while self._queue:
                self._flush()

    def stop(self):
        """停止队列"""
        self._running = False
        if self._timer:
            self._timer.cancel()
        self.flush_all()
