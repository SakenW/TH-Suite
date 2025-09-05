#!/usr/bin/env python
"""
测试真实数据扫描功能
"""

import asyncio
import os
import json
import zipfile
from pathlib import Path
import httpx
import time

# 测试数据目录
TEST_MODS_DIR = Path("/tmp/test_minecraft_mods")
API_BASE_URL = "http://localhost:18000"


def setup_test_data():
    """创建测试数据目录和模拟的mod文件"""
    # 创建测试目录
    TEST_MODS_DIR.mkdir(exist_ok=True)
    
    print(f"📁 测试目录: {TEST_MODS_DIR}")
    
    # 创建一个模拟的mod jar文件（包含语言文件）
    create_mock_mod_jar(TEST_MODS_DIR / "twilightforest-1.21.1-4.7.3196.jar")
    create_mock_mod_jar(TEST_MODS_DIR / "ae2-15.3.1-beta.jar")
    create_mock_mod_jar(TEST_MODS_DIR / "jei-1.21.1-20.1.16.jar")
    
    # 创建一个资源包目录结构
    resource_pack_dir = TEST_MODS_DIR / "MyResourcePack"
    resource_pack_dir.mkdir(exist_ok=True)
    
    # 创建pack.mcmeta
    pack_meta = {
        "pack": {
            "pack_format": 15,
            "description": "Test Resource Pack"
        }
    }
    
    with open(resource_pack_dir / "pack.mcmeta", "w", encoding="utf-8") as f:
        json.dump(pack_meta, f, indent=2)
    
    # 创建语言文件目录
    lang_dir = resource_pack_dir / "assets" / "minecraft" / "lang"
    lang_dir.mkdir(parents=True, exist_ok=True)
    
    # 创建语言文件
    en_us_lang = {
        "item.minecraft.diamond": "Diamond",
        "item.minecraft.iron_ingot": "Iron Ingot",
        "block.minecraft.stone": "Stone",
        "block.minecraft.dirt": "Dirt"
    }
    
    zh_cn_lang = {
        "item.minecraft.diamond": "钻石",
        "item.minecraft.iron_ingot": "铁锭",
        "block.minecraft.stone": "石头",
        "block.minecraft.dirt": "泥土"
    }
    
    with open(lang_dir / "en_us.json", "w", encoding="utf-8") as f:
        json.dump(en_us_lang, f, indent=2, ensure_ascii=False)
    
    with open(lang_dir / "zh_cn.json", "w", encoding="utf-8") as f:
        json.dump(zh_cn_lang, f, indent=2, ensure_ascii=False)
    
    print(f"✅ 创建测试数据完成")
    print(f"  - 3个模拟的mod JAR文件")
    print(f"  - 1个资源包目录")
    
    # 列出所有文件
    print("\n📋 测试文件列表:")
    for file in TEST_MODS_DIR.rglob("*"):
        if file.is_file():
            print(f"  - {file.relative_to(TEST_MODS_DIR)}")


def create_mock_mod_jar(jar_path: Path):
    """创建一个模拟的mod JAR文件"""
    mod_name = jar_path.stem.split("-")[0]
    
    # 创建临时目录
    temp_dir = Path(f"/tmp/{mod_name}_temp")
    temp_dir.mkdir(exist_ok=True)
    
    # 创建META-INF目录
    meta_dir = temp_dir / "META-INF"
    meta_dir.mkdir(exist_ok=True)
    
    # 创建mods.toml (Forge格式)
    mods_toml = f'''
modLoader="javafml"
loaderVersion="[47,)"

[[mods]]
modId="{mod_name}"
version="1.0.0"
displayName="{mod_name.title()}"
description="Test mod for {mod_name}"
'''
    
    with open(meta_dir / "mods.toml", "w") as f:
        f.write(mods_toml)
    
    # 创建assets目录和语言文件
    assets_dir = temp_dir / "assets" / mod_name / "lang"
    assets_dir.mkdir(parents=True, exist_ok=True)
    
    # 创建示例语言文件
    en_us_lang = {
        f"item.{mod_name}.test_item": f"{mod_name.title()} Test Item",
        f"block.{mod_name}.test_block": f"{mod_name.title()} Test Block",
        f"gui.{mod_name}.title": f"{mod_name.title()} GUI",
        f"tooltip.{mod_name}.info": f"This is a {mod_name} tooltip",
        f"config.{mod_name}.enabled": "Enable {mod_name.title()}",
    }
    
    zh_cn_lang = {
        f"item.{mod_name}.test_item": f"{mod_name.title()} 测试物品",
        f"block.{mod_name}.test_block": f"{mod_name.title()} 测试方块",
        f"gui.{mod_name}.title": f"{mod_name.title()} 界面",
        f"tooltip.{mod_name}.info": f"这是一个 {mod_name} 提示",
        f"config.{mod_name}.enabled": f"启用 {mod_name.title()}",
    }
    
    # 保存语言文件
    with open(assets_dir / "en_us.json", "w", encoding="utf-8") as f:
        json.dump(en_us_lang, f, indent=2, ensure_ascii=False)
    
    with open(assets_dir / "zh_cn.json", "w", encoding="utf-8") as f:
        json.dump(zh_cn_lang, f, indent=2, ensure_ascii=False)
    
    # 创建JAR文件
    with zipfile.ZipFile(jar_path, "w", zipfile.ZIP_DEFLATED) as zf:
        for file_path in temp_dir.rglob("*"):
            if file_path.is_file():
                arcname = file_path.relative_to(temp_dir)
                zf.write(file_path, arcname)
    
    # 清理临时目录
    import shutil
    shutil.rmtree(temp_dir)
    
    print(f"  ✓ 创建mod: {jar_path.name}")


async def test_scan_api():
    """测试扫描API"""
    async with httpx.AsyncClient() as client:
        print("\n🚀 开始测试扫描API...")
        
        # 1. 启动扫描
        print(f"\n1️⃣ 启动扫描: {TEST_MODS_DIR}")
        scan_request = {
            "path": str(TEST_MODS_DIR),
            "incremental": False  # 全量扫描
        }
        
        response = await client.post(
            f"{API_BASE_URL}/api/scan/project/start",
            json=scan_request
        )
        
        if response.status_code != 200:
            print(f"❌ 扫描启动失败: {response.status_code}")
            print(f"   响应: {response.text}")
            return
        
        scan_result = response.json()
        task_id = scan_result["task_id"]
        print(f"✅ 扫描启动成功")
        print(f"   任务ID: {task_id}")
        print(f"   状态: {scan_result['status']}")
        
        # 2. 轮询扫描进度
        print(f"\n2️⃣ 轮询扫描进度...")
        
        max_attempts = 30  # 最多等待30秒
        for i in range(max_attempts):
            await asyncio.sleep(1)  # 每秒检查一次
            
            response = await client.get(
                f"{API_BASE_URL}/api/scan/progress/{task_id}"
            )
            
            if response.status_code != 200:
                print(f"❌ 获取进度失败: {response.status_code}")
                continue
            
            progress = response.json()
            status = progress["status"]
            percent = progress.get("progress", 0) * 100
            
            print(f"   [{i+1}/{max_attempts}] 状态: {status}, 进度: {percent:.1f}%")
            print(f"      当前步骤: {progress.get('current_step', 'N/A')}")
            print(f"      已处理: {progress.get('processed_files', 0)}/{progress.get('total_files', 0)} 个文件")
            
            if status == "completed":
                print(f"\n✅ 扫描完成!")
                
                # 显示结果
                if "result" in progress and progress["result"]:
                    result = progress["result"]
                    project_info = result.get("project_info", {})
                    
                    print(f"\n📊 扫描结果:")
                    print(f"   - 总模组数: {project_info.get('total_mods', 0)}")
                    print(f"   - 语言文件数: {project_info.get('total_files', 0)}")
                    print(f"   - 翻译键数: {project_info.get('total_keys', 0)}")
                    
                    if "statistics" in progress:
                        stats = progress["statistics"]
                        print(f"\n📈 详细统计:")
                        for key, value in stats.items():
                            print(f"   - {key}: {value}")
                    
                    if result.get("errors"):
                        print(f"\n⚠️ 错误信息:")
                        for error in result["errors"]:
                            print(f"   - {error}")
                    
                    if result.get("warnings"):
                        print(f"\n⚠️ 警告信息:")
                        for warning in result["warnings"]:
                            print(f"   - {warning}")
                
                break
            
            elif status == "failed":
                print(f"\n❌ 扫描失败!")
                if "error_message" in progress:
                    print(f"   错误: {progress['error_message']}")
                break
        
        else:
            print(f"\n⏱️ 扫描超时（等待{max_attempts}秒）")
        
        # 3. 获取统计信息
        print(f"\n3️⃣ 获取扫描统计信息...")
        response = await client.get(f"{API_BASE_URL}/api/scan/statistics")
        
        if response.status_code == 200:
            stats = response.json()
            print(f"✅ 统计信息:")
            print(f"   - 总模组数: {stats.get('total_mods', 0)}")
            print(f"   - 语言文件数: {stats.get('total_language_files', 0)}")
            print(f"   - 翻译条目数: {stats.get('total_translation_entries', 0)}")
            print(f"   - 支持的游戏类型: {stats.get('supported_game_types', [])}")
            print(f"   - 扫描器版本: {stats.get('scanner_version', 'N/A')}")
        else:
            print(f"❌ 获取统计信息失败: {response.status_code}")


async def main():
    """主测试函数"""
    print("=" * 60)
    print("🎮 Minecraft本地化扫描器 - 真实数据测试")
    print("=" * 60)
    
    # 设置测试数据
    setup_test_data()
    
    # 等待服务启动
    print("\n⏳ 等待服务就绪...")
    await asyncio.sleep(2)
    
    # 测试扫描API
    await test_scan_api()
    
    print("\n" + "=" * 60)
    print("✨ 测试完成!")
    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(main())