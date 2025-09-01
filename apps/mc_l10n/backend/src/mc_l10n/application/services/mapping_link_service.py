from typing import Any

import structlog

from packages.core.database import SQLCipherDatabase

logger = structlog.get_logger(__name__)


class MappingLinkService:
    """映射链接管理服务"""

    def __init__(self, database: SQLCipherDatabase):
        self.db = database

    def create_mapping_link(
        self,
        local_entry_id: int,
        server_content_id: str,
        link_state: str = "active",  # Keep parameter for compatibility but don't use
    ) -> int:
        """创建映射链接"""
        try:
            # Note: link_state column doesn't exist in the database table

            query = """
                INSERT INTO mapping_link (
                    local_id, server_content_id
                ) VALUES (?, ?)
            """

            with self.db._get_connection() as conn:
                cursor = conn.execute(query, (local_entry_id, server_content_id))

            link_id = cursor.lastrowid
            conn.commit()

            logger.info(
                f"Created mapping link {link_id} between local entry {local_entry_id} and server content {server_content_id}"
            )
            return link_id

        except Exception as e:
            logger.error(f"Failed to create mapping link: {e}")
            # rollback handled by context manager
            raise

    def get_mapping_link(self, link_id: int) -> dict[str, Any] | None:
        """获取映射链接"""
        try:
            query = """
                SELECT ml.link_id, ml.local_id, ml.server_content_id, ml.link_state,
                       ml.created_at, ml.updated_at,
                       le.source_file, le.namespace, le.keys_sha256_hex, le.lang_mc,
                       le.content_json
                FROM mapping_link ml
                JOIN local_entries le ON ml.local_id = le.local_id
                WHERE ml.link_id = ?
            """

            with self.db._get_connection() as conn:
                cursor = conn.execute(query, (link_id,))
            row = cursor.fetchone()

            if not row:
                return None

            return self._link_row_to_dict(row)

        except Exception as e:
            logger.error(f"Failed to get mapping link {link_id}: {e}")
            raise

    def get_link_by_local_entry(self, local_entry_id: int) -> dict[str, Any] | None:
        """根据本地条目ID获取映射链接"""
        try:
            query = """
                SELECT ml.link_id, ml.local_id, ml.server_content_id, ml.link_state,
                       ml.created_at, ml.updated_at,
                       le.source_file, le.namespace, le.keys_sha256_hex, le.lang_mc,
                       le.content_json
                FROM mapping_link ml
                JOIN local_entries le ON ml.local_id = le.local_id
                WHERE ml.local_id = ? AND ml.link_state = 'active'
            """

            with self.db._get_connection() as conn:
                cursor = conn.execute(query, (local_entry_id,))
            row = cursor.fetchone()

            if not row:
                return None

            return self._link_row_to_dict(row)

        except Exception as e:
            logger.error(
                f"Failed to get mapping link for local entry {local_entry_id}: {e}"
            )
            raise

    def get_link_by_server_content(
        self, server_content_id: str
    ) -> dict[str, Any] | None:
        """根据服务器内容ID获取映射链接"""
        try:
            query = """
                SELECT ml.link_id, ml.local_entry_id, ml.server_content_id, ml.link_state,
                       ml.created_at, ml.updated_at,
                       le.source_file, le.namespace, le.keys_sha256_hex, le.lang_mc,
                       le.content_json
                FROM mapping_link ml
                JOIN local_entries le ON ml.local_entry_id = le.entry_id
                WHERE ml.server_content_id = ? AND ml.link_state = 'active'
            """

            with self.db._get_connection() as conn:
                cursor = conn.execute(query, (server_content_id,))
            row = cursor.fetchone()

            if not row:
                return None

            return self._link_row_to_dict(row)

        except Exception as e:
            logger.error(
                f"Failed to get mapping link for server content {server_content_id}: {e}"
            )
            raise

    def list_mapping_links(
        self,
        link_state: str | None = None,
        namespace: str | None = None,
        lang_mc: str | None = None,
        limit: int = 100,
        offset: int = 0,
    ) -> list[dict[str, Any]]:
        """列出映射链接"""
        try:
            conditions = []
            params = []

            # link_state column doesn't exist in the database table
            # if link_state:
            #     conditions.append("ml.link_state = ?")
            #     params.append(link_state)

            if namespace:
                conditions.append("mp.proposed_namespace LIKE ?")
                params.append(f"%{namespace}%")

            if lang_mc:
                conditions.append("mp.lang_mc = ?")
                params.append(lang_mc)

            where_clause = "WHERE " + " AND ".join(conditions) if conditions else ""

            query = f"""
                SELECT ml.link_id, ml.local_id, ml.server_content_id,
                       ml.created_at,
                       le.source_file, mp.proposed_namespace, mp.keyhash_hex_local, mp.lang_mc,
                       le.source_payload_json
                FROM mapping_link ml
                JOIN local_entries le ON ml.local_id = le.local_id
                LEFT JOIN mapping_plan mp ON ml.local_id = mp.local_id
                {where_clause}
                ORDER BY ml.created_at DESC
                LIMIT ? OFFSET ?
            """

            params.extend([limit, offset])
            with self.db._get_connection() as conn:
                cursor = conn.execute(query, params)
                rows = cursor.fetchall()

            return [self._link_row_to_dict(row) for row in rows]

        except Exception as e:
            logger.error(f"Failed to list mapping links: {e}")
            raise

    def update_link_state(self, link_id: int, link_state: str) -> bool:
        """更新链接状态 - 注意：link_state列在数据库中不存在，此方法保留以兼容性"""
        try:
            # Note: link_state column doesn't exist in the database table
            # This method is kept for compatibility but doesn't perform any actual update
            logger.warning(
                f"update_link_state called for link {link_id} but link_state column doesn't exist"
            )

            # Check if the link exists
            query = "SELECT link_id FROM mapping_link WHERE link_id = ?"
            with self.db._get_connection() as conn:
                cursor = conn.execute(query, (link_id,))
                exists = cursor.fetchone() is not None

            if exists:
                logger.info(f"Mapping link {link_id} exists (state update skipped)")

            return exists

        except Exception as e:
            logger.error(f"Failed to check mapping link {link_id}: {e}")
            raise

    def delete_mapping_link(self, link_id: int) -> bool:
        """删除映射链接"""
        try:
            query = "DELETE FROM mapping_link WHERE link_id = ?"

            with self.db._get_connection() as conn:
                cursor = conn.execute(query, (link_id,))
            conn.commit()

            deleted = cursor.rowcount > 0
            if deleted:
                logger.info(f"Deleted mapping link {link_id}")

            return deleted

        except Exception as e:
            logger.error(f"Failed to delete mapping link {link_id}: {e}")
            # rollback handled by context manager
            raise

    def find_potential_matches(
        self, namespace: str, keys_sha256_hex: str, lang_mc: str
    ) -> list[dict[str, Any]]:
        """查找潜在的匹配项"""
        try:
            # 查找具有相同命名空间、键哈希和语言的本地条目
            query = """
                SELECT le.entry_id, le.source_file, le.namespace, le.keys_sha256_hex,
                       le.lang_mc, le.content_json, le.created_at, le.updated_at,
                       ml.link_id, ml.server_content_id, ml.link_state
                FROM local_entries le
                LEFT JOIN mapping_link ml ON le.entry_id = ml.local_entry_id
                WHERE le.namespace LIKE ? AND le.keys_sha256_hex = ? AND le.lang_mc = ?
                ORDER BY le.updated_at DESC
            """

            with self.db._get_connection() as conn:
                cursor = conn.execute(
                    query, (f"%{namespace}%", keys_sha256_hex, lang_mc)
                )
            rows = cursor.fetchall()

            results = []
            for row in rows:
                result = {
                    "entry_id": row[0],
                    "source_file": row[1],
                    "namespace": row[2],
                    "keys_sha256_hex": row[3],
                    "lang_mc": row[4],
                    "content_json": row[5],
                    "created_at": row[6],
                    "updated_at": row[7],
                    "has_link": row[8] is not None,
                    "link_id": row[8],
                    "server_content_id": row[9],
                    "link_state": row[10],
                }
                results.append(result)

            return results

        except Exception as e:
            logger.error(f"Failed to find potential matches: {e}")
            raise

    def create_auto_mapping(
        self, namespace: str, keys_sha256_hex: str, lang_mc: str, server_content_id: str
    ) -> int | None:
        """自动创建映射"""
        try:
            # 查找匹配的本地条目
            matches = self.find_potential_matches(namespace, keys_sha256_hex, lang_mc)

            # 找到未链接的最新条目
            unlinked_matches = [m for m in matches if not m["has_link"]]

            if not unlinked_matches:
                logger.warning("No unlinked local entries found for auto mapping")
                return None

            # 选择最新的条目
            best_match = unlinked_matches[0]

            # 创建映射链接
            link_id = self.create_mapping_link(
                best_match["entry_id"], server_content_id, "active"
            )

            logger.info(
                f"Auto-created mapping link {link_id} for entry {best_match['entry_id']}"
            )
            return link_id

        except Exception as e:
            logger.error(f"Failed to create auto mapping: {e}")
            raise

    def get_unmapped_local_entries(
        self, namespace: str | None = None, lang_mc: str | None = None, limit: int = 100
    ) -> list[dict[str, Any]]:
        """获取未映射的本地条目"""
        try:
            conditions = ["ml.link_id IS NULL"]
            params = []

            if namespace:
                conditions.append("le.namespace LIKE ?")
                params.append(f"%{namespace}%")

            if lang_mc:
                conditions.append("le.lang_mc = ?")
                params.append(lang_mc)

            where_clause = "WHERE " + " AND ".join(conditions)

            query = f"""
                SELECT le.local_id, le.source_file, le.namespace, le.keys_sha256_hex,
                       le.lang_mc, le.content_json, le.created_at, le.updated_at
                FROM local_entries le
                LEFT JOIN mapping_link ml ON le.local_id = ml.local_id AND ml.link_state = 'active'
                {where_clause}
                ORDER BY le.updated_at DESC
                LIMIT ?
            """

            params.append(limit)
            with self.db._get_connection() as conn:
                cursor = conn.execute(query, params)
            rows = cursor.fetchall()

            return [
                {
                    "local_id": row[0],
                    "source_file": row[1],
                    "namespace": row[2],
                    "keys_sha256_hex": row[3],
                    "lang_mc": row[4],
                    "content_json": row[5],
                    "created_at": row[6],
                    "updated_at": row[7],
                }
                for row in rows
            ]

        except Exception as e:
            logger.error(f"Failed to get unmapped local entries: {e}")
            raise

    def get_mapping_statistics(self) -> dict[str, Any]:
        """获取映射统计信息"""
        try:
            # 链接状态统计
            link_stats_query = """
                SELECT link_state, COUNT(*) as count
                FROM mapping_link
                GROUP BY link_state
            """

            with self.db._get_connection() as conn:
                cursor = conn.execute(link_stats_query)
            link_stats = {row[0]: row[1] for row in cursor.fetchall()}

            # 总体统计
            total_query = """
                SELECT
                    (SELECT COUNT(*) FROM local_entries) as total_local_entries,
                    (SELECT COUNT(*) FROM mapping_link WHERE link_state = 'active') as active_mappings,
                    (SELECT COUNT(*) FROM local_entries le
                     LEFT JOIN mapping_link ml ON le.entry_id = ml.local_entry_id AND ml.link_state = 'active'
                     WHERE ml.link_id IS NULL) as unmapped_entries
            """

            with self.db._get_connection() as conn:
                cursor = conn.execute(total_query)
            total_row = cursor.fetchone()

            return {
                "link_states": link_stats,
                "total_local_entries": total_row[0] if total_row else 0,
                "active_mappings": total_row[1] if total_row else 0,
                "unmapped_entries": total_row[2] if total_row else 0,
            }

        except Exception as e:
            logger.error(f"Failed to get mapping statistics: {e}")
            raise

    def _link_row_to_dict(self, row) -> dict[str, Any]:
        """将映射链接行转换为字典"""
        return {
            "link_id": row[0],
            "local_id": row[1],
            "server_content_id": row[2],
            "created_at": row[3],
            "local_entry": {
                "source_file": row[4],
                "namespace": row[5],  # proposed_namespace from mapping_plan
                "keys_sha256_hex": row[6],  # keyhash_hex_local from mapping_plan
                "lang_mc": row[7],  # lang_mc from mapping_plan
                "content_json": row[8],  # source_payload_json from local_entries
            },
        }
