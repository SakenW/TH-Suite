"""
通用UPSERT数据库引擎

职责：
- 提供与游戏无关的数据库UPSERT操作
- 基于内容哈希的去重机制
- 扫描会话和内容分离的数据库设计
- 支持任何类型内容的存储和检索

设计原则：
- 数据库无关：抽象的数据库操作接口
- 内容无关：不依赖特定的内容类型结构
- 事务安全：确保数据一致性
"""

import hashlib
import json
import sqlite3
from abc import ABC, abstractmethod
from datetime import datetime
from pathlib import Path
from typing import Any

from .scanner_interface import (
    ContentItem,
    ContentType,
    ScanProgress,
    ScanStatus,
)


class DatabaseInterface(ABC):
    """数据库操作接口"""

    @abstractmethod
    async def init_schema(self) -> None:
        """初始化数据库结构"""
        pass

    @abstractmethod
    async def upsert_content_item(self, item: ContentItem, scan_id: str) -> str:
        """UPSERT内容项"""
        pass

    @abstractmethod
    async def record_scan_discovery(
        self, scan_id: str, content_hash: str, content_type: ContentType
    ) -> None:
        """记录扫描发现"""
        pass

    @abstractmethod
    async def get_scan_statistics(self, scan_id: str) -> dict[str, int]:
        """获取扫描统计"""
        pass


class UniversalUpsertEngine:
    """通用UPSERT数据库引擎"""

    def __init__(self, db_path: str, game_type: str = "universal"):
        self.db_path = db_path
        self.game_type = game_type
        self._init_schema()

    def _init_schema(self) -> None:
        """初始化通用数据库结构"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        try:
            # === 扫描会话表（通用） ===
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS scan_sessions (
                    scan_id TEXT PRIMARY KEY,
                    game_type TEXT NOT NULL,
                    target_path TEXT NOT NULL,
                    scan_mode TEXT DEFAULT 'incremental',
                    status TEXT DEFAULT 'pending',
                    started_at TEXT NOT NULL,
                    completed_at TEXT,
                    progress_percent REAL DEFAULT 0.0,
                    processed_count INTEGER DEFAULT 0,
                    total_count INTEGER DEFAULT 0,
                    current_item TEXT,
                    error_message TEXT,
                    metadata TEXT  -- JSON格式的元数据
                )
            """)

            # === 内容项目表（通用） ===
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS content_items (
                    content_hash TEXT PRIMARY KEY,
                    content_type TEXT NOT NULL,
                    name TEXT NOT NULL,
                    game_type TEXT NOT NULL,
                    first_discovered TEXT NOT NULL,
                    last_seen TEXT NOT NULL,
                    metadata TEXT,  -- JSON格式的元数据
                    relationships TEXT  -- JSON格式的关系数据
                )
            """)

            # === 扫描发现记录表 ===
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS scan_discoveries (
                    scan_id TEXT NOT NULL,
                    content_hash TEXT NOT NULL,
                    content_type TEXT NOT NULL,
                    discovered_at TEXT NOT NULL,
                    PRIMARY KEY (scan_id, content_hash, content_type),
                    FOREIGN KEY (scan_id) REFERENCES scan_sessions(scan_id),
                    FOREIGN KEY (content_hash) REFERENCES content_items(content_hash)
                )
            """)

            # === 内容关系表 ===
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS content_relationships (
                    parent_hash TEXT NOT NULL,
                    child_hash TEXT NOT NULL,
                    relationship_type TEXT NOT NULL,
                    metadata TEXT,
                    created_at TEXT NOT NULL,
                    PRIMARY KEY (parent_hash, child_hash, relationship_type),
                    FOREIGN KEY (parent_hash) REFERENCES content_items(content_hash),
                    FOREIGN KEY (child_hash) REFERENCES content_items(content_hash)
                )
            """)

            # === 索引优化 ===
            indexes = [
                "CREATE INDEX IF NOT EXISTS idx_content_items_type ON content_items(content_type)",
                "CREATE INDEX IF NOT EXISTS idx_content_items_game ON content_items(game_type)",
                "CREATE INDEX IF NOT EXISTS idx_content_items_name ON content_items(name)",
                "CREATE INDEX IF NOT EXISTS idx_scan_sessions_status ON scan_sessions(status)",
                "CREATE INDEX IF NOT EXISTS idx_scan_sessions_game ON scan_sessions(game_type)",
                "CREATE INDEX IF NOT EXISTS idx_scan_discoveries_scan ON scan_discoveries(scan_id)",
                "CREATE INDEX IF NOT EXISTS idx_scan_discoveries_type ON scan_discoveries(content_type)",
            ]

            for index_sql in indexes:
                cursor.execute(index_sql)

            conn.commit()

        finally:
            conn.close()

    def generate_content_hash(self, content: Any) -> str:
        """生成内容哈希"""
        if isinstance(content, str):
            content_bytes = content.encode("utf-8")
        elif isinstance(content, bytes):
            content_bytes = content
        elif isinstance(content, dict):
            # 对字典进行标准化后计算哈希
            content_json = json.dumps(content, sort_keys=True, ensure_ascii=False)
            content_bytes = content_json.encode("utf-8")
        else:
            content_bytes = str(content).encode("utf-8")

        return hashlib.sha256(content_bytes).hexdigest()

    async def start_scan_session(
        self,
        scan_id: str,
        target_path: Path,
        game_type: str,
        scan_mode: str = "incremental",
        metadata: dict[str, Any] | None = None,
    ) -> None:
        """开始扫描会话"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        try:
            now = datetime.now().isoformat()
            metadata_json = json.dumps(metadata or {})

            cursor.execute(
                """
                INSERT OR REPLACE INTO scan_sessions
                (scan_id, game_type, target_path, scan_mode, status, started_at, metadata)
                VALUES (?, ?, ?, ?, 'pending', ?, ?)
            """,
                (scan_id, game_type, str(target_path), scan_mode, now, metadata_json),
            )

            conn.commit()
        finally:
            conn.close()

    async def update_scan_progress(self, progress: ScanProgress) -> None:
        """更新扫描进度"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        try:
            cursor.execute(
                """
                UPDATE scan_sessions SET
                    status = ?,
                    progress_percent = ?,
                    processed_count = ?,
                    total_count = ?,
                    current_item = ?,
                    error_message = ?,
                    completed_at = ?,
                    metadata = ?
                WHERE scan_id = ?
            """,
                (
                    progress.status.value,
                    progress.progress_percent,
                    progress.processed_count,
                    progress.total_count,
                    progress.current_item,
                    progress.error_message,
                    progress.end_time.isoformat() if progress.end_time else None,
                    json.dumps(progress.metadata),
                    progress.scan_id,
                ),
            )

            conn.commit()
        finally:
            conn.close()

    async def upsert_content_item(self, item: ContentItem) -> str:
        """UPSERT内容项"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        try:
            now = datetime.now().isoformat()

            # 检查是否存在
            cursor.execute(
                "SELECT content_hash, last_seen FROM content_items WHERE content_hash = ?",
                (item.content_hash,),
            )
            existing = cursor.fetchone()

            if existing:
                # 更新现有记录
                cursor.execute(
                    """
                    UPDATE content_items SET
                        name = ?,
                        last_seen = ?,
                        metadata = ?,
                        relationships = ?
                    WHERE content_hash = ?
                """,
                    (
                        item.name,
                        now,
                        json.dumps(item.metadata),
                        json.dumps(item.relationships),
                        item.content_hash,
                    ),
                )
            else:
                # 插入新记录
                cursor.execute(
                    """
                    INSERT INTO content_items
                    (content_hash, content_type, name, game_type, first_discovered, last_seen, metadata, relationships)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                    (
                        item.content_hash,
                        item.content_type.value,
                        item.name,
                        self.game_type,
                        now,
                        now,
                        json.dumps(item.metadata),
                        json.dumps(item.relationships),
                    ),
                )

            conn.commit()
            return item.content_hash

        finally:
            conn.close()

    async def record_scan_discovery(
        self, scan_id: str, content_hash: str, content_type: ContentType
    ) -> None:
        """记录扫描发现"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        try:
            now = datetime.now().isoformat()
            cursor.execute(
                """
                INSERT OR IGNORE INTO scan_discoveries
                (scan_id, content_hash, content_type, discovered_at)
                VALUES (?, ?, ?, ?)
            """,
                (scan_id, content_hash, content_type.value, now),
            )

            conn.commit()
        finally:
            conn.close()

    async def record_content_relationship(
        self,
        parent_hash: str,
        child_hash: str,
        relationship_type: str,
        metadata: dict[str, Any] | None = None,
    ) -> None:
        """记录内容关系"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        try:
            now = datetime.now().isoformat()
            metadata_json = json.dumps(metadata or {})

            cursor.execute(
                """
                INSERT OR REPLACE INTO content_relationships
                (parent_hash, child_hash, relationship_type, metadata, created_at)
                VALUES (?, ?, ?, ?, ?)
            """,
                (parent_hash, child_hash, relationship_type, metadata_json, now),
            )

            conn.commit()
        finally:
            conn.close()

    async def get_scan_statistics(self, scan_id: str) -> dict[str, int]:
        """获取扫描统计"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        try:
            cursor.execute(
                """
                SELECT content_type, COUNT(*) as count
                FROM scan_discoveries
                WHERE scan_id = ?
                GROUP BY content_type
            """,
                (scan_id,),
            )

            stats = {}
            for content_type, count in cursor.fetchall():
                stats[f"total_{content_type}s"] = count

            return stats
        finally:
            conn.close()

    async def get_scan_progress(self, scan_id: str) -> ScanProgress | None:
        """获取扫描进度"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        try:
            cursor.execute(
                """
                SELECT status, progress_percent, processed_count, total_count,
                       current_item, error_message, started_at, completed_at, metadata
                FROM scan_sessions
                WHERE scan_id = ?
            """,
                (scan_id,),
            )

            row = cursor.fetchone()
            if not row:
                return None

            progress = ScanProgress(scan_id)
            progress.status = ScanStatus(row[0])
            progress.progress_percent = row[1]
            progress.processed_count = row[2]
            progress.total_count = row[3]
            progress.current_item = row[4] or ""
            progress.error_message = row[5]
            progress.start_time = datetime.fromisoformat(row[6])
            if row[7]:
                progress.end_time = datetime.fromisoformat(row[7])
            progress.metadata = json.loads(row[8] or "{}")

            return progress

        finally:
            conn.close()

    async def get_content_items(
        self,
        content_type: ContentType | None = None,
        game_type: str | None = None,
        limit: int | None = None,
    ) -> list[ContentItem]:
        """获取内容项列表"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        try:
            query = "SELECT content_hash, content_type, name, metadata, relationships FROM content_items"
            params = []
            conditions = []

            if content_type:
                conditions.append("content_type = ?")
                params.append(content_type.value)

            if game_type:
                conditions.append("game_type = ?")
                params.append(game_type)

            if conditions:
                query += " WHERE " + " AND ".join(conditions)

            query += " ORDER BY last_seen DESC"

            if limit:
                query += " LIMIT ?"
                params.append(limit)

            cursor.execute(query, params)

            items = []
            for row in cursor.fetchall():
                item = ContentItem(
                    content_hash=row[0],
                    content_type=ContentType(row[1]),
                    name=row[2],
                    metadata=json.loads(row[3] or "{}"),
                    relationships=json.loads(row[4] or "{}"),
                )
                items.append(item)

            return items

        finally:
            conn.close()

    async def cleanup_old_sessions(self, days: int = 30) -> int:
        """清理旧的扫描会话"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        try:
            cutoff_date = datetime.now().replace(day=datetime.now().day - days)
            cutoff_iso = cutoff_date.isoformat()

            cursor.execute(
                """
                DELETE FROM scan_sessions
                WHERE started_at < ? AND status IN ('completed', 'failed', 'cancelled')
            """,
                (cutoff_iso,),
            )

            deleted_count = cursor.rowcount
            conn.commit()

            return deleted_count

        finally:
            conn.close()
