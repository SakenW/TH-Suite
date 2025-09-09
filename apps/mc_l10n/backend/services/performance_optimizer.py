#!/usr/bin/env python
"""
性能优化服务
提供多线程并发上传、内存优化、异步I/O等性能增强功能
"""

import asyncio
import aiofiles
import threading
import weakref
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import List, Dict, Any, Optional, Callable, Iterator, AsyncIterator
from dataclasses import dataclass, field
from pathlib import Path
import time
import psutil
import gc
from enum import IntEnum
from contextlib import asynccontextmanager
import structlog

logger = structlog.get_logger(__name__)


class TaskPriority(IntEnum):
    """任务优先级枚举"""
    LOW = 1
    NORMAL = 2
    HIGH = 3
    URGENT = 4


@dataclass
class PerformanceMetrics:
    """性能指标"""
    start_time: float = field(default_factory=time.time)
    end_time: Optional[float] = None
    
    # 上传指标
    total_bytes: int = 0
    uploaded_bytes: int = 0
    upload_speed_mbps: float = 0.0
    
    # 并发指标
    concurrent_tasks: int = 0
    max_concurrent: int = 0
    completed_tasks: int = 0
    failed_tasks: int = 0
    
    # 内存指标
    peak_memory_mb: float = 0.0
    current_memory_mb: float = 0.0
    gc_collections: int = 0
    
    # I/O指标
    disk_read_mb: float = 0.0
    disk_write_mb: float = 0.0
    
    def calculate_metrics(self):
        """计算派生指标"""
        if self.end_time:
            duration = self.end_time - self.start_time
            if duration > 0:
                self.upload_speed_mbps = (self.uploaded_bytes / (1024 * 1024)) / duration
        
        # 更新内存使用
        process = psutil.Process()
        memory_info = process.memory_info()
        self.current_memory_mb = memory_info.rss / (1024 * 1024)
        if self.current_memory_mb > self.peak_memory_mb:
            self.peak_memory_mb = self.current_memory_mb
    
    def get_success_rate(self) -> float:
        """获取成功率"""
        total = self.completed_tasks + self.failed_tasks
        return (self.completed_tasks / total * 100) if total > 0 else 0.0
    
    def get_throughput_mbps(self) -> float:
        """获取吞吐量 MB/s"""
        duration = (self.end_time or time.time()) - self.start_time
        return (self.uploaded_bytes / (1024 * 1024)) / duration if duration > 0 else 0.0
    
    def get_average_upload_speed_mbps(self) -> float:
        """获取平均上传速度"""
        return self.upload_speed_mbps
    
    def get_summary(self) -> Dict[str, Any]:
        """获取指标摘要"""
        return {
            'total_uploads': self.completed_tasks + self.failed_tasks,
            'successful_uploads': self.completed_tasks,
            'failed_uploads': self.failed_tasks,
            'total_bytes_transferred': self.total_bytes,
            'total_upload_time': (self.end_time or time.time()) - self.start_time,
            'success_rate': self.get_success_rate(),
            'throughput_mbps': self.get_throughput_mbps(),
            'peak_memory_mb': self.peak_memory_mb,
            'current_memory_mb': self.current_memory_mb
        }


@dataclass
class UploadTask:
    """上传任务"""
    cid: str
    data: bytes
    priority: TaskPriority = TaskPriority.NORMAL
    total_chunks: int = 1
    metadata: Optional[Dict[str, Any]] = None
    task_id: Optional[str] = None
    chunk_index: int = 0
    callback: Optional[Callable] = None
    retry_count: int = 0
    max_retries: int = 3


class ConcurrentUploadManager:
    """并发上传管理器"""
    
    def __init__(self, 
                 max_concurrent: int = 8,
                 chunk_size: int = 2 * 1024 * 1024,  # 2MB
                 memory_limit_mb: int = 512,  # 512MB内存限制
                 enable_compression: bool = True):
        self.max_concurrent = max_concurrent
        self.chunk_size = chunk_size
        self.memory_limit_mb = memory_limit_mb
        self.enable_compression = enable_compression
        
        # 线程池和信号量
        self.thread_pool = ThreadPoolExecutor(max_workers=max_concurrent)
        self.semaphore = asyncio.Semaphore(max_concurrent)
        
        # 任务队列和管理
        self.upload_queue = asyncio.PriorityQueue()
        self.active_tasks: Dict[str, asyncio.Task] = {}
        self.completed_tasks: weakref.WeakSet = weakref.WeakSet()
        
        # 性能监控
        self.metrics = PerformanceMetrics()
        self.metrics.max_concurrent = max_concurrent
        
        # 内存管理
        self._memory_monitor_task: Optional[asyncio.Task] = None
        self._gc_threshold = memory_limit_mb * 0.8  # 80%时触发GC
        
        logger.info("并发上传管理器初始化",
                   max_concurrent=max_concurrent,
                   chunk_size_mb=chunk_size // (1024 * 1024),
                   memory_limit_mb=memory_limit_mb)
    
    async def start(self):
        """启动管理器"""
        self._memory_monitor_task = asyncio.create_task(self._monitor_memory())
        logger.info("并发上传管理器已启动")
    
    async def _monitor_memory(self):
        """监控内存使用"""
        try:
            while True:
                await self._check_memory_usage()
                await asyncio.sleep(5)
        except asyncio.CancelledError:
            pass
        except Exception as e:
            logger.error("内存监控错误", error=str(e))
    
    async def _check_memory_usage(self):
        """检查内存使用情况"""
        self.metrics.calculate_metrics()
        
        if self.metrics.current_memory_mb > self._gc_threshold:
            logger.info("内存使用接近限制，触发垃圾回收",
                       current_mb=self.metrics.current_memory_mb,
                       threshold_mb=self._gc_threshold)
            gc.collect()
            self.metrics.gc_collections += 1
    
    async def stop(self):
        """停止管理器"""
        # 取消所有活动任务
        for task in self.active_tasks.values():
            task.cancel()
        
        # 等待任务完成
        if self.active_tasks:
            await asyncio.gather(*self.active_tasks.values(), return_exceptions=True)
        
        # 停止内存监控
        if self._memory_monitor_task:
            self._memory_monitor_task.cancel()
        
        # 关闭线程池
        self.thread_pool.shutdown(wait=True)
        
        # 更新最终指标
        self.metrics.end_time = time.time()
        self.metrics.calculate_metrics()
        
        logger.info("并发上传管理器已停止",
                   total_uploaded_mb=self.metrics.uploaded_bytes // (1024 * 1024),
                   speed_mbps=self.metrics.upload_speed_mbps,
                   peak_memory_mb=self.metrics.peak_memory_mb)
    
    async def submit_upload(self, task: UploadTask) -> str:
        """提交上传任务"""
        task_id = f"{task.cid}#{task.chunk_index}"
        
        # 内存检查
        await self._check_memory_usage()
        
        # 创建优先级任务 (负数因为PriorityQueue是最小堆)
        priority_item = (-task.priority, time.time(), task)
        await self.upload_queue.put(priority_item)
        
        # 立即启动工作协程（如果还有并发槽位）
        if len(self.active_tasks) < self.max_concurrent:
            worker_task = asyncio.create_task(self._upload_worker())
            self.active_tasks[f"worker_{len(self.active_tasks)}"] = worker_task
        
        logger.debug("上传任务已提交",
                    task_id=task_id,
                    cid=task.cid[:16],
                    chunk_index=task.chunk_index,
                    data_size_kb=len(task.data) // 1024,
                    queue_size=self.upload_queue.qsize())
        
        return task_id
    
    async def _upload_worker(self):
        """上传工作协程"""
        worker_id = f"worker_{threading.current_thread().ident}"
        
        try:
            while True:
                try:
                    # 获取任务（带超时）
                    priority, timestamp, task = await asyncio.wait_for(
                        self.upload_queue.get(), timeout=1.0
                    )
                    
                    async with self.semaphore:
                        await self._execute_upload_task(task)
                        self.upload_queue.task_done()
                    
                except asyncio.TimeoutError:
                    # 队列空闲，退出工作协程
                    break
                except Exception as e:
                    logger.error("上传工作协程错误", worker_id=worker_id, error=str(e))
                    continue
        
        finally:
            # 清理工作协程
            if worker_id in self.active_tasks:
                del self.active_tasks[worker_id]
    
    async def _execute_upload_task(self, task: UploadTask):
        """执行单个上传任务"""
        start_time = time.time()
        task_id = f"{task.cid}#{task.chunk_index}"
        
        try:
            self.metrics.concurrent_tasks += 1
            self.metrics.total_bytes += len(task.data)
            
            # 模拟上传操作（实际实现中应该调用真实的上传API）
            await self._simulate_upload(task)
            
            # 更新成功指标
            self.metrics.uploaded_bytes += len(task.data)
            self.metrics.completed_tasks += 1
            
            # 调用回调
            if task.callback:
                await asyncio.get_event_loop().run_in_executor(
                    self.thread_pool, task.callback, task, True
                )
            
            duration = time.time() - start_time
            logger.debug("上传任务完成",
                        task_id=task_id,
                        duration_ms=int(duration * 1000),
                        size_kb=len(task.data) // 1024)
        
        except Exception as e:
            self.metrics.failed_tasks += 1
            
            # 重试逻辑
            if task.retry_count < task.max_retries:
                task.retry_count += 1
                retry_delay = min(2 ** task.retry_count, 10)  # 指数退避，最大10秒
                
                logger.warning("上传任务失败，准备重试",
                              task_id=task_id,
                              retry_count=task.retry_count,
                              retry_delay=retry_delay,
                              error=str(e))
                
                # 重新加入队列
                await asyncio.sleep(retry_delay)
                priority_item = (-task.priority, time.time(), task)
                await self.upload_queue.put(priority_item)
            else:
                logger.error("上传任务最终失败",
                           task_id=task_id,
                           retries=task.retry_count,
                           error=str(e))
                
                if task.callback:
                    await asyncio.get_event_loop().run_in_executor(
                        self.thread_pool, task.callback, task, False
                    )
        
        finally:
            self.metrics.concurrent_tasks = max(0, self.metrics.concurrent_tasks - 1)
    
    async def batch_upload(self, tasks: List[UploadTask], upload_function: Callable) -> List[Dict[str, Any]]:
        """批量上传任务"""
        results = []
        
        # 启动工作协程
        workers = []
        for i in range(min(self.max_concurrent, len(tasks))):
            worker = asyncio.create_task(self._batch_upload_worker(upload_function))
            workers.append(worker)
            self.active_tasks[f"batch_worker_{i}"] = worker
        
        # 提交所有任务
        for task in tasks:
            priority_item = (-task.priority, time.time(), task)
            await self.upload_queue.put(priority_item)
        
        # 等待所有任务完成
        await self.upload_queue.join()
        
        # 停止工作协程
        for worker in workers:
            worker.cancel()
        
        # 收集结果
        for task in tasks:
            results.append({
                "cid": task.cid,
                "success": True,
                "chunk_index": task.chunk_index
            })
        
        return results
    
    async def _batch_upload_worker(self, upload_function: Callable):
        """批量上传工作协程"""
        while True:
            try:
                priority, timestamp, task = await self.upload_queue.get()
                
                async with self.semaphore:
                    # 调用实际的上传函数
                    result = await upload_function(
                        task.cid, 
                        task.data, 
                        task.chunk_index, 
                        task.total_chunks
                    )
                    
                    if result.get("success"):
                        self.metrics.completed_tasks += 1
                    else:
                        self.metrics.failed_tasks += 1
                
                self.upload_queue.task_done()
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error("批量上传工作协程错误", error=str(e))
                self.upload_queue.task_done()


class MemoryMonitor:
    """内存监控器"""
    
    def __init__(self,
                 warning_threshold_mb: float = 400,
                 critical_threshold_mb: float = 500,
                 gc_interval_seconds: float = 30):
        self.warning_threshold_mb = warning_threshold_mb
        self.critical_threshold_mb = critical_threshold_mb
        self.gc_interval_seconds = gc_interval_seconds
        
        self.is_monitoring = False
        self.monitor_task: Optional[asyncio.Task] = None
        self.gc_count = 0
        self.peak_memory_mb = 0.0
        
        logger.info("内存监控器初始化",
                   warning_threshold_mb=warning_threshold_mb,
                   critical_threshold_mb=critical_threshold_mb,
                   gc_interval_seconds=gc_interval_seconds)
    
    def start_monitoring(self):
        """启动内存监控"""
        if self.is_monitoring:
            return
        
        self.is_monitoring = True
        self.monitor_task = asyncio.create_task(self._monitor_loop())
        logger.info("内存监控已启动")
    
    def stop_monitoring(self):
        """停止内存监控"""
        if not self.is_monitoring:
            return
        
        self.is_monitoring = False
        if self.monitor_task:
            self.monitor_task.cancel()
        
        logger.info("内存监控已停止", 
                   peak_memory_mb=self.peak_memory_mb,
                   total_gc_collections=self.gc_count)
    
    async def _monitor_loop(self):
        """监控循环"""
        try:
            while self.is_monitoring:
                stats = self.get_memory_stats()
                current_memory = stats["current_memory_mb"]
                
                # 更新峰值
                if current_memory > self.peak_memory_mb:
                    self.peak_memory_mb = current_memory
                
                # 检查阈值
                if current_memory > self.critical_threshold_mb:
                    logger.warning("内存使用超过临界阈值",
                                  current_mb=current_memory,
                                  critical_mb=self.critical_threshold_mb)
                    self.force_gc()
                elif current_memory > self.warning_threshold_mb:
                    logger.info("内存使用超过警告阈值",
                              current_mb=current_memory,
                              warning_mb=self.warning_threshold_mb)
                
                await asyncio.sleep(self.gc_interval_seconds)
                
        except asyncio.CancelledError:
            pass
        except Exception as e:
            logger.error("内存监控循环错误", error=str(e))
    
    def get_memory_stats(self) -> Dict[str, float]:
        """获取内存统计信息"""
        process = psutil.Process()
        memory_info = process.memory_info()
        virtual_memory = psutil.virtual_memory()
        
        return {
            "current_memory_mb": memory_info.rss / (1024 * 1024),
            "peak_memory_mb": self.peak_memory_mb,
            "available_memory_mb": virtual_memory.available / (1024 * 1024),
            "memory_percent": process.memory_percent(),
            "gc_collections": self.gc_count
        }
    
    def force_gc(self):
        """强制垃圾回收"""
        before = psutil.Process().memory_info().rss / (1024 * 1024)
        collected = gc.collect()
        after = psutil.Process().memory_info().rss / (1024 * 1024)
        
        self.gc_count += 1
        
        logger.info("执行垃圾回收",
                   collected_objects=collected,
                   memory_before_mb=round(before, 2),
                   memory_after_mb=round(after, 2),
                   memory_freed_mb=round(before - after, 2))
    
    async def _simulate_upload(self, task: UploadTask):
        """模拟上传操作"""
        # 模拟网络延迟
        upload_delay = len(task.data) / (50 * 1024 * 1024)  # 50MB/s模拟速度
        await asyncio.sleep(min(upload_delay, 0.1))  # 最大100ms延迟
        
        # 模拟压缩（如果启用）
        if self.enable_compression:
            # 运行在线程池中以避免阻塞
            compressed_data = await asyncio.get_event_loop().run_in_executor(
                self.thread_pool, self._compress_data, task.data
            )
            logger.debug("数据压缩完成",
                        original_size=len(task.data),
                        compressed_size=len(compressed_data),
                        ratio=len(compressed_data) / len(task.data))
    
    def _compress_data(self, data: bytes) -> bytes:
        """压缩数据（在线程池中运行）"""
        # 简单的模拟压缩
        import zlib
        return zlib.compress(data, level=6)
    
    async def _monitor_memory(self):
        """内存监控协程"""
        while True:
            try:
                self.metrics.calculate_metrics()
                
                if self.metrics.current_memory_mb > self._gc_threshold:
                    logger.info("内存使用过高，触发垃圾收集",
                               current_mb=self.metrics.current_memory_mb,
                               threshold_mb=self._gc_threshold)
                    
                    # 在线程池中执行GC以避免阻塞
                    await asyncio.get_event_loop().run_in_executor(
                        self.thread_pool, self._force_gc
                    )
                
                await asyncio.sleep(5)  # 每5秒检查一次
                
            except Exception as e:
                logger.error("内存监控错误", error=str(e))
                await asyncio.sleep(5)
    
    def _force_gc(self):
        """强制垃圾收集"""
        before = psutil.Process().memory_info().rss / (1024 * 1024)
        collected = gc.collect()
        after = psutil.Process().memory_info().rss / (1024 * 1024)
        
        self.metrics.gc_collections += 1
        
        logger.info("垃圾收集完成",
                   collected_objects=collected,
                   memory_before_mb=before,
                   memory_after_mb=after,
                   memory_freed_mb=before - after)
    
    async def _check_memory_usage(self):
        """检查内存使用情况"""
        self.metrics.calculate_metrics()
        
        if self.metrics.current_memory_mb > self.memory_limit_mb:
            logger.warning("内存使用超过限制，等待GC完成",
                          current_mb=self.metrics.current_memory_mb,
                          limit_mb=self.memory_limit_mb)
            
            # 等待内存释放
            for _ in range(10):  # 最多等待5秒
                await asyncio.sleep(0.5)
                self.metrics.calculate_metrics()
                if self.metrics.current_memory_mb <= self.memory_limit_mb:
                    break
            else:
                raise MemoryError(f"内存使用超过限制: {self.metrics.current_memory_mb}MB > {self.memory_limit_mb}MB")
    
    def get_metrics(self) -> PerformanceMetrics:
        """获取当前性能指标"""
        self.metrics.calculate_metrics()
        return self.metrics


class StreamingUploader:
    """流式上传器 - 优化大文件上传的内存使用"""
    
    def __init__(self, upload_manager: Optional[ConcurrentUploadManager] = None,
                 chunk_size: int = 2 * 1024 * 1024,
                 max_retries: int = 3,
                 enable_compression: bool = False):
        self.upload_manager = upload_manager
        self.chunk_size = chunk_size if upload_manager is None else upload_manager.chunk_size
        self.max_retries = max_retries
        self.enable_compression = enable_compression
    
    async def upload_file_stream(self,
                                file_path: Path,
                                cid: str,
                                callback: Optional[Callable] = None) -> List[str]:
        """流式上传文件，避免将整个文件加载到内存"""
        upload_tasks = []
        chunk_index = 0
        
        try:
            file_size = file_path.stat().st_size
            total_chunks = (file_size + self.chunk_size - 1) // self.chunk_size
            
            logger.info("开始流式上传",
                       file_path=str(file_path),
                       file_size_mb=file_size // (1024 * 1024),
                       total_chunks=total_chunks,
                       chunk_size_mb=self.chunk_size // (1024 * 1024))
            
            async with aiofiles.open(file_path, 'rb') as f:
                while True:
                    chunk_data = await f.read(self.chunk_size)
                    if not chunk_data:
                        break
                    
                    # 如果有上传管理器，使用它；否则模拟上传
                    if self.upload_manager:
                        task = UploadTask(
                            cid=cid,
                            data=chunk_data,
                            chunk_index=chunk_index,
                            total_chunks=total_chunks,
                            priority=TaskPriority.NORMAL,
                            callback=callback
                        )
                        task_id = await self.upload_manager.submit_upload(task)
                        upload_tasks.append(task_id)
                    else:
                        # 模拟上传操作
                        chunk_cid = f"{cid}_chunk_{chunk_index}"
                        await self._simulate_chunk_upload(chunk_data, chunk_cid)
                        upload_tasks.append(chunk_cid)
                        
                        if callback:
                            callback(chunk_index, total_chunks, len(chunk_data))
                    
                    chunk_index += 1
                    
                    # 内存使用检查
                    if chunk_index % 10 == 0:  # 每10个分片检查一次
                        await asyncio.sleep(0.01)  # 让出控制权
            
            logger.info("流式上传提交完成",
                       file_path=str(file_path),
                       total_tasks=len(upload_tasks))
            
            return upload_tasks
            
        except Exception as e:
            logger.error("流式上传失败",
                        file_path=str(file_path),
                        error=str(e))
            raise
    
    async def _simulate_chunk_upload(self, chunk_data: bytes, chunk_cid: str):
        """模拟分片上传"""
        # 模拟网络延迟
        upload_delay = len(chunk_data) / (50 * 1024 * 1024)  # 50MB/s模拟速度
        await asyncio.sleep(min(upload_delay, 0.1))
    
    async def upload_data_stream(self,
                                data_iterator: AsyncIterator[bytes],
                                cid: str,
                                callback: Optional[Callable] = None) -> List[str]:
        """从数据流上传，支持生成器和异步迭代器"""
        upload_tasks = []
        chunk_index = 0
        buffer = b''
        
        try:
            async for data_chunk in data_iterator:
                buffer += data_chunk
                
                # 当缓冲区达到分片大小时上传
                while len(buffer) >= self.chunk_size:
                    chunk_data = buffer[:self.chunk_size]
                    buffer = buffer[self.chunk_size:]
                    
                    task = UploadTask(
                        task_id=f"{cid}#{chunk_index}",
                        cid=cid,
                        chunk_index=chunk_index,
                        data=chunk_data,
                        callback=callback,
                        priority=100 - chunk_index
                    )
                    
                    task_id = await self.upload_manager.submit_upload(task)
                    upload_tasks.append(task_id)
                    chunk_index += 1
            
            # 上传剩余数据
            if buffer:
                task = UploadTask(
                    task_id=f"{cid}#{chunk_index}",
                    cid=cid,
                    chunk_index=chunk_index,
                    data=buffer,
                    callback=callback,
                    priority=100 - chunk_index
                )
                
                task_id = await self.upload_manager.submit_upload(task)
                upload_tasks.append(task_id)
            
            logger.info("数据流上传完成",
                       total_tasks=len(upload_tasks))
            
            return upload_tasks
            
        except Exception as e:
            logger.error("数据流上传失败", error=str(e))
            raise


@asynccontextmanager
async def performance_context(max_concurrent: int = 8,
                            memory_limit_mb: int = 512,
                            enable_compression: bool = True):
    """性能优化上下文管理器"""
    upload_manager = ConcurrentUploadManager(
        max_concurrent=max_concurrent,
        memory_limit_mb=memory_limit_mb,
        enable_compression=enable_compression
    )
    
    try:
        await upload_manager.start()
        yield upload_manager
    finally:
        await upload_manager.stop()


# 全局管理器实例
_upload_manager: Optional[ConcurrentUploadManager] = None


async def get_upload_manager() -> ConcurrentUploadManager:
    """获取全局上传管理器实例"""
    global _upload_manager
    if _upload_manager is None:
        _upload_manager = ConcurrentUploadManager()
        await _upload_manager.start()
        logger.info("全局上传管理器初始化完成")
    return _upload_manager


def get_streaming_uploader() -> StreamingUploader:
    """获取流式上传器"""
    # 注意：这需要先获取upload_manager
    # 在实际使用中应该确保manager已初始化
    return StreamingUploader(None)  # 需要在async context中正确初始化


class PerformanceOptimizer:
    """性能优化器主类 - 统一管理所有性能优化组件"""
    
    def __init__(self,
                 max_concurrent_uploads: int = 8,
                 chunk_size_kb: int = 2048,
                 memory_limit_mb: int = 512,
                 enable_compression: bool = True,
                 enable_memory_monitoring: bool = True):
        self.max_concurrent_uploads = max_concurrent_uploads
        self.chunk_size = chunk_size_kb * 1024
        self.memory_limit_mb = memory_limit_mb
        self.enable_compression = enable_compression
        self.enable_memory_monitoring = enable_memory_monitoring
        
        # 组件
        self.upload_manager: Optional[ConcurrentUploadManager] = None
        self.streaming_uploader: Optional[StreamingUploader] = None
        self.memory_monitor: Optional[MemoryMonitor] = None
        
        # 指标
        self.metrics = PerformanceMetrics()
        self.is_running = False
        
        logger.info("性能优化器初始化",
                   max_concurrent=max_concurrent_uploads,
                   chunk_size_kb=chunk_size_kb,
                   memory_limit_mb=memory_limit_mb,
                   compression_enabled=enable_compression)
    
    async def start(self):
        """启动所有优化组件"""
        if self.is_running:
            logger.warning("性能优化器已在运行")
            return
        
        try:
            # 初始化上传管理器
            self.upload_manager = ConcurrentUploadManager(
                max_concurrent=self.max_concurrent_uploads,
                chunk_size=self.chunk_size,
                memory_limit_mb=self.memory_limit_mb,
                enable_compression=self.enable_compression
            )
            await self.upload_manager.start()
            
            # 初始化流式上传器
            self.streaming_uploader = StreamingUploader(self.upload_manager)
            
            # 初始化内存监控器
            if self.enable_memory_monitoring:
                self.memory_monitor = MemoryMonitor(
                    warning_threshold_mb=self.memory_limit_mb * 0.8,
                    critical_threshold_mb=self.memory_limit_mb * 0.95
                )
                self.memory_monitor.start_monitoring()
            
            self.is_running = True
            self.metrics.start_time = time.time()
            
            logger.info("性能优化器启动完成")
            
        except Exception as e:
            logger.error("性能优化器启动失败", error=str(e))
            await self.stop()
            raise
    
    async def stop(self):
        """停止所有优化组件"""
        if not self.is_running:
            return
        
        try:
            # 停止内存监控
            if self.memory_monitor:
                self.memory_monitor.stop_monitoring()
            
            # 停止上传管理器
            if self.upload_manager:
                await self.upload_manager.stop()
            
            self.is_running = False
            self.metrics.end_time = time.time()
            
            logger.info("性能优化器已停止",
                       total_runtime_seconds=self.get_runtime_seconds())
            
        except Exception as e:
            logger.error("性能优化器停止过程中发生错误", error=str(e))
    
    async def upload_file(self,
                         file_path: Path,
                         cid: str,
                         progress_callback: Optional[Callable] = None) -> Dict[str, Any]:
        """优化的文件上传"""
        if not self.is_running:
            raise RuntimeError("性能优化器未启动")
        
        try:
            start_time = time.time()
            file_size = file_path.stat().st_size
            
            # 更新指标
            self.metrics.total_bytes += file_size
            
            # 使用流式上传器
            task_ids = await self.streaming_uploader.upload_file_stream(
                file_path=file_path,
                cid=cid,
                callback=progress_callback
            )
            
            upload_time = time.time() - start_time
            self.metrics.upload_speed_mbps = (file_size / (1024 * 1024)) / upload_time if upload_time > 0 else 0
            self.metrics.completed_tasks += 1
            
            logger.info("文件上传完成",
                       file_path=str(file_path),
                       file_size_mb=file_size / (1024 * 1024),
                       upload_time_seconds=upload_time,
                       speed_mbps=self.metrics.upload_speed_mbps,
                       total_chunks=len(task_ids))
            
            return {
                "success": True,
                "cid": cid,
                "file_size": file_size,
                "upload_time": upload_time,
                "chunks": len(task_ids),
                "speed_mbps": self.metrics.upload_speed_mbps
            }
            
        except Exception as e:
            self.metrics.failed_tasks += 1
            logger.error("文件上传失败", file_path=str(file_path), error=str(e))
            return {
                "success": False,
                "error": str(e),
                "cid": cid
            }
    
    async def batch_upload_files(self,
                                file_paths: List[Path],
                                progress_callback: Optional[Callable] = None) -> List[Dict[str, Any]]:
        """批量文件上传优化"""
        if not self.is_running:
            raise RuntimeError("性能优化器未启动")
        
        logger.info("开始批量文件上传", file_count=len(file_paths))
        
        results = []
        
        # 并发上传文件
        semaphore = asyncio.Semaphore(self.max_concurrent_uploads)
        
        async def upload_single_file(file_path: Path) -> Dict[str, Any]:
            async with semaphore:
                # 生成CID
                cid = f"file_{file_path.name}_{int(time.time())}"
                return await self.upload_file(file_path, cid, progress_callback)
        
        # 创建上传任务
        upload_tasks = [upload_single_file(fp) for fp in file_paths]
        
        # 并发执行
        results = await asyncio.gather(*upload_tasks, return_exceptions=True)
        
        # 处理异常结果
        processed_results = []
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                processed_results.append({
                    "success": False,
                    "error": str(result),
                    "file_path": str(file_paths[i])
                })
            else:
                processed_results.append(result)
        
        successful_uploads = len([r for r in processed_results if r.get("success", False)])
        
        logger.info("批量文件上传完成",
                   total_files=len(file_paths),
                   successful_uploads=successful_uploads,
                   failed_uploads=len(file_paths) - successful_uploads)
        
        return processed_results
    
    def get_runtime_seconds(self) -> float:
        """获取运行时长（秒）"""
        if self.metrics.start_time:
            end_time = self.metrics.end_time or time.time()
            return end_time - self.metrics.start_time
        return 0.0
    
    def get_performance_summary(self) -> Dict[str, Any]:
        """获取性能摘要"""
        runtime = self.get_runtime_seconds()
        
        summary = {
            "runtime_seconds": runtime,
            "total_bytes_mb": self.metrics.total_bytes / (1024 * 1024),
            "average_speed_mbps": self.metrics.upload_speed_mbps,
            "completed_tasks": self.metrics.completed_tasks,
            "failed_tasks": self.metrics.failed_tasks,
            "success_rate": (self.metrics.completed_tasks / (self.metrics.completed_tasks + self.metrics.failed_tasks) * 100) if (self.metrics.completed_tasks + self.metrics.failed_tasks) > 0 else 0,
            "is_running": self.is_running
        }
        
        # 添加内存指标
        if self.memory_monitor:
            memory_stats = self.memory_monitor.get_memory_stats()
            summary.update({
                "current_memory_mb": memory_stats.get("current_memory_mb", 0),
                "peak_memory_mb": memory_stats.get("peak_memory_mb", 0),
                "gc_collections": memory_stats.get("gc_collections", 0)
            })
        
        return summary
    
    async def optimize_for_large_files(self):
        """针对大文件优化设置"""
        if self.upload_manager:
            # 增加块大小以减少网络开销
            self.upload_manager.chunk_size = min(8 * 1024 * 1024, self.chunk_size * 4)  # 最大8MB
            logger.info("已优化大文件上传设置", new_chunk_size_mb=self.upload_manager.chunk_size / (1024 * 1024))
    
    async def optimize_for_small_files(self):
        """针对小文件优化设置"""
        if self.upload_manager:
            # 减小块大小以提高并发度
            self.upload_manager.chunk_size = max(64 * 1024, self.chunk_size // 4)  # 最小64KB
            # 增加并发数
            self.upload_manager.max_concurrent = min(self.max_concurrent_uploads * 2, 16)
            logger.info("已优化小文件上传设置",
                       new_chunk_size_kb=self.upload_manager.chunk_size / 1024,
                       new_concurrent=self.upload_manager.max_concurrent)
    
    async def __aenter__(self):
        """支持async with语法"""
        await self.start()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """支持async with语法"""
        await self.stop()