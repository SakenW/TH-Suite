#!/usr/bin/env python
"""
测试同步协议API功能
验证Bloom握手、分片传输、会话管理等核心功能
"""

import sys
import os
import uuid
import json
import base64
import hashlib
import blake3
from datetime import datetime

sys.path.append('.')

import structlog
from services.content_addressing import compute_cid, HashAlgorithm

# 配置日志
structlog.configure(
    processors=[
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.dev.ConsoleRenderer()
    ]
)

logger = structlog.get_logger(__name__)

def test_bloom_filter():
    """测试Bloom过滤器基本功能"""
    print("=== 测试Bloom过滤器基本功能 ===")
    
    try:
        from api.v6.sync.sync_endpoints import BloomFilter
        
        # 创建Bloom过滤器
        bloom = BloomFilter(bits=1024, hashes=3)
        
        # 添加一些CID
        test_cids = [
            "blake3:1234567890abcdef1234567890abcdef12345678",
            "blake3:abcdef1234567890abcdef1234567890abcdef12",
            "blake3:567890abcdef1234567890abcdef1234567890ab"
        ]
        
        for cid in test_cids:
            bloom.add(cid)
        
        # 测试存在性查询
        for cid in test_cids:
            if bloom.might_contain(cid):
                print(f"✓ CID存在于过滤器: {cid[:20]}...")
            else:
                print(f"✗ CID不存在: {cid[:20]}...")
                return False
        
        # 测试不存在的CID
        non_existent = "blake3:nonexistent1234567890abcdef1234567890"
        if not bloom.might_contain(non_existent):
            print(f"✓ 正确识别不存在的CID: {non_existent[:20]}...")
        
        # 测试序列化
        b64_data = bloom.to_base64()
        print(f"✓ Bloom过滤器Base64长度: {len(b64_data)}")
        
        # 测试反序列化
        bloom2 = BloomFilter.from_base64(b64_data, bits=1024, hashes=3)
        for cid in test_cids:
            if not bloom2.might_contain(cid):
                print(f"✗ 反序列化后CID丢失: {cid[:20]}...")
                return False
        
        print("✓ Bloom过滤器序列化/反序列化成功")
        return True
        
    except Exception as e:
        print(f"✗ Bloom过滤器测试失败: {e}")
        return False

def test_entry_delta_processor():
    """测试Entry-Delta处理器"""
    print("\n=== 测试Entry-Delta处理器 ===")
    
    try:
        from api.v6.sync.entry_delta import get_entry_delta_processor, EntryDelta
        from database.repositories.translation_entry_repository import TranslationEntry
        
        processor = get_entry_delta_processor()
        
        # 创建测试翻译条目
        test_entry = TranslationEntry(
            uid="test_entry_001",
            uida_keys_b64="eyJ0ZXN0IjoidmFsdWUifQ",
            uida_hash="1234567890abcdef",
            key="item.create.brass_ingot",
            src_text="Brass Ingot",
            dst_text="黄铜锭", 
            status="reviewed",
            language_file_uid="test_file_001",
            updated_at=datetime.now().isoformat(),
            qa_flags={"checked": True}
        )
        
        # 序列化为Entry-Delta
        delta = processor.serialize_entry_delta(test_entry, "update")
        print(f"✓ 序列化Entry-Delta: {delta.entry_uid}")
        
        # 反序列化回翻译条目
        restored_entry = processor.deserialize_entry_delta(delta)
        print(f"✓ 反序列化翻译条目: {restored_entry.key}")
        
        # 创建载荷
        deltas = [delta]
        payload_bytes = processor.create_delta_payload(deltas)
        print(f"✓ 创建载荷，大小: {len(payload_bytes)} 字节")
        
        # 解析载荷
        parsed_deltas = processor.parse_delta_payload(payload_bytes)
        print(f"✓ 解析载荷，条目数量: {len(parsed_deltas)}")
        
        # 计算CID
        cid = processor.calculate_payload_cid(payload_bytes)
        print(f"✓ 计算CID: {cid}")
        
        return True
        
    except Exception as e:
        print(f"✗ Entry-Delta处理器测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_sync_models():
    """测试同步协议数据模型"""
    print("\n=== 测试同步协议数据模型 ===")
    
    try:
        from api.v6.sync.models import (
            BloomHandshakeRequest, BloomHandshakeResponse,
            ChunkUploadRequest, ChunkUploadResponse,
            SyncCommitRequest, SyncCommitResponse,
            SyncSession, SyncStatistics
        )
        
        # 测试握手请求
        handshake_req = BloomHandshakeRequest(
            client_id="test_client_001",
            session_id=str(uuid.uuid4()),
            bloom_filter="dGVzdGJsb29tZmlsdGVy"  # base64 encoded
        )
        print(f"✓ 创建握手请求: {handshake_req.client_id}")
        
        # 测试握手响应
        handshake_resp = BloomHandshakeResponse(
            session_id=handshake_req.session_id,
            server_protocol_version="v1",
            missing_cids=["blake3:test123", "blake3:test456"],
            session_expires_at=datetime.now().isoformat()
        )
        print(f"✓ 创建握手响应，缺失CID: {len(handshake_resp.missing_cids)}")
        
        # 测试分片上传请求
        chunk_req = ChunkUploadRequest(
            session_id=handshake_req.session_id,
            cid="blake3:test123",
            chunk_index=0,
            total_chunks=1,
            data="dGVzdGRhdGE=",  # base64 encoded
            data_size=1024,
            chunk_hash="blake3:chunkhash123"
        )
        print(f"✓ 创建分片上传请求: {chunk_req.cid}")
        
        # 测试同步会话
        session = SyncSession(
            session_id=handshake_req.session_id,
            client_id=handshake_req.client_id,
            status="active",
            created_at=datetime.now().isoformat(),
            expires_at=datetime.now().isoformat(),
            chunk_size_bytes=2097152
        )
        print(f"✓ 创建同步会话: {session.status}")
        
        # 测试JSON序列化
        session_json = session.model_dump()
        print(f"✓ 会话JSON序列化: {len(json.dumps(session_json))} 字符")
        
        return True
        
    except Exception as e:
        print(f"✗ 同步协议模型测试失败: {e}")
        return False

def test_cid_calculation():
    """测试CID计算功能"""
    print("\n=== 测试CID计算功能 ===")
    
    try:
        # 测试数据
        test_data = b'{"test": "data", "timestamp": "2025-09-10"}'
        
        # 计算哈希 (使用真实的BLAKE3)
        cid_obj = compute_cid(test_data, HashAlgorithm.BLAKE3)
        cid = str(cid_obj)
        
        print(f"✓ 计算CID: {cid}")
        
        # 测试一致性
        cid_obj2 = compute_cid(test_data, HashAlgorithm.BLAKE3)
        cid2 = str(cid_obj2)
        
        if cid == cid2:
            print("✓ CID计算一致性验证通过")
        else:
            print("✗ CID计算一致性验证失败")
            return False
        
        # 测试不同数据产生不同CID
        different_data = b'{"test": "different", "timestamp": "2025-09-10"}'
        different_cid_obj = compute_cid(different_data, HashAlgorithm.BLAKE3)
        different_cid = str(different_cid_obj)
        
        if cid != different_cid:
            print("✓ 不同数据产生不同CID")
        else:
            print("✗ 不同数据产生了相同CID")
            return False
        
        return True
        
    except Exception as e:
        print(f"✗ CID计算测试失败: {e}")
        return False

def test_merge_scenarios():
    """测试合并场景"""
    print("\n=== 测试合并场景 ===")
    
    try:
        from api.v6.sync.entry_delta import get_entry_delta_processor, MergeContext, MergeResult
        from database.repositories.translation_entry_repository import TranslationEntry
        
        processor = get_entry_delta_processor()
        
        # 场景1: 只有远程版本 (新增)
        remote_entry = TranslationEntry(
            uid="new_entry_001",
            key="item.new.item",
            src_text="New Item",
            dst_text="新物品",
            status="new"
        )
        
        context = MergeContext(
            base_entry=None,
            local_entry=None,
            remote_entry=remote_entry,
            merge_strategy="3way"
        )
        
        result = processor.perform_3way_merge(context)
        if result.success and not result.has_conflict:
            print("✓ 场景1 - 远程新增: 合并成功")
        else:
            print(f"✗ 场景1失败: {result.error_message}")
            return False
        
        # 场景2: 内容冲突
        base_entry = TranslationEntry(
            uid="conflict_entry_001",
            key="item.conflict.item", 
            src_text="Conflict Item",
            dst_text="原始翻译",
            status="reviewed"
        )
        
        local_entry = TranslationEntry(
            uid="conflict_entry_001",
            key="item.conflict.item",
            src_text="Conflict Item", 
            dst_text="本地翻译",
            status="reviewed"
        )
        
        remote_entry = TranslationEntry(
            uid="conflict_entry_001",
            key="item.conflict.item",
            src_text="Conflict Item",
            dst_text="远程翻译", 
            status="reviewed"
        )
        
        context = MergeContext(
            base_entry=base_entry,
            local_entry=local_entry,
            remote_entry=remote_entry,
            merge_strategy="3way",
            conflict_resolution="mark_for_review"
        )
        
        result = processor.perform_3way_merge(context)
        if result.success and result.has_conflict:
            print("✓ 场景2 - 内容冲突: 正确标记为冲突")
        else:
            print(f"✗ 场景2失败: 应该标记为冲突但没有")
            return False
        
        return True
        
    except Exception as e:
        print(f"✗ 合并场景测试失败: {e}")
        return False

def main():
    """运行所有同步协议测试"""
    print("🔄 开始同步协议测试")
    print("=" * 60)
    
    tests = [
        test_bloom_filter,
        test_entry_delta_processor,
        test_sync_models,
        test_cid_calculation,
        test_merge_scenarios
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
    print(f"🏁 同步协议测试完成: {passed}/{total} 通过")
    
    if passed == total:
        print("🎉 所有同步协议测试通过!")
        return 0
    else:
        print("❌ 部分测试失败，需要检查实现")
        return 1

if __name__ == "__main__":
    exit(main())