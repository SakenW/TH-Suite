"""
V5架构 - 工作队列Repository（适配实际表结构）
管理ops_work_queue表的数据访问，支持异步任务处理
"""

import json
from typing import Optional, List, Dict, Any
from dataclasses import dataclass
from enum import Enum

from .base_repository import BaseRepository


class TaskState(Enum):
    """任务状态枚举（匹配实际表约束）"""
    PENDING = "pending"
    LEASED = "leased"  # 对应 running
    DONE = "done"      # 对应 completed
    ERR = "err"        # 对应 failed
    DEAD = "dead"      # 对应 cancelled


@dataclass
class WorkQueueTask:
    """工作队列任务实体（匹配实际表结构）"""
    task_type: str  # 对应 type 字段
    payload: Dict[str, Any]  # 对应 payload_json 字段
    state: TaskState = TaskState.PENDING  # 对应 state 字段
    priority: int = 0  # 对应 priority 字段（整数，越小优先级越高）
    not_before: Optional[str] = None
    dedupe_key: Optional[str] = None
    attempt: int = 0
    last_error: Optional[str] = None
    lease_owner: Optional[str] = None
    lease_expires_at: Optional[str] = None
    created_at: Optional[str] = None
    updated_at: Optional[str] = None
    id: Optional[int] = None


class OpsWorkQueueRepository(BaseRepository[WorkQueueTask]):
    """工作队列Repository实现（匹配实际表结构）"""
    
    def table_name(self) -> str:
        return "ops_work_queue"
    
    def create(self, entity: WorkQueueTask) -> int:
        """创建任务（返回ID）"""
        query = """
            INSERT INTO ops_work_queue (
                type, payload_json, state, priority, not_before, dedupe_key, attempt, last_error
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """
        task_id = self.execute_write_with_id(query, (
            entity.task_type,
            json.dumps(entity.payload),
            entity.state.value,
            entity.priority,
            entity.not_before,
            entity.dedupe_key,
            entity.attempt,
            entity.last_error
        ))
        return task_id
    
    def get_by_uid(self, uid: str) -> Optional[WorkQueueTask]:
        """根据ID获取任务（实际表没有uid字段）"""
        return self.get_by_id(int(uid))
    
    def get_by_id(self, task_id: int) -> Optional[WorkQueueTask]:
        """根据ID获取任务"""
        query = """
            SELECT id, type, payload_json, state, priority, not_before, dedupe_key,
                   attempt, last_error, lease_owner, lease_expires_at, created_at, updated_at
            FROM ops_work_queue 
            WHERE id = ?
        """
        row = self.execute_single(query, (task_id,))
        return self._row_to_entity(row) if row else None
    
    def update(self, entity: WorkQueueTask) -> bool:
        """更新任务"""
        if not entity.id:
            return False
        
        query = """
            UPDATE ops_work_queue 
            SET state = ?, attempt = ?, last_error = ?, lease_owner = ?, 
                lease_expires_at = ?, updated_at = datetime('now')
            WHERE id = ?
        """
        affected = self.execute_write(query, (
            entity.state.value,
            entity.attempt,
            entity.last_error,
            entity.lease_owner,
            entity.lease_expires_at,
            entity.id
        ))
        return affected > 0
    
    def delete_by_uid(self, uid: str) -> bool:
        """删除任务"""
        return self.delete_by_id(int(uid))
    
    def delete_by_id(self, task_id: int) -> bool:
        """删除任务"""
        query = "DELETE FROM ops_work_queue WHERE id = ?"
        affected = self.execute_write(query, (task_id,))
        return affected > 0
    
    def list_all(self, limit: Optional[int] = None, offset: int = 0) -> List[WorkQueueTask]:
        """列出所有任务"""
        query = """
            SELECT id, type, payload_json, state, priority, not_before, dedupe_key,
                   attempt, last_error, lease_owner, lease_expires_at, created_at, updated_at
            FROM ops_work_queue 
            ORDER BY created_at DESC
        """
        if limit:
            query += f" LIMIT {limit} OFFSET {offset}"
        
        rows = self.execute_query(query)
        return [self._row_to_entity(row) for row in rows]
    
    def get_pending_tasks(self, limit: int = 10) -> List[WorkQueueTask]:
        """获取待处理任务（按优先级排序）"""
        query = """
            SELECT id, type, payload_json, state, priority, not_before, dedupe_key,
                   attempt, last_error, lease_owner, lease_expires_at, created_at, updated_at
            FROM ops_work_queue 
            WHERE state = 'pending' 
              AND (not_before IS NULL OR not_before <= datetime('now'))
              AND (lease_expires_at IS NULL OR lease_expires_at <= datetime('now'))
            ORDER BY priority ASC, created_at ASC
            LIMIT ?
        """
        rows = self.execute_query(query, (limit,))
        return [self._row_to_entity(row) for row in rows]
    
    def mark_as_running(self, task_id: int, lease_owner: str, lease_duration_minutes: int = 30) -> bool:
        """标记任务为运行中"""
        query = """
            UPDATE ops_work_queue 
            SET state = 'leased', 
                lease_owner = ?, 
                lease_expires_at = datetime('now', '+{} minutes'),
                updated_at = datetime('now')
            WHERE id = ? AND state = 'pending'
        """.format(lease_duration_minutes)
        affected = self.execute_write(query, (lease_owner, task_id))
        return affected > 0
    
    def mark_as_completed(self, task_id: int) -> bool:
        """标记任务为已完成"""
        query = """
            UPDATE ops_work_queue 
            SET state = 'done', 
                lease_owner = NULL, 
                lease_expires_at = NULL,
                updated_at = datetime('now')
            WHERE id = ?
        """
        affected = self.execute_write(query, (task_id,))
        return affected > 0
    
    def mark_as_failed(self, task_id: int, error_message: str, increment_attempt: bool = True) -> bool:
        """标记任务为失败"""
        if increment_attempt:
            query = """
                UPDATE ops_work_queue 
                SET state = 'failed', 
                    last_error = ?, 
                    attempt = attempt + 1,
                    lease_owner = NULL, 
                    lease_expires_at = NULL,
                    updated_at = datetime('now')
                WHERE id = ?
            """
        else:
            query = """
                UPDATE ops_work_queue 
                SET state = 'failed', 
                    last_error = ?,
                    lease_owner = NULL, 
                    lease_expires_at = NULL,
                    updated_at = datetime('now')
                WHERE id = ?
            """
        affected = self.execute_write(query, (error_message, task_id))
        return affected > 0
    
    def retry_failed_task(self, task_id: int, max_attempts: int = 3) -> bool:
        """重试失败的任务"""
        query = """
            UPDATE ops_work_queue 
            SET state = 'pending', 
                last_error = NULL, 
                lease_owner = NULL, 
                lease_expires_at = NULL,
                updated_at = datetime('now')
            WHERE id = ? AND state = 'failed' AND attempt < ?
        """
        affected = self.execute_write(query, (task_id, max_attempts))
        return affected > 0
    
    def get_tasks_by_type(self, task_type: str, state: Optional[TaskState] = None) -> List[WorkQueueTask]:
        """按类型获取任务"""
        if state:
            query = """
                SELECT id, type, payload_json, state, priority, not_before, dedupe_key,
                       attempt, last_error, lease_owner, lease_expires_at, created_at, updated_at
                FROM ops_work_queue 
                WHERE type = ? AND state = ?
                ORDER BY created_at DESC
            """
            rows = self.execute_query(query, (task_type, state.value))
        else:
            query = """
                SELECT id, type, payload_json, state, priority, not_before, dedupe_key,
                       attempt, last_error, lease_owner, lease_expires_at, created_at, updated_at
                FROM ops_work_queue 
                WHERE type = ?
                ORDER BY created_at DESC
            """
            rows = self.execute_query(query, (task_type,))
        
        return [self._row_to_entity(row) for row in rows]
    
    def get_task_stats(self) -> Dict[str, int]:
        """获取任务统计信息"""
        query = """
            SELECT state, COUNT(*) as count
            FROM ops_work_queue 
            GROUP BY state
        """
        rows = self.execute_query(query)
        stats = {row['state']: row['count'] for row in rows}
        
        # 确保所有状态都有值
        for state in TaskState:
            if state.value not in stats:
                stats[state.value] = 0
        
        return stats
    
    def cleanup_completed_tasks(self, older_than_days: int = 7) -> int:
        """清理已完成的旧任务"""
        query = """
            DELETE FROM ops_work_queue 
            WHERE state IN ('completed', 'cancelled') 
              AND updated_at < datetime('now', '-{} days')
        """.format(older_than_days)
        return self.execute_write(query)
    
    def cleanup_expired_leases(self) -> int:
        """清理过期的租约，将任务重新设为pending"""
        query = """
            UPDATE ops_work_queue 
            SET state = 'pending', 
                lease_owner = NULL, 
                lease_expires_at = NULL,
                updated_at = datetime('now')
            WHERE state = 'running' 
              AND lease_expires_at IS NOT NULL 
              AND lease_expires_at <= datetime('now')
        """
        return self.execute_write(query)
    
    def _row_to_entity(self, row) -> WorkQueueTask:
        """将数据库行转换为实体"""
        return WorkQueueTask(
            id=row['id'],
            task_type=row['type'],
            payload=json.loads(row['payload_json']) if row['payload_json'] else {},
            state=TaskState(row['state']) if row['state'] else TaskState.PENDING,
            priority=row['priority'] or 0,
            not_before=row['not_before'],
            dedupe_key=row['dedupe_key'],
            attempt=row['attempt'] or 0,
            last_error=row['last_error'],
            lease_owner=row['lease_owner'],
            lease_expires_at=row['lease_expires_at'],
            created_at=row['created_at'],
            updated_at=row['updated_at']
        )