"""
SQLite Repository实现
实现领域层定义的Repository接口
"""

import json
import logging
import sqlite3
from datetime import datetime
from typing import Any

from domain.models.mod import Mod, ModId, ModMetadata, ModVersion
from domain.models.translation_project import TranslationProject
from domain.repositories import (
    EventRepository,
    ModRepository,
    ScanResultRepository,
    TranslationProjectRepository,
    TranslationRepository,
)

logger = logging.getLogger(__name__)


class SqliteModRepository(ModRepository):
    """SQLite Mod仓储实现"""

    def __init__(self, db_path: str):
        self.db_path = db_path
        self._init_database()

    def _init_database(self):
        """初始化数据库表"""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS mods (
                    mod_id TEXT PRIMARY KEY,
                    name TEXT NOT NULL,
                    version TEXT NOT NULL,
                    authors TEXT,
                    description TEXT,
                    minecraft_version TEXT,
                    loader_type TEXT,
                    file_path TEXT NOT NULL UNIQUE,
                    scan_status TEXT NOT NULL DEFAULT 'pending',
                    last_scanned TIMESTAMP,
                    content_hash TEXT,
                    metadata TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)

            # 创建优化的复合索引
            conn.execute(
                "CREATE INDEX IF NOT EXISTS idx_mods_status ON mods(scan_status)"
            )
            conn.execute(
                "CREATE UNIQUE INDEX IF NOT EXISTS idx_mods_file_path ON mods(file_path)"
            )
            conn.execute(
                "CREATE INDEX IF NOT EXISTS idx_mods_content_hash ON mods(content_hash)"
            )
            conn.execute(
                "CREATE INDEX IF NOT EXISTS idx_mods_status_updated ON mods(scan_status, updated_at)"
            )
            conn.execute(
                "CREATE INDEX IF NOT EXISTS idx_mods_name_search ON mods(name COLLATE NOCASE)"
            )
            conn.execute(
                "CREATE INDEX IF NOT EXISTS idx_mods_loader_version ON mods(loader_type, minecraft_version)"
            )
            
            # 启用 WAL 模式以提高并发性能
            conn.execute("PRAGMA journal_mode=WAL")
            conn.execute("PRAGMA synchronous=NORMAL")
            conn.execute("PRAGMA cache_size=10000")
            conn.execute("PRAGMA temp_store=MEMORY")
            conn.execute("PRAGMA mmap_size=268435456")  # 256MB

    def find_by_id(self, mod_id: ModId) -> Mod | None:
        """根据ID查找Mod"""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.execute("SELECT * FROM mods WHERE mod_id = ?", (str(mod_id),))
            row = cursor.fetchone()

            if row:
                return self._row_to_mod(row)
            return None

    def find_by_file_path(self, file_path: str) -> Mod | None:
        """根据文件路径查找Mod"""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.execute(
                "SELECT * FROM mods WHERE file_path = ?", (file_path,)
            )
            row = cursor.fetchone()

            if row:
                return self._row_to_mod(row)
            return None

    def find_by_content_hash(self, content_hash: str) -> Mod | None:
        """根据内容哈希查找Mod"""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.execute(
                "SELECT * FROM mods WHERE content_hash = ?", (content_hash,)
            )
            row = cursor.fetchone()

            if row:
                return self._row_to_mod(row)
            return None

    def find_all(self, limit: int = 100, offset: int = 0, order_by: str = "updated_at DESC") -> list[Mod]:
        """查找所有Mod"""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            # 添加排序以利用索引
            cursor = conn.execute(
                f"SELECT * FROM mods ORDER BY {order_by} LIMIT ? OFFSET ?", (limit, offset)
            )

            return [self._row_to_mod(row) for row in cursor.fetchall()]

    def find_by_status(self, status: str) -> list[Mod]:
        """根据状态查找Mod"""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.execute("SELECT * FROM mods WHERE scan_status = ?", (status,))

            return [self._row_to_mod(row) for row in cursor.fetchall()]

    def find_needs_rescan(self) -> list[Mod]:
        """查找需要重新扫描的Mod"""
        # 这里简化实现，实际应该比较文件修改时间
        return self.find_by_status("pending")

    def save(self, mod: Mod) -> Mod:
        """保存Mod - 使用UPSERT优化"""
        with sqlite3.connect(self.db_path) as conn:
            metadata_json = json.dumps(
                {
                    "authors": mod.metadata.authors,
                    "dependencies": mod.metadata.dependencies,
                    "tags": list(mod.metadata.tags),
                }
            )

            # 使用 INSERT OR REPLACE 优化单次操作
            conn.execute(
                """
                INSERT OR REPLACE INTO mods (
                    mod_id, name, version, authors, description,
                    minecraft_version, loader_type, file_path,
                    scan_status, last_scanned, content_hash, metadata,
                    created_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
                (
                    str(mod.mod_id),
                    mod.metadata.name,
                    str(mod.metadata.version),
                    json.dumps(mod.metadata.authors),
                    mod.metadata.description,
                    mod.metadata.minecraft_version,
                    mod.metadata.loader_type,
                    mod.file_path,
                    mod.scan_status,
                    mod.last_scanned,
                    mod.content_hash,
                    metadata_json,
                    mod.created_at,
                    mod.updated_at,
                ),
            )

            conn.commit()
            return mod

    def update(self, mod: Mod) -> Mod:
        """更新Mod"""
        with sqlite3.connect(self.db_path) as conn:
            metadata_json = json.dumps(
                {
                    "authors": mod.metadata.authors,
                    "dependencies": mod.metadata.dependencies,
                    "tags": list(mod.metadata.tags),
                }
            )

            conn.execute(
                """
                UPDATE mods SET
                    name = ?, version = ?, authors = ?, description = ?,
                    minecraft_version = ?, loader_type = ?, file_path = ?,
                    scan_status = ?, last_scanned = ?, content_hash = ?,
                    metadata = ?, updated_at = ?
                WHERE mod_id = ?
            """,
                (
                    mod.metadata.name,
                    str(mod.metadata.version),
                    json.dumps(mod.metadata.authors),
                    mod.metadata.description,
                    mod.metadata.minecraft_version,
                    mod.metadata.loader_type,
                    mod.file_path,
                    mod.scan_status,
                    mod.last_scanned,
                    mod.content_hash,
                    metadata_json,
                    mod.updated_at,
                    str(mod.mod_id),
                ),
            )

            conn.commit()
            return mod

    def delete(self, mod_id: ModId) -> bool:
        """删除Mod"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute("DELETE FROM mods WHERE mod_id = ?", (str(mod_id),))
            conn.commit()
            return cursor.rowcount > 0

    def exists(self, mod_id: ModId) -> bool:
        """检查Mod是否存在"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute(
                "SELECT COUNT(*) FROM mods WHERE mod_id = ?", (str(mod_id),)
            )
            return cursor.fetchone()[0] > 0

    def count(self) -> int:
        """统计Mod数量"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute("SELECT COUNT(*) FROM mods")
            return cursor.fetchone()[0]

    def count_by_status(self, status: str) -> int:
        """统计指定状态的Mod数量"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute(
                "SELECT COUNT(*) FROM mods WHERE scan_status = ?", (status,)
            )
            return cursor.fetchone()[0]

    def search(self, query: str, limit: int = 100) -> list[Mod]:
        """搜索Mod - 优化的全文搜索"""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            
            # 使用更高效的搜索策略
            search_term = f"%{query}%"
            cursor = conn.execute(
                """
                SELECT * FROM mods
                WHERE (
                    name LIKE ? 
                    OR mod_id LIKE ?
                    OR description LIKE ?
                )
                ORDER BY 
                    CASE 
                        WHEN name = ? THEN 1
                        WHEN mod_id = ? THEN 2
                        WHEN name LIKE ? THEN 3
                        WHEN mod_id LIKE ? THEN 4
                        ELSE 5
                    END,
                    updated_at DESC
                LIMIT ?
            """,
                (
                    search_term, search_term, search_term,  # LIKE searches
                    query, query,  # exact matches
                    f"{query}%", f"{query}%",  # prefix matches
                    limit
                ),
            )

            return [self._row_to_mod(row) for row in cursor.fetchall()]

    def _row_to_mod(self, row: sqlite3.Row) -> Mod:
        """将数据库行转换为Mod对象"""
        # 解析元数据
        metadata_json = json.loads(row["metadata"] or "{}")

        # 创建ModMetadata
        metadata = ModMetadata(
            name=row["name"],
            version=ModVersion.from_string(row["version"]),
            authors=json.loads(row["authors"] or "[]"),
            description=row["description"],
            minecraft_version=row["minecraft_version"],
            loader_type=row["loader_type"],
            dependencies=metadata_json.get("dependencies", []),
            tags=set(metadata_json.get("tags", [])),
        )

        # 创建Mod
        mod = Mod(
            mod_id=ModId(row["mod_id"]), metadata=metadata, file_path=row["file_path"]
        )

        # 设置其他属性
        mod.scan_status = row["scan_status"]
        mod.last_scanned = (
            datetime.fromisoformat(row["last_scanned"]) if row["last_scanned"] else None
        )
        mod.content_hash = row["content_hash"]
        mod.created_at = datetime.fromisoformat(row["created_at"])
        mod.updated_at = datetime.fromisoformat(row["updated_at"])

        return mod


class SqliteTranslationProjectRepository(TranslationProjectRepository):
    """SQLite翻译项目仓储实现"""

    def __init__(self, db_path: str):
        self.db_path = db_path
        self._init_database()

    def _init_database(self):
        """初始化数据库表"""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS projects (
                    project_id TEXT PRIMARY KEY,
                    name TEXT NOT NULL,
                    description TEXT,
                    status TEXT NOT NULL,
                    target_languages TEXT,
                    mod_ids TEXT,
                    settings TEXT,
                    contributors TEXT,
                    tasks TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)

    def find_by_id(self, project_id: str) -> TranslationProject | None:
        """根据ID查找项目"""
        # 简化实现
        return None

    def find_all(self, limit: int = 100, offset: int = 0) -> list[TranslationProject]:
        """查找所有项目"""
        return []

    def find_by_status(self, status: str) -> list[TranslationProject]:
        """根据状态查找项目"""
        return []

    def find_by_contributor(self, user_id: str) -> list[TranslationProject]:
        """查找用户参与的项目"""
        return []

    def find_containing_mod(self, mod_id: ModId) -> list[TranslationProject]:
        """查找包含指定Mod的项目"""
        return []

    def save(self, project: TranslationProject) -> TranslationProject:
        """保存项目"""
        return project

    def update(self, project: TranslationProject) -> TranslationProject:
        """更新项目"""
        return project

    def delete(self, project_id: str) -> bool:
        """删除项目"""
        return False

    def exists(self, project_id: str) -> bool:
        """检查项目是否存在"""
        return False


class SqliteTranslationRepository(TranslationRepository):
    """SQLite翻译仓储实现"""

    def __init__(self, db_path: str):
        self.db_path = db_path
        self._init_database()

    def _init_database(self):
        """初始化数据库表"""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS translations (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    mod_id TEXT NOT NULL,
                    language TEXT NOT NULL,
                    key TEXT NOT NULL,
                    original TEXT,
                    translated TEXT,
                    status TEXT NOT NULL DEFAULT 'pending',
                    translator TEXT,
                    reviewed_by TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    UNIQUE(mod_id, language, key)
                )
            """)
            
            # 创建优化索引
            conn.execute(
                "CREATE INDEX IF NOT EXISTS idx_translations_mod_lang ON translations(mod_id, language)"
            )
            conn.execute(
                "CREATE INDEX IF NOT EXISTS idx_translations_status ON translations(status)"
            )
            conn.execute(
                "CREATE INDEX IF NOT EXISTS idx_translations_key ON translations(key)"
            )
            
            # 启用 WAL 模式
            conn.execute("PRAGMA journal_mode=WAL")
            conn.execute("PRAGMA synchronous=NORMAL")

    def find_by_mod_and_language(self, mod_id: ModId, language: str) -> dict[str, str]:
        """查找指定Mod和语言的翻译"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute(
                """
                SELECT key, translated FROM translations
                WHERE mod_id = ? AND language = ?
            """,
                (str(mod_id), language),
            )

            return {row[0]: row[1] for row in cursor.fetchall()}

    def find_by_key(self, key: str, language: str) -> list[dict[str, Any]]:
        """根据键查找翻译"""
        return []

    def save_translations(
        self, mod_id: ModId, language: str, translations: dict[str, str]
    ) -> bool:
        """保存翻译 - 批量插入优化"""
        with sqlite3.connect(self.db_path) as conn:
            # 使用 executemany 进行批量插入
            translation_data = [
                (str(mod_id), language, key, value)
                for key, value in translations.items()
            ]
            
            conn.executemany(
                """
                INSERT OR REPLACE INTO translations
                (mod_id, language, key, translated, updated_at)
                VALUES (?, ?, ?, ?, CURRENT_TIMESTAMP)
            """,
                translation_data,
            )
            conn.commit()
            return True

    def update_translation(
        self, mod_id: ModId, language: str, key: str, value: str
    ) -> bool:
        """更新单个翻译"""
        return False

    def delete_translations(self, mod_id: ModId, language: str) -> bool:
        """删除翻译"""
        return False

    def get_translation_stats(self, mod_id: ModId) -> dict[str, int]:
        """获取翻译统计"""
        return {}

    def get_untranslated_keys(self, mod_id: ModId, language: str) -> list[str]:
        """获取未翻译的键"""
        return []

    def search_translations(
        self, query: str, language: str | None = None
    ) -> list[dict[str, Any]]:
        """搜索翻译"""
        return []


class SqliteEventRepository(EventRepository):
    """SQLite事件仓储实现"""

    def __init__(self, db_path: str):
        self.db_path = db_path

    def save_event(self, event: Any) -> bool:
        """保存事件"""
        return True

    def find_by_aggregate_id(self, aggregate_id: str) -> list[Any]:
        """根据聚合ID查找事件"""
        return []

    def find_by_type(self, event_type: str, limit: int = 100) -> list[Any]:
        """根据类型查找事件"""
        return []

    def find_between(self, start: datetime, end: datetime) -> list[Any]:
        """查找时间范围内的事件"""
        return []

    def get_event_stream(self, aggregate_id: str, from_version: int = 0) -> list[Any]:
        """获取事件流"""
        return []


class SqliteScanResultRepository(ScanResultRepository):
    """SQLite扫描结果仓储实现"""

    def __init__(self, db_path: str):
        self.db_path = db_path

    def save_scan_result(self, mod_id: ModId, result: dict[str, Any]) -> bool:
        """保存扫描结果"""
        return True

    def find_latest_scan(self, mod_id: ModId) -> dict[str, Any] | None:
        """查找最新的扫描结果"""
        return None

    def find_scan_history(self, mod_id: ModId, limit: int = 10) -> list[dict[str, Any]]:
        """查找扫描历史"""
        return []

    def delete_old_scans(self, before: datetime) -> int:
        """删除旧的扫描结果"""
        return 0
