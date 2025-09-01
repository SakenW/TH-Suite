# packages/adapters/minecraft/repository.py
"""
Minecraft 项目仓储实现

实现 ProjectRepository 接口，提供 Minecraft 项目数据的持久化操作。
支持项目信息、MOD信息、语言文件等数据的增删改查。
"""

from __future__ import annotations

import json
import sqlite3
from datetime import UTC, datetime
from pathlib import Path

from ...core.errors import EntityNotFoundError, RepositoryError
from ...core.types import LanguageFileInfo, ModInfo, ProjectInfo, ProjectScanResult


class MinecraftProjectRepository:
    """Minecraft 项目仓储实现"""

    def __init__(self, db_path: Path | None = None):
        self.db_path = db_path or Path("minecraft_projects.db")
        self._connection: sqlite3.Connection | None = None
        self._initialized = False

    async def initialize(self) -> None:
        """初始化仓储"""
        if self._initialized:
            return

        await self._create_tables()
        self._initialized = True

    async def _create_tables(self) -> None:
        """创建数据库表"""
        try:
            conn = await self._get_connection()

            # 项目表
            conn.execute("""
                CREATE TABLE IF NOT EXISTS projects (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT NOT NULL,
                    path TEXT UNIQUE NOT NULL,
                    project_type TEXT NOT NULL,
                    game_type TEXT NOT NULL DEFAULT 'minecraft',
                    loader_type TEXT,
                    minecraft_versions TEXT,  -- JSON array
                    total_mods INTEGER DEFAULT 0,
                    total_language_files INTEGER DEFAULT 0,
                    supported_languages TEXT,  -- JSON array
                    metadata TEXT,  -- JSON object
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    last_scan_at TIMESTAMP,
                    is_active BOOLEAN DEFAULT 1
                )
            """)

            # MOD 表
            conn.execute("""
                CREATE TABLE IF NOT EXISTS mods (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    project_id INTEGER NOT NULL,
                    name TEXT NOT NULL,
                    mod_id TEXT NOT NULL,
                    version TEXT,
                    description TEXT,
                    authors TEXT,  -- JSON array
                    file_path TEXT NOT NULL,
                    file_size INTEGER DEFAULT 0,
                    loader_type TEXT,
                    minecraft_versions TEXT,  -- JSON array
                    dependencies TEXT,  -- JSON object
                    language_files_count INTEGER DEFAULT 0,
                    supported_languages TEXT,  -- JSON array
                    metadata TEXT,  -- JSON object
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (project_id) REFERENCES projects (id) ON DELETE CASCADE
                )
            """)

            # 语言文件表
            conn.execute("""
                CREATE TABLE IF NOT EXISTS language_files (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    project_id INTEGER NOT NULL,
                    mod_id INTEGER,  -- NULL for project-level files
                    file_path TEXT NOT NULL,
                    full_path TEXT NOT NULL,
                    language_code TEXT,
                    file_format TEXT NOT NULL,
                    file_size INTEGER DEFAULT 0,
                    is_archived BOOLEAN DEFAULT 0,
                    encoding TEXT DEFAULT 'utf-8',
                    keys_count INTEGER DEFAULT 0,
                    hash_value TEXT,  -- File content hash for change detection
                    metadata TEXT,  -- JSON object
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (project_id) REFERENCES projects (id) ON DELETE CASCADE,
                    FOREIGN KEY (mod_id) REFERENCES mods (id) ON DELETE CASCADE
                )
            """)

            # 语言条目表（可选，用于详细的翻译管理）
            conn.execute("""
                CREATE TABLE IF NOT EXISTS language_entries (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    language_file_id INTEGER NOT NULL,
                    key_name TEXT NOT NULL,
                    value_text TEXT,
                    comment TEXT,
                    metadata TEXT,  -- JSON object
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (language_file_id) REFERENCES language_files (id) ON DELETE CASCADE,
                    UNIQUE(language_file_id, key_name)
                )
            """)

            # 扫描历史表
            conn.execute("""
                CREATE TABLE IF NOT EXISTS scan_history (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    project_id INTEGER NOT NULL,
                    scan_type TEXT NOT NULL,  -- 'full', 'incremental'
                    scan_status TEXT NOT NULL,  -- 'success', 'failed', 'partial'
                    files_scanned INTEGER DEFAULT 0,
                    mods_found INTEGER DEFAULT 0,
                    language_files_found INTEGER DEFAULT 0,
                    errors_count INTEGER DEFAULT 0,
                    duration_seconds REAL DEFAULT 0,
                    scan_summary TEXT,  -- JSON object
                    error_details TEXT,  -- JSON object
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (project_id) REFERENCES projects (id) ON DELETE CASCADE
                )
            """)

            # 创建索引
            conn.execute(
                "CREATE INDEX IF NOT EXISTS idx_projects_path ON projects (path)"
            )
            conn.execute(
                "CREATE INDEX IF NOT EXISTS idx_projects_type ON projects (project_type)"
            )
            conn.execute(
                "CREATE INDEX IF NOT EXISTS idx_mods_project_id ON mods (project_id)"
            )
            conn.execute("CREATE INDEX IF NOT EXISTS idx_mods_mod_id ON mods (mod_id)")
            conn.execute(
                "CREATE INDEX IF NOT EXISTS idx_language_files_project_id ON language_files (project_id)"
            )
            conn.execute(
                "CREATE INDEX IF NOT EXISTS idx_language_files_mod_id ON language_files (mod_id)"
            )
            conn.execute(
                "CREATE INDEX IF NOT EXISTS idx_language_files_language ON language_files (language_code)"
            )
            conn.execute(
                "CREATE INDEX IF NOT EXISTS idx_language_entries_file_id ON language_entries (language_file_id)"
            )
            conn.execute(
                "CREATE INDEX IF NOT EXISTS idx_scan_history_project_id ON scan_history (project_id)"
            )

            conn.commit()

        except sqlite3.Error as e:
            raise RepositoryError(f"初始化数据库失败: {e}") from e

    async def _get_connection(self) -> sqlite3.Connection:
        """获取数据库连接"""
        if not self._connection:
            self._connection = sqlite3.connect(
                self.db_path, check_same_thread=False, timeout=30.0
            )
            self._connection.row_factory = sqlite3.Row
            # 启用外键约束
            self._connection.execute("PRAGMA foreign_keys = ON")
        return self._connection

    async def add_project(self, project_info: ProjectInfo) -> int:
        """添加项目

        Args:
            project_info: 项目信息

        Returns:
            项目 ID
        """
        try:
            conn = await self._get_connection()

            cursor = conn.execute(
                """
                INSERT INTO projects (
                    name, path, project_type, game_type, loader_type,
                    minecraft_versions, total_mods, total_language_files,
                    supported_languages, metadata, last_scan_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
                (
                    project_info.name,
                    project_info.path,
                    project_info.project_type,
                    project_info.game_type,
                    project_info.loader_type,
                    json.dumps(project_info.minecraft_versions),
                    project_info.total_mods,
                    project_info.total_language_files,
                    json.dumps(project_info.supported_languages),
                    json.dumps(project_info.metadata)
                    if project_info.metadata
                    else None,
                    datetime.now(UTC).isoformat(),
                ),
            )

            conn.commit()
            return cursor.lastrowid

        except sqlite3.IntegrityError as e:
            if "UNIQUE constraint failed" in str(e):
                raise RepositoryError(f"项目路径已存在: {project_info.path}") from e
            raise RepositoryError(f"添加项目失败: {e}") from e
        except sqlite3.Error as e:
            raise RepositoryError(f"数据库操作失败: {e}") from e

    async def get_project_by_id(self, project_id: int) -> ProjectInfo | None:
        """根据 ID 获取项目"""
        try:
            conn = await self._get_connection()
            row = conn.execute(
                "SELECT * FROM projects WHERE id = ? AND is_active = 1", (project_id,)
            ).fetchone()

            if not row:
                return None

            return self._row_to_project_info(row)

        except sqlite3.Error as e:
            raise RepositoryError(f"查询项目失败: {e}") from e

    async def get_project_by_path(self, path: str) -> ProjectInfo | None:
        """根据路径获取项目"""
        try:
            conn = await self._get_connection()
            row = conn.execute(
                "SELECT * FROM projects WHERE path = ? AND is_active = 1", (path,)
            ).fetchone()

            if not row:
                return None

            return self._row_to_project_info(row)

        except sqlite3.Error as e:
            raise RepositoryError(f"查询项目失败: {e}") from e

    async def update_project(self, project_id: int, project_info: ProjectInfo) -> None:
        """更新项目信息"""
        try:
            conn = await self._get_connection()

            result = conn.execute(
                """
                UPDATE projects SET
                    name = ?, project_type = ?, loader_type = ?,
                    minecraft_versions = ?, total_mods = ?, total_language_files = ?,
                    supported_languages = ?, metadata = ?, updated_at = CURRENT_TIMESTAMP,
                    last_scan_at = ?
                WHERE id = ? AND is_active = 1
            """,
                (
                    project_info.name,
                    project_info.project_type,
                    project_info.loader_type,
                    json.dumps(project_info.minecraft_versions),
                    project_info.total_mods,
                    project_info.total_language_files,
                    json.dumps(project_info.supported_languages),
                    json.dumps(project_info.metadata)
                    if project_info.metadata
                    else None,
                    datetime.now(UTC).isoformat(),
                    project_id,
                ),
            )

            if result.rowcount == 0:
                raise EntityNotFoundError(f"项目不存在: ID {project_id}")

            conn.commit()

        except sqlite3.Error as e:
            raise RepositoryError(f"更新项目失败: {e}") from e

    async def delete_project(self, project_id: int) -> None:
        """删除项目（软删除）"""
        try:
            conn = await self._get_connection()

            result = conn.execute(
                "UPDATE projects SET is_active = 0, updated_at = CURRENT_TIMESTAMP WHERE id = ?",
                (project_id,),
            )

            if result.rowcount == 0:
                raise EntityNotFoundError(f"项目不存在: ID {project_id}")

            conn.commit()

        except sqlite3.Error as e:
            raise RepositoryError(f"删除项目失败: {e}") from e

    async def list_projects(
        self,
        project_type: str | None = None,
        game_type: str | None = None,
        limit: int = 100,
        offset: int = 0,
    ) -> list[ProjectInfo]:
        """列出项目"""
        try:
            conn = await self._get_connection()

            query = "SELECT * FROM projects WHERE is_active = 1"
            params = []

            if project_type:
                query += " AND project_type = ?"
                params.append(project_type)

            if game_type:
                query += " AND game_type = ?"
                params.append(game_type)

            query += " ORDER BY updated_at DESC LIMIT ? OFFSET ?"
            params.extend([limit, offset])

            rows = conn.execute(query, params).fetchall()

            return [self._row_to_project_info(row) for row in rows]

        except sqlite3.Error as e:
            raise RepositoryError(f"列出项目失败: {e}") from e

    async def add_mods_bulk(self, project_id: int, mods: list[ModInfo]) -> None:
        """批量添加 MOD"""
        try:
            conn = await self._get_connection()

            # 先清理该项目的旧 MOD 数据
            conn.execute("DELETE FROM mods WHERE project_id = ?", (project_id,))

            # 批量插入新数据
            mod_data = []
            for mod in mods:
                mod_data.append(
                    (
                        project_id,
                        mod.name,
                        mod.mod_id,
                        mod.version,
                        mod.description,
                        json.dumps(mod.authors),
                        mod.file_path,
                        mod.file_size,
                        mod.loader_type,
                        json.dumps(mod.minecraft_versions),
                        json.dumps(mod.dependencies) if mod.dependencies else None,
                        mod.language_files_count,
                        json.dumps(mod.supported_languages),
                        json.dumps(mod.metadata) if mod.metadata else None,
                    )
                )

            conn.executemany(
                """
                INSERT INTO mods (
                    project_id, name, mod_id, version, description, authors,
                    file_path, file_size, loader_type, minecraft_versions,
                    dependencies, language_files_count, supported_languages, metadata
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
                mod_data,
            )

            conn.commit()

        except sqlite3.Error as e:
            raise RepositoryError(f"批量添加MOD失败: {e}") from e

    async def get_mods_by_project(self, project_id: int) -> list[ModInfo]:
        """获取项目的所有 MOD"""
        try:
            conn = await self._get_connection()
            rows = conn.execute(
                "SELECT * FROM mods WHERE project_id = ? ORDER BY name", (project_id,)
            ).fetchall()

            return [self._row_to_mod_info(row) for row in rows]

        except sqlite3.Error as e:
            raise RepositoryError(f"查询MOD失败: {e}") from e

    async def add_language_files_bulk(
        self,
        project_id: int,
        language_files: list[LanguageFileInfo],
        mod_id_mapping: dict[str, int] | None = None,
    ) -> None:
        """批量添加语言文件"""
        try:
            conn = await self._get_connection()

            # 清理旧数据
            conn.execute(
                "DELETE FROM language_files WHERE project_id = ?", (project_id,)
            )

            # 准备数据
            file_data = []
            for lang_file in language_files:
                # 根据文件路径确定所属 MOD
                mod_id = None
                if mod_id_mapping:
                    for mod_path, mid in mod_id_mapping.items():
                        if lang_file.full_path.startswith(mod_path):
                            mod_id = mid
                            break

                file_data.append(
                    (
                        project_id,
                        mod_id,
                        lang_file.file_path,
                        lang_file.full_path,
                        lang_file.language_code,
                        lang_file.file_format,
                        lang_file.file_size,
                        lang_file.is_archived,
                        lang_file.encoding,
                        lang_file.keys_count,
                        lang_file.hash_value,
                        json.dumps(lang_file.metadata) if lang_file.metadata else None,
                    )
                )

            conn.executemany(
                """
                INSERT INTO language_files (
                    project_id, mod_id, file_path, full_path, language_code,
                    file_format, file_size, is_archived, encoding, keys_count,
                    hash_value, metadata
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
                file_data,
            )

            conn.commit()

        except sqlite3.Error as e:
            raise RepositoryError(f"批量添加语言文件失败: {e}") from e

    async def get_language_files_by_project(
        self, project_id: int, language_code: str | None = None
    ) -> list[LanguageFileInfo]:
        """获取项目的语言文件"""
        try:
            conn = await self._get_connection()

            query = "SELECT * FROM language_files WHERE project_id = ?"
            params = [project_id]

            if language_code:
                query += " AND language_code = ?"
                params.append(language_code)

            query += " ORDER BY file_path"

            rows = conn.execute(query, params).fetchall()

            return [self._row_to_language_file_info(row) for row in rows]

        except sqlite3.Error as e:
            raise RepositoryError(f"查询语言文件失败: {e}") from e

    async def save_scan_result(
        self, project_id: int, scan_result: ProjectScanResult
    ) -> None:
        """保存扫描结果"""
        try:
            # 获取或创建项目记录
            existing_project = await self.get_project_by_id(project_id)
            if not existing_project:
                project_id = await self.add_project(scan_result.project_info)
            else:
                await self.update_project(project_id, scan_result.project_info)

            # 保存 MOD 数据
            if scan_result.mods_info:
                await self.add_mods_bulk(project_id, scan_result.mods_info)

            # 构建 MOD ID 映射（用于关联语言文件）
            mods = await self.get_mods_by_project(project_id)
            mod_id_mapping = {
                mod.file_path: mod.id for mod in mods if hasattr(mod, "id")
            }

            # 保存语言文件数据
            if scan_result.language_files:
                await self.add_language_files_bulk(
                    project_id, scan_result.language_files, mod_id_mapping
                )

            # 记录扫描历史
            await self._add_scan_history(project_id, scan_result)

        except Exception as e:
            raise RepositoryError(f"保存扫描结果失败: {e}") from e

    async def _add_scan_history(
        self, project_id: int, scan_result: ProjectScanResult
    ) -> None:
        """添加扫描历史记录"""
        try:
            conn = await self._get_connection()

            conn.execute(
                """
                INSERT INTO scan_history (
                    project_id, scan_type, scan_status, files_scanned,
                    mods_found, language_files_found, scan_summary
                ) VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
                (
                    project_id,
                    "full",  # 扫描类型
                    "success" if scan_result.success else "failed",
                    0,  # 文件扫描数量（待实现）
                    len(scan_result.mods_info) if scan_result.mods_info else 0,
                    len(scan_result.language_files)
                    if scan_result.language_files
                    else 0,
                    json.dumps(scan_result.scan_summary)
                    if scan_result.scan_summary
                    else None,
                ),
            )

            conn.commit()

        except sqlite3.Error:
            # 记录历史失败不应影响主流程
            pass

    def _row_to_project_info(self, row: sqlite3.Row) -> ProjectInfo:
        """将数据行转换为项目信息"""
        return ProjectInfo(
            id=row["id"] if "id" in row.keys() else None,
            name=row["name"],
            path=row["path"],
            project_type=row["project_type"],
            game_type=row["game_type"],
            loader_type=row["loader_type"],
            minecraft_versions=json.loads(row["minecraft_versions"])
            if row["minecraft_versions"]
            else [],
            total_mods=row["total_mods"],
            total_language_files=row["total_language_files"],
            supported_languages=json.loads(row["supported_languages"])
            if row["supported_languages"]
            else [],
            metadata=json.loads(row["metadata"]) if row["metadata"] else None,
            created_at=row["created_at"] if "created_at" in row.keys() else None,
            updated_at=row["updated_at"] if "updated_at" in row.keys() else None,
            last_scan_at=row["last_scan_at"] if "last_scan_at" in row.keys() else None,
        )

    def _row_to_mod_info(self, row: sqlite3.Row) -> ModInfo:
        """将数据行转换为 MOD 信息"""
        return ModInfo(
            id=row["id"] if "id" in row.keys() else None,
            name=row["name"],
            mod_id=row["mod_id"],
            version=row["version"],
            description=row["description"],
            authors=json.loads(row["authors"]) if row["authors"] else [],
            file_path=row["file_path"],
            file_size=row["file_size"],
            loader_type=row["loader_type"],
            minecraft_versions=json.loads(row["minecraft_versions"])
            if row["minecraft_versions"]
            else [],
            dependencies=json.loads(row["dependencies"]) if row["dependencies"] else [],
            language_files_count=row["language_files_count"],
            supported_languages=json.loads(row["supported_languages"])
            if row["supported_languages"]
            else [],
            metadata=json.loads(row["metadata"]) if row["metadata"] else None,
        )

    def _row_to_language_file_info(self, row: sqlite3.Row) -> LanguageFileInfo:
        """将数据行转换为语言文件信息"""
        return LanguageFileInfo(
            id=row["id"] if "id" in row.keys() else None,
            file_path=row["file_path"],
            full_path=row["full_path"],
            language_code=row["language_code"],
            file_format=row["file_format"],
            file_size=row["file_size"],
            is_archived=bool(row["is_archived"]),
            encoding=row["encoding"],
            keys_count=row["keys_count"],
            hash_value=row["hash_value"],
            metadata=json.loads(row["metadata"]) if row["metadata"] else None,
        )

    async def close(self) -> None:
        """关闭连接"""
        if self._connection:
            self._connection.close()
            self._connection = None
            self._initialized = False


class MinecraftUnitOfWork:
    """Minecraft 工作单元实现"""

    def __init__(self, repository: MinecraftProjectRepository):
        self.repository = repository
        self._transaction_active = False

    async def __aenter__(self) -> MinecraftUnitOfWork:
        conn = await self.repository._get_connection()
        conn.execute("BEGIN TRANSACTION")
        self._transaction_active = True
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb) -> None:
        if self._transaction_active:
            conn = await self.repository._get_connection()
            if exc_type is None:
                conn.commit()
            else:
                conn.rollback()
            self._transaction_active = False

    async def commit(self) -> None:
        """提交事务"""
        if self._transaction_active:
            conn = await self.repository._get_connection()
            conn.commit()

    async def rollback(self) -> None:
        """回滚事务"""
        if self._transaction_active:
            conn = await self.repository._get_connection()
            conn.rollback()
