#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
初始化干净的数据库
"""

import sqlite3
from pathlib import Path

def init_database(db_path: str = "mc_l10n.db"):
    """初始化数据库表结构"""
    
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    try:
        # 创建 mods 表
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS mods (
                mod_id TEXT PRIMARY KEY,
                name TEXT NOT NULL,
                display_name TEXT,
                version TEXT,
                minecraft_version TEXT,
                mod_loader TEXT,
                file_path TEXT,
                file_hash TEXT,
                metadata TEXT,
                scan_result TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # 创建索引
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_mods_name ON mods(name)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_mods_loader ON mods(mod_loader)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_mods_mc_version ON mods(minecraft_version)")
        
        # 创建 language_files 表
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS language_files (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                mod_id TEXT NOT NULL,
                language_code TEXT NOT NULL,
                file_path TEXT NOT NULL,
                content TEXT,
                translation_count INTEGER DEFAULT 0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (mod_id) REFERENCES mods(mod_id) ON DELETE CASCADE
            )
        """)
        
        # 创建索引
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_lang_files_mod_id ON language_files(mod_id)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_lang_files_code ON language_files(language_code)")
        
        # 创建 translation_entries 表
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS translation_entries (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                mod_id TEXT NOT NULL,
                language_file_id INTEGER NOT NULL,
                translation_key TEXT NOT NULL,
                original_text TEXT,
                translated_text TEXT,
                status TEXT DEFAULT 'pending',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (mod_id) REFERENCES mods(mod_id) ON DELETE CASCADE,
                FOREIGN KEY (language_file_id) REFERENCES language_files(id) ON DELETE CASCADE
            )
        """)
        
        # 创建索引
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_trans_entries_mod_id ON translation_entries(mod_id)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_trans_entries_key ON translation_entries(translation_key)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_trans_entries_status ON translation_entries(status)")
        
        # 创建 scan_sessions 表
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS scan_sessions (
                scan_id TEXT PRIMARY KEY,
                status TEXT NOT NULL,
                path TEXT,
                target_path TEXT,
                game_type TEXT,
                scan_mode TEXT,
                started_at TIMESTAMP,
                completed_at TIMESTAMP,
                progress_percent REAL DEFAULT 0,
                total_files INTEGER DEFAULT 0,
                processed_files INTEGER DEFAULT 0,
                processed_count INTEGER DEFAULT 0,
                total_count INTEGER DEFAULT 0,
                current_item TEXT,
                error_message TEXT,
                statistics TEXT
            )
        """)
        
        conn.commit()
        print(f"✅ 数据库初始化成功: {db_path}")
        
        # 显示表信息
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
        tables = cursor.fetchall()
        print(f"\n创建的表:")
        for table in tables:
            cursor.execute(f"SELECT COUNT(*) FROM {table[0]}")
            count = cursor.fetchone()[0]
            print(f"  - {table[0]}: {count} 条记录")
        
    except Exception as e:
        print(f"❌ 数据库初始化失败: {e}")
        conn.rollback()
        raise
    finally:
        conn.close()

if __name__ == '__main__':
    init_database()