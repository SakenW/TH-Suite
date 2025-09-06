#!/usr/bin/env python3
"""
统一数据库管理系统
解决数据库结构不一致和数据存储问题
"""

import sqlite3
import hashlib
import json
import os
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Optional, Tuple, Any
import uuid
import logging

# 配置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class UnifiedDatabase:
    """统一的数据库管理器"""
    
    def __init__(self, db_path: str = None):
        """初始化数据库管理器"""
        if db_path is None:
            db_path = Path(__file__).parent / "mc_l10n.db"
        
        self.db_path = Path(db_path)
        self.conn = None
        self.ensure_database()
    
    def ensure_database(self):
        """确保数据库存在并具有正确的结构"""
        try:
            self.conn = sqlite3.connect(str(self.db_path))
            self.conn.row_factory = sqlite3.Row
            
            # 检查是否需要初始化或升级
            if not self.check_schema():
                logger.info("数据库结构不完整，正在初始化...")
                self.initialize_schema()
            else:
                # 检查是否需要升级
                if self.needs_upgrade():
                    logger.info("数据库需要升级，正在执行迁移...")
                    self.upgrade_schema()
            
            logger.info(f"数据库就绪: {self.db_path}")
            
        except Exception as e:
            logger.error(f"数据库初始化失败: {e}")
            raise
    
    def check_schema(self) -> bool:
        """检查数据库结构是否完整"""
        cursor = self.conn.cursor()
        
        # 检查必要的表是否存在
        required_tables = ['mods', 'language_files', 'translation_entries', 'scan_sessions']
        
        for table in required_tables:
            cursor.execute(
                "SELECT name FROM sqlite_master WHERE type='table' AND name=?",
                (table,)
            )
            if not cursor.fetchone():
                return False
        
        return True
    
    def needs_upgrade(self) -> bool:
        """检查是否需要升级数据库"""
        cursor = self.conn.cursor()
        
        # 检查关键列是否存在
        checks = [
            ('mods', 'file_size'),
            ('language_files', 'locale_code'),
            ('scan_sessions', 'scan_mode')
        ]
        
        for table, column in checks:
            cursor.execute(f"PRAGMA table_info({table})")
            columns = [col[1] for col in cursor.fetchall()]
            if column not in columns:
                return True
        
        return False
    
    def initialize_schema(self):
        """初始化数据库结构"""
        cursor = self.conn.cursor()
        
        # 1. 扫描会话表
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS scan_sessions (
                scan_id TEXT PRIMARY KEY,
                directory TEXT NOT NULL,
                started_at TEXT NOT NULL,
                completed_at TEXT,
                status TEXT DEFAULT 'scanning',
                scan_mode TEXT DEFAULT 'incremental',
                total_mods INTEGER DEFAULT 0,
                total_language_files INTEGER DEFAULT 0,
                total_keys INTEGER DEFAULT 0,
                error_message TEXT
            )
        """)
        
        # 2. 模组表
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS mods (
                mod_id TEXT PRIMARY KEY,
                display_name TEXT,
                version TEXT,
                description TEXT,
                mod_loader TEXT,
                authors TEXT,
                file_path TEXT,
                file_size INTEGER DEFAULT 0,
                file_hash TEXT,
                first_discovered TEXT,
                last_updated TEXT,
                scan_id TEXT,
                FOREIGN KEY (scan_id) REFERENCES scan_sessions(scan_id)
            )
        """)
        
        # 3. 语言文件表
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS language_files (
                file_id TEXT PRIMARY KEY,
                mod_id TEXT NOT NULL,
                locale_code TEXT NOT NULL,
                namespace TEXT DEFAULT 'minecraft',
                file_path TEXT,
                key_count INTEGER DEFAULT 0,
                content_hash TEXT,
                created_at TEXT,
                updated_at TEXT,
                FOREIGN KEY (mod_id) REFERENCES mods(mod_id) ON DELETE CASCADE
            )
        """)
        
        # 4. 翻译条目表
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS translation_entries (
                entry_id TEXT PRIMARY KEY,
                file_id TEXT NOT NULL,
                entry_key TEXT NOT NULL,
                entry_value TEXT,
                created_at TEXT,
                updated_at TEXT,
                FOREIGN KEY (file_id) REFERENCES language_files(file_id) ON DELETE CASCADE
            )
        """)
        
        # 5. 创建索引
        indexes = [
            "CREATE INDEX IF NOT EXISTS idx_mods_scan ON mods(scan_id)",
            "CREATE INDEX IF NOT EXISTS idx_mods_name ON mods(display_name)",
            "CREATE INDEX IF NOT EXISTS idx_language_files_mod ON language_files(mod_id)",
            "CREATE INDEX IF NOT EXISTS idx_language_files_locale ON language_files(locale_code)",
            "CREATE INDEX IF NOT EXISTS idx_translation_entries_file ON translation_entries(file_id)",
            "CREATE INDEX IF NOT EXISTS idx_translation_entries_key ON translation_entries(entry_key)"
        ]
        
        for index_sql in indexes:
            cursor.execute(index_sql)
        
        self.conn.commit()
        logger.info("数据库结构初始化完成")
    
    def upgrade_schema(self):
        """升级数据库结构"""
        cursor = self.conn.cursor()
        
        try:
            # 添加缺失的列
            upgrades = [
                ("ALTER TABLE mods ADD COLUMN file_size INTEGER DEFAULT 0", "mods", "file_size"),
                ("ALTER TABLE mods ADD COLUMN file_hash TEXT", "mods", "file_hash"),
                ("ALTER TABLE language_files ADD COLUMN locale_code TEXT DEFAULT 'en_us'", "language_files", "locale_code"),
                ("ALTER TABLE scan_sessions ADD COLUMN scan_mode TEXT DEFAULT 'incremental'", "scan_sessions", "scan_mode"),
                ("ALTER TABLE scan_sessions ADD COLUMN error_message TEXT", "scan_sessions", "error_message")
            ]
            
            for sql, table, column in upgrades:
                # 检查列是否已存在
                cursor.execute(f"PRAGMA table_info({table})")
                columns = [col[1] for col in cursor.fetchall()]
                if column not in columns:
                    cursor.execute(sql)
                    logger.info(f"添加列: {table}.{column}")
            
            self.conn.commit()
            logger.info("数据库升级完成")
            
        except Exception as e:
            logger.error(f"数据库升级失败: {e}")
            self.conn.rollback()
            raise
    
    def create_scan_session(self, directory: str, scan_mode: str = 'incremental') -> str:
        """创建扫描会话"""
        scan_id = str(uuid.uuid4())
        now = datetime.now().isoformat()
        
        cursor = self.conn.cursor()
        cursor.execute("""
            INSERT INTO scan_sessions 
            (scan_id, directory, started_at, status, scan_mode)
            VALUES (?, ?, ?, 'scanning', ?)
        """, (scan_id, directory, now, scan_mode))
        
        self.conn.commit()
        return scan_id
    
    def save_mod(self, scan_id: str, mod_info: Dict) -> str:
        """保存模组信息"""
        cursor = self.conn.cursor()
        now = datetime.now().isoformat()
        
        # 生成模组ID
        mod_id = mod_info.get('mod_id', str(uuid.uuid4()))
        
        # 准备数据
        display_name = mod_info.get('name', mod_info.get('mod_id', 'Unknown'))
        version = mod_info.get('version', 'unknown')
        description = mod_info.get('description', '')
        mod_loader = mod_info.get('mod_loader', '')
        authors = json.dumps(mod_info.get('authors', []))
        file_path = mod_info.get('file_path', '')
        file_size = mod_info.get('file_size', 0)
        file_hash = mod_info.get('file_hash', '')
        
        # 检查是否已存在
        cursor.execute("SELECT mod_id FROM mods WHERE mod_id = ?", (mod_id,))
        exists = cursor.fetchone()
        
        if exists:
            # 更新现有记录
            cursor.execute("""
                UPDATE mods SET 
                    display_name = ?, version = ?, description = ?,
                    mod_loader = ?, authors = ?, file_path = ?,
                    file_size = ?, file_hash = ?, last_updated = ?,
                    scan_id = ?
                WHERE mod_id = ?
            """, (display_name, version, description, mod_loader, authors,
                  file_path, file_size, file_hash, now, scan_id, mod_id))
        else:
            # 插入新记录
            cursor.execute("""
                INSERT INTO mods 
                (mod_id, display_name, version, description, mod_loader, authors,
                 file_path, file_size, file_hash, first_discovered, last_updated, scan_id)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (mod_id, display_name, version, description, mod_loader, authors,
                  file_path, file_size, file_hash, now, now, scan_id))
        
        self.conn.commit()
        return mod_id
    
    def save_language_file(self, mod_id: str, lang_info: Dict) -> str:
        """保存语言文件"""
        cursor = self.conn.cursor()
        now = datetime.now().isoformat()
        
        # 生成文件ID
        file_id = str(uuid.uuid4())
        
        # 准备数据
        locale_code = lang_info.get('locale', 'en_us')
        namespace = lang_info.get('namespace', 'minecraft')
        file_path = lang_info.get('file_path', '')
        key_count = lang_info.get('key_count', 0)
        content_hash = lang_info.get('content_hash', '')
        
        # 检查是否已存在相同的语言文件
        cursor.execute("""
            SELECT file_id FROM language_files 
            WHERE mod_id = ? AND locale_code = ? AND namespace = ?
        """, (mod_id, locale_code, namespace))
        
        existing = cursor.fetchone()
        
        if existing:
            file_id = existing[0]
            # 更新现有记录
            cursor.execute("""
                UPDATE language_files SET 
                    file_path = ?, key_count = ?, content_hash = ?, updated_at = ?
                WHERE file_id = ?
            """, (file_path, key_count, content_hash, now, file_id))
        else:
            # 插入新记录
            cursor.execute("""
                INSERT INTO language_files 
                (file_id, mod_id, locale_code, namespace, file_path, 
                 key_count, content_hash, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (file_id, mod_id, locale_code, namespace, file_path,
                  key_count, content_hash, now, now))
        
        self.conn.commit()
        return file_id
    
    def save_translation_entries(self, file_id: str, entries: Dict):
        """保存翻译条目"""
        cursor = self.conn.cursor()
        now = datetime.now().isoformat()
        
        # 首先删除该文件的所有旧条目
        cursor.execute("DELETE FROM translation_entries WHERE file_id = ?", (file_id,))
        
        # 批量插入新条目
        for key, value in entries.items():
            entry_id = str(uuid.uuid4())
            cursor.execute("""
                INSERT INTO translation_entries 
                (entry_id, file_id, entry_key, entry_value, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (entry_id, file_id, key, str(value), now, now))
        
        self.conn.commit()
    
    def complete_scan_session(self, scan_id: str, stats: Dict = None, error: str = None):
        """完成扫描会话"""
        cursor = self.conn.cursor()
        now = datetime.now().isoformat()
        
        if error:
            cursor.execute("""
                UPDATE scan_sessions 
                SET completed_at = ?, status = 'failed', error_message = ?
                WHERE scan_id = ?
            """, (now, error, scan_id))
        else:
            status = 'completed'
            total_mods = stats.get('total_mods', 0) if stats else 0
            total_language_files = stats.get('total_language_files', 0) if stats else 0
            total_keys = stats.get('total_keys', 0) if stats else 0
            
            cursor.execute("""
                UPDATE scan_sessions 
                SET completed_at = ?, status = ?, total_mods = ?, 
                    total_language_files = ?, total_keys = ?
                WHERE scan_id = ?
            """, (now, status, total_mods, total_language_files, total_keys, scan_id))
        
        self.conn.commit()
    
    def get_statistics(self) -> Dict:
        """获取数据库统计信息"""
        cursor = self.conn.cursor()
        
        stats = {}
        
        # 模组总数
        cursor.execute("SELECT COUNT(*) FROM mods")
        stats['total_mods'] = cursor.fetchone()[0]
        
        # 语言文件总数
        cursor.execute("SELECT COUNT(*) FROM language_files")
        stats['total_language_files'] = cursor.fetchone()[0]
        
        # 翻译条目总数
        cursor.execute("SELECT COUNT(*) FROM translation_entries")
        stats['total_keys'] = cursor.fetchone()[0]
        
        # 语言分布
        cursor.execute("""
            SELECT locale_code, COUNT(*) as count 
            FROM language_files 
            GROUP BY locale_code 
            ORDER BY count DESC
        """)
        stats['language_distribution'] = dict(cursor.fetchall())
        
        # 最近的扫描
        cursor.execute("""
            SELECT scan_id, directory, started_at, completed_at, status, 
                   total_mods, total_language_files, total_keys
            FROM scan_sessions 
            ORDER BY started_at DESC 
            LIMIT 5
        """)
        
        recent_scans = []
        for row in cursor.fetchall():
            recent_scans.append(dict(row))
        stats['recent_scans'] = recent_scans
        
        return stats
    
    def close(self):
        """关闭数据库连接"""
        if self.conn:
            self.conn.close()
    
    def __enter__(self):
        """上下文管理器入口"""
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """上下文管理器出口"""
        self.close()


def test_database():
    """测试数据库功能"""
    with UnifiedDatabase() as db:
        # 创建扫描会话
        scan_id = db.create_scan_session("/test/mods", "full")
        print(f"创建扫描会话: {scan_id}")
        
        # 保存模组
        mod_info = {
            'mod_id': 'test_mod',
            'name': 'Test Mod',
            'version': '1.0.0',
            'description': 'A test mod',
            'mod_loader': 'forge',
            'authors': ['TestAuthor'],
            'file_path': '/test/mods/test.jar',
            'file_size': 1024
        }
        mod_id = db.save_mod(scan_id, mod_info)
        print(f"保存模组: {mod_id}")
        
        # 保存语言文件
        lang_info = {
            'locale': 'en_us',
            'namespace': 'test_mod',
            'file_path': 'assets/test_mod/lang/en_us.json',
            'key_count': 2
        }
        file_id = db.save_language_file(mod_id, lang_info)
        print(f"保存语言文件: {file_id}")
        
        # 保存翻译条目
        entries = {
            'item.test_mod.test_item': 'Test Item',
            'block.test_mod.test_block': 'Test Block'
        }
        db.save_translation_entries(file_id, entries)
        print("保存翻译条目")
        
        # 完成扫描
        stats = {
            'total_mods': 1,
            'total_language_files': 1,
            'total_keys': 2
        }
        db.complete_scan_session(scan_id, stats)
        print("完成扫描会话")
        
        # 获取统计
        statistics = db.get_statistics()
        print("\n数据库统计:")
        print(f"  模组总数: {statistics['total_mods']}")
        print(f"  语言文件总数: {statistics['total_language_files']}")
        print(f"  翻译条目总数: {statistics['total_keys']}")


if __name__ == "__main__":
    test_database()