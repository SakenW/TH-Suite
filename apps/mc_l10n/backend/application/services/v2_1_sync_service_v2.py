#!/usr/bin/env python3
"""
TH-Suite v2.1 同步服务 - 基于最新Trans-Hub SDK
完全重构的同步服务，使用官方SDK实现更高效的数据同步

主要特性:
- 集成最新Trans-Hub官方SDK
- 支持双向同步（推送和拉取）
- 批量处理和进度跟踪
- 智能冲突解决
- 实时状态监控
"""

import asyncio
import uuid
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, AsyncIterator
from enum import Enum
from dataclasses import dataclass, field

import structlog

# 导入TH-Suite模块
from clients.transhub_sdk_client_v2 import (
    TH_Suite_TransHub_SDK_Client,
    MinecraftContentItem,
    SyncOptions,
    SyncProgress,
    create_th_suite_sdk_client
)
from models.v2_1_models import (
    Pack, PackVersion, ModVersionInstance, 
    ContentInstance, PackContentRelation,
    ContentSource, ChangeType
)
from repositories.v2_1_repositories import (
    PackRepository, PackVersionRepository,
    ContentInstanceRepository, PackContentRelationRepository
)

# 导入统一内容映射器
from mappers.unified_content_mapper import UnifiedContentMapper

logger = structlog.get_logger(__name__)


# ============================================================
# 同步服务枚举和数据类
# ============================================================

class SyncStatus(Enum):
    """同步状态枚举"""
    IDLE = "idle"
    PREPARING = "preparing"
    PUSHING = "pushing"
    PULLING = "pulling"
    PROCESSING = "processing"
    COMPLETING = "completing"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class SyncDirection(Enum):
    """同步方向枚举"""
    PUSH_ONLY = "push"        # 仅推送到Trans-Hub
    PULL_ONLY = "pull"        # 仅从Trans-Hub拉取
    BIDIRECTIONAL = "bidirectional"  # 双向同步


@dataclass
class SyncTask:
    """同步任务"""
    task_id: str
    status: SyncStatus
    direction: SyncDirection
    created_at: datetime
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    
    # 进度信息
    total_items: int = 0
    processed_items: int = 0
    success_items: int = 0
    failed_items: int = 0
    
    # 配置选项
    options: Optional[SyncOptions] = None
    
    # 结果和错误
    errors: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    result_summary: Dict[str, Any] = field(default_factory=dict)


@dataclass
class SyncConfiguration:
    """同步配置"""
    
    # Trans-Hub连接配置
    base_url: str = "http://localhost:8000"
    api_key: Optional[str] = None
    project_id: str = "minecraft"
    
    # 同步策略
    default_direction: SyncDirection = SyncDirection.BIDIRECTIONAL
    batch_size: int = 100
    max_concurrent_tasks: int = 3
    
    # 过滤配置
    enabled_languages: List[str] = field(default_factory=lambda: ["en_us", "zh_cn"])
    enabled_content_sources: List[str] = field(default_factory=lambda: ["mod_jar", "pack_resource", "quest_pack"])
    
    # 冲突解决
    conflict_resolution: str = "latest_wins"
    auto_resolve_conflicts: bool = True
    
    # 性能配置
    enable_caching: bool = True
    cache_ttl: int = 300  # 秒
    retry_attempts: int = 3
    retry_delay: int = 5  # 秒


# ============================================================
# 主要同步服务类
# ============================================================

class V2_1_SyncService:
    """TH-Suite v2.1 同步服务"""
    
    def __init__(self, config: Optional[SyncConfiguration] = None):
        """
        初始化同步服务
        
        Args:
            config: 同步配置，如果不提供则使用默认配置
        """
        self.config = config or SyncConfiguration()
        
        # 任务管理
        self.active_tasks: Dict[str, SyncTask] = {}
        self.task_history: List[SyncTask] = []
        
        # 组件初始化
        self._init_repositories()
        self._init_mappers()
        
        logger.info("TH-Suite v2.1 同步服务初始化完成",
                   config=self.config.__dict__)
    
    def _init_repositories(self):
        """初始化数据访问组件"""
        try:
            self.pack_repo = PackRepository()
            self.pack_version_repo = PackVersionRepository()
            self.content_repo = ContentInstanceRepository()
            self.content_relation_repo = PackContentRelationRepository()
            
            logger.info("数据访问组件初始化完成")
        except Exception as e:
            logger.error("数据访问组件初始化失败", error=str(e))
            raise
    
    def _init_mappers(self):
        """初始化映射器组件"""
        try:
            # 假设映射规则配置文件位于config目录
            from pathlib import Path
            config_path = Path(__file__).parent.parent.parent / "config" / "mapping_rules.yaml"
            
            if config_path.exists():
                self.content_mapper = UnifiedContentMapper(str(config_path))
                logger.info("统一内容映射器初始化完成")
            else:
                logger.warning("映射规则配置文件不存在，使用默认映射器")
                self.content_mapper = None
                
        except Exception as e:
            logger.error("映射器初始化失败", error=str(e))
            self.content_mapper = None
    
    # ============================================================
    # 任务管理功能
    # ============================================================
    
    def create_sync_task(
        self,
        direction: SyncDirection = None,
        options: Optional[SyncOptions] = None
    ) -> str:
        """创建同步任务"""
        
        task_id = str(uuid.uuid4())
        task = SyncTask(
            task_id=task_id,
            status=SyncStatus.IDLE,
            direction=direction or self.config.default_direction,
            created_at=datetime.now(),
            options=options
        )
        
        self.active_tasks[task_id] = task
        
        logger.info("创建同步任务", task_id=task_id, direction=direction)
        return task_id
    
    async def start_sync_task(self, task_id: str) -> bool:
        """启动同步任务"""
        
        if task_id not in self.active_tasks:
            logger.error("同步任务不存在", task_id=task_id)
            return False
        
        task = self.active_tasks[task_id]
        
        if task.status != SyncStatus.IDLE:
            logger.error("同步任务状态不正确", task_id=task_id, status=task.status)
            return False
        
        # 检查并发任务限制
        active_count = sum(1 for t in self.active_tasks.values() 
                          if t.status not in [SyncStatus.IDLE, SyncStatus.COMPLETED, SyncStatus.FAILED])
        
        if active_count >= self.config.max_concurrent_tasks:
            logger.error("达到最大并发任务限制", 
                        active_count=active_count, 
                        max_tasks=self.config.max_concurrent_tasks)
            return False
        
        # 异步执行任务
        task.status = SyncStatus.PREPARING
        task.started_at = datetime.now()
        
        asyncio.create_task(self._execute_sync_task(task_id))
        
        logger.info("启动同步任务", task_id=task_id)
        return True
    
    async def _execute_sync_task(self, task_id: str):
        """执行同步任务"""
        
        task = self.active_tasks[task_id]
        
        try:
            logger.info("开始执行同步任务", task_id=task_id, direction=task.direction)
            
            # 创建SDK客户端
            async with create_th_suite_sdk_client(
                base_url=self.config.base_url,
                api_key=self.config.api_key,
                project_id=self.config.project_id
            ) as sdk_client:
                
                # 根据方向执行不同的同步操作
                if task.direction in [SyncDirection.PUSH_ONLY, SyncDirection.BIDIRECTIONAL]:
                    await self._execute_push_sync(task, sdk_client)
                
                if task.direction in [SyncDirection.PULL_ONLY, SyncDirection.BIDIRECTIONAL]:
                    await self._execute_pull_sync(task, sdk_client)
                
                # 完成任务
                task.status = SyncStatus.COMPLETED
                task.completed_at = datetime.now()
                
                logger.info("同步任务完成", 
                           task_id=task_id,
                           success_items=task.success_items,
                           failed_items=task.failed_items)
        
        except Exception as e:
            task.status = SyncStatus.FAILED
            task.errors.append(str(e))
            logger.error("同步任务失败", task_id=task_id, error=str(e))
        
        finally:
            # 移到历史记录
            self.task_history.append(task)
            if len(self.task_history) > 100:  # 保留最近100个任务
                self.task_history = self.task_history[-100:]
    
    async def _execute_push_sync(self, task: SyncTask, sdk_client: TH_Suite_TransHub_SDK_Client):
        """执行推送同步"""
        
        task.status = SyncStatus.PUSHING
        logger.info("开始推送同步", task_id=task.task_id)
        
        try:
            # 1. 从本地数据库获取内容
            local_content = await self._get_local_content_for_sync(task.options)
            task.total_items += len(local_content)
            
            logger.info("获取本地内容", content_count=len(local_content))
            
            # 2. 转换为Minecraft内容项
            minecraft_items = await self._convert_to_minecraft_content(local_content)
            
            # 3. 批量推送到Trans-Hub
            if minecraft_items:
                result = await sdk_client.ingest_minecraft_content(
                    minecraft_items, 
                    task.options
                )
                
                task.success_items += result.processed_count
                task.failed_items += result.failed_count
                task.processed_items += result.processed_count + result.failed_count
                
                if result.errors:
                    task.errors.extend(result.errors[:10])  # 记录前10个错误
            
            logger.info("推送同步完成",
                       success=task.success_items,
                       failed=task.failed_items)
        
        except Exception as e:
            task.errors.append(f"推送同步失败: {str(e)}")
            raise
    
    async def _execute_pull_sync(self, task: SyncTask, sdk_client: TH_Suite_TransHub_SDK_Client):
        """执行拉取同步"""
        
        task.status = SyncStatus.PULLING
        logger.info("开始拉取同步", task_id=task.task_id)
        
        try:
            # 获取支持的语言列表
            languages = self.config.enabled_languages
            
            for language in languages:
                logger.info("拉取语言翻译", language=language)
                
                # 流式获取翻译
                translation_count = 0
                async for translation in sdk_client.export_translations_stream(
                    target_language=language,
                    content_filters={
                        "minecraft_version": "1.20.1",  # 可配置
                        "status": ["published", "draft"]
                    }
                ):
                    # 处理翻译条目
                    await self._process_translation_entry(translation, language)
                    translation_count += 1
                    task.processed_items += 1
                    
                    # 更新进度
                    if translation_count % 100 == 0:
                        logger.info("翻译处理进度", 
                                   language=language, 
                                   count=translation_count)
                
                task.success_items += translation_count
                logger.info("语言翻译拉取完成", 
                           language=language, 
                           count=translation_count)
            
            logger.info("拉取同步完成", total_translations=task.success_items)
        
        except Exception as e:
            task.errors.append(f"拉取同步失败: {str(e)}")
            raise
    
    # ============================================================
    # 数据转换和处理功能
    # ============================================================
    
    async def _get_local_content_for_sync(self, options: Optional[SyncOptions] = None) -> List[ContentInstance]:
        """获取本地内容用于同步"""
        
        try:
            # 这里需要实现从本地数据库获取内容的逻辑
            # 暂时返回模拟数据
            mock_content = []
            
            # 实际实现应该使用Repository查询数据库
            # async with self.content_repo as repo:
            #     content = await repo.get_content_for_sync(options)
            
            logger.info("获取本地内容完成", count=len(mock_content))
            return mock_content
            
        except Exception as e:
            logger.error("获取本地内容失败", error=str(e))
            return []
    
    async def _convert_to_minecraft_content(
        self, 
        content_instances: List[ContentInstance]
    ) -> List[MinecraftContentItem]:
        """将内容实例转换为Minecraft内容项"""
        
        minecraft_items = []
        
        for content in content_instances:
            try:
                # 构建Minecraft内容项
                item = MinecraftContentItem(
                    content_key=content.content_key,
                    source_text=content.source_text,
                    language_code=content.language_code,
                    content_type=content.content_type,
                    content_source=content.content_source.value if isinstance(content.content_source, ContentSource) else content.content_source,
                    context=getattr(content, 'context', None),
                    metadata=getattr(content, 'metadata', {})
                )
                
                # 如果有映射器，生成UIDA
                if self.content_mapper:
                    item.uida = self.content_mapper.generate_content_uida(
                        namespace=item.mod_id or "unknown",
                        content_key=item.content_key,
                        language=item.language_code,
                        version=item.mod_version or "1.0.0"
                    )
                
                minecraft_items.append(item)
                
            except Exception as e:
                logger.error("内容转换失败", 
                           content_id=getattr(content, 'id', 'unknown'), 
                           error=str(e))
        
        return minecraft_items
    
    async def _process_translation_entry(self, translation, language: str):
        """处理翻译条目"""
        
        try:
            # 这里需要实现将翻译保存到本地数据库的逻辑
            # 实际实现应该：
            # 1. 解析翻译键，确定对应的内容实例
            # 2. 更新或创建本地翻译记录
            # 3. 处理冲突（如果本地也有修改）
            
            logger.debug("处理翻译条目",
                        source_text=translation.source_text,
                        target_text=translation.target_text,
                        language=language)
        
        except Exception as e:
            logger.error("翻译条目处理失败", error=str(e))
    
    # ============================================================
    # 状态查询功能
    # ============================================================
    
    def get_task_status(self, task_id: str) -> Optional[SyncProgress]:
        """获取任务状态"""
        
        if task_id in self.active_tasks:
            task = self.active_tasks[task_id]
        else:
            # 从历史记录中查找
            task = next((t for t in self.task_history if t.task_id == task_id), None)
        
        if not task:
            return None
        
        # 计算进度百分比
        progress_percentage = 0
        if task.total_items > 0:
            progress_percentage = (task.processed_items / task.total_items) * 100
        
        # 估算完成时间
        estimated_completion = None
        if task.started_at and task.processed_items > 0 and task.total_items > task.processed_items:
            elapsed = datetime.now() - task.started_at
            remaining_items = task.total_items - task.processed_items
            items_per_second = task.processed_items / elapsed.total_seconds()
            if items_per_second > 0:
                remaining_seconds = remaining_items / items_per_second
                estimated_completion = datetime.now() + timedelta(seconds=remaining_seconds)
        
        return SyncProgress(
            sync_id=task.task_id,
            status=task.status.value,
            total_items=task.total_items,
            processed_items=task.processed_items,
            success_items=task.success_items,
            failed_items=task.failed_items,
            start_time=task.started_at,
            current_time=datetime.now(),
            estimated_completion=estimated_completion,
            current_operation=f"执行{task.direction.value}同步",
            errors=task.errors,
            warnings=task.warnings
        )
    
    def get_all_task_statuses(self) -> List[SyncProgress]:
        """获取所有任务状态"""
        
        statuses = []
        
        # 活动任务
        for task_id in self.active_tasks:
            status = self.get_task_status(task_id)
            if status:
                statuses.append(status)
        
        # 最近的历史任务
        for task in self.task_history[-10:]:
            status = self.get_task_status(task.task_id)
            if status:
                statuses.append(status)
        
        return statuses
    
    def cancel_task(self, task_id: str) -> bool:
        """取消同步任务"""
        
        if task_id not in self.active_tasks:
            return False
        
        task = self.active_tasks[task_id]
        
        if task.status in [SyncStatus.COMPLETED, SyncStatus.FAILED, SyncStatus.CANCELLED]:
            return False
        
        task.status = SyncStatus.CANCELLED
        task.completed_at = datetime.now()
        
        logger.info("同步任务已取消", task_id=task_id)
        return True
    
    # ============================================================
    # 便捷方法
    # ============================================================
    
    async def quick_push_sync(
        self, 
        content_filters: Optional[Dict[str, Any]] = None
    ) -> str:
        """快速推送同步"""
        
        options = SyncOptions(
            sync_type="push",
            content_type_filters=content_filters.get("content_types", []) if content_filters else [],
            pack_filters=content_filters.get("pack_names", []) if content_filters else []
        )
        
        task_id = self.create_sync_task(SyncDirection.PUSH_ONLY, options)
        await self.start_sync_task(task_id)
        
        return task_id
    
    async def quick_pull_sync(
        self,
        target_languages: Optional[List[str]] = None
    ) -> str:
        """快速拉取同步"""
        
        languages = target_languages or self.config.enabled_languages
        options = SyncOptions(
            sync_type="pull",
            language_filters=languages
        )
        
        task_id = self.create_sync_task(SyncDirection.PULL_ONLY, options)
        await self.start_sync_task(task_id)
        
        return task_id
    
    async def quick_bidirectional_sync(self) -> str:
        """快速双向同步"""
        
        task_id = self.create_sync_task(SyncDirection.BIDIRECTIONAL)
        await self.start_sync_task(task_id)
        
        return task_id


# ============================================================
# 服务工厂方法
# ============================================================

def create_sync_service(config: Optional[SyncConfiguration] = None) -> V2_1_SyncService:
    """创建同步服务实例"""
    return V2_1_SyncService(config)


# ============================================================
# 兼容性别名
# ============================================================

# 保持与原有代码的兼容性
SyncService = V2_1_SyncService