"""
同步服务 - 协调本地和 Trans-Hub 的数据同步

管理上传、下载、增量同步等操作
"""

import logging
import asyncio
from typing import Dict, List, Optional, Tuple, Set
from datetime import datetime, timedelta
from pathlib import Path
import json

from sqlalchemy.orm import Session

from .transhub_client import TransHubClient
from ..models import Container, LanguageFile, Blob, PatchSet, PatchItem, PatchPolicy
from ..services.blob_service import BlobService
from ..services.patch_service import PatchService
from ..quality.gate import QualityGate

logger = logging.getLogger(__name__)


class SyncService:
    """
    同步服务
    
    功能：
    1. 内容上传：将本地扫描结果上传到 Trans-Hub
    2. 补丁下载：从 Trans-Hub 下载翻译补丁
    3. 增量同步：只同步变化的内容
    4. 冲突处理：处理本地和远程的冲突
    """
    
    def __init__(
        self,
        session: Session,
        transhub_client: Optional[TransHubClient] = None,
        base_url: str = "http://localhost:8000",
        api_key: Optional[str] = None
    ):
        """
        初始化同步服务
        
        Args:
            session: 数据库会话
            transhub_client: Trans-Hub 客户端（可选）
            base_url: Trans-Hub API URL
            api_key: API 密钥
        """
        self.session = session
        self.blob_service = BlobService(session)
        self.patch_service = PatchService(session)
        self.quality_gate = QualityGate(session)
        
        # Trans-Hub 客户端
        self.client = transhub_client or TransHubClient(base_url, api_key)
        
        # 同步状态
        self.sync_status: Dict[str, Any] = {}
        self.last_sync: Optional[datetime] = None
    
    async def sync_project(
        self,
        project_id: str,
        containers: List[Container],
        target_locales: List[str],
        incremental: bool = True
    ) -> Dict[str, Any]:
        """
        同步项目
        
        Args:
            project_id: Trans-Hub 项目 ID
            containers: 要同步的容器列表
            target_locales: 目标语言列表
            incremental: 是否增量同步
            
        Returns:
            同步结果
        """
        async with self.client:
            # 1. 检查项目状态
            success, project_info = await self.client.get_project(project_id)
            if not success:
                # 项目不存在，创建新项目
                success, project_id = await self._create_project(containers[0])
                if not success:
                    return {'success': False, 'error': '创建项目失败'}
            
            # 2. 上传内容
            upload_results = await self._upload_content(
                project_id, containers, incremental
            )
            
            # 3. 请求翻译
            translation_tasks = await self._request_translations(
                project_id, target_locales
            )
            
            # 4. 等待翻译完成（可选）
            # await self._wait_for_translations(project_id, translation_tasks)
            
            # 5. 下载补丁
            patch_results = await self._download_patches(
                project_id, target_locales
            )
            
            # 6. 更新同步状态
            self.last_sync = datetime.now()
            self.sync_status = {
                'project_id': project_id,
                'last_sync': self.last_sync.isoformat(),
                'uploaded': upload_results,
                'translations': translation_tasks,
                'patches': patch_results
            }
            
            return {
                'success': True,
                'project_id': project_id,
                'statistics': {
                    'containers_synced': len(containers),
                    'blobs_uploaded': upload_results.get('blob_count', 0),
                    'patches_downloaded': len(patch_results.get('patch_items', []))
                }
            }
    
    async def _create_project(self, container: Container) -> Tuple[bool, Optional[str]]:
        """创建 Trans-Hub 项目"""
        project_name = f"MC_{container.display_name}_{datetime.now().strftime('%Y%m%d')}"
        description = f"Minecraft localization project for {container.display_name}"
        
        return await self.client.create_project(
            name=project_name,
            description=description,
            source_language="en_us",
            target_languages=["zh_cn", "zh_tw", "ja_jp"]
        )
    
    async def _upload_content(
        self,
        project_id: str,
        containers: List[Container],
        incremental: bool
    ) -> Dict[str, Any]:
        """上传内容到 Trans-Hub"""
        upload_stats = {
            'blob_count': 0,
            'entry_count': 0,
            'skipped_count': 0,
            'failed_count': 0
        }
        
        # 收集所有需要上传的 Blob
        uploaded_hashes: Set[str] = set()
        
        for container in containers:
            for lang_file in container.language_files:
                if not lang_file.content_hash:
                    continue
                
                # 检查是否已上传
                if lang_file.content_hash in uploaded_hashes:
                    upload_stats['skipped_count'] += 1
                    continue
                
                # 获取 Blob
                blob = self.blob_service.get_blob(lang_file.content_hash)
                if not blob:
                    logger.warning(f"Blob 不存在: {lang_file.content_hash[:8]}...")
                    upload_stats['failed_count'] += 1
                    continue
                
                # 检查是否需要上传（增量模式）
                if incremental and self._is_blob_uploaded(blob.blob_hash):
                    upload_stats['skipped_count'] += 1
                    uploaded_hashes.add(blob.blob_hash)
                    continue
                
                # 上传 Blob
                blob.load_entries()
                success, blob_id = await self.client.upload_blob(
                    project_id=project_id,
                    blob_hash=blob.blob_hash,
                    blob_content=blob.entries,
                    metadata={
                        'container_id': container.container_id,
                        'namespace': lang_file.namespace,
                        'locale': lang_file.locale
                    }
                )
                
                if success:
                    upload_stats['blob_count'] += 1
                    upload_stats['entry_count'] += blob.entry_count
                    uploaded_hashes.add(blob.blob_hash)
                    self._mark_blob_uploaded(blob.blob_hash)
                else:
                    upload_stats['failed_count'] += 1
        
        logger.info(
            f"内容上传完成: {upload_stats['blob_count']} Blobs, "
            f"{upload_stats['entry_count']} 条目"
        )
        
        return upload_stats
    
    async def _request_translations(
        self,
        project_id: str,
        target_locales: List[str]
    ) -> List[str]:
        """请求翻译任务"""
        task_ids = []
        
        for locale in target_locales:
            success, task_id = await self.client.request_translation(
                project_id=project_id,
                source_locale="en_us",
                target_locale=locale,
                engine="auto"
            )
            
            if success:
                task_ids.append(task_id)
                logger.info(f"翻译任务创建: {task_id} (目标: {locale})")
        
        return task_ids
    
    async def _download_patches(
        self,
        project_id: str,
        target_locales: List[str]
    ) -> Dict[str, Any]:
        """下载补丁"""
        patch_stats = {
            'patch_sets': [],
            'patch_items': [],
            'total_entries': 0
        }
        
        for locale in target_locales:
            # 获取上次同步时间
            since_timestamp = None
            if self.last_sync:
                # 减去一小时以确保不遗漏
                since_time = self.last_sync - timedelta(hours=1)
                since_timestamp = since_time.isoformat()
            
            # 下载补丁集
            success, patch_data = await self.client.download_patch_set(
                project_id=project_id,
                locale=locale,
                since_timestamp=since_timestamp
            )
            
            if not success or not patch_data:
                logger.warning(f"下载补丁失败: {locale}")
                continue
            
            # 导入补丁集
            patch_set = await self._import_patch_set(patch_data, locale)
            if patch_set:
                patch_stats['patch_sets'].append(patch_set.patch_set_id)
                patch_stats['patch_items'].extend([
                    item.patch_item_id for item in patch_set.patch_items
                ])
                patch_stats['total_entries'] += sum(
                    len(item.content) for item in patch_set.patch_items
                )
        
        logger.info(
            f"补丁下载完成: {len(patch_stats['patch_sets'])} 个补丁集, "
            f"{len(patch_stats['patch_items'])} 个补丁项"
        )
        
        return patch_stats
    
    async def _import_patch_set(
        self,
        patch_data: Dict,
        locale: str
    ) -> Optional[PatchSet]:
        """导入补丁集"""
        try:
            # 创建补丁集
            patch_set = self.patch_service.create_patch_set(
                name=f"TransHub_Sync_{locale}_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
                description=f"从 Trans-Hub 同步的 {locale} 翻译",
                version="1.0.0"
            )
            
            # 添加补丁项
            for item_data in patch_data.get('patch_items', []):
                # 质量检查
                passed, results = self.quality_gate.validate_batch(
                    item_data.get('content', {}),
                    item_data.get('source_content', {})
                )
                
                if not passed:
                    logger.warning(f"补丁项质量检查失败: {item_data.get('namespace')}:{locale}")
                    continue
                
                # 生成补丁项
                patch_item = self.patch_service.generate_patch_item(
                    container_id=item_data.get('container_id'),
                    locale=locale,
                    new_entries=item_data.get('content', {}),
                    policy=PatchPolicy.OVERLAY,
                    namespace=item_data.get('namespace')
                )
                
                if patch_item:
                    self.patch_service.add_patch_item_to_set(
                        patch_set.patch_set_id, patch_item
                    )
            
            # 发布补丁集
            if len(patch_set.patch_items) > 0:
                self.patch_service.publish_patch_set(patch_set.patch_set_id)
                return patch_set
            
        except Exception as e:
            logger.error(f"导入补丁集失败: {e}")
        
        return None
    
    def _is_blob_uploaded(self, blob_hash: str) -> bool:
        """检查 Blob 是否已上传"""
        # 这里可以使用缓存或数据库记录
        # 简化实现：使用内存缓存
        if not hasattr(self, '_uploaded_blobs'):
            self._uploaded_blobs = set()
        return blob_hash in self._uploaded_blobs
    
    def _mark_blob_uploaded(self, blob_hash: str) -> None:
        """标记 Blob 为已上传"""
        if not hasattr(self, '_uploaded_blobs'):
            self._uploaded_blobs = set()
        self._uploaded_blobs.add(blob_hash)
    
    async def get_sync_status(self) -> Dict[str, Any]:
        """获取同步状态"""
        return {
            'connected': await self.client.health_check(),
            'last_sync': self.last_sync.isoformat() if self.last_sync else None,
            'sync_status': self.sync_status
        }