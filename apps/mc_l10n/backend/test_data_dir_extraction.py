#!/usr/bin/env python3
"""
测试JAR解压是否使用数据库目录内的temp_extracts
"""

import asyncio
import tempfile
import zipfile
import json
from pathlib import Path

from infrastructure.services.simple_minecraft_scanner import SimpleMinecraftScannerService


async def test_data_dir_extraction():
    """测试JAR解压使用数据库目录"""
    print("=== 测试JAR解压使用数据库目录 ===")
    
    # 创建测试JAR文件
    with tempfile.NamedTemporaryFile(suffix='.jar', delete=False) as temp_jar:
        jar_path = Path(temp_jar.name)
        
        # 创建一个模拟的MOD JAR文件
        with zipfile.ZipFile(jar_path, 'w') as zf:
            zf.writestr('assets/testmod/lang/en_us.json', json.dumps({
                "test.key": "test value"
            }))
            zf.writestr('META-INF/mods.toml', 'modLoader="forge"')
    
    try:
        # 创建临时目录作为数据库目录
        with tempfile.TemporaryDirectory() as temp_db_dir:
            db_path = Path(temp_db_dir) / "test.db"
            
            # 创建扫描服务，应该会在data目录创建temp_extracts
            scanner = SimpleMinecraftScannerService(str(db_path))
            
            # 检查temp_extracts目录是否被创建
            expected_temp_dir = Path(temp_db_dir) / "temp_extracts"
            print(f"预期临时目录: {expected_temp_dir}")
            print(f"临时目录是否存在: {expected_temp_dir.exists()}")
            
            if expected_temp_dir.exists():
                print("✅ temp_extracts目录已创建在数据库目录内")
            else:
                print("❌ temp_extracts目录未创建")
                
            # 测试JAR读取器的基本目录配置
            print(f"JAR读取器临时目录配置: {scanner.jar_reader.helper.temp_base_dir}")
            
            # 简单测试JAR解压功能
            print("测试JAR解压功能...")
            lang_patterns = {'json': r'assets/.+/lang/[a-z]{2}_[a-z]{2}\.json$'}
            
            lang_files = await scanner.jar_reader.find_language_files(jar_path, lang_patterns)
            print(f"找到 {len(lang_files)} 个语言文件")
            
            # 检查是否有临时文件在预期目录中被创建和清理
            temp_files_before = list(expected_temp_dir.glob("*")) if expected_temp_dir.exists() else []
            print(f"解压后剩余临时文件: {len(temp_files_before)}")
            
            if len(temp_files_before) == 0:
                print("✅ 临时文件已正确清理")
            else:
                print(f"⚠️ 发现 {len(temp_files_before)} 个未清理的临时文件")
                for f in temp_files_before:
                    print(f"  - {f}")
            
            # 清理JAR读取器
            await scanner.jar_reader.cleanup()
            
    finally:
        # 清理测试文件
        if jar_path.exists():
            jar_path.unlink()


async def main():
    """主测试函数"""
    print("测试JAR解压是否正确使用数据库目录内的temp_extracts")
    
    await test_data_dir_extraction()
    
    print("\n=== 测试完成 ===")


if __name__ == "__main__":
    asyncio.run(main())