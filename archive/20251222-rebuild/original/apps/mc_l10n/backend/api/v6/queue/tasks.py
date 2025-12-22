"""
V6 工作队列管理API
"""
from typing import Dict, Any, List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
import structlog

from apps.mc_l10n.backend.database.core.manager import McL10nDatabaseManager
from apps.mc_l10n.backend.core.di_container import get_database_manager
from packages.core.infrastructure.database.manager import WorkQueueManager

logger = structlog.get_logger(__name__)
router = APIRouter(prefix="/queue", tags=["工作队列管理"])


class TaskCreateRequest(BaseModel):
    type: str = Field(..., pattern=r"^(import_delta_block|export_stream|tm_index|qa_run|merge_resolve|sync_out|sync_in)$")
    payload_json: Dict[str, Any] = Field(...)
    priority: int = Field(0, ge=0, le=100)
    not_before: Optional[str] = Field(None)
    dedupe_key: Optional[str] = Field(None, max_length=200)


class TaskLeaseRequest(BaseModel):
    lease_owner: str = Field(..., min_length=1, max_length=100)
    lease_duration_seconds: int = Field(300, ge=1, le=3600)


class TaskCompleteRequest(BaseModel):
    result: str = Field(..., pattern=r"^(success|fail)$")
    output: Dict[str, Any] = Field({})
    error_message: Optional[str] = Field(None, max_length=1000)


def get_work_queue_manager(db_manager: McL10nDatabaseManager = Depends(get_database_manager)) -> WorkQueueManager:
    return WorkQueueManager(db_manager)


@router.get("/tasks")
async def list_queue_tasks(
    state: Optional[str] = Query(None, pattern=r"^(pending|leased|done|err|dead)$"),
    type: Optional[str] = Query(None),
    lease_owner: Optional[str] = Query(None),
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
    queue_manager: WorkQueueManager = Depends(get_work_queue_manager)
) -> Dict[str, Any]:
    """列出队列任务"""
    try:
        with queue_manager.db_manager.get_connection() as conn:
            cursor = conn.cursor()
            
            # 构建查询条件
            conditions = []
            params = []
            
            if state:
                conditions.append("state = ?")
                params.append(state)
            if type:
                conditions.append("type = ?")
                params.append(type)
            if lease_owner:
                conditions.append("lease_owner = ?")
                params.append(lease_owner)
            
            where_clause = " AND ".join(conditions) if conditions else "1=1"
            
            # 查询任务
            query = f"""
                SELECT id, type, payload_json, state, priority, not_before, 
                       dedupe_key, attempt, last_error, lease_owner, 
                       lease_expires_at, created_at, updated_at
                FROM ops_work_queue 
                WHERE {where_clause}
                ORDER BY priority DESC, created_at ASC
                LIMIT ? OFFSET ?
            """
            params.extend([limit, offset])
            
            cursor.execute(query, params)
            rows = cursor.fetchall()
            
            tasks = []
            for row in rows:
                tasks.append({
                    "id": row[0],
                    "type": row[1],
                    "payload_json": row[2],
                    "state": row[3],
                    "priority": row[4],
                    "not_before": row[5],
                    "dedupe_key": row[6],
                    "attempt": row[7],
                    "last_error": row[8],
                    "lease_owner": row[9],
                    "lease_expires_at": row[10],
                    "created_at": row[11],
                    "updated_at": row[12]
                })
            
            # 获取总数
            count_query = f"SELECT COUNT(*) FROM ops_work_queue WHERE {where_clause}"
            cursor.execute(count_query, params[:-2])  # 排除limit和offset
            total = cursor.fetchone()[0]
        
        return {
            "tasks": tasks,
            "pagination": {
                "total": total,
                "limit": limit,
                "offset": offset,
                "has_more": offset + limit < total
            }
        }
    except Exception as e:
        logger.error("列出队列任务失败", error=str(e))
        raise HTTPException(status_code=500, detail="列出队列任务失败")


@router.post("/tasks")
async def create_task(
    task_data: TaskCreateRequest,
    queue_manager: WorkQueueManager = Depends(get_work_queue_manager)
) -> Dict[str, Any]:
    """创建任务"""
    try:
        task_id = await queue_manager.create_task(
            task_type=task_data.type,
            payload=task_data.payload_json,
            priority=task_data.priority,
            not_before=task_data.not_before,
            dedupe_key=task_data.dedupe_key
        )
        
        return {
            "task_id": task_id,
            "message": "任务创建成功"
        }
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error("创建任务失败", error=str(e))
        raise HTTPException(status_code=500, detail="创建任务失败")


@router.get("/tasks/{task_id}")
async def get_task(
    task_id: int,
    queue_manager: WorkQueueManager = Depends(get_work_queue_manager)
) -> Dict[str, Any]:
    """获取任务详情"""
    try:
        with queue_manager.db_manager.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT id, type, payload_json, state, priority, not_before, 
                       dedupe_key, attempt, last_error, lease_owner, 
                       lease_expires_at, created_at, updated_at
                FROM ops_work_queue WHERE id = ?
            """, (task_id,))
            row = cursor.fetchone()
            
            if not row:
                raise HTTPException(status_code=404, detail="任务不存在")
                
            task = {
                "id": row[0],
                "type": row[1],
                "payload_json": row[2],
                "state": row[3],
                "priority": row[4],
                "not_before": row[5],
                "dedupe_key": row[6],
                "attempt": row[7],
                "last_error": row[8],
                "lease_owner": row[9],
                "lease_expires_at": row[10],
                "created_at": row[11],
                "updated_at": row[12]
            }
            
        return {"task": task}
    except HTTPException:
        raise
    except Exception as e:
        logger.error("获取任务失败", task_id=task_id, error=str(e))
        raise HTTPException(status_code=500, detail="获取任务失败")


@router.post("/tasks/{task_id}/lease")
async def lease_task(
    task_id: int,
    lease_data: TaskLeaseRequest,
    queue_manager: WorkQueueManager = Depends(get_work_queue_manager)
) -> Dict[str, Any]:
    """租用任务"""
    try:
        success = await queue_manager.lease_task(
            task_id=task_id,
            owner=lease_data.lease_owner,
            lease_duration=lease_data.lease_duration_seconds
        )
        
        if not success:
            raise HTTPException(status_code=409, detail="任务已被租用或不存在")
            
        return {
            "task_id": task_id,
            "lease_owner": lease_data.lease_owner,
            "message": "任务租用成功"
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error("租用任务失败", task_id=task_id, error=str(e))
        raise HTTPException(status_code=500, detail="租用任务失败")


@router.post("/tasks/{task_id}/complete")
async def complete_task(
    task_id: int,
    complete_data: TaskCompleteRequest,
    queue_manager: WorkQueueManager = Depends(get_work_queue_manager)
) -> Dict[str, Any]:
    """完成任务"""
    try:
        success = await queue_manager.complete_task(
            task_id=task_id,
            result=complete_data.result,
            output=complete_data.output,
            error_message=complete_data.error_message
        )
        
        if not success:
            raise HTTPException(status_code=404, detail="任务不存在或未租用")
            
        return {
            "task_id": task_id,
            "result": complete_data.result,
            "message": "任务完成"
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error("完成任务失败", task_id=task_id, error=str(e))
        raise HTTPException(status_code=500, detail="完成任务失败")


@router.post("/tasks/{task_id}/retry")
async def retry_task(
    task_id: int,
    queue_manager: WorkQueueManager = Depends(get_work_queue_manager)
) -> Dict[str, Any]:
    """重试任务"""
    try:
        success = await queue_manager.retry_task(task_id)
        if not success:
            raise HTTPException(status_code=404, detail="任务不存在")
            
        return {
            "task_id": task_id,
            "message": "任务已重置为待处理状态"
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error("重试任务失败", task_id=task_id, error=str(e))
        raise HTTPException(status_code=500, detail="重试任务失败")


@router.get("/status")
async def get_queue_status(
    queue_manager: WorkQueueManager = Depends(get_work_queue_manager)
) -> Dict[str, Any]:
    """获取队列状态"""
    try:
        with queue_manager.db_manager.get_connection() as conn:
            cursor = conn.cursor()
            
            # 统计各状态任务数量
            cursor.execute("""
                SELECT state, COUNT(*) as count,
                       MIN(created_at) as oldest_created,
                       MAX(updated_at) as latest_updated
                FROM ops_work_queue 
                GROUP BY state
            """)
            
            status_stats = {}
            for row in cursor.fetchall():
                status_stats[row[0]] = {
                    "count": row[1],
                    "oldest_created": row[2],
                    "latest_updated": row[3]
                }
            
            # 获取队列深度和滞后时间
            cursor.execute("""
                SELECT COUNT(*) as depth,
                       AVG(CASE WHEN state = 'pending' 
                           THEN (julianday('now') - julianday(created_at)) * 86400000 
                           ELSE NULL END) as avg_lag_ms
                FROM ops_work_queue
                WHERE state IN ('pending', 'leased')
            """)
            queue_row = cursor.fetchone()
            
            return {
                "queue_depth": queue_row[0] or 0,
                "avg_lag_ms": queue_row[1] or 0.0,
                "status_breakdown": status_stats,
                "timestamp": "2025-09-10T02:30:00Z"
            }
    except Exception as e:
        logger.error("获取队列状态失败", error=str(e))
        raise HTTPException(status_code=500, detail="获取队列状态失败")


@router.post("/cleanup")
async def cleanup_queue(
    older_than_days: int = Query(7, ge=1, le=30),
    states: str = Query("done,err", pattern=r"^(done|err|dead)(,(done|err|dead))*$"),
    queue_manager: WorkQueueManager = Depends(get_work_queue_manager)
) -> Dict[str, Any]:
    """清理队列中的旧任务"""
    try:
        state_list = [s.strip() for s in states.split(',')]
        
        with queue_manager.db_manager.get_connection() as conn:
            cursor = conn.cursor()
            
            placeholders = ','.join(['?' for _ in state_list])
            params = state_list + [older_than_days]
            
            cursor.execute(f"""
                DELETE FROM ops_work_queue 
                WHERE state IN ({placeholders})
                AND created_at < datetime('now', '-{older_than_days} days')
            """, params)
            
            deleted_count = cursor.rowcount
            conn.commit()
            
        return {
            "deleted_count": deleted_count,
            "cleanup_criteria": {
                "older_than_days": older_than_days,
                "states": state_list
            },
            "message": f"清理了 {deleted_count} 个旧任务"
        }
    except Exception as e:
        logger.error("清理队列失败", error=str(e))
        raise HTTPException(status_code=500, detail="清理队列失败")