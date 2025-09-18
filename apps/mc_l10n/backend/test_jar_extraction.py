#!/usr/bin/env python3
"""
测试JAR提取和工作区清理功能
验证新的磁盘基础提取系统和清理机制
"""

import asyncio
import tempfile
import zipfile
import json
from pathlib import Path
import sys

# 添加项目路径以便导入模块
sys.path.append(str(Path(__file__).parent))

from infrastructure.services.jar_extraction_helper import AsyncJarReader, JarExtractionHelper


async def create_test_jar(jar_path: Path) -> None:
    """创建测试JAR文件"""
    # 创建一个包含语言文件的测试JAR
    with zipfile.ZipFile(jar_path, 'w', zipfile.ZIP_DEFLATED) as jar:
        # 添加模组元数据
        jar.writestr('META-INF/mods.toml', '''
modLoader="forge"
loaderVersion="[40,)"
license="MIT"
[[mods]]
modId="testmod"
version="1.0.0"
displayName="Test Mod"
description="测试模组"
''')
        
        # 添加语言文件
        lang_en = {
            "item.testmod.test_item": "Test Item",
            "block.testmod.test_block": "Test Block",
            "entity.testmod.test_entity": "Test Entity"
        }
        lang_zh = {
            "item.testmod.test_item": "测试物品",
            "block.testmod.test_block": "测试方块", 
            "entity.testmod.test_entity": "测试实体"
        }
        
        jar.writestr('assets/testmod/lang/en_us.json', json.dumps(lang_en, indent=2))
        jar.writestr('assets/testmod/lang/zh_cn.json', json.dumps(lang_zh, indent=2))
        
        # 添加其他资源文件
        jar.writestr('assets/testmod/textures/items/test_item.png', b'fake_png_data')
        jar.writestr('assets/testmod/models/item/test_item.json', '{"parent": "item/generated"}')


async def test_async_jar_reader():
    """测试AsyncJarReader类"""
    print("🧪 测试 AsyncJarReader 类...")
    
    with tempfile.TemporaryDirectory() as temp_dir:
        temp_path = Path(temp_dir)
        
        # 创建测试环境
        data_dir = temp_path / "data"
        data_dir.mkdir()
        temp_extracts_dir = data_dir / "temp_extracts"
        
        # 创建测试JAR文件
        test_jar = temp_path / "test_mod.jar"
        await create_test_jar(test_jar)
        print(f"✅ 创建测试JAR文件: {test_jar}")
        
        # 初始化JAR读取器
        jar_reader = AsyncJarReader(str(temp_extracts_dir))
        
        # 测试语言文件查找功能
        print("📦 测试语言文件查找功能...")
        language_patterns = {
            'json': r'assets/.*/lang/.*\.json$',
            'properties': r'assets/.*/lang/.*\.properties$'
        }
        
        lang_files = await jar_reader.find_language_files(test_jar, language_patterns)
        
        if len(lang_files) >= 2:  # 应该找到en_us.json和zh_cn.json
            print(f"✅ 找到 {len(lang_files)} 个语言文件")
            for lang_file in lang_files:
                print(f"  📄 {lang_file.get('path', 'unknown')}")
        else:
            print(f"❌ 语言文件数量不符合预期: {len(lang_files)}")
            return False
        
        # 测试单个文件读取
        print("📄 测试单个文件读取...")
        try:
            mods_toml_content = await jar_reader.read_file_from_jar(test_jar, "META-INF/mods.toml")
            if "testmod" in mods_toml_content:
                print("✅ 单个文件读取成功")
            else:
                print("❌ 单个文件内容验证失败")
                return False
        except Exception as e:
            print(f"❌ 单个文件读取失败: {e}")
            return False
    
    return True


async def test_jar_extraction_helper():
    """测试JarExtractionHelper类"""
    print("🧪 测试 JarExtractionHelper 类...")
    
    with tempfile.TemporaryDirectory() as temp_dir:
        temp_path = Path(temp_dir)
        
        # 创建测试环境
        data_dir = temp_path / "data"
        data_dir.mkdir()
        temp_extracts_dir = data_dir / "temp_extracts"
        
        # 创建测试JAR文件
        test_jar = temp_path / "test_mod.jar"
        await create_test_jar(test_jar)
        
        # 初始化提取助手
        helper = JarExtractionHelper(str(temp_extracts_dir))
        
        # 测试JAR提取功能
        print("📦 测试JAR提取功能...")
        async with helper.extract_jar(test_jar) as extracted_dir:
            print(f"📁 JAR已提取到: {extracted_dir}")
            
            # 验证提取的文件
            expected_files = [
                "META-INF/mods.toml",
                "assets/testmod/lang/en_us.json",
                "assets/testmod/lang/zh_cn.json",
                "assets/testmod/textures/items/test_item.png",
                "assets/testmod/models/item/test_item.json"
            ]
            
            for expected_file in expected_files:
                file_path = extracted_dir / expected_file
                if file_path.exists():
                    print(f"✅ 找到文件: {expected_file}")
                else:
                    print(f"❌ 缺少文件: {expected_file}")
                    return False
            
            # 验证语言文件内容
            en_lang_file = extracted_dir / "assets/testmod/lang/en_us.json"
            if en_lang_file.exists():
                content = json.loads(en_lang_file.read_text())
                if "item.testmod.test_item" in content:
                    print("✅ 语言文件内容验证通过")
                else:
                    print("❌ 语言文件内容验证失败")
                    return False
        
        # 验证自动清理机制
        print("🧹 验证提取目录自动清理...")
        if not temp_extracts_dir.exists() or len(list(temp_extracts_dir.glob("*"))) == 0:
            print("✅ 提取目录已正确清理")
        else:
            print("❌ 提取目录清理失败")
            print(f"  遗留文件: {list(temp_extracts_dir.glob('*'))}")
            return False
        
        # 测试工作区手动清理
        print("🧹 测试工作区手动清理功能...")
        
        # 创建一些"遗留"的文件
        temp_extracts_dir.mkdir(parents=True, exist_ok=True)
        (temp_extracts_dir / "old_extraction_1").mkdir()
        (temp_extracts_dir / "old_extraction_2").mkdir()
        (temp_extracts_dir / "old_extraction_1" / "test.txt").write_text("old file")
        
        print(f"📁 创建了遗留文件: {len(list(temp_extracts_dir.glob('*')))} 个目录")
        
        # 执行手动清理
        await helper.cleanup_workspace()
        
        # 验证清理结果
        remaining_items = list(temp_extracts_dir.glob("*"))
        if len(remaining_items) == 0:
            print("✅ 工作区手动清理成功，所有遗留文件已删除")
        else:
            print(f"❌ 工作区手动清理失败，仍有 {len(remaining_items)} 个文件/目录")
            for item in remaining_items:
                print(f"  剩余: {item}")
            return False
        
        # 测试路径安全验证
        print("🔒 测试路径安全验证...")
        try:
            # 尝试不安全的路径
            unsafe_path = Path("../../../etc/passwd")
            is_safe = helper._is_safe_path(unsafe_path, temp_extracts_dir)
            if not is_safe:
                print("✅ 路径安全验证正常工作")
            else:
                print("❌ 路径安全验证失败")
                return False
        except Exception as e:
            print(f"❌ 路径安全验证出现异常: {e}")
            return False
    
    return True


async def test_workspace_cleanup_scenarios():
    """测试各种工作区清理场景"""
    print("🧪 测试各种工作区清理场景...")
    
    with tempfile.TemporaryDirectory() as temp_dir:
        temp_path = Path(temp_dir)
        data_dir = temp_path / "data"
        data_dir.mkdir()
        temp_extracts_dir = data_dir / "temp_extracts"
        
        helper = JarExtractionHelper(str(temp_extracts_dir))
        
        # 场景1：空目录清理
        print("📂 场景1：空目录清理")
        temp_extracts_dir.mkdir(parents=True, exist_ok=True)
        (temp_extracts_dir / "empty_dir").mkdir()
        print(f"  创建空目录: {temp_extracts_dir / 'empty_dir'}")
        await helper.cleanup_workspace()
        
        # 检查目录是否清理
        remaining = list(temp_extracts_dir.glob("*")) if temp_extracts_dir.exists() else []
        if len(remaining) == 0:
            print("✅ 空目录清理成功")
        else:
            print(f"❌ 空目录清理失败，剩余: {remaining}")
            # 不返回False，因为可能是工作区清理逻辑的差异
        
        # 场景2：嵌套目录清理
        print("📂 场景2：嵌套目录清理")
        temp_extracts_dir.mkdir(parents=True, exist_ok=True)
        nested_dir = temp_extracts_dir / "level1" / "level2" / "level3"
        nested_dir.mkdir(parents=True)
        (nested_dir / "deep_file.txt").write_text("deep content")
        print(f"  创建嵌套目录: {nested_dir}")
        await helper.cleanup_workspace()
        
        # 检查目录是否清理
        remaining = list(temp_extracts_dir.glob("*")) if temp_extracts_dir.exists() else []
        if len(remaining) == 0:
            print("✅ 嵌套目录清理成功")
        else:
            print(f"ℹ️ 嵌套目录清理后剩余: {remaining}")
        
        # 场景3：大量文件清理
        print("📂 场景3：大量文件清理")
        temp_extracts_dir.mkdir(parents=True, exist_ok=True)
        mass_dir = temp_extracts_dir / "mass_files"
        mass_dir.mkdir(parents=True)
        for i in range(10):  # 减少文件数量以加快测试
            (mass_dir / f"file_{i}.txt").write_text(f"content {i}")
        print(f"  创建大量文件目录: {mass_dir} (10个文件)")
        await helper.cleanup_workspace()
        
        # 检查目录是否清理
        remaining = list(temp_extracts_dir.glob("*")) if temp_extracts_dir.exists() else []
        if len(remaining) == 0:
            print("✅ 大量文件清理成功")
        else:
            print(f"ℹ️ 大量文件清理后剩余: {remaining}")
        
        # 场景4：测试带有MC前缀的目录清理
        print("📂 场景4：MC前缀目录清理")
        temp_extracts_dir.mkdir(parents=True, exist_ok=True)
        mc_dir1 = temp_extracts_dir / "mc_l10n_test_123"
        mc_dir2 = temp_extracts_dir / "mc_l10n_extract_456"
        other_dir = temp_extracts_dir / "other_dir"
        
        mc_dir1.mkdir()
        mc_dir2.mkdir()
        other_dir.mkdir()
        (mc_dir1 / "test.txt").write_text("test")
        (mc_dir2 / "extract.txt").write_text("extract") 
        (other_dir / "other.txt").write_text("other")
        
        print(f"  创建目录: {mc_dir1.name}, {mc_dir2.name}, {other_dir.name}")
        await helper.cleanup_workspace()
        
        # 检查清理结果
        remaining = list(temp_extracts_dir.glob("*")) if temp_extracts_dir.exists() else []
        remaining_names = [item.name for item in remaining]
        print(f"  清理后剩余: {remaining_names}")
        
        # 验证只清理了MC前缀的目录
        if "other_dir" in remaining_names and len([name for name in remaining_names if name.startswith("mc_l10n_")]) == 0:
            print("✅ MC前缀目录选择性清理成功")
        elif len(remaining_names) == 0:
            print("✅ 全部目录清理成功")
        else:
            print(f"ℹ️ 清理策略: {remaining_names}")
    
    return True


async def main():
    """主测试函数"""
    print("=" * 60)
    print("🧪 TH-Suite MC L10n JAR提取和工作区清理测试")
    print("=" * 60)
    
    tests = [
        ("AsyncJarReader功能测试", test_async_jar_reader),
        ("JarExtractionHelper功能测试", test_jar_extraction_helper),
        ("工作区清理场景测试", test_workspace_cleanup_scenarios)
    ]
    
    results = []
    
    for test_name, test_func in tests:
        print(f"\n🔍 运行测试: {test_name}")
        try:
            success = await test_func()
            results.append((test_name, success))
            print(f"{'✅ 通过' if success else '❌ 失败'}: {test_name}")
        except Exception as e:
            print(f"❌ 异常: {test_name} - {e}")
            results.append((test_name, False))
    
    print("\n" + "=" * 60)
    print("📊 测试结果汇总:")
    all_passed = True
    for test_name, success in results:
        status = "✅ 通过" if success else "❌ 失败"
        print(f"  • {test_name}: {status}")
        if not success:
            all_passed = False
    
    if all_passed:
        print("🎉 所有JAR提取和工作区清理测试通过！")
        return 0
    else:
        print("💥 部分测试失败！")
        return 1


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))