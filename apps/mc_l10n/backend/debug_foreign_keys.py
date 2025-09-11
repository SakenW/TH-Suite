#!/usr/bin/env python3
"""
调试数据库外键约束失败问题
分析core_language_files表的外键约束和数据
"""
import sqlite3
from pathlib import Path

def analyze_database():
    """分析数据库架构和外键约束"""
    db_path = Path("data/mc_l10n_v6.db")
    if not db_path.exists():
        print("❌ 数据库文件不存在")
        return
    
    conn = sqlite3.connect(str(db_path))
    cursor = conn.cursor()
    
    print("=== 数据库外键约束分析 ===")
    
    # 1. 检查core_language_files表结构
    print("\n📋 core_language_files 表结构:")
    cursor.execute("PRAGMA table_info(core_language_files)")
    columns = cursor.fetchall()
    for col in columns:
        print(f"  {col[1]} ({col[2]}) {'NOT NULL' if col[3] else ''}")
    
    # 2. 检查外键约束
    print("\n🔗 core_language_files 外键约束:")
    cursor.execute("PRAGMA foreign_key_list(core_language_files)")
    fk_info = cursor.fetchall()
    for fk in fk_info:
        print(f"  外键: {fk[3]} -> {fk[2]}.{fk[4]} (删除规则: {fk[6]})")
    
    # 3. 检查数据统计
    print("\n📊 数据统计:")
    cursor.execute("SELECT COUNT(*) FROM core_mods")
    mod_count = cursor.fetchone()[0]
    print(f"  core_mods: {mod_count} 条记录")
    
    cursor.execute("SELECT COUNT(*) FROM core_language_files")
    file_count = cursor.fetchone()[0]
    print(f"  core_language_files: {file_count} 条记录")
    
    cursor.execute("SELECT COUNT(*) FROM core_translation_entries")
    entry_count = cursor.fetchone()[0]
    print(f"  core_translation_entries: {entry_count} 条记录")
    
    # 4. 检查存在孤立记录的情况
    print("\n🔍 外键完整性检查:")
    
    # 检查carrier_uid是否都有对应的core_mods记录
    cursor.execute("""
        SELECT COUNT(*) FROM core_language_files lf
        LEFT JOIN core_mods m ON lf.carrier_uid = m.uid
        WHERE m.uid IS NULL
    """)
    orphaned_files = cursor.fetchone()[0]
    print(f"  孤立的语言文件(无对应MOD): {orphaned_files} 条")
    
    if orphaned_files > 0:
        cursor.execute("""
            SELECT lf.uid, lf.carrier_uid, lf.rel_path 
            FROM core_language_files lf
            LEFT JOIN core_mods m ON lf.carrier_uid = m.uid
            WHERE m.uid IS NULL
            LIMIT 5
        """)
        orphaned_examples = cursor.fetchall()
        print("  孤立记录示例:")
        for example in orphaned_examples:
            print(f"    {example[0]}: carrier_uid={example[1]}, path={example[2]}")
    
    # 5. 检查core_translation_entries的外键
    cursor.execute("""
        SELECT COUNT(*) FROM core_translation_entries te
        LEFT JOIN core_language_files lf ON te.language_file_uid = lf.uid
        WHERE lf.uid IS NULL
    """)
    orphaned_entries = cursor.fetchone()[0]
    print(f"  孤立的翻译条目(无对应语言文件): {orphaned_entries} 条")
    
    # 6. 检查最近的记录是否有问题
    print("\n📝 最近创建的记录:")
    cursor.execute("""
        SELECT uid, carrier_uid, rel_path, discovered_at
        FROM core_language_files 
        ORDER BY discovered_at DESC 
        LIMIT 5
    """)
    recent_files = cursor.fetchall()
    for rf in recent_files:
        print(f"  {rf[0][:8]}... carrier_uid={rf[1][:8]}... path={rf[2]} time={rf[3]}")
        
        # 检查这个carrier_uid是否存在于core_mods中
        cursor.execute("SELECT uid FROM core_mods WHERE uid = ?", (rf[1],))
        mod_exists = cursor.fetchone()
        print(f"    → carrier对应的MOD存在: {'✓' if mod_exists else '✗'}")

    conn.close()

if __name__ == "__main__":
    analyze_database()