#!/usr/bin/env python
"""
测试高级功能集成
验证数据库集成、压缩中间件、QA规则引擎、高级缓存等功能
"""

import sys
import os
import time
import json
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

def test_compression_middleware():
    """测试压缩中间件"""
    print("=== 测试压缩中间件 ===")
    
    try:
        from api.v6.middleware.compression import CompressionMiddleware
        
        # 创建测试数据
        test_data = json.dumps({
            "translations": [
                {"key": "item.create.brass_ingot", "src": "Brass Ingot", "dst": "黄铜锭"},
                {"key": "block.create.brass_block", "src": "Brass Block", "dst": "黄铜块"},
            ] * 50  # 重复50次创建较大的数据
        }, ensure_ascii=False).encode('utf-8')
        
        print(f"✓ 创建测试数据: {len(test_data)} 字节")
        
        # 测试压缩中间件
        middleware = CompressionMiddleware(None, min_response_size=100)
        import asyncio
        
        # 测试Zstd压缩（如果可用）
        from api.v6.middleware.compression import ZSTD_AVAILABLE
        if ZSTD_AVAILABLE:
            compressed_zstd = asyncio.run(middleware._compress_with_zstd(test_data, 'zh_cn'))
            if compressed_zstd:
                compression_ratio = len(compressed_zstd) / len(test_data)
                print(f"✓ Zstd压缩: {len(test_data)} → {len(compressed_zstd)} 字节 (比例: {compression_ratio:.3f})")
            else:
                print("✗ Zstd压缩失败")
        
        # 测试Gzip压缩（fallback）
        compressed_gzip = asyncio.run(middleware._compress_with_gzip(test_data))
        
        if compressed_gzip:
            compression_ratio = len(compressed_gzip) / len(test_data)
            print(f"✓ Gzip压缩: {len(test_data)} → {len(compressed_gzip)} 字节 (比例: {compression_ratio:.3f})")
        else:
            print("✗ Gzip压缩失败")
            return False
        
        # 测试locale字典
        dictionary = middleware._create_locale_dictionary('zh_cn')
        if dictionary:
            print(f"✓ 创建zh_cn字典: {len(dictionary)} 字节")
        
        # 测试压缩统计
        stats = middleware.get_compression_stats()
        print(f"✓ 压缩配置: level={stats['compression_level']}, min_size={stats['min_response_size']}")
        
        return True
        
    except Exception as e:
        print(f"✗ 压缩中间件测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_qa_engine():
    """测试QA规则引擎"""
    print("\n=== 测试QA规则引擎 ===")
    
    try:
        from services.qa_engine import get_qa_engine
        from database.repositories.translation_entry_repository import TranslationEntry
        
        qa_engine = get_qa_engine()
        print(f"✓ QA引擎初始化: {len(qa_engine.rules)} 个规则")
        
        # 测试占位符检查
        test_entries = [
            # 正常条目
            TranslationEntry(
                uid="normal_001",
                key="item.test.normal",
                src_text="A simple %s item",
                dst_text="一个简单的%s物品",
                status="reviewed"
            ),
            # 占位符数量不匹配
            TranslationEntry(
                uid="placeholder_mismatch_001",
                key="item.test.placeholder",
                src_text="Item %s with %d count",
                dst_text="物品%s",  # 缺少%d
                status="new"
            ),
            # 空翻译
            TranslationEntry(
                uid="empty_001",
                key="item.test.empty",
                src_text="Empty item",
                dst_text="",
                status="new"
            ),
            # 翻译过长
            TranslationEntry(
                uid="long_001",
                key="item.test.long",
                src_text="Short",
                dst_text="这是一个非常非常非常长的翻译内容，远远超过了原文的长度，可能存在问题",
                status="reviewed"
            ),
            # Minecraft格式
            TranslationEntry(
                uid="mc_format_001", 
                key="item.test.colored",
                src_text="§aGreen §bblue §cred text",
                dst_text="绿色 蓝色 红色 文本",  # 缺少颜色代码
                status="reviewed"
            )
        ]
        
        issues_count = 0
        for entry in test_entries:
            issues = qa_engine.check_entry(entry)
            if issues:
                issues_count += len(issues)
                print(f"  ⚠️  {entry.uid}: {len(issues)} 个问题")
                for issue in issues:
                    print(f"    - {issue.severity.value}: {issue.message}")
            else:
                print(f"  ✓ {entry.uid}: 无问题")
        
        # 批量检查
        batch_results = qa_engine.check_entries(test_entries)
        print(f"✓ 批量检查: {len(batch_results)} 个条目有问题，总计 {issues_count} 个问题")
        
        # 测试规则管理
        rules_info = qa_engine.get_rules_info()
        print(f"✓ 规则信息: {len(rules_info)} 个规则")
        
        return True
        
    except Exception as e:
        print(f"✗ QA规则引擎测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_advanced_cache():
    """测试高级缓存"""
    print("\n=== 测试高级缓存 ===")
    
    try:
        from services.advanced_cache import get_cache_service, CacheKeyGenerator
        
        cache_service = get_cache_service()
        print("✓ 缓存服务初始化")
        
        # 测试LRU缓存
        test_data = {"test": "value", "number": 42}
        
        # 测试缓存存储和获取
        cache_service.cache.put_translation("test_key", test_data)
        retrieved = cache_service.cache.get_translation("test_key")
        
        if retrieved == test_data:
            print("✓ 缓存存储和获取成功")
        else:
            print("✗ 缓存数据不匹配")
            return False
        
        # 测试缓存键生成器
        key_gen = CacheKeyGenerator()
        translation_key = key_gen.translation_key("test_uid")
        stats_key = key_gen.statistics_key("progress", {"locale": "zh_cn"})
        
        print(f"✓ 缓存键生成: {translation_key}, {stats_key}")
        
        # 测试get_or_compute
        def expensive_computation():
            time.sleep(0.1)  # 模拟耗时操作
            return {"computed": True, "timestamp": time.time()}
        
        start_time = time.time()
        result1 = cache_service.get_or_compute("compute_test", expensive_computation)
        first_call_time = time.time() - start_time
        
        start_time = time.time()
        result2 = cache_service.get_or_compute("compute_test", expensive_computation)
        second_call_time = time.time() - start_time
        
        if result1 == result2 and second_call_time < first_call_time:
            print(f"✓ 缓存加速: 首次 {first_call_time*1000:.1f}ms，缓存 {second_call_time*1000:.1f}ms")
        else:
            print("✗ 缓存加速失败")
            return False
        
        # 测试缓存统计
        stats = cache_service.cache.get_all_stats()
        print(f"✓ 缓存统计: L1命中率 {stats['l1_translations']['hit_rate']}")
        
        # 测试健康报告
        health = cache_service.get_health_report()
        print(f"✓ 健康报告: 评分 {health['health_score']}, 内存 {health['memory_usage_mb']:.1f}MB")
        
        # 测试缓存清理
        import asyncio
        cleaned = asyncio.run(cache_service.cleanup_expired())
        print(f"✓ 清理过期缓存: {cleaned} 个条目")
        
        return True
        
    except Exception as e:
        print(f"✗ 高级缓存测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_sync_service_integration():
    """测试同步服务集成"""
    print("\n=== 测试同步服务集成 ===")
    
    try:
        # 由于需要数据库连接，这里只测试服务创建
        from api.v6.sync.sync_service import SyncProtocolService
        from database.core.manager import McL10nDatabaseManager
        
        print("✓ 同步服务导入成功")
        
        # 测试Entry-Delta处理器
        from api.v6.sync.entry_delta import get_entry_delta_processor, MergeContext
        from database.repositories.translation_entry_repository import TranslationEntry
        
        processor = get_entry_delta_processor()
        
        # 创建测试条目
        test_entry = TranslationEntry(
            uid="sync_test_001",
            uida_keys_b64="test_uida_keys",
            uida_hash="test_blake3",
            key="item.sync.test",
            src_text="Sync Test Item",
            dst_text="同步测试物品",
            status="reviewed",
            language_file_uid="test_file_001"
        )
        
        # 序列化为Entry-Delta
        delta = processor.serialize_entry_delta(test_entry, "update")
        print(f"✓ Entry-Delta序列化: {delta.entry_uid}")
        
        # 创建载荷
        payload = processor.create_delta_payload([delta])
        print(f"✓ 载荷创建: {len(payload)} 字节")
        
        # 计算CID
        cid = processor.calculate_payload_cid(payload)
        print(f"✓ CID计算: {cid}")
        
        # 解析载荷
        parsed_deltas = processor.parse_delta_payload(payload)
        print(f"✓ 载荷解析: {len(parsed_deltas)} 个Entry-Delta")
        
        # 测试3-way合并
        local_entry = TranslationEntry(
            uid="sync_test_001",
            key="item.sync.test",
            src_text="Sync Test Item",
            dst_text="本地翻译",
            status="new"
        )
        
        remote_entry = TranslationEntry(
            uid="sync_test_001", 
            key="item.sync.test",
            src_text="Sync Test Item",
            dst_text="远程翻译",
            status="reviewed"
        )
        
        context = MergeContext(
            base_entry=None,
            local_entry=local_entry,
            remote_entry=remote_entry,
            merge_strategy="3way",
            conflict_resolution="mark_for_review"
        )
        
        merge_result = processor.perform_3way_merge(context)
        print(f"✓ 3-way合并: 成功={merge_result.success}, 冲突={merge_result.has_conflict}")
        
        return True
        
    except Exception as e:
        print(f"✗ 同步服务集成测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_middleware_integration():
    """测试中间件集成"""
    print("\n=== 测试中间件集成 ===")
    
    try:
        from api.v6.middleware.middleware import V6MiddlewareConfig, setup_v6_middlewares
        from fastapi import FastAPI
        
        # 创建测试配置
        config = V6MiddlewareConfig(
            enable_idempotency=True,
            enable_ndjson=True, 
            enable_etag=True,
            enable_compression=True,
            compression_level=6,
            min_compression_size=512
        )
        
        print(f"✓ 中间件配置: 压缩={config.enable_compression}, 级别={config.compression_level}")
        
        # 创建测试应用 (不实际运行)
        app = FastAPI()
        
        print("✓ 中间件集成配置完成")
        
        # 测试中间件组件
        from api.v6.middleware.idempotency import get_cache_stats
        from api.v6.middleware.compression import CompressionMiddleware
        
        # 测试幂等性缓存
        cache_stats = get_cache_stats()
        print(f"✓ 幂等性缓存: {cache_stats}")
        
        # 测试压缩中间件
        compression = CompressionMiddleware(None)
        comp_stats = compression.get_compression_stats()
        print(f"✓ 压缩中间件: zstd可用={comp_stats['zstd_available']}")
        
        return True
        
    except Exception as e:
        print(f"✗ 中间件集成测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False

async def run_async_tests():
    """运行需要async的测试"""
    return await test_compression_middleware()

def main():
    """运行所有高级功能测试"""
    print("🚀 开始高级功能集成测试")
    print("=" * 60)
    
    tests = [
        test_compression_middleware,  # 重新启用压缩测试
        test_qa_engine,
        test_advanced_cache,
        test_sync_service_integration,
        test_middleware_integration
    ]
    
    passed = 0
    total = len(tests)
    
    for test in tests:
        try:
            if test():
                passed += 1
        except Exception as e:
            print(f"测试异常: {e}")
            import traceback
            traceback.print_exc()
    
    print("\n" + "=" * 60)
    print(f"🏁 高级功能测试完成: {passed}/{total} 通过")
    
    if passed == total:
        print("🎉 所有高级功能测试通过!")
        return 0
    else:
        print("❌ 部分测试失败，需要检查实现")
        return 1

if __name__ == "__main__":
    exit(main())