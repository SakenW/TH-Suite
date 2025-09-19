#!/usr/bin/env python3
"""
TH-Suite 翻译数据传输架构性能基准测试

评估指标：
1. 数据提取性能 (记录/秒)
2. 压缩性能 (MB/秒, 压缩率)
3. 传输吞吐量 (MB/秒, 并发数)
4. 内存使用效率
5. 端到端延迟
6. 错误恢复时间
"""

import asyncio
import time
import os
import json
import tempfile
import shutil
import psutil
import statistics
from pathlib import Path
from typing import List, Dict, Any, Tuple
from dataclasses import dataclass, asdict
import sqlite3

from infrastructure.services.translation_data_extractor import (
    TranslationDataExtractor,
    ExtractionType,
    ExtractionRequest
)
from infrastructure.services.localized_compression_service import (
    LocalizedCompressionService,
    CompressionLevel,
    LanguageFamily
)
from infrastructure.services.transfer_controller import (
    TransferController,
    TransferMode,
    TransferPriority
)


@dataclass
class PerformanceMetrics:
    """性能指标数据类"""
    operation: str
    duration_seconds: float
    throughput_mb_per_second: float
    memory_usage_mb: float
    cpu_usage_percent: float
    records_processed: int = 0
    compression_ratio: float = 0.0
    error_count: int = 0


@dataclass
class BenchmarkResults:
    """基准测试结果"""
    test_name: str
    total_duration: float
    metrics: List[PerformanceMetrics]
    summary: Dict[str, Any]


class TransmissionPerformanceBenchmark:
    """传输架构性能基准测试"""
    
    def __init__(self):
        self.temp_dir = None
        self.db_path = None
        self.process = psutil.Process()
        self.results: List[BenchmarkResults] = []
    
    async def setup_benchmark_environment(self):
        """设置基准测试环境"""
        print("🔧 设置基准测试环境...")
        
        # 创建临时目录
        self.temp_dir = tempfile.mkdtemp()
        self.db_path = os.path.join(self.temp_dir, "benchmark.db")
        
        # 初始化数据库
        await self._init_benchmark_database()
        
        # 生成测试数据
        await self._generate_test_data()
        
        # 初始化服务
        await self._init_benchmark_services()
        
        print(f"✅ 基准测试环境设置完成: {self.temp_dir}")
    
    async def _init_benchmark_database(self):
        """初始化基准测试数据库"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # 创建表结构
        cursor.execute("""
            CREATE TABLE scan_results (
                id INTEGER PRIMARY KEY,
                project_uid TEXT,
                mod_name TEXT,
                language TEXT,
                translation_key TEXT,
                translation_value TEXT,
                blake3_hash TEXT,
                file_path TEXT,
                scan_timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        cursor.execute("""
            CREATE TABLE transfer_sessions (
                session_id TEXT PRIMARY KEY,
                session_type TEXT,
                file_path TEXT,
                total_size INTEGER,
                chunk_size INTEGER,
                total_chunks INTEGER,
                status TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        cursor.execute("""
            CREATE TABLE transfer_chunks (
                chunk_id TEXT PRIMARY KEY,
                session_id TEXT,
                chunk_index INTEGER,
                chunk_size INTEGER,
                status TEXT,
                blake3_hash TEXT,
                retry_count INTEGER DEFAULT 0
            )
        """)
        
        # 创建索引优化查询性能
        cursor.execute("CREATE INDEX idx_scan_project_mod ON scan_results(project_uid, mod_name)")
        cursor.execute("CREATE INDEX idx_scan_language ON scan_results(language)")
        cursor.execute("CREATE INDEX idx_transfer_session ON transfer_chunks(session_id)")
        
        conn.commit()
        conn.close()
    
    async def _generate_test_data(self):
        """生成大规模测试数据"""
        print("📊 生成测试数据...")
        
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # 生成不同规模的测试数据集
        test_datasets = [
            ("small", 1000),      # 1K 记录
            ("medium", 10000),    # 10K 记录
            ("large", 100000),    # 100K 记录
            ("xlarge", 500000),   # 500K 记录
        ]
        
        for dataset_name, record_count in test_datasets:
            print(f"  生成 {dataset_name} 数据集: {record_count:,} 记录")
            
            batch_size = 1000
            for i in range(0, record_count, batch_size):
                batch_data = []
                for j in range(min(batch_size, record_count - i)):
                    record_id = i + j
                    batch_data.append((
                        f"project_{dataset_name}",
                        f"mod_{record_id % 50}",  # 50个不同模组
                        ["zh_cn", "en_us", "ja_jp", "ko_kr", "fr_fr"][record_id % 5],
                        f"key.{record_id}",
                        f"翻译内容_{record_id}" if record_id % 5 == 0 else f"Translation_{record_id}",
                        f"hash_{record_id}",
                        f"/path/to/lang_{record_id % 5}.json"
                    ))
                
                cursor.executemany("""
                    INSERT INTO scan_results 
                    (project_uid, mod_name, language, translation_key, translation_value, blake3_hash, file_path)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                """, batch_data)
                
                if i % 10000 == 0:
                    conn.commit()  # 定期提交避免内存占用过高
            
            conn.commit()
        
        conn.close()
        print("✅ 测试数据生成完成")
    
    async def _init_benchmark_services(self):
        """初始化基准测试服务"""
        class MockContainer:
            def __init__(self, db_path):
                self.db_path = db_path
            
            def get_sqlite_connection(self):
                return sqlite3.connect(self.db_path)
        
        self.container = MockContainer(self.db_path)
        self.extractor = TranslationDataExtractor(self.container)
        self.compressor = LocalizedCompressionService()
        # transfer_service 需要时再初始化
    
    def _get_system_metrics(self) -> Tuple[float, float]:
        """获取系统资源使用情况"""
        memory_mb = self.process.memory_info().rss / 1024 / 1024
        cpu_percent = self.process.cpu_percent()
        return memory_mb, cpu_percent
    
    async def benchmark_data_extraction(self) -> BenchmarkResults:
        """基准测试数据提取性能"""
        print("\n📊 开始数据提取性能基准测试...")
        
        test_cases = [
            ("small", "project_small", 1000),
            ("medium", "project_medium", 10000),
            ("large", "project_large", 100000),
            ("xlarge", "project_xlarge", 500000),
        ]
        
        metrics = []
        total_start = time.time()
        
        for case_name, project_uid, expected_records in test_cases:
            print(f"  测试 {case_name} 数据集 ({expected_records:,} 记录)...")
            
            # 测量提取性能
            start_time = time.time()
            memory_before, _ = self._get_system_metrics()
            
            extraction_request = ExtractionRequest(
                extraction_type=ExtractionType.FULL,
                project_uid=project_uid,
                target_languages=["zh_cn", "en_us", "ja_jp"],
                include_empty_translations=False,
                compression_enabled=False
            )
            
            result = await self.extractor.extract_translation_data(
                extraction_request.extraction_type,
                extraction_request.project_uid,
                extraction_request.target_languages,
                extraction_request.include_empty_translations
            )
            
            end_time = time.time()
            memory_after, cpu_percent = self._get_system_metrics()
            
            duration = end_time - start_time
            memory_used = memory_after - memory_before
            records_per_second = expected_records / duration if duration > 0 else 0
            
            metric = PerformanceMetrics(
                operation=f"extraction_{case_name}",
                duration_seconds=duration,
                throughput_mb_per_second=0,  # 这里是记录/秒
                memory_usage_mb=memory_used,
                cpu_usage_percent=cpu_percent,
                records_processed=expected_records,
                error_count=0 if result.success else 1
            )
            
            metrics.append(metric)
            print(f"    ⚡ {records_per_second:,.0f} 记录/秒, "
                  f"内存: {memory_used:.1f}MB, "
                  f"时间: {duration:.2f}s")
        
        total_duration = time.time() - total_start
        
        return BenchmarkResults(
            test_name="data_extraction",
            total_duration=total_duration,
            metrics=metrics,
            summary={
                "max_records_per_second": max(m.records_processed / m.duration_seconds for m in metrics),
                "avg_memory_usage_mb": statistics.mean(m.memory_usage_mb for m in metrics),
                "total_records_processed": sum(m.records_processed for m in metrics)
            }
        )
    
    async def benchmark_compression_performance(self) -> BenchmarkResults:
        """基准测试压缩性能"""
        print("\n🗜️  开始压缩性能基准测试...")
        
        # 创建不同大小的测试文件
        test_files = await self._create_compression_test_files()
        
        compression_levels = [
            CompressionLevel.FAST,
            CompressionLevel.BALANCED,
            CompressionLevel.HIGH,
            CompressionLevel.MAX
        ]
        
        language_families = [
            LanguageFamily.CJK,
            LanguageFamily.LATIN,
            LanguageFamily.CYRILLIC
        ]
        
        metrics = []
        total_start = time.time()
        
        for file_name, file_path, file_size_mb in test_files:
            for level in compression_levels:
                for lang_family in language_families:
                    test_name = f"{file_name}_{level.value}_{lang_family.value}"
                    print(f"  测试 {test_name}...")
                    
                    start_time = time.time()
                    memory_before, _ = self._get_system_metrics()
                    
                    try:
                        result = await self.compressor.compress_file(
                            file_path,
                            level,
                            lang_family
                        )
                        
                        end_time = time.time()
                        memory_after, cpu_percent = self._get_system_metrics()
                        
                        duration = end_time - start_time
                        throughput = file_size_mb / duration if duration > 0 else 0
                        memory_used = memory_after - memory_before
                        
                        metric = PerformanceMetrics(
                            operation=test_name,
                            duration_seconds=duration,
                            throughput_mb_per_second=throughput,
                            memory_usage_mb=memory_used,
                            cpu_usage_percent=cpu_percent,
                            compression_ratio=result.compression_ratio if result.success else 0,
                            error_count=0 if result.success else 1
                        )
                        
                        metrics.append(metric)
                        print(f"    ⚡ {throughput:.1f} MB/s, "
                              f"压缩率: {result.compression_ratio:.1%}, "
                              f"内存: {memory_used:.1f}MB")
                    
                    except Exception as e:
                        print(f"    ❌ 错误: {str(e)}")
                        metrics.append(PerformanceMetrics(
                            operation=test_name,
                            duration_seconds=0,
                            throughput_mb_per_second=0,
                            memory_usage_mb=0,
                            cpu_usage_percent=0,
                            error_count=1
                        ))
        
        total_duration = time.time() - total_start
        
        return BenchmarkResults(
            test_name="compression_performance",
            total_duration=total_duration,
            metrics=metrics,
            summary={
                "max_throughput_mb_per_second": max((m.throughput_mb_per_second for m in metrics if m.throughput_mb_per_second > 0), default=0),
                "avg_compression_ratio": statistics.mean((m.compression_ratio for m in metrics if m.compression_ratio > 0)),
                "avg_memory_usage_mb": statistics.mean(m.memory_usage_mb for m in metrics),
                "error_rate": sum(m.error_count for m in metrics) / len(metrics)
            }
        )
    
    async def _create_compression_test_files(self) -> List[Tuple[str, str, float]]:
        """创建压缩测试文件"""
        test_files = []
        
        # 不同大小和内容类型的测试文件
        file_configs = [
            ("small_json", 1024, "json"),      # 1MB JSON
            ("medium_json", 5120, "json"),     # 5MB JSON
            ("large_json", 20480, "json"),     # 20MB JSON
            ("small_text", 1024, "text"),      # 1MB 纯文本
            ("medium_text", 5120, "text"),     # 5MB 纯文本
        ]
        
        for name, size_kb, file_type in file_configs:
            file_path = os.path.join(self.temp_dir, f"{name}.{file_type}")
            
            if file_type == "json":
                # 创建 JSON 格式的翻译数据
                content = {
                    "translations": {
                        f"key_{i}": f"这是一个测试翻译内容_{i}，包含中文字符用于测试压缩效果。" * 10
                        for i in range(size_kb // 4)  # 估算大小
                    }
                }
                with open(file_path, 'w', encoding='utf-8') as f:
                    json.dump(content, f, ensure_ascii=False, indent=2)
            
            else:  # text
                # 创建纯文本文件
                line = "这是一个测试行，包含中文和英文 This is a test line with Chinese and English content.\n"
                lines_needed = size_kb * 1024 // len(line.encode('utf-8'))
                
                with open(file_path, 'w', encoding='utf-8') as f:
                    for _ in range(lines_needed):
                        f.write(line)
            
            file_size_mb = os.path.getsize(file_path) / 1024 / 1024
            test_files.append((name, file_path, file_size_mb))
        
        return test_files
    
    async def benchmark_concurrent_operations(self) -> BenchmarkResults:
        """基准测试并发操作性能"""
        print("\n🔄 开始并发操作性能基准测试...")
        
        # 测试不同并发级别
        concurrency_levels = [1, 2, 4, 8, 16]
        metrics = []
        total_start = time.time()
        
        for concurrency in concurrency_levels:
            print(f"  测试并发级别: {concurrency}")
            
            start_time = time.time()
            memory_before, _ = self._get_system_metrics()
            
            # 创建并发任务
            tasks = []
            for i in range(concurrency):
                task = self._concurrent_extraction_task(f"project_medium", i)
                tasks.append(task)
            
            # 执行并发任务
            results = await asyncio.gather(*tasks, return_exceptions=True)
            
            end_time = time.time()
            memory_after, cpu_percent = self._get_system_metrics()
            
            duration = end_time - start_time
            memory_used = memory_after - memory_before
            successful_tasks = len([r for r in results if not isinstance(r, Exception)])
            
            metric = PerformanceMetrics(
                operation=f"concurrent_{concurrency}",
                duration_seconds=duration,
                throughput_mb_per_second=successful_tasks / duration if duration > 0 else 0,
                memory_usage_mb=memory_used,
                cpu_usage_percent=cpu_percent,
                records_processed=successful_tasks,
                error_count=concurrency - successful_tasks
            )
            
            metrics.append(metric)
            print(f"    ⚡ {successful_tasks}/{concurrency} 任务成功, "
                  f"内存: {memory_used:.1f}MB, "
                  f"时间: {duration:.2f}s")
        
        total_duration = time.time() - total_start
        
        return BenchmarkResults(
            test_name="concurrent_operations",
            total_duration=total_duration,
            metrics=metrics,
            summary={
                "optimal_concurrency": max(enumerate(metrics), key=lambda x: x[1].throughput_mb_per_second)[0] + 1,
                "max_throughput": max(m.throughput_mb_per_second for m in metrics),
                "peak_memory_usage_mb": max(m.memory_usage_mb for m in metrics)
            }
        )
    
    async def _concurrent_extraction_task(self, project_uid: str, task_id: int):
        """并发提取任务"""
        try:
            extraction_request = ExtractionRequest(
                extraction_type=ExtractionType.INCREMENTAL,
                project_uid=project_uid,
                target_languages=["zh_cn", "en_us"],
                include_empty_translations=False,
                compression_enabled=False
            )
            
            result = await self.extractor.extract_translation_data(
                extraction_request.extraction_type,
                extraction_request.project_uid,
                extraction_request.target_languages,
                extraction_request.include_empty_translations
            )
            
            return result.success
        
        except Exception as e:
            return False
    
    def generate_performance_report(self) -> str:
        """生成性能报告"""
        report = []
        report.append("📊 TH-Suite 翻译数据传输架构性能基准测试报告")
        report.append("=" * 80)
        report.append(f"测试时间: {time.strftime('%Y-%m-%d %H:%M:%S')}")
        report.append(f"系统信息: {psutil.cpu_count()} 核 CPU, {psutil.virtual_memory().total / 1024**3:.1f}GB 内存")
        report.append("")
        
        for result in self.results:
            report.append(f"\n🔬 {result.test_name.upper()} 测试结果")
            report.append("-" * 50)
            report.append(f"总耗时: {result.total_duration:.2f} 秒")
            
            # 汇总统计
            if result.summary:
                report.append("\n📈 关键指标:")
                for key, value in result.summary.items():
                    if isinstance(value, float):
                        report.append(f"  {key}: {value:.2f}")
                    else:
                        report.append(f"  {key}: {value}")
            
            # 详细指标
            report.append("\n📋 详细指标:")
            for metric in result.metrics:
                report.append(f"  {metric.operation}:")
                report.append(f"    时间: {metric.duration_seconds:.3f}s")
                if metric.throughput_mb_per_second > 0:
                    report.append(f"    吞吐量: {metric.throughput_mb_per_second:.2f} MB/s")
                if metric.records_processed > 0:
                    records_per_sec = metric.records_processed / metric.duration_seconds if metric.duration_seconds > 0 else 0
                    report.append(f"    处理速度: {records_per_sec:,.0f} 记录/s")
                if metric.compression_ratio > 0:
                    report.append(f"    压缩率: {metric.compression_ratio:.1%}")
                report.append(f"    内存使用: {metric.memory_usage_mb:.1f}MB")
                if metric.error_count > 0:
                    report.append(f"    错误数: {metric.error_count}")
        
        # 整体性能总结
        report.append("\n🎯 性能总结")
        report.append("-" * 50)
        
        if self.results:
            all_metrics = []
            for result in self.results:
                all_metrics.extend(result.metrics)
            
            max_throughput = max((m.throughput_mb_per_second for m in all_metrics if m.throughput_mb_per_second > 0), default=0)
            max_records_per_sec = max((m.records_processed / m.duration_seconds for m in all_metrics if m.duration_seconds > 0 and m.records_processed > 0), default=0)
            avg_memory = statistics.mean(m.memory_usage_mb for m in all_metrics)
            error_rate = sum(m.error_count for m in all_metrics) / len(all_metrics) if all_metrics else 0
            
            report.append(f"最大数据吞吐量: {max_throughput:.2f} MB/s")
            report.append(f"最大记录处理速度: {max_records_per_sec:,.0f} 记录/s")
            report.append(f"平均内存使用: {avg_memory:.1f} MB")
            report.append(f"总体错误率: {error_rate:.1%}")
        
        return "\n".join(report)
    
    async def run_all_benchmarks(self):
        """运行所有基准测试"""
        try:
            await self.setup_benchmark_environment()
            
            # 运行各项基准测试
            print("🚀 开始运行 TH-Suite 传输架构性能基准测试")
            print("=" * 80)
            
            extraction_result = await self.benchmark_data_extraction()
            self.results.append(extraction_result)
            
            compression_result = await self.benchmark_compression_performance()
            self.results.append(compression_result)
            
            concurrent_result = await self.benchmark_concurrent_operations()
            self.results.append(concurrent_result)
            
            # 生成报告
            report = self.generate_performance_report()
            print("\n" + report)
            
            # 保存报告到文件
            report_file = os.path.join(self.temp_dir, "performance_report.txt")
            with open(report_file, 'w', encoding='utf-8') as f:
                f.write(report)
            
            print(f"\n📄 性能报告已保存到: {report_file}")
            
        except Exception as e:
            print(f"❌ 基准测试失败: {str(e)}")
            import traceback
            traceback.print_exc()
        
        finally:
            # 清理环境
            if self.temp_dir and os.path.exists(self.temp_dir):
                try:
                    shutil.rmtree(self.temp_dir)
                    print("🧹 测试环境清理完成")
                except:
                    print(f"⚠️  无法清理测试目录: {self.temp_dir}")


async def main():
    """主函数"""
    benchmark = TransmissionPerformanceBenchmark()
    await benchmark.run_all_benchmarks()


if __name__ == "__main__":
    """
    运行方式:
    cd TH-Suite/apps/mc_l10n/backend/
    python benchmark_transmission_performance.py
    """
    asyncio.run(main())