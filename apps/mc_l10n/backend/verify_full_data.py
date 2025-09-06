#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""验证完整数据库内容"""

import sqlite3
from pathlib import Path

db_path = Path(__file__).parent / "mc_l10n.db"

conn = sqlite3.connect(db_path)
cursor = conn.cursor()

print("="*60)
print("  数据库内容验证")
print("="*60)

# 统计各表记录数
tables = ['mods', 'language_files', 'translation_entries', 'scan_sessions']
for table in tables:
    cursor.execute(f"SELECT COUNT(*) FROM {table}")
    count = cursor.fetchone()[0]
    print(f"\n{table}: {count} 条记录")
    
    if table == 'language_files' and count > 0:
        # 显示语言分布
        cursor.execute("""
            SELECT language_code, COUNT(*) as count 
            FROM language_files 
            GROUP BY language_code 
            ORDER BY count DESC 
            LIMIT 10
        """)
        print("  语言分布:")
        for lang, cnt in cursor.fetchall():
            print(f"    {lang}: {cnt} 个文件")
    
    elif table == 'translation_entries' and count > 0:
        # 显示翻译统计
        cursor.execute("""
            SELECT status, COUNT(*) as count 
            FROM translation_entries 
            GROUP BY status
        """)
        print("  翻译状态:")
        for status, cnt in cursor.fetchall():
            print(f"    {status}: {cnt} 条")
        
        # 显示翻译最多的MOD
        cursor.execute("""
            SELECT mod_id, COUNT(*) as count 
            FROM translation_entries 
            GROUP BY mod_id 
            ORDER BY count DESC 
            LIMIT 5
        """)
        print("  翻译最多的MOD:")
        for mod_id, cnt in cursor.fetchall():
            print(f"    {mod_id}: {cnt} 条翻译")
    
    elif table == 'scan_sessions' and count > 0:
        # 显示扫描会话
        cursor.execute("""
            SELECT scan_id, status, statistics
            FROM scan_sessions 
            ORDER BY started_at DESC 
            LIMIT 1
        """)
        result = cursor.fetchone()
        if result:
            print(f"  最新会话: {result[0]}")
            print(f"  状态: {result[1]}")
            if result[2]:
                import json
                stats = json.loads(result[2])
                print(f"  统计: {stats}")

# 显示一些具体的翻译示例
print("\n" + "="*60)
print("  翻译示例")
print("="*60)
cursor.execute("""
    SELECT te.translation_key, te.original_text, lf.language_code, te.mod_id
    FROM translation_entries te
    JOIN language_files lf ON te.language_file_id = lf.id
    WHERE te.original_text != '' 
    LIMIT 5
""")

for key, text, lang, mod_id in cursor.fetchall():
    print(f"\n模组: {mod_id}")
    print(f"语言: {lang}")
    print(f"键值: {key}")
    print(f"文本: {text[:100]}..." if len(text) > 100 else f"文本: {text}")

conn.close()