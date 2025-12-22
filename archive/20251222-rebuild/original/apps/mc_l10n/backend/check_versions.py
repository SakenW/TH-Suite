#!/usr/bin/env python3
"""检查数据库中的版本信息"""
import sqlite3

def check_versions():
    conn = sqlite3.connect("data/mc_l10n_v6.db")
    cursor = conn.cursor()
    
    print("=== core_mods 表结构 ===")
    cursor.execute("PRAGMA table_info(core_mods)")
    columns = cursor.fetchall()
    for col in columns:
        print(f"  {col[1]} ({col[2]})")
    
    print("\n=== core_mods 示例数据 ===")
    cursor.execute("SELECT modid, name, homepage FROM core_mods LIMIT 10")
    rows = cursor.fetchall()
    for row in rows:
        print(f"  modid: {row[0]}")
        print(f"  name: {row[1]}")
        print(f"  homepage: {row[2] if row[2] else 'None'}")
        print("  ---")
    
    print("\n=== core_mod_versions 表结构 ===")
    cursor.execute("PRAGMA table_info(core_mod_versions)")
    columns = cursor.fetchall()
    for col in columns:
        print(f"  {col[1]} ({col[2]})")
    
    print("\n=== core_mod_versions 数据 ===")
    cursor.execute("SELECT COUNT(*) FROM core_mod_versions")
    count = cursor.fetchone()[0]
    print(f"  数据行数: {count}")
    
    if count > 0:
        cursor.execute("SELECT * FROM core_mod_versions LIMIT 5")
        rows = cursor.fetchall()
        for row in rows:
            print(f"  {row}")
    
    print("\n=== 版本信息统计 ===")
    cursor.execute("SELECT COUNT(*) FROM core_mods")
    total_mods = cursor.fetchone()[0]
    print(f"  总MOD数: {total_mods}")
    
    cursor.execute("SELECT COUNT(*) FROM core_mod_versions")
    total_versions = cursor.fetchone()[0]
    print(f"  版本记录数: {total_versions}")
    print(f"  缺失版本记录: {total_mods - total_versions}")
    
    print("\n=== MOD名称示例（检查解析质量）===")
    cursor.execute("SELECT modid, name FROM core_mods WHERE name LIKE '%-%' OR name LIKE '%.%' LIMIT 10")
    problematic = cursor.fetchall()
    for modid, name in problematic:
        print(f"  {modid}: {name}")
    
    conn.close()

if __name__ == "__main__":
    check_versions()