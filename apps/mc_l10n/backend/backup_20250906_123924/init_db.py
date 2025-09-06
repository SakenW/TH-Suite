"""
初始化数据库表结构
"""
import sqlite3
import os
from datetime import datetime

def init_database():
    """初始化数据库表"""
    db_path = 'mc_l10n.db'
    
    # 连接数据库
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    try:
        # 创建扫描会话表
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS scan_sessions (
            scan_id TEXT PRIMARY KEY,
            status TEXT NOT NULL DEFAULT 'pending',
            path TEXT NOT NULL,
            target_path TEXT NOT NULL,
            game_type TEXT DEFAULT 'minecraft',
            scan_mode TEXT DEFAULT 'full',
            started_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            completed_at TIMESTAMP,
            error_message TEXT,
            progress_percent REAL DEFAULT 0,
            total_files INTEGER DEFAULT 0,
            processed_files INTEGER DEFAULT 0,
            processed_count INTEGER DEFAULT 0,
            total_count INTEGER DEFAULT 0,
            total_mods INTEGER DEFAULT 0,
            total_language_files INTEGER DEFAULT 0,
            total_keys INTEGER DEFAULT 0,
            current_item TEXT,
            metadata TEXT
        )
        """)
        
        # 创建扫描进度表
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS scan_progress (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            scan_id TEXT NOT NULL,
            timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            progress_percent REAL,
            current_file TEXT,
            message TEXT,
            FOREIGN KEY (scan_id) REFERENCES scan_sessions(scan_id)
        )
        """)
        
        # 创建扫描结果表
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS scan_results (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            scan_id TEXT NOT NULL,
            mod_id TEXT,
            mod_name TEXT,
            mod_version TEXT,
            file_path TEXT,
            language_code TEXT,
            keys_count INTEGER,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (scan_id) REFERENCES scan_sessions(scan_id)
        )
        """)
        
        # 创建项目信息表
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS projects (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            project_id TEXT UNIQUE NOT NULL,
            name TEXT NOT NULL,
            path TEXT NOT NULL,
            game_type TEXT DEFAULT 'minecraft',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            last_scan_id TEXT,
            metadata TEXT
        )
        """)
        
        # 创建模组信息表
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS mods (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            mod_id TEXT UNIQUE NOT NULL,
            name TEXT NOT NULL,
            version TEXT,
            file_path TEXT,
            jar_name TEXT,
            loader_type TEXT,
            game_version TEXT,
            metadata TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        """)
        
        # 创建语言文件表
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS language_files (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            mod_id TEXT NOT NULL,
            language_code TEXT NOT NULL,
            file_path TEXT,
            content TEXT,
            keys_count INTEGER,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (mod_id) REFERENCES mods(mod_id)
        )
        """)
        
        # 创建索引以提高查询性能
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_scan_id ON scan_progress(scan_id)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_scan_results_scan_id ON scan_results(scan_id)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_mod_id ON language_files(mod_id)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_language_code ON language_files(language_code)")
        
        # 提交更改
        conn.commit()
        print(f"✅ 数据库初始化成功: {db_path}")
        
        # 显示创建的表
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
        tables = cursor.fetchall()
        print(f"📊 创建的表: {[t[0] for t in tables]}")
        
    except Exception as e:
        print(f"❌ 数据库初始化失败: {e}")
        conn.rollback()
        raise
    finally:
        conn.close()

if __name__ == "__main__":
    init_database()