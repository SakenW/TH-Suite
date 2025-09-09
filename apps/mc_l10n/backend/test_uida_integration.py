#!/usr/bin/env python
"""
测试UIDA集成
验证MC L10n UIDA服务与底层UIDA包的集成
"""

import sys
import asyncio
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

from services.uida_service import get_uida_service, MCUIDANamespace

def test_uida_service_basic():
    """测试UIDA服务基本功能"""
    print("=== 测试UIDA服务基本功能 ===")
    
    try:
        uida_service = get_uida_service()
        print("✓ UIDA服务初始化成功")
        
        # 测试翻译条目UIDA生成
        uida_components = uida_service.generate_translation_entry_uida(
            mod_id="create",
            translation_key="item.create.brass_ingot",
            locale="zh_cn"
        )
        
        print(f"✓ 翻译条目UIDA生成成功")
        print(f"  keys_b64: {uida_components.keys_b64[:32]}...")
        print(f"  hash_hex: {uida_components.hash_hex[:32]}...")
        print(f"  hash长度: {len(uida_components.hash_hex)} 字符")
        
        # 验证是否是BLAKE3哈希（32字节 = 64字符）
        if len(uida_components.hash_hex) == 64:
            print("✓ 哈希长度正确 (BLAKE3)")
        else:
            print(f"✗ 哈希长度错误: 期望64字符，实际{len(uida_components.hash_hex)}字符")
        
        return True
        
    except Exception as e:
        print(f"✗ UIDA服务基本功能测试失败: {e}")
        logger.error("UIDA服务测试异常", error=str(e))
        return False


def test_language_file_uida():
    """测试语言文件UIDA生成"""
    print("\n=== 测试语言文件UIDA生成 ===")
    
    try:
        uida_service = get_uida_service()
        
        # 测试MOD语言文件
        uida_components = uida_service.generate_language_file_uida(
            carrier_type="mod",
            carrier_uid="create_mod_v1.2.3",
            locale="zh_cn",
            file_path="assets/create/lang/zh_cn.json"
        )
        
        print(f"✓ MOD语言文件UIDA生成成功")
        print(f"  keys_b64: {uida_components.keys_b64[:32]}...")
        print(f"  hash_hex: {uida_components.hash_hex[:32]}...")
        
        # 测试资源包语言文件
        rp_uida = uida_service.generate_language_file_uida(
            carrier_type="resource_pack",
            carrier_uid="faithful_32x",
            locale="zh_cn"
        )
        
        print(f"✓ 资源包语言文件UIDA生成成功")
        print(f"  keys_b64: {rp_uida.keys_b64[:32]}...")
        
        # 验证不同参数产生不同UIDA
        if uida_components.hash_hex != rp_uida.hash_hex:
            print("✓ 不同参数产生不同UIDA")
        else:
            print("✗ 不同参数产生相同UIDA")
        
        return True
        
    except Exception as e:
        print(f"✗ 语言文件UIDA生成测试失败: {e}")
        return False


def test_namespace_validation():
    """测试命名空间验证"""
    print("\n=== 测试命名空间验证 ===")
    
    try:
        uida_service = get_uida_service()
        
        # 测试有效命名空间
        valid_namespaces = [
            MCUIDANamespace.MOD_ITEM,
            MCUIDANamespace.MOD_BLOCK,
            MCUIDANamespace.RESOURCEPACK_LANG
        ]
        
        for namespace in valid_namespaces:
            if uida_service.validate_namespace(namespace):
                print(f"✓ 命名空间验证通过: {namespace}")
            else:
                print(f"✗ 命名空间验证失败: {namespace}")
        
        # 测试无效命名空间
        invalid_namespace = "invalid.namespace"
        if not uida_service.validate_namespace(invalid_namespace):
            print(f"✓ 正确拒绝无效命名空间: {invalid_namespace}")
        else:
            print(f"✗ 错误接受无效命名空间: {invalid_namespace}")
        
        # 测试获取所有命名空间
        all_namespaces = uida_service.get_all_namespaces()
        print(f"✓ 获取所有命名空间: {len(all_namespaces)} 个")
        for ns in all_namespaces[:3]:  # 显示前3个
            print(f"  - {ns}")
        
        return True
        
    except Exception as e:
        print(f"✗ 命名空间验证测试失败: {e}")
        return False


def test_uida_consistency():
    """测试UIDA一致性"""
    print("\n=== 测试UIDA一致性 ===")
    
    try:
        uida_service = get_uida_service()
        
        # 多次生成相同参数的UIDA，应该产生相同结果
        test_params = {
            "mod_id": "create",
            "translation_key": "item.create.brass_ingot",
            "locale": "zh_cn"
        }
        
        uida_results = []
        for i in range(3):
            uida = uida_service.generate_translation_entry_uida(**test_params)
            uida_results.append(uida.hash_hex)
        
        # 验证一致性
        if len(set(uida_results)) == 1:
            print("✓ UIDA生成一致性验证通过")
            print(f"  重复生成结果: {uida_results[0][:32]}...")
        else:
            print("✗ UIDA生成一致性验证失败")
            print(f"  结果差异: {uida_results}")
        
        # 测试不同参数产生不同结果
        different_uida = uida_service.generate_translation_entry_uida(
            mod_id="thermal",  # 不同的mod_id
            translation_key="item.create.brass_ingot",
            locale="zh_cn"
        )
        
        if different_uida.hash_hex != uida_results[0]:
            print("✓ 不同参数产生不同UIDA")
        else:
            print("✗ 不同参数产生相同UIDA")
        
        return True
        
    except Exception as e:
        print(f"✗ UIDA一致性测试失败: {e}")
        return False


def test_blake3_integration():
    """测试BLAKE3集成"""
    print("\n=== 测试BLAKE3集成 ===")
    
    try:
        uida_service = get_uida_service()
        
        # 生成UIDA并验证BLAKE3特性
        uida = uida_service.generate_translation_entry_uida(
            mod_id="test",
            translation_key="test.key",
            locale="en_us"
        )
        
        # 验证哈希长度（BLAKE3产生32字节 = 64字符十六进制）
        if len(uida.hash_hex) == 64:
            print("✓ BLAKE3哈希长度正确 (32字节)")
        else:
            print(f"✗ 哈希长度错误: {len(uida.hash_hex)} != 64")
        
        # 验证keys_hash_bytes长度
        if len(uida.keys_hash_bytes) == 32:
            print("✓ BLAKE3字节哈希长度正确 (32字节)")
        else:
            print(f"✗ 字节哈希长度错误: {len(uida.keys_hash_bytes)} != 32")
        
        # 验证hex和bytes的一致性
        calculated_hex = uida.keys_hash_bytes.hex()
        if calculated_hex == uida.hash_hex:
            print("✓ 十六进制哈希与字节哈希一致")
        else:
            print("✗ 十六进制哈希与字节哈希不一致")
        
        print(f"  BLAKE3哈希示例: {uida.hash_hex[:32]}...")
        
        return True
        
    except Exception as e:
        print(f"✗ BLAKE3集成测试失败: {e}")
        return False


def run_all_tests():
    """运行所有UIDA集成测试"""
    print("🔧 开始UIDA集成测试")
    print("=" * 60)
    
    tests = [
        test_uida_service_basic,
        test_language_file_uida,
        test_namespace_validation,
        test_uida_consistency,
        test_blake3_integration,
    ]
    
    passed = 0
    total = len(tests)
    
    for test in tests:
        try:
            result = test()
            if result:
                passed += 1
        except Exception as e:
            logger.error(f"测试执行异常: {test.__name__}", error=str(e))
    
    print("=" * 60)
    print(f"🏁 UIDA集成测试完成: {passed}/{total} 通过")
    
    if passed == total:
        print("🎉 所有UIDA集成测试通过!")
        return True
    else:
        print(f"⚠️  有 {total - passed} 个测试失败")
        return False


if __name__ == "__main__":
    run_all_tests()