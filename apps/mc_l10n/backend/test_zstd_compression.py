#!/usr/bin/env python
"""
测试Zstd压缩服务
验证基于locale的字典训练、压缩效率、中间件集成等功能
"""

import asyncio
import json
import tempfile
from pathlib import Path
import structlog

# 配置日志
structlog.configure(
    processors=[
        structlog.processors.TimeStamper(fmt="ISO"),
        structlog.dev.ConsoleRenderer()
    ],
    wrapper_class=structlog.stdlib.BoundLogger,
    logger_factory=structlog.stdlib.LoggerFactory(),
    cache_logger_on_first_use=True,
)

logger = structlog.get_logger(__name__)

from services.zstd_compression import (
    ZstdCompressionService, 
    CompressionLevel,
    get_compression_service,
    compress_translation_data,
    decompress_translation_data
)


def test_basic_compression():
    """测试基础压缩功能"""
    print("=== 测试基础压缩功能 ===")
    
    try:
        service = ZstdCompressionService()
        
        # 测试字符串压缩
        test_string = "Hello, 世界! This is a test string for compression. " * 10
        compressed, stats = service.compress(test_string)
        decompressed = service.decompress(compressed)
        
        assert decompressed.decode('utf-8') == test_string
        print(f"✓ 字符串压缩: {stats.original_size} → {stats.compressed_size} (比率: {stats.compression_ratio:.3f})")
        
        # 测试字典压缩
        test_dict = {
            "items": {
                "minecraft:iron_ingot": "铁锭",
                "minecraft:gold_ingot": "金锭",
                "minecraft:diamond": "钻石",
                "create:brass_ingot": "黄铜锭",
                "create:steel_ingot": "钢锭"
            },
            "blocks": {
                "minecraft:stone": "石头",
                "minecraft:dirt": "泥土",
                "minecraft:grass_block": "草方块"
            }
        }
        
        compressed, stats = service.compress(test_dict)
        decompressed_bytes = service.decompress(compressed)
        decompressed_dict = json.loads(decompressed_bytes.decode('utf-8'))
        
        assert decompressed_dict == test_dict
        print(f"✓ 字典压缩: {stats.original_size} → {stats.compressed_size} (比率: {stats.compression_ratio:.3f})")
        
        return True
        
    except Exception as e:
        print(f"✗ 基础压缩测试失败: {e}")
        return False


def test_locale_dictionary_training():
    """测试locale字典训练"""
    print("\n=== 测试Locale字典训练 ===")
    
    try:
        service = ZstdCompressionService(enable_dictionaries=True)
        
        # 准备中文翻译样本 - 增加更多数据以满足zstd训练要求
        zh_cn_samples = []
        base_translations = [
            ("item.minecraft.iron_ingot", "铁锭"), ("item.minecraft.gold_ingot", "金锭"),
            ("block.minecraft.stone", "石头"), ("block.minecraft.dirt", "泥土"),
            ("entity.minecraft.cow", "牛"), ("entity.minecraft.pig", "猪"),
            ("item.create.brass_ingot", "黄铜锭"), ("item.create.steel_ingot", "钢锭"),
            ("fluid.create.honey", "蜂蜜"), ("fluid.create.milk", "牛奶"),
            ("advancement.minecraft.story.mine_stone", "石器时代"),
            ("advancement.minecraft.story.upgrade_tools", "获得升级"),
            ("itemGroup.minecraft.building_blocks", "建筑方块"),
            ("itemGroup.minecraft.decorations", "装饰性方块"),
            ("enchantment.minecraft.sharpness", "锋利"),
            ("enchantment.minecraft.protection", "保护"),
            ("biome.minecraft.forest", "森林"), ("biome.minecraft.desert", "沙漠"),
            ("gui.minecraft.options.title", "选项"), ("gui.minecraft.controls.title", "控制"),
            ("key.minecraft.forward", "前进"), ("key.minecraft.back", "后退"),
            ("menu.minecraft.singleplayer", "单人游戏"),
            ("menu.minecraft.multiplayer", "多人游戏"),
            ("container.minecraft.chest", "箱子"), ("container.minecraft.furnace", "熔炉"),
            ("death.attack.fall", "%1$s 摔死了"), ("death.attack.drown", "%1$s 淹死了"),
            ("gameMode.survival", "生存模式"), ("gameMode.creative", "创造模式")
        ]
        
        # 为每个基础翻译创建多个变体以增加数据量
        for i, (key, value) in enumerate(base_translations):
            # 创建多个包含该翻译的样本
            for j in range(3):  # 每个翻译创建3个样本
                sample = {}
                # 添加当前翻译
                sample[key] = value
                # 添加一些额外的上下文条目
                for k in range(5):  # 每个样本包含5个额外条目
                    idx = (i * 3 + j + k) % len(base_translations)
                    ctx_key, ctx_value = base_translations[idx]
                    sample[f"{ctx_key}.variant_{j}"] = f"{ctx_value}(变体{j})"
                
                # 添加描述性文本增加数据量
                sample[f"description.{i}.{j}"] = f"这是第{i}个项目的第{j}个变体，包含详细的中文描述和说明文本，用于增加训练样本的数据量。"
                zh_cn_samples.append(sample)
        
        # 准备英文样本 - 同样增加数据量
        en_us_samples = []
        base_en_translations = [
            ("item.minecraft.iron_ingot", "Iron Ingot"), ("item.minecraft.gold_ingot", "Gold Ingot"),
            ("block.minecraft.stone", "Stone"), ("block.minecraft.dirt", "Dirt"),
            ("entity.minecraft.cow", "Cow"), ("entity.minecraft.pig", "Pig"),
            ("item.create.brass_ingot", "Brass Ingot"), ("item.create.steel_ingot", "Steel Ingot"),
            ("fluid.create.honey", "Honey"), ("fluid.create.milk", "Milk"),
            ("advancement.minecraft.story.mine_stone", "Stone Age"),
            ("advancement.minecraft.story.upgrade_tools", "Getting an Upgrade"),
            ("itemGroup.minecraft.building_blocks", "Building Blocks"),
            ("itemGroup.minecraft.decorations", "Decoration Blocks"),
            ("enchantment.minecraft.sharpness", "Sharpness"),
            ("enchantment.minecraft.protection", "Protection"),
            ("biome.minecraft.forest", "Forest"), ("biome.minecraft.desert", "Desert"),
            ("gui.minecraft.options.title", "Options"), ("gui.minecraft.controls.title", "Controls"),
            ("key.minecraft.forward", "Forward"), ("key.minecraft.back", "Back"),
            ("menu.minecraft.singleplayer", "Singleplayer"),
            ("menu.minecraft.multiplayer", "Multiplayer"),
            ("container.minecraft.chest", "Chest"), ("container.minecraft.furnace", "Furnace"),
            ("death.attack.fall", "%1$s fell from a high place"), 
            ("death.attack.drown", "%1$s drowned"),
            ("gameMode.survival", "Survival Mode"), ("gameMode.creative", "Creative Mode")
        ]
        
        # 为英文样本也创建多个变体
        for i, (key, value) in enumerate(base_en_translations):
            for j in range(3):
                sample = {}
                sample[key] = value
                for k in range(5):
                    idx = (i * 3 + j + k) % len(base_en_translations)
                    ctx_key, ctx_value = base_en_translations[idx]
                    sample[f"{ctx_key}.variant_{j}"] = f"{ctx_value} (Variant {j})"
                
                sample[f"description.{i}.{j}"] = f"This is variant {j} of item {i}, containing detailed English descriptions and explanatory text to increase training sample data size."
                en_us_samples.append(sample)
        
        # 添加训练样本
        for sample in zh_cn_samples:
            service.add_training_sample("zh_cn", sample)
        
        for sample in en_us_samples:
            service.add_training_sample("en_us", sample)
        
        print(f"✓ 添加训练样本: zh_cn({len(zh_cn_samples)}), en_us({len(en_us_samples)})")
        
        # 训练字典
        zh_success = service.train_dictionary("zh_cn")
        en_success = service.train_dictionary("en_us")
        
        if zh_success:
            print("✓ 中文字典训练成功")
        else:
            print("✗ 中文字典训练失败")
        
        if en_success:
            print("✓ 英文字典训练成功")
        else:
            print("✗ 英文字典训练失败")
        
        # 测试字典压缩效果
        if zh_success:
            test_zh_data = {"item.create.copper_ingot": "铜锭", "block.create.limestone": "石灰岩"}
            
            # 不使用字典
            compressed_no_dict, stats_no_dict = service.compress(test_zh_data)
            
            # 使用字典
            compressed_with_dict, stats_with_dict = service.compress(test_zh_data, locale="zh_cn")
            
            improvement = (stats_no_dict.compression_ratio - stats_with_dict.compression_ratio) / stats_no_dict.compression_ratio * 100
            print(f"✓ 字典压缩改进: {improvement:.1f}% (无字典: {stats_no_dict.compression_ratio:.3f}, 有字典: {stats_with_dict.compression_ratio:.3f})")
        
        return True
        
    except Exception as e:
        print(f"✗ 字典训练测试失败: {e}")
        logger.exception("字典训练测试异常")
        return False


def test_compression_levels():
    """测试不同压缩级别"""
    print("\n=== 测试压缩级别 ===")
    
    try:
        service = ZstdCompressionService()
        
        test_data = {
            "translations": {
                f"item.test.item_{i}": f"测试物品{i}" for i in range(100)
            },
            "description": "这是一个用于测试压缩级别的大型数据集，包含重复的模式和结构。" * 20
        }
        
        levels = [CompressionLevel.FAST, CompressionLevel.BALANCED, CompressionLevel.HIGH, CompressionLevel.MAXIMUM]
        
        for level in levels:
            compressed, stats = service.compress(test_data, level=level)
            print(f"✓ {level.name}: {stats.original_size} → {stats.compressed_size} (比率: {stats.compression_ratio:.3f})")
        
        return True
        
    except Exception as e:
        print(f"✗ 压缩级别测试失败: {e}")
        return False


def test_dictionary_persistence():
    """测试字典持久化"""
    print("\n=== 测试字典持久化 ===")
    
    try:
        with tempfile.TemporaryDirectory() as temp_dir:
            dict_dir = Path(temp_dir) / "dictionaries"
            
            # 创建服务并训练字典
            service1 = ZstdCompressionService(enable_dictionaries=True)
            
            # 添加样本并训练 - 生成足够的训练数据
            samples = []
            for i in range(50):  # 生成50个样本
                sample = {}
                for j in range(10):  # 每个样本包含10个键值对
                    key_idx = i * 10 + j
                    sample[f"test.key_{key_idx}"] = f"测试值{key_idx}包含详细描述信息"
                    sample[f"test.description_{key_idx}"] = f"这是第{key_idx}个测试项目的详细说明，用于增加训练样本的数据量和复杂度。"
                samples.append(sample)
            
            for sample in samples:
                service1.add_training_sample("test_locale", sample)
            
            success = service1.train_dictionary("test_locale")
            assert success, "字典训练失败"
            
            # 保存字典
            service1.save_dictionaries(dict_dir)
            print("✓ 字典保存成功")
            
            # 创建新服务并加载字典
            service2 = ZstdCompressionService(enable_dictionaries=True)
            service2.load_dictionaries(dict_dir)
            print("✓ 字典加载成功")
            
            # 验证加载的字典工作正常
            test_data = {"test.new_key": "新测试值"}
            compressed, stats = service2.compress(test_data, locale="test_locale")
            decompressed_data = service2.decompress_json(compressed, "test_locale")
            
            assert decompressed_data == test_data
            assert stats.dictionary_used
            print("✓ 加载的字典功能正常")
            
        return True
        
    except Exception as e:
        print(f"✗ 字典持久化测试失败: {e}")
        logger.exception("字典持久化测试异常")
        return False


def test_convenience_functions():
    """测试便捷函数"""
    print("\n=== 测试便捷函数 ===")
    
    try:
        # 测试全局服务实例
        service1 = get_compression_service()
        service2 = get_compression_service()
        assert service1 is service2, "全局服务实例不是单例"
        print("✓ 全局服务单例正常")
        
        # 测试便捷函数
        test_data = {
            "minecraft:items": {
                "iron_ingot": "铁锭",
                "gold_ingot": "金锭",
                "diamond": "钻石"
            }
        }
        
        compressed, stats = compress_translation_data(test_data, "zh_cn")
        decompressed = decompress_translation_data(compressed, "zh_cn")
        
        assert decompressed == test_data
        print(f"✓ 便捷函数正常: {stats.original_size} → {stats.compressed_size}")
        
        return True
        
    except Exception as e:
        print(f"✗ 便捷函数测试失败: {e}")
        return False


def test_compression_statistics():
    """测试压缩统计"""
    print("\n=== 测试压缩统计 ===")
    
    try:
        service = ZstdCompressionService()
        
        # 执行一些压缩操作
        for i in range(5):
            data = {"test": f"data {i}", "content": "测试内容" * (i+1)}
            service.compress(data, locale="zh_cn")
            service.compress(data, locale="en_us")
        
        # 获取统计信息
        all_stats = service.get_compression_stats()
        zh_stats = service.get_compression_stats("zh_cn")
        en_stats = service.get_compression_stats("en_us")
        
        print(f"✓ 总体统计: {all_stats['total_operations']} 次操作, 节省空间: {all_stats['space_saved_percent']:.1f}%")
        print(f"✓ 中文统计: {zh_stats['total_operations']} 次操作, 平均比率: {zh_stats['average_ratio']:.3f}")
        print(f"✓ 英文统计: {en_stats['total_operations']} 次操作, 平均比率: {en_stats['average_ratio']:.3f}")
        
        # 列出字典信息
        dict_info = service.list_dictionaries()
        print(f"✓ 字典信息: {len(dict_info)} 个字典")
        
        return True
        
    except Exception as e:
        print(f"✗ 压缩统计测试失败: {e}")
        return False


async def run_all_tests():
    """运行所有测试"""
    print("🚀 开始Zstd压缩服务测试")
    print("=" * 60)
    
    tests = [
        test_basic_compression,
        test_locale_dictionary_training,
        test_compression_levels,
        test_dictionary_persistence,
        test_convenience_functions,
        test_compression_statistics,
    ]
    
    passed = 0
    total = len(tests)
    
    for test in tests:
        try:
            result = test()
            if result:
                passed += 1
        except Exception as e:
            logger.error(f"测试执行异常: {test.__name__}", error=str(e))
    
    print("=" * 60)
    print(f"🏁 Zstd压缩服务测试完成: {passed}/{total} 通过")
    
    if passed == total:
        print("🎉 所有压缩测试通过!")
        return True
    else:
        print(f"⚠️  有 {total - passed} 个测试失败")
        return False


if __name__ == "__main__":
    asyncio.run(run_all_tests())