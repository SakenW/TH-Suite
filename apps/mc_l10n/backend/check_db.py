#!/usr/bin/env python3
"""检查数据库表和数据"""
import sqlite3

def check_database(db_path: str, name: str):
    print(f"\n=== 检查数据库: {name} ({db_path}) ===")
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # 获取所有表
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
        tables = cursor.fetchall()
        print(f"表数量: {len(tables)}")
        
        for table in tables:
            table_name = table[0]
            cursor.execute(f"SELECT COUNT(*) FROM {table_name}")
            count = cursor.fetchone()[0]
            
            # 获取表结构
            cursor.execute(f"PRAGMA table_info({table_name})")
            columns = cursor.fetchall()
            col_names = [col[1] for col in columns]
            
            print(f"  {table_name}: {count} 行, 字段: {', '.join(col_names[:5])}{'...' if len(col_names) > 5 else ''}")
        
        conn.close()
        
    except Exception as e:
        print(f"错误: {e}")

if __name__ == "__main__":
    # 检查V6数据库
    check_database("data/mc_l10n_v6.db", "V6统一数据库")
    
    # 检查归档数据库（可选）
    import os
    archive_db = "archive/legacy_database/data/core_mc_l10n.db"
    if os.path.exists(archive_db):
        check_database(archive_db, "归档数据库（仅参考）")