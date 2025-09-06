#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""检查 mods 表数据完整性"""

import sqlite3
import json
from pathlib import Path
# from tabulate import tabulate  # 可选依赖

# 数据库路径
db_path = Path(__file__).parent.parent / "backend" / "mc_l10n.db"

def check_mods_table():
    """检查 mods 表的数据"""
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    
    print(f"数据库: {db_path}")
    print("=" * 80)
    
    # 获取表结构
    cursor.execute("PRAGMA table_info(mods)")
    columns = cursor.fetchall()
    print("\n表结构:")
    for col in columns:
        print(f"  {col['name']:20} {col['type']:15} {'NOT NULL' if col['notnull'] else 'NULL':10} {f'DEFAULT {col[4]}' if col[4] else ''}")
    
    print("\n" + "=" * 80)
    
    # 检查数据
    cursor.execute("""
        SELECT 
            mod_id,
            name,
            display_name,
            version,
            minecraft_version,
            mod_loader,
            SUBSTR(file_path, 1, 50) as file_path_short,
            file_hash,
            created_at,
            updated_at
        FROM mods
        LIMIT 10
    """)
    
    rows = cursor.fetchall()
    
    if rows:
        # 转换为列表格式
        data = []
        for row in rows:
            data.append([
                row['mod_id'][:20] if row['mod_id'] else 'NULL',
                row['name'][:20] if row['name'] else 'NULL',
                row['display_name'][:20] if row['display_name'] else 'NULL',
                row['version'][:15] if row['version'] else 'NULL',
                row['minecraft_version'][:10] if row['minecraft_version'] else 'NULL',
                row['mod_loader'] if row['mod_loader'] else 'NULL',
                row['file_path_short'] + '...' if row['file_path_short'] else 'NULL',
                row['file_hash'][:8] + '...' if row['file_hash'] else 'NULL',
            ])
        
        headers = ['mod_id', 'name', 'display_name', 'version', 'mc_version', 'loader', 'file_path', 'hash']
        print("\n前10条记录:")
        print("-" * 120)
        print(f"{'mod_id':<20} {'name':<20} {'display_name':<20} {'version':<15} {'mc_ver':<10} {'loader':<8}")
        print("-" * 120)
        for row_data in data:
            print(f"{row_data[0]:<20} {row_data[1]:<20} {row_data[2]:<20} {row_data[3]:<15} {row_data[4]:<10} {row_data[5]:<8}")
    
    # 检查数据质量
    print("\n" + "=" * 80)
    print("数据质量检查:")
    
    # 统计NULL值
    for col_info in columns:
        col_name = col_info['name']
        cursor.execute(f"SELECT COUNT(*) FROM mods WHERE {col_name} IS NULL")
        null_count = cursor.fetchone()[0]
        cursor.execute("SELECT COUNT(*) FROM mods")
        total_count = cursor.fetchone()[0]
        
        if null_count > 0:
            print(f"  {col_name:20} - NULL值: {null_count}/{total_count} ({null_count*100/total_count:.1f}%)")
    
    # 检查异常数据
    print("\n异常数据检查:")
    
    # 检查mod_id是否包含异常字符
    cursor.execute("""
        SELECT mod_id, name 
        FROM mods 
        WHERE mod_id LIKE '%#%' 
           OR mod_id LIKE '%"%'
           OR mod_id LIKE '%${%'
        LIMIT 5
    """)
    bad_mod_ids = cursor.fetchall()
    if bad_mod_ids:
        print("  发现异常的 mod_id:")
        for row in bad_mod_ids:
            print(f"    - {row[0][:50]}")
    
    # 检查version字段
    cursor.execute("""
        SELECT mod_id, version 
        FROM mods 
        WHERE version LIKE '%#mandatory%' 
           OR version LIKE '%${%'
           OR version LIKE '%"%'
        LIMIT 5
    """)
    bad_versions = cursor.fetchall()
    if bad_versions:
        print("  发现异常的 version:")
        for row in bad_versions:
            print(f"    - {row[0]}: {row[1][:50]}")
    
    conn.close()

if __name__ == "__main__":
    check_mods_table()