"""
V5架构 - 工作队列Repository
管理ops_work_queue表的数据访问，支持异步任务处理
"""

import uuid
import json
from typing import Optional, List, Dict, Any
from dataclasses import dataclass
from enum import Enum
from datetime import datetime

from .base_repository import BaseRepository


class TaskStatus(Enum):
    """任务状态枚举"""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class TaskPriority(Enum):
    """任务优先级枚举"""
    LOW = "low"
    NORMAL = "normal"
    HIGH = "high"
    URGENT = "urgent"


@dataclass
class WorkQueueTask:
    """工作队列任务实体（适配V5实际表结构）"""
    task_type: str  # 对应 type 字段
    payload: Dict[str, Any]  # 对应 payload_json 字段
    state: TaskStatus  # 对应 state 字段
    priority: int = 0  # 对应 priority 字段（整数）
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
    """工作队列Repository实现"""
    
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
        """根据UID获取任务"""
        query = """
            SELECT id, uid, task_type, status, priority, payload, result,
                   error_message, retry_count, max_retries, created_at,
                   started_at, completed_at, expires_at
            FROM ops_work_queue 
            WHERE uid = ?
        """
        row = self.execute_single(query, (uid,))
        return self._row_to_entity(row) if row else None
    
    def update(self, entity: WorkQueueTask) -> bool:
        """更新任务"""
        query = """
            UPDATE ops_work_queue 
            SET status = ?, result = ?, error_message = ?, retry_count = ?,
                started_at = ?, completed_at = ?
            WHERE uid = ?
        """
        self.execute_write(query, (
            entity.status.value,
            json.dumps(entity.result) if entity.result else None,
            entity.error_message,
            entity.retry_count,
            entity.started_at,
            entity.completed_at,
            entity.uid
        ))
        return True
    
    def delete_by_uid(self, uid: str) -> bool:
        """删除任务"""
        query = "DELETE FROM ops_work_queue WHERE uid = ?"
        affected = self.execute_write(query, (uid,))
        return affected > 0
    
    def list_all(self, limit: Optional[int] = None, offset: int = 0) -> List[WorkQueueTask]:
        """列出所有任务"""
        query = """
            SELECT id, uid, task_type, status, priority, payload, result,
                   error_message, retry_count, max_retries, created_at,
                   started_at, completed_at, expires_at
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
            SELECT id, uid, task_type, status, priority, payload, result,
                   error_message, retry_count, max_retries, created_at,
                   started_at, completed_at, expires_at
            FROM ops_work_queue 
            WHERE status = 'pending' 
              AND (expires_at IS NULL OR expires_at > datetime('now'))
            ORDER BY 
                CASE priority 
                    WHEN 'urgent' THEN 1
                    WHEN 'high' THEN 2  
                    WHEN 'normal' THEN 3
                    WHEN 'low' THEN 4
                END,
                created_at ASC
            LIMIT ?
        """
        rows = self.execute_query(query, (limit,))
        return [self._row_to_entity(row) for row in rows]
    
    def mark_as_running(self, uid: str) -> bool:
        """标记任务为运行中"""
        query = """
            UPDATE ops_work_queue 
            SET status = 'running', started_at = datetime('now')
            WHERE uid = ? AND status = 'pending'
        """
        affected = self.execute_write(query, (uid,))
        return affected > 0
    
    def mark_as_completed(self, uid: str, result: Dict[str, Any]) -> bool:
        """标记任务为已完成"""
        query = """
            UPDATE ops_work_queue 
            SET status = 'completed', result = ?, completed_at = datetime('now')
            WHERE uid = ?
        """
        affected = self.execute_write(query, (uid, json.dumps(result)))
        return affected > 0
    
    def mark_as_failed(self, uid: str, error_message: str, increment_retry: bool = True) -> bool:
        """标记任务为失败"""
        if increment_retry:
            query = """
                UPDATE ops_work_queue 
                SET status = 'failed', error_message = ?, retry_count = retry_count + 1
                WHERE uid = ?
            """
        else:
            query = """
                UPDATE ops_work_queue 
                SET status = 'failed', error_message = ?
                WHERE uid = ?
            """
        affected = self.execute_write(query, (error_message, uid))
        return affected > 0
    
    def retry_failed_task(self, uid: str) -> bool:
        """重试失败的任务"""
        query = """
            UPDATE ops_work_queue 
            SET status = 'pending', error_message = NULL, started_at = NULL, completed_at = NULL
            WHERE uid = ? AND status = 'failed' AND retry_count < max_retries
        """
        affected = self.execute_write(query, (uid,))
        return affected > 0
    
    def get_tasks_by_type(self, task_type: str, status: Optional[TaskStatus] = None) -> List[WorkQueueTask]:
        """按类型获取任务"""
        if status:
            query = """
                SELECT id, uid, task_type, status, priority, payload, result,
                       error_message, retry_count, max_retries, created_at,
                       started_at, completed_at, expires_at
                FROM ops_work_queue 
                WHERE task_type = ? AND status = ?
                ORDER BY created_at DESC
            """
            rows = self.execute_query(query, (task_type, status.value))
        else:
            query = """
                SELECT id, uid, task_type, status, priority, payload, result,
                       error_message, retry_count, max_retries, created_at,
                       started_at, completed_at, expires_at
                FROM ops_work_queue 
                WHERE task_type = ?
                ORDER BY created_at DESC
            """
            rows = self.execute_query(query, (task_type,))
        
        return [self._row_to_entity(row) for row in rows]
    
    def get_task_stats(self) -> Dict[str, int]:
        """获取任务统计信息"""
        query = """
            SELECT status, COUNT(*) as count
            FROM ops_work_queue 
            GROUP BY status
        """
        rows = self.execute_query(query)
        stats = {row['status']: row['count'] for row in rows}
        
        # 确保所有状态都有值
        for status in TaskStatus:
            if status.value not in stats:
                stats[status.value] = 0
        
        return stats
    
    def cleanup_completed_tasks(self, older_than_days: int = 7) -> int:
        """清理已完成的旧任务"""
        query = """
            DELETE FROM ops_work_queue 
            WHERE status IN ('completed', 'cancelled') 
              AND completed_at < datetime('now', '-{} days')
        """.format(older_than_days)
        return self.execute_write(query)
    
    def cleanup_expired_tasks(self) -> int:
        """清理过期任务"""
        query = """
            DELETE FROM ops_work_queue 
            WHERE expires_at IS NOT NULL 
              AND expires_at < datetime('now')
        """
        return self.execute_write(query)
    
    def _row_to_entity(self, row) -> WorkQueueTask:
        """将数据库行转换为实体"""
        return WorkQueueTask(
            id=row['id'],
            uid=row['uid'],
            task_type=row['task_type'],
            status=TaskStatus(row['status']),
            priority=TaskPriority(row['priority']),
            payload=json.loads(row['payload']) if row['payload'] else {},
            result=json.loads(row['result']) if row['result'] else None,
            error_message=row['error_message'],
            retry_count=row['retry_count'],
            max_retries=row['max_retries'],
            created_at=row['created_at'],
            started_at=row['started_at'],
            completed_at=row['completed_at'],
            expires_at=row['expires_at']
        )