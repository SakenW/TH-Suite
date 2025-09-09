#!/usr/bin/env python
"""
测试扩展功能集成
验证磁盘缓存、同步监控、覆盖链处理等新功能
"""

import sys
import os
import time
import json
import asyncio
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

async def test_disk_cache():
    """测试磁盘JSON缓存"""
    print("=== 测试磁盘JSON缓存 ===")
    
    try:
        from services.disk_cache import DiskJSONCache
        
        # 创建临时缓存目录
        cache_dir = "./test_cache"
        cache = DiskJSONCache(
            cache_dir=cache_dir,
            max_size_mb=10,
            default_ttl=3600
        )
        
        await cache.initialize()
        print("✓ 磁盘缓存初始化成功")
        
        # 测试数据存储
        test_data = {
            "translations": [
                {"key": "item.test.disk_cache", "src": "Disk Cache Test", "dst": "磁盘缓存测试"},
                {"key": "block.test.performance", "src": "Performance Block", "dst": "性能方块"},
            ],
            "metadata": {
                "locale": "zh_cn",
                "source": "disk_cache_test"
            }
        }
        
        success = await cache.put("test_translations", test_data, ttl=60)
        if success:
            print("✓ 数据存储成功")
        else:
            print("✗ 数据存储失败")
            return False
        
        # 测试数据读取
        retrieved_data = await cache.get("test_translations")
        if retrieved_data == test_data:
            print("✓ 数据读取成功，内容匹配")
        else:
            print("✗ 数据读取失败或内容不匹配")
            return False
        
        # 测试缓存统计
        stats = cache.get_stats()
        print(f"✓ 缓存统计: {stats['total_entries']} 条目, {stats['total_size_mb']} MB")
        
        # 测试条目信息
        entries = cache.get_entries_info()
        print(f"✓ 条目信息: {len(entries)} 个条目")
        
        # 清理测试缓存
        await cache.clear()
        await cache.shutdown()
        
        # 清理目录
        import shutil
        if os.path.exists(cache_dir):
            shutil.rmtree(cache_dir)
        
        return True
        
    except Exception as e:
        print(f"✗ 磁盘缓存测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_sync_metrics():
    """测试同步协议性能监控"""
    print("\n=== 测试同步协议性能监控 ===")
    
    try:
        from services.sync_metrics import SyncMetricsCollector
        
        collector = SyncMetricsCollector()
        print("✓ 性能监控初始化")
        
        # 测试Bloom过滤器监控
        collector.record_bloom_handshake(
            elements_checked=1000,
            filter_size_bytes=8192,
            missing_count=50,
            total_count=1000
        )
        print("✓ Bloom握手性能记录")
        
        # 测试压缩监控
        collector.record_compression(
            algorithm="zstd",
            input_bytes=10240,
            output_bytes=3072,
            compression_time_ms=15.5
        )
        
        collector.record_compression(
            algorithm="gzip",
            input_bytes=8192,
            output_bytes=2048,
            compression_time_ms=25.2
        )
        print("✓ 压缩性能记录")
        
        # 测试同步会话监控
        session = collector.start_sync_session("test_session_001", "client_001")
        
        collector.record_handshake_time("test_session_001", 50.0)
        collector.record_chunk_upload("test_session_001", 1024, 20.0)
        collector.record_chunk_upload("test_session_001", 2048, 35.0)
        collector.record_merge_operation("test_session_001", 100.0, 2)
        
        collector.complete_sync_session("test_session_001", "completed")
        print("✓ 同步会话监控")
        
        # 测试综合统计
        stats = collector.get_comprehensive_stats()
        print(f"✓ 综合统计: Bloom握手 {stats['bloom_filter']['total_handshakes']} 次")
        print(f"  压缩操作 {stats['compression']['total_operations']} 次")
        print(f"  已完成会话 {stats['sync_sessions']['completed_sessions']} 个")
        
        # 测试性能趋势
        trends = collector.get_performance_trends(hours=1)
        print(f"✓ 性能趋势: 吞吐量样本 {trends['throughput']['samples']} 个")
        
        return True
        
    except Exception as e:
        print(f"✗ 同步监控测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_override_chain():
    """测试覆盖链处理"""
    print("\n=== 测试覆盖链处理 ===")
    
    try:
        from services.override_chain import (
            OverrideChainProcessor, 
            OverridePriority,
            OverrideSource,
            TranslationOverride
        )
        
        processor = OverrideChainProcessor()
        print("✓ 覆盖链处理器初始化")
        
        # 创建测试覆盖源
        mod_source = processor.create_override_source(
            source_type="mod",
            source_id="test_mod",
            source_name="测试MOD",
            version="1.0.0"
        )
        
        resource_pack_source = processor.create_override_source(
            source_type="resource_pack", 
            source_id="test_pack",
            source_name="测试资源包",
            version="2.0.0"
        )
        
        print("✓ 覆盖源创建成功")
        
        # 创建测试翻译覆盖
        mod_translation = TranslationOverride(
            key="item.test.override",
            locale="zh_cn",
            src_text="Override Test Item",
            dst_text="MOD覆盖测试物品",
            status="reviewed",
            source=mod_source,
            priority=OverridePriority.MOD,
            locked_fields={"key", "src_text"},
            metadata={"source": "mod"},
            created_at="2025-09-10T01:00:00Z",
            updated_at="2025-09-10T01:00:00Z"
        )
        
        pack_translation = TranslationOverride(
            key="item.test.override",
            locale="zh_cn", 
            src_text="Override Test Item",
            dst_text="资源包覆盖测试物品",
            status="approved",
            source=resource_pack_source,
            priority=OverridePriority.RESOURCE_PACK,
            locked_fields={"key", "src_text", "dst_text"},
            metadata={"source": "resource_pack"},
            created_at="2025-09-10T02:00:00Z",
            updated_at="2025-09-10T02:00:00Z"
        )
        
        # 处理覆盖链
        result = processor.process_override_chain(
            [mod_translation, pack_translation],
            "item.test.override",
            "zh_cn"
        )
        
        if result:
            print(f"✓ 覆盖链处理成功: 最终优先级 {result.priority.name}")
            print(f"  最终翻译: {result.dst_text}")
            print(f"  锁定字段: {result.locked_fields}")
        else:
            print("✗ 覆盖链处理失败")
            return False
        
        # 测试批量处理
        batch_result = processor.batch_process_overrides(
            [mod_translation, pack_translation],
            "zh_cn"
        )
        
        print(f"✓ 批量处理: {len(batch_result)} 个key处理完成")
        
        # 测试手动覆盖
        manual_override = processor.create_manual_override(
            key="item.test.manual",
            locale="zh_cn",
            dst_text="手动覆盖翻译",
            user_id="test_user",
            reason="测试手动覆盖功能"
        )
        
        print(f"✓ 手动覆盖创建: {manual_override.priority.name}")
        
        # 测试验证
        all_translations = [mod_translation, pack_translation, manual_override]
        issues = processor.validate_override_chain(all_translations)
        print(f"✓ 覆盖链验证: {len(issues)} 个问题")
        
        # 测试统计
        stats = processor.get_override_statistics(all_translations)
        print(f"✓ 覆盖链统计: 总计 {stats['total_translations']} 个翻译")
        print(f"  按优先级: {stats['by_priority']}")
        
        return True
        
    except Exception as e:
        print(f"✗ 覆盖链测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False

async def test_integrated_workflow():
    """测试集成工作流"""
    print("\n=== 测试集成工作流 ===")
    
    try:
        # 模拟一个完整的工作流：缓存 + 监控 + 覆盖
        from services.sync_metrics import get_sync_metrics
        from services.override_chain import get_override_processor
        
        metrics = get_sync_metrics()
        processor = get_override_processor()
        
        # 模拟同步会话开始
        session = metrics.start_sync_session("workflow_test", "integrated_client")
        
        # 模拟Bloom握手
        start_time = time.time()
        await asyncio.sleep(0.05)  # 模拟网络延迟
        handshake_time = (time.time() - start_time) * 1000
        
        metrics.record_handshake_time(session.session_id, handshake_time)
        metrics.record_bloom_handshake(500, 4096, 25, 500)
        
        # 模拟数据压缩和传输
        metrics.record_compression("zstd", 20480, 4096, 12.5)
        metrics.record_chunk_upload(session.session_id, 4096, 30.0)
        
        # 模拟覆盖链处理
        # (这里简化处理，实际应用中会有复杂的翻译数据)
        
        # 完成会话
        metrics.complete_sync_session(session.session_id, "completed")
        
        print("✓ 集成工作流完成")
        
        # 获取最终统计
        final_stats = metrics.get_comprehensive_stats()
        print(f"  最终会话数: {final_stats['sync_sessions']['completed_sessions']}")
        print(f"  压缩比: {final_stats['compression']['average_compression_ratio']:.3f}")
        
        return True
        
    except Exception as e:
        print(f"✗ 集成工作流测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False

async def main():
    """运行所有扩展功能测试"""
    print("🚀 开始扩展功能集成测试")
    print("=" * 60)
    
    tests = [
        test_disk_cache,
        test_sync_metrics,
        test_override_chain,
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
    print(f"🏁 扩展功能测试完成: {passed}/{total} 通过")
    
    if passed == total:
        print("🎉 所有扩展功能测试通过!")
        return 0
    else:
        print("❌ 部分测试失败，需要检查实现")
        return 1

if __name__ == "__main__":
    exit(asyncio.run(main()))