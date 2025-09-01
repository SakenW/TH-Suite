import hashlib
import json
from typing import Any

import structlog

from packages.core.database import SQLCipherDatabase

logger = structlog.get_logger(__name__)


class MappingPlanService:
    """映射计划管理服务"""

    def __init__(self, database: SQLCipherDatabase):
        self.db = database

    def create_plan(
        self,
        local_id: int,
        proposed_namespace: str,
        proposed_keys: dict[str, Any],
        lang_mc: str | None = None,
        validation_state: str = "drafted",
    ) -> int:
        """创建新的映射计划"""
        try:
            # 验证状态值
            if validation_state not in ["drafted", "validated", "mapped"]:
                raise ValueError(f"Invalid validation_state: {validation_state}")

            proposed_keys_json = json.dumps(
                proposed_keys, ensure_ascii=False, sort_keys=True
            )
            keyhash_hex_local = self._calculate_key_hash(proposed_keys)

            with self.db._get_connection() as conn:
                cursor = conn.execute(
                    """
                    INSERT INTO mapping_plan (
                        local_id, proposed_namespace, proposed_keys_json,
                        keyhash_hex_local, lang_mc, validation_state
                    ) VALUES (?, ?, ?, ?, ?, ?)
                    """,
                    (
                        local_id,
                        proposed_namespace,
                        proposed_keys_json,
                        keyhash_hex_local,
                        lang_mc,
                        validation_state,
                    ),
                )

                plan_id = cursor.lastrowid
                conn.commit()

            logger.info(f"Created mapping plan {plan_id} for local_id {local_id}")
            return plan_id

        except Exception as e:
            logger.error(f"Failed to create mapping plan: {e}")
            # rollback handled by context manager
            raise

    def get_plan(self, plan_id: int) -> dict[str, Any] | None:
        """获取单个映射计划"""
        try:
            query = """
                SELECT p.plan_id, p.local_id, p.proposed_namespace, p.proposed_keys_json,
                       p.keyhash_hex_local, p.lang_mc, p.validation_state, p.validation_errors,
                       p.created_at, p.updated_at,
                       le.source_type, le.source_file, le.source_locator
                FROM mapping_plan p
                JOIN local_entries le ON p.local_id = le.local_id
                WHERE p.plan_id = ?
            """

            with self.db._get_connection() as conn:
                cursor = conn.execute(query, (plan_id,))
                row = cursor.fetchone()

                if not row:
                    return None

                return self._row_to_dict(row)

        except Exception as e:
            logger.error(f"Failed to get mapping plan {plan_id}: {e}")
            raise

    def list_plans(
        self,
        local_id: int | None = None,
        validation_state: str | None = None,
        namespace: str | None = None,
        limit: int = 100,
        offset: int = 0,
    ) -> list[dict[str, Any]]:
        """列出映射计划"""
        try:
            conditions = []
            params = []

            if local_id:
                conditions.append("p.local_id = ?")
                params.append(local_id)

            if validation_state:
                conditions.append("p.validation_state = ?")
                params.append(validation_state)

            if namespace:
                conditions.append("p.proposed_namespace LIKE ?")
                params.append(f"%{namespace}%")

            where_clause = "WHERE " + " AND ".join(conditions) if conditions else ""

            query = f"""
                SELECT p.plan_id, p.local_id, p.proposed_namespace, p.proposed_keys_json,
                       p.keyhash_hex_local, p.lang_mc, p.validation_state, p.validation_errors,
                       p.created_at, p.updated_at,
                       le.source_type, le.source_file, le.source_locator
                FROM mapping_plan p
                JOIN local_entries le ON p.local_id = le.local_id
                {where_clause}
                ORDER BY p.created_at DESC
                LIMIT ? OFFSET ?
            """

            params.extend([limit, offset])
            with self.db._get_connection() as conn:
                cursor = conn.execute(query, params)
                rows = cursor.fetchall()

                return [self._row_to_dict(row) for row in rows]

        except Exception as e:
            logger.error(f"Failed to list mapping plans: {e}")
            raise

    def update_plan(
        self,
        plan_id: int,
        proposed_namespace: str | None = None,
        proposed_keys: dict[str, Any] | None = None,
        lang_mc: str | None = None,
        validation_state: str | None = None,
        validation_errors: list[str] | None = None,
    ) -> bool:
        """更新映射计划"""
        try:
            updates = []
            params = []

            if proposed_namespace is not None:
                updates.append("proposed_namespace = ?")
                params.append(proposed_namespace)

            if proposed_keys is not None:
                proposed_keys_json = json.dumps(
                    proposed_keys, ensure_ascii=False, sort_keys=True
                )
                keyhash_hex_local = self._calculate_key_hash(proposed_keys)
                updates.extend(["proposed_keys_json = ?", "keyhash_hex_local = ?"])
                params.extend([proposed_keys_json, keyhash_hex_local])

            if lang_mc is not None:
                updates.append("lang_mc = ?")
                params.append(lang_mc)

            if validation_state is not None:
                if validation_state not in ["drafted", "validated", "mapped"]:
                    raise ValueError(f"Invalid validation_state: {validation_state}")
                updates.append("validation_state = ?")
                params.append(validation_state)

            if validation_errors is not None:
                updates.append("validation_errors = ?")
                params.append(
                    json.dumps(validation_errors, ensure_ascii=False)
                    if validation_errors
                    else None
                )

            if not updates:
                return False

            query = f"""
                UPDATE mapping_plan
                SET {", ".join(updates)}
                WHERE plan_id = ?
            """

            params.append(plan_id)
            with self.db._get_connection() as conn:
                cursor = conn.execute(query, params)
            conn.commit()

            updated = cursor.rowcount > 0
            if updated:
                logger.info(f"Updated mapping plan {plan_id}")

            return updated

        except Exception as e:
            logger.error(f"Failed to update mapping plan {plan_id}: {e}")
            # rollback handled by context manager
            raise

    def delete_plan(self, plan_id: int) -> bool:
        """删除映射计划"""
        try:
            query = "DELETE FROM mapping_plan WHERE plan_id = ?"
            with self.db._get_connection() as conn:
                cursor = conn.execute(query, (plan_id,))
                conn.commit()

                deleted = cursor.rowcount > 0
                if deleted:
                    logger.info(f"Deleted mapping plan {plan_id}")

                return deleted

        except Exception as e:
            logger.error(f"Failed to delete mapping plan {plan_id}: {e}")
            # rollback handled by context manager
            raise

    def validate_plan(self, plan_id: int) -> tuple[bool, list[str]]:
        """验证映射计划"""
        try:
            plan = self.get_plan(plan_id)
            if not plan:
                return False, ["Plan not found"]

            errors = []

            # 验证命名空间格式
            namespace = plan["proposed_namespace"]
            if not namespace or not self._is_valid_namespace(namespace):
                errors.append(f"Invalid namespace format: {namespace}")

            # 验证键结构
            proposed_keys = plan["proposed_keys"]
            if not proposed_keys:
                errors.append("Empty proposed keys")
            elif not isinstance(proposed_keys, dict):
                errors.append("Proposed keys must be a dictionary")

            # 验证语言码
            lang_mc = plan["lang_mc"]
            if lang_mc and not self._is_valid_lang_code(lang_mc):
                errors.append(f"Invalid language code: {lang_mc}")

            # 更新验证状态
            is_valid = len(errors) == 0
            new_state = "validated" if is_valid else "drafted"

            self.update_plan(
                plan_id, validation_state=new_state, validation_errors=errors
            )

            return is_valid, errors

        except Exception as e:
            logger.error(f"Failed to validate mapping plan {plan_id}: {e}")
            raise

    def get_ready_to_queue(self) -> list[dict[str, Any]]:
        """获取准备提交的映射计划"""
        try:
            query = """
                SELECT p.plan_id, p.local_id, p.proposed_namespace, p.proposed_keys_json, p.lang_mc
                FROM v_ready_to_queue v
                JOIN mapping_plan p ON v.plan_id = p.plan_id
                ORDER BY p.created_at
            """

            with self.db._get_connection() as conn:
                cursor = conn.execute(query)
                rows = cursor.fetchall()

            return [
                {
                    "plan_id": row[0],
                    "local_id": row[1],
                    "proposed_namespace": row[2],
                    "proposed_keys": json.loads(row[3]) if row[3] else {},
                    "lang_mc": row[4],
                }
                for row in rows
            ]

        except Exception as e:
            logger.error(f"Failed to get ready to queue plans: {e}")
            raise

    def count_plans_by_state(self) -> dict[str, int]:
        """按状态统计映射计划数量"""
        try:
            query = """
                SELECT validation_state, COUNT(*) as count
                FROM mapping_plan
                GROUP BY validation_state
            """

            with self.db._get_connection() as conn:
                cursor = conn.execute(query)
            rows = cursor.fetchall()

            return {row[0]: row[1] for row in rows}

        except Exception as e:
            logger.error(f"Failed to count plans by state: {e}")
            raise

    def _calculate_key_hash(self, keys: dict[str, Any]) -> str:
        """计算键的哈希值"""
        # 排序并序列化键，然后计算SHA256哈希
        sorted_json = json.dumps(keys, ensure_ascii=False, sort_keys=True)
        return hashlib.sha256(sorted_json.encode("utf-8")).hexdigest()

    def _is_valid_namespace(self, namespace: str) -> bool:
        """验证命名空间格式"""
        # 简单的命名空间验证：至少包含一个点，不能以点开始或结束
        return (
            namespace
            and "." in namespace
            and not namespace.startswith(".")
            and not namespace.endswith(".")
            and all(part.strip() for part in namespace.split("."))
        )

    def _is_valid_lang_code(self, lang_code: str) -> bool:
        """验证语言码格式"""
        # 简单的MC语言码验证：如 zh_cn, en_us
        return (
            lang_code
            and len(lang_code) >= 2
            and "_" in lang_code
            and len(lang_code.split("_")) == 2
        )

    def _row_to_dict(self, row) -> dict[str, Any]:
        """将数据库行转换为字典"""
        return {
            "plan_id": row[0],
            "local_id": row[1],
            "proposed_namespace": row[2],
            "proposed_keys": json.loads(row[3]) if row[3] else {},
            "keyhash_hex_local": row[4],
            "lang_mc": row[5],
            "validation_state": row[6],
            "validation_errors": json.loads(row[7]) if row[7] else [],
            "created_at": row[8],
            "updated_at": row[9],
            "source_type": row[10],
            "source_file": row[11],
            "source_locator": row[12],
        }
