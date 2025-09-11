#!/usr/bin/env python3
"""
调试扫描器的数据库连接问题
检查扫描器使用的是哪个数据库和表结构
"""
import sqlite3
from pathlib import Path
from core.ddd_scanner_simple import get_scanner_instance
from database.core.manager import McL10nDatabaseManager

def debug_scanner_database():
    """调试扫描器的数据库连接"""
    print("=== 扫描器数据库连接调试 ===\n")
    
    # 1. 检查扫描器实例
    scanner = get_scanner_instance()
    print(f"扫描器数据库路径: {scanner.database_path}")
    
    # 2. 直接检查扫描器使用的数据库
    print(f"\n扫描器数据库文件是否存在: {Path(scanner.database_path).exists()}")
    
    try:
        conn = sqlite3.connect(scanner.database_path)
        cursor = conn.cursor()
        
        # 查看所有表
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
        tables = cursor.fetchall()
        print(f"\n扫描器数据库中的表:")
        for table in tables:
            print(f"  - {table[0]}")
        
        # 检查是否有mods表
        table_names = [table[0] for table in tables]
        if 'mods' in table_names:
            print("  ❌ 发现旧的'mods'表！")
        if 'core_mods' in table_names:
            print("  ✅ 发现V6的'core_mods'表")
        
        conn.close()
        
    except Exception as e:
        print(f"❌ 检查扫描器数据库失败: {e}")
    
    # 3. 检查数据库管理器
    print(f"\n=== 数据库管理器调试 ===")
    db_manager = McL10nDatabaseManager()
    print(f"数据库管理器路径: {db_manager.db_path}")
    
    try:
        with db_manager.get_connection() as conn:
            cursor = conn.cursor()
            
            # 查看所有表
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
            tables = cursor.fetchall()
            print(f"\n数据库管理器的表:")
            for table in tables:
                print(f"  - {table[0]}")
                
    except Exception as e:
        print(f"❌ 检查数据库管理器失败: {e}")
    
    # 4. 检查两者是否指向同一文件
    print(f"\n=== 路径对比 ===")
    scanner_path = Path(scanner.database_path).resolve()
    manager_path = Path(db_manager.db_path).resolve()
    
    print(f"扫描器路径: {scanner_path}")
    print(f"管理器路径: {manager_path}")
    print(f"是否同一文件: {scanner_path == manager_path}")

if __name__ == "__main__":
    debug_scanner_database()