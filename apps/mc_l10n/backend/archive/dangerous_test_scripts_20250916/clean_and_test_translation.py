#!/usr/bin/env python3
"""
清理数据库并重新测试翻译内容存储
"""

import asyncio
import sys
import sqlite3
from pathlib import Path

# 添加路径
sys.path.insert(0, '/home/saken/project/TH-Suite/apps/mc_l10n/backend')

def clean_database():
    """清理数据库中的测试数据"""
    print("🧹 清理数据库...")
    
    db_path = Path("data/mc_l10n_v2_1.db")
    if not db_path.exists():
        print(f"❌ 数据库文件不存在: {db_path}")
        return False
    
    conn = sqlite3.connect(str(db_path))
    try:
        # 清理所有扫描相关的数据
        conn.execute("DELETE FROM pack_content_relations")
        conn.execute("DELETE FROM content_instances") 
        conn.execute("DELETE FROM pack_mod_relations")
        conn.execute("DELETE FROM mod_version_instances")
        conn.execute("DELETE FROM pack_versions")
        conn.execute("DELETE FROM packs")
        
        # 重置自增ID
        conn.execute("DELETE FROM sqlite_sequence WHERE name IN ('packs', 'pack_versions', 'mod_version_instances', 'content_instances', 'pack_mod_relations', 'pack_content_relations')")
        
        conn.commit()
        print("✅ 数据库清理完成")
        return True
        
    except Exception as e:
        print(f"❌ 数据库清理失败: {e}")
        conn.rollback()
        return False
    finally:
        conn.close()

async def test_translation_storage():
    """测试翻译内容存储功能"""
    print("🔍 开始测试翻译内容存储...")
    
    try:
        from infrastructure.services.simple_minecraft_scanner import get_simple_minecraft_scanner_service
        
        # 获取扫描服务
        service = get_simple_minecraft_scanner_service()
        print(f"✅ 获取扫描服务成功")
        
        # 使用指定的整合包路径
        minecraft_path = "/mnt/d/Games/Curseforge/Minecraft/Instances/DeceasedCraft - Modern Zombie Apocalypse"
        
        print(f"📁 扫描路径: {minecraft_path}")
        
        # 启动扫描
        scan_result = await service.start_scan(
            target_path=minecraft_path,
            incremental=False,
            scan_options={
                "include_subdirectories": True,
                "validate_after_scan": True,
                "generate_statistics": True,
                "file_extensions": [".jar", ".zip"],
                "max_depth": 5,  # 限制深度
                "max_file_size_mb": 50  # 限制文件大小以加快测试
            }
        )
        
        print(f"📊 扫描启动结果: {scan_result.get('success')}")
        
        if not scan_result.get("success"):
            print("❌ 扫描启动失败")
            return False
        
        scan_id = scan_result["scan_id"]
        print(f"🔄 等待扫描完成，扫描ID: {scan_id}")
        
        # 等待扫描完成
        for i in range(60):  # 最多等待1分钟
            await asyncio.sleep(1)
            status_result = await service.get_scan_status(scan_id)
            
            if status_result.get("success"):
                status = status_result.get("status", "unknown")
                progress = status_result.get("progress", 0)
                
                if i % 15 == 0:  # 每15秒打印一次
                    print(f"⏳ 状态: {status}, 进度: {progress}%")
                    stats = status_result.get("statistics", {})
                    if stats:
                        print(f"   MOD: {stats.get('mods_found', 0)}, 语言文件: {stats.get('language_files_found', 0)}, 翻译: {stats.get('total_translation_keys', 0)}")
                
                if status in ["completed", "failed"]:
                    break
            else:
                print(f"❌ 获取状态失败: {status_result}")
                break
        
        # 检查最终结果
        final_status = await service.get_scan_status(scan_id)
        if final_status.get("success") and final_status.get("status") == "completed":
            stats = final_status.get("statistics", {})
            print(f"🏁 扫描完成!")
            print(f"   发现MOD: {stats.get('mods_found', 0)}")
            print(f"   语言文件: {stats.get('language_files_found', 0)}")
            print(f"   翻译条目: {stats.get('total_translation_keys', 0)}")
            
            return await check_translation_results()
        else:
            print(f"❌ 扫描失败: {final_status}")
            return False
            
    except Exception as e:
        print(f"❌ 测试失败: {e}")
        import traceback
        print(traceback.format_exc())
        return False

async def check_translation_results():
    """检查翻译结果"""
    print("\n🔍 检查翻译存储结果...")
    
    db_path = Path("data/mc_l10n_v2_1.db")
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
        
        print(f"📊 数据库记录统计:")
        print(f"  Pack记录: {pack_count}")
        print(f"  Mod记录: {mod_count}")
        print(f"  翻译内容记录: {content_count}")
        print(f"  内容关联记录: {content_relation_count}")
        
        success = content_count > 0
        
        if success:
            print("🎉 翻译内容存储成功！")
            
            # 显示语言统计
            cursor.execute("""
                SELECT language_code, COUNT(*) as count
                FROM content_instances 
                GROUP BY language_code
                ORDER BY count DESC
                LIMIT 5
            """)
            lang_stats = cursor.fetchall()
            
            print(f"\n📊 语言统计:")
            for lang_code, count in lang_stats:
                print(f"  {lang_code}: {count} 条翻译")
                
            # 显示示例翻译
            cursor.execute("""
                SELECT content_key, content_source, language_code
                FROM content_instances 
                LIMIT 3
            """)
            samples = cursor.fetchall()
            
            print(f"\n📝 翻译示例:")
            for content_key, content_source, language_code in samples:
                print(f"  - {content_source} ({language_code}): {content_key}")
        else:
            print("❌ 翻译内容存储失败")
        
        return success
        
    except Exception as e:
        print(f"❌ 检查失败: {e}")
        return False
    finally:
        conn.close()

async def main():
    print("🚀 开始清理数据库并测试翻译内容存储")
    
    # 1. 清理数据库
    if not clean_database():
        return False
    
    # 2. 测试翻译存储
    success = await test_translation_storage()
    
    print(f"\n🎯 测试{'成功' if success else '失败'}")
    return success

if __name__ == "__main__":
    success = asyncio.run(main())
    exit(0 if success else 1)