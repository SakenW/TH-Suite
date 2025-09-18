#!/usr/bin/env python3
"""
修复cache_stats表的列名问题（正确版本）
根据实际表结构调整代码期望
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
    
    # 检查现有列名
    column_names = [col[1] for col in columns]
    
    print(f"\n=== 发现的列名: {column_names} ===")
    
    # 当前表结构: id, stats_type, stats_key, stats_data, valid_until, created_at
    # 扫描规则期望: id, stat_key, stat_value, category, session_id, created_at, updated_at
    
    if 'stats_key' in column_names and 'stats_data' in column_names:
        print("\n=== 发现现有cache_stats表，需要重建为扫描规则规范 ===")
        
        # 备份现有数据
        cursor.execute("SELECT COUNT(*) FROM cache_stats")
        row_count = cursor.fetchone()[0]
        print(f"  当前数据行数: {row_count}")
        
        if row_count > 0:
            print("  备份现有数据...")
            cursor.execute("CREATE TABLE cache_stats_backup AS SELECT * FROM cache_stats")
        
        # 删除旧表
        cursor.execute("DROP TABLE cache_stats")
        print("  ✓ 删除旧表")
        
        # 创建符合扫描规则的新表
        cursor.execute("""
            CREATE TABLE cache_stats (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                stat_key TEXT NOT NULL,
                stat_value TEXT,
                category TEXT,
                session_id TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        print("  ✓ 创建新表结构")
        
        # 如果有备份数据，尝试迁移
        if row_count > 0:
            try:
                cursor.execute("""
                    INSERT INTO cache_stats (stat_key, stat_value, category, session_id, created_at, updated_at)
                    SELECT 
                        stats_key,
                        stats_data,
                        stats_type,
                        NULL,  -- session_id 在旧数据中不存在
                        created_at,
                        created_at  -- updated_at 使用 created_at
                    FROM cache_stats_backup
                """)
                print(f"  ✓ 迁移了 {cursor.rowcount} 行数据")
            except Exception as e:
                print(f"  ⚠️  数据迁移失败: {e}")
                print("  可以手动检查 cache_stats_backup 表")
        
    elif 'stat_key' in column_names:
        print("\n✓ cache_stats表已经符合扫描规则规范")
    else:
        print("\n❌ cache_stats表结构异常，无法识别")
        return False
    
    # 创建索引
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_cache_stats_key ON cache_stats(stat_key)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_cache_stats_session ON cache_stats(session_id)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_cache_stats_category ON cache_stats(category)")
    print("✓ 已创建cache_stats索引")
    
    conn.commit()
    
    # 验证新表结构
    cursor.execute("PRAGMA table_info(cache_stats)")
    new_columns = cursor.fetchall()
    
    print("\n=== 修复后cache_stats表结构 ===")
    for col in new_columns:
        print(f"  {col[1]} {col[2]}")
    
    conn.close()
    
    print("\n=== cache_stats表修复完成 ===")
    return True

if __name__ == "__main__":
    success = fix_cache_stats_table()
    exit(0 if success else 1)