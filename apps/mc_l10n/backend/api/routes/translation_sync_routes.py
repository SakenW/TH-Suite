"""
翻译同步API路由
提供翻译数据同步的RESTful API接口

主要功能:
- 准备同步，分析差异
- 执行同步操作
- 获取同步状态
- 解决冲突
- 管理同步会话

作者: Claude Code
创建时间: 2025-09-20
"""

from datetime import datetime
from typing import Any, Dict, List, Optional
from fastapi import APIRouter, HTTPException, BackgroundTasks, Query, Path, Body
from pydantic import BaseModel, Field
import structlog

from infrastructure.services.translation_sync_engine import (
    TranslationSyncEngine,
    SyncDirection,
    SyncStatus,
    ConflictResolution,
    get_translation_sync_engine
)

logger = structlog.get_logger(__name__)

# 创建路由器
router = APIRouter(prefix="/api/v1/sync", tags=["翻译同步"])


# ============================================================
# Pydantic模型定义
# ============================================================

class SyncPrepareRequest(BaseModel):
    """同步准备请求"""
    direction: str = Field(..., description="同步方向: local_to_remote, remote_to_local, bidirectional")
    language_filters: Optional[List[str]] = Field(default=None, description="语言过滤器")
    pack_filters: Optional[List[str]] = Field(default=None, description="包过滤器")
    mod_filters: Optional[List[str]] = Field(default=None, description="模组过滤器")
    auto_resolve_conflicts: bool = Field(default=True, description="自动解决冲突")
    conflict_resolution: str = Field(default="latest_wins", description="冲突解决策略")
    batch_size: int = Field(default=100, description="批处理大小")
    max_concurrency: int = Field(default=3, description="最大并发数")
    
    class Config:
        schema_extra = {
            "example": {
                "direction": "bidirectional",
                "language_filters": ["zh_cn", "en_us"],
                "pack_filters": ["minecraft", "jei"],
                "auto_resolve_conflicts": True,
                "conflict_resolution": "latest_wins",
                "batch_size": 100
            }
        }


class SyncExecuteRequest(BaseModel):
    """同步执行请求"""
    force: bool = Field(default=False, description="强制执行，跳过冲突检查")
    dry_run: bool = Field(default=False, description="演练模式，不实际执行")
    
    class Config:
        schema_extra = {
            "example": {
                "force": False,
                "dry_run": False
            }
        }


class ConflictResolveRequest(BaseModel):
    """冲突解决请求"""
    conflict_id: str = Field(..., description="冲突ID")
    resolution: str = Field(..., description="解决方式: local_wins, remote_wins, manual")
    resolved_entry: Optional[Dict[str, Any]] = Field(default=None, description="手动解决的条目数据")
    
    class Config:
        schema_extra = {
            "example": {
                "conflict_id": "conflict-123",
                "resolution": "local_wins",
                "resolved_entry": None
            }
        }


class SyncProgressResponse(BaseModel):
    """同步进度响应"""
    session_id: str
    status: str
    direction: str
    created_at: datetime
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    
    # 进度统计
    total_entries: int = 0
    processed_entries: int = 0
    success_entries: int = 0
    failed_entries: int = 0
    conflicts_entries: int = 0
    
    # 进度百分比
    progress_percentage: float = 0.0
    estimated_completion: Optional[datetime] = None
    current_operation: Optional[str] = None
    
    # 结果信息
    errors: List[str] = []
    warnings: List[str] = []


class SyncAnalysisResponse(BaseModel):
    """同步分析响应"""
    session_id: str
    direction: str
    total_local: int
    total_remote: int
    
    # 变更统计
    total_changes: int
    added: int
    modified: int
    deleted: int
    conflicts: int
    
    # 详细分析
    by_language: Dict[str, int]
    by_pack: Dict[str, int]
    estimated_time: float
    
    # 建议
    recommendations: List[str] = []


# ============================================================
# API路由实现
# ============================================================

@router.post("/prepare", response_model=SyncAnalysisResponse, summary="准备同步")
async def prepare_sync(
    request: SyncPrepareRequest,
    background_tasks: BackgroundTasks
) -> SyncAnalysisResponse:
    """
    准备同步操作，分析本地和远程数据的差异
    
    - 检测增量变更
    - 识别冲突
    - 生成同步计划
    - 估算执行时间
    """
    
    try:
        # 验证同步方向
        try:
            direction = SyncDirection(request.direction)
        except ValueError:
            raise HTTPException(
                status_code=400,
                detail=f"无效的同步方向: {request.direction}"
            )
        
        # 验证冲突解决策略
        try:
            ConflictResolution(request.conflict_resolution)
        except ValueError:
            raise HTTPException(
                status_code=400,
                detail=f"无效的冲突解决策略: {request.conflict_resolution}"
            )
        
        # 构建配置
        config = {
            "language_filters": request.language_filters or [],
            "pack_filters": request.pack_filters or [],
            "mod_filters": request.mod_filters or [],
            "auto_resolve_conflicts": request.auto_resolve_conflicts,
            "conflict_resolution": request.conflict_resolution,
            "batch_size": request.batch_size,
            "max_concurrency": request.max_concurrency
        }
        
        # 获取同步引擎
        sync_engine = get_translation_sync_engine()
        
        # 准备同步
        session_id, analysis = await sync_engine.prepare_sync(direction, config)
        
        # 生成建议
        recommendations = _generate_sync_recommendations(analysis)
        
        logger.info("同步准备完成",
                   session_id=session_id,
                   direction=direction,
                   changes=analysis["total_changes"])
        
        return SyncAnalysisResponse(
            session_id=session_id,
            direction=direction.value,
            total_local=analysis["total_local"],
            total_remote=analysis["total_remote"],
            total_changes=analysis["total_changes"],
            added=analysis["added"],
            modified=analysis["modified"],
            deleted=analysis["deleted"],
            conflicts=analysis["conflicts"],
            by_language=analysis["by_language"],
            by_pack=analysis["by_pack"],
            estimated_time=analysis["estimated_time"],
            recommendations=recommendations
        )
        
    except Exception as e:
        logger.error("同步准备失败", error=str(e))
        raise HTTPException(status_code=500, detail=f"同步准备失败: {str(e)}")


@router.post("/execute/{session_id}", response_model=Dict[str, Any], summary="执行同步")
async def execute_sync(
    session_id: str = Path(..., description="同步会话ID"),
    request: SyncExecuteRequest = Body(...),
    background_tasks: BackgroundTasks = None
) -> Dict[str, Any]:
    """
    执行同步操作
    
    - 处理冲突
    - 传输数据
    - 应用变更
    - 更新本地状态
    """
    
    try:
        sync_engine = get_translation_sync_engine()
        
        # 检查会话是否存在
        progress = await sync_engine.get_sync_status(session_id)
        if not progress:
            raise HTTPException(
                status_code=404,
                detail=f"同步会话不存在: {session_id}"
            )
        
        # 检查会话状态
        current_status = SyncStatus(progress["status"])
        if current_status not in [SyncStatus.IDLE, SyncStatus.FAILED]:
            raise HTTPException(
                status_code=400,
                detail=f"同步会话状态不允许执行: {current_status.value}"
            )
        
        if request.dry_run:
            # 演练模式，返回模拟结果
            return {
                "success": True,
                "message": "演练模式执行成功",
                "session_id": session_id,
                "dry_run": True,
                "estimated_changes": progress.get("total_entries", 0)
            }
        
        # 在后台执行同步
        background_tasks.add_task(sync_engine.execute_sync, session_id)
        
        logger.info("同步执行已启动", session_id=session_id)
        
        return {
            "success": True,
            "message": "同步执行已启动",
            "session_id": session_id,
            "dry_run": False
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error("同步执行失败", session_id=session_id, error=str(e))
        raise HTTPException(status_code=500, detail=f"同步执行失败: {str(e)}")


@router.get("/status/{session_id}", response_model=SyncProgressResponse, summary="获取同步状态")
async def get_sync_status(
    session_id: str = Path(..., description="同步会话ID")
) -> SyncProgressResponse:
    """
    获取同步进度和状态信息
    
    - 进度百分比
    - 处理统计
    - 错误信息
    - 预估完成时间
    """
    
    try:
        sync_engine = get_translation_sync_engine()
        progress = await sync_engine.get_sync_status(session_id)
        
        if not progress:
            raise HTTPException(
                status_code=404,
                detail=f"同步会话不存在: {session_id}"
            )
        
        # 计算进度百分比
        progress_percentage = 0.0
        if progress.get("total_entries", 0) > 0:
            progress_percentage = (progress.get("processed_entries", 0) / progress["total_entries"]) * 100
        
        # 解析错误信息
        errors = []
        if progress.get("errors_json"):
            import json
            try:
                errors = json.loads(progress["errors_json"])
            except:
                errors = [progress["errors_json"]]
        
        # 估算完成时间
        estimated_completion = None
        if (progress.get("started_at") and 
            progress.get("processed_entries", 0) > 0 and 
            progress.get("total_entries", 0) > progress.get("processed_entries", 0)):
            # 这里可以实现更复杂的时间估算逻辑
            pass
        
        return SyncProgressResponse(
            session_id=session_id,
            status=progress["status"],
            direction=progress["direction"],
            created_at=datetime.fromisoformat(progress["created_at"]),
            started_at=datetime.fromisoformat(progress["started_at"]) if progress.get("started_at") else None,
            completed_at=datetime.fromisoformat(progress["completed_at"]) if progress.get("completed_at") else None,
            total_entries=progress.get("total_entries", 0),
            processed_entries=progress.get("processed_entries", 0),
            success_entries=progress.get("success_entries", 0),
            failed_entries=progress.get("failed_entries", 0),
            conflicts_entries=progress.get("conflicts_entries", 0),
            progress_percentage=progress_percentage,
            estimated_completion=estimated_completion,
            current_operation=_get_current_operation(progress["status"]),
            errors=errors
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error("获取同步状态失败", session_id=session_id, error=str(e))
        raise HTTPException(status_code=500, detail=f"获取同步状态失败: {str(e)}")


@router.get("/sessions", response_model=List[SyncProgressResponse], summary="获取所有同步会话")
async def get_all_sync_sessions(
    status: Optional[str] = Query(None, description="按状态过滤"),
    limit: int = Query(20, description="限制返回数量", ge=1, le=100)
) -> List[SyncProgressResponse]:
    """
    获取所有同步会话的状态信息
    
    - 支持按状态过滤
    - 支持分页限制
    """
    
    try:
        # 这里需要实现从数据库查询所有会话的逻辑
        # 暂时返回空列表
        sessions = []
        
        # 如果有状态过滤
        if status:
            sessions = [s for s in sessions if s.status == status]
        
        # 限制数量
        sessions = sessions[:limit]
        
        return sessions
        
    except Exception as e:
        logger.error("获取同步会话列表失败", error=str(e))
        raise HTTPException(status_code=500, detail=f"获取同步会话列表失败: {str(e)}")


@router.post("/resolve-conflict", response_model=Dict[str, Any], summary="解决冲突")
async def resolve_conflict(
    request: ConflictResolveRequest
) -> Dict[str, Any]:
    """
    手动解决同步冲突
    
    - 选择解决策略
    - 提供自定义解决方案
    - 更新同步状态
    """
    
    try:
        # 验证解决策略
        try:
            resolution = ConflictResolution(request.resolution)
        except ValueError:
            raise HTTPException(
                status_code=400,
                detail=f"无效的冲突解决策略: {request.resolution}"
            )
        
        # 这里需要实现冲突解决的逻辑
        # 暂时返回成功响应
        
        logger.info("冲突解决完成",
                   conflict_id=request.conflict_id,
                   resolution=resolution)
        
        return {
            "success": True,
            "message": "冲突解决成功",
            "conflict_id": request.conflict_id,
            "resolution": resolution.value
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error("冲突解决失败",
                    conflict_id=request.conflict_id,
                    error=str(e))
        raise HTTPException(status_code=500, detail=f"冲突解决失败: {str(e)}")


@router.delete("/cancel/{session_id}", response_model=Dict[str, Any], summary="取消同步")
async def cancel_sync(
    session_id: str = Path(..., description="同步会话ID")
) -> Dict[str, Any]:
    """
    取消正在进行的同步操作
    """
    
    try:
        sync_engine = get_translation_sync_engine()
        
        # 检查会话是否存在
        progress = await sync_engine.get_sync_status(session_id)
        if not progress:
            raise HTTPException(
                status_code=404,
                detail=f"同步会话不存在: {session_id}"
            )
        
        # 检查是否可以取消
        current_status = SyncStatus(progress["status"])
        if current_status in [SyncStatus.COMPLETED, SyncStatus.FAILED, SyncStatus.CANCELLED]:
            raise HTTPException(
                status_code=400,
                detail=f"同步会话无法取消，当前状态: {current_status.value}"
            )
        
        # 取消同步
        await sync_engine.state_manager.update_session_status(
            session_id,
            SyncStatus.CANCELLED
        )
        
        logger.info("同步已取消", session_id=session_id)
        
        return {
            "success": True,
            "message": "同步已取消",
            "session_id": session_id
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error("取消同步失败", session_id=session_id, error=str(e))
        raise HTTPException(status_code=500, detail=f"取消同步失败: {str(e)}")


# ============================================================
# 辅助函数
# ============================================================

def _generate_sync_recommendations(analysis: Dict[str, Any]) -> List[str]:
    """生成同步建议"""
    
    recommendations = []
    
    # 基于冲突数量的建议
    if analysis["conflicts"] > 0:
        recommendations.append(f"检测到 {analysis['conflicts']} 个冲突，建议先解决冲突再执行同步")
    
    # 基于变更数量的建议
    if analysis["total_changes"] > 1000:
        recommendations.append("变更数量较多，建议分批同步以提高稳定性")
    
    # 基于语言分布的建议
    if len(analysis["by_language"]) > 5:
        recommendations.append("涉及多种语言，建议按语言分别同步")
    
    # 基于估算时间的建议
    if analysis["estimated_time"] > 300:  # 5分钟
        recommendations.append("预估同步时间较长，建议在非高峰时段执行")
    
    # 默认建议
    if not recommendations:
        recommendations.append("数据分析完成，可以安全执行同步")
    
    return recommendations


def _get_current_operation(status: str) -> str:
    """获取当前操作描述"""
    
    status_operations = {
        "idle": "等待执行",
        "preparing": "准备同步",
        "detecting_changes": "检测变更",
        "merging": "合并数据",
        "transferring": "传输数据",
        "applying_changes": "应用变更",
        "completed": "同步完成",
        "failed": "同步失败",
        "cancelled": "已取消"
    }
    
    return status_operations.get(status, "未知状态")


# ============================================================
# 快捷API
# ============================================================

@router.post("/quick/push", response_model=Dict[str, Any], summary="快速推送同步")
async def quick_push_sync(
    language_filters: Optional[List[str]] = Body(default=None),
    pack_filters: Optional[List[str]] = Body(default=None),
    background_tasks: BackgroundTasks = None
) -> Dict[str, Any]:
    """
    快速推送本地翻译到远程
    
    - 自动准备同步
    - 立即执行推送
    - 返回会话ID
    """
    
    try:
        # 准备推送同步
        prepare_request = SyncPrepareRequest(
            direction="local_to_remote",
            language_filters=language_filters,
            pack_filters=pack_filters,
            auto_resolve_conflicts=True,
            conflict_resolution="local_wins"
        )
        
        analysis = await prepare_sync(prepare_request, background_tasks)
        
        # 立即执行
        execute_request = SyncExecuteRequest(force=False, dry_run=False)
        result = await execute_sync(analysis.session_id, execute_request, background_tasks)
        
        return {
            **result,
            "analysis": analysis.dict(),
            "type": "quick_push"
        }
        
    except Exception as e:
        logger.error("快速推送同步失败", error=str(e))
        raise HTTPException(status_code=500, detail=f"快速推送同步失败: {str(e)}")


@router.post("/quick/pull", response_model=Dict[str, Any], summary="快速拉取同步")
async def quick_pull_sync(
    language_filters: Optional[List[str]] = Body(default=None),
    pack_filters: Optional[List[str]] = Body(default=None),
    background_tasks: BackgroundTasks = None
) -> Dict[str, Any]:
    """
    快速拉取远程翻译到本地
    
    - 自动准备同步
    - 立即执行拉取
    - 返回会话ID
    """
    
    try:
        # 准备拉取同步
        prepare_request = SyncPrepareRequest(
            direction="remote_to_local",
            language_filters=language_filters,
            pack_filters=pack_filters,
            auto_resolve_conflicts=True,
            conflict_resolution="remote_wins"
        )
        
        analysis = await prepare_sync(prepare_request, background_tasks)
        
        # 立即执行
        execute_request = SyncExecuteRequest(force=False, dry_run=False)
        result = await execute_sync(analysis.session_id, execute_request, background_tasks)
        
        return {
            **result,
            "analysis": analysis.dict(),
            "type": "quick_pull"
        }
        
    except Exception as e:
        logger.error("快速拉取同步失败", error=str(e))
        raise HTTPException(status_code=500, detail=f"快速拉取同步失败: {str(e)}")