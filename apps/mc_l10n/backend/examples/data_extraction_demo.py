#!/usr/bin/env python3
"""
游戏专属数据提取器演示脚本
展示如何使用数据提取器系统处理不同游戏的翻译数据
"""

import asyncio
import json
import logging
import sys
import tempfile
import zipfile
from pathlib import Path

# 添加项目根目录到Python路径
sys.path.append(str(Path(__file__).parent.parent))

from infrastructure.services.unified_data_extraction_service import get_unified_extraction_service
from infrastructure.services.performance_optimized_extractor import get_performance_optimized_extractor
from infrastructure.services.cas_keyset_cache_service import get_cas_keyset_cache_service
from infrastructure.services.game_data_extractors import GameType, ExtractorRegistry

# 配置日志
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


async def create_sample_minecraft_mod():
    """创建示例Minecraft MOD文件"""
    logger.info("创建示例Minecraft MOD...")
    
    # 创建临时JAR文件
    temp_dir = Path(tempfile.mkdtemp())
    jar_path = temp_dir / "sample_mod.jar"
    
    # 创建MOD元数据
    mod_info = {
        "modLoader": "javafml",
        "loaderVersion": "[40,)",
        "mods": [{
            "modId": "sample_mod",
            "version": "1.0.0",
            "displayName": "示例MOD",
            "description": "这是一个示例MOD，用于演示数据提取功能",
            "authors": "TH-Suite Team"
        }]
    }
    
    # 创建语言文件
    zh_cn_lang = {
        "item.sample_mod.test_sword": "测试剑",
        "item.sample_mod.test_pickaxe": "测试镐",
        "block.sample_mod.test_ore": "测试矿石",
        "block.sample_mod.test_block": "测试方块",
        "gui.sample_mod.inventory": "背包",
        "gui.sample_mod.crafting": "合成",
        "itemGroup.sample_mod.items": "示例MOD物品",
        "advancement.sample_mod.root.title": "示例MOD",
        "advancement.sample_mod.root.description": "欢迎使用示例MOD!"
    }
    
    en_us_lang = {
        "item.sample_mod.test_sword": "Test Sword",
        "item.sample_mod.test_pickaxe": "Test Pickaxe", 
        "block.sample_mod.test_ore": "Test Ore",
        "block.sample_mod.test_block": "Test Block",
        "gui.sample_mod.inventory": "Inventory",
        "gui.sample_mod.crafting": "Crafting",
        "itemGroup.sample_mod.items": "Sample Mod Items",
        "advancement.sample_mod.root.title": "Sample Mod",
        "advancement.sample_mod.root.description": "Welcome to Sample Mod!"
    }
    
    # 创建JAR文件
    with zipfile.ZipFile(jar_path, 'w') as jar:
        # 添加MOD信息
        jar.writestr("META-INF/mods.toml", f"""
modLoader="javafml"
loaderVersion="[40,)"
license="MIT"

[[mods]]
modId="sample_mod"
version="1.0.0"
displayName="示例MOD"
description="演示用的示例MOD"
authors="TH-Suite Team"
""")
        
        # 添加语言文件
        jar.writestr("assets/sample_mod/lang/zh_cn.json", 
                    json.dumps(zh_cn_lang, ensure_ascii=False, indent=2))
        jar.writestr("assets/sample_mod/lang/en_us.json",
                    json.dumps(en_us_lang, ensure_ascii=False, indent=2))
    
    logger.info(f"示例Minecraft MOD已创建: {jar_path}")
    return jar_path


async def create_sample_discovered_items():
    """创建示例扫描发现项目"""
    minecraft_jar = await create_sample_minecraft_mod()
    
    discovered_items = [
        {
            "type": "mod",
            "mod_id": "sample_mod",
            "name": "示例MOD",
            "version": "1.0.0",
            "authors": ["TH-Suite Team"],
            "description": "演示用的示例MOD",
            "minecraft_version": "1.19.2",
            "loader_type": "forge",
            "path": str(minecraft_jar),
            "size": minecraft_jar.stat().st_size,
            "language_files": [
                {
                    "type": "language_file",
                    "language_code": "zh_cn",
                    "parent_mod": "sample_mod",
                    "entries_count": 9,
                    "file_path": "assets/sample_mod/lang/zh_cn.json",
                    "translations": {
                        "item.sample_mod.test_sword": "测试剑",
                        "item.sample_mod.test_pickaxe": "测试镐",
                        "block.sample_mod.test_ore": "测试矿石",
                        "block.sample_mod.test_block": "测试方块",
                        "gui.sample_mod.inventory": "背包",
                        "gui.sample_mod.crafting": "合成",
                        "itemGroup.sample_mod.items": "示例MOD物品",
                        "advancement.sample_mod.root.title": "示例MOD",
                        "advancement.sample_mod.root.description": "欢迎使用示例MOD!"
                    }
                },
                {
                    "type": "language_file", 
                    "language_code": "en_us",
                    "parent_mod": "sample_mod",
                    "entries_count": 9,
                    "file_path": "assets/sample_mod/lang/en_us.json",
                    "translations": {
                        "item.sample_mod.test_sword": "Test Sword",
                        "item.sample_mod.test_pickaxe": "Test Pickaxe",
                        "block.sample_mod.test_ore": "Test Ore",
                        "block.sample_mod.test_block": "Test Block",
                        "gui.sample_mod.inventory": "Inventory",
                        "gui.sample_mod.crafting": "Crafting",
                        "itemGroup.sample_mod.items": "Sample Mod Items",
                        "advancement.sample_mod.root.title": "Sample Mod",
                        "advancement.sample_mod.root.description": "Welcome to Sample Mod!"
                    }
                }
            ]
        }
    ]
    
    return discovered_items


async def demo_basic_extraction():
    """演示基础数据提取功能"""
    logger.info("=" * 50)
    logger.info("演示基础数据提取功能")
    logger.info("=" * 50)
    
    # 获取统一提取服务
    service = get_unified_extraction_service()
    
    # 创建示例数据
    discovered_items = await create_sample_discovered_items()
    
    logger.info(f"准备提取 {len(discovered_items)} 个发现项目...")
    
    # 执行提取
    result = await service.extract_from_scan_results(discovered_items)
    
    if result["success"]:
        stats = result["statistics"]
        logger.info("✅ 基础提取成功!")
        logger.info(f"   📁 语言文件数量: {stats['total_language_files']}")
        logger.info(f"   📝 翻译条目数量: {stats['total_translation_entries']}")
        logger.info(f"   🎮 支持的游戏: {', '.join(stats['supported_games'])}")
        logger.info(f"   ⏱️  提取耗时: {result['duration_ms']}ms")
    else:
        logger.error(f"❌ 基础提取失败: {result.get('error', '未知错误')}")
    
    return result


async def demo_performance_optimization():
    """演示性能优化提取功能"""
    logger.info("=" * 50)
    logger.info("演示性能优化提取功能")
    logger.info("=" * 50)
    
    # 获取性能优化提取器
    extractor = get_performance_optimized_extractor()
    
    # 创建示例数据
    discovered_items = await create_sample_discovered_items()
    
    # 配置优化选项
    optimization_options = {
        "max_workers": 4,
        "memory_threshold_mb": 256,
        "batch_size": 50,
        "cache_enabled": True
    }
    
    logger.info(f"启用性能优化，配置: {optimization_options}")
    
    # 执行优化提取
    result = await extractor.extract_with_optimization(
        discovered_items, 
        optimization_options
    )
    
    if result["success"]:
        metrics = result["performance_metrics"]
        logger.info("✅ 性能优化提取成功!")
        logger.info(f"   📊 处理项目数: {metrics['items_processed']}")
        logger.info(f"   🚀 吞吐量: {metrics['throughput_items_per_sec']:.2f} 项目/秒")
        logger.info(f"   💾 峰值内存: {metrics['peak_memory_mb']:.1f} MB")
        logger.info(f"   🎯 缓存命中率: {metrics['cache_hit_rate']*100:.1f}%")
        logger.info(f"   ⚡ 并行工作线程: {metrics['parallel_workers']}")
        logger.info(f"   💰 增量节省: {metrics['incremental_savings_percent']:.1f}%")
    else:
        logger.error(f"❌ 性能优化提取失败: {result.get('error', '未知错误')}")
    
    return result


async def demo_incremental_extraction():
    """演示增量提取功能"""
    logger.info("=" * 50)
    logger.info("演示增量提取功能")
    logger.info("=" * 50)
    
    service = get_unified_extraction_service()
    cache_service = get_cas_keyset_cache_service()
    
    # 创建示例数据
    discovered_items = await create_sample_discovered_items()
    
    logger.info("第一次提取（全量）...")
    result1 = await service.extract_from_scan_results(discovered_items)
    
    if result1["success"]:
        logger.info(f"✅ 全量提取完成: {result1['statistics']['total_language_files']} 个文件")
    
    logger.info("第二次提取（增量）...")
    result2 = await service.extract_incremental(discovered_items)
    
    if result2["success"]:
        logger.info(f"✅ 增量提取完成: {result2['processed_files']} 个变更文件")
        logger.info("💡 由于内容未变化，增量提取应该跳过大部分文件")
    else:
        logger.error(f"❌ 增量提取失败: {result2.get('error', '未知错误')}")
    
    return result2


async def demo_cache_operations():
    """演示缓存操作功能"""
    logger.info("=" * 50)
    logger.info("演示缓存操作功能")
    logger.info("=" * 50)
    
    cache_service = get_cas_keyset_cache_service()
    
    # 存储键集指纹
    test_keys = ["item.test.sword", "item.test.pickaxe", "block.test.ore"]
    
    logger.info("存储键集指纹...")
    keyset_hash = await cache_service.store_keyset_fingerprint(
        carrier_uid="test_mod",
        relative_path="assets/test_mod/lang/zh_cn.json",
        locale="zh_cn",
        keys=test_keys
    )
    logger.info(f"✅ 键集指纹已存储: {keyset_hash}")
    
    # 检查键集变化
    logger.info("检查键集变化...")
    changes = await cache_service.check_keyset_changes(
        carrier_uid="test_mod",
        relative_path="assets/test_mod/lang/zh_cn.json", 
        locale="zh_cn",
        current_keys=test_keys  # 相同的键
    )
    
    logger.info(f"🔍 键集变化检查: {'有变化' if changes['has_changes'] else '无变化'}")
    logger.info(f"   变更类型: {changes['change_type']}")
    
    # 修改键集再次检查
    modified_keys = test_keys + ["item.test.new_item"]  # 添加新键
    changes2 = await cache_service.check_keyset_changes(
        carrier_uid="test_mod",
        relative_path="assets/test_mod/lang/zh_cn.json",
        locale="zh_cn", 
        current_keys=modified_keys
    )
    
    logger.info(f"🔍 修改后键集检查: {'有变化' if changes2['has_changes'] else '无变化'}")
    if changes2['has_changes']:
        logger.info(f"   新增键: {changes2['added_keys']}")
        logger.info(f"   删除键: {changes2['removed_keys']}")
    
    # 存储CAS对象
    logger.info("存储CAS对象...")
    test_content = {
        "extraction_result": {
            "files_processed": 10,
            "entries_extracted": 150,
            "timestamp": "2025-09-20T10:00:00Z"
        }
    }
    
    object_hash = await cache_service.store_cas_object(
        object_type="demo_extraction",
        content=test_content,
        metadata={"demo": True, "version": "1.0"}
    )
    logger.info(f"✅ CAS对象已存储: {object_hash}")
    
    # 检索CAS对象
    retrieved_object = await cache_service.get_cas_object(object_hash)
    if retrieved_object:
        logger.info("✅ CAS对象检索成功")
        logger.info(f"   对象类型: {retrieved_object['object_type']}")
        logger.info(f"   内容大小: {retrieved_object['size_bytes']} 字节")
    
    # 获取缓存统计
    logger.info("获取缓存统计...")
    stats = await cache_service.get_cache_statistics()
    logger.info("📊 缓存统计:")
    logger.info(f"   键集指纹: {stats['keyset_fingerprints']['total_count']} 条")
    logger.info(f"   CAS对象: {stats['cas_objects']['total_count']} 个")
    logger.info(f"   总大小: {stats['cas_objects']['total_size_bytes']} 字节")


async def demo_game_type_detection():
    """演示游戏类型检测功能"""
    logger.info("=" * 50)
    logger.info("演示游戏类型检测功能")
    logger.info("=" * 50)
    
    # 测试不同游戏类型的检测
    test_cases = [
        {
            "name": "Minecraft MOD",
            "items": [{"type": "mod", "loader_type": "forge", "path": "/test/mod.jar"}]
        },
        {
            "name": "RimWorld MOD",
            "items": [{"path": "Languages/ChineseSimplified/DefInjected/ThingDef/Weapons.xml"}]
        },
        {
            "name": "Factorio MOD", 
            "items": [{"path": "locale/zh-CN/base.cfg"}]
        },
        {
            "name": "Minecraft 资源包",
            "items": [{"path": "assets/minecraft/lang/zh_cn.json"}]
        },
        {
            "name": "未知类型",
            "items": [{"path": "/some/unknown/file.txt"}]
        }
    ]
    
    for test_case in test_cases:
        detected_type = ExtractorRegistry.detect_game_type(test_case["items"])
        logger.info(f"🎮 {test_case['name']}: {detected_type.value if detected_type else '未识别'}")


async def demo_statistics_and_monitoring():
    """演示统计和监控功能"""
    logger.info("=" * 50)
    logger.info("演示统计和监控功能")
    logger.info("=" * 50)
    
    service = get_unified_extraction_service()
    extractor = get_performance_optimized_extractor()
    
    # 获取提取统计
    logger.info("获取提取统计...")
    extraction_stats = await service.get_extraction_statistics()
    
    if "error" not in extraction_stats:
        logger.info("📊 提取统计:")
        if "language_files" in extraction_stats:
            lang_stats = extraction_stats["language_files"]
            logger.info(f"   语言文件总数: {lang_stats.get('total_files', 0)}")
            logger.info(f"   按格式分布: {lang_stats.get('by_format', {})}")
            logger.info(f"   按语言分布: {lang_stats.get('by_locale', {})}")
        
        if "translation_entries" in extraction_stats:
            entry_stats = extraction_stats["translation_entries"] 
            logger.info(f"   翻译条目总数: {entry_stats.get('total_entries', 0)}")
            logger.info(f"   翻译完成率: {entry_stats.get('completion_rate', 0)*100:.1f}%")
    
    # 获取性能报告
    logger.info("获取性能报告...")
    performance_report = await extractor.get_performance_report()
    
    if "recent_performance" in performance_report:
        perf = performance_report["recent_performance"]
        logger.info("🚀 性能报告:")
        logger.info(f"   平均吞吐量: {perf['average_throughput_items_per_sec']:.2f} 项目/秒")
        logger.info(f"   平均内存使用: {perf['average_memory_usage_mb']:.1f} MB")
        logger.info(f"   平均缓存命中率: {perf['average_cache_hit_rate']:.1f}%")
        logger.info(f"   并行工作线程: {perf['parallel_workers']}")
    
    logger.info(f"   活跃会话数: {performance_report.get('active_sessions', 0)}")
    logger.info(f"   总提取次数: {performance_report.get('total_extractions', 0)}")


async def main():
    """主演示函数"""
    logger.info("🚀 游戏专属数据提取器演示开始")
    logger.info("这个演示将展示TH-Suite v2.0数据提取器的主要功能")
    
    try:
        # 1. 基础提取演示
        await demo_basic_extraction()
        
        # 2. 性能优化演示
        await demo_performance_optimization()
        
        # 3. 增量提取演示
        await demo_incremental_extraction()
        
        # 4. 缓存操作演示
        await demo_cache_operations()
        
        # 5. 游戏类型检测演示
        await demo_game_type_detection()
        
        # 6. 统计和监控演示
        await demo_statistics_and_monitoring()
        
        logger.info("=" * 50)
        logger.info("✅ 所有演示完成!")
        logger.info("=" * 50)
        
        # 支持的功能总结
        logger.info("📋 功能总结:")
        logger.info("   ✅ 多游戏支持 (Minecraft, RimWorld, Factorio)")
        logger.info("   ✅ 智能格式检测 (JSON, Lang, Properties, XML, CFG)")
        logger.info("   ✅ 性能优化 (并行处理, 内存管理, 批量操作)")
        logger.info("   ✅ 增量提取 (键集指纹, 变更检测)")
        logger.info("   ✅ CAS缓存 (内容寻址存储, 去重优化)")
        logger.info("   ✅ 事件驱动 (LANG_UPSERT事件, 批量处理)")
        logger.info("   ✅ 数据库集成 (Repository模式, 事务安全)")
        logger.info("   ✅ 监控统计 (性能指标, 缓存统计)")
        
    except Exception as e:
        logger.error(f"❌ 演示过程中发生错误: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    # 运行演示
    asyncio.run(main())