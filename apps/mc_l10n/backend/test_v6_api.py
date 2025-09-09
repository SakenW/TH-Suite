#!/usr/bin/env python3
"""
V6 API测试脚本
简单验证V6 API端点是否正常工作
"""

import sys
import os
import subprocess
import time
import requests
import json
from typing import Dict, Any

def test_v6_endpoints():
    """测试V6 API端点"""
    base_url = "http://localhost:18000"
    
    test_endpoints = [
        # V6 API基础端点
        ("/api/v6/", "V6 API信息"),
        ("/api/v6/health", "V6健康检查"),
        
        # 数据库统计端点
        ("/api/v6/database/health", "数据库健康检查"),
        ("/api/v6/database/info", "数据库基础信息"),
        
        # 实体管理端点
        ("/api/v6/packs", "Pack列表"),
        ("/api/v6/mods", "MOD列表"),
        ("/api/v6/language-files", "语言文件列表"),
        ("/api/v6/translations", "翻译条目列表"),
        
        # 管理端点
        ("/api/v6/queue/status", "队列状态"),
        ("/api/v6/cache/status", "缓存状态"),
        ("/api/v6/settings", "配置列表"),
    ]
    
    results = []
    
    print("🚀 开始测试V6 API端点...")
    print("=" * 50)
    
    for endpoint, description in test_endpoints:
        url = f"{base_url}{endpoint}"
        try:
            response = requests.get(url, timeout=5)
            
            if response.status_code == 200:
                status = "✅ 成功"
                try:
                    data = response.json()
                    details = f"返回数据: {list(data.keys()) if isinstance(data, dict) else str(type(data))}"
                except:
                    details = f"响应长度: {len(response.text)} 字符"
            else:
                status = f"❌ HTTP {response.status_code}"
                details = response.text[:100] + "..." if len(response.text) > 100 else response.text
                
            results.append({
                "endpoint": endpoint,
                "description": description,
                "status_code": response.status_code,
                "success": response.status_code == 200,
                "details": details
            })
            
        except requests.exceptions.ConnectionError:
            status = "🔌 连接失败"
            details = "服务器未启动或端口不可用"
            results.append({
                "endpoint": endpoint,
                "description": description,
                "status_code": None,
                "success": False,
                "details": details
            })
            
        except requests.exceptions.Timeout:
            status = "⏰ 超时"
            details = "请求超时（5秒）"
            results.append({
                "endpoint": endpoint,
                "description": description,
                "status_code": None,
                "success": False,
                "details": details
            })
            
        except Exception as e:
            status = f"❌ 错误"
            details = str(e)
            results.append({
                "endpoint": endpoint,
                "description": description,
                "status_code": None,
                "success": False,
                "details": details
            })
        
        print(f"{status} {endpoint} - {description}")
        if not results[-1]["success"]:
            print(f"    详情: {details}")
    
    print("=" * 50)
    
    # 统计结果
    total = len(results)
    success_count = sum(1 for r in results if r["success"])
    failure_count = total - success_count
    
    print(f"📊 测试结果统计:")
    print(f"   总计: {total} 个端点")
    print(f"   成功: {success_count} 个 ({success_count/total*100:.1f}%)")
    print(f"   失败: {failure_count} 个 ({failure_count/total*100:.1f}%)")
    
    if failure_count > 0:
        print("\n❌ 失败的端点:")
        for result in results:
            if not result["success"]:
                print(f"   {result['endpoint']} - {result['details']}")
    
    return success_count == total


def check_server_status():
    """检查服务器是否正在运行"""
    try:
        response = requests.get("http://localhost:18000/health", timeout=2)
        return response.status_code == 200
    except:
        return False


def main():
    """主函数"""
    print("🔍 MC L10n V6 API 测试工具")
    print("=" * 50)
    
    # 检查服务器状态
    if not check_server_status():
        print("❌ 服务器未启动或不可用")
        print("💡 请先启动MC L10n后端服务:")
        print("   cd /home/saken/project/TH-Suite")
        print("   poetry run python apps/mc_l10n/backend/main.py")
        print()
        return False
    
    print("✅ 服务器正在运行")
    print()
    
    # 运行API测试
    success = test_v6_endpoints()
    
    if success:
        print("\n🎉 所有V6 API端点测试通过！")
        return True
    else:
        print("\n⚠️  部分V6 API端点测试失败")
        return False


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)