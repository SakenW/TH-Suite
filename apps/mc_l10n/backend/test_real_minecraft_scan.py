#!/usr/bin/env python3
"""
使用真实的Minecraft整合包测试翻译内容存储功能
"""

import asyncio
import sys
import json
import sqlite3
from pathlib import Path

# 添加路径
sys.path.insert(0, '/home/saken/project/TH-Suite/apps/mc_l10n/backend')

async def test_real_minecraft_scan():
    """使用真实的Minecraft整合包测试扫描"""
    print("🔍 开始使用真实Minecraft整合包测试扫描")
    
    try:
        from infrastructure.services.simple_minecraft_scanner import get_simple_minecraft_scanner_service
        
        # 获取扫描服务
        service = get_simple_minecraft_scanner_service()
        print(f"✅ 获取扫描服务成功")
        
        # 使用真实的Minecraft整合包路径
        real_minecraft_path = "/mnt/d/Games/Curseforge/Minecraft/Instances/DeceasedCraft - Modern Zombie Apocalypse"
        
        print(f"📁 扫描真实Minecraft路径: {real_minecraft_path}")
        
        # 检查路径是否存在
        if not Path(real_minecraft_path).exists():
            print(f"❌ 路径不存在: {real_minecraft_path}")
            print("🔄 使用测试路径...")
            real_minecraft_path = "/tmp"
        
        # 启动扫描
        scan_result = await service.start_scan(
            target_path=real_minecraft_path,
            incremental=False,
            scan_options={
                "include_subdirectories": True,
                "validate_after_scan": True,
                "generate_statistics": True,
                "file_extensions": [".jar", ".zip"],
                "max_depth": 5,  # 减少深度以加快测试
                "max_file_size_mb": 100  # 限制文件大小
            }
        )
        
        print(f"📊 扫描启动结果:")
        print(f"  成功: {scan_result.get('success')}")
        print(f"  扫描ID: {scan_result.get('scan_id')}")
        print(f"  消息: {scan_result.get('message')}")
        
        if not scan_result.get("success"):
            print("❌ 扫描启动失败")
            return False
        
        scan_id = scan_result["scan_id"]
        print(f"🔄 等待扫描完成，扫描ID: {scan_id}")
        
        # 等待扫描完成，增加超时时间
        for i in range(120):  # 最多等待2分钟
            await asyncio.sleep(1)
            status_result = await service.get_scan_status(scan_id)
            
            if status_result.get("success"):
                status = status_result.get("status", "unknown")
                progress = status_result.get("progress", 0)
                
                if i % 10 == 0:  # 每10秒打印一次状态
                    print(f"⏳ 扫描状态: {status}, 进度: {progress}%")
                    
                    # 显示统计信息
                    stats = status_result.get("statistics", {})
                    if stats:
                        print(f"   已发现MOD: {stats.get('mods_found', 0)}")
                        print(f"   语言文件: {stats.get('language_files_found', 0)}")
                        print(f"   翻译条目: {stats.get('total_translation_keys', 0)}")
                
                if status in ["completed", "failed"]:
                    break
            else:
                print(f"❌ 获取状态失败: {status_result}")
                break
        
        # 检查最终状态
        final_status = await service.get_scan_status(scan_id)
        print(f"🏁 扫描完成!")
        
        if final_status.get("success") and final_status.get("status") == "completed":
            stats = final_status.get("statistics", {})
            print(f"📊 最终统计:")
            print(f"  总文件数: {stats.get('total_files', 0)}")
            print(f"  发现MOD数: {stats.get('mods_found', 0)}")
            print(f"  语言文件数: {stats.get('language_files_found', 0)}")
            print(f"  翻译条目数: {stats.get('total_translation_keys', 0)}")
            
            # 检查数据库中的实际数据
            await check_database_content()
            
            return True
        else:
            print(f"❌ 扫描未成功完成: {final_status}")
            return False
            
    except Exception as e:
        print(f"❌ 测试失败: {e}")
        import traceback
        print(traceback.format_exc())
        return False

async def check_database_content():
    """检查数据库中的实际内容"""
    print("\n🔍 检查数据库内容...")
    
    db_path = Path("data/mc_l10n_v2_1.db")
    if not db_path.exists():
        print(f"❌ 数据库文件不存在: {db_path}")
        return
    
    conn = sqlite3.connect(str(db_path))
    try:
        cursor = conn.cursor()
        
        # 检查各表记录数
        cursor.execute("SELECT COUNT(*) FROM packs")
        pack_count = cursor.fetchone()[0]
        
        cursor.execute("SELECT COUNT(*) FROM mod_version_instances")
        mod_count = cursor.fetchone()[0]
        
        cursor.execute("SELECT COUNT(*) FROM content_instances")
        content_count = cursor.fetchone()[0]
        
        cursor.execute("SELECT COUNT(*) FROM pack_content_relations")
        content_relation_count = cursor.fetchone()[0]
        
        print(f"📋 数据库验证结果:")
        print(f"  Pack记录: {pack_count}")
        print(f"  Mod记录: {mod_count}")
        print(f"  翻译内容记录: {content_count}")
        print(f"  内容关联记录: {content_relation_count}")
        
        if content_count > 0:
            print("🎉 翻译内容存储成功！")
            
            # 显示一些示例翻译内容
            cursor.execute("""
                SELECT content_key, content_source, language_code, file_path
                FROM content_instances 
                ORDER BY created_at DESC
                LIMIT 5
            """)
            samples = cursor.fetchall()
            
            print(f"\n📝 翻译内容示例:")
            for content_key, content_source, language_code, file_path in samples:
                print(f"  - {content_source} ({language_code}): {content_key}")
        else:
            print("❌ 未找到翻译内容记录")
            
    except Exception as e:
        print(f"❌ 数据库检查失败: {e}")
    finally:
        conn.close()

async def main():
    print("🚀 开始真实Minecraft整合包扫描测试")
    success = await test_real_minecraft_scan()
    print(f"🎯 测试{'成功' if success else '失败'}")
    return success

if __name__ == "__main__":
    success = asyncio.run(main())
    exit(0 if success else 1)