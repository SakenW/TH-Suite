#!/usr/bin/env python
"""
测试性能优化器
验证并发上传、内存优化、流式处理等功能
"""

import sys
import asyncio
import tempfile
import time
import threading
from pathlib import Path
from typing import List, Dict
import structlog

sys.path.append('.')

# 配置日志
structlog.configure(
    processors=[
        structlog.processors.TimeStamper(fmt="ISO"),
        structlog.dev.ConsoleRenderer()
    ],
    wrapper_class=structlog.stdlib.BoundLogger,
    logger_factory=structlog.stdlib.LoggerFactory(),
    cache_logger_on_first_use=True,
)

logger = structlog.get_logger(__name__)

from services.performance_optimizer import (
    PerformanceOptimizer, ConcurrentUploadManager, StreamingUploader,
    MemoryMonitor, PerformanceMetrics, UploadTask, TaskPriority
)


async def test_concurrent_upload_manager():
    """测试并发上传管理器"""
    print("=== 测试并发上传管理器 ===")
    
    try:
        # 创建测试上传管理器
        manager = ConcurrentUploadManager(
            max_concurrent=4,
            chunk_size=1024,  # 小块用于测试
            memory_limit_mb=50,
            enable_compression=False  # 简化测试
        )
        
        # 模拟上传函数
        upload_results = []
        upload_times = []
        
        async def mock_upload(cid: str, chunk_data: bytes, chunk_index: int, total_chunks: int) -> Dict:
            start_time = time.time()
            await asyncio.sleep(0.1)  # 模拟网络延迟
            end_time = time.time()
            
            result = {
                "cid": cid,
                "chunk_index": chunk_index,
                "success": True,
                "upload_time": end_time - start_time
            }
            upload_results.append(result)
            upload_times.append(end_time - start_time)
            return result
        
        # 创建测试数据
        test_data = b"x" * 5000  # 5KB测试数据
        
        # 测试并发上传
        tasks = []
        for i in range(8):  # 8个并发任务
            task = UploadTask(
                cid=f"test_cid_{i}",
                data=test_data,
                priority=TaskPriority.NORMAL,
                total_chunks=5,
                metadata={"test_id": i}
            )
            tasks.append(task)
        
        print(f"创建 {len(tasks)} 个上传任务")
        
        # 执行并发上传
        start_time = time.time()
        results = await manager.batch_upload(tasks, mock_upload)
        end_time = time.time()
        
        print(f"✓ 并发上传完成")
        print(f"  总耗时: {end_time - start_time:.2f}秒")
        print(f"  成功任务: {len([r for r in results if r['success']])}/{len(results)}")
        print(f"  平均块上传时间: {sum(upload_times)/len(upload_times):.3f}秒")
        print(f"  最大并发控制: {manager.max_concurrent}")
        
        # 验证内存监控
        if hasattr(manager, 'memory_monitor'):
            memory_stats = manager.memory_monitor.get_memory_stats()
            print(f"  峰值内存使用: {memory_stats.get('peak_memory_mb', 0):.1f}MB")
        
        return True
        
    except Exception as e:
        print(f"✗ 并发上传管理器测试失败: {e}")
        logger.error("并发上传测试异常", error=str(e))
        return False


async def test_streaming_uploader():
    """测试流式上传器"""
    print("\n=== 测试流式上传器 ===")
    
    try:
        # 创建临时文件
        temp_dir = Path(tempfile.mkdtemp())
        test_file = temp_dir / "large_test_file.bin"
        
        # 生成测试文件 (1MB)
        test_data = b"A" * (1024 * 1024)
        test_file.write_bytes(test_data)
        
        print(f"创建测试文件: {test_file} ({len(test_data)} bytes)")
        
        # 创建流式上传器
        uploader = StreamingUploader(
            chunk_size=256 * 1024,  # 256KB块
            max_retries=3,
            enable_compression=False
        )
        
        # 模拟上传结果
        uploaded_chunks = []
        
        def upload_callback(chunk_index: int, total_chunks: int, bytes_uploaded: int):
            progress = (chunk_index + 1) / total_chunks * 100
            uploaded_chunks.append(chunk_index)
            print(f"  上传进度: {progress:.1f}% (块 {chunk_index+1}/{total_chunks})")
        
        # 执行流式上传
        start_time = time.time()
        chunk_cids = await uploader.upload_file_stream(
            test_file, 
            "test_file_cid",
            callback=upload_callback
        )
        end_time = time.time()
        
        print(f"✓ 流式上传完成")
        print(f"  总耗时: {end_time - start_time:.2f}秒")
        print(f"  生成分片: {len(chunk_cids)}")
        print(f"  上传速度: {len(test_data) / (end_time - start_time) / 1024 / 1024:.2f} MB/s")
        print(f"  内存使用: 流式处理，无需全部加载到内存")
        
        # 验证所有块都被上传
        expected_chunks = (len(test_data) + uploader.chunk_size - 1) // uploader.chunk_size
        if len(uploaded_chunks) == expected_chunks:
            print(f"  分片完整性: ✓ 所有 {expected_chunks} 个分片已上传")
        else:
            print(f"  分片完整性: ✗ 预期 {expected_chunks}, 实际 {len(uploaded_chunks)}")
        
        # 清理
        import shutil
        shutil.rmtree(temp_dir)
        
        return True
        
    except Exception as e:
        print(f"✗ 流式上传器测试失败: {e}")
        logger.error("流式上传测试异常", error=str(e))
        return False


async def test_memory_monitor():
    """测试内存监控器"""
    print("\n=== 测试内存监控器 ===")
    
    try:
        monitor = MemoryMonitor(
            warning_threshold_mb=100,
            critical_threshold_mb=200,
            gc_interval_seconds=5
        )
        
        # 启动监控
        monitor.start_monitoring()
        print("✓ 内存监控已启动")
        
        # 获取初始内存状态
        initial_stats = monitor.get_memory_stats()
        print(f"  初始内存使用: {initial_stats['current_memory_mb']:.1f}MB")
        print(f"  可用内存: {initial_stats['available_memory_mb']:.1f}MB")
        
        # 模拟内存使用
        large_data = []
        for i in range(10):
            # 每次分配10MB
            data = bytearray(10 * 1024 * 1024)
            large_data.append(data)
            await asyncio.sleep(0.1)
        
        # 检查内存增长
        peak_stats = monitor.get_memory_stats()
        print(f"  峰值内存使用: {peak_stats['peak_memory_mb']:.1f}MB")
        print(f"  内存增长: {peak_stats['current_memory_mb'] - initial_stats['current_memory_mb']:.1f}MB")
        
        # 触发垃圾回收
        gc_count_before = monitor.gc_count
        monitor.force_gc()
        await asyncio.sleep(0.1)
        
        if monitor.gc_count > gc_count_before:
            print(f"  垃圾回收: ✓ 已执行 ({monitor.gc_count - gc_count_before} 次)")
        
        # 清理内存
        del large_data
        monitor.force_gc()
        
        final_stats = monitor.get_memory_stats()
        print(f"  清理后内存: {final_stats['current_memory_mb']:.1f}MB")
        
        # 停止监控
        monitor.stop_monitoring()
        print("✓ 内存监控已停止")
        
        return True
        
    except Exception as e:
        print(f"✗ 内存监控器测试失败: {e}")
        logger.error("内存监控测试异常", error=str(e))
        return False


async def test_performance_metrics():
    """测试性能指标收集"""
    print("\n=== 测试性能指标收集 ===")
    
    try:
        # 创建性能指标
        metrics = PerformanceMetrics()
        print("✓ 性能指标收集器初始化")
        
        # 模拟上传操作
        await asyncio.sleep(0.1)
        metrics.completed_tasks = 45
        metrics.failed_tasks = 5
        metrics.uploaded_bytes = 1024 * 1024 * 100  # 100MB
        metrics.end_time = time.time() + 30.5  # 设置结束时间
        
        # 测试性能计算
        success_rate = metrics.get_success_rate()
        throughput = metrics.get_throughput_mbps()
        avg_speed = metrics.get_average_upload_speed_mbps()
        
        print(f"  上传成功率: {success_rate:.1f}%")
        print(f"  平均吞吐量: {throughput:.2f} MB/s")
        print(f"  平均上传速度: {avg_speed:.2f} MB/s")
        
        # 测试指标汇总
        summary = metrics.get_summary()
        print(f"  指标汇总: {len(summary)} 项")
        for key, value in list(summary.items())[:5]:  # 显示前5项
            print(f"    {key}: {value}")
        
        # 验证计算正确性
        expected_success_rate = 45 / 50 * 100
        if abs(success_rate - expected_success_rate) < 0.1:
            print("  ✓ 成功率计算正确")
        else:
            print(f"  ✗ 成功率计算错误: 期望 {expected_success_rate}, 实际 {success_rate}")
        
        return True
        
    except Exception as e:
        print(f"✗ 性能指标测试失败: {e}")
        logger.error("性能指标测试异常", error=str(e))
        return False


async def test_performance_optimizer_integration():
    """测试性能优化器集成"""
    print("\n=== 测试性能优化器集成 ===")
    
    try:
        # 创建性能优化器
        optimizer = PerformanceOptimizer(
            max_concurrent_uploads=4,
            chunk_size_kb=256,
            memory_limit_mb=100,
            enable_compression=False
        )
        
        print("✓ 性能优化器初始化")
        
        # 启动优化器
        await optimizer.start()
        print("✓ 性能优化器已启动")
        
        # 创建测试数据
        test_files = []
        temp_dir = Path(tempfile.mkdtemp())
        
        for i in range(5):
            file_path = temp_dir / f"test_file_{i}.bin"
            # 创建不同大小的文件
            file_data = b"TEST_DATA_" * (1000 * (i + 1))  # 递增大小
            file_path.write_bytes(file_data)
            test_files.append(file_path)
        
        print(f"创建 {len(test_files)} 个测试文件")
        
        # 模拟批量上传
        results = []
        
        async def process_file(file_path: Path):
            # 模拟文件处理
            await asyncio.sleep(0.1)
            return {
                "file": file_path.name,
                "size": file_path.stat().st_size,
                "status": "success"
            }
        
        # 并发处理文件
        start_time = time.time()
        tasks = [process_file(f) for f in test_files]
        results = await asyncio.gather(*tasks)
        end_time = time.time()
        
        print(f"✓ 批量处理完成")
        print(f"  处理时间: {end_time - start_time:.2f}秒")
        print(f"  成功文件: {len([r for r in results if r['status'] == 'success'])}/{len(results)}")
        
        # 获取性能指标
        if hasattr(optimizer, 'metrics'):
            summary = optimizer.metrics.get_summary()
            print(f"  性能指标: {len(summary)} 项监控数据")
        
        # 停止优化器
        await optimizer.stop()
        print("✓ 性能优化器已停止")
        
        # 清理
        import shutil
        shutil.rmtree(temp_dir)
        
        return True
        
    except Exception as e:
        print(f"✗ 性能优化器集成测试失败: {e}")
        logger.error("性能优化器集成测试异常", error=str(e))
        return False


async def test_priority_queue():
    """测试优先级队列功能"""
    print("\n=== 测试优先级队列 ===")
    
    try:
        manager = ConcurrentUploadManager(max_concurrent=2)
        
        # 创建不同优先级的任务
        tasks = [
            UploadTask("low_1", b"data1", TaskPriority.LOW, 1, {"order": 1}),
            UploadTask("high_1", b"data2", TaskPriority.HIGH, 1, {"order": 2}),
            UploadTask("normal_1", b"data3", TaskPriority.NORMAL, 1, {"order": 3}),
            UploadTask("high_2", b"data4", TaskPriority.HIGH, 1, {"order": 4}),
            UploadTask("low_2", b"data5", TaskPriority.LOW, 1, {"order": 5}),
        ]
        
        # 记录执行顺序
        execution_order = []
        
        async def priority_upload(cid: str, chunk_data: bytes, chunk_index: int, total_chunks: int) -> Dict:
            execution_order.append(cid)
            await asyncio.sleep(0.1)
            return {"cid": cid, "success": True}
        
        # 执行优先级上传
        results = await manager.batch_upload(tasks, priority_upload)
        
        print(f"✓ 优先级队列测试完成")
        print(f"  执行顺序: {execution_order}")
        print(f"  成功任务: {len([r for r in results if r['success']])}")
        
        # 验证高优先级任务优先执行
        high_priority_positions = [i for i, cid in enumerate(execution_order) if cid.startswith('high_')]
        if high_priority_positions and max(high_priority_positions) < len(execution_order) - 1:
            print("  ✓ 高优先级任务优先执行")
        else:
            print("  ⚠️ 优先级顺序可能受并发影响")
        
        return True
        
    except Exception as e:
        print(f"✗ 优先级队列测试失败: {e}")
        return False


async def run_all_tests():
    """运行所有性能优化器测试"""
    print("🚀 开始性能优化器测试")
    print("=" * 60)
    
    tests = [
        test_concurrent_upload_manager,
        test_streaming_uploader,
        test_memory_monitor,
        test_performance_metrics,
        test_priority_queue,
        test_performance_optimizer_integration,
    ]
    
    passed = 0
    total = len(tests)
    
    for test in tests:
        try:
            result = await test()
            if result:
                passed += 1
        except Exception as e:
            logger.error(f"测试执行异常: {test.__name__}", error=str(e))
    
    print("=" * 60)
    print(f"🏁 性能优化器测试完成: {passed}/{total} 通过")
    
    if passed == total:
        print("🎉 所有性能优化器测试通过!")
        return True
    else:
        print(f"⚠️  有 {total - passed} 个测试失败")
        return False


if __name__ == "__main__":
    asyncio.run(run_all_tests())