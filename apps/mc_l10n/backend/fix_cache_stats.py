#!/usr/bin/env python3
"""
修复cache_stats表的列名问题
"""

import sqlite3

DB_PATH = "data/mc_l10n.db"

def fix_cache_stats_table():
    """修复cache_stats表结构"""
    
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    # 检查cache_stats表的当前结构
    cursor.execute("PRAGMA table_info(cache_stats)")
    columns = cursor.fetchall()
    
    print("=== 当前cache_stats表结构 ===")
    for col in columns:
        print(f"  {col[1]} {col[2]}")
    
    # 检查是否有'key'列存在
    column_names = [col[1] for col in columns]
    has_key_column = 'key' in column_names
    has_stat_key_column = 'stat_key' in column_names
    
    if has_key_column and not has_stat_key_column:
        print("\n=== 修复cache_stats表：将'key'列重命名为'stat_key' ===")
        
        # SQLite不支持直接重命名列，需要重建表
        cursor.execute("""
            CREATE TABLE cache_stats_new (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                stat_key TEXT NOT NULL,
                stat_value TEXT,
                category TEXT,
                session_id TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # 复制数据（如果有的话）
        cursor.execute("SELECT COUNT(*) FROM cache_stats")
        row_count = cursor.fetchone()[0]
        
        if row_count > 0:
            print(f"  复制 {row_count} 行数据...")
            cursor.execute("""
                INSERT INTO cache_stats_new (stat_key, stat_value, category, session_id, created_at, updated_at)
                SELECT key, value, category, session_id, created_at, updated_at 
                FROM cache_stats
            """)
        
        # 删除旧表并重命名新表
        cursor.execute("DROP TABLE cache_stats")
        cursor.execute("ALTER TABLE cache_stats_new RENAME TO cache_stats")
        
        print("  ✓ cache_stats表结构已修复")
        
    elif has_stat_key_column:
        print("\n✓ cache_stats表已经有正确的stat_key列")
    else:
        print("\n❌ cache_stats表结构异常，需要手动检查")
    
    # 创建索引
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_cache_stats_key ON cache_stats(stat_key)")
    print("✓ 已创建cache_stats索引")
    
    conn.commit()
    conn.close()
    
    print("\n=== 修复完成 ===")

if __name__ == "__main__":
    fix_cache_stats_table()