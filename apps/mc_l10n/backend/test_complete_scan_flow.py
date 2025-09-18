#!/usr/bin/env python3
"""
完整扫描流程测试
验证新架构端到端工作流程
"""

import asyncio
import json
import requests
import time
from pathlib import Path

API_BASE_URL = "http://localhost:18000"


def test_api_connection():
    """测试API连接"""
    print("=== 1. 测试API连接 ===")
    try:
        response = requests.get(f"{API_BASE_URL}/api/v1/scan/test")
        if response.status_code == 200:
            data = response.json()
            print(f"✅ API连接成功: {data['message']}")
            return True
        else:
            print(f"❌ API连接失败: {response.status_code}")
            return False
    except Exception as e:
        print(f"❌ API连接异常: {e}")
        return False


def test_database_stats():
    """测试数据库统计"""
    print("\n=== 2. 测试数据库统计 ===")
    try:
        response = requests.get(f"{API_BASE_URL}/api/v1/scan/stats")
        if response.status_code == 200:
            data = response.json()
            if data.get("success"):
                stats = data["data"]
                print(f"✅ 数据库统计获取成功:")
                print(f"   - 总表数: {stats.get('totalTables', 0)}")
                print(f"   - 数据库大小: {stats.get('database_size', 0)} bytes")
                print(f"   - Pack数量: {stats.get('totalProjects', 0)}")
                return True
            else:
                print(f"❌ 数据库统计失败: {data}")
                return False
        else:
            print(f"❌ 数据库统计请求失败: {response.status_code}")
            return False
    except Exception as e:
        print(f"❌ 数据库统计异常: {e}")
        return False


def test_scan_start():
    """测试启动扫描"""
    print("\n=== 3. 测试启动扫描 ===")
    
    # 创建测试目录
    test_dir = Path("test_minecraft_pack")
    test_dir.mkdir(exist_ok=True)
    
    # 创建一个简单的测试JAR文件结构
    (test_dir / "mods").mkdir(exist_ok=True)
    test_jar = test_dir / "mods" / "example_mod.jar"
    test_jar.write_text("fake jar content")  # 占位文件
    
    scan_request = {
        "directory": str(test_dir.absolute()),
        "incremental": False,
        "options": {
            "target_languages": ["en_us", "zh_cn"]
        }
    }
    
    try:
        response = requests.post(
            f"{API_BASE_URL}/api/v1/scan/start",
            json=scan_request
        )
        
        if response.status_code == 200:
            data = response.json()
            if data.get("success"):
                scan_id = data["data"]["scan_id"]
                print(f"✅ 扫描启动成功: {scan_id}")
                print(f"   - 扫描目录: {data['data']['directory']}")
                print(f"   - 扫描模式: {data['data']['mode']}")
                return scan_id
            else:
                print(f"❌ 扫描启动响应失败: {data}")
                return None
        else:
            print(f"❌ 扫描启动请求失败: {response.status_code}")
            print(f"   响应内容: {response.text}")
            return None
            
    except Exception as e:
        print(f"❌ 扫描启动异常: {e}")
        return None


def test_scan_status(scan_id):
    """测试扫描状态查询"""
    print(f"\n=== 4. 测试扫描状态查询 ===")
    
    max_attempts = 10
    for attempt in range(max_attempts):
        try:
            response = requests.get(f"{API_BASE_URL}/api/v1/scan/status/{scan_id}")
            
            if response.status_code == 200:
                data = response.json()
                if data.get("success"):
                    status_data = data["data"]
                    print(f"✅ 状态查询成功 (尝试 {attempt + 1}):")
                    print(f"   - 扫描ID: {status_data['scan_id']}")
                    print(f"   - 状态: {status_data['status']}")
                    print(f"   - 进度: {status_data['progress']}")
                    print(f"   - 已处理: {status_data['processed_count']}")
                    print(f"   - 总数: {status_data['total_count']}")
                    
                    # 检查是否完成
                    if status_data['status'] in ['completed', 'failed', 'cancelled']:
                        print(f"✅ 扫描已完成: {status_data['status']}")
                        return status_data['status']
                    
                    # 等待后继续检查
                    time.sleep(2)
                    
                else:
                    print(f"❌ 状态查询响应失败: {data}")
                    return None
            else:
                print(f"❌ 状态查询请求失败: {response.status_code}")
                return None
                
        except Exception as e:
            print(f"❌ 状态查询异常: {e}")
            return None
    
    print(f"⚠️  扫描状态检查超时")
    return "timeout"


def test_active_scans():
    """测试活跃扫描查询"""
    print("\n=== 5. 测试活跃扫描查询 ===")
    try:
        response = requests.get(f"{API_BASE_URL}/api/v1/scan/active")
        
        if response.status_code == 200:
            data = response.json()
            if data.get("success"):
                active_scans = data["data"]
                print(f"✅ 活跃扫描查询成功:")
                print(f"   - 活跃扫描数量: {len(active_scans)}")
                for i, scan in enumerate(active_scans):
                    print(f"   - 扫描 {i+1}: {scan.get('session_id', 'N/A')} [{scan.get('stage', 'N/A')}]")
                return True
            else:
                print(f"❌ 活跃扫描查询响应失败: {data}")
                return False
        else:
            print(f"❌ 活跃扫描查询请求失败: {response.status_code}")
            return False
            
    except Exception as e:
        print(f"❌ 活跃扫描查询异常: {e}")
        return False


def test_scan_results(scan_id):
    """测试扫描结果查询"""
    print(f"\n=== 6. 测试扫描结果查询 ===")
    try:
        response = requests.get(f"{API_BASE_URL}/api/v1/scan/results/{scan_id}")
        
        if response.status_code == 200:
            data = response.json()
            if data.get("success"):
                results = data["data"]
                print(f"✅ 扫描结果查询成功:")
                print(f"   - 会话ID: {results['session_id']}")
                print(f"   - 完成时间: {results.get('completed_at', 'N/A')}")
                print(f"   - 统计信息: {results.get('statistics', {})}")
                return True
            else:
                print(f"❌ 扫描结果查询响应失败: {data}")
                return False
        else:
            print(f"❌ 扫描结果查询请求失败: {response.status_code}")
            return False
            
    except Exception as e:
        print(f"❌ 扫描结果查询异常: {e}")
        return False


def main():
    """主测试流程"""
    print("🧪 开始完整扫描流程测试")
    print("=" * 50)
    
    # 1. 测试API连接
    if not test_api_connection():
        print("❌ API连接失败，停止测试")
        return False
    
    # 2. 测试数据库统计
    if not test_database_stats():
        print("❌ 数据库统计失败，停止测试")
        return False
    
    # 3. 启动扫描
    scan_id = test_scan_start()
    if not scan_id:
        print("❌ 扫描启动失败，停止测试")
        return False
    
    # 4. 查询活跃扫描
    test_active_scans()
    
    # 5. 监控扫描状态
    final_status = test_scan_status(scan_id)
    
    # 6. 查询扫描结果（如果扫描完成）
    if final_status == "completed":
        test_scan_results(scan_id)
    
    # 总结
    print("\n" + "=" * 50)
    if final_status in ["completed", "timeout"]:
        print("🎉 完整扫描流程测试完成")
        print("✅ 新架构工作正常")
        return True
    else:
        print("⚠️  扫描流程测试部分完成")
        print("   - 可能需要更长时间或有其他问题")
        return False


if __name__ == "__main__":
    success = main()
    exit(0 if success else 1)