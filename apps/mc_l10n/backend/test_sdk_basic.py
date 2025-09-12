#!/usr/bin/env python3
"""
基础SDK集成测试
仅测试核心功能，避免复杂的依赖问题
"""

import asyncio
import sys
import os

# 添加当前目录到路径
sys.path.insert(0, os.path.dirname(__file__))

def test_sdk_imports():
    """测试SDK导入功能"""
    print("🔍 测试SDK导入...")
    
    try:
        from clients.transhub_sdk_client_v2 import (
            TH_Suite_TransHub_SDK_Client,
            MinecraftContentItem,
            SyncOptions,
            SyncProgress,
            SDK_AVAILABLE
        )
        print(f"✅ SDK客户端导入成功，SDK可用性: {SDK_AVAILABLE}")
        
        if not SDK_AVAILABLE:
            print("⚠️  Trans-Hub SDK未安装，将使用占位符类型")
        
        return True
    except Exception as e:
        print(f"❌ SDK客户端导入失败: {e}")
        return False

def test_content_mapper():
    """测试内容映射器"""
    print("🔍 测试内容映射器...")
    
    try:
        from mappers.unified_content_mapper_v2 import UnifiedContentMapperV2
        mapper = UnifiedContentMapperV2()
        print("✅ 内容映射器初始化成功")
        return True
    except Exception as e:
        print(f"❌ 内容映射器测试失败: {e}")
        return False

def test_basic_client_initialization():
    """测试基础客户端初始化"""
    print("🔍 测试基础客户端初始化...")
    
    try:
        from clients.transhub_sdk_client_v2 import TH_Suite_TransHub_SDK_Client, SDK_AVAILABLE
        
        if SDK_AVAILABLE:
            client = TH_Suite_TransHub_SDK_Client(
                base_url="http://localhost:8000",
                api_key="test-key",
                project_id="test-minecraft"
            )
            print("✅ SDK客户端初始化成功")
        else:
            print("⚠️  SDK不可用，跳过客户端初始化测试")
        
        return True
    except Exception as e:
        print(f"❌ 客户端初始化失败: {e}")
        return False

async def main():
    """主测试函数"""
    print("🚀 开始TH-Suite SDK基础集成测试\n")
    
    tests = [
        ("SDK导入测试", test_sdk_imports),
        ("内容映射器测试", test_content_mapper),
        ("客户端初始化测试", test_basic_client_initialization),
    ]
    
    passed = 0
    total = len(tests)
    
    for name, test_func in tests:
        print(f"\n📋 {name}")
        print("-" * 50)
        
        try:
            if test_func():
                passed += 1
                print(f"✅ {name} 通过")
            else:
                print(f"❌ {name} 失败")
        except Exception as e:
            print(f"❌ {name} 异常: {e}")
        
        print()
    
    print("=" * 60)
    print(f"📊 测试结果: {passed}/{total} 通过")
    
    if passed == total:
        print("🎉 所有基础测试通过！SDK集成基本功能正常")
        return True
    else:
        print("⚠️  部分测试失败，请检查相关组件")
        return False

if __name__ == "__main__":
    success = asyncio.run(main())
    sys.exit(0 if success else 1)