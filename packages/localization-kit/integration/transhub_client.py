"""
Trans-Hub 客户端 - 与翻译平台集成

提供与 Trans-Hub 翻译平台的 API 集成
支持上传、下载、同步等操作
"""

import logging
import asyncio
import aiohttp
import json
from typing import Dict, List, Optional, Any, Tuple
from datetime import datetime
from pathlib import Path
import hashlib

logger = logging.getLogger(__name__)


class TransHubClient:
    """
    Trans-Hub API 客户端
    
    功能：
    1. 项目管理
    2. 内容上传（NDJSON 流式）
    3. 翻译任务管理
    4. 补丁下载
    5. 状态同步
    """
    
    def __init__(
        self,
        base_url: str = "http://localhost:8000",
        api_key: Optional[str] = None,
        timeout: int = 30
    ):
        """
        初始化 Trans-Hub 客户端
        
        Args:
            base_url: API 基础 URL
            api_key: API 密钥
            timeout: 请求超时时间（秒）
        """
        self.base_url = base_url.rstrip('/')
        self.api_key = api_key
        self.timeout = aiohttp.ClientTimeout(total=timeout)
        
        # 会话管理
        self.session: Optional[aiohttp.ClientSession] = None
        self.headers = {
            'Content-Type': 'application/json',
            'User-Agent': 'TransHub-LocalizationKit/1.0'
        }
        
        if api_key:
            self.headers['Authorization'] = f'Bearer {api_key}'
    
    async def __aenter__(self):
        """异步上下文管理器入口"""
        await self.connect()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """异步上下文管理器出口"""
        await self.close()
    
    async def connect(self) -> None:
        """建立连接"""
        if not self.session:
            self.session = aiohttp.ClientSession(
                timeout=self.timeout,
                headers=self.headers
            )
            logger.info(f"连接到 Trans-Hub: {self.base_url}")
    
    async def close(self) -> None:
        """关闭连接"""
        if self.session:
            await self.session.close()
            self.session = None
            logger.info("断开 Trans-Hub 连接")
    
    async def _request(
        self,
        method: str,
        endpoint: str,
        **kwargs
    ) -> Tuple[bool, Any]:
        """
        发送 HTTP 请求
        
        Args:
            method: HTTP 方法
            endpoint: API 端点
            **kwargs: 额外参数
            
        Returns:
            (成功标志, 响应数据)
        """
        if not self.session:
            await self.connect()
        
        url = f"{self.base_url}{endpoint}"
        
        try:
            async with self.session.request(method, url, **kwargs) as response:
                if response.status == 200:
                    data = await response.json()
                    return True, data
                else:
                    error_msg = await response.text()
                    logger.error(f"API 请求失败 ({response.status}): {error_msg}")
                    return False, {'error': error_msg, 'status': response.status}
                    
        except asyncio.TimeoutError:
            logger.error(f"请求超时: {url}")
            return False, {'error': 'Request timeout'}
        except Exception as e:
            logger.error(f"请求异常: {e}")
            return False, {'error': str(e)}
    
    # ==================== 项目管理 ====================
    
    async def create_project(
        self,
        name: str,
        description: str,
        source_language: str = "en_us",
        target_languages: Optional[List[str]] = None
    ) -> Tuple[bool, Optional[str]]:
        """
        创建翻译项目
        
        Args:
            name: 项目名称
            description: 项目描述
            source_language: 源语言
            target_languages: 目标语言列表
            
        Returns:
            (成功标志, 项目ID)
        """
        if not target_languages:
            target_languages = ["zh_cn"]
        
        payload = {
            'name': name,
            'description': description,
            'source_language': source_language,
            'target_languages': target_languages,
            'metadata': {
                'platform': 'minecraft',
                'created_by': 'localization_kit'
            }
        }
        
        success, data = await self._request(
            'POST',
            '/api/v1/projects',
            json=payload
        )
        
        if success:
            project_id = data.get('project_id')
            logger.info(f"创建项目成功: {project_id}")
            return True, project_id
        
        return False, None
    
    async def get_project(self, project_id: str) -> Tuple[bool, Optional[Dict]]:
        """
        获取项目信息
        
        Args:
            project_id: 项目 ID
            
        Returns:
            (成功标志, 项目信息)
        """
        success, data = await self._request(
            'GET',
            f'/api/v1/projects/{project_id}'
        )
        
        return success, data if success else None
    
    # ==================== 内容上传 ====================
    
    async def upload_content_stream(
        self,
        project_id: str,
        namespace: str,
        locale: str,
        entries: Dict[str, str],
        metadata: Optional[Dict] = None
    ) -> Tuple[bool, Optional[str]]:
        """
        流式上传内容（NDJSON）
        
        Args:
            project_id: 项目 ID
            namespace: 命名空间
            locale: 语言代码
            entries: 翻译条目
            metadata: 元数据
            
        Returns:
            (成功标志, 上传ID)
        """
        # 构建 NDJSON 流
        ndjson_lines = []
        
        # 头部信息
        header = {
            'type': 'header',
            'project_id': project_id,
            'namespace': namespace,
            'locale': locale,
            'total_entries': len(entries),
            'metadata': metadata or {},
            'timestamp': datetime.now().isoformat()
        }
        ndjson_lines.append(json.dumps(header, ensure_ascii=False))
        
        # 内容条目
        for key, value in entries.items():
            entry = {
                'type': 'entry',
                'key': key,
                'value': value,
                'hash': hashlib.md5(f"{key}:{value}".encode()).hexdigest()
            }
            ndjson_lines.append(json.dumps(entry, ensure_ascii=False))
        
        # 尾部信息
        footer = {
            'type': 'footer',
            'checksum': hashlib.sha256('\n'.join(ndjson_lines).encode()).hexdigest()
        }
        ndjson_lines.append(json.dumps(footer, ensure_ascii=False))
        
        # 发送流式数据
        ndjson_content = '\n'.join(ndjson_lines)
        
        success, data = await self._request(
            'POST',
            f'/api/v1/projects/{project_id}/content/upload',
            data=ndjson_content,
            headers={'Content-Type': 'application/x-ndjson'}
        )
        
        if success:
            upload_id = data.get('upload_id')
            logger.info(f"内容上传成功: {upload_id} ({len(entries)} 条目)")
            return True, upload_id
        
        return False, None
    
    async def upload_blob(
        self,
        project_id: str,
        blob_hash: str,
        blob_content: Dict[str, str],
        metadata: Optional[Dict] = None
    ) -> Tuple[bool, Optional[str]]:
        """
        上传 Blob（去重内容）
        
        Args:
            project_id: 项目 ID
            blob_hash: Blob 哈希
            blob_content: Blob 内容
            metadata: 元数据
            
        Returns:
            (成功标志, Blob ID)
        """
        payload = {
            'blob_hash': blob_hash,
            'content': blob_content,
            'entry_count': len(blob_content),
            'metadata': metadata or {}
        }
        
        success, data = await self._request(
            'POST',
            f'/api/v1/projects/{project_id}/blobs',
            json=payload
        )
        
        if success:
            blob_id = data.get('blob_id', blob_hash)
            logger.info(f"Blob 上传成功: {blob_id[:8]}...")
            return True, blob_id
        
        return False, None
    
    # ==================== 翻译管理 ====================
    
    async def request_translation(
        self,
        project_id: str,
        source_locale: str,
        target_locale: str,
        keys: Optional[List[str]] = None,
        engine: str = "auto"
    ) -> Tuple[bool, Optional[str]]:
        """
        请求翻译
        
        Args:
            project_id: 项目 ID
            source_locale: 源语言
            target_locale: 目标语言
            keys: 要翻译的键列表（None 表示全部）
            engine: 翻译引擎
            
        Returns:
            (成功标志, 任务ID)
        """
        payload = {
            'source_locale': source_locale,
            'target_locale': target_locale,
            'keys': keys,
            'engine': engine,
            'options': {
                'quality_check': True,
                'preserve_placeholders': True
            }
        }
        
        success, data = await self._request(
            'POST',
            f'/api/v1/projects/{project_id}/translate',
            json=payload
        )
        
        if success:
            task_id = data.get('task_id')
            logger.info(f"翻译任务创建成功: {task_id}")
            return True, task_id
        
        return False, None
    
    async def get_translation_status(
        self,
        project_id: str,
        task_id: str
    ) -> Tuple[bool, Optional[Dict]]:
        """
        获取翻译任务状态
        
        Args:
            project_id: 项目 ID
            task_id: 任务 ID
            
        Returns:
            (成功标志, 状态信息)
        """
        success, data = await self._request(
            'GET',
            f'/api/v1/projects/{project_id}/translate/{task_id}'
        )
        
        return success, data if success else None
    
    # ==================== 补丁下载 ====================
    
    async def download_patch_set(
        self,
        project_id: str,
        locale: str,
        since_timestamp: Optional[str] = None
    ) -> Tuple[bool, Optional[Dict]]:
        """
        下载补丁集
        
        Args:
            project_id: 项目 ID
            locale: 目标语言
            since_timestamp: 增量更新时间戳
            
        Returns:
            (成功标志, 补丁集数据)
        """
        params = {'locale': locale}
        if since_timestamp:
            params['since'] = since_timestamp
        
        success, data = await self._request(
            'GET',
            f'/api/v1/projects/{project_id}/patches',
            params=params
        )
        
        if success:
            logger.info(f"下载补丁集成功: {len(data.get('patch_items', []))} 个补丁项")
            return True, data
        
        return False, None
    
    async def download_translated_content(
        self,
        project_id: str,
        namespace: str,
        locale: str
    ) -> Tuple[bool, Optional[Dict[str, str]]]:
        """
        下载翻译内容
        
        Args:
            project_id: 项目 ID
            namespace: 命名空间
            locale: 语言代码
            
        Returns:
            (成功标志, 翻译内容)
        """
        success, data = await self._request(
            'GET',
            f'/api/v1/projects/{project_id}/content/{namespace}/{locale}'
        )
        
        if success:
            content = data.get('content', {})
            logger.info(f"下载翻译内容成功: {len(content)} 条目")
            return True, content
        
        return False, None
    
    # ==================== 状态同步 ====================
    
    async def sync_status(
        self,
        project_id: str
    ) -> Tuple[bool, Optional[Dict]]:
        """
        同步项目状态
        
        Args:
            project_id: 项目 ID
            
        Returns:
            (成功标志, 状态信息)
        """
        success, data = await self._request(
            'GET',
            f'/api/v1/projects/{project_id}/status'
        )
        
        if success:
            status = {
                'project_id': project_id,
                'translation_progress': data.get('translation_progress', {}),
                'pending_tasks': data.get('pending_tasks', []),
                'recent_updates': data.get('recent_updates', []),
                'last_sync': datetime.now().isoformat()
            }
            return True, status
        
        return False, None
    
    async def report_apply_result(
        self,
        project_id: str,
        patch_set_id: str,
        results: List[Dict]
    ) -> Tuple[bool, Optional[str]]:
        """
        报告补丁应用结果
        
        Args:
            project_id: 项目 ID
            patch_set_id: 补丁集 ID
            results: 应用结果列表
            
        Returns:
            (成功标志, 报告ID)
        """
        payload = {
            'patch_set_id': patch_set_id,
            'results': results,
            'timestamp': datetime.now().isoformat(),
            'client_version': '1.0.0'
        }
        
        success, data = await self._request(
            'POST',
            f'/api/v1/projects/{project_id}/apply-reports',
            json=payload
        )
        
        if success:
            report_id = data.get('report_id')
            logger.info(f"应用结果报告成功: {report_id}")
            return True, report_id
        
        return False, None
    
    # ==================== 健康检查 ====================
    
    async def health_check(self) -> bool:
        """
        健康检查
        
        Returns:
            是否健康
        """
        success, data = await self._request('GET', '/health')
        
        if success:
            status = data.get('status')
            return status == 'healthy'
        
        return False
    
    async def get_server_info(self) -> Optional[Dict]:
        """
        获取服务器信息
        
        Returns:
            服务器信息
        """
        success, data = await self._request('GET', '/info')
        return data if success else None