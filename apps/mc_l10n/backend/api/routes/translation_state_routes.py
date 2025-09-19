"""
翻译状态管理 - API路由
提供翻译状态管理的REST API接口
"""

from datetime import datetime
from typing import Any, Dict, List, Optional, Set
from fastapi import APIRouter, Depends, HTTPException, Query, Body
from pydantic import BaseModel, Field

import structlog

from ...core.di_container import get_dependency
from ...application.services.translation_state_application_service import (
    TranslationStateApplicationService
)
from ...application.services.translation_state_statistics_service import (
    TranslationStateStatisticsService
)
from ...application.services.translation_batch_operation_service import (
    TranslationBatchOperationService, BatchOperationConfig, BatchOperationType
)

logger = structlog.get_logger(__name__)

router = APIRouter(prefix="/api/v1/translation/states", tags=["翻译状态管理"])


# ============================================================
# 请求/响应模型
# ============================================================

class StateChangeRequest(BaseModel):
    """状态变更请求"""
    entry_uid: str = Field(..., description="翻译条目UID")
    target_state: str = Field(..., description="目标状态")
    reason: str = Field("", description="变更原因")
    metadata: Optional[Dict[str, Any]] = Field(None, description="额外元数据")


class BatchStateChangeRequest(BaseModel):
    """批量状态变更请求"""
    operation_name: str = Field(..., description="操作名称")
    target_state: str = Field(..., description="目标状态")
    filter_criteria: Dict[str, Any] = Field(..., description="筛选条件")
    reason: str = Field("", description="变更原因")
    max_concurrent: int = Field(5, description="最大并发数")


class BatchAssignmentRequest(BaseModel):
    """批量分配请求"""
    operation_name: str = Field(..., description="操作名称")
    assignee_id: str = Field(..., description="被分配者ID")
    assignee_name: str = Field(..., description="被分配者名称")
    assignment_type: str = Field("translate", description="分配类型")
    filter_criteria: Dict[str, Any] = Field(..., description="筛选条件")


class BatchReviewRequest(BaseModel):
    """批量审核请求"""
    operation_name: str = Field(..., description="操作名称")
    review_action: str = Field(..., description="审核动作: approve, reject, request_revision")
    review_comment: str = Field("", description="审核评论")
    filter_criteria: Dict[str, Any] = Field(..., description="筛选条件")


class StateActionRequest(BaseModel):
    """状态动作请求"""
    entry_uid: str = Field(..., description="翻译条目UID")
    action_name: str = Field(..., description="动作名称")
    params: Optional[Dict[str, Any]] = Field(None, description="动作参数")


class ProgressReportRequest(BaseModel):
    """进度报告请求"""
    project_uid: Optional[str] = Field(None, description="项目UID")
    mod_uid: Optional[str] = Field(None, description="MOD UID")
    locale: Optional[str] = Field(None, description="语言代码")


# ============================================================
# 状态管理接口
# ============================================================

@router.get("/list", summary="获取所有翻译状态")
async def list_states(
    state_service: TranslationStateApplicationService = Depends(
        lambda: get_dependency(TranslationStateApplicationService)
    )
):
    """获取所有可用的翻译状态"""
    try:
        states = state_service.state_machine.states
        
        result = []
        for state_key, state in states.items():
            result.append({
                "state_key": state_key,
                "display_name": state.display_name,
                "description": state.description,
                "category": state.category.value,
                "color_hex": state.color_hex,
                "icon_name": state.icon_name,
                "sort_order": state.sort_order,
                "is_active": state.is_active,
                "is_terminal": state.is_terminal,
                "is_locked": state.is_locked
            })
        
        # 按排序顺序排列
        result.sort(key=lambda x: x["sort_order"])
        
        return {
            "success": True,
            "data": result,
            "count": len(result)
        }
        
    except Exception as e:
        logger.error(f"获取状态列表失败: {e}")
        raise HTTPException(status_code=500, detail=f"获取状态列表失败: {str(e)}")


@router.post("/change", summary="变更翻译条目状态")
async def change_state(
    request: StateChangeRequest,
    operator_id: str = Query(..., description="操作者ID"),
    operator_name: str = Query(..., description="操作者名称"),
    state_service: TranslationStateApplicationService = Depends(
        lambda: get_dependency(TranslationStateApplicationService)
    )
):
    """变更翻译条目状态"""
    try:
        success, error_msg = state_service.change_translation_state(
            request.entry_uid,
            request.target_state,
            operator_id,
            operator_name,
            request.reason,
            request.metadata
        )
        
        if success:
            return {
                "success": True,
                "message": "状态变更成功",
                "data": {
                    "entry_uid": request.entry_uid,
                    "new_state": request.target_state
                }
            }
        else:
            raise HTTPException(status_code=400, detail=error_msg)
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"状态变更失败", entry_uid=request.entry_uid, error=str(e))
        raise HTTPException(status_code=500, detail=f"状态变更失败: {str(e)}")


@router.get("/actions/{entry_uid}", summary="获取条目可用动作")
async def get_available_actions(
    entry_uid: str,
    operator_role: str = Query("translator", description="操作者角色"),
    state_service: TranslationStateApplicationService = Depends(
        lambda: get_dependency(TranslationStateApplicationService)
    )
):
    """获取翻译条目的可用动作"""
    try:
        actions = state_service.get_available_actions(entry_uid, operator_role)
        
        return {
            "success": True,
            "data": actions,
            "count": len(actions)
        }
        
    except Exception as e:
        logger.error(f"获取可用动作失败", entry_uid=entry_uid, error=str(e))
        raise HTTPException(status_code=500, detail=f"获取可用动作失败: {str(e)}")


@router.get("/history/{entry_uid}", summary="获取条目状态历史")
async def get_entry_history(
    entry_uid: str,
    limit: int = Query(20, description="返回记录数量限制"),
    state_service: TranslationStateApplicationService = Depends(
        lambda: get_dependency(TranslationStateApplicationService)
    )
):
    """获取翻译条目的状态变更历史"""
    try:
        history = state_service.get_entry_history(entry_uid, limit)
        
        return {
            "success": True,
            "data": history,
            "count": len(history)
        }
        
    except Exception as e:
        logger.error(f"获取条目历史失败", entry_uid=entry_uid, error=str(e))
        raise HTTPException(status_code=500, detail=f"获取条目历史失败: {str(e)}")


@router.get("/activities/recent", summary="获取最近的状态变更活动")
async def get_recent_activities(
    limit: int = Query(50, description="返回记录数量限制"),
    state_service: TranslationStateApplicationService = Depends(
        lambda: get_dependency(TranslationStateApplicationService)
    )
):
    """获取最近的状态变更活动"""
    try:
        activities = state_service.get_recent_activities(limit)
        
        return {
            "success": True,
            "data": activities,
            "count": len(activities)
        }
        
    except Exception as e:
        logger.error(f"获取最近活动失败: {e}")
        raise HTTPException(status_code=500, detail=f"获取最近活动失败: {str(e)}")


@router.post("/auto-transition/{entry_uid}", summary="检查并执行自动状态转换")
async def check_auto_transitions(
    entry_uid: str,
    state_service: TranslationStateApplicationService = Depends(
        lambda: get_dependency(TranslationStateApplicationService)
    )
):
    """检查并执行自动状态转换"""
    try:
        transitions = state_service.check_auto_transitions(entry_uid)
        
        return {
            "success": True,
            "data": transitions,
            "count": len(transitions)
        }
        
    except Exception as e:
        logger.error(f"自动转换检查失败", entry_uid=entry_uid, error=str(e))
        raise HTTPException(status_code=500, detail=f"自动转换检查失败: {str(e)}")


# ============================================================
# 批量操作接口
# ============================================================

@router.post("/batch/state-change", summary="批量状态变更")
async def batch_state_change(
    request: BatchStateChangeRequest,
    operator_id: str = Query(..., description="操作者ID"),
    operator_name: str = Query(..., description="操作者名称"),
    batch_service: TranslationBatchOperationService = Depends(
        lambda: get_dependency(TranslationBatchOperationService)
    )
):
    """批量变更翻译条目状态"""
    try:
        config = BatchOperationConfig(
            operation_type=BatchOperationType.STATE_CHANGE,
            operation_name=request.operation_name,
            target_filter=request.filter_criteria,
            operation_params={
                "target_state": request.target_state,
                "reason": request.reason
            },
            operator_id=operator_id,
            operator_name=operator_name,
            max_concurrent=request.max_concurrent
        )
        
        operation_id = batch_service.start_batch_operation(config)
        
        return {
            "success": True,
            "message": "批量操作已启动",
            "data": {"operation_id": operation_id}
        }
        
    except Exception as e:
        logger.error(f"批量状态变更失败: {e}")
        raise HTTPException(status_code=500, detail=f"批量状态变更失败: {str(e)}")


@router.post("/batch/assignment", summary="批量分配")
async def batch_assignment(
    request: BatchAssignmentRequest,
    operator_id: str = Query(..., description="操作者ID"),
    operator_name: str = Query(..., description="操作者名称"),
    batch_service: TranslationBatchOperationService = Depends(
        lambda: get_dependency(TranslationBatchOperationService)
    )
):
    """批量分配翻译条目"""
    try:
        config = BatchOperationConfig(
            operation_type=BatchOperationType.ASSIGNMENT,
            operation_name=request.operation_name,
            target_filter=request.filter_criteria,
            operation_params={
                "assignee_id": request.assignee_id,
                "assignee_name": request.assignee_name,
                "assignment_type": request.assignment_type
            },
            operator_id=operator_id,
            operator_name=operator_name
        )
        
        operation_id = batch_service.start_batch_operation(config)
        
        return {
            "success": True,
            "message": "批量分配已启动",
            "data": {"operation_id": operation_id}
        }
        
    except Exception as e:
        logger.error(f"批量分配失败: {e}")
        raise HTTPException(status_code=500, detail=f"批量分配失败: {str(e)}")


@router.post("/batch/review", summary="批量审核")
async def batch_review(
    request: BatchReviewRequest,
    operator_id: str = Query(..., description="操作者ID"),
    operator_name: str = Query(..., description="操作者名称"),
    batch_service: TranslationBatchOperationService = Depends(
        lambda: get_dependency(TranslationBatchOperationService)
    )
):
    """批量审核翻译条目"""
    try:
        config = BatchOperationConfig(
            operation_type=BatchOperationType.REVIEW,
            operation_name=request.operation_name,
            target_filter=request.filter_criteria,
            operation_params={
                "review_action": request.review_action,
                "review_comment": request.review_comment
            },
            operator_id=operator_id,
            operator_name=operator_name
        )
        
        operation_id = batch_service.start_batch_operation(config)
        
        return {
            "success": True,
            "message": "批量审核已启动",
            "data": {"operation_id": operation_id}
        }
        
    except Exception as e:
        logger.error(f"批量审核失败: {e}")
        raise HTTPException(status_code=500, detail=f"批量审核失败: {str(e)}")


@router.get("/batch/operations", summary="获取批量操作列表")
async def list_batch_operations(
    status: Optional[str] = Query(None, description="操作状态过滤"),
    batch_service: TranslationBatchOperationService = Depends(
        lambda: get_dependency(TranslationBatchOperationService)
    )
):
    """获取批量操作列表"""
    try:
        if status == "active":
            operations = batch_service.list_active_operations()
            data = [
                {
                    "operation_id": op.operation_id,
                    "operation_type": op.operation_type,
                    "status": op.status.value,
                    "total_count": op.total_count,
                    "processed_count": op.processed_count,
                    "success_count": op.success_count,
                    "failed_count": op.failed_count,
                    "started_at": op.started_at.isoformat() if op.started_at else None
                }
                for op in operations
            ]
        else:
            history = batch_service.get_operation_history(7)
            data = history
        
        return {
            "success": True,
            "data": data,
            "count": len(data)
        }
        
    except Exception as e:
        logger.error(f"获取批量操作列表失败: {e}")
        raise HTTPException(status_code=500, detail=f"获取批量操作列表失败: {str(e)}")


@router.get("/batch/operations/{operation_id}", summary="获取批量操作状态")
async def get_batch_operation_status(
    operation_id: str,
    batch_service: TranslationBatchOperationService = Depends(
        lambda: get_dependency(TranslationBatchOperationService)
    )
):
    """获取批量操作状态"""
    try:
        result = batch_service.get_operation_status(operation_id)
        
        if not result:
            raise HTTPException(status_code=404, detail="操作不存在")
        
        return {
            "success": True,
            "data": {
                "operation_id": result.operation_id,
                "operation_type": result.operation_type,
                "status": result.status.value,
                "total_count": result.total_count,
                "processed_count": result.processed_count,
                "success_count": result.success_count,
                "failed_count": result.failed_count,
                "skipped_count": result.skipped_count,
                "error_message": result.error_message,
                "started_at": result.started_at.isoformat() if result.started_at else None,
                "completed_at": result.completed_at.isoformat() if result.completed_at else None
            }
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"获取批量操作状态失败", operation_id=operation_id, error=str(e))
        raise HTTPException(status_code=500, detail=f"获取批量操作状态失败: {str(e)}")


@router.post("/batch/operations/{operation_id}/cancel", summary="取消批量操作")
async def cancel_batch_operation(
    operation_id: str,
    batch_service: TranslationBatchOperationService = Depends(
        lambda: get_dependency(TranslationBatchOperationService)
    )
):
    """取消批量操作"""
    try:
        success = batch_service.cancel_operation(operation_id)
        
        if success:
            return {
                "success": True,
                "message": "操作已取消"
            }
        else:
            raise HTTPException(status_code=400, detail="无法取消操作（操作不存在或已完成）")
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"取消批量操作失败", operation_id=operation_id, error=str(e))
        raise HTTPException(status_code=500, detail=f"取消批量操作失败: {str(e)}")


# ============================================================
# 统计和报表接口
# ============================================================

@router.get("/statistics", summary="获取状态统计信息")
async def get_statistics(
    state_service: TranslationStateApplicationService = Depends(
        lambda: get_dependency(TranslationStateApplicationService)
    )
):
    """获取翻译状态统计信息"""
    try:
        stats = state_service.get_state_statistics()
        
        return {
            "success": True,
            "data": stats
        }
        
    except Exception as e:
        logger.error(f"获取状态统计失败: {e}")
        raise HTTPException(status_code=500, detail=f"获取状态统计失败: {str(e)}")


@router.get("/statistics/comprehensive", summary="获取综合统计信息")
async def get_comprehensive_statistics(
    days: int = Query(30, description="统计天数"),
    stats_service: TranslationStateStatisticsService = Depends(
        lambda: get_dependency(TranslationStateStatisticsService)
    )
):
    """获取综合统计信息"""
    try:
        stats = stats_service.get_comprehensive_statistics(days)
        
        return {
            "success": True,
            "data": stats
        }
        
    except Exception as e:
        logger.error(f"获取综合统计失败: {e}")
        raise HTTPException(status_code=500, detail=f"获取综合统计失败: {str(e)}")


@router.post("/reports/progress", summary="获取进度报告")
async def get_progress_report(
    request: ProgressReportRequest,
    stats_service: TranslationStateStatisticsService = Depends(
        lambda: get_dependency(TranslationStateStatisticsService)
    )
):
    """获取进度报告"""
    try:
        report = stats_service.get_progress_report(
            request.project_uid,
            request.mod_uid,
            request.locale
        )
        
        return {
            "success": True,
            "data": report
        }
        
    except Exception as e:
        logger.error(f"获取进度报告失败: {e}")
        raise HTTPException(status_code=500, detail=f"获取进度报告失败: {str(e)}")


@router.get("/reports/performance", summary="获取性能分析")
async def get_performance_analysis(
    days: int = Query(30, description="分析天数"),
    stats_service: TranslationStateStatisticsService = Depends(
        lambda: get_dependency(TranslationStateStatisticsService)
    )
):
    """获取性能分析报告"""
    try:
        analysis = stats_service.get_performance_analysis(days)
        
        return {
            "success": True,
            "data": analysis
        }
        
    except Exception as e:
        logger.error(f"获取性能分析失败: {e}")
        raise HTTPException(status_code=500, detail=f"获取性能分析失败: {str(e)}")


@router.get("/reports/quality", summary="获取质量仪表板")
async def get_quality_dashboard(
    stats_service: TranslationStateStatisticsService = Depends(
        lambda: get_dependency(TranslationStateStatisticsService)
    )
):
    """获取质量仪表板"""
    try:
        dashboard = stats_service.get_quality_dashboard()
        
        return {
            "success": True,
            "data": dashboard
        }
        
    except Exception as e:
        logger.error(f"获取质量仪表板失败: {e}")
        raise HTTPException(status_code=500, detail=f"获取质量仪表板失败: {str(e)}")


@router.get("/reports/workload", summary="获取工作负载报告")
async def get_workload_report(
    days: int = Query(30, description="报告天数"),
    stats_service: TranslationStateStatisticsService = Depends(
        lambda: get_dependency(TranslationStateStatisticsService)
    )
):
    """获取工作负载报告"""
    try:
        report = stats_service.get_workload_report(days)
        
        return {
            "success": True,
            "data": report
        }
        
    except Exception as e:
        logger.error(f"获取工作负载报告失败: {e}")
        raise HTTPException(status_code=500, detail=f"获取工作负载报告失败: {str(e)}")


# ============================================================
# 工作流管理接口
# ============================================================

@router.get("/workflow/recommendations", summary="获取工作流建议")
async def get_workflow_recommendations(
    project_uid: Optional[str] = Query(None, description="项目UID"),
    mod_uid: Optional[str] = Query(None, description="MOD UID"),
    state_service: TranslationStateApplicationService = Depends(
        lambda: get_dependency(TranslationStateApplicationService)
    )
):
    """获取工作流建议"""
    try:
        recommendations = state_service.get_workflow_recommendations(project_uid, mod_uid)
        
        return {
            "success": True,
            "data": recommendations,
            "count": len(recommendations)
        }
        
    except Exception as e:
        logger.error(f"获取工作流建议失败: {e}")
        raise HTTPException(status_code=500, detail=f"获取工作流建议失败: {str(e)}")