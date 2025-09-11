#!/usr/bin/env python
"""
缓存功能测试脚本
测试新实现的智能缓存功能
"""

import asyncio
import time
import json
from pathlib import Path

from application.services.scan_application_service import ScanApplicationService


async def test_cache_functionality():
    """测试缓存功能"""
    print("🚀 开始测试缓存功能...")
    
    # 初始化扫描服务
    scan_service = ScanApplicationService()
    
    # 测试目录路径（使用一个小的测试目录）
    test_directory = "/tmp/test_mods_with_data"
    
    print(f"\n📁 测试目录: {test_directory}")
    
    # 第一次扫描 - 应该执行实际扫描
    print("\n🔍 执行第一次扫描（无缓存）...")
    start_time = time.time()
    
    result1 = await scan_service.start_project_scan(
        directory=test_directory,
        incremental=True,
        use_cache=True
    )
    
    scan_time1 = time.time() - start_time
    
    print(f"第一次扫描结果: {json.dumps(result1, indent=2, ensure_ascii=False)}")
    print(f"第一次扫描耗时: {scan_time1:.2f}秒")
    
    # 等待一小段时间模拟用户操作
    await asyncio.sleep(2)
    
    # 第二次扫描 - 应该使用缓存
    print("\n⚡ 执行第二次扫描（预期缓存命中）...")
    start_time = time.time()
    
    result2 = await scan_service.start_project_scan(
        directory=test_directory,
        incremental=True,
        use_cache=True
    )
    
    scan_time2 = time.time() - start_time
    
    print(f"第二次扫描结果: {json.dumps(result2, indent=2, ensure_ascii=False)}")
    print(f"第二次扫描耗时: {scan_time2:.2f}秒")
    
    # 分析结果
    print("\n📊 缓存性能分析:")
    
    cache_hit1 = result1.get("cache_hit", False)
    cache_hit2 = result2.get("cache_hit", False)
    
    print(f"第一次扫描缓存命中: {'是' if cache_hit1 else '否'}")
    print(f"第二次扫描缓存命中: {'是' if cache_hit2 else '否'}")
    
    if not cache_hit1 and cache_hit2:
        speedup = scan_time1 / scan_time2 if scan_time2 > 0 else 0
        print(f"性能提升: {speedup:.1f}x 倍")
        print(f"时间节省: {scan_time1 - scan_time2:.2f}秒 ({((scan_time1 - scan_time2) / scan_time1 * 100):.1f}%)")
        print("✅ 缓存功能正常工作!")
    elif cache_hit1:
        print("⚠️  第一次扫描就命中缓存，可能已有缓存数据")
    elif not cache_hit2:
        print("❌ 第二次扫描未命中缓存，缓存功能可能有问题")
    
    # 测试缓存统计
    print("\n📈 获取缓存统计信息...")
    stats_result = await scan_service.get_cache_statistics()
    
    if stats_result.get("success"):
        stats_data = stats_result.get("data", {})
        print(f"缓存条目总数: {stats_data.get('total_entries', 0)}")
        print(f"有效缓存条目: {stats_data.get('valid_entries', 0)}")
        print(f"已过期条目: {stats_data.get('expired_entries', 0)}")
        print(f"缓存总大小: {stats_data.get('total_size_mb', 0):.2f} MB")
        print(f"平均条目大小: {stats_data.get('avg_size_bytes', 0):.0f} 字节")
    else:
        print(f"获取缓存统计失败: {stats_result.get('message', '未知错误')}")
    
    # 测试缓存清理
    print("\n🧹 测试缓存清理...")
    clear_result = await scan_service.clear_cache(test_directory)
    
    if clear_result.get("success"):
        print(f"✅ 缓存清理成功: {clear_result.get('message', '')}")
    else:
        print(f"❌ 缓存清理失败: {clear_result.get('message', '未知错误')}")


if __name__ == "__main__":
    asyncio.run(test_cache_functionality())