"""
翻译批量操作服务
实现批量状态变更、分配、审核等操作的管理和执行
"""

import uuid
import json
from datetime import datetime
from typing import Any, Dict, List, Optional, Set, Callable
from enum import Enum
from dataclasses import dataclass
from concurrent.futures import ThreadPoolExecutor, as_completed
import asyncio

import structlog

from domain.models.translation_state import StateHistory
from infrastructure.repositories.core_translation_entry_repository import (
    CoreTranslationEntryRepository, CoreTranslationEntry
)
from infrastructure.repositories.translation_state_repository import StateHistoryRepository
from .translation_state_application_service import TranslationStateApplicationService

logger = structlog.get_logger(__name__)


class BatchOperationType(Enum):
    """批量操作类型"""
    STATE_CHANGE = "state_change"
    ASSIGNMENT = "assignment"
    REVIEW = "review"
    PUBLICATION = "publication"
    CLEANUP = "cleanup"


class BatchOperationStatus(Enum):
    """批量操作状态"""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


@dataclass
class BatchOperationConfig:
    """批量操作配置"""
    operation_type: BatchOperationType
    operation_name: str
    target_filter: Dict[str, Any]
    operation_params: Dict[str, Any]
    operator_id: str
    operator_name: str
    max_concurrent: int = 5
    timeout_seconds: int = 300
    auto_retry: bool = True
    retry_count: int = 3


@dataclass
class BatchOperationResult:
    """批量操作结果"""
    operation_id: str
    operation_type: str
    status: BatchOperationStatus
    total_count: int
    processed_count: int
    success_count: int
    failed_count: int
    skipped_count: int
    error_message: Optional[str] = None
    details: List[Dict[str, Any]] = None
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None


class TranslationBatchOperationService:
    """翻译批量操作服务"""
    
    def __init__(
        self,
        entry_repo: CoreTranslationEntryRepository,
        history_repo: StateHistoryRepository,
        state_service: TranslationStateApplicationService
    ):
        self.entry_repo = entry_repo
        self.history_repo = history_repo
        self.state_service = state_service
        self.active_operations: Dict[str, BatchOperationResult] = {}
    
    async def execute_batch_operation(
        self,
        config: BatchOperationConfig
    ) -> BatchOperationResult:
        """
        执行批量操作
        
        Args:
            config: 批量操作配置
            
        Returns:
            批量操作结果
        """
        operation_id = str(uuid.uuid4())
        
        try:
            # 创建操作结果记录
            result = BatchOperationResult(
                operation_id=operation_id,
                operation_type=config.operation_type.value,
                status=BatchOperationStatus.PENDING,
                total_count=0,
                processed_count=0,
                success_count=0,
                failed_count=0,
                skipped_count=0,
                details=[],
                started_at=datetime.now()
            )
            
            self.active_operations[operation_id] = result
            
            # 查找目标条目
            entries = await self._find_target_entries(config.target_filter)
            result.total_count = len(entries)
            
            if not entries:
                result.status = BatchOperationStatus.COMPLETED
                result.completed_at = datetime.now()
                result.error_message = "没有找到符合条件的翻译条目"
                return result
            
            # 记录到数据库
            await self._create_batch_operation_record(operation_id, config, result)
            
            # 更新状态为运行中
            result.status = BatchOperationStatus.RUNNING
            
            # 根据操作类型执行相应的处理
            if config.operation_type == BatchOperationType.STATE_CHANGE:
                await self._execute_state_change_batch(operation_id, config, entries)
            elif config.operation_type == BatchOperationType.ASSIGNMENT:
                await self._execute_assignment_batch(operation_id, config, entries)
            elif config.operation_type == BatchOperationType.REVIEW:
                await self._execute_review_batch(operation_id, config, entries)
            elif config.operation_type == BatchOperationType.PUBLICATION:
                await self._execute_publication_batch(operation_id, config, entries)
            elif config.operation_type == BatchOperationType.CLEANUP:
                await self._execute_cleanup_batch(operation_id, config, entries)
            else:
                raise ValueError(f"不支持的操作类型: {config.operation_type}")
            
            # 更新最终状态
            result = self.active_operations[operation_id]
            result.status = BatchOperationStatus.COMPLETED
            result.completed_at = datetime.now()
            
            # 更新数据库记录
            await self._update_batch_operation_record(operation_id, result)
            
            logger.info(
                "批量操作完成",
                operation_id=operation_id,
                operation_type=config.operation_type.value,
                total=result.total_count,
                success=result.success_count,
                failed=result.failed_count
            )
            
            return result
            
        except Exception as e:
            logger.error(f"批量操作失败", operation_id=operation_id, error=str(e))
            
            result = self.active_operations.get(operation_id)
            if result:
                result.status = BatchOperationStatus.FAILED
                result.error_message = str(e)
                result.completed_at = datetime.now()
                await self._update_batch_operation_record(operation_id, result)
            
            raise
    
    def start_batch_operation(
        self,
        config: BatchOperationConfig
    ) -> str:
        """
        启动批量操作（异步）
        
        Args:
            config: 批量操作配置
            
        Returns:
            操作ID
        """
        operation_id = str(uuid.uuid4())
        
        # 创建初始记录
        result = BatchOperationResult(
            operation_id=operation_id,
            operation_type=config.operation_type.value,
            status=BatchOperationStatus.PENDING,
            total_count=0,
            processed_count=0,
            success_count=0,
            failed_count=0,
            skipped_count=0
        )
        
        self.active_operations[operation_id] = result
        
        # 在后台执行操作
        asyncio.create_task(self.execute_batch_operation(config))
        
        return operation_id
    
    def get_operation_status(self, operation_id: str) -> Optional[BatchOperationResult]:
        """获取操作状态"""
        return self.active_operations.get(operation_id)
    
    def cancel_operation(self, operation_id: str) -> bool:
        """取消操作"""
        result = self.active_operations.get(operation_id)
        if result and result.status == BatchOperationStatus.RUNNING:
            result.status = BatchOperationStatus.CANCELLED
            result.completed_at = datetime.now()
            return True
        return False
    
    def list_active_operations(self) -> List[BatchOperationResult]:
        """列出活跃的操作"""
        return [
            result for result in self.active_operations.values()
            if result.status in [BatchOperationStatus.PENDING, BatchOperationStatus.RUNNING]
        ]
    
    def get_operation_history(self, days: int = 7) -> List[Dict[str, Any]]:
        """获取操作历史"""
        try:
            query = """
                SELECT operation_id, operation_type, operation_name, total_count,
                       success_count, failed_count, status, created_at, completed_at,
                       operator_name
                FROM translation_batch_operations
                WHERE created_at >= datetime('now', '-{} days')
                ORDER BY created_at DESC
            """.format(days)
            
            rows = self.entry_repo.execute_query(query)
            
            history = []
            for row in rows:
                history.append({
                    "operation_id": row['operation_id'],
                    "operation_type": row['operation_type'],
                    "operation_name": row['operation_name'],
                    "total_count": row['total_count'],
                    "success_count": row['success_count'],
                    "failed_count": row['failed_count'],
                    "status": row['status'],
                    "created_at": row['created_at'],
                    "completed_at": row['completed_at'],
                    "operator_name": row['operator_name']
                })
            
            return history
            
        except Exception as e:
            logger.error(f"获取操作历史失败: {e}")
            return []
    
    async def _find_target_entries(self, filter_criteria: Dict[str, Any]) -> List[CoreTranslationEntry]:
        """查找目标条目"""
        query_parts = ["SELECT * FROM core_translation_entries WHERE 1=1"]
        params = []
        
        # 构建查询条件
        if "status" in filter_criteria:
            if isinstance(filter_criteria["status"], list):
                placeholders = ",".join("?" * len(filter_criteria["status"]))
                query_parts.append(f"AND status IN ({placeholders})")
                params.extend(filter_criteria["status"])
            else:
                query_parts.append("AND status = ?")
                params.append(filter_criteria["status"])
        
        if "language_file_uid" in filter_criteria:
            query_parts.append("AND language_file_uid = ?")
            params.append(filter_criteria["language_file_uid"])
        
        if "key_pattern" in filter_criteria:
            query_parts.append("AND key LIKE ?")
            params.append(f"%{filter_criteria['key_pattern']}%")
        
        if "src_text_pattern" in filter_criteria:
            query_parts.append("AND src_text LIKE ?")
            params.append(f"%{filter_criteria['src_text_pattern']}%")
        
        if "updated_before" in filter_criteria:
            query_parts.append("AND updated_at < ?")
            params.append(filter_criteria["updated_before"])
        
        if "updated_after" in filter_criteria:
            query_parts.append("AND updated_at > ?")
            params.append(filter_criteria["updated_after"])
        
        # 添加限制
        limit = filter_criteria.get("limit", 1000)
        query_parts.append(f"LIMIT {limit}")
        
        query = " ".join(query_parts)
        rows = self.entry_repo.execute_query(query, params)
        
        return [self.entry_repo._row_to_entity(row) for row in rows]
    
    async def _execute_state_change_batch(
        self,
        operation_id: str,
        config: BatchOperationConfig,
        entries: List[CoreTranslationEntry]
    ):
        """执行批量状态变更"""
        target_state = config.operation_params.get("target_state")
        reason = config.operation_params.get("reason", "批量状态变更")
        
        if not target_state:
            raise ValueError("缺少目标状态参数")
        
        result = self.active_operations[operation_id]
        
        # 使用线程池并发处理
        with ThreadPoolExecutor(max_workers=config.max_concurrent) as executor:
            futures = []
            
            for entry in entries:
                future = executor.submit(
                    self._process_single_state_change,
                    entry, target_state, config.operator_id, config.operator_name, reason
                )
                futures.append((future, entry))
            
            # 处理结果
            for future, entry in futures:
                try:
                    success, error_msg = future.result(timeout=config.timeout_seconds)
                    
                    if success:
                        result.success_count += 1
                        await self._record_batch_detail(operation_id, entry.uid, "success")
                    else:
                        result.failed_count += 1
                        await self._record_batch_detail(operation_id, entry.uid, "failed", error_msg)
                    
                    result.processed_count += 1
                    
                except Exception as e:
                    result.failed_count += 1
                    result.processed_count += 1
                    await self._record_batch_detail(operation_id, entry.uid, "failed", str(e))
                    logger.error(f"处理条目失败", entry_uid=entry.uid, error=str(e))
    
    async def _execute_assignment_batch(
        self,
        operation_id: str,
        config: BatchOperationConfig,
        entries: List[CoreTranslationEntry]
    ):
        """执行批量分配"""
        assignee_id = config.operation_params.get("assignee_id")
        assignee_name = config.operation_params.get("assignee_name")
        assignment_type = config.operation_params.get("assignment_type", "translate")
        
        if not assignee_id or not assignee_name:
            raise ValueError("缺少分配目标参数")
        
        result = self.active_operations[operation_id]
        
        for entry in entries:
            try:
                # 创建分配记录
                assignment_id = str(uuid.uuid4())
                await self._create_assignment_record(
                    assignment_id, entry.uid, assignee_id, assignee_name,
                    config.operator_id, config.operator_name, assignment_type
                )
                
                result.success_count += 1
                await self._record_batch_detail(operation_id, entry.uid, "success")
                
            except Exception as e:
                result.failed_count += 1
                await self._record_batch_detail(operation_id, entry.uid, "failed", str(e))
                logger.error(f"分配条目失败", entry_uid=entry.uid, error=str(e))
            
            result.processed_count += 1
    
    async def _execute_review_batch(
        self,
        operation_id: str,
        config: BatchOperationConfig,
        entries: List[CoreTranslationEntry]
    ):
        """执行批量审核"""
        review_action = config.operation_params.get("review_action", "approve")
        review_comment = config.operation_params.get("review_comment", "")
        
        result = self.active_operations[operation_id]
        
        for entry in entries:
            try:
                if review_action == "approve":
                    target_state = "reviewed"
                elif review_action == "reject":
                    target_state = "rejected"
                elif review_action == "request_revision":
                    target_state = "needs_revision"
                else:
                    raise ValueError(f"不支持的审核动作: {review_action}")
                
                success, error_msg = self._process_single_state_change(
                    entry, target_state, config.operator_id, config.operator_name,
                    f"批量审核: {review_comment}"
                )
                
                if success:
                    result.success_count += 1
                    await self._record_batch_detail(operation_id, entry.uid, "success")
                else:
                    result.failed_count += 1
                    await self._record_batch_detail(operation_id, entry.uid, "failed", error_msg)
                
            except Exception as e:
                result.failed_count += 1
                await self._record_batch_detail(operation_id, entry.uid, "failed", str(e))
                logger.error(f"审核条目失败", entry_uid=entry.uid, error=str(e))
            
            result.processed_count += 1
    
    async def _execute_publication_batch(
        self,
        operation_id: str,
        config: BatchOperationConfig,
        entries: List[CoreTranslationEntry]
    ):
        """执行批量发布"""
        publication_target = config.operation_params.get("publication_target", "production")
        
        result = self.active_operations[operation_id]
        
        for entry in entries:
            try:
                # 检查条目是否可以发布
                if entry.status not in ["approved", "reviewed"]:
                    result.skipped_count += 1
                    await self._record_batch_detail(
                        operation_id, entry.uid, "skipped", 
                        f"状态不符合发布条件: {entry.status}"
                    )
                    continue
                
                success, error_msg = self._process_single_state_change(
                    entry, "published", config.operator_id, config.operator_name,
                    f"批量发布到: {publication_target}"
                )
                
                if success:
                    result.success_count += 1
                    await self._record_batch_detail(operation_id, entry.uid, "success")
                else:
                    result.failed_count += 1
                    await self._record_batch_detail(operation_id, entry.uid, "failed", error_msg)
                
            except Exception as e:
                result.failed_count += 1
                await self._record_batch_detail(operation_id, entry.uid, "failed", str(e))
                logger.error(f"发布条目失败", entry_uid=entry.uid, error=str(e))
            
            result.processed_count += 1
    
    async def _execute_cleanup_batch(
        self,
        operation_id: str,
        config: BatchOperationConfig,
        entries: List[CoreTranslationEntry]
    ):
        """执行批量清理"""
        cleanup_action = config.operation_params.get("cleanup_action", "archive")
        
        result = self.active_operations[operation_id]
        
        for entry in entries:
            try:
                if cleanup_action == "archive":
                    target_state = "archived"
                elif cleanup_action == "reset":
                    target_state = "draft"
                elif cleanup_action == "delete":
                    # 删除条目
                    self.entry_repo.delete_by_uid(entry.uid)
                    result.success_count += 1
                    await self._record_batch_detail(operation_id, entry.uid, "success")
                    result.processed_count += 1
                    continue
                else:
                    raise ValueError(f"不支持的清理动作: {cleanup_action}")
                
                success, error_msg = self._process_single_state_change(
                    entry, target_state, config.operator_id, config.operator_name,
                    f"批量清理: {cleanup_action}"
                )
                
                if success:
                    result.success_count += 1
                    await self._record_batch_detail(operation_id, entry.uid, "success")
                else:
                    result.failed_count += 1
                    await self._record_batch_detail(operation_id, entry.uid, "failed", error_msg)
                
            except Exception as e:
                result.failed_count += 1
                await self._record_batch_detail(operation_id, entry.uid, "failed", str(e))
                logger.error(f"清理条目失败", entry_uid=entry.uid, error=str(e))
            
            result.processed_count += 1
    
    def _process_single_state_change(
        self,
        entry: CoreTranslationEntry,
        target_state: str,
        operator_id: str,
        operator_name: str,
        reason: str
    ) -> tuple[bool, str]:
        """处理单个条目的状态变更"""
        return self.state_service.change_translation_state(
            entry.uid, target_state, operator_id, operator_name, reason
        )
    
    async def _create_batch_operation_record(
        self,
        operation_id: str,
        config: BatchOperationConfig,
        result: BatchOperationResult
    ):
        """创建批量操作记录"""
        query = """
            INSERT INTO translation_batch_operations (
                operation_id, operation_type, operation_name, target_filter,
                operation_params, operator_id, operator_name, total_count, 
                status, started_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """
        
        self.entry_repo.execute_write(query, (
            operation_id, config.operation_type.value, config.operation_name,
            json.dumps(config.target_filter), json.dumps(config.operation_params),
            config.operator_id, config.operator_name, result.total_count,
            result.status.value, result.started_at.isoformat()
        ))
    
    async def _update_batch_operation_record(
        self,
        operation_id: str,
        result: BatchOperationResult
    ):
        """更新批量操作记录"""
        query = """
            UPDATE translation_batch_operations
            SET status = ?, processed_count = ?, success_count = ?, failed_count = ?,
                error_message = ?, completed_at = ?
            WHERE operation_id = ?
        """
        
        self.entry_repo.execute_write(query, (
            result.status.value, result.processed_count, result.success_count,
            result.failed_count, result.error_message,
            result.completed_at.isoformat() if result.completed_at else None,
            operation_id
        ))
    
    async def _record_batch_detail(
        self,
        operation_id: str,
        entry_uid: str,
        status: str,
        error_message: str = None
    ):
        """记录批量操作详情"""
        query = """
            INSERT OR REPLACE INTO translation_batch_operation_details (
                operation_id, entry_uid, status, error_message, processed_at
            ) VALUES (?, ?, ?, ?, datetime('now'))
        """
        
        self.entry_repo.execute_write(query, (
            operation_id, entry_uid, status, error_message
        ))
    
    async def _create_assignment_record(
        self,
        assignment_id: str,
        entry_uid: str,
        assignee_id: str,
        assignee_name: str,
        assigner_id: str,
        assigner_name: str,
        assignment_type: str
    ):
        """创建分配记录"""
        query = """
            INSERT INTO translation_assignments (
                assignment_id, entry_uid, assignee_id, assignee_name,
                assigner_id, assigner_name, assignment_type, status
            ) VALUES (?, ?, ?, ?, ?, ?, ?, 'active')
        """
        
        self.entry_repo.execute_write(query, (
            assignment_id, entry_uid, assignee_id, assignee_name,
            assigner_id, assigner_name, assignment_type
        ))