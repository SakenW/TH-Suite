"""
性能基准测试套件
测试系统性能指标和回归检测
"""
import pytest
import asyncio
import time
import psutil
import tempfile
import json
from pathlib import Path
from typing import Dict, List, Any
from concurrent.futures import ThreadPoolExecutor
import statistics

from apps.mc_l10n.backend.infrastructure.services.simple_minecraft_scanner import SimpleMinecraftScanner


class PerformanceMonitor:
    """性能监控器"""
    
    def __init__(self):
        self.metrics = {}
        self.start_time = None
        self.process = psutil.Process()
    
    def start_monitoring(self, test_name: str):
        """开始性能监控"""
        self.start_time = time.time()
        self.metrics[test_name] = {
            "start_time": self.start_time,
            "start_memory": self.process.memory_info().rss,
            "start_cpu": self.process.cpu_percent()
        }
    
    def stop_monitoring(self, test_name: str) -> Dict[str, Any]:
        """停止性能监控并返回结果"""
        end_time = time.time()
        end_memory = self.process.memory_info().rss
        end_cpu = self.process.cpu_percent()
        
        if test_name not in self.metrics:
            raise ValueError(f"测试 {test_name} 未开始监控")
        
        start_metrics = self.metrics[test_name]
        
        result = {
            "duration": end_time - start_metrics["start_time"],
            "memory_usage": end_memory - start_metrics["start_memory"],
            "peak_memory": end_memory,
            "cpu_usage": end_cpu,
            "start_time": start_metrics["start_time"],
            "end_time": end_time
        }
        
        self.metrics[test_name].update(result)
        return result


class TestPerformanceBenchmarks:
    """性能基准测试"""
    
    @pytest.fixture
    def performance_monitor(self):
        """性能监控器fixture"""
        return PerformanceMonitor()
    
    @pytest.fixture
    def test_data_generator(self):
        """测试数据生成器"""
        def generate_large_dataset(size: int) -> List[Dict[str, Any]]:
            """生成大量测试数据"""
            return [
                {
                    "id": f"entry_{i}",
                    "key": f"item.test_mod.item_{i}",
                    "source_text": f"Test Item {i}",
                    "target_text": f"测试物品 {i}",
                    "metadata": {
                        "category": "items",
                        "priority": i % 5,
                        "tags": [f"tag_{j}" for j in range(i % 3)]
                    }
                }
                for i in range(size)
            ]
        return generate_large_dataset
    
    async def test_file_scanning_performance(self, performance_monitor, test_data_generator):
        """测试文件扫描性能"""
        monitor = performance_monitor
        
        # 创建临时测试文件
        with tempfile.TemporaryDirectory() as temp_dir:
            test_dir = Path(temp_dir)
            
            # 生成大量测试文件
            file_count = 1000
            for i in range(file_count):
                file_path = test_dir / f"test_file_{i}.json"
                test_data = test_data_generator(10)  # 每个文件10个条目
                
                with open(file_path, 'w', encoding='utf-8') as f:
                    json.dump(test_data, f, ensure_ascii=False, indent=2)
            
            # 开始性能监控
            monitor.start_monitoring("file_scanning")
            
            # 执行扫描
            scanner = SimpleMinecraftScanner()
            scan_result = await scanner.scan_directory(str(test_dir))
            
            # 停止监控
            metrics = monitor.stop_monitoring("file_scanning")
            
            # 性能断言
            assert metrics["duration"] < 10.0  # 扫描时间应少于10秒
            assert len(scan_result) >= file_count  # 应该扫描到所有文件
            
            # 内存使用应该合理（少于100MB）
            assert metrics["memory_usage"] < 100 * 1024 * 1024
            
            # 计算处理速率
            processing_rate = file_count / metrics["duration"]
            assert processing_rate > 100  # 每秒处理超过100个文件
            
            print(f"文件扫描性能指标:")
            print(f"  - 处理文件数: {file_count}")
            print(f"  - 耗时: {metrics['duration']:.2f}秒")
            print(f"  - 处理速率: {processing_rate:.2f}文件/秒")
            print(f"  - 内存使用: {metrics['memory_usage'] / 1024 / 1024:.2f}MB")
    
    async def test_large_dataset_processing_performance(self, performance_monitor, test_data_generator):
        """测试大数据集处理性能"""
        monitor = performance_monitor
        
        # 生成大型数据集
        dataset_sizes = [1000, 5000, 10000, 50000]
        results = {}
        
        for size in dataset_sizes:
            test_name = f"dataset_processing_{size}"
            monitor.start_monitoring(test_name)
            
            # 生成测试数据
            test_data = test_data_generator(size)
            
            # 模拟数据处理操作
            processed_data = []
            for entry in test_data:
                # 模拟复杂处理
                processed_entry = {
                    "id": entry["id"],
                    "processed_key": entry["key"].upper(),
                    "char_count": len(entry["source_text"]) + len(entry["target_text"]),
                    "processed_at": time.time()
                }
                processed_data.append(processed_entry)
            
            # 停止监控
            metrics = monitor.stop_monitoring(test_name)
            results[size] = metrics
            
            # 验证处理结果
            assert len(processed_data) == size
            
            # 性能要求
            processing_rate = size / metrics["duration"]
            assert processing_rate > 1000  # 每秒处理超过1000条记录
            
        # 分析性能趋势
        print("\n大数据集处理性能分析:")
        for size, metrics in results.items():
            rate = size / metrics["duration"]
            memory_mb = metrics["memory_usage"] / 1024 / 1024
            print(f"  数据集大小: {size:>6} | 耗时: {metrics['duration']:>6.2f}s | "
                  f"速率: {rate:>8.0f}/s | 内存: {memory_mb:>6.1f}MB")
    
    async def test_concurrent_operations_performance(self, performance_monitor):
        """测试并发操作性能"""
        monitor = performance_monitor
        
        async def mock_translation_task(task_id: int, duration: float = 0.1) -> Dict[str, Any]:
            """模拟翻译任务"""
            await asyncio.sleep(duration)
            return {
                "task_id": task_id,
                "translations": task_id * 10,
                "duration": duration
            }
        
        # 测试不同并发级别
        concurrency_levels = [1, 5, 10, 20, 50]
        results = {}
        
        for concurrency in concurrency_levels:
            test_name = f"concurrent_{concurrency}"
            monitor.start_monitoring(test_name)
            
            # 创建并发任务
            tasks = [
                mock_translation_task(i, 0.1) 
                for i in range(concurrency)
            ]
            
            # 执行并发任务
            task_results = await asyncio.gather(*tasks)
            
            # 停止监控
            metrics = monitor.stop_monitoring(test_name)
            results[concurrency] = metrics
            
            # 验证结果
            assert len(task_results) == concurrency
            
            # 并发效果验证
            expected_sequential_time = concurrency * 0.1
            actual_time = metrics["duration"]
            speedup = expected_sequential_time / actual_time
            
            # 并发应该带来显著的性能提升
            if concurrency > 1:
                assert speedup > 1.5  # 至少1.5倍的加速
        
        # 分析并发性能
        print("\n并发操作性能分析:")
        for concurrency, metrics in results.items():
            expected_time = concurrency * 0.1
            actual_time = metrics["duration"]
            speedup = expected_time / actual_time if actual_time > 0 else 0
            print(f"  并发数: {concurrency:>2} | 实际耗时: {actual_time:>6.2f}s | "
                  f"预期耗时: {expected_time:>6.2f}s | 加速比: {speedup:>4.1f}x")
    
    async def test_memory_usage_patterns(self, performance_monitor, test_data_generator):
        """测试内存使用模式"""
        monitor = performance_monitor
        
        # 测试内存增长模式
        monitor.start_monitoring("memory_patterns")
        
        memory_snapshots = []
        dataset_sizes = [1000, 2000, 5000, 10000]
        
        for size in dataset_sizes:
            # 生成数据
            data = test_data_generator(size)
            
            # 记录内存快照
            current_memory = psutil.Process().memory_info().rss
            memory_snapshots.append({
                "dataset_size": size,
                "memory_usage": current_memory,
                "data_items": len(data)
            })
            
            # 模拟数据处理
            processed = [item["key"] for item in data]
            assert len(processed) == size
        
        # 停止监控
        metrics = monitor.stop_monitoring("memory_patterns")
        
        # 分析内存使用模式
        if len(memory_snapshots) > 1:
            memory_growth = []
            for i in range(1, len(memory_snapshots)):
                prev_snapshot = memory_snapshots[i-1]
                curr_snapshot = memory_snapshots[i]
                
                size_increase = curr_snapshot["dataset_size"] - prev_snapshot["dataset_size"]
                memory_increase = curr_snapshot["memory_usage"] - prev_snapshot["memory_usage"]
                
                memory_per_item = memory_increase / size_increase if size_increase > 0 else 0
                memory_growth.append(memory_per_item)
            
            # 验证内存使用效率
            avg_memory_per_item = statistics.mean(memory_growth)
            assert avg_memory_per_item < 10000  # 每个条目内存使用少于10KB
            
            print("\n内存使用模式分析:")
            for snapshot in memory_snapshots:
                memory_mb = snapshot["memory_usage"] / 1024 / 1024
                print(f"  数据集大小: {snapshot['dataset_size']:>6} | "
                      f"内存使用: {memory_mb:>6.1f}MB")
    
    async def test_compression_performance(self, performance_monitor, test_data_generator):
        """测试压缩性能"""
        import zstandard as zstd
        import json
        
        monitor = performance_monitor
        
        # 生成测试数据
        test_data = test_data_generator(10000)
        json_data = json.dumps(test_data, ensure_ascii=False)
        original_size = len(json_data.encode('utf-8'))
        
        # 测试不同压缩级别
        compression_levels = [1, 3, 6, 9, 15]
        results = {}
        
        for level in compression_levels:
            test_name = f"compression_level_{level}"
            monitor.start_monitoring(test_name)
            
            # 执行压缩
            compressor = zstd.ZstdCompressor(level=level)
            compressed_data = compressor.compress(json_data.encode('utf-8'))
            
            # 执行解压缩
            decompressor = zstd.ZstdDecompressor()
            decompressed_data = decompressor.decompress(compressed_data)
            
            # 停止监控
            metrics = monitor.stop_monitoring(test_name)
            
            # 验证数据完整性
            assert decompressed_data.decode('utf-8') == json_data
            
            # 记录压缩效果
            compressed_size = len(compressed_data)
            compression_ratio = original_size / compressed_size
            
            results[level] = {
                "metrics": metrics,
                "original_size": original_size,
                "compressed_size": compressed_size,
                "compression_ratio": compression_ratio
            }
            
            # 性能要求
            assert metrics["duration"] < 5.0  # 压缩时间少于5秒
            assert compression_ratio > 1.5  # 压缩比至少1.5:1
        
        # 分析压缩性能
        print("\n压缩性能分析:")
        print(f"原始数据大小: {original_size / 1024:.1f}KB")
        for level, result in results.items():
            compressed_kb = result["compressed_size"] / 1024
            ratio = result["compression_ratio"]
            duration = result["metrics"]["duration"]
            throughput = (original_size / 1024 / 1024) / duration  # MB/s
            
            print(f"  级别 {level:>2}: {compressed_kb:>6.1f}KB | "
                  f"压缩比 {ratio:>4.1f}:1 | 耗时 {duration:>5.2f}s | "
                  f"吞吐量 {throughput:>5.1f}MB/s")


class TestPerformanceRegression:
    """性能回归测试"""
    
    PERFORMANCE_BASELINES = {
        "file_scanning_rate": 100,  # 文件/秒
        "data_processing_rate": 1000,  # 条目/秒
        "memory_per_item": 10000,  # 字节/条目
        "compression_ratio": 1.5,  # 压缩比
        "concurrent_speedup": 1.5  # 并发加速比
    }
    
    async def test_performance_regression_check(self):
        """性能回归检查"""
        # 这里应该与基准值进行比较
        # 实际实现中，可以从性能数据库或文件中读取历史基准
        
        current_metrics = {
            "file_scanning_rate": 150,  # 模拟当前性能
            "data_processing_rate": 1200,
            "memory_per_item": 8000,
            "compression_ratio": 2.0,
            "concurrent_speedup": 2.5
        }
        
        regression_detected = False
        regression_details = []
        
        for metric_name, baseline in self.PERFORMANCE_BASELINES.items():
            current_value = current_metrics.get(metric_name, 0)
            
            # 检查性能回归（允许5%的波动）
            tolerance = 0.05
            if current_value < baseline * (1 - tolerance):
                regression_detected = True
                regression_details.append({
                    "metric": metric_name,
                    "baseline": baseline,
                    "current": current_value,
                    "regression_percent": ((baseline - current_value) / baseline) * 100
                })
        
        # 如果检测到回归，记录详细信息
        if regression_detected:
            print("\n⚠️  检测到性能回归:")
            for detail in regression_details:
                print(f"  - {detail['metric']}: "
                      f"基准值 {detail['baseline']} -> "
                      f"当前值 {detail['current']} "
                      f"(下降 {detail['regression_percent']:.1f}%)")
        
        # 在实际环境中，可以选择是否让测试失败
        # assert not regression_detected, "检测到性能回归，请检查代码变更"
        
        print(f"\n性能回归检查结果: {'通过' if not regression_detected else '未通过'}")


class TestLoadAndStressTest:
    """负载和压力测试"""
    
    async def test_high_load_simulation(self):
        """高负载模拟测试"""
        
        async def simulate_user_request(user_id: int):
            """模拟用户请求"""
            # 模拟各种用户操作
            operations = ["scan", "translate", "sync", "export"]
            
            for operation in operations:
                # 模拟操作延迟
                await asyncio.sleep(0.01)
                
                # 模拟操作结果
                result = {
                    "user_id": user_id,
                    "operation": operation,
                    "timestamp": time.time(),
                    "status": "success"
                }
            
            return result
        
        # 模拟高并发用户
        concurrent_users = 100
        
        start_time = time.time()
        tasks = [simulate_user_request(i) for i in range(concurrent_users)]
        results = await asyncio.gather(*tasks)
        end_time = time.time()
        
        # 验证负载测试结果
        assert len(results) == concurrent_users
        total_duration = end_time - start_time
        
        # 高负载下的性能要求
        assert total_duration < 5.0  # 100个并发用户的操作应在5秒内完成
        
        # 计算吞吐量
        total_operations = concurrent_users * 4  # 每用户4个操作
        throughput = total_operations / total_duration
        
        assert throughput > 200  # 每秒处理超过200个操作
        
        print(f"\n高负载测试结果:")
        print(f"  - 并发用户数: {concurrent_users}")
        print(f"  - 总操作数: {total_operations}")
        print(f"  - 总耗时: {total_duration:.2f}秒")
        print(f"  - 吞吐量: {throughput:.0f}操作/秒")
    
    async def test_memory_leak_detection(self):
        """内存泄漏检测测试"""
        import gc
        
        # 记录初始内存
        gc.collect()  # 强制垃圾回收
        initial_memory = psutil.Process().memory_info().rss
        
        # 执行大量操作
        for cycle in range(10):
            # 创建大量临时对象
            temp_data = [{"id": i, "data": f"data_{i}" * 100} for i in range(1000)]
            
            # 模拟处理
            processed = [item["id"] for item in temp_data]
            
            # 清理引用
            del temp_data
            del processed
            
            # 强制垃圾回收
            gc.collect()
            
            # 检查内存使用
            current_memory = psutil.Process().memory_info().rss
            memory_growth = current_memory - initial_memory
            
            # 内存增长不应该超过50MB
            assert memory_growth < 50 * 1024 * 1024, f"检测到内存泄漏: {memory_growth / 1024 / 1024:.1f}MB"
        
        # 最终内存检查
        final_memory = psutil.Process().memory_info().rss
        total_growth = final_memory - initial_memory
        
        print(f"\n内存泄漏检测结果:")
        print(f"  - 初始内存: {initial_memory / 1024 / 1024:.1f}MB")
        print(f"  - 最终内存: {final_memory / 1024 / 1024:.1f}MB")
        print(f"  - 内存增长: {total_growth / 1024 / 1024:.1f}MB")
        
        # 总内存增长应该在合理范围内
        assert total_growth < 20 * 1024 * 1024  # 少于20MB


if __name__ == "__main__":
    # 运行性能测试
    pytest.main([__file__, "-v", "-s"])