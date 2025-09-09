#!/usr/bin/env python
"""
直接测试UIDA包
验证底层UIDA包的导入和使用
"""

import sys
import os

# 添加UIDA包路径
# 从 /home/saken/project/TH-Suite/apps/mc_l10n/backend/ 到 /home/saken/project/Trans-Hub/packages/uida/src
uida_package_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '../../../../../Trans-Hub/packages/uida/src'))
if os.path.exists(uida_package_path):
    sys.path.insert(0, uida_package_path)
    print(f"添加UIDA包路径: {uida_package_path}")
else:
    print(f"警告: UIDA包路径不存在: {uida_package_path}")
    # 尝试备选路径
    alt_paths = [
        '/home/saken/project/Trans-Hub/packages/uida/src',
        os.path.abspath(os.path.join(os.path.dirname(__file__), '../../packages/uida/src'))
    ]
    for alt_path in alt_paths:
        if os.path.exists(alt_path):
            sys.path.insert(0, alt_path)
            print(f"使用备选路径: {alt_path}")
            break
    else:
        print("所有UIDA包路径都不存在")

try:
    from trans_hub_uida import generate_uida, UIDAComponents, CanonicalizationError
    print("✓ 成功导入UIDA包")
    
    # 测试基本功能
    test_keys = {
        "namespace": "mc.mod.item",
        "mod_id": "create",
        "item_id": "brass_ingot",
        "locale": "zh_cn"
    }
    
    uida_components = generate_uida(test_keys)
    print("✓ 成功生成UIDA")
    print(f"类型: {type(uida_components)}")
    print(f"属性: {dir(uida_components)}")
    print(f"keys_b64: {uida_components.keys_b64[:32]}...")
    
    # 检查keys_hash_bytes属性
    if hasattr(uida_components, 'keys_hash_bytes'):
        print(f"✓ keys_hash_bytes存在: {len(uida_components.keys_hash_bytes)} 字节")
        print(f"hash_hex: {uida_components.keys_hash_bytes.hex()[:32]}...")
    else:
        print("✗ keys_hash_bytes属性不存在")
        print(f"可用属性: {[attr for attr in dir(uida_components) if not attr.startswith('_')]}")
    
except ImportError as e:
    print(f"✗ 导入失败: {e}")
except Exception as e:
    print(f"✗ 测试失败: {e}")