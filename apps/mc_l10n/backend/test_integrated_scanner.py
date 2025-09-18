#!/usr/bin/env python3
"""
测试集成了JAR解压系统的扫描服务
"""

import asyncio
import tempfile
import zipfile
import json
from pathlib import Path

from infrastructure.services.simple_minecraft_scanner import SimpleMinecraftScannerService


async def create_test_jar():
    """创建一个测试用的JAR文件"""
    with tempfile.NamedTemporaryFile(suffix='.jar', delete=False) as temp_jar:
        jar_path = Path(temp_jar.name)
        
        # 创建一个模拟的MOD JAR文件
        with zipfile.ZipFile(jar_path, 'w') as zf:
            # 添加Forge mods.toml
            mods_toml = '''modLoader="forge"
loaderVersion="[47,)"
license="MIT"

[[mods]]
modId="testmod"
version="1.0.0"
displayName="Test Mod"
authors="Test Author"
description="A test mod for scanning"
'''
            zf.writestr('META-INF/mods.toml', mods_toml)
            
            # 添加语言文件
            zf.writestr('assets/testmod/lang/en_us.json', json.dumps({
                "item.testmod.test_item": "Test Item",
                "block.testmod.test_block": "Test Block",
                "tooltip.testmod.test_tooltip": "This is a test tooltip"
            }))
            
            zf.writestr('assets/testmod/lang/zh_cn.json', json.dumps({
                "item.testmod.test_item": "测试物品",
                "block.testmod.test_block": "测试方块",
                "tooltip.testmod.test_tooltip": "这是一个测试提示"
            }))
            
            # 添加properties格式的语言文件
            zf.writestr('assets/testmod/lang/es_es.properties', 
                       "item.testmod.test_item=Artículo de prueba\n"
                       "block.testmod.test_block=Bloque de prueba\n"
                       "tooltip.testmod.test_tooltip=Este es un tooltip de prueba")
    
    return jar_path


async def test_integrated_scanner():
    """测试集成了JAR解压系统的扫描服务"""
    print("=== 测试集成扫描服务 ===")
    
    # 创建测试JAR文件
    jar_path = await create_test_jar()
    
    try:
        # 创建临时目录作为扫描目标
        with tempfile.TemporaryDirectory() as temp_dir:
            target_dir = Path(temp_dir) / "mods"
            target_dir.mkdir(parents=True, exist_ok=True)
            
            # 复制JAR文件到mods目录
            test_jar = target_dir / "testmod-1.0.0.jar"
            test_jar.write_bytes(jar_path.read_bytes())
            
            # 初始化扫描服务
            scanner = SimpleMinecraftScannerService()
            
            print(f"开始扫描目录: {temp_dir}")
            
            # 启动扫描
            result = await scanner.start_scan(
                target_path=str(temp_dir),
                incremental=False,
                scan_options={}
            )
            
            print(f"扫描启动结果: {result}")
            
            if result["success"]:
                scan_id = result["scan_id"]
                
                # 等待扫描完成
                max_wait = 30  # 最多等待30秒
                for i in range(max_wait):
                    await asyncio.sleep(1)
                    
                    # 获取扫描状态
                    status = await scanner.get_scan_status(scan_id)
                    
                    print(f"扫描进度: {status.get('progress', 0):.1f}% - {status.get('current_item', '')}")
                    
                    if status.get('status') == 'completed':
                        print("✅ 扫描完成！")
                        print(f"扫描结果: {status['statistics']}")
                        
                        discovered_items = status.get('discovered_items', [])
                        print(f"发现 {len(discovered_items)} 个项目:")
                        
                        for item in discovered_items:
                            print(f"  - {item['type']}: {item.get('name', item.get('mod_id', 'Unknown'))}")
                            if item['type'] == 'mod':
                                lang_files = item.get('language_files', [])
                                print(f"    语言文件: {len(lang_files)} 个")
                                for lang_file in lang_files:
                                    print(f"      - {lang_file['language']}: {lang_file['key_count']} 个条目")
                        break
                        
                    elif status.get('status') == 'failed':
                        print(f"❌ 扫描失败: {status.get('error', 'Unknown error')}")
                        break
                        
                else:
                    print("⏰ 扫描超时")
            
            # 清理JAR读取器
            await scanner.jar_reader.cleanup()
            
    finally:
        # 清理测试文件
        if jar_path.exists():
            jar_path.unlink()


async def main():
    """主测试函数"""
    print("测试集成了JAR解压系统的简化扫描服务")
    
    await test_integrated_scanner()
    
    print("\n=== 测试完成 ===")


if __name__ == "__main__":
    asyncio.run(main())