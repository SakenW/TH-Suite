#!/usr/bin/env python3
"""
检查MC L10n V6数据库表结构
"""

import sqlite3
from pathlib import Path

def check_database():
    # 使用V6数据库路径
    db_path = Path(__file__).parent / "data" / "mc_l10n_v6.db"
    
    if not db_path.exists():
        print(f"❌ 数据库文件不存在: {db_path}")
        return
    
    print(f"✅ 检查数据库: {db_path}")
    
    try:
        conn = sqlite3.connect(str(db_path))
        cursor = conn.cursor()
        
        # 获取所有表名
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
        tables = cursor.fetchall()
        
        print(f"\n📊 数据库中的表 ({len(tables)} 个):")
        for i, (table,) in enumerate(tables, 1):
            print(f"  {i}. {table}")
        
        # 检查V6架构表状态
        table_names = [table[0] for table in tables]
        if 'mods' in table_names:
            print(f"\n⚠️ 检测到旧的'mods'表，应该迁移到V6架构")
        else:
            print(f"\n✅ 没有旧的'mods'表，使用V6架构")
            
        # 检查V6表是否存在
        v6_tables = ['core_mods', 'core_language_files', 'core_translation_entries']
        print(f"\n🔍 检查V6表结构:")
        for table in v6_tables:
            if table in table_names:
                print(f"  ✅ {table}")
                # 获取表结构
                cursor.execute(f"PRAGMA table_info({table})")
                columns = cursor.fetchall()
                for col in columns:
                    print(f"    - {col[1]} ({col[2]})")
            else:
                print(f"  ❌ {table}")
        
        # 统计数据
        print(f"\n📈 数据统计:")
        for table in ['core_mods', 'core_language_files', 'core_translation_entries']:
            if table in table_names:
                cursor.execute(f"SELECT COUNT(*) FROM {table}")
                count = cursor.fetchone()[0]
                print(f"  {table}: {count} 条记录")
                
        conn.close()
        
    except Exception as e:
        print(f"❌ 数据库检查失败: {e}")

if __name__ == "__main__":
    check_database()