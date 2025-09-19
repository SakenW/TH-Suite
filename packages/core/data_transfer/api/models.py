"""
翻译数据传输API模型定义

定义了API请求和响应的数据模型
"""

from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field

from ..models import SyncStrategy, TranslationEntry, TranslationProject


class ExtractRequest(BaseModel):
    """提取翻译数据请求"""
    
    project_path: str = Field(..., description="项目根路径")
    incremental: bool = Field(True, description="是否增量提取")
    target_languages: Optional[List[str]] = Field(None, description="目标语言列表")
    includes: Optional[List[str]] = Field(None, description="包含的MOD/包模式")
    excludes: Optional[List[str]] = Field(None, description="排除的模式")


class ExtractResponse(BaseModel):
    """提取翻译数据响应"""
    
    success: bool = Field(..., description="是否成功")
    message: str = Field("", description="消息")
    data: Optional[Dict[str, Any]] = Field(None, description="数据")
    
    # 统计信息
    total_entries: int = Field(0, description="总条目数")
    total_mods: int = Field(0, description="总MOD数")
    processing_time: float = Field(0.0, description="处理时间(秒)")


class SyncRequest(BaseModel):
    """同步翻译数据请求"""
    
    project_id: str = Field(..., description="项目ID")
    strategy: SyncStrategy = Field(SyncStrategy.INCREMENTAL, description="同步策略")
    force: bool = Field(False, description="是否强制同步")
    conflict_resolution: Optional[str] = Field(None, description="冲突解决策略")


class SyncResponse(BaseModel):
    """同步翻译数据响应"""
    
    success: bool = Field(..., description="是否成功")
    message: str = Field("", description="消息")
    data: Optional[Dict[str, Any]] = Field(None, description="数据")
    
    # 同步统计
    pushed_entries: int = Field(0, description="推送的条目数")
    pulled_entries: int = Field(0, description="拉取的条目数")
    conflicts_detected: int = Field(0, description="检测到的冲突数")
    conflicts_resolved: int = Field(0, description="解决的冲突数")
    processing_time: float = Field(0.0, description="处理时间(秒)")


class DiffRequest(BaseModel):
    """获取翻译差异请求"""
    
    project_id: str = Field(..., description="项目ID")
    from_version: int = Field(..., description="起始版本")
    to_version: int = Field(..., description="目标版本")
    include_content: bool = Field(True, description="是否包含条目内容")


class DiffResponse(BaseModel):
    """获取翻译差异响应"""
    
    success: bool = Field(..., description="是否成功")
    message: str = Field("", description="消息")
    data: Optional[Dict[str, Any]] = Field(None, description="数据")
    
    # 差异统计
    added_count: int = Field(0, description="新增条目数")
    modified_count: int = Field(0, description="修改条目数")
    deleted_count: int = Field(0, description="删除条目数")
    moved_count: int = Field(0, description="移动条目数")


class ApplyRequest(BaseModel):
    """应用翻译数据请求"""
    
    project_id: str = Field(..., description="项目ID")
    target_path: str = Field(..., description="目标路径")
    entries: Optional[List[Dict[str, Any]]] = Field(None, description="指定的翻译条目")
    languages: Optional[List[str]] = Field(None, description="目标语言")
    backup: bool = Field(True, description="是否备份原文件")


class ApplyResponse(BaseModel):
    """应用翻译数据响应"""
    
    success: bool = Field(..., description="是否成功")
    message: str = Field("", description="消息")
    data: Optional[Dict[str, Any]] = Field(None, description="数据")
    
    # 应用统计
    applied_files: int = Field(0, description="应用的文件数")
    applied_entries: int = Field(0, description="应用的条目数")
    backup_path: Optional[str] = Field(None, description="备份路径")
    processing_time: float = Field(0.0, description="处理时间(秒)")


class StatusResponse(BaseModel):
    """翻译状态响应"""
    
    success: bool = Field(..., description="是否成功")
    message: str = Field("", description="消息")
    data: Optional[Dict[str, Any]] = Field(None, description="状态数据")


class BatchRequest(BaseModel):
    """批量操作请求"""
    
    project_id: str = Field(..., description="项目ID")
    operations: List[Dict[str, Any]] = Field(..., description="操作列表")
    parallel: bool = Field(True, description="是否并行执行")


class BatchResponse(BaseModel):
    """批量操作响应"""
    
    success: bool = Field(..., description="是否成功")
    message: str = Field("", description="消息")
    results: List[Dict[str, Any]] = Field([], description="操作结果列表")
    
    # 统计信息
    total_operations: int = Field(0, description="总操作数")
    successful_operations: int = Field(0, description="成功操作数")
    failed_operations: int = Field(0, description="失败操作数")
    processing_time: float = Field(0.0, description="处理时间(秒)")


class WebSocketMessage(BaseModel):
    """WebSocket消息模型"""
    
    type: str = Field(..., description="消息类型")
    project_id: Optional[str] = Field(None, description="项目ID")
    data: Optional[Dict[str, Any]] = Field(None, description="消息数据")
    timestamp: Optional[str] = Field(None, description="时间戳")


class TranslationUpdateMessage(WebSocketMessage):
    """翻译更新消息"""
    
    type: str = Field("translation_update", description="消息类型")
    entry: Dict[str, Any] = Field(..., description="翻译条目数据")
    operation: str = Field(..., description="操作类型: create/update/delete")


class SyncProgressMessage(WebSocketMessage):
    """同步进度消息"""
    
    type: str = Field("sync_progress", description="消息类型")
    progress: float = Field(..., description="进度百分比 0-100")
    stage: str = Field(..., description="当前阶段")
    details: Optional[str] = Field(None, description="详细信息")


class ConflictNotificationMessage(WebSocketMessage):
    """冲突通知消息"""
    
    type: str = Field("conflict_notification", description="消息类型")
    conflicts: List[Dict[str, Any]] = Field(..., description="冲突列表")
    auto_resolved: int = Field(0, description="自动解决的冲突数")
    manual_required: int = Field(0, description="需要手动解决的冲突数")


class ProjectStatusMessage(WebSocketMessage):
    """项目状态消息"""
    
    type: str = Field("project_status", description="消息类型")
    status: str = Field(..., description="项目状态")
    statistics: Dict[str, Any] = Field(..., description="统计信息")


class ErrorMessage(WebSocketMessage):
    """错误消息"""
    
    type: str = Field("error", description="消息类型")
    error_code: str = Field(..., description="错误代码")
    error_message: str = Field(..., description="错误消息")
    details: Optional[Dict[str, Any]] = Field(None, description="错误详情")


# 消息工厂函数
def create_translation_update_message(
    project_id: str,
    entry: TranslationEntry,
    operation: str
) -> TranslationUpdateMessage:
    """创建翻译更新消息"""
    
    return TranslationUpdateMessage(
        project_id=project_id,
        entry=entry.to_dict(),
        operation=operation,
        timestamp=entry.last_modified.isoformat()
    )


def create_sync_progress_message(
    project_id: str,
    progress: float,
    stage: str,
    details: Optional[str] = None
) -> SyncProgressMessage:
    """创建同步进度消息"""
    
    from datetime import datetime
    
    return SyncProgressMessage(
        project_id=project_id,
        progress=progress,
        stage=stage,
        details=details,
        timestamp=datetime.now().isoformat()
    )


def create_conflict_notification_message(
    project_id: str,
    conflicts: List[Any],  # List[TranslationConflict]
    auto_resolved: int = 0,
    manual_required: int = 0
) -> ConflictNotificationMessage:
    """创建冲突通知消息"""
    
    from datetime import datetime
    
    return ConflictNotificationMessage(
        project_id=project_id,
        conflicts=[
            {
                "entry_id": c.entry_id,
                "conflict_type": c.conflict_type.value,
                "local_version": c.local_entry.version if c.local_entry else None,
                "remote_version": c.remote_entry.version if c.remote_entry else None
            }
            for c in conflicts
        ],
        auto_resolved=auto_resolved,
        manual_required=manual_required,
        timestamp=datetime.now().isoformat()
    )


def create_error_message(
    error_code: str,
    error_message: str,
    project_id: Optional[str] = None,
    details: Optional[Dict[str, Any]] = None
) -> ErrorMessage:
    """创建错误消息"""
    
    from datetime import datetime
    
    return ErrorMessage(
        project_id=project_id,
        error_code=error_code,
        error_message=error_message,
        details=details,
        timestamp=datetime.now().isoformat()
    )