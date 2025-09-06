#!/usr/bin/env python3
import sqlite3

def check_database():
    db_path = 'mc_l10n.db'
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    tables = [
        'mods',
        'language_files', 
        'translation_entries',
        'scan_sessions',
        'translation_projects',
        'scan_discoveries'
    ]
    
    print(f"\n📊 数据库统计 ({db_path}):")
    print("=" * 50)
    
    for table in tables:
        try:
            cursor.execute(f"SELECT COUNT(*) FROM {table}")
            count = cursor.fetchone()[0]
            print(f"{table:25} : {count:,} 条记录")
        except sqlite3.OperationalError as e:
            print(f"{table:25} : 表不存在或错误 - {e}")
    
    # 查看最新的扫描会话
    print("\n📋 最新扫描会话:")
    print("-" * 50)
    try:
        cursor.execute("""
            SELECT scan_id, status, started_at, total_mods, total_language_files, total_keys
            FROM scan_sessions
            ORDER BY started_at DESC
            LIMIT 3
        """)
        sessions = cursor.fetchall()
        for session in sessions:
            print(f"ID: {session[0][:8]}... | 状态: {session[1]} | 时间: {session[2]}")
            print(f"   模组: {session[3] or 0} | 语言文件: {session[4] or 0} | 键值: {session[5] or 0}")
    except Exception as e:
        print(f"无法查询扫描会话: {e}")
    
    conn.close()

if __name__ == "__main__":
    check_database()
