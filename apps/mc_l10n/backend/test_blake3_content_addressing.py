#!/usr/bin/env python
"""
测试BLAKE3内容寻址系统
验证内容寻址、缓存和性能优化功能
"""

import sys
import os
import time
import json
import asyncio
import tempfile
from pathlib import Path

sys.path.append('.')

import structlog

# 配置日志
structlog.configure(
    processors=[
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.dev.ConsoleRenderer()
    ]
)

logger = structlog.get_logger(__name__)

async def test_content_addressing():
    """测试基础内容寻址功能"""
    print("=== 测试BLAKE3内容寻址 ===")
    
    try:
        from services.content_addressing import (
            ContentAddressingSystem,
            HashAlgorithm,
            compute_cid,
            benchmark_hash_algorithms
        )
        
        # 创建内容寻址系统
        cas = ContentAddressingSystem(
            algorithm=HashAlgorithm.BLAKE3,
            enable_caching=True,
            max_cache_entries=1000
        )
        
        print("✓ 内容寻址系统初始化成功")
        
        # 测试不同类型内容的CID计算
        test_cases = [
            ("hello world", "字符串"),
            (b"hello world", "字节数据"),
            ({"key": "value", "number": 42}, "JSON对象"),
            ([1, 2, 3, "test"], "JSON数组"),
        ]
        
        for content, desc in test_cases:
            cid = cas.compute_cid(content)
            print(f"✓ {desc} CID: {cid.algorithm.value}:{cid.hash_value[:16]}... (size: {cid.size})")
        
        # 测试相同内容生成相同CID
        content1 = {"name": "测试", "value": 123}
        content2 = {"value": 123, "name": "测试"}  # 不同顺序，但内容相同
        
        cid1 = cas.compute_cid(content1)
        cid2 = cas.compute_cid(content2)
        
        if cas.compare_content(cid1, cid2):
            print("✓ 相同内容生成相同CID（顺序无关）")
        else:
            print("✗ 相同内容应生成相同CID")
            return False
        
        # 测试内容存储和检索
        test_data = {"translations": ["Hello", "World"], "count": 2}
        cid = cas.store_content(test_data, {"source": "test"})
        
        retrieved_data = cas.retrieve_content(cid)
        if retrieved_data == test_data:
            print("✓ 内容存储和检索成功")
        else:
            print("✗ 内容存储和检索失败")
            return False
        
        # 测试内容验证
        if cas.verify_content(test_data, cid):
            print("✓ 内容验证成功")
        else:
            print("✗ 内容验证失败")
            return False
        
        # 测试批量CID计算
        batch_contents = [
            "batch item 1",
            "batch item 2", 
            {"batch": "item", "id": 3}
        ]
        batch_cids = cas.batch_compute_cids(batch_contents)
        print(f"✓ 批量CID计算: {len(batch_cids)} 个CID")
        
        # 测试性能统计
        stats = cas.get_performance_stats()
        print(f"✓ 性能统计: {stats['hash_operations']} 次哈希操作, 缓存命中率 {stats['cache_hit_rate']:.1%}")
        
        return True
        
    except Exception as e:
        print(f"✗ BLAKE3内容寻址测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False

async def test_file_content_addressing():
    """测试文件内容寻址"""
    print("\n=== 测试文件内容寻址 ===")
    
    try:
        from services.content_addressing import ContentAddressingSystem, HashAlgorithm
        
        cas = ContentAddressingSystem(HashAlgorithm.BLAKE3)
        
        # 创建测试文件
        with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.json') as f:
            test_data = {
                "minecraft": {
                    "items": {
                        "diamond_sword": "钻石剑",
                        "iron_pickaxe": "铁镐"
                    },
                    "blocks": {
                        "stone": "石头",
                        "dirt": "泥土"
                    }
                }
            }
            json.dump(test_data, f, ensure_ascii=False, indent=2)
            temp_file = Path(f.name)
        
        try:
            # 计算文件CID
            file_cid = await cas.compute_file_cid(temp_file)
            print(f"✓ 文件CID计算: {file_cid.algorithm.value}:{file_cid.hash_value[:16]}... (size: {file_cid.size})")
            
            # 验证文件内容
            with open(temp_file, 'r', encoding='utf-8') as f:
                file_content = f.read()
            
            if cas.verify_content(file_content, file_cid):
                print("✓ 文件内容验证成功")
            else:
                print("✗ 文件内容验证失败")
                return False
            
            # 测试相同内容的文件生成相同CID
            with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.json') as f2:
                json.dump(test_data, f2, ensure_ascii=False, indent=2)
                temp_file2 = Path(f2.name)
            
            try:
                file_cid2 = await cas.compute_file_cid(temp_file2)
                
                if cas.compare_content(file_cid, file_cid2):
                    print("✓ 相同内容文件生成相同CID")
                else:
                    print("✗ 相同内容文件应生成相同CID")
                    return False
                
            finally:
                temp_file2.unlink()
            
            return True
            
        finally:
            temp_file.unlink()
        
    except Exception as e:
        print(f"✗ 文件内容寻址测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False

async def test_blake3_disk_cache():
    """测试BLAKE3磁盘缓存"""
    print("\n=== 测试BLAKE3磁盘缓存 ===")
    
    try:
        from services.blake3_disk_cache import Blake3DiskCache
        
        # 创建临时缓存目录
        with tempfile.TemporaryDirectory() as temp_dir:
            cache = Blake3DiskCache(
                cache_dir=temp_dir,
                max_size_mb=10,
                default_ttl=3600,
                compression="zstd",
                enable_deduplication=True,
                enable_content_verification=True
            )
            
            await cache.initialize()
            print("✓ BLAKE3磁盘缓存初始化成功")
            
            # 测试数据存储
            test_data = {
                "translations": [
                    {"key": "item.diamond_sword", "src": "Diamond Sword", "dst": "钻石剑"},
                    {"key": "item.iron_pickaxe", "src": "Iron Pickaxe", "dst": "铁镐"},
                    {"key": "block.stone", "src": "Stone", "dst": "石头"},
                ],
                "metadata": {
                    "locale": "zh_cn",
                    "mod": "minecraft",
                    "version": "1.21"
                }
            }
            
            # 存储数据
            success = await cache.put("minecraft_translations", test_data, ttl=60)
            if success:
                print("✓ 数据存储成功")
            else:
                print("✗ 数据存储失败")
                return False
            
            # 读取数据
            retrieved_data = await cache.get("minecraft_translations")
            if retrieved_data == test_data:
                print("✓ 数据读取成功，内容匹配")
            else:
                print("✗ 数据读取失败或内容不匹配")
                return False
            
            # 测试去重功能
            duplicate_data = test_data.copy()  # 相同内容
            success2 = await cache.put("minecraft_translations_copy", duplicate_data, ttl=60)
            
            if success2:
                print("✓ 重复数据存储（去重）")
            else:
                print("✗ 重复数据存储失败")
                return False
            
            # 验证去重效果
            stats = cache.get_stats()
            if stats["deduplication_saves"] > 0:
                print(f"✓ 去重生效: 节省 {stats['deduplication_saves']} 次存储")
            
            # 测试不同内容
            different_data = {
                "translations": [
                    {"key": "item.golden_apple", "src": "Golden Apple", "dst": "金苹果"},
                ],
                "metadata": {
                    "locale": "zh_cn",
                    "mod": "minecraft"
                }
            }
            
            await cache.put("different_translations", different_data)
            
            # 获取统计信息
            final_stats = cache.get_stats()
            print(f"✓ 缓存统计:")
            print(f"  总条目: {final_stats['total_entries']}")
            print(f"  唯一内容块: {final_stats['unique_content_blocks']}")
            print(f"  缓存命中率: {final_stats['cache_hit_rate']}%")
            print(f"  压缩比: {final_stats['average_compression_ratio']}")
            print(f"  去重节省: {final_stats['deduplication_saves']} 次")
            
            await cache.shutdown()
            return True
            
    except Exception as e:
        print(f"✗ BLAKE3磁盘缓存测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_hash_algorithm_benchmark():
    """测试哈希算法性能基准"""
    print("\n=== 测试哈希算法性能基准 ===")
    
    try:
        from services.content_addressing import benchmark_hash_algorithms
        
        # 准备测试数据
        test_sizes = [1024, 10240, 102400]  # 1KB, 10KB, 100KB
        
        for size in test_sizes:
            test_data = b"x" * size
            print(f"\n测试数据大小: {size} bytes ({size/1024:.1f} KB)")
            
            results = benchmark_hash_algorithms(test_data, iterations=100)
            
            # 按性能排序
            sorted_results = sorted(results.items(), key=lambda x: x[1])
            
            print("性能排序（越小越快）:")
            for i, (algorithm, avg_time) in enumerate(sorted_results):
                print(f"  {i+1}. {algorithm}: {avg_time:.3f} ms")
            
            # 计算相对性能
            fastest = sorted_results[0][1]
            print("相对性能:")
            for algorithm, avg_time in sorted_results:
                relative = avg_time / fastest
                print(f"  {algorithm}: {relative:.2f}x")
        
        return True
        
    except Exception as e:
        print(f"✗ 哈希算法基准测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False

async def test_integrated_workflow():
    """测试集成工作流"""
    print("\n=== 测试集成工作流 ===")
    
    try:
        from services.content_addressing import ContentAddressingSystem, HashAlgorithm
        from services.blake3_disk_cache import Blake3DiskCache
        
        # 模拟一个完整的工作流：内容寻址 + 磁盘缓存
        with tempfile.TemporaryDirectory() as temp_dir:
            # 创建系统
            cas = ContentAddressingSystem(HashAlgorithm.BLAKE3)
            cache = Blake3DiskCache(
                cache_dir=temp_dir,
                max_size_mb=5,
                enable_deduplication=True
            )
            
            await cache.initialize()
            
            # 模拟翻译数据处理流程
            translation_sets = [
                {
                    "mod": "minecraft",
                    "translations": [
                        {"key": "item.diamond", "src": "Diamond", "dst": "钻石"},
                        {"key": "item.emerald", "src": "Emerald", "dst": "绿宝石"},
                    ]
                },
                {
                    "mod": "create",
                    "translations": [
                        {"key": "item.copper_ingot", "src": "Copper Ingot", "dst": "铜锭"},
                        {"key": "block.copper_block", "src": "Copper Block", "dst": "铜块"},
                    ]
                },
                {
                    "mod": "minecraft",  # 重复mod，测试去重
                    "translations": [
                        {"key": "item.diamond", "src": "Diamond", "dst": "钻石"},  # 重复数据
                        {"key": "item.emerald", "src": "Emerald", "dst": "绿宝石"},
                    ]
                }
            ]
            
            processed_count = 0
            dedup_count = 0
            
            for i, data in enumerate(translation_sets):
                # 计算内容CID
                cid = cas.compute_cid(data)
                
                # 存储到磁盘缓存
                cache_key = f"translations_{data['mod']}_{i}"
                success = await cache.put(cache_key, data)
                
                if success:
                    processed_count += 1
                    print(f"✓ 处理翻译集 {i+1}: {data['mod']} (CID: {str(cid)[:16]}...)")
                
                # 验证数据完整性
                retrieved = await cache.get(cache_key)
                if retrieved and cas.verify_content(retrieved, cid):
                    print(f"  内容验证通过")
                else:
                    print(f"  内容验证失败")
                    return False
            
            # 获取最终统计
            cas_stats = cas.get_performance_stats()
            cache_stats = cache.get_stats()
            
            print(f"\n✓ 集成工作流完成:")
            print(f"  处理翻译集: {processed_count} 个")
            print(f"  哈希操作: {cas_stats['hash_operations']} 次")
            print(f"  缓存条目: {cache_stats['total_entries']} 个")
            print(f"  唯一内容块: {cache_stats['unique_content_blocks']} 个")
            print(f"  去重节省: {cache_stats['deduplication_saves']} 次")
            print(f"  缓存命中率: {cache_stats['cache_hit_rate']}%")
            
            await cache.shutdown()
            return True
            
    except Exception as e:
        print(f"✗ 集成工作流测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False

async def main():
    """运行所有BLAKE3内容寻址测试"""
    print("🚀 开始BLAKE3内容寻址系统测试")
    print("=" * 60)
    
    tests = [
        test_content_addressing,
        test_file_content_addressing,
        test_blake3_disk_cache,
        test_hash_algorithm_benchmark,
        test_integrated_workflow
    ]
    
    passed = 0
    total = len(tests)
    
    for i, test in enumerate(tests):
        try:
            if asyncio.iscoroutinefunction(test):
                result = await test()
            else:
                result = test()
            
            if result:
                passed += 1
        except Exception as e:
            print(f"测试异常: {e}")
            import traceback
            traceback.print_exc()
    
    print("\n" + "=" * 60)
    print(f"🏁 BLAKE3内容寻址测试完成: {passed}/{total} 通过")
    
    if passed == total:
        print("🎉 所有BLAKE3测试通过!")
        return 0
    else:
        print("❌ 部分测试失败，需要检查实现")
        return 1

if __name__ == "__main__":
    exit(asyncio.run(main()))