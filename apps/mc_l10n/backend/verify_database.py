#!/usr/bin/env python3
"""验证v2.1数据库结构"""

import sqlite3
from pathlib import Path

def verify_database():
    db_path = Path(__file__).parent / "data" / "mc_l10n_v2_1.db"
    
    if not db_path.exists():
        print(f"❌ 数据库文件不存在: {db_path}")
        return False
        
    conn = sqlite3.connect(str(db_path))
    cursor = conn.cursor()
    
    # 获取所有表名
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name")
    tables = [row[0] for row in cursor.fetchall()]
    
    expected_tables = [
        'packs', 'pack_versions', 'mod_version_instances', 
        'pack_mod_relations', 'content_instances', 'pack_content_relations'
    ]
    
    print("✅ v2.1数据库验证结果:")
    print(f"数据库路径: {db_path}")
    print(f"数据库大小: {db_path.stat().st_size} bytes")
    
    print(f"\n📋 创建的表 ({len(tables)}个):")
    for table in tables:
        print(f"  - {table}")
    
    print(f"\n🔍 关键表结构验证:")
    missing_tables = []
    for expected_table in expected_tables:
        if expected_table in tables:
            print(f"  ✅ {expected_table}")
            
            # 获取表结构
            cursor.execute(f"PRAGMA table_info({expected_table})")
            columns = cursor.fetchall()
            print(f"     字段数: {len(columns)}")
            
            # 获取索引
            cursor.execute(f"PRAGMA index_list({expected_table})")
            indexes = cursor.fetchall()
            print(f"     索引数: {len(indexes)}")
            
        else:
            missing_tables.append(expected_table)
            print(f"  ❌ {expected_table} (缺失)")
    
    if missing_tables:
        print(f"\n⚠️ 缺失的表: {missing_tables}")
        success = False
    else:
        print("\n🎉 所有预期的表都已创建!")
        success = True
        
    # 验证统计视图
    print(f"\n📊 统计视图验证:")
    try:
        cursor.execute("SELECT * FROM pack_version_stats LIMIT 1")
        print("  ✅ pack_version_stats 视图")
    except sqlite3.Error as e:
        print(f"  ❌ pack_version_stats 视图: {e}")
        success = False
    
    conn.close()
    return success

if __name__ == "__main__":
    success = verify_database()
    print(f"\n{'✅ 验证通过' if success else '❌ 验证失败'}")