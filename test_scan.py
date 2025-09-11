#!/usr/bin/env python3
"""
测试扫描功能的脚本
"""
import requests
import json
import time

BASE_URL = "http://localhost:18000"

def test_scan_directory():
    """测试扫描DeceasedCraft目录"""
    directory = "/mnt/d/Games/Curseforge/Minecraft/Instances/DeceasedCraft - Modern Zombie Apocalypse"
    
    # 1. 测试连接
    print("🔌 测试API连接...")
    try:
        response = requests.get(f"{BASE_URL}/health", timeout=5)
        print(f"✅ 连接成功: {response.status_code}")
    except Exception as e:
        print(f"❌ 连接失败: {e}")
        return

    # 2. 启动扫描
    print(f"\n📂 开始扫描目录: {directory}")
    scan_request = {
        "directory": directory,
        "deep_scan": True,
        "extract_assets": True,
        "merge_duplicates": True
    }
    
    try:
        response = requests.post(
            f"{BASE_URL}/api/v1/scan/start",
            json=scan_request,
            timeout=30
        )
        print(f"扫描请求状态: {response.status_code}")
        
        if response.status_code == 200:
            try:
                result = response.json()
                print(f"✅ 扫描启动成功!")
                print(f"扫描ID: {result.get('scan_id', 'N/A')}")
                print(f"状态: {result.get('status', 'N/A')}")
                
                scan_id = result.get('scan_id')
                if scan_id:
                    # 3. 监控扫描进度
                    print("\n⏳ 监控扫描进度...")
                    monitor_scan_progress(scan_id)
                    
            except json.JSONDecodeError as e:
                print(f"⚠️ 响应解析错误: {e}")
                print(f"原始响应: {response.text[:500]}")
        else:
            print(f"❌ 扫描启动失败: {response.status_code}")
            print(f"错误信息: {response.text}")
            
    except Exception as e:
        print(f"❌ 扫描请求异常: {e}")

def monitor_scan_progress(scan_id):
    """监控扫描进度"""
    for i in range(30):  # 最多监控30次，每次2秒
        try:
            response = requests.get(
                f"{BASE_URL}/api/v1/scan/{scan_id}/status",
                timeout=5
            )
            
            if response.status_code == 200:
                try:
                    status = response.json()
                    print(f"进度 {i+1}/30: {status.get('status', 'unknown')} - {status.get('progress', 0):.1f}%")
                    
                    if status.get('status') == 'completed':
                        print("✅ 扫描完成!")
                        # 获取扫描结果
                        get_scan_results(scan_id)
                        break
                    elif status.get('status') == 'failed':
                        print(f"❌ 扫描失败: {status.get('error', 'Unknown error')}")
                        break
                        
                except json.JSONDecodeError:
                    print(f"进度查询响应解析失败: {response.text[:200]}")
            else:
                print(f"进度查询失败: {response.status_code}")
                
        except Exception as e:
            print(f"进度查询异常: {e}")
            
        time.sleep(2)

def get_scan_results(scan_id):
    """获取扫描结果"""
    try:
        response = requests.get(
            f"{BASE_URL}/api/v1/scan/{scan_id}/results",
            timeout=10
        )
        
        if response.status_code == 200:
            try:
                results = response.json()
                print(f"\n📊 扫描结果摘要:")
                print(f"找到的包数量: {results.get('total_packs', 0)}")
                print(f"找到的模组数量: {results.get('total_mods', 0)}")
                print(f"语言文件数量: {results.get('total_lang_files', 0)}")
                print(f"翻译条目数量: {results.get('total_entries', 0)}")
                
                # 显示详细信息
                packs = results.get('packs', [])
                if packs:
                    print(f"\n📦 找到的包:")
                    for pack in packs[:5]:  # 只显示前5个
                        print(f"  - {pack.get('name', 'Unknown')} ({pack.get('type', 'unknown')})")
                
                mods = results.get('mods', [])
                if mods:
                    print(f"\n🔧 找到的模组:")
                    for mod in mods[:5]:  # 只显示前5个
                        print(f"  - {mod.get('name', 'Unknown')} v{mod.get('version', 'unknown')}")
                        
            except json.JSONDecodeError as e:
                print(f"结果解析错误: {e}")
                print(f"原始响应: {response.text[:500]}")
        else:
            print(f"❌ 获取结果失败: {response.status_code}")
            print(f"错误: {response.text}")
            
    except Exception as e:
        print(f"获取结果异常: {e}")

if __name__ == "__main__":
    print("🚀 MC L10n 扫描测试")
    print("=" * 50)
    test_scan_directory()