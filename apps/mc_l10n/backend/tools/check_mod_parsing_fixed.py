#!/usr/bin/env python3
"""检查模组解析问题的脚本（修正版）"""
import sqlite3

def check_mod_parsing():
    # 使用相对路径获取数据库位置
    from pathlib import Path
    project_root = Path(__file__).parent.parent
    db_path = project_root / "data" / "mc_l10n_v6.db"
    
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    print("🔍 检查模组解析问题...")
    print("=" * 80)
    
    # 检查所有表结构
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
    tables = cursor.fetchall()
    print("📋 数据库表结构:")
    for table in tables:
        table_name = table[0]
        cursor.execute(f"PRAGMA table_info({table_name})")
        columns = cursor.fetchall()
        print(f"\n  📊 {table_name}:")
        for col in columns:
            print(f"    {col[1]} ({col[2]})")
    print()
    
    # 检查core_mods表的实际数据
    cursor.execute("""
        SELECT name, modid, created_at 
        FROM core_mods 
        ORDER BY created_at DESC 
        LIMIT 15
    """)
    mods = cursor.fetchall()
    
    print("📦 最新15个模组的解析结果:")
    for mod in mods:
        name, modid, created_at = mod
        print(f"  名称: {name}")
        print(f"  ModID: {modid}") 
        print(f"  时间: {created_at}")
        
        # 检查是否有版本号在名称中的问题
        version_in_name = False
        if '-' in name:
            parts = name.split('-')
            for part in parts:
                # 检查是否包含版本号模式 (如 1.18.2, 0.5.2)
                if '.' in part and any(c.isdigit() for c in part):
                    version_in_name = True
                    break
        
        print(f"  问题: {'❌ 名称包含版本号' if version_in_name else '✅ 解析正常'}")
        print("-" * 50)
    
    # 统计有问题的模组数量（名称中包含版本号）
    cursor.execute("""
        SELECT COUNT(*) 
        FROM core_mods 
        WHERE name LIKE '%-%.%-%' OR name LIKE '%-%.%.%-%'
    """)
    problematic_count = cursor.fetchone()[0]
    
    print(f"🚨 疑似有问题的模组数量: {problematic_count}")
    
    # 检查具体的AI-Improvements案例
    cursor.execute("""
        SELECT name, modid 
        FROM core_mods 
        WHERE name LIKE '%AI-Improvements%'
    """)
    ai_mods = cursor.fetchall()
    
    if ai_mods:
        print("\n🔍 AI-Improvements模组案例:")
        for mod in ai_mods:
            print(f"  名称: {mod[0]} | ModID: {mod[1]}")
    
    # 总结统计
    cursor.execute("SELECT COUNT(*) FROM core_mods")
    total_mods = cursor.fetchone()[0]
    
    cursor.execute("SELECT COUNT(*) FROM core_language_files")
    total_files = cursor.fetchone()[0]
    
    cursor.execute("SELECT COUNT(*) FROM core_translation_entries")
    total_entries = cursor.fetchone()[0]
    
    print(f"\n📊 数据库统计:")
    print(f"  总模组数: {total_mods}")
    print(f"  总语言文件数: {total_files}")
    print(f"  总翻译条目数: {total_entries}")
    
    conn.close()

if __name__ == "__main__":
    check_mod_parsing()