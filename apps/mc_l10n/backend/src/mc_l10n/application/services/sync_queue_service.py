import json
from datetime import datetime
from typing import Any

import structlog

from packages.core.database import SQLCipherDatabase

logger = structlog.get_logger(__name__)


class SyncQueueService:
    """双向同步队列管理服务"""

    def __init__(self, database: SQLCipherDatabase):
        self.db = database

    # ==================== Outbound Queue Management ====================

    def create_outbound_item(
        self,
        plan_id: int,
        intent: str,
        submit_payload: dict[str, Any],
        base_etag: str | None = None,
    ) -> int:
        """创建出站队列项"""
        try:
            # 验证意图值
            if intent not in ["upsert", "delete"]:
                raise ValueError(f"Invalid intent: {intent}")

            submit_payload_json = json.dumps(submit_payload, ensure_ascii=False)

            query = """
                INSERT INTO outbound_queue (
                    plan_id, intent, submit_payload_json, base_etag
                ) VALUES (?, ?, ?, ?)
            """

            with self.db._get_connection() as conn:
                cursor = conn.execute(
                    query, (plan_id, intent, submit_payload_json, base_etag)
                )

            queue_id = cursor.lastrowid
            conn.commit()

            logger.info(f"Created outbound queue item {queue_id} for plan {plan_id}")
            return queue_id

        except Exception as e:
            logger.error(f"Failed to create outbound queue item: {e}")
            # rollback handled by context manager
            raise

    def get_outbound_item(self, queue_id: int) -> dict[str, Any] | None:
        """获取出站队列项"""
        try:
            query = """
                SELECT oq.queue_id, oq.plan_id, oq.intent, oq.submit_payload_json,
                       oq.base_etag, oq.queue_state, oq.result_message, oq.server_content_id,
                       oq.submitted_at, oq.updated_at,
                       mp.proposed_namespace, mp.lang_mc
                FROM outbound_queue oq
                JOIN mapping_plan mp ON oq.plan_id = mp.plan_id
                WHERE oq.queue_id = ?
            """

            with self.db._get_connection() as conn:
                cursor = conn.execute(query, (queue_id,))
                row = cursor.fetchone()

                if not row:
                    return None

                return self._outbound_row_to_dict(row)

        except Exception as e:
            logger.error(f"Failed to get outbound queue item {queue_id}: {e}")
            raise

    def list_outbound_items(
        self,
        queue_state: str | None = None,
        intent: str | None = None,
        limit: int = 100,
        offset: int = 0,
    ) -> list[dict[str, Any]]:
        """列出出站队列项"""
        try:
            conditions = []
            params = []

            if queue_state:
                conditions.append("oq.queue_state = ?")
                params.append(queue_state)

            if intent:
                conditions.append("oq.intent = ?")
                params.append(intent)

            where_clause = "WHERE " + " AND ".join(conditions) if conditions else ""

            query = f"""
                SELECT oq.queue_id, oq.plan_id, oq.intent, oq.submit_payload_json,
                       oq.base_etag, oq.queue_state, oq.result_message, oq.server_content_id,
                       oq.submitted_at, oq.updated_at,
                       mp.proposed_namespace, mp.lang_mc
                FROM outbound_queue oq
                JOIN mapping_plan mp ON oq.plan_id = mp.plan_id
                {where_clause}
                ORDER BY oq.updated_at DESC
                LIMIT ? OFFSET ?
            """

            params.extend([limit, offset])
            with self.db._get_connection() as conn:
                cursor = conn.execute(query, params)
                rows = cursor.fetchall()

                return [self._outbound_row_to_dict(row) for row in rows]

        except Exception as e:
            logger.error(f"Failed to list outbound queue items: {e}")
            raise

    def update_outbound_item(
        self,
        queue_id: int,
        queue_state: str | None = None,
        result_message: str | None = None,
        server_content_id: str | None = None,
        submitted_at: str | None = None,
    ) -> bool:
        """更新出站队列项"""
        try:
            updates = []
            params = []

            if queue_state is not None:
                valid_states = [
                    "queued",
                    "submitted",
                    "accepted",
                    "rejected",
                    "conflict",
                    "error",
                ]
                if queue_state not in valid_states:
                    raise ValueError(f"Invalid queue_state: {queue_state}")
                updates.append("queue_state = ?")
                params.append(queue_state)

            if result_message is not None:
                updates.append("result_message = ?")
                params.append(result_message)

            if server_content_id is not None:
                updates.append("server_content_id = ?")
                params.append(server_content_id)

            if submitted_at is not None:
                updates.append("submitted_at = ?")
                params.append(submitted_at)

            if not updates:
                return False

            query = f"""
                UPDATE outbound_queue
                SET {", ".join(updates)}
                WHERE queue_id = ?
            """

            params.append(queue_id)
            with self.db._get_connection() as conn:
                cursor = conn.execute(query, params)
            conn.commit()

            updated = cursor.rowcount > 0
            if updated:
                logger.info(f"Updated outbound queue item {queue_id}")

            return updated

        except Exception as e:
            logger.error(f"Failed to update outbound queue item {queue_id}: {e}")
            # rollback handled by context manager
            raise

    def mark_as_submitted(self, queue_id: int) -> bool:
        """标记为已提交"""
        return self.update_outbound_item(
            queue_id, queue_state="submitted", submitted_at=datetime.now().isoformat()
        )

    def mark_as_accepted(self, queue_id: int, server_content_id: str) -> bool:
        """标记为已接受"""
        return self.update_outbound_item(
            queue_id, queue_state="accepted", server_content_id=server_content_id
        )

    def mark_as_rejected(self, queue_id: int, reason: str) -> bool:
        """标记为已拒绝"""
        return self.update_outbound_item(
            queue_id, queue_state="rejected", result_message=reason
        )

    # ==================== Inbound Snapshot Management ====================

    def create_snapshot(
        self, snapshot_id: str, project_id: str, from_snapshot_id: str | None = None
    ) -> bool:
        """创建入站快照"""
        try:
            query = """
                INSERT INTO inbound_snapshot (
                    snapshot_id, obtained_at, project_id, from_snapshot_id
                ) VALUES (?, ?, ?, ?)
            """

            with self.db._get_connection() as conn:
                conn.execute(
                    query,
                    (
                        snapshot_id,
                        datetime.now().isoformat(),
                        project_id,
                        from_snapshot_id,
                    ),
                )
            conn.commit()

            logger.info(f"Created inbound snapshot {snapshot_id}")
            return True

        except Exception as e:
            logger.error(f"Failed to create inbound snapshot: {e}")
            # rollback handled by context manager
            raise

    def add_inbound_items(self, snapshot_id: str, items: list[dict[str, Any]]) -> int:
        """批量添加入站项目"""
        try:
            query = """
                INSERT INTO inbound_items (
                    snapshot_id, server_content_id, namespace, keys_sha256_hex,
                    lang_mc, server_payload_json, etag, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """

            count = 0
            for item in items:
                server_payload_json = json.dumps(
                    item["server_payload"], ensure_ascii=False
                )

                with self.db._get_connection() as conn:
                    conn.execute(
                        query,
                        (
                            snapshot_id,
                            item["server_content_id"],
                            item["namespace"],
                            item["keys_sha256_hex"],
                            item["lang_mc"],
                            server_payload_json,
                            item.get("etag"),
                            item.get("updated_at", datetime.now().isoformat()),
                        ),
                    )
                count += 1

            conn.commit()
            logger.info(f"Added {count} inbound items to snapshot {snapshot_id}")
            return count

        except Exception as e:
            logger.error(f"Failed to add inbound items: {e}")
            # rollback handled by context manager
            raise

    def get_snapshot(self, snapshot_id: str) -> dict[str, Any] | None:
        """获取快照信息"""
        try:
            query = """
                SELECT snapshot_id, obtained_at, project_id, from_snapshot_id
                FROM inbound_snapshot
                WHERE snapshot_id = ?
            """

            with self.db._get_connection() as conn:
                cursor = conn.execute(query, (snapshot_id,))
                row = cursor.fetchone()

            if not row:
                return None

            return {
                "snapshot_id": row[0],
                "obtained_at": row[1],
                "project_id": row[2],
                "from_snapshot_id": row[3],
            }

        except Exception as e:
            logger.error(f"Failed to get snapshot {snapshot_id}: {e}")
            raise

    def get_inbound_items(
        self, snapshot_id: str, namespace: str | None = None, lang_mc: str | None = None
    ) -> list[dict[str, Any]]:
        """获取入站项目"""
        try:
            conditions = ["snapshot_id = ?"]
            params = [snapshot_id]

            if namespace:
                conditions.append("namespace LIKE ?")
                params.append(f"%{namespace}%")

            if lang_mc:
                conditions.append("lang_mc = ?")
                params.append(lang_mc)

            where_clause = "WHERE " + " AND ".join(conditions)

            query = f"""
                SELECT snapshot_id, server_content_id, namespace, keys_sha256_hex,
                       lang_mc, server_payload_json, etag, updated_at
                FROM inbound_items
                {where_clause}
                ORDER BY namespace, lang_mc
            """

            with self.db._get_connection() as conn:
                cursor = conn.execute(query, params)
                rows = cursor.fetchall()

            return [
                {
                    "snapshot_id": row[0],
                    "server_content_id": row[1],
                    "namespace": row[2],
                    "keys_sha256_hex": row[3],
                    "lang_mc": row[4],
                    "server_payload": json.loads(row[5]) if row[5] else {},
                    "etag": row[6],
                    "updated_at": row[7],
                }
                for row in rows
            ]

        except Exception as e:
            logger.error(f"Failed to get inbound items: {e}")
            raise

    def list_snapshots(
        self, project_id: str | None = None, limit: int = 50
    ) -> list[dict[str, Any]]:
        """列出快照"""
        try:
            conditions = []
            params = []

            if project_id:
                conditions.append("project_id = ?")
                params.append(project_id)

            where_clause = "WHERE " + " AND ".join(conditions) if conditions else ""

            query = f"""
                SELECT snapshot_id, obtained_at, project_id, from_snapshot_id
                FROM inbound_snapshot
                {where_clause}
                ORDER BY obtained_at DESC
                LIMIT ?
            """

            params.append(limit)
            with self.db._get_connection() as conn:
                cursor = conn.execute(query, params)
                rows = cursor.fetchall()

            return [
                {
                    "snapshot_id": row[0],
                    "obtained_at": row[1],
                    "project_id": row[2],
                    "from_snapshot_id": row[3],
                }
                for row in rows
            ]

        except Exception as e:
            logger.error(f"Failed to list snapshots: {e}")
            raise

    def get_queue_statistics(self) -> dict[str, Any]:
        """获取队列统计信息"""
        try:
            # 出站队列统计
            outbound_query = """
                SELECT queue_state, COUNT(*) as count
                FROM outbound_queue
                GROUP BY queue_state
            """

            with self.db._get_connection() as conn:
                cursor = conn.execute(outbound_query)
                outbound_stats = {row[0]: row[1] for row in cursor.fetchall()}

            # 入站快照统计
            snapshot_query = """
                SELECT COUNT(*) as total_snapshots,
                       MAX(obtained_at) as latest_snapshot
                FROM inbound_snapshot
            """

            with self.db._get_connection() as conn:
                cursor = conn.execute(snapshot_query)
                snapshot_row = cursor.fetchone()

            return {
                "outbound_queue": outbound_stats,
                "total_snapshots": snapshot_row[0] if snapshot_row else 0,
                "latest_snapshot": snapshot_row[1] if snapshot_row else None,
            }

        except Exception as e:
            logger.error(f"Failed to get queue statistics: {e}")
            raise

    def _outbound_row_to_dict(self, row) -> dict[str, Any]:
        """将出站队列行转换为字典"""
        return {
            "queue_id": row[0],
            "plan_id": row[1],
            "intent": row[2],
            "submit_payload": json.loads(row[3]) if row[3] else {},
            "base_etag": row[4],
            "queue_state": row[5],
            "result_message": row[6],
            "server_content_id": row[7],
            "submitted_at": row[8],
            "updated_at": row[9],
            "proposed_namespace": row[10],
            "lang_mc": row[11],
        }
