#!/usr/bin/env python3
"""
测试扫描功能
验证数据能正确保存到数据库
"""

import asyncio
import sys
from pathlib import Path

# 添加父目录到路径
sys.path.insert(0, str(Path(__file__).parent.parent / "backend"))

from ddd_scanner import DDDScanner
from unified_database import UnifiedDatabase


async def test_scan():
    """测试扫描功能"""
    print("=" * 60)
    print("MC L10n 扫描功能测试")
    print("=" * 60)

    # 数据库路径
    db_path = Path(__file__).parent.parent / "backend" / "mc_l10n.db"

    # 测试目录（使用示例模组目录）
    test_paths = [
        "/home/saken/mods",  # 用户之前扫描的目录
        "/home/saken/project/TH-Suite/apps/mc_l10n/test_mods",  # 测试目录
        "/tmp/test_mods",  # 临时测试目录
    ]

    # 找到存在的测试路径
    test_path = None
    for path in test_paths:
        if Path(path).exists():
            test_path = path
            break

    if not test_path:
        print("❌ 没有找到测试目录")
        print("请提供一个包含JAR文件的目录路径作为参数")
        if len(sys.argv) > 1:
            test_path = sys.argv[1]
            if not Path(test_path).exists():
                print(f"❌ 路径不存在: {test_path}")
                return
        else:
            return

    print(f"📂 测试目录: {test_path}")

    # 显示扫描前的数据库状态
    print("\n📊 扫描前数据库状态:")
    with UnifiedDatabase(str(db_path)) as db:
        stats = db.get_statistics()
        print(f"  模组总数: {stats['total_mods']}")
        print(f"  语言文件总数: {stats['total_language_files']}")
        print(f"  翻译条目总数: {stats['total_keys']}")

    # 创建扫描器
    scanner = DDDScanner(str(db_path))

    # 启动扫描
    print("\n🔍 开始扫描...")
    result = await scanner.start_scan(test_path, incremental=False)
    scan_id = result["scan_id"]
    print(f"  扫描ID: {scan_id}")

    # 等待扫描完成
    print("\n⏳ 等待扫描完成...")
    while True:
        status = await scanner.get_scan_status(scan_id)
        progress = status.get("progress", 0)
        current_file = status.get("current_file", "")

        # 显示进度
        bar_length = 40
        filled = int(bar_length * progress / 100)
        bar = "█" * filled + "░" * (bar_length - filled)

        print(
            f"\r  进度: [{bar}] {progress:.1f}% - {current_file[:30]}",
            end="",
            flush=True,
        )

        if status["status"] in ["completed", "failed", "cancelled"]:
            print()  # 换行
            break

        await asyncio.sleep(0.5)

    # 显示扫描结果
    print(f"\n✅ 扫描状态: {status['status']}")

    if status["status"] == "completed":
        print("\n📈 扫描统计:")
        stats = status.get("statistics", {})
        print(f"  找到模组: {stats.get('total_mods', 0)}")
        print(f"  语言文件: {stats.get('total_language_files', 0)}")
        print(f"  翻译键: {stats.get('total_keys', 0)}")

        # 显示错误和警告
        if status.get("errors"):
            print("\n❌ 错误:")
            for error in status["errors"][:5]:  # 只显示前5个错误
                print(f"  - {error}")

        if status.get("warnings"):
            print("\n⚠️ 警告:")
            for warning in status["warnings"][:5]:  # 只显示前5个警告
                print(f"  - {warning}")

    # 显示扫描后的数据库状态
    print("\n📊 扫描后数据库状态:")
    with UnifiedDatabase(str(db_path)) as db:
        stats = db.get_statistics()
        print(f"  模组总数: {stats['total_mods']}")
        print(f"  语言文件总数: {stats['total_language_files']}")
        print(f"  翻译条目总数: {stats['total_keys']}")

        # 显示语言分布
        if stats.get("language_distribution"):
            print("\n🌐 语言分布:")
            for locale, count in list(stats["language_distribution"].items())[:10]:
                print(f"  {locale}: {count} 个文件")

        # 显示最近的扫描
        if stats.get("recent_scans"):
            print("\n📅 最近的扫描:")
            for scan in stats["recent_scans"][:3]:
                print(
                    f"  - {scan['started_at']}: {scan['directory']} ({scan['status']})"
                )
                if scan["status"] == "completed":
                    print(
                        f"    模组: {scan['total_mods']}, 语言文件: {scan['total_language_files']}, 键: {scan['total_keys']}"
                    )

    print("\n✨ 测试完成!")


if __name__ == "__main__":
    # 运行异步测试
    asyncio.run(test_scan())
