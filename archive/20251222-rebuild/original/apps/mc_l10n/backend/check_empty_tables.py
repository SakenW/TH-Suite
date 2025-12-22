#!/usr/bin/env python3
"""
检查数据库中空表的状态
"""
import sqlite3
import os
from pathlib import Path

def check_database_tables():
    """检查数据库表状态"""
    db_path = Path(__file__).parent / "data" / "mc_l10n_v6.db"
    
    if not db_path.exists():
        print(f"❌ 数据库文件不存在: {db_path}")
        return
    
    print(f"📂 数据库路径: {db_path}")
    print("=" * 60)
    
    try:
        with sqlite3.connect(str(db_path)) as conn:
            cursor = conn.cursor()
            
            # 获取所有表
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name")
            tables = [row[0] for row in cursor.fetchall()]
            
            print(f"📊 总共找到 {len(tables)} 个表")
            print()
            
            # 分类表
            empty_tables = []
            non_empty_tables = []
            
            for table in tables:
                try:
                    cursor.execute(f"SELECT COUNT(*) FROM {table}")
                    count = cursor.fetchone()[0]
                    
                    if count == 0:
                        empty_tables.append(table)
                    else:
                        non_empty_tables.append((table, count))
                        
                except Exception as e:
                    print(f"⚠️ 无法检查表 {table}: {e}")
            
            # 显示有数据的表
            if non_empty_tables:
                print("✅ 有数据的表:")
                for table, count in sorted(non_empty_tables, key=lambda x: x[1], reverse=True):
                    print(f"  - {table}: {count:,} 条记录")
                print()
            
            # 显示空表
            if empty_tables:
                print("📋 空表列表:")
                for table in sorted(empty_tables):
                    print(f"  - {table}")
                print(f"\n总共 {len(empty_tables)} 个空表")
            else:
                print("✅ 没有空表")
            
            print("=" * 60)
            
            # 特别关注您提到的表
            mentioned_tables = [
                'cache_scan_results', 'cfg_file_watch', 'core_pack_installations',
                'core_pack_items', 'core_pack_versions', 'core_packs', 
                'core_projects', 'ops_cas_objects', 'ops_outbox_journal', 
                'ops_sync_log', 'ops_work_queue'
            ]
            
            print("🔍 您提到的表状态:")
            for table in mentioned_tables:
                if table in tables:
                    cursor.execute(f"SELECT COUNT(*) FROM {table}")
                    count = cursor.fetchone()[0]
                    status = "空" if count == 0 else f"{count} 条记录"
                    print(f"  - {table}: {status}")
                else:
                    print(f"  - {table}: 表不存在")
            
    except Exception as e:
        print(f"❌ 数据库操作失败: {e}")

if __name__ == "__main__":
    check_database_tables()