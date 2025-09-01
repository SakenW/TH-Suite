import json
from typing import Any

import structlog

from packages.core.database import SQLCipherDatabase

logger = structlog.get_logger(__name__)


class LocalEntryService:
    """本地条目管理服务"""

    def __init__(self, database: SQLCipherDatabase):
        self.db = database

    def create_entry(
        self,
        project_id: str,
        source_type: str,
        source_file: str,
        source_locator: str | None = None,
        source_lang_bcp47: str | None = None,
        source_context: dict[str, Any] = None,
        source_payload: dict[str, Any] = None,
        note: str | None = None,
    ) -> int:
        """创建新的本地条目"""
        try:
            source_context_json = json.dumps(source_context or {}, ensure_ascii=False)
            source_payload_json = json.dumps(source_payload or {}, ensure_ascii=False)

            with self.db._get_connection() as conn:
                cursor = conn.execute(
                    """
                    INSERT INTO local_entries (
                        project_id, source_type, source_file, source_locator,
                        source_lang_bcp47, source_context_json, source_payload_json, note
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        project_id,
                        source_type,
                        source_file,
                        source_locator,
                        source_lang_bcp47,
                        source_context_json,
                        source_payload_json,
                        note,
                    ),
                )

                local_id = cursor.lastrowid
                conn.commit()

                logger.info(
                    f"Created local entry {local_id} for {source_type}:{source_file}"
                )
                return local_id

        except Exception as e:
            logger.error(f"Failed to create local entry: {e}")
            raise

    def get_entry(self, local_id: int) -> dict[str, Any] | None:
        """获取单个本地条目"""
        try:
            with self.db._get_connection() as conn:
                row = conn.execute(
                    """
                    SELECT local_id, project_id, source_type, source_file, source_locator,
                           source_lang_bcp47, source_context_json, source_payload_json,
                           note, created_at, updated_at
                    FROM local_entries
                    WHERE local_id = ?
                    """,
                    (local_id,),
                ).fetchone()

                if not row:
                    return None

                return self._row_to_dict(row)

        except Exception as e:
            logger.error(f"Failed to get local entry {local_id}: {e}")
            raise

    def list_entries(
        self,
        project_id: str | None = None,
        source_type: str | None = None,
        limit: int = 100,
        offset: int = 0,
    ) -> list[dict[str, Any]]:
        """列出本地条目"""
        try:
            conditions = []
            params = []

            if project_id:
                conditions.append("project_id = ?")
                params.append(project_id)

            if source_type:
                conditions.append("source_type = ?")
                params.append(source_type)

            where_clause = "WHERE " + " AND ".join(conditions) if conditions else ""

            query = f"""
                SELECT local_id, project_id, source_type, source_file, source_locator,
                       source_lang_bcp47, source_context_json, source_payload_json,
                       note, created_at, updated_at
                FROM local_entries
                {where_clause}
                ORDER BY created_at DESC
                LIMIT ? OFFSET ?
            """

            params.extend([limit, offset])

            with self.db._get_connection() as conn:
                rows = conn.execute(query, params).fetchall()
                return [self._row_to_dict(row) for row in rows]

        except Exception as e:
            logger.error(f"Failed to list local entries: {e}")
            raise

    def list_local_entries(
        self,
        namespace: str | None = None,
        lang_mc: str | None = None,
        source_file: str | None = None,
        limit: int = 100,
        offset: int = 0,
    ) -> list[dict[str, Any]]:
        """列出本地条目（API兼容方法）"""
        try:
            conditions = []
            params = []

            if namespace:
                conditions.append("source_context_json LIKE ?")
                params.append(f'%"namespace":"{namespace}"%')

            if lang_mc:
                conditions.append("source_lang_bcp47 = ?")
                params.append(lang_mc)

            if source_file:
                conditions.append("source_file = ?")
                params.append(source_file)

            where_clause = "WHERE " + " AND ".join(conditions) if conditions else ""

            query = f"""
                SELECT local_id, project_id, source_type, source_file, source_locator,
                       source_lang_bcp47, source_context_json, source_payload_json,
                       note, created_at, updated_at
                FROM local_entries
                {where_clause}
                ORDER BY created_at DESC
                LIMIT ? OFFSET ?
            """

            params.extend([limit, offset])

            with self.db._get_connection() as conn:
                rows = conn.execute(query, params).fetchall()
                return [self._row_to_dict(row) for row in rows]

        except Exception as e:
            logger.error(f"Failed to list local entries: {e}")
            raise

    def update_entry(
        self,
        local_id: int,
        source_locator: str | None = None,
        source_lang_bcp47: str | None = None,
        source_context: dict[str, Any] | None = None,
        source_payload: dict[str, Any] | None = None,
        note: str | None = None,
    ) -> bool:
        """更新本地条目"""
        try:
            updates = []
            params = []

            if source_locator is not None:
                updates.append("source_locator = ?")
                params.append(source_locator)

            if source_lang_bcp47 is not None:
                updates.append("source_lang_bcp47 = ?")
                params.append(source_lang_bcp47)

            if source_context is not None:
                updates.append("source_context_json = ?")
                params.append(json.dumps(source_context, ensure_ascii=False))

            if source_payload is not None:
                updates.append("source_payload_json = ?")
                params.append(json.dumps(source_payload, ensure_ascii=False))

            if note is not None:
                updates.append("note = ?")
                params.append(note)

            if not updates:
                return False

            query = f"""
                UPDATE local_entries
                SET {", ".join(updates)}
                WHERE local_id = ?
            """

            params.append(local_id)

            with self.db._get_connection() as conn:
                cursor = conn.execute(query, params)
                conn.commit()

                updated = cursor.rowcount > 0
                if updated:
                    logger.info(f"Updated local entry {local_id}")

                return updated

        except Exception as e:
            logger.error(f"Failed to update local entry {local_id}: {e}")
            raise

    def delete_entry(self, local_id: int) -> bool:
        """删除本地条目"""
        try:
            with self.db._get_connection() as conn:
                cursor = conn.execute(
                    "DELETE FROM local_entries WHERE local_id = ?", (local_id,)
                )
                conn.commit()

                deleted = cursor.rowcount > 0
                if deleted:
                    logger.info(f"Deleted local entry {local_id}")

                return deleted

        except Exception as e:
            logger.error(f"Failed to delete local entry {local_id}: {e}")
            raise

    def count_entries(
        self, project_id: str | None = None, source_type: str | None = None
    ) -> int:
        """统计本地条目数量"""
        try:
            conditions = []
            params = []

            if project_id:
                conditions.append("project_id = ?")
                params.append(project_id)

            if source_type:
                conditions.append("source_type = ?")
                params.append(source_type)

            where_clause = "WHERE " + " AND ".join(conditions) if conditions else ""

            query = f"SELECT COUNT(*) FROM local_entries {where_clause}"

            with self.db._get_connection() as conn:
                row = conn.execute(query, params).fetchone()
                return row[0] if row else 0

        except Exception as e:
            logger.error(f"Failed to count local entries: {e}")
            raise

    def get_entries_by_source_file(self, source_file: str) -> list[dict[str, Any]]:
        """根据源文件获取条目"""
        try:
            query = """
                SELECT local_id, project_id, source_type, source_file, source_locator,
                       source_lang_bcp47, source_context_json, source_payload_json,
                       note, created_at, updated_at
                FROM local_entries
                WHERE source_file = ?
                ORDER BY created_at DESC
            """

            with self.db._get_connection() as conn:
                rows = conn.execute(query, (source_file,)).fetchall()
                return [self._row_to_dict(row) for row in rows]

        except Exception as e:
            logger.error(f"Failed to get entries by source file {source_file}: {e}")
            raise

    def get_statistics(self) -> dict[str, Any]:
        """获取本地条目统计信息"""
        try:
            with self.db._get_connection() as conn:
                # 总条目数
                total_count = conn.execute(
                    "SELECT COUNT(*) FROM local_entries"
                ).fetchone()[0]

                # 按项目分组统计
                project_stats = conn.execute(
                    "SELECT project_id, COUNT(*) FROM local_entries GROUP BY project_id"
                ).fetchall()

                # 按源类型分组统计
                type_stats = conn.execute(
                    "SELECT source_type, COUNT(*) FROM local_entries GROUP BY source_type"
                ).fetchall()

                return {
                    "total_entries": total_count,
                    "by_project": {row[0]: row[1] for row in project_stats},
                    "by_source_type": {row[0]: row[1] for row in type_stats},
                }

        except Exception as e:
            logger.error(f"Failed to get local entries statistics: {e}")
            raise

    def _row_to_dict(self, row) -> dict[str, Any]:
        """将数据库行转换为字典"""
        return {
            "local_id": row[0],
            "project_id": row[1],
            "source_type": row[2],
            "source_file": row[3],
            "source_locator": row[4],
            "source_lang_bcp47": row[5],
            "source_context": json.loads(row[6]) if row[6] else {},
            "source_payload": json.loads(row[7]) if row[7] else {},
            "note": row[8],
            "created_at": row[9],
            "updated_at": row[10],
        }
