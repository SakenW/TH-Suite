#!/usr/bin/env python3
"""
检查content_instances表结构
"""

import sqlite3
from pathlib import Path

def check_table_schema():
    """检查表结构"""
    db_path = Path("data/mc_l10n_v2_1.db")
    
    if not db_path.exists():
        print(f"❌ 数据库文件不存在: {db_path}")
        return
    
    conn = sqlite3.connect(str(db_path))
    try:
        cursor = conn.cursor()
        
        # 检查content_instances表结构
        cursor.execute("PRAGMA table_info(content_instances)")
        columns = cursor.fetchall()
        
        print("📋 content_instances表结构:")
        for column in columns:
            col_id, name, col_type, not_null, default_value, pk = column
            nullable = "NOT NULL" if not_null else "NULL"
            default = f" DEFAULT {default_value}" if default_value else ""
            primary = " PRIMARY KEY" if pk else ""
            print(f"  {name}: {col_type} {nullable}{default}{primary}")
        
        # 检查是否有file_format字段
        cursor.execute("SELECT sql FROM sqlite_master WHERE type='table' AND name='content_instances'")
        create_sql = cursor.fetchone()
        if create_sql:
            print(f"\n📝 建表语句:")
            print(create_sql[0])
        
    except Exception as e:
        print(f"❌ 检查失败: {e}")
    finally:
        conn.close()

if __name__ == "__main__":
    check_table_schema()