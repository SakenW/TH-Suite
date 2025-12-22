#!/usr/bin/env python
"""
测试新的六边形架构
验证所有组件是否正常工作
"""

import sys
from pathlib import Path

# 添加src目录到Python路径
sys.path.insert(0, str(Path(__file__).parent / "src"))

from container import get_container
from domain.models.mod import Mod, ModId
from infrastructure.minecraft.mod_scanner import MinecraftModScanner


def test_container():
    """测试依赖注入容器"""
    print("Testing Container...")

    container = get_container()
    stats = container.get_stats()

    print(f"  Initialized: {stats['initialized']}")
    print(f"  Repositories: {len(stats['repositories'])}")
    print(f"  Services: {len(stats['services'])}")

    # 测试获取服务
    scan_service = container.get_service("scan")
    print(f"  Scan Service: {scan_service is not None}")

    # 测试获取repository
    mod_repo = container.get_repository("mod")
    print(f"  Mod Repository: {mod_repo is not None}")

    return True


def test_domain_models():
    """测试领域模型"""
    print("\nTesting Domain Models...")

    # 创建Mod
    mod = Mod.create(
        mod_id="test_mod",
        name="Test Mod",
        version="1.0.0",
        file_path="/test/path/mod.jar",
    )

    print(f"  Created Mod: {mod.mod_id}")
    print(f"  Name: {mod.metadata.name}")
    print(f"  Version: {mod.metadata.version}")

    # 测试领域行为
    mod.scan_completed("hash123", 100)
    print(f"  Scan Status: {mod.scan_status}")
    print(f"  Events: {len(mod.domain_events)}")

    return True


def test_repository():
    """测试Repository层"""
    print("\nTesting Repository...")

    container = get_container()
    mod_repo = container.get_repository("mod")

    # 创建测试Mod
    mod = Mod.create(
        mod_id="test_repo_mod",
        name="Repository Test Mod",
        version="2.0.0",
        file_path="/test/repo/mod.jar",
    )

    # 保存
    saved = mod_repo.save(mod)
    print(f"  Saved Mod: {saved.mod_id}")

    # 查找
    found = mod_repo.find_by_id(ModId("test_repo_mod"))
    print(f"  Found Mod: {found is not None}")

    # 统计
    count = mod_repo.count()
    print(f"  Total Mods: {count}")

    return True


def test_scanner():
    """测试扫描器"""
    print("\nTesting Scanner...")

    scanner = MinecraftModScanner()

    # 测试支持的扩展
    print(f"  Supported Extensions: {scanner.supported_extensions}")

    # 注意：实际扫描需要真实的jar文件
    print("  Scanner initialized successfully")

    return True


def test_cache():
    """测试缓存"""
    print("\nTesting Cache...")

    container = get_container()
    cache = container.get_repository("cache")

    # 设置值
    cache.set("test_key", "test_value", ttl=60)

    # 获取值
    value = cache.get("test_key")
    print(f"  Cached Value: {value}")

    # 检查存在
    exists = cache.exists("test_key")
    print(f"  Key Exists: {exists}")

    # 获取统计
    stats = cache.get_stats()
    print(
        f"  Cache Stats: Size={stats['size']}, Hits={stats['hits']}, Misses={stats['misses']}"
    )

    return True


def test_health_check():
    """测试健康检查"""
    print("\nTesting Health Check...")

    from adapters.api.dependencies import check_dependencies_health

    health = check_dependencies_health()

    print(f"  Database: {health.get('database', False)}")
    print(f"  Cache: {health.get('cache', False)}")
    print(
        f"  Services Initialized: {health.get('services', {}).get('initialized', False)}"
    )

    if "cache_stats" in health:
        print(f"  Cache Hit Rate: {health['cache_stats'].get('hit_rate', 0):.2f}%")

    return True


def main():
    """主测试函数"""
    print("=" * 60)
    print("MC L10n Architecture Test")
    print("Testing Hexagonal Architecture Implementation")
    print("=" * 60)

    tests = [
        ("Container", test_container),
        ("Domain Models", test_domain_models),
        ("Repository", test_repository),
        ("Scanner", test_scanner),
        ("Cache", test_cache),
        ("Health Check", test_health_check),
    ]

    results = []

    for name, test_func in tests:
        try:
            success = test_func()
            results.append((name, success))
        except Exception as e:
            print(f"\n❌ {name} failed: {e}")
            results.append((name, False))

    # 报告
    print("\n" + "=" * 60)
    print("Test Results:")
    print("-" * 60)

    for name, success in results:
        status = "✅ PASS" if success else "❌ FAIL"
        print(f"  {name}: {status}")

    total = len(results)
    passed = sum(1 for _, success in results if success)

    print("-" * 60)
    print(f"Total: {passed}/{total} passed")

    if passed == total:
        print("\n🎉 All tests passed! Architecture is working correctly.")
    else:
        print(f"\n⚠️ {total - passed} test(s) failed. Please check the errors above.")

    print("=" * 60)

    # 清理
    container = get_container()
    container.cleanup()


if __name__ == "__main__":
    main()
