#!/usr/bin/env python3
"""
最终系统完整性测试 - 端到端验证
"""

import asyncio
import requests
import json
import sys
import sqlite3
from pathlib import Path

# 添加路径
sys.path.insert(0, '/home/saken/project/TH-Suite/apps/mc_l10n/backend')

def test_api_connectivity():
    """测试API连接性"""
    print("🌐 测试API连接性...")
    
    try:
        # 测试健康检查端点
        response = requests.get("http://localhost:18000/api/v2.1/scan/test", timeout=5)
        if response.status_code == 200:
            print("✅ API健康检查正常")
            return True
        else:
            print(f"❌ API健康检查失败，状态码: {response.status_code}")
            return False
    except requests.exceptions.RequestException as e:
        print(f"❌ API连接失败: {e}")
        return False

def test_database_integrity():
    """测试数据库完整性"""
    print("\n📊 测试数据库完整性...")
    
    db_path = Path("data/mc_l10n_v2_1.db")
    if not db_path.exists():
        print("❌ 数据库文件不存在")
        return False
    
    conn = sqlite3.connect(str(db_path))
    try:
        cursor = conn.cursor()
        
        # 检查关键表
        tables = ['packs', 'pack_versions', 'mod_version_instances', 'content_instances', 'pack_mod_relations', 'pack_content_relations']
        for table in tables:
            cursor.execute(f"SELECT COUNT(*) FROM {table}")
            count = cursor.fetchone()[0]
            print(f"  📋 {table}: {count} 条记录")
        
        # 检查翻译内容
        cursor.execute("SELECT COUNT(*) FROM content_instances")
        content_count = cursor.fetchone()[0]
        
        cursor.execute("SELECT COUNT(DISTINCT language_code) FROM content_instances")
        language_count = cursor.fetchone()[0]
        
        cursor.execute("SELECT COUNT(DISTINCT content_source) FROM content_instances")
        mod_count = cursor.fetchone()[0]
        
        print(f"\n🎯 核心指标:")
        print(f"  - 翻译内容: {content_count} 条")
        print(f"  - 支持语言: {language_count} 种") 
        print(f"  - MOD数量: {mod_count} 个")
        
        if content_count > 1000 and language_count > 10 and mod_count > 50:
            print("✅ 数据库完整性验证通过")
            return True
        else:
            print("❌ 数据库数据不足")
            return False
            
    except Exception as e:
        print(f"❌ 数据库检查失败: {e}")
        return False
    finally:
        conn.close()

def test_scan_api_functionality():
    """测试扫描API功能"""
    print("\n🔍 测试扫描API功能...")
    
    try:
        # 测试获取活跃扫描
        response = requests.get("http://localhost:18000/api/v2.1/scan/active", timeout=5)
        if response.status_code == 200:
            result = response.json()
            print(f"✅ 活跃扫描API正常: {result}")
        else:
            print(f"❌ 活跃扫描API异常，状态码: {response.status_code}")
            return False
        
        # 测试开始扫描API（模拟）
        scan_data = {
            "directory": "/tmp",
            "incremental": False,
            "options": {"include_subdirectories": True}
        }
        
        response = requests.post(
            "http://localhost:18000/api/v2.1/scan/start",
            json=scan_data,
            timeout=10
        )
        
        if response.status_code == 200:
            result = response.json()
            if result.get("success"):
                print(f"✅ 扫描API正常启动: {result.get('message', 'N/A')}")
                return True
            else:
                print(f"❌ 扫描API返回失败: {result.get('message', 'N/A')}")
                return False
        else:
            print(f"❌ 扫描API异常，状态码: {response.status_code}")
            return False
            
    except requests.exceptions.RequestException as e:
        print(f"❌ API请求失败: {e}")
        return False

def test_translation_storage_functionality():
    """测试翻译存储功能"""
    print("\n💾 测试翻译存储功能...")
    
    try:
        from infrastructure.services.simple_minecraft_scanner import get_simple_minecraft_scanner_service
        
        service = get_simple_minecraft_scanner_service()
        print("✅ 扫描服务实例化成功")
        
        # 验证数据库路径
        print(f"📁 数据库路径: {service.db_path}")
        
        # 检查数据库连接
        import sqlite3
        conn = sqlite3.connect(str(service.db_path))
        cursor = conn.cursor()
        
        # 检查是否有真实的翻译数据
        cursor.execute("""
            SELECT content_source, language_code, COUNT(*) as count
            FROM content_instances 
            GROUP BY content_source, language_code
            ORDER BY count DESC
            LIMIT 5
        """)
        top_translations = cursor.fetchall()
        
        print("🏆 翻译数据示例:")
        for source, lang, count in top_translations:
            print(f"  - {source} ({lang}): {count} 条翻译")
        
        conn.close()
        
        if top_translations and len(top_translations) > 0:
            print("✅ 翻译存储功能正常")
            return True
        else:
            print("❌ 翻译存储功能异常")
            return False
            
    except Exception as e:
        print(f"❌ 翻译存储测试失败: {e}")
        return False

def check_frontend_accessibility():
    """检查前端可访问性"""
    print("\n🌍 检查前端可访问性...")
    
    try:
        response = requests.get("http://localhost:18001", timeout=5)
        if response.status_code == 200:
            print("✅ 前端服务可访问")
            print(f"   响应大小: {len(response.content)} 字节")
            return True
        else:
            print(f"❌ 前端服务异常，状态码: {response.status_code}")
            return False
    except requests.exceptions.RequestException as e:
        print(f"❌ 前端连接失败: {e}")
        return False

def run_final_system_test():
    """运行最终系统测试"""
    print("🚀 开始最终系统完整性测试\n")
    
    tests = [
        ("API连接性", test_api_connectivity),
        ("数据库完整性", test_database_integrity), 
        ("扫描API功能", test_scan_api_functionality),
        ("翻译存储功能", test_translation_storage_functionality),
        ("前端可访问性", check_frontend_accessibility)
    ]
    
    passed_tests = 0
    total_tests = len(tests)
    
    for test_name, test_func in tests:
        print(f"{'='*50}")
        print(f"🧪 执行测试: {test_name}")
        print(f"{'='*50}")
        
        try:
            if test_func():
                passed_tests += 1
                print(f"✅ {test_name} - 通过")
            else:
                print(f"❌ {test_name} - 失败")
        except Exception as e:
            print(f"❌ {test_name} - 异常: {e}")
        
        print()  # 空行分隔
    
    print(f"{'='*60}")
    print(f"🎯 测试结果总结")
    print(f"{'='*60}")
    print(f"总测试数: {total_tests}")
    print(f"通过测试: {passed_tests}")
    print(f"失败测试: {total_tests - passed_tests}")
    print(f"通过率: {passed_tests/total_tests*100:.1f}%")
    
    if passed_tests == total_tests:
        print("\n🎉 所有测试通过！系统完全正常运行！")
        return True
    else:
        print(f"\n❌ {total_tests - passed_tests} 个测试失败，需要进一步修复")
        return False

if __name__ == "__main__":
    success = run_final_system_test()
    exit(0 if success else 1)