"""
TH-Suite v2.1 同步服务
基于新的SDK集成和数据分层架构

特性:
- 使用Trans-Hub官方SDK
- 数据分层同步（仅同步业务数据）
- 智能增量同步
- 冲突检测和解决
"""

import asyncio
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Set, Any, Tuple
from dataclasses import dataclass
from enum import Enum

import structlog

from ..clients.transhub_sdk_client import (
    MinecraftTransHubSDKAdapter, 
    TransHubSDKConfig,
    ContentItem,
    IngestionResult,
    SyncStatus,
    TransHubSDKError
)
from ..repositories.v2_1_repositories import (
    RepositoryManager,
    PackRepository,
    PackVersionRepository,
    ContentInstanceRepository
)
from ..models.v2_1_models import (
    Pack, PackVersion, ContentInstance,
    ContentSource, ChangeType
)
from ..models.data_layer_config import DataLayerConfig, DataLayerValidator

logger = structlog.get_logger(__name__)


# ============================================================
# 同步配置和状态
# ============================================================

class SyncDirection(Enum):
    """同步方向"""
    UPLOAD = "upload"      # 本地 → 服务器
    DOWNLOAD = "download"  # 服务器 → 本地
    BIDIRECTIONAL = "bidirectional"  # 双向同步


class SyncStrategy(Enum):
    """同步策略"""
    FULL = "full"          # 全量同步
    INCREMENTAL = "incremental"  # 增量同步
    SMART = "smart"        # 智能同步（自动选择）


@dataclass
class SyncOptions:
    """同步选项"""
    direction: SyncDirection = SyncDirection.BIDIRECTIONAL
    strategy: SyncStrategy = SyncStrategy.SMART
    dry_run: bool = False
    force: bool = False
    batch_size: int = 100
    timeout: float = 300.0
    
    # 过滤选项
    include_languages: Set[str] = None
    exclude_languages: Set[str] = None
    include_content_types: Set[str] = None
    exclude_content_types: Set[str] = None


@dataclass
class SyncResult:
    """同步结果"""
    success: bool
    pack_version_id: int
    direction: SyncDirection
    strategy: SyncStrategy
    
    # 统计信息
    total_items: int = 0
    uploaded_items: int = 0
    downloaded_items: int = 0
    skipped_items: int = 0
    failed_items: int = 0
    
    # 详细信息
    errors: List[str] = None
    warnings: List[str] = None
    conflicts: List[Dict[str, Any]] = None
    
    # 时间信息
    started_at: datetime = None
    completed_at: datetime = None
    
    def __post_init__(self):
        if self.errors is None:
            self.errors = []
        if self.warnings is None:
            self.warnings = []
        if self.conflicts is None:
            self.conflicts = []


# ============================================================
# 同步服务主类
# ============================================================

class SyncService:
    """
    TH-Suite v2.1 同步服务
    
    职责:
    - 协调SDK客户端和数据访问层
    - 实现智能同步策略
    - 处理数据分层和冲突解决
    - 提供实时同步状态
    """
    
    def __init__(self, sdk_config: TransHubSDKConfig, db_path: str):
        self.sdk_config = sdk_config
        self.db_path = db_path
        
        # 组件初始化
        self.sdk_adapter: Optional[MinecraftTransHubSDKAdapter] = None
        self.repo_manager = RepositoryManager(db_path)
        self.pack_repo = self.repo_manager.get_pack_repository()
        self.version_repo = self.repo_manager.get_pack_version_repository()
        self.content_repo = self.repo_manager.get_content_repository()
        
        # 同步状态
        self._active_syncs: Dict[int, SyncResult] = {}
        self._sync_lock = asyncio.Lock()
        
    async def initialize(self) -> bool:
        """初始化同步服务"""
        try:
            # 初始化SDK适配器
            from ..clients.transhub_sdk_client import TransHubSDKFactory
            self.sdk_adapter = await TransHubSDKFactory.create_minecraft_adapter(
                self.sdk_config
            )
            
            logger.info("同步服务初始化成功")
            return True
            
        except Exception as e:
            logger.error(f"同步服务初始化失败: {e}")
            return False
    
    # ============================================================
    # 主要同步方法
    # ============================================================
    
    async def sync_pack_version(
        self,
        pack_version_id: int,
        options: Optional[SyncOptions] = None
    ) -> SyncResult:
        """同步整合包版本"""
        options = options or SyncOptions()
        
        async with self._sync_lock:
            if pack_version_id in self._active_syncs:
                raise ValueError(f"版本 {pack_version_id} 正在同步中")
            
            # 创建同步结果
            sync_result = SyncResult(
                success=False,
                pack_version_id=pack_version_id,
                direction=options.direction,
                strategy=options.strategy,
                started_at=datetime.now()
            )
            
            self._active_syncs[pack_version_id] = sync_result
            
        try:
            # 获取版本信息
            pack_version = await self.version_repo.get_by_id(pack_version_id)
            if not pack_version:
                raise ValueError(f"未找到版本: {pack_version_id}")
            
            pack = await self.pack_repo.get_by_id(pack_version.pack_id)
            if not pack:
                raise ValueError(f"未找到包: {pack_version.pack_id}")
            
            logger.info(f"开始同步: {pack.name} v{pack_version.version_tag}")
            
            # 根据方向执行同步
            if options.direction == SyncDirection.UPLOAD:
                await self._sync_upload(pack, pack_version, options, sync_result)
            elif options.direction == SyncDirection.DOWNLOAD:
                await self._sync_download(pack, pack_version, options, sync_result)
            else:  # BIDIRECTIONAL
                await self._sync_bidirectional(pack, pack_version, options, sync_result)
            
            sync_result.success = len(sync_result.errors) == 0
            sync_result.completed_at = datetime.now()
            
            logger.info(f"同步完成: {pack.name} v{pack_version.version_tag}")
            
        except Exception as e:
            sync_result.errors.append(str(e))
            sync_result.completed_at = datetime.now()
            logger.error(f"同步失败: {e}")
        
        finally:
            # 清理活跃同步状态
            self._active_syncs.pop(pack_version_id, None)
        
        return sync_result
    
    async def _sync_upload(
        self,
        pack: Pack,
        pack_version: PackVersion,
        options: SyncOptions,
        result: SyncResult
    ):
        """执行上传同步"""
        logger.info(f"开始上传同步: {pack.name} v{pack_version.version_tag}")
        
        # 1. 确保服务器端项目存在
        project_info = await self.sdk_adapter.get_project(pack.name)
        if not project_info:
            project_info = await self.sdk_adapter.create_project(
                name=pack.name,
                project_type=pack.project_type.value,
                metadata=pack.get_sync_data('packs')
            )
        
        # 2. 获取需要上传的内容
        content_items = await self._get_local_content_for_sync(
            pack_version.id, options
        )
        
        result.total_items = len(content_items)
        
        if options.dry_run:
            logger.info(f"试运行模式: 将上传 {len(content_items)} 项内容")
            result.uploaded_items = len(content_items)
            return
        
        # 3. 批量上传内容
        uploaded_count = 0
        failed_count = 0
        
        for i in range(0, len(content_items), options.batch_size):
            batch = content_items[i:i + options.batch_size]
            
            try:
                ingest_result = await self.sdk_adapter.ingest_content(
                    project_info.id, batch
                )
                
                uploaded_count += ingest_result.processed_items
                failed_count += ingest_result.failed_items
                
                if ingest_result.errors:
                    result.errors.extend(ingest_result.errors)
                
                logger.info(f"批次上传完成: {ingest_result.processed_items}/{len(batch)}")
                
            except Exception as e:
                failed_count += len(batch)
                result.errors.append(f"批次上传失败: {e}")
                logger.error(f"批次上传失败: {e}")
        
        result.uploaded_items = uploaded_count
        result.failed_items = failed_count
    
    async def _sync_download(
        self,
        pack: Pack,
        pack_version: PackVersion,
        options: SyncOptions,
        result: SyncResult
    ):
        """执行下载同步"""
        logger.info(f"开始下载同步: {pack.name} v{pack_version.version_tag}")
        
        # TODO: 实现下载同步逻辑
        # 1. 从服务器获取翻译内容
        # 2. 与本地内容对比
        # 3. 更新本地数据库
        
        result.warnings.append("下载同步功能开发中")
    
    async def _sync_bidirectional(
        self,
        pack: Pack,
        pack_version: PackVersion,
        options: SyncOptions,
        result: SyncResult
    ):
        """执行双向同步"""
        logger.info(f"开始双向同步: {pack.name} v{pack_version.version_tag}")
        
        # TODO: 实现双向同步逻辑
        # 1. 检测冲突
        # 2. 根据策略解决冲突
        # 3. 执行上传和下载
        
        # 目前先执行上传
        await self._sync_upload(pack, pack_version, options, result)
    
    # ============================================================
    # 辅助方法
    # ============================================================
    
    async def _get_local_content_for_sync(
        self,
        pack_version_id: int,
        options: SyncOptions
    ) -> List[ContentItem]:
        """获取需要同步的本地内容"""
        try:
            # 从数据库获取内容
            content_instances = await self._fetch_content_instances(pack_version_id, options)
            
            # 转换为SDK格式
            sdk_items = []
            for instance in content_instances:
                if self._should_sync_content(instance, options):
                    sdk_item = self._convert_to_sdk_format(instance)
                    sdk_items.append(sdk_item)
            
            logger.info(f"准备同步内容: {len(sdk_items)} 项")
            return sdk_items
            
        except Exception as e:
            logger.error(f"获取同步内容失败: {e}")
            return []
    
    async def _fetch_content_instances(
        self,
        pack_version_id: int,
        options: SyncOptions
    ) -> List[ContentInstance]:
        """从数据库获取内容实例"""
        # TODO: 根据pack_version_id查询相关内容
        # 这需要通过pack_content_relations表关联查询
        
        # 临时返回空列表
        return []
    
    def _should_sync_content(self, instance: ContentInstance, options: SyncOptions) -> bool:
        """判断内容是否应该同步"""
        # 检查语言过滤
        if options.include_languages and instance.language_code not in options.include_languages:
            return False
        
        if options.exclude_languages and instance.language_code in options.exclude_languages:
            return False
        
        # 检查内容类型过滤
        content_type = instance.content_type.value
        if options.include_content_types and content_type not in options.include_content_types:
            return False
        
        if options.exclude_content_types and content_type in options.exclude_content_types:
            return False
        
        # 检查是否为同步数据
        return DataLayerConfig.should_sync_field('content_instances', 'source_text')
    
    def _convert_to_sdk_format(self, instance: ContentInstance) -> ContentItem:
        """将内容实例转换为SDK格式"""
        return ContentItem(
            uida_hash=self._generate_uida_hash(instance),
            uida_uri=f"minecraft://{instance.source_identifier}/{instance.content_key}",
            namespace=instance.source_identifier,
            project_id=instance.source_identifier,  # TODO: 映射到正确的项目ID
            keys=[instance.content_key],
            context={
                "content_source": instance.content_source.value,
                "content_type": instance.content_type.value,
                "category": instance.category,
                "language": instance.language_code
            },
            source_text=instance.source_text,
            target_text=None,  # TODO: 如果有翻译则填充
            metadata={
                "priority": instance.priority,
                "is_override": instance.is_override,
                "comment": instance.comment
            },
            mod_id=instance.source_identifier if instance.content_source == ContentSource.MOD_JAR else None
        )
    
    def _generate_uida_hash(self, instance: ContentInstance) -> str:
        """生成UIDA哈希"""
        import hashlib
        content = f"{instance.source_identifier}:{instance.content_key}:{instance.language_code}"
        return hashlib.sha256(content.encode()).hexdigest()[:16]
    
    # ============================================================
    # 状态查询方法
    # ============================================================
    
    async def get_sync_status(self, pack_version_id: int) -> Optional[SyncResult]:
        """获取同步状态"""
        return self._active_syncs.get(pack_version_id)
    
    async def list_active_syncs(self) -> List[SyncResult]:
        """列出活跃的同步任务"""
        return list(self._active_syncs.values())
    
    async def cancel_sync(self, pack_version_id: int) -> bool:
        """取消同步任务"""
        if pack_version_id in self._active_syncs:
            # TODO: 实现同步取消逻辑
            sync_result = self._active_syncs[pack_version_id]
            sync_result.errors.append("同步被用户取消")
            sync_result.completed_at = datetime.now()
            return True
        return False
    
    # ============================================================
    # 配置管理
    # ============================================================
    
    async def update_sync_config(self, pack_id: int, config: Dict[str, Any]) -> bool:
        """更新同步配置"""
        try:
            # 验证配置
            validated_config = self._validate_sync_config(config)
            
            # 更新数据库中的同步配置
            success = await self.pack_repo.update(pack_id, {
                "sync_config": validated_config
            })
            
            logger.info(f"同步配置更新: Pack {pack_id}")
            return success
            
        except Exception as e:
            logger.error(f"更新同步配置失败: {e}")
            return False
    
    def _validate_sync_config(self, config: Dict[str, Any]) -> Dict[str, Any]:
        """验证同步配置"""
        # TODO: 实现配置验证逻辑
        return config
    
    # ============================================================
    # 清理方法
    # ============================================================
    
    async def close(self):
        """关闭同步服务"""
        try:
            # 等待活跃同步完成或取消
            for pack_version_id in list(self._active_syncs.keys()):
                await self.cancel_sync(pack_version_id)
            
            # 关闭SDK适配器
            if self.sdk_adapter:
                await self.sdk_adapter.close()
            
            # 关闭数据库连接
            await self.repo_manager.close_all()
            
            logger.info("同步服务已关闭")
            
        except Exception as e:
            logger.warning(f"关闭同步服务时出错: {e}")


# ============================================================
# 同步工具类
# ============================================================

class SyncUtilities:
    """同步工具类"""
    
    @staticmethod
    def create_default_options(
        direction: SyncDirection = SyncDirection.BIDIRECTIONAL,
        languages: Optional[List[str]] = None
    ) -> SyncOptions:
        """创建默认同步选项"""
        options = SyncOptions(direction=direction)
        
        if languages:
            options.include_languages = set(languages)
        
        return options
    
    @staticmethod
    def estimate_sync_time(content_count: int, avg_item_time: float = 0.1) -> float:
        """估算同步时间（秒）"""
        return content_count * avg_item_time
    
    @staticmethod
    def format_sync_summary(result: SyncResult) -> str:
        """格式化同步摘要"""
        duration = "未知"
        if result.started_at and result.completed_at:
            delta = result.completed_at - result.started_at
            duration = f"{delta.total_seconds():.1f}秒"
        
        return f"""
同步摘要:
- 状态: {'成功' if result.success else '失败'}
- 方向: {result.direction.value}
- 策略: {result.strategy.value}
- 总项目: {result.total_items}
- 上传: {result.uploaded_items}
- 下载: {result.downloaded_items}
- 跳过: {result.skipped_items}
- 失败: {result.failed_items}
- 耗时: {duration}
- 错误: {len(result.errors)}
- 警告: {len(result.warnings)}
        """.strip()