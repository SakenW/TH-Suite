"""
数据库重构设计 - 解决重复数据问题

核心设计原则：
1. 使用内容哈希而非UUID作为主要标识
2. 基于文件内容而非文件路径进行去重
3. 实现UPSERT而非INSERT OR IGNORE
4. 分离扫描会话和实际内容数据
"""

import sqlite3
import hashlib
import json
from pathlib import Path
from typing import Dict, List, Optional, Tuple
from datetime import datetime

class DatabaseRedesign:
    """重新设计的数据库结构"""
    
    def __init__(self, db_path: str = "mc_l10n_v2.db"):
        self.db_path = db_path
        
    def create_new_schema(self):
        """创建新的数据库结构"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # === 1. 扫描会话表 (扩展支持组合包信息) ===
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS scan_sessions (
                id TEXT PRIMARY KEY,
                directory TEXT NOT NULL,
                started_at TEXT NOT NULL,
                completed_at TEXT,
                status TEXT DEFAULT 'scanning',
                scan_mode TEXT DEFAULT '全量',
                -- 组合包信息
                modpack_name TEXT,
                modpack_platform TEXT,  -- CurseForge, Modrinth, MultiMC, Generic
                modpack_version TEXT,
                minecraft_version TEXT,
                mod_loader TEXT,
                expected_mod_count INTEGER DEFAULT 0,
                -- 统计信息 (将通过关联表计算)
                total_mods INTEGER DEFAULT 0,
                total_language_files INTEGER DEFAULT 0,
                total_keys INTEGER DEFAULT 0
            )
        """)
        
        # === 2. 文件内容表 - 基于文件哈希的去重 ===
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS file_contents (
                content_hash TEXT PRIMARY KEY,  -- SHA256哈希作为主键
                file_path TEXT NOT NULL,        -- 最后一次发现的文件路径
                file_name TEXT NOT NULL,        -- 文件名
                file_size INTEGER NOT NULL,     -- 文件大小
                first_discovered TEXT NOT NULL, -- 首次发现时间
                last_seen TEXT NOT NULL,        -- 最后一次发现时间
                content_type TEXT NOT NULL      -- 文件类型 (jar, directory, etc.)
            )
        """)
        
        # === 3. 模组信息表 - 基于模组ID和版本的去重，支持完整信息 ===
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS mods (
                mod_key TEXT PRIMARY KEY,       -- mod_id + version 的复合主键
                mod_id TEXT NOT NULL,           -- 模组ID
                display_name TEXT,              -- 显示名称
                version TEXT,                   -- 版本
                description TEXT,               -- 描述
                mod_loader TEXT,                -- 模组加载器 (forge, fabric, quilt, neoforge)
                authors TEXT,                   -- 作者列表 (JSON)
                dependencies TEXT,              -- 依赖列表 (JSON)
                minecraft_version TEXT,         -- 支持的MC版本
                loader_version TEXT,            -- 加载器版本要求
                license TEXT,                   -- 许可证
                homepage_url TEXT,              -- 主页链接
                source_url TEXT,                -- 源码链接
                issues_url TEXT,                -- 问题追踪链接
                file_size INTEGER DEFAULT 0,   -- 文件大小
                content_hash TEXT NOT NULL,     -- 关联到文件内容
                first_discovered TEXT NOT NULL, -- 首次发现时间
                last_seen TEXT NOT NULL,        -- 最后一次发现时间
                FOREIGN KEY (content_hash) REFERENCES file_contents(content_hash)
            )
        """)
        
        # === 4. 语言文件表 - 基于内容哈希的去重 ===
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS language_files (
                content_hash TEXT PRIMARY KEY,  -- 语言文件内容的SHA256哈希
                mod_key TEXT NOT NULL,          -- 所属模组
                namespace TEXT NOT NULL,        -- 命名空间
                locale TEXT NOT NULL,           -- 语言代码
                file_path TEXT NOT NULL,        -- 文件在JAR中的路径
                key_count INTEGER NOT NULL,     -- 翻译键数量
                first_discovered TEXT NOT NULL, -- 首次发现时间
                last_seen TEXT NOT NULL,        -- 最后一次发现时间
                FOREIGN KEY (mod_key) REFERENCES mods(mod_key)
            )
        """)
        
        # === 5. 翻译条目表 - 基于语言文件和键的去重 ===
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS translation_entries (
                entry_key TEXT PRIMARY KEY,     -- language_file_hash + key 的复合主键
                language_file_hash TEXT NOT NULL,
                translation_key TEXT NOT NULL,  -- 翻译键
                value TEXT NOT NULL,            -- 翻译值
                first_discovered TEXT NOT NULL, -- 首次发现时间
                last_seen TEXT NOT NULL,        -- 最后一次发现时间
                FOREIGN KEY (language_file_hash) REFERENCES language_files(content_hash)
            )
        """)
        
        # === 6. 扫描关联表 - 记录每次扫描发现的内容 ===
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS scan_discoveries (
                scan_id TEXT NOT NULL,
                content_hash TEXT NOT NULL,
                content_type TEXT NOT NULL,     -- 'mod', 'language_file', 'translation_entry'
                discovered_at TEXT NOT NULL,    -- 发现时间
                PRIMARY KEY (scan_id, content_hash, content_type),
                FOREIGN KEY (scan_id) REFERENCES scan_sessions(id)
            )
        """)
        
        # === 7. 创建索引优化查询 ===
        indexes = [
            "CREATE INDEX IF NOT EXISTS idx_file_contents_path ON file_contents(file_path)",
            "CREATE INDEX IF NOT EXISTS idx_mods_mod_id ON mods(mod_id)",
            "CREATE INDEX IF NOT EXISTS idx_language_files_locale ON language_files(locale)",
            "CREATE INDEX IF NOT EXISTS idx_language_files_namespace ON language_files(namespace)", 
            "CREATE INDEX IF NOT EXISTS idx_translation_entries_key ON translation_entries(translation_key)",
            "CREATE INDEX IF NOT EXISTS idx_scan_discoveries_scan ON scan_discoveries(scan_id)",
            "CREATE INDEX IF NOT EXISTS idx_scan_discoveries_type ON scan_discoveries(content_type)"
        ]
        
        for index_sql in indexes:
            cursor.execute(index_sql)
        
        conn.commit()
        conn.close()
    
    def generate_content_hash(self, content: str) -> str:
        """生成内容哈希"""
        return hashlib.sha256(content.encode('utf-8')).hexdigest()
    
    def generate_mod_key(self, mod_id: str, version: str) -> str:
        """生成模组复合主键"""
        return f"{mod_id}#{version}"
    
    def generate_entry_key(self, language_file_hash: str, translation_key: str) -> str:
        """生成翻译条目复合主键"""
        return f"{language_file_hash}#{translation_key}"
    
    def upsert_file_content(self, cursor: sqlite3.Cursor, file_path: str, 
                           file_content: bytes, content_type: str) -> str:
        """UPSERT文件内容记录"""
        content_hash = hashlib.sha256(file_content).hexdigest()
        now = datetime.now().isoformat()
        file_size = len(file_content)
        file_name = Path(file_path).name
        
        # 检查是否存在
        cursor.execute("SELECT content_hash FROM file_contents WHERE content_hash = ?", (content_hash,))
        exists = cursor.fetchone()
        
        if exists:
            # 更新最后发现时间和路径
            cursor.execute("""
                UPDATE file_contents 
                SET file_path = ?, last_seen = ?
                WHERE content_hash = ?
            """, (file_path, now, content_hash))
        else:
            # 插入新记录
            cursor.execute("""
                INSERT INTO file_contents 
                (content_hash, file_path, file_name, file_size, first_discovered, last_seen, content_type)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (content_hash, file_path, file_name, file_size, now, now, content_type))
        
        return content_hash
    
    def upsert_mod(self, cursor: sqlite3.Cursor, mod_info: Dict, content_hash: str) -> str:
        """UPSERT模组记录"""
        mod_id = mod_info.get('mod_id', 'unknown')
        version = mod_info.get('version', 'unknown')
        mod_key = self.generate_mod_key(mod_id, version)
        now = datetime.now().isoformat()
        
        # 检查是否存在
        cursor.execute("SELECT mod_key FROM mods WHERE mod_key = ?", (mod_key,))
        exists = cursor.fetchone()
        
        if exists:
            # 更新最后发现时间
            cursor.execute("""
                UPDATE mods 
                SET last_seen = ?, content_hash = ?, display_name = ?
                WHERE mod_key = ?
            """, (now, content_hash, mod_info.get('name'), mod_key))
        else:
            # 插入新记录
            authors_json = json.dumps(mod_info.get('authors', []))
            cursor.execute("""
                INSERT INTO mods 
                (mod_key, mod_id, display_name, version, mod_loader, description, authors, 
                 content_hash, first_discovered, last_seen)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (mod_key, mod_id, mod_info.get('name'), version, 
                  mod_info.get('mod_loader'), mod_info.get('description'),
                  authors_json, content_hash, now, now))
        
        return mod_key
    
    def upsert_language_file(self, cursor: sqlite3.Cursor, mod_key: str, 
                           lang_file_info: Dict, content: Dict) -> str:
        """UPSERT语言文件记录"""
        # 基于文件内容生成哈希
        content_json = json.dumps(content, sort_keys=True, ensure_ascii=False)
        content_hash = self.generate_content_hash(content_json)
        now = datetime.now().isoformat()
        
        # 检查是否存在
        cursor.execute("SELECT content_hash FROM language_files WHERE content_hash = ?", (content_hash,))
        exists = cursor.fetchone()
        
        if exists:
            # 更新最后发现时间
            cursor.execute("""
                UPDATE language_files 
                SET last_seen = ?
                WHERE content_hash = ?
            """, (now, content_hash))
        else:
            # 插入新记录
            cursor.execute("""
                INSERT INTO language_files 
                (content_hash, mod_key, namespace, locale, file_path, key_count, 
                 first_discovered, last_seen)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, (content_hash, mod_key, lang_file_info.get('namespace', 'minecraft'),
                  lang_file_info.get('locale', 'en_us'), lang_file_info.get('file_path', ''),
                  len(content), now, now))
        
        return content_hash
    
    def upsert_translation_entries(self, cursor: sqlite3.Cursor, 
                                 language_file_hash: str, entries: Dict):
        """UPSERT翻译条目记录"""
        now = datetime.now().isoformat()
        
        for key, value in entries.items():
            entry_key = self.generate_entry_key(language_file_hash, key)
            
            # 检查是否存在
            cursor.execute("SELECT entry_key FROM translation_entries WHERE entry_key = ?", (entry_key,))
            exists = cursor.fetchone()
            
            if exists:
                # 更新值和最后发现时间
                cursor.execute("""
                    UPDATE translation_entries 
                    SET value = ?, last_seen = ?
                    WHERE entry_key = ?
                """, (str(value), now, entry_key))
            else:
                # 插入新记录
                cursor.execute("""
                    INSERT INTO translation_entries 
                    (entry_key, language_file_hash, translation_key, value, first_discovered, last_seen)
                    VALUES (?, ?, ?, ?, ?, ?)
                """, (entry_key, language_file_hash, key, str(value), now, now))
    
    def record_scan_discovery(self, cursor: sqlite3.Cursor, scan_id: str, 
                            content_hash: str, content_type: str):
        """记录扫描发现"""
        now = datetime.now().isoformat()
        cursor.execute("""
            INSERT OR IGNORE INTO scan_discoveries 
            (scan_id, content_hash, content_type, discovered_at)
            VALUES (?, ?, ?, ?)
        """, (scan_id, content_hash, content_type, now))
    
    def migrate_existing_data(self, old_db_path: str = "mc_l10n.db"):
        """迁移现有数据到新结构"""
        # 这里可以实现数据迁移逻辑
        # 读取旧数据库，使用UPSERT方法写入新数据库
        pass
    
    def get_scan_statistics(self, scan_id: str) -> Dict:
        """获取扫描统计信息"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # 统计发现的内容
        cursor.execute("""
            SELECT content_type, COUNT(*) as count
            FROM scan_discoveries 
            WHERE scan_id = ?
            GROUP BY content_type
        """, (scan_id,))
        
        stats = {'total_mods': 0, 'total_language_files': 0, 'total_keys': 0}
        for content_type, count in cursor.fetchall():
            if content_type == 'mod':
                stats['total_mods'] = count
            elif content_type == 'language_file':
                stats['total_language_files'] = count
            elif content_type == 'translation_entry':
                stats['total_keys'] = count
        
        conn.close()
        return stats

if __name__ == "__main__":
    # 测试新数据库设计
    redesign = DatabaseRedesign()
    redesign.create_new_schema()
    print("新数据库结构创建完成")