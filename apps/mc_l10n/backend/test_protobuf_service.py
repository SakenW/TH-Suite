#!/usr/bin/env python
"""
测试Protobuf序列化服务
验证序列化、压缩、批处理等功能
"""

import sys
import os
import time
import json
import asyncio
from typing import List, Dict, Any

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

def test_protobuf_serialization():
    """测试基本Protobuf序列化功能"""
    print("=== 测试Protobuf序列化 ===")
    
    try:
        from services.protobuf_service import ProtobufSerializer, TranslationProtobufConverter
        
        # 创建序列化器
        serializer = ProtobufSerializer(
            enable_compression=True,
            compression_algorithm="zstd",
            enable_content_addressing=True
        )
        
        converter = TranslationProtobufConverter(serializer)
        print("✓ Protobuf服务初始化成功")
        
        # 测试翻译条目转换
        test_entry = {
            "uid": "entry_001",
            "key": "item.diamond_sword",
            "locale": "zh_cn",
            "src_text": "Diamond Sword",
            "dst_text": "钻石剑",
            "status": "approved",
            "created_at": "2025-09-10T12:00:00",
            "updated_at": "2025-09-10T12:30:00",
            "language_file_uid": "minecraft_zh_cn_001",
            "pack_uid": "minecraft_vanilla",
            "metadata": {
                "translator": "test_user",
                "confidence": "0.95",
                "source": "crowdsourced"
            },
            "notes": "高质量翻译",
            "version": 1
        }
        
        # 转换为Protobuf消息
        proto_entry = converter.translation_entry_to_proto(test_entry)
        print("✓ 翻译条目转换为Protobuf消息")
        
        # 序列化
        serialized_data = serializer.serialize(proto_entry)
        print(f"✓ 序列化完成，大小: {len(serialized_data)} bytes")
        
        # 反序列化
        import generated.translation_pb2 as pb
        deserialized_entry = serializer.deserialize(serialized_data, pb.TranslationEntry)
        print("✓ 反序列化成功")
        
        # 转换回字典
        recovered_entry = converter.proto_to_translation_entry(deserialized_entry)
        
        # 验证数据完整性
        key_fields = ["uid", "key", "locale", "src_text", "dst_text", "status"]
        for field in key_fields:
            if recovered_entry.get(field) != test_entry.get(field):
                print(f"✗ 字段不匹配: {field}")
                return False
        
        print("✓ 数据完整性验证通过")
        
        # 测试JSON序列化（用于调试）
        json_str = serializer.serialize_to_json(proto_entry)
        print("✓ JSON序列化成功")
        
        json_deserialized = serializer.deserialize_from_json(json_str, pb.TranslationEntry)
        if json_deserialized.uid == test_entry["uid"]:
            print("✓ JSON反序列化验证通过")
        else:
            print("✗ JSON反序列化验证失败")
            return False
        
        # 获取性能统计
        stats = serializer.get_stats()
        print(f"✓ 性能统计: {stats['serializations']} 次序列化, {stats['deserializations']} 次反序列化")
        
        return True
        
    except Exception as e:
        print(f"✗ Protobuf序列化测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_batch_processing():
    """测试批处理功能"""
    print("\n=== 测试Protobuf批处理 ===")
    
    try:
        from services.protobuf_service import ProtobufBatchProcessor, ProtobufSerializer, TranslationProtobufConverter
        
        # 创建批处理器
        serializer = ProtobufSerializer(enable_compression=True)
        converter = TranslationProtobufConverter(serializer)
        processor = ProtobufBatchProcessor(
            serializer, 
            converter, 
            batch_size=10,  # 小批次用于测试
            max_batch_size_bytes=1024  # 1KB限制
        )
        
        print("✓ 批处理器初始化成功")
        
        # 创建测试数据
        test_entries = []
        for i in range(25):  # 创建25个条目，应该分成3个批次
            entry = {
                "uid": f"entry_{i:03d}",
                "key": f"item.test_{i}",
                "locale": "zh_cn",
                "src_text": f"Test Item {i}",
                "dst_text": f"测试物品{i}",
                "status": "approved" if i % 2 == 0 else "pending",
                "created_at": int(time.time()),
                "updated_at": int(time.time()),
                "language_file_uid": "test_file",
                "pack_uid": "test_pack",
                "metadata": {
                    "batch_test": "true",
                    "item_id": str(i)
                }
            }
            test_entries.append(entry)
        
        # 批处理
        batch_info = {
            "batch_id": "test_batch_001",
            "source": "unit_test",
            "metadata": {
                "test_type": "batch_processing"
            }
        }
        
        batch_bytes_list = processor.process_translation_entries_batch(test_entries, batch_info)
        print(f"✓ 批处理完成: {len(batch_bytes_list)} 个批次")
        
        # 验证每个批次
        total_recovered_entries = 0
        import generated.translation_pb2 as pb
        
        for i, batch_bytes in enumerate(batch_bytes_list):
            batch = serializer.deserialize(batch_bytes, pb.TranslationBatch)
            total_recovered_entries += len(batch.entries)
            print(f"  批次 {i+1}: {len(batch.entries)} 个条目")
        
        if total_recovered_entries == len(test_entries):
            print("✓ 批次数据完整性验证通过")
        else:
            print(f"✗ 批次数据丢失: 期望 {len(test_entries)}, 实际 {total_recovered_entries}")
            return False
        
        # 测试批次合并
        merged_batch = processor.merge_batches(batch_bytes_list)
        print(f"✓ 批次合并完成: {len(merged_batch.entries)} 个条目")
        
        if len(merged_batch.entries) == len(test_entries):
            print("✓ 合并后数据完整性验证通过")
        else:
            print(f"✗ 合并后数据丢失: 期望 {len(test_entries)}, 实际 {len(merged_batch.entries)}")
            return False
        
        return True
        
    except Exception as e:
        print(f"✗ 批处理测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_sync_protocol():
    """测试同步协议消息"""
    print("\n=== 测试同步协议 ===")
    
    try:
        from services.protobuf_service import ProtobufSerializer, TranslationProtobufConverter
        import generated.translation_pb2 as pb
        
        serializer = ProtobufSerializer()
        converter = TranslationProtobufConverter(serializer)
        
        # 测试同步请求
        sync_request = converter.create_sync_request(
            session_id="session_001",
            client_id="client_test",
            locale="zh_cn",
            pack_uids=["minecraft", "create_mod"],
            since_timestamp=int(time.time() - 3600),  # 一小时前
            compression="zstd"
        )
        
        print("✓ 同步请求创建成功")
        
        # 序列化同步请求
        request_bytes = serializer.serialize(sync_request)
        print(f"✓ 同步请求序列化完成: {len(request_bytes)} bytes")
        
        # 反序列化验证
        deserialized_request = serializer.deserialize(request_bytes, pb.SyncRequest)
        if (deserialized_request.session_id == "session_001" and 
            deserialized_request.client_id == "client_test" and
            deserialized_request.locale == "zh_cn"):
            print("✓ 同步请求反序列化验证通过")
        else:
            print("✗ 同步请求反序列化验证失败")
            return False
        
        # 测试同步响应
        added_entries = [
            {
                "uid": "new_entry_001",
                "key": "item.new_item",
                "locale": "zh_cn",
                "src_text": "New Item",
                "dst_text": "新物品",
                "status": "approved",
                "created_at": int(time.time()),
                "updated_at": int(time.time()),
                "language_file_uid": "test_file",
                "pack_uid": "test_pack"
            }
        ]
        
        updated_entries = [
            {
                "uid": "updated_entry_001",
                "key": "item.updated_item",
                "locale": "zh_cn", 
                "src_text": "Updated Item",
                "dst_text": "更新物品",
                "status": "approved",
                "created_at": int(time.time() - 1000),
                "updated_at": int(time.time()),
                "language_file_uid": "test_file",
                "pack_uid": "test_pack"
            }
        ]
        
        deleted_uids = ["deleted_entry_001", "deleted_entry_002"]
        
        sync_response = converter.create_sync_response(
            session_id="session_001",
            status=pb.SYNC_SUCCESS,
            added_entries=added_entries,
            updated_entries=updated_entries,
            deleted_uids=deleted_uids
        )
        
        print("✓ 同步响应创建成功")
        
        # 验证响应内容
        if (len(sync_response.added_entries) == 1 and
            len(sync_response.updated_entries) == 1 and
            len(sync_response.deleted_entry_uids) == 2 and
            sync_response.total_changes == 4):
            print("✓ 同步响应内容验证通过")
        else:
            print("✗ 同步响应内容验证失败")
            return False
        
        # 序列化同步响应
        response_bytes = serializer.serialize(sync_response)
        print(f"✓ 同步响应序列化完成: {len(response_bytes)} bytes")
        
        return True
        
    except Exception as e:
        print(f"✗ 同步协议测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_compression_performance():
    """测试压缩性能"""
    print("\n=== 测试压缩性能 ===")
    
    try:
        from services.protobuf_service import ProtobufSerializer, TranslationProtobufConverter
        import generated.translation_pb2 as pb
        
        # 测试不同压缩算法
        algorithms = ["zstd", "gzip", "zlib"]  # 不包含 "none" 因为需要特殊处理
        results = {}
        
        # 创建大量测试数据
        test_entries = []
        for i in range(1000):
            entry = {
                "uid": f"perf_entry_{i:04d}",
                "key": f"item.performance_test_{i}",
                "locale": "zh_cn",
                "src_text": f"Performance Test Item {i} with some longer description text",
                "dst_text": f"性能测试物品{i}，包含一些更长的描述文本用于测试压缩效果",
                "status": "approved",
                "created_at": int(time.time()),
                "updated_at": int(time.time()),
                "language_file_uid": "performance_test",
                "pack_uid": "performance_pack",
                "metadata": {
                    "test_type": "performance",
                    "iteration": str(i),
                    "category": "compression_test"
                }
            }
            test_entries.append(entry)
        
        for algorithm in algorithms:
            print(f"\n测试压缩算法: {algorithm}")
            
            try:
                serializer = ProtobufSerializer(
                    enable_compression=True,
                    compression_algorithm=algorithm
                )
                converter = TranslationProtobufConverter(serializer)
                
                # 批量转换和序列化
                start_time = time.time()
                
                total_original_size = 0
                total_compressed_size = 0
                
                for entry in test_entries[:100]:  # 测试前100个条目
                    proto_entry = converter.translation_entry_to_proto(entry)
                    
                    # 未压缩大小
                    uncompressed_data = proto_entry.SerializeToString()
                    total_original_size += len(uncompressed_data)
                    
                    # 压缩后大小
                    compressed_data = serializer.serialize(proto_entry)
                    total_compressed_size += len(compressed_data)
                
                end_time = time.time()
                
                compression_ratio = total_original_size / total_compressed_size if total_compressed_size > 0 else 1.0
                processing_time = (end_time - start_time) * 1000
                
                results[algorithm] = {
                    "compression_ratio": compression_ratio,
                    "processing_time_ms": processing_time,
                    "original_size_kb": total_original_size / 1024,
                    "compressed_size_kb": total_compressed_size / 1024,
                    "space_saved_percent": ((total_original_size - total_compressed_size) / total_original_size) * 100
                }
                
                print(f"  压缩比: {compression_ratio:.2f}")
                print(f"  处理时间: {processing_time:.1f} ms")
                print(f"  空间节省: {results[algorithm]['space_saved_percent']:.1f}%")
                
            except Exception as e:
                print(f"  ⚠️ {algorithm} 测试失败: {e}")
                continue
        
        # 显示性能对比
        if results:
            print("\n性能对比:")
            best_compression = max(results.items(), key=lambda x: x[1]["compression_ratio"])
            fastest_algorithm = min(results.items(), key=lambda x: x[1]["processing_time_ms"])
            
            print(f"最佳压缩: {best_compression[0]} (压缩比 {best_compression[1]['compression_ratio']:.2f})")
            print(f"最快处理: {fastest_algorithm[0]} (时间 {fastest_algorithm[1]['processing_time_ms']:.1f} ms)")
        
        return True
        
    except Exception as e:
        print(f"✗ 压缩性能测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_large_data_handling():
    """测试大数据处理"""
    print("\n=== 测试大数据处理 ===")
    
    try:
        from services.protobuf_service import get_protobuf_service, get_batch_processor
        import generated.translation_pb2 as pb
        
        # 初始化服务
        serializer = get_protobuf_service()
        processor = get_batch_processor()
        
        # 创建大量测试数据
        large_dataset = []
        for i in range(10000):  # 1万个条目
            entry = {
                "uid": f"large_entry_{i:05d}",
                "key": f"large_scale.test_{i}",
                "locale": "zh_cn",
                "src_text": f"Large scale test entry {i}",
                "dst_text": f"大规模测试条目{i}",
                "status": "approved" if i % 3 == 0 else "pending",
                "created_at": int(time.time()),
                "updated_at": int(time.time()),
                "language_file_uid": "large_test",
                "pack_uid": "large_pack"
            }
            large_dataset.append(entry)
        
        print(f"创建了 {len(large_dataset)} 个测试条目")
        
        # 批处理大数据
        start_time = time.time()
        
        batches = processor.process_translation_entries_batch(large_dataset)
        
        processing_time = (time.time() - start_time) * 1000
        
        print(f"✓ 大数据批处理完成:")
        print(f"  处理时间: {processing_time:.1f} ms")
        print(f"  生成批次: {len(batches)} 个")
        print(f"  平均每批次: {len(large_dataset) / len(batches):.0f} 个条目")
        
        # 验证数据完整性
        total_size = sum(len(batch_bytes) for batch_bytes in batches)
        print(f"  总序列化大小: {total_size / 1024 / 1024:.2f} MB")
        
        # 抽样验证
        sample_batch = serializer.deserialize(batches[0], pb.TranslationBatch)
        if len(sample_batch.entries) > 0:
            sample_entry = sample_batch.entries[0]
            if sample_entry.uid and sample_entry.key:
                print("✓ 抽样数据完整性验证通过")
            else:
                print("✗ 抽样数据完整性验证失败")
                return False
        
        # 获取统计信息
        stats = serializer.get_stats()
        print(f"✓ 序列化统计:")
        print(f"  序列化次数: {stats['serializations']}")
        print(f"  平均序列化时间: {stats['average_serialization_time_ms']:.2f} ms")
        print(f"  压缩节省: {stats['compression_saves_bytes'] / 1024:.1f} KB")
        
        return True
        
    except Exception as e:
        print(f"✗ 大数据处理测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False

async def main():
    """运行所有Protobuf测试"""
    print("🚀 开始Protobuf服务测试")
    print("=" * 60)
    
    tests = [
        test_protobuf_serialization,
        test_batch_processing,
        test_sync_protocol,
        test_compression_performance,
        test_large_data_handling
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
    print(f"🏁 Protobuf服务测试完成: {passed}/{total} 通过")
    
    if passed == total:
        print("🎉 所有Protobuf测试通过!")
        return 0
    else:
        print("❌ 部分测试失败，需要检查实现")
        return 1

if __name__ == "__main__":
    exit(asyncio.run(main()))