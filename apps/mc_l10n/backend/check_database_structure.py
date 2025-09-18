#!/usr/bin/env python3
"""
数据库结构检查工具
用于诊断数据库架构问题
"""

import sqlite3
import sys
from pathlib import Path

def check_database_structure(db_path: str):
    """检查数据库结构完整性"""
    print(f"🔍 检查数据库: {db_path}")
    
    if not Path(db_path).exists():
        print(f"❌ 数据库文件不存在: {db_path}")
        return False
    
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    try:
        # 1. 检查表结构
        print("\n📊 数据库表:")
        cursor.execute("SELECT name, type FROM sqlite_master WHERE type='table' ORDER BY name")
        tables = cursor.fetchall()
        for name, table_type in tables:
            cursor.execute(f"SELECT COUNT(*) FROM {name}")
            count = cursor.fetchone()[0]
            print(f"  ✅ {name}: {count} 条记录")
        
        # 2. 检查视图
        print("\n👁 数据库视图:")
        cursor.execute("SELECT name FROM sqlite_master WHERE type='view' ORDER BY name")
        views = cursor.fetchall()
        if views:
            for (name,) in views:
                print(f"  ✅ {name}")
        else:
            print("  ❌ 无视图存在")
        
        # 3. 检查索引
        print("\n🔗 数据库索引:")
        cursor.execute("SELECT name FROM sqlite_master WHERE type='index' AND name NOT LIKE 'sqlite_%' ORDER BY name")
        indexes = cursor.fetchall()
        print(f"  📈 共 {len(indexes)} 个自定义索引")
        
        # 4. 检查触发器
        print("\n⚡ 数据库触发器:")
        cursor.execute("SELECT name FROM sqlite_master WHERE type='trigger' ORDER BY name")
        triggers = cursor.fetchall()
        for (name,) in triggers:
            print(f"  ✅ {name}")
        
        # 5. 统计信息
        print("\n📈 数据统计:")
        expected_tables = ['packs', 'pack_versions', 'mod_version_instances', 
                          'pack_mod_relations', 'content_instances', 'pack_content_relations']
        
        missing_tables = []
        for table in expected_tables:
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name=?", (table,))
            if not cursor.fetchone():
                missing_tables.append(table)
        
        if missing_tables:
            print(f"  ❌ 缺少表: {missing_tables}")
        else:
            print("  ✅ 所有核心表都存在")
        
        # 6. 检查pack_version_stats视图
        cursor.execute("SELECT name FROM sqlite_master WHERE type='view' AND name='pack_version_stats'")
        if cursor.fetchone():
            print("  ✅ pack_version_stats 视图存在")
        else:
            print("  ❌ pack_version_stats 视图缺失 - 这会导致数据库重建！")
        
        return True
        
    except Exception as e:
        print(f"❌ 检查失败: {e}")
        return False
    finally:
        conn.close()

if __name__ == "__main__":
    db_path = "data/mc_l10n.db"
    check_database_structure(db_path)