#!/usr/bin/env python3
"""
清理数据库中的演示数据
"""

import sqlite3
from pathlib import Path

def clear_demo_data():
    """清理数据库中的所有演示数据"""
    db_path = Path(__file__).parent / "data" / "mc_l10n_v6.db"
    
    if not db_path.exists():
        print("❌ 数据库文件不存在")
        return
    
    try:
        with sqlite3.connect(str(db_path)) as conn:
            cursor = conn.cursor()
            
            # 获取当前数据统计
            cursor.execute("SELECT COUNT(*) FROM core_mods")
            mods_count = cursor.fetchone()[0]
            
            cursor.execute("SELECT COUNT(*) FROM core_language_files")
            files_count = cursor.fetchone()[0]
            
            cursor.execute("SELECT COUNT(*) FROM core_translation_entries")
            entries_count = cursor.fetchone()[0]
            
            cursor.execute("SELECT COUNT(*) FROM cache_scan_results")
            cache_count = cursor.fetchone()[0]
            
            print(f"📊 清理前数据统计:")
            print(f"  - 模组: {mods_count}")
            print(f"  - 语言文件: {files_count}")
            print(f"  - 翻译条目: {entries_count}")
            print(f"  - 缓存记录: {cache_count}")
            
            if mods_count == 0 and files_count == 0 and entries_count == 0:
                print("✅ 数据库已经是空的，无需清理")
                return
            
            # 清理核心数据表（按依赖关系倒序删除）
            print("\n🧹 开始清理数据...")
            
            # 1. 清理翻译条目
            cursor.execute("DELETE FROM core_translation_entries")
            print(f"✅ 清理翻译条目: {cursor.rowcount} 条")
            
            # 2. 清理语言文件
            cursor.execute("DELETE FROM core_language_files")
            print(f"✅ 清理语言文件: {cursor.rowcount} 个")
            
            # 3. 清理模组版本
            cursor.execute("DELETE FROM core_mod_versions")
            print(f"✅ 清理模组版本: {cursor.rowcount} 个")
            
            # 4. 清理模组
            cursor.execute("DELETE FROM core_mods")
            print(f"✅ 清理模组: {cursor.rowcount} 个")
            
            # 5. 清理整合包相关数据
            cursor.execute("DELETE FROM core_pack_items")
            cursor.execute("DELETE FROM core_pack_installations") 
            cursor.execute("DELETE FROM core_pack_versions")
            cursor.execute("DELETE FROM core_packs")
            cursor.execute("DELETE FROM core_projects")
            print("✅ 清理整合包数据")
            
            # 6. 清理缓存数据
            cursor.execute("DELETE FROM cache_scan_results")
            print(f"✅ 清理缓存记录: {cache_count} 条")
            
            # 7. 清理运维数据
            cursor.execute("DELETE FROM ops_work_queue")
            cursor.execute("DELETE FROM ops_outbox_journal")
            cursor.execute("DELETE FROM ops_sync_log")
            cursor.execute("DELETE FROM ops_cas_objects")
            print("✅ 清理运维数据")
            
            # 8. 重置自增ID
            cursor.execute("DELETE FROM sqlite_sequence")
            print("✅ 重置自增ID序列")
            
            # 提交所有更改
            conn.commit()
            
            # 优化数据库
            cursor.execute("VACUUM")
            print("✅ 数据库优化完成")
            
            print(f"\n🎉 数据库清理完成！")
            print(f"📁 数据库路径: {db_path}")
            
    except Exception as e:
        print(f"❌ 清理失败: {e}")

if __name__ == "__main__":
    clear_demo_data()