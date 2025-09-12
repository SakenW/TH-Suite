#!/usr/bin/env python3
"""
TH-Suite Trans-Hub SDK 集成客户端 v2.0
基于最新的Trans-Hub官方SDK进行完整重构

主要改进:
- 使用官方SDK替代自定义HTTP客户端
- 支持项目管理、内容摄入、翻译导出
- Minecraft专用辅助功能
- 异步操作和错误处理
- 实时进度跟踪
"""

import asyncio
import os
from datetime import datetime
from typing import Any, Dict, List, Optional, AsyncIterator
from pathlib import Path

import structlog
from pydantic import BaseModel, Field

# 导入Trans-Hub官方SDK
try:
    from trans_hub_sdk import (
        TransHubClient,
        ContentItem,
        BatchIngestionRequest,
        CreateProjectRequest,
        ProjectInfo,
        IngestionResult,
        TranslationEntry,
        ContentExportRequest,
        TransHubError,
        AuthenticationError,
        NetworkError,
    )
    from trans_hub_sdk.helpers import (
        create_client_from_env,
        create_minecraft_project,
        MinecraftContentBuilder,
    )
    SDK_AVAILABLE = True
except ImportError as e:
    structlog.get_logger(__name__).warning(f"Trans-Hub SDK不可用: {e}")
    SDK_AVAILABLE = False
    
    # 当SDK不可用时的占位符类型
    class TransHubClient: pass
    class ContentItem: pass
    class BatchIngestionRequest: pass
    class CreateProjectRequest: pass
    class ProjectInfo: pass
    class IngestionResult: pass
    class TranslationEntry: pass
    class ContentExportRequest: pass
    class TransHubError(Exception): pass
    class AuthenticationError(TransHubError): pass
    class NetworkError(TransHubError): pass
    class MinecraftContentBuilder: pass

logger = structlog.get_logger(__name__)


# ============================================================
# TH-Suite专用模型定义
# ============================================================

class MinecraftContentItem(BaseModel):
    """Minecraft内容项模型"""
    
    content_key: str = Field(..., description="内容键，如 'item.diamond_sword'")
    source_text: str = Field(..., description="源文本")
    language_code: str = Field(default="en_us", description="语言代码")
    
    # Minecraft特有字段
    mod_id: Optional[str] = Field(None, description="MOD ID")
    mod_version: Optional[str] = Field(None, description="MOD版本")
    mod_name: Optional[str] = Field(None, description="MOD名称")
    
    # 整合包信息
    pack_name: Optional[str] = Field(None, description="整合包名称")
    pack_version: Optional[str] = Field(None, description="整合包版本")
    minecraft_version: Optional[str] = Field(None, description="Minecraft版本")
    loader_type: Optional[str] = Field(None, description="MOD加载器类型")
    
    # 内容分类
    content_type: str = Field(default="mod_jar", description="内容类型")
    content_source: str = Field(default="mod_jar", description="内容来源")
    category: Optional[str] = Field(None, description="内容分类")
    
    # 翻译上下文
    context: Optional[str] = Field(None, description="翻译上下文")
    comment: Optional[str] = Field(None, description="备注信息")
    
    # 元数据
    metadata: Dict[str, Any] = Field(default_factory=dict, description="附加元数据")
    
    # 生成的UIDA
    uida: Optional[str] = Field(None, description="统一内容标识符")


class SyncOptions(BaseModel):
    """同步选项配置"""
    
    # 同步策略
    sync_type: str = Field(default="bidirectional", description="同步类型: push, pull, bidirectional")
    batch_size: int = Field(default=100, description="批量处理大小")
    max_workers: int = Field(default=4, description="最大并发数")
    
    # 过滤条件
    language_filters: List[str] = Field(default_factory=list, description="语言过滤")
    content_type_filters: List[str] = Field(default_factory=list, description="内容类型过滤")
    pack_filters: List[str] = Field(default_factory=list, description="整合包过滤")
    
    # 冲突处理
    conflict_resolution: str = Field(default="latest_wins", description="冲突解决策略")
    merge_strategy: str = Field(default="upsert", description="合并策略")
    
    # 验证选项
    validate_keys: bool = Field(default=True, description="验证内容键")
    skip_duplicates: bool = Field(default=True, description="跳过重复项")


class SyncProgress(BaseModel):
    """同步进度信息"""
    
    sync_id: str = Field(..., description="同步任务ID")
    status: str = Field(..., description="同步状态")
    
    # 进度统计
    total_items: int = Field(default=0, description="总项数")
    processed_items: int = Field(default=0, description="已处理项数")
    success_items: int = Field(default=0, description="成功项数")
    failed_items: int = Field(default=0, description="失败项数")
    
    # 时间信息
    start_time: Optional[datetime] = Field(None, description="开始时间")
    current_time: Optional[datetime] = Field(None, description="当前时间")
    estimated_completion: Optional[datetime] = Field(None, description="预计完成时间")
    
    # 详细信息
    current_operation: Optional[str] = Field(None, description="当前操作")
    errors: List[str] = Field(default_factory=list, description="错误信息")
    warnings: List[str] = Field(default_factory=list, description="警告信息")


# ============================================================
# 主要客户端适配器类
# ============================================================

class TH_Suite_TransHub_SDK_Client:
    """TH-Suite Trans-Hub SDK客户端"""
    
    def __init__(
        self,
        base_url: Optional[str] = None,
        api_key: Optional[str] = None,
        project_id: str = "minecraft",
        **kwargs
    ):
        """
        初始化SDK客户端
        
        Args:
            base_url: Trans-Hub API 基础URL
            api_key: API密钥
            project_id: 默认项目ID
            **kwargs: 其他配置选项
        """
        if not SDK_AVAILABLE:
            raise ImportError("Trans-Hub SDK 不可用，请检查安装")
        
        self.project_id = project_id
        self.base_url = base_url or os.getenv("TRANSHUB_BASE_URL", "http://localhost:8000")
        self.api_key = api_key or os.getenv("TRANSHUB_API_KEY")
        
        # 创建官方SDK客户端
        try:
            if self.api_key:
                self.client = TransHubClient(
                    base_url=self.base_url,
                    api_key=self.api_key,
                    **kwargs
                )
            else:
                # 尝试从环境变量创建
                self.client = create_client_from_env()
            
            logger.info("Trans-Hub SDK客户端初始化成功", 
                       base_url=self.base_url, project_id=self.project_id)
                       
        except Exception as e:
            logger.error("Trans-Hub SDK客户端初始化失败", error=str(e))
            raise
    
    async def __aenter__(self):
        """异步上下文管理器入口"""
        await self.client.__aenter__()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """异步上下文管理器出口"""
        await self.client.__aexit__(exc_type, exc_val, exc_tb)
    
    # ============================================================
    # 项目管理功能
    # ============================================================
    
    async def ensure_minecraft_project(self) -> Optional["ProjectInfo"]:
        """确保Minecraft项目存在"""
        try:
            # 尝试获取现有项目
            project = await self.client.get_project(self.project_id)
            if project:
                logger.info("找到现有Minecraft项目", project_id=self.project_id)
                return project
        except Exception:
            logger.info("项目不存在，将创建新项目")
        
        # 创建新的Minecraft项目
        project_request = create_minecraft_project(
            project_id=self.project_id,
            display_name="TH-Suite Minecraft项目",
            description="由TH-Suite管理的Minecraft本地化项目",
        )
        
        project = await self.client.create_or_update_project(project_request)
        logger.info("创建Minecraft项目成功", project_id=project.project_id)
        return project
    
    async def get_project_info(self) -> Optional[ProjectInfo]:
        """获取项目信息"""
        try:
            return await self.client.get_project(self.project_id)
        except Exception as e:
            logger.error("获取项目信息失败", project_id=self.project_id, error=str(e))
            return None
    
    # ============================================================
    # 内容摄入功能
    # ============================================================
    
    async def ingest_minecraft_content(
        self,
        content_items: List[MinecraftContentItem],
        options: Optional[SyncOptions] = None
    ) -> Optional["IngestionResult"]:
        """摄入Minecraft内容到Trans-Hub"""
        
        if not content_items:
            logger.warning("没有内容需要摄入")
            return IngestionResult(processed_count=0, failed_count=0, processing_time_ms=0)
        
        # 确保项目存在
        await self.ensure_minecraft_project()
        
        # 转换为SDK格式
        builder = MinecraftContentBuilder(project_id=self.project_id)
        
        for item in content_items:
            # 根据内容类型添加到构建器
            if item.content_source == "mod_jar":
                builder.add_mod_content(
                    content_key=item.content_key,
                    source_text=item.source_text,
                    mod_id=item.mod_id or "unknown",
                    mod_version=item.mod_version or "1.0.0",
                    pack_name=item.pack_name or "default",
                    pack_version=item.pack_version or "1.0.0",
                    minecraft_version=item.minecraft_version or "1.20.1",
                    loader_type=item.loader_type or "forge",
                    context=item.context,
                    metadata=item.metadata
                )
            elif item.content_source == "pack_resource":
                builder.add_pack_resource(
                    content_key=item.content_key,
                    source_text=item.source_text,
                    pack_name=item.pack_name or "default",
                    pack_version=item.pack_version or "1.0.0",
                    minecraft_version=item.minecraft_version or "1.20.1",
                    context=item.context,
                    metadata=item.metadata
                )
            elif item.content_source == "quest_pack":
                builder.add_quest_content(
                    content_key=item.content_key,
                    source_text=item.source_text,
                    pack_name=item.pack_name or "default",
                    pack_version=item.pack_version or "1.0.0",
                    minecraft_version=item.minecraft_version or "1.20.1",
                    quest_type=item.metadata.get("quest_type", "general"),
                    context=item.context,
                    metadata=item.metadata
                )
        
        # 构建内容项
        sdk_content_items = builder.build()
        
        # 创建批量摄入请求
        ingestion_request = BatchIngestionRequest(
            project_id=self.project_id,
            items=sdk_content_items,
            batch_options={
                "merge_strategy": options.merge_strategy if options else "upsert",
                "validate_keys": options.validate_keys if options else True,
                "skip_duplicates": options.skip_duplicates if options else True,
            }
        )
        
        try:
            result = await self.client.ingest_content_batch(ingestion_request)
            logger.info("内容摄入完成",
                       processed=result.processed_count,
                       failed=result.failed_count,
                       time_ms=result.processing_time_ms)
            return result
            
        except Exception as e:
            logger.error("内容摄入失败", error=str(e))
            raise
    
    # ============================================================
    # 翻译导出功能
    # ============================================================
    
    async def export_translations(
        self,
        target_language: str = "zh_cn",
        content_filters: Optional[Dict[str, Any]] = None,
        status_filter: Optional[List[str]] = None
    ) -> List[TranslationEntry]:
        """导出翻译内容"""
        
        try:
            # 设置默认过滤器
            metadata_filters = content_filters or {}
            status_list = status_filter or ["published", "draft"]
            
            # 导出翻译
            translations = await self.client.export_content(
                project_id=self.project_id,
                target_language=target_language,
                status_filter=status_list,
                metadata_filters=metadata_filters
            )
            
            logger.info("翻译导出完成",
                       language=target_language,
                       count=len(translations))
            return translations
            
        except Exception as e:
            logger.error("翻译导出失败", 
                        language=target_language, 
                        error=str(e))
            raise
    
    async def export_translations_stream(
        self,
        target_language: str = "zh_cn",
        content_filters: Optional[Dict[str, Any]] = None,
        status_filter: Optional[List[str]] = None
    ) -> AsyncIterator[TranslationEntry]:
        """流式导出翻译内容"""
        
        try:
            metadata_filters = content_filters or {}
            status_list = status_filter or ["published", "draft"]
            
            async for translation in self.client.export_content_stream(
                project_id=self.project_id,
                target_language=target_language,
                status_filter=status_list,
                metadata_filters=metadata_filters
            ):
                yield translation
                
        except Exception as e:
            logger.error("流式翻译导出失败",
                        language=target_language,
                        error=str(e))
            raise
    
    # ============================================================
    # 同步管理功能
    # ============================================================
    
    async def start_sync_task(
        self,
        content_items: List[MinecraftContentItem],
        options: Optional[SyncOptions] = None
    ) -> str:
        """启动同步任务"""
        
        sync_id = f"sync_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        
        # 异步执行同步任务
        asyncio.create_task(self._execute_sync_task(sync_id, content_items, options))
        
        logger.info("同步任务已启动", sync_id=sync_id)
        return sync_id
    
    async def _execute_sync_task(
        self,
        sync_id: str,
        content_items: List[MinecraftContentItem],
        options: Optional[SyncOptions] = None
    ):
        """执行同步任务"""
        
        try:
            logger.info("开始执行同步任务", sync_id=sync_id)
            
            # 根据同步类型执行不同操作
            sync_type = options.sync_type if options else "bidirectional"
            
            if sync_type in ["push", "bidirectional"]:
                # 推送本地内容到Trans-Hub
                await self.ingest_minecraft_content(content_items, options)
            
            if sync_type in ["pull", "bidirectional"]:
                # 从Trans-Hub拉取翻译
                await self.export_translations()
            
            logger.info("同步任务完成", sync_id=sync_id)
            
        except Exception as e:
            logger.error("同步任务失败", sync_id=sync_id, error=str(e))
    
    # ============================================================
    # 健康检查和工具功能
    # ============================================================
    
    async def health_check(self) -> Dict[str, Any]:
        """健康检查"""
        try:
            return await self.client.health_check()
        except Exception as e:
            logger.error("健康检查失败", error=str(e))
            return {"status": "error", "message": str(e)}
    
    async def get_supported_languages(self) -> List[str]:
        """获取支持的语言列表"""
        try:
            info = await self.get_project_info()
            if info and hasattr(info, 'supported_languages'):
                return info.supported_languages
            return ["en_us", "zh_cn", "ja_jp", "ko_kr"]  # 默认支持的语言
        except Exception:
            return ["en_us", "zh_cn"]
    
    def convert_to_minecraft_format(
        self, 
        translations: List[TranslationEntry],
        format_type: str = "json"
    ) -> Dict[str, Any]:
        """将翻译转换为Minecraft格式"""
        
        result = {}
        
        for translation in translations:
            for key in translation.keys:
                # 根据格式类型转换
                if format_type == "json":
                    result[key] = translation.target_text
                elif format_type == "properties":
                    # Properties格式需要转义特殊字符
                    escaped_text = translation.target_text.replace("=", "\\=").replace(":", "\\:")
                    result[key] = escaped_text
                else:
                    result[key] = translation.target_text
        
        return result


# ============================================================
# 便捷函数和工厂方法
# ============================================================

def create_th_suite_sdk_client(
    base_url: Optional[str] = None,
    api_key: Optional[str] = None,
    project_id: str = "minecraft"
) -> TH_Suite_TransHub_SDK_Client:
    """创建TH-Suite SDK客户端"""
    return TH_Suite_TransHub_SDK_Client(
        base_url=base_url,
        api_key=api_key,
        project_id=project_id
    )


async def quick_sync_minecraft_content(
    content_items: List[MinecraftContentItem],
    target_language: str = "zh_cn",
    base_url: Optional[str] = None,
    api_key: Optional[str] = None
) -> List[TranslationEntry]:
    """快速同步Minecraft内容并获取翻译"""
    
    async with create_th_suite_sdk_client(base_url, api_key) as client:
        # 摄入内容
        await client.ingest_minecraft_content(content_items)
        
        # 导出翻译
        translations = await client.export_translations(target_language)
        
        return translations


# ============================================================
# 兼容性接口 (保持与原有代码的兼容)
# ============================================================

# 为了向后兼容，保留原有的类名
MinecraftTransHubSDKAdapter = TH_Suite_TransHub_SDK_Client