#!/usr/bin/env python3
"""测试新的MOD解析逻辑"""

import sys
import os
from pathlib import Path

# 添加项目根目录到Python路径
project_root = Path(__file__).parent.parent
sys.path.append(str(project_root))

from core.ddd_scanner_simple import DDDScanner

def test_filename_parsing():
    """测试文件名解析"""
    scanner = DDDScanner(":memory:")  # 使用内存数据库进行测试
    
    test_cases = [
        # (输入文件名, 期望的clean_name, 期望的version)
        ("AI-Improvements-1.18.2-0.5.2", "AI-Improvements", "1.18.2-0.5.2"),
        ("jei-1.19.2-11.5.0.297", "jei", "1.19.2-11.5.0.297"),
        ("betterend_1.18.2", "betterend", "1.18.2"),
        ("iron-chests-1.19.2-14.4.4", "iron-chests", "1.19.2-14.4.4"),
        ("create-1.18.2-0.5.1.f", "create", "1.18.2-0.5.1.f"),
        ("simple-mod", "simple-mod", ""),  # 无版本号
        ("mod-name-v2.0", "mod-name", "v2.0"),
    ]
    
    print("🧪 测试文件名解析逻辑...")
    print("=" * 80)
    
    all_passed = True
    for filename, expected_name, expected_version in test_cases:
        clean_name, extracted_version = scanner._parse_filename_intelligently(filename)
        
        name_ok = clean_name == expected_name
        version_ok = extracted_version == expected_version
        
        status = "✅" if (name_ok and version_ok) else "❌"
        print(f"{status} {filename}")
        print(f"    期望: 名称='{expected_name}', 版本='{expected_version}'")
        print(f"    实际: 名称='{clean_name}', 版本='{extracted_version}'")
        
        if not (name_ok and version_ok):
            all_passed = False
            print(f"    🚨 解析失败!")
        print()
    
    print(f"📊 测试结果: {'全部通过' if all_passed else '有失败项'}")
    return all_passed

def test_template_variables():
    """测试模板变量解析"""
    scanner = DDDScanner(":memory:")
    
    test_cases = [
        # (模板字符串, 文件路径, 期望结果)
        ("${version}", "/path/to/mod-1.18.2-0.5.2.jar", "1.18.2-0.5.2"),
        ("${file.jarVersion}", "/path/to/jei-1.19.2-11.5.0.297.jar", "1.19.2-11.5.0.297"),
        ("v${mc_version}", "/path/to/create-1.18.2-0.5.1.jar", "v1.18.2"),
        ("1.0.0", "/any/path.jar", "1.0.0"),  # 无模板变量
        ("${version}-SNAPSHOT", "/path/to/test-2.1.0.jar", "2.1.0-SNAPSHOT"),
    ]
    
    print("🧪 测试模板变量解析...")
    print("=" * 80)
    
    all_passed = True
    for template, file_path, expected in test_cases:
        result = scanner._resolve_template_variables(template, file_path)
        
        passed = result == expected
        status = "✅" if passed else "❌"
        
        print(f"{status} 模板: '{template}' | 文件: {Path(file_path).name}")
        print(f"    期望: '{expected}'")
        print(f"    实际: '{result}'")
        
        if not passed:
            all_passed = False
            print(f"    🚨 解析失败!")
        print()
    
    print(f"📊 测试结果: {'全部通过' if all_passed else '有失败项'}")
    return all_passed

if __name__ == "__main__":
    print("🔍 测试MOD解析修复...")
    print("=" * 80)
    
    test1_passed = test_filename_parsing()
    print()
    test2_passed = test_template_variables()
    
    print("\n" + "=" * 80)
    if test1_passed and test2_passed:
        print("🎉 所有测试通过！MOD解析修复成功")
    else:
        print("🚨 有测试失败，需要进一步调试")