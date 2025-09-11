#!/usr/bin/env python3
"""
测试扫描功能修复是否生效
"""
import requests
import json
import time

def test_scan_functionality():
    """测试扫描功能"""
    base_url = "http://localhost:18000"
    
    print("=== 测试扫描功能修复 ===\n")
    
    # 1. 测试服务器状态
    try:
        response = requests.get(f"{base_url}/api/v1/scan/test")
        if response.status_code == 200:
            print("✅ 后端服务正常")
        else:
            print(f"❌ 后端服务异常: {response.status_code}")
            return
    except Exception as e:
        print(f"❌ 无法连接后端服务: {e}")
        return
    
    # 2. 测试数据库统计接口
    try:
        response = requests.get(f"{base_url}/api/v1/scan/stats")
        if response.status_code == 200:
            stats = response.json()
            if stats.get("success"):
                data = stats.get("data", {})
                print(f"✅ 数据库统计正常:")
                print(f"  - 总项目数: {data.get('totalProjects', 0)}")
                print(f"  - 语言文件数: {data.get('totalFiles', 0)}")
                print(f"  - 翻译条目数: {data.get('totalEntries', 0)}")
            else:
                print(f"❌ 数据库统计接口错误: {stats}")
        else:
            print(f"❌ 数据库统计接口HTTP错误: {response.status_code}")
    except Exception as e:
        print(f"❌ 测试数据库统计失败: {e}")
    
    # 3. 测试小规模扫描
    print(f"\n=== 测试小规模扫描 ===")
    try:
        scan_data = {
            "target_path": "/tmp/test_mods_with_data",
            "incremental": True
        }
        
        response = requests.post(f"{base_url}/api/v1/scan/start", json=scan_data)
        
        if response.status_code == 200:
            result = response.json()
            if result.get("success"):
                scan_id = result.get("scan_id")
                print(f"✅ 扫描启动成功: {scan_id}")
                
                # 等待扫描完成
                for i in range(10):
                    time.sleep(1)
                    status_response = requests.get(f"{base_url}/api/v1/scan/status/{scan_id}")
                    if status_response.status_code == 200:
                        status_data = status_response.json()
                        if status_data.get("success"):
                            status = status_data.get("status")
                            print(f"  扫描状态: {status}")
                            if status == "completed":
                                print("✅ 扫描完成！")
                                # 显示扫描结果
                                stats = status_data.get("stats", {})
                                print(f"  - 找到模组: {stats.get('mods', 0)}")
                                print(f"  - 语言文件: {stats.get('language_files', 0)}")  
                                print(f"  - 翻译条目: {stats.get('keys', 0)}")
                                break
                            elif status == "error":
                                error = status_data.get("error", "未知错误")
                                print(f"❌ 扫描失败: {error}")
                                break
                    else:
                        print(f"❌ 获取扫描状态失败: {status_response.status_code}")
                        break
            else:
                print(f"❌ 扫描启动失败: {result}")
        else:
            print(f"❌ 扫描请求HTTP错误: {response.status_code} - {response.text}")
    except Exception as e:
        print(f"❌ 测试扫描失败: {e}")

if __name__ == "__main__":
    test_scan_functionality()