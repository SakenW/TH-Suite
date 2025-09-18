"""
工作队列管理相关路由
提供异步任务队列的管理和监控功能
V5架构 - 集成Repository模式
"""

import logging
from typing import Any, List, Dict

from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel

from infrastructure.repositories.repository_factory import get_repository_factory, RepositoryFactory
from infrastructure.repositories.ops_work_queue_repository_v2 import WorkQueueTask, TaskState

logger = logging.getLogger(__name__)

def get_repo_factory() -> RepositoryFactory:
    """依赖注入：获取Repository工厂"""
    return get_repository_factory()

router = APIRouter(
    prefix="/api/v1/queue",
    tags=["工作队列管理"],
    responses={404: {"description": "Not found"}},
)


class TaskCreateRequest(BaseModel):
    """创建任务请求模型"""
    task_type: str  # sync_in, import_delta_block, export_stream, tm_index, qa_run, merge_resolve, sync_out
    payload: Dict[str, Any]
    priority: int = 0
    not_before: str | None = None
    dedupe_key: str | None = None


class TaskResponse(BaseModel):
    """任务响应模型"""
    id: int
    task_type: str
    state: str
    priority: int
    payload: Dict[str, Any]
    attempt: int
    last_error: str | None = None
    lease_owner: str | None = None
    lease_expires_at: str | None = None
    created_at: str
    updated_at: str


class TaskListResponse(BaseModel):
    """任务列表响应模型"""
    tasks: List[TaskResponse]
    total: int


@router.get("/test", response_model=dict[str, Any])
async def queue_test_endpoint():
    """
    队列路由测试端点
    """
    return {
        "success": True,
        "message": "Queue routes are working",
        "service": "queue-management",
        "supported_task_types": [
            "import_delta_block", "export_stream", "tm_index", 
            "qa_run", "merge_resolve", "sync_out", "sync_in"
        ],
        "endpoints_available": [
            "GET /api/v1/queue/test",
            "GET /api/v1/queue/stats",
            "GET /api/v1/queue/tasks",
            "POST /api/v1/queue/tasks",
            "GET /api/v1/queue/tasks/{task_id}",
            "GET /api/v1/queue/tasks/pending",
            "POST /api/v1/queue/tasks/{task_id}/start",
            "POST /api/v1/queue/tasks/{task_id}/complete",
            "POST /api/v1/queue/tasks/{task_id}/fail",
        ],
    }


@router.get("/stats", response_model=dict[str, Any])
async def get_queue_stats(
    factory: RepositoryFactory = Depends(get_repo_factory)
):
    """
    获取工作队列统计信息
    """
    try:
        queue_repo = factory.get_ops_work_queue_repo()
        stats = queue_repo.get_task_stats()
        total_tasks = sum(stats.values())
        
        return {
            "success": True,
            "data": {
                "task_stats": stats,
                "total_tasks": total_tasks,
                "pending_tasks": stats.get("pending", 0),
                "running_tasks": stats.get("leased", 0),
                "completed_tasks": stats.get("done", 0),
                "failed_tasks": stats.get("err", 0),
            },
            "message": "队列统计信息获取成功",
        }
    except Exception as e:
        logger.error(f"获取队列统计失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/tasks", response_model=dict[str, Any])
async def list_tasks(
    limit: int = 50,
    offset: int = 0,
    state: str | None = None,
    task_type: str | None = None,
    factory: RepositoryFactory = Depends(get_repo_factory)
):
    """
    获取任务列表

    Args:
        limit: 限制数量
        offset: 偏移量
        state: 状态过滤（pending, leased, done, err, dead）
        task_type: 任务类型过滤
    """
    try:
        queue_repo = factory.get_ops_work_queue_repo()
        
        if task_type:
            state_enum = None
            if state:
                try:
                    state_enum = TaskState(state)
                except ValueError:
                    raise HTTPException(status_code=400, detail=f"无效的状态: {state}")
            
            tasks = queue_repo.get_tasks_by_type(task_type, state_enum)
        else:
            tasks = queue_repo.list_all(limit=limit, offset=offset)
        
        task_responses = [
            TaskResponse(
                id=task.id,
                task_type=task.task_type,
                state=task.state.value,
                priority=task.priority,
                payload=task.payload,
                attempt=task.attempt,
                last_error=task.last_error,
                lease_owner=task.lease_owner,
                lease_expires_at=task.lease_expires_at,
                created_at=task.created_at or "",
                updated_at=task.updated_at or ""
            )
            for task in tasks if task.id is not None
        ]
        
        return {
            "success": True,
            "data": {
                "tasks": [t.dict() for t in task_responses],
                "total": len(task_responses)
            },
            "message": "任务列表获取成功",
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"获取任务列表失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/tasks", response_model=dict[str, Any])
async def create_task(
    task_data: TaskCreateRequest,
    factory: RepositoryFactory = Depends(get_repo_factory)
):
    """
    创建新任务

    Args:
        task_data: 任务创建信息
    """
    try:
        queue_repo = factory.get_ops_work_queue_repo()
        
        # 验证任务类型
        valid_types = ["import_delta_block", "export_stream", "tm_index", 
                      "qa_run", "merge_resolve", "sync_out", "sync_in"]
        if task_data.task_type not in valid_types:
            raise HTTPException(
                status_code=400, 
                detail=f"无效的任务类型: {task_data.task_type}。支持的类型: {valid_types}"
            )
        
        # 创建新任务
        new_task = WorkQueueTask(
            task_type=task_data.task_type,
            payload=task_data.payload,
            state=TaskState.PENDING,
            priority=task_data.priority,
            not_before=task_data.not_before,
            dedupe_key=task_data.dedupe_key
        )
        
        task_id = queue_repo.create(new_task)
        created_task = queue_repo.get_by_id(task_id)
        
        if not created_task:
            raise HTTPException(status_code=500, detail="任务创建失败")
        
        response = TaskResponse(
            id=created_task.id,
            task_type=created_task.task_type,
            state=created_task.state.value,
            priority=created_task.priority,
            payload=created_task.payload,
            attempt=created_task.attempt,
            last_error=created_task.last_error,
            lease_owner=created_task.lease_owner,
            lease_expires_at=created_task.lease_expires_at,
            created_at=created_task.created_at or "",
            updated_at=created_task.updated_at or ""
        )

        return {
            "success": True,
            "data": response.dict(),
            "message": f"任务创建成功: {task_data.task_type}",
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"创建任务失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/tasks/pending", response_model=dict[str, Any])
async def get_pending_tasks(
    limit: int = 10,
    factory: RepositoryFactory = Depends(get_repo_factory)
):
    """
    获取待处理任务（按优先级排序）

    Args:
        limit: 限制数量
    """
    try:
        queue_repo = factory.get_ops_work_queue_repo()
        tasks = queue_repo.get_pending_tasks(limit=limit)
        
        task_responses = [
            TaskResponse(
                id=task.id,
                task_type=task.task_type,
                state=task.state.value,
                priority=task.priority,
                payload=task.payload,
                attempt=task.attempt,
                last_error=task.last_error,
                lease_owner=task.lease_owner,
                lease_expires_at=task.lease_expires_at,
                created_at=task.created_at or "",
                updated_at=task.updated_at or ""
            )
            for task in tasks if task.id is not None
        ]
        
        return {
            "success": True,
            "data": {
                "tasks": [t.dict() for t in task_responses],
                "total": len(task_responses)
            },
            "message": "待处理任务获取成功",
        }
    except Exception as e:
        logger.error(f"获取待处理任务失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/tasks/{task_id}", response_model=dict[str, Any])
async def get_task_info(
    task_id: int,
    factory: RepositoryFactory = Depends(get_repo_factory)
):
    """
    获取任务详细信息

    Args:
        task_id: 任务ID
    """
    try:
        queue_repo = factory.get_ops_work_queue_repo()
        task = queue_repo.get_by_id(task_id)
        
        if not task:
            raise HTTPException(status_code=404, detail=f"任务不存在: {task_id}")
        
        response = TaskResponse(
            id=task.id,
            task_type=task.task_type,
            state=task.state.value,
            priority=task.priority,
            payload=task.payload,
            attempt=task.attempt,
            last_error=task.last_error,
            lease_owner=task.lease_owner,
            lease_expires_at=task.lease_expires_at,
            created_at=task.created_at or "",
            updated_at=task.updated_at or ""
        )

        return {
            "success": True,
            "data": response.dict(),
            "message": f"任务信息获取成功: {task_id}",
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"获取任务信息失败 {task_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/tasks/{task_id}/start", response_model=dict[str, Any])
async def start_task(
    task_id: int,
    lease_owner: str = "api_worker",
    lease_duration_minutes: int = 30,
    factory: RepositoryFactory = Depends(get_repo_factory)
):
    """
    标记任务为运行中（获取租约）

    Args:
        task_id: 任务ID
        lease_owner: 租约持有者
        lease_duration_minutes: 租约持续时间（分钟）
    """
    try:
        queue_repo = factory.get_ops_work_queue_repo()
        success = queue_repo.mark_as_running(task_id, lease_owner, lease_duration_minutes)
        
        if not success:
            raise HTTPException(status_code=409, detail="任务无法启动（可能已被其他worker处理）")
        
        return {
            "success": True,
            "data": {
                "task_id": task_id,
                "lease_owner": lease_owner,
                "lease_duration_minutes": lease_duration_minutes
            },
            "message": f"任务启动成功: {task_id}",
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"启动任务失败 {task_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/tasks/{task_id}/complete", response_model=dict[str, Any])
async def complete_task(
    task_id: int,
    factory: RepositoryFactory = Depends(get_repo_factory)
):
    """
    标记任务为已完成

    Args:
        task_id: 任务ID
    """
    try:
        queue_repo = factory.get_ops_work_queue_repo()
        success = queue_repo.mark_as_completed(task_id)
        
        if not success:
            raise HTTPException(status_code=404, detail="任务不存在或无法完成")
        
        return {
            "success": True,
            "data": {"task_id": task_id},
            "message": f"任务完成: {task_id}",
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"完成任务失败 {task_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/tasks/{task_id}/fail", response_model=dict[str, Any])
async def fail_task(
    task_id: int,
    error_message: str,
    increment_attempt: bool = True,
    factory: RepositoryFactory = Depends(get_repo_factory)
):
    """
    标记任务为失败

    Args:
        task_id: 任务ID
        error_message: 错误信息
        increment_attempt: 是否增加尝试次数
    """
    try:
        queue_repo = factory.get_ops_work_queue_repo()
        success = queue_repo.mark_as_failed(task_id, error_message, increment_attempt)
        
        if not success:
            raise HTTPException(status_code=404, detail="任务不存在或无法标记为失败")
        
        return {
            "success": True,
            "data": {
                "task_id": task_id,
                "error_message": error_message,
                "increment_attempt": increment_attempt
            },
            "message": f"任务标记为失败: {task_id}",
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"标记任务失败 {task_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/cleanup/completed", response_model=dict[str, Any])
async def cleanup_completed_tasks(
    older_than_days: int = 7,
    factory: RepositoryFactory = Depends(get_repo_factory)
):
    """
    清理已完成的旧任务

    Args:
        older_than_days: 清理多少天前的任务
    """
    try:
        queue_repo = factory.get_ops_work_queue_repo()
        deleted_count = queue_repo.cleanup_completed_tasks(older_than_days)
        
        return {
            "success": True,
            "data": {
                "deleted_count": deleted_count,
                "older_than_days": older_than_days
            },
            "message": f"清理完成，删除了 {deleted_count} 个旧任务",
        }
    except Exception as e:
        logger.error(f"清理任务失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/cleanup/expired-leases", response_model=dict[str, Any])
async def cleanup_expired_leases(
    factory: RepositoryFactory = Depends(get_repo_factory)
):
    """
    清理过期的租约，将任务重新设为pending
    """
    try:
        queue_repo = factory.get_ops_work_queue_repo()
        updated_count = queue_repo.cleanup_expired_leases()
        
        return {
            "success": True,
            "data": {"updated_count": updated_count},
            "message": f"清理完成，重置了 {updated_count} 个过期租约的任务",
        }
    except Exception as e:
        logger.error(f"清理过期租约失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))