"""
数据库初始化模块
创建和初始化数据库表结构
"""

import sqlite3
import logging
from pathlib import Path

logger = logging.getLogger(__name__)


def init_database(db_path: str = "mc_l10n.db"):
    """
    初始化数据库
    
    Args:
        db_path: 数据库文件路径
    """
    try:
        logger.info(f"开始初始化数据库: {db_path}")
        
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # 创建扫描会话表
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS scan_sessions (
                id TEXT PRIMARY KEY,
                directory TEXT NOT NULL,
                started_at TEXT NOT NULL,
                completed_at TEXT,
                status TEXT DEFAULT 'scanning',
                total_mods INTEGER DEFAULT 0,
                total_language_files INTEGER DEFAULT 0,
                total_keys INTEGER DEFAULT 0,
                scan_mode TEXT DEFAULT '全量'
            )
        """)
        
        # 创建模组信息表
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS mods (
                id TEXT PRIMARY KEY,
                scan_id TEXT,
                mod_id TEXT,
                display_name TEXT,
                version TEXT,
                file_path TEXT,
                size INTEGER,
                mod_loader TEXT,
                description TEXT,
                authors TEXT,
                FOREIGN KEY (scan_id) REFERENCES scan_sessions(id)
            )
        """)
        
        # 创建语言文件表
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS language_files (
                id TEXT PRIMARY KEY,
                scan_id TEXT,
                mod_id TEXT,
                namespace TEXT,
                locale_code TEXT,
                file_path TEXT,
                key_count INTEGER,
                FOREIGN KEY (scan_id) REFERENCES scan_sessions(id)
            )
        """)
        
        # 创建翻译条目表
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS translation_entries (
                id TEXT PRIMARY KEY,
                file_id TEXT,
                entry_key TEXT,
                source_text TEXT,
                translated_text TEXT,
                FOREIGN KEY (file_id) REFERENCES language_files(id)
            )
        """)
        
        # 创建文件哈希表，用于增量扫描
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS file_hashes (
                file_path TEXT PRIMARY KEY,
                file_hash TEXT NOT NULL,
                last_modified TIMESTAMP NOT NULL,
                file_size INTEGER NOT NULL,
                last_scanned TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # 创建索引
        try:
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_mods_mod_id ON mods(mod_id)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_language_files_mod_id ON language_files(mod_id)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_translation_entries_file_id ON translation_entries(file_id)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_translation_entries_key ON translation_entries(entry_key)")
        except Exception as e:
            logger.warning(f"创建索引时出现警告: {e}")
        
        conn.commit()
        conn.close()
        
        logger.info("数据库初始化完成")
        
    except Exception as e:
        logger.error(f"数据库初始化失败: {e}")
        raise