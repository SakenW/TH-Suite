#!/usr/bin/env python
"""
MC L10n 生产级数据库管理器
唯一的数据库实现版本，用于生产环境
"""

import hashlib
import json
import logging
import sqlite3
from contextlib import contextmanager
from dataclasses import asdict, dataclass
from datetime import datetime
from pathlib import Path

logger = logging.getLogger(__name__)


@dataclass
class ModInfo:
    """MOD信息数据类"""

    mod_id: str
    display_name: str
    version: str = ""
    description: str = ""
    mod_loader: str = ""
    authors: str = ""
    file_path: str = ""
    file_size: int = 0
    file_hash: str = ""

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass
class LanguageFile:
    """语言文件数据类"""

    language_code: str
    file_path: str
    format: str = "json"
    content: dict = None
    entry_count: int = 0

    def to_dict(self) -> dict:
        data = asdict(self)
        if self.content:
            data["content"] = json.dumps(self.content)
        return data


@dataclass
class TranslationEntry:
    """翻译条目数据类"""

    key: str
    source_text: str
    target_text: str = ""
    status: str = "pending"
    category: str = ""

    def to_dict(self) -> dict:
        return asdict(self)


class Database:
    """生产级数据库管理器 - MC L10n 唯一数据库实现"""

    DB_VERSION = "5.0.0"
    _instance = None
    _initialized = False

    def __new__(cls, db_path: str = None):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self, db_path: str = None):
        if db_path is None:
            db_path = Path(__file__).parent / "mc_l10n.db"

        # 如果路径改变了，重新初始化
        new_path = Path(db_path)
        if hasattr(self, "db_path") and self.db_path == new_path and self._initialized:
            return

        self.db_path = new_path
        self.conn: sqlite3.Connection | None = None
        self._initialized = True
        self.init_database()

    @contextmanager
    def get_connection(self):
        """获取数据库连接的上下文管理器"""
        conn = sqlite3.connect(self.db_path, timeout=30.0)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA foreign_keys = ON")
        conn.execute("PRAGMA journal_mode = WAL")
        conn.execute("PRAGMA cache_size = -65536")
        conn.execute("PRAGMA temp_store = MEMORY")
        conn.execute("PRAGMA synchronous = NORMAL")
        try:
            yield conn
            conn.commit()
        except Exception as e:
            conn.rollback()
            raise e
        finally:
            conn.close()

    def init_database(self):
        """初始化数据库"""
        with self.get_connection() as conn:
            self._create_tables(conn)
            self._create_indexes(conn)
            self._create_views(conn)
            self._insert_metadata(conn)

    def _create_tables(self, conn: sqlite3.Connection):
        """创建所有数据库表"""

        # 1. 数据库元数据表
        conn.execute("""
        CREATE TABLE IF NOT EXISTS db_metadata (
            key TEXT PRIMARY KEY,
            value TEXT NOT NULL,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        """)

        # 2. 扫描会话表
        conn.execute("""
        CREATE TABLE IF NOT EXISTS scan_sessions (
            id TEXT PRIMARY KEY DEFAULT (hex(randomblob(16))),
            project_path TEXT NOT NULL,
            scan_type TEXT DEFAULT 'full',
            status TEXT DEFAULT 'pending',
            total_files INTEGER DEFAULT 0,
            processed_files INTEGER DEFAULT 0,
            discovered_mods INTEGER DEFAULT 0,
            discovered_languages INTEGER DEFAULT 0,
            discovered_entries INTEGER DEFAULT 0,
            error_count INTEGER DEFAULT 0,
            started_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            completed_at TIMESTAMP,
            metadata TEXT
        )
        """)

        # 3. MOD表
        conn.execute("""
        CREATE TABLE IF NOT EXISTS mods (
            id TEXT PRIMARY KEY DEFAULT (hex(randomblob(16))),
            mod_id TEXT UNIQUE NOT NULL,
            display_name TEXT NOT NULL,
            version TEXT,
            description TEXT,
            mod_loader TEXT,
            authors TEXT,
            file_path TEXT NOT NULL,
            file_size INTEGER DEFAULT 0,
            file_hash TEXT,
            first_discovered TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            scan_id TEXT,
            FOREIGN KEY (scan_id) REFERENCES scan_sessions(id) ON DELETE SET NULL
        )
        """)

        # 4. 语言文件表
        conn.execute("""
        CREATE TABLE IF NOT EXISTS language_files (
            id TEXT PRIMARY KEY DEFAULT (hex(randomblob(16))),
            mod_id TEXT NOT NULL,
            language_code TEXT NOT NULL,
            file_path TEXT,
            format TEXT DEFAULT 'json',
            entry_count INTEGER DEFAULT 0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            UNIQUE(mod_id, language_code),
            FOREIGN KEY (mod_id) REFERENCES mods(id) ON DELETE CASCADE
        )
        """)

        # 5. 翻译条目表
        conn.execute("""
        CREATE TABLE IF NOT EXISTS translation_entries (
            id TEXT PRIMARY KEY DEFAULT (hex(randomblob(16))),
            language_file_id TEXT NOT NULL,
            key TEXT NOT NULL,
            source_text TEXT,
            target_text TEXT,
            machine_translation TEXT,
            human_translation TEXT,
            status TEXT DEFAULT 'pending',
            category TEXT,
            context TEXT,
            max_length INTEGER,
            translator_notes TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            UNIQUE(language_file_id, key),
            FOREIGN KEY (language_file_id) REFERENCES language_files(id) ON DELETE CASCADE
        )
        """)

        # 6. 项目表
        conn.execute("""
        CREATE TABLE IF NOT EXISTS projects (
            id TEXT PRIMARY KEY DEFAULT (hex(randomblob(16))),
            name TEXT NOT NULL,
            path TEXT UNIQUE NOT NULL,
            source_language TEXT DEFAULT 'en_us',
            target_languages TEXT DEFAULT '["zh_cn"]',
            scan_config TEXT,
            auto_scan BOOLEAN DEFAULT FALSE,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        """)

        # 7. 扫描缓存表
        conn.execute("""
        CREATE TABLE IF NOT EXISTS scan_cache (
            id TEXT PRIMARY KEY DEFAULT (hex(randomblob(16))),
            file_path TEXT UNIQUE NOT NULL,
            file_hash TEXT,
            file_size INTEGER,
            scan_result TEXT,
            cached_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            expires_at TIMESTAMP
        )
        """)

        # 8. 翻译记忆库表
        conn.execute("""
        CREATE TABLE IF NOT EXISTS translation_memory (
            id TEXT PRIMARY KEY DEFAULT (hex(randomblob(16))),
            source_text TEXT NOT NULL,
            source_lang TEXT NOT NULL,
            target_text TEXT NOT NULL,
            target_lang TEXT NOT NULL,
            context TEXT,
            domain TEXT,
            quality_score REAL DEFAULT 1.0,
            usage_count INTEGER DEFAULT 1,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            UNIQUE(source_text, source_lang, target_lang, context)
        )
        """)

        # 9. 术语表
        conn.execute("""
        CREATE TABLE IF NOT EXISTS glossary (
            id TEXT PRIMARY KEY DEFAULT (hex(randomblob(16))),
            term TEXT NOT NULL,
            translation TEXT NOT NULL,
            language TEXT NOT NULL,
            category TEXT,
            description TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            UNIQUE(term, language)
        )
        """)

        # 10. 操作日志表
        conn.execute("""
        CREATE TABLE IF NOT EXISTS operation_logs (
            id TEXT PRIMARY KEY DEFAULT (hex(randomblob(16))),
            operation_type TEXT NOT NULL,
            target_type TEXT,
            target_id TEXT,
            details TEXT,
            status TEXT DEFAULT 'success',
            error_message TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        """)

    def _create_indexes(self, conn: sqlite3.Connection):
        """创建性能优化索引"""
        indexes = [
            # 扫描会话索引
            "CREATE INDEX IF NOT EXISTS idx_scan_sessions_status ON scan_sessions(status)",
            "CREATE INDEX IF NOT EXISTS idx_scan_sessions_started ON scan_sessions(started_at DESC)",
            # MOD索引
            "CREATE INDEX IF NOT EXISTS idx_mods_mod_id ON mods(mod_id)",
            "CREATE INDEX IF NOT EXISTS idx_mods_name ON mods(display_name)",
            "CREATE INDEX IF NOT EXISTS idx_mods_scan ON mods(scan_id)",
            # 语言文件索引
            "CREATE INDEX IF NOT EXISTS idx_language_files_mod ON language_files(mod_id)",
            "CREATE INDEX IF NOT EXISTS idx_language_files_lang ON language_files(language_code)",
            # 翻译条目索引
            "CREATE INDEX IF NOT EXISTS idx_translation_entries_file ON translation_entries(language_file_id)",
            "CREATE INDEX IF NOT EXISTS idx_translation_entries_key ON translation_entries(key)",
            "CREATE INDEX IF NOT EXISTS idx_translation_entries_status ON translation_entries(status)",
            # 项目索引
            "CREATE INDEX IF NOT EXISTS idx_projects_path ON projects(path)",
            # 扫描缓存索引
            "CREATE INDEX IF NOT EXISTS idx_scan_cache_path ON scan_cache(file_path)",
            # 翻译记忆库索引
            "CREATE INDEX IF NOT EXISTS idx_translation_memory_source ON translation_memory(source_text, source_lang)",
            "CREATE INDEX IF NOT EXISTS idx_translation_memory_target ON translation_memory(target_lang)",
            # 术语表索引
            "CREATE INDEX IF NOT EXISTS idx_glossary_term ON glossary(term)",
            # 操作日志索引
            "CREATE INDEX IF NOT EXISTS idx_operation_logs_type ON operation_logs(operation_type)",
            "CREATE INDEX IF NOT EXISTS idx_operation_logs_created ON operation_logs(created_at DESC)",
        ]

        for index_sql in indexes:
            conn.execute(index_sql)

    def _create_views(self, conn: sqlite3.Connection):
        """创建统计视图"""

        # 扫描统计视图
        conn.execute("""
        CREATE VIEW IF NOT EXISTS v_scan_statistics AS
        SELECT
            COUNT(*) as total_scans,
            SUM(CASE WHEN status = 'completed' THEN 1 ELSE 0 END) as completed_scans,
            SUM(discovered_mods) as total_mods_discovered,
            SUM(discovered_languages) as total_languages_discovered,
            SUM(discovered_entries) as total_entries_discovered,
            AVG(CASE WHEN completed_at IS NOT NULL THEN
                (julianday(completed_at) - julianday(started_at)) * 86400
            ELSE NULL END) as avg_scan_duration_seconds
        FROM scan_sessions
        """)

        # MOD统计视图
        conn.execute("""
        CREATE VIEW IF NOT EXISTS v_mod_statistics AS
        SELECT
            m.mod_id,
            m.display_name,
            m.version,
            COUNT(DISTINCT lf.language_code) as language_count,
            SUM(lf.entry_count) as total_entries,
            m.file_size,
            m.first_discovered,
            m.last_updated
        FROM mods m
        LEFT JOIN language_files lf ON m.id = lf.mod_id
        GROUP BY m.id
        """)

        # 翻译进度视图
        conn.execute("""
        CREATE VIEW IF NOT EXISTS v_translation_progress AS
        SELECT
            lf.mod_id,
            lf.language_code,
            COUNT(te.id) as total_entries,
            SUM(CASE WHEN te.status = 'translated' THEN 1 ELSE 0 END) as translated_entries,
            SUM(CASE WHEN te.status = 'reviewed' THEN 1 ELSE 0 END) as reviewed_entries,
            ROUND(100.0 * SUM(CASE WHEN te.status IN ('translated', 'reviewed') THEN 1 ELSE 0 END) / COUNT(te.id), 2) as progress_percentage
        FROM language_files lf
        LEFT JOIN translation_entries te ON lf.id = te.language_file_id
        GROUP BY lf.mod_id, lf.language_code
        """)

        # 缓存统计视图
        conn.execute("""
        CREATE VIEW IF NOT EXISTS v_cache_statistics AS
        SELECT
            COUNT(*) as total_cached_files,
            SUM(file_size) as total_cache_size,
            COUNT(CASE WHEN expires_at > CURRENT_TIMESTAMP OR expires_at IS NULL THEN 1 END) as valid_cache_entries,
            COUNT(CASE WHEN expires_at <= CURRENT_TIMESTAMP THEN 1 END) as expired_cache_entries
        FROM scan_cache
        """)

    def _insert_metadata(self, conn: sqlite3.Connection):
        """插入数据库元数据"""
        conn.execute(
            """
            INSERT OR REPLACE INTO db_metadata (key, value)
            VALUES ('version', ?), ('created_at', ?)
        """,
            (self.DB_VERSION, datetime.now().isoformat()),
        )

    # ========== 扫描相关方法 ==========

    def create_scan_session(self, project_path: str, scan_type: str = "full") -> str:
        """创建扫描会话"""
        scan_id = hashlib.md5(
            f"{project_path}_{datetime.now().isoformat()}".encode()
        ).hexdigest()[:16]
        with self.get_connection() as conn:
            conn.execute(
                """
                INSERT INTO scan_sessions (id, project_path, scan_type, status)
                VALUES (?, ?, ?, 'processing')
            """,
                (scan_id, project_path, scan_type),
            )
        return scan_id

    def update_scan_progress(self, scan_id: str, processed: int, total: int):
        """更新扫描进度"""
        with self.get_connection() as conn:
            conn.execute(
                """
                UPDATE scan_sessions
                SET processed_files = ?, total_files = ?
                WHERE id = ?
            """,
                (processed, total, scan_id),
            )

    def complete_scan_session(self, scan_id: str, stats: dict):
        """完成扫描会话"""
        with self.get_connection() as conn:
            conn.execute(
                """
                UPDATE scan_sessions
                SET status = 'completed',
                    completed_at = CURRENT_TIMESTAMP,
                    discovered_mods = ?,
                    discovered_languages = ?,
                    discovered_entries = ?,
                    metadata = ?
                WHERE id = ?
            """,
                (
                    stats.get("mods", 0),
                    stats.get("languages", 0),
                    stats.get("entries", 0),
                    json.dumps(stats),
                    scan_id,
                ),
            )

    # ========== MOD相关方法 ==========

    def save_mod(self, mod_info: ModInfo, scan_id: str = None) -> str:
        """保存MOD信息"""
        mod_id = mod_info.mod_id
        with self.get_connection() as conn:
            # 检查是否已存在
            existing = conn.execute(
                "SELECT id FROM mods WHERE mod_id = ?", (mod_id,)
            ).fetchone()

            if existing:
                # 更新现有MOD
                conn.execute(
                    """
                    UPDATE mods
                    SET display_name = ?, version = ?, description = ?,
                        mod_loader = ?, authors = ?, file_path = ?,
                        file_size = ?, file_hash = ?, last_updated = CURRENT_TIMESTAMP,
                        scan_id = ?
                    WHERE mod_id = ?
                """,
                    (
                        mod_info.display_name,
                        mod_info.version,
                        mod_info.description,
                        mod_info.mod_loader,
                        mod_info.authors,
                        mod_info.file_path,
                        mod_info.file_size,
                        mod_info.file_hash,
                        scan_id,
                        mod_id,
                    ),
                )
                return existing["id"]
            else:
                # 插入新MOD
                id_value = hashlib.md5(mod_id.encode()).hexdigest()[:16]
                conn.execute(
                    """
                    INSERT INTO mods
                    (id, mod_id, display_name, version, description, mod_loader,
                     authors, file_path, file_size, file_hash, scan_id)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                    (
                        id_value,
                        mod_id,
                        mod_info.display_name,
                        mod_info.version,
                        mod_info.description,
                        mod_info.mod_loader,
                        mod_info.authors,
                        mod_info.file_path,
                        mod_info.file_size,
                        mod_info.file_hash,
                        scan_id,
                    ),
                )
                return id_value

    def get_mod_by_id(self, mod_id: str) -> dict | None:
        """获取MOD信息"""
        with self.get_connection() as conn:
            result = conn.execute(
                """
                SELECT * FROM mods WHERE mod_id = ? OR id = ?
            """,
                (mod_id, mod_id),
            ).fetchone()
            return dict(result) if result else None

    # ========== 语言文件相关方法 ==========

    def save_language_file(self, mod_id: str, lang_file: LanguageFile) -> str:
        """保存语言文件"""
        with self.get_connection() as conn:
            # 获取MOD的数据库ID
            mod_result = conn.execute(
                "SELECT id FROM mods WHERE mod_id = ? OR id = ?", (mod_id, mod_id)
            ).fetchone()

            if not mod_result:
                raise ValueError(f"MOD {mod_id} not found")

            mod_db_id = mod_result["id"]

            # 检查是否已存在
            existing = conn.execute(
                """
                SELECT id FROM language_files
                WHERE mod_id = ? AND language_code = ?
            """,
                (mod_db_id, lang_file.language_code),
            ).fetchone()

            if existing:
                # 更新现有语言文件
                conn.execute(
                    """
                    UPDATE language_files
                    SET file_path = ?, format = ?, entry_count = ?,
                        updated_at = CURRENT_TIMESTAMP
                    WHERE id = ?
                """,
                    (
                        lang_file.file_path,
                        lang_file.format,
                        lang_file.entry_count,
                        existing["id"],
                    ),
                )
                return existing["id"]
            else:
                # 插入新语言文件
                id_value = hashlib.md5(
                    f"{mod_db_id}_{lang_file.language_code}".encode()
                ).hexdigest()[:16]

                conn.execute(
                    """
                    INSERT INTO language_files
                    (id, mod_id, language_code, file_path, format, entry_count)
                    VALUES (?, ?, ?, ?, ?, ?)
                """,
                    (
                        id_value,
                        mod_db_id,
                        lang_file.language_code,
                        lang_file.file_path,
                        lang_file.format,
                        lang_file.entry_count,
                    ),
                )
                return id_value

    # ========== 翻译条目相关方法 ==========

    def save_translation_entries(
        self, language_file_id: str, entries: list[TranslationEntry]
    ):
        """批量保存翻译条目"""
        with self.get_connection() as conn:
            for entry in entries:
                entry_id = hashlib.md5(
                    f"{language_file_id}_{entry.key}".encode()
                ).hexdigest()[:16]

                conn.execute(
                    """
                    INSERT OR REPLACE INTO translation_entries
                    (id, language_file_id, key, source_text, target_text,
                     status, category)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                    (
                        entry_id,
                        language_file_id,
                        entry.key,
                        entry.source_text,
                        entry.target_text,
                        entry.status,
                        entry.category,
                    ),
                )

    # ========== 缓存相关方法 ==========

    def get_cache(self, file_path: str) -> dict | None:
        """获取缓存数据"""
        with self.get_connection() as conn:
            result = conn.execute(
                """
                SELECT * FROM scan_cache
                WHERE file_path = ?
                AND (expires_at IS NULL OR expires_at > CURRENT_TIMESTAMP)
            """,
                (file_path,),
            ).fetchone()

            if result:
                return {
                    "file_hash": result["file_hash"],
                    "scan_result": json.loads(result["scan_result"])
                    if result["scan_result"]
                    else None,
                }
            return None

    def save_cache(
        self,
        file_path: str,
        file_hash: str,
        scan_result: dict,
        ttl_seconds: int = 86400,
    ):
        """保存缓存数据"""
        with self.get_connection() as conn:
            conn.execute(
                """
                INSERT OR REPLACE INTO scan_cache
                (file_path, file_hash, scan_result, expires_at)
                VALUES (?, ?, ?, datetime('now', '+' || ? || ' seconds'))
            """,
                (file_path, file_hash, json.dumps(scan_result), ttl_seconds),
            )

    # ========== 项目相关方法 ==========

    def create_project(self, name: str, path: str, config: dict = None) -> str:
        """创建项目"""
        project_id = hashlib.md5(path.encode()).hexdigest()[:16]
        with self.get_connection() as conn:
            conn.execute(
                """
                INSERT OR REPLACE INTO projects
                (id, name, path, scan_config)
                VALUES (?, ?, ?, ?)
            """,
                (project_id, name, path, json.dumps(config) if config else None),
            )
        return project_id

    def get_project(self, path: str) -> dict | None:
        """获取项目信息"""
        with self.get_connection() as conn:
            result = conn.execute(
                """
                SELECT * FROM projects WHERE path = ?
            """,
                (path,),
            ).fetchone()
            return dict(result) if result else None

    # ========== 统计相关方法 ==========

    def get_statistics(self) -> dict:
        """获取数据库统计信息"""
        with self.get_connection() as conn:
            stats = {}

            # 基本统计
            for table in ["mods", "language_files", "translation_entries", "projects"]:
                count = conn.execute(f"SELECT COUNT(*) as cnt FROM {table}").fetchone()
                stats[f"total_{table}"] = count["cnt"]

            # 扫描统计
            scan_stats = conn.execute("""
                SELECT * FROM v_scan_statistics
            """).fetchone()
            if scan_stats:
                stats["scan_statistics"] = dict(scan_stats)

            # 缓存统计
            cache_stats = conn.execute("""
                SELECT * FROM v_cache_statistics
            """).fetchone()
            if cache_stats:
                stats["cache_statistics"] = dict(cache_stats)

            return stats

    def cleanup_expired_cache(self):
        """清理过期缓存"""
        with self.get_connection() as conn:
            conn.execute("""
                DELETE FROM scan_cache
                WHERE expires_at <= CURRENT_TIMESTAMP
            """)

    def close(self):
        """关闭数据库连接"""
        if self.conn:
            self.conn.close()
            self.conn = None


# 导出主要类和函数
__all__ = ["Database", "ModInfo", "LanguageFile", "TranslationEntry"]


def get_database(db_path: str = None) -> Database:
    """获取数据库实例"""
    return Database(db_path)


if __name__ == "__main__":
    # 测试数据库
    db = Database("test_production.db")
    print(f"数据库版本: {db.DB_VERSION}")
    print(f"数据库路径: {db.db_path}")

    # 测试基本功能
    scan_id = db.create_scan_session("/test/path", "full")
    print(f"创建扫描会话: {scan_id}")

    # 测试MOD保存
    mod = ModInfo(
        mod_id="test_mod",
        display_name="Test Mod",
        version="1.0.0",
        file_path="/test/mod.jar",
    )
    mod_id = db.save_mod(mod, scan_id)
    print(f"保存MOD: {mod_id}")

    # 测试语言文件
    lang_file = LanguageFile(
        language_code="zh_cn", file_path="/test/lang/zh_cn.json", entry_count=100
    )
    lang_id = db.save_language_file("test_mod", lang_file)
    print(f"保存语言文件: {lang_id}")

    # 获取统计
    stats = db.get_statistics()
    print(f"数据库统计: {json.dumps(stats, indent=2)}")
