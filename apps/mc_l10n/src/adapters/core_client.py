"""
Trans-Hub Core客户端
基于升级方案实现与Trans-Hub核心的通信，专注于适配器功能
"""

import asyncio
import time
import json
import httpx
from typing import Dict, List, Optional, Any, Union, AsyncIterator
from dataclasses import dataclass, asdict
from enum import Enum
import structlog

logger = structlog.get_logger(__name__)


class TransHubClientError(Exception):
    """Trans-Hub客户端错误"""
    pass


class TransHubConnectionError(TransHubClientError):
    """连接错误"""
    pass


class TransHubAuthError(TransHubClientError):
    """认证错误"""
    pass


@dataclass
class TransHubConfig:
    """Trans-Hub配置"""
    base_url: str
    api_key: str
    app_name: str = "mc-l10n"
    timeout: float = 30.0
    max_retries: int = 3
    enable_cache: bool = True


@dataclass
class ProjectInfo:
    """项目信息"""
    id: str
    name: str
    type: str
    status: str
    metadata: Dict[str, Any]
    created_at: str
    updated_at: str


@dataclass
class ContentItem:
    """内容项目"""
    uida_hash: str
    uida_uri: str
    namespace: str
    project_id: str
    keys: List[str]
    context: Dict[str, Any]
    source_text: str
    target_text: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None
    status: str = "active"


@dataclass
class IngestionResult:
    """摄入结果"""
    success: bool
    project_id: str
    processed_items: int
    failed_items: int
    errors: List[str]
    operation_id: Optional[str] = None


@dataclass
class ExportFilter:
    """导出过滤器"""
    target_language: Optional[str] = None
    status_filter: Optional[List[str]] = None
    mod_id_filter: Optional[str] = None
    updated_since: Optional[str] = None


class TransHubClient:
    """Trans-Hub核心客户端"""
    
    def __init__(self, config: TransHubConfig):
        self.config = config
        self.session: Optional[httpx.AsyncClient] = None
        self.auth_token: Optional[str] = None
        self.last_auth_time: float = 0
        self.auth_cache_duration: float = 3600  # 1小时
        
        logger.info("Trans-Hub客户端初始化",
                   base_url=config.base_url,
                   app_name=config.app_name)
    
    async def __aenter__(self):
        await self.connect()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.disconnect()
    
    async def connect(self):
        """建立连接"""
        if self.session is None:
            self.session = httpx.AsyncClient(
                base_url=self.config.base_url,
                timeout=httpx.Timeout(self.config.timeout),
                headers={
                    "User-Agent": f"TH-Suite-{self.config.app_name}/2.0",
                    "Content-Type": "application/json"
                }
            )
        
        # 进行认证
        await self._authenticate()
        logger.info("Trans-Hub连接已建立")
    
    async def disconnect(self):
        """断开连接"""
        if self.session:
            await self.session.aclose()
            self.session = None
        
        self.auth_token = None
        logger.info("Trans-Hub连接已断开")
    
    async def _authenticate(self):
        """进行认证"""
        current_time = time.time()
        
        # 检查token是否仍然有效
        if (self.auth_token and 
            current_time - self.last_auth_time < self.auth_cache_duration):
            return
        
        try:
            response = await self.session.post(
                "/auth/token",
                json={
                    "api_key": self.config.api_key,
                    "app_name": self.config.app_name
                }
            )
            response.raise_for_status()
            
            auth_data = response.json()
            self.auth_token = auth_data["access_token"]
            self.last_auth_time = current_time
            
            # 更新session headers
            self.session.headers.update({
                "Authorization": f"Bearer {self.auth_token}"
            })
            
            logger.info("Trans-Hub认证成功")
            
        except httpx.HTTPStatusError as e:
            if e.response.status_code == 401:
                raise TransHubAuthError("API Key无效或已过期")
            else:
                raise TransHubConnectionError(f"认证失败: {e}")
        except Exception as e:
            raise TransHubConnectionError(f"认证连接失败: {e}")
    
    async def create_project(self, project_data: Dict[str, Any]) -> ProjectInfo:
        """创建项目"""
        try:
            await self._ensure_authenticated()
            
            response = await self.session.post(
                "/projects",
                json=project_data
            )
            response.raise_for_status()
            
            project_json = response.json()
            
            return ProjectInfo(
                id=project_json["id"],
                name=project_json["name"],
                type=project_json["type"],
                status=project_json["status"],
                metadata=project_json.get("metadata", {}),
                created_at=project_json["created_at"],
                updated_at=project_json["updated_at"]
            )
            
        except httpx.HTTPStatusError as e:
            logger.error("创建项目失败", status_code=e.response.status_code, response=e.response.text)
            raise TransHubClientError(f"创建项目失败: {e}")
        except Exception as e:
            logger.error("创建项目异常", error=str(e))
            raise TransHubConnectionError(f"创建项目连接失败: {e}")
    
    async def get_project(self, project_id: str) -> Optional[ProjectInfo]:
        """获取项目信息"""
        try:
            await self._ensure_authenticated()
            
            response = await self.session.get(f"/projects/{project_id}")
            
            if response.status_code == 404:
                return None
            
            response.raise_for_status()
            project_json = response.json()
            
            return ProjectInfo(
                id=project_json["id"],
                name=project_json["name"],
                type=project_json["type"],
                status=project_json["status"],
                metadata=project_json.get("metadata", {}),
                created_at=project_json["created_at"],
                updated_at=project_json["updated_at"]
            )
            
        except httpx.HTTPStatusError as e:
            logger.error("获取项目失败", project_id=project_id, status_code=e.response.status_code)
            raise TransHubClientError(f"获取项目失败: {e}")
        except Exception as e:
            logger.error("获取项目异常", project_id=project_id, error=str(e))
            raise TransHubConnectionError(f"获取项目连接失败: {e}")
    
    async def ingest_content(
        self, 
        project_id: str, 
        content_items: List[ContentItem]
    ) -> IngestionResult:
        """摄入内容到核心"""
        try:
            await self._ensure_authenticated()
            
            # 转换为API格式
            api_items = [
                {
                    "uida_hash": item.uida_hash,
                    "uida_uri": item.uida_uri,
                    "namespace": item.namespace,
                    "project_id": item.project_id,
                    "keys": item.keys,
                    "context": item.context,
                    "source_text": item.source_text,
                    "target_text": item.target_text,
                    "metadata": item.metadata or {},
                    "status": item.status
                }
                for item in content_items
            ]
            
            response = await self.session.post(
                f"/projects/{project_id}/content/ingest",
                json={
                    "items": api_items,
                    "batch_size": len(api_items),
                    "app_name": self.config.app_name
                }
            )
            response.raise_for_status()
            
            result_data = response.json()
            
            return IngestionResult(
                success=result_data["success"],
                project_id=project_id,
                processed_items=result_data["processed_items"],
                failed_items=result_data["failed_items"],
                errors=result_data.get("errors", []),
                operation_id=result_data.get("operation_id")
            )
            
        except httpx.HTTPStatusError as e:
            logger.error("内容摄入失败", 
                        project_id=project_id,
                        items_count=len(content_items),
                        status_code=e.response.status_code)
            raise TransHubClientError(f"内容摄入失败: {e}")
        except Exception as e:
            logger.error("内容摄入异常", project_id=project_id, error=str(e))
            raise TransHubConnectionError(f"内容摄入连接失败: {e}")
    
    async def export_content(
        self, 
        project_id: str, 
        export_filter: ExportFilter
    ) -> AsyncIterator[Dict[str, Any]]:
        """导出内容（流式）"""
        try:
            await self._ensure_authenticated()
            
            # 构建查询参数
            params = {}
            if export_filter.target_language:
                params["target_language"] = export_filter.target_language
            if export_filter.status_filter:
                params["status"] = ",".join(export_filter.status_filter)
            if export_filter.mod_id_filter:
                params["mod_id"] = export_filter.mod_id_filter
            if export_filter.updated_since:
                params["updated_since"] = export_filter.updated_since
            
            async with self.session.stream(
                "GET",
                f"/projects/{project_id}/content/export",
                params=params
            ) as response:
                response.raise_for_status()
                
                async for line in response.aiter_lines():
                    if line:
                        try:
                            item = json.loads(line)
                            yield item
                        except json.JSONDecodeError:
                            logger.warning("跳过无效的JSON行", line=line)
                            continue
                            
        except httpx.HTTPStatusError as e:
            logger.error("内容导出失败",
                        project_id=project_id,
                        status_code=e.response.status_code)
            raise TransHubClientError(f"内容导出失败: {e}")
        except Exception as e:
            logger.error("内容导出异常", project_id=project_id, error=str(e))
            raise TransHubConnectionError(f"内容导出连接失败: {e}")
    
    async def register_projection_spec(self, spec_data: Dict[str, Any]) -> bool:
        """注册投影规范"""
        try:
            await self._ensure_authenticated()
            
            response = await self.session.post(
                "/projection-specs",
                json={
                    "spec": spec_data,
                    "app_name": self.config.app_name
                }
            )
            response.raise_for_status()
            
            result = response.json()
            success = result.get("success", False)
            
            if success:
                logger.info("投影规范注册成功", 
                           app=spec_data.get("app"),
                           version=spec_data.get("version"))
            else:
                logger.error("投影规范注册失败", errors=result.get("errors"))
            
            return success
            
        except httpx.HTTPStatusError as e:
            logger.error("投影规范注册失败", status_code=e.response.status_code)
            raise TransHubClientError(f"投影规范注册失败: {e}")
        except Exception as e:
            logger.error("投影规范注册异常", error=str(e))
            raise TransHubConnectionError(f"投影规范注册连接失败: {e}")
    
    async def get_translation_progress(self, project_id: str) -> Dict[str, Any]:
        """获取翻译进度"""
        try:
            await self._ensure_authenticated()
            
            response = await self.session.get(f"/projects/{project_id}/progress")
            response.raise_for_status()
            
            return response.json()
            
        except httpx.HTTPStatusError as e:
            logger.error("获取翻译进度失败", 
                        project_id=project_id,
                        status_code=e.response.status_code)
            raise TransHubClientError(f"获取翻译进度失败: {e}")
        except Exception as e:
            logger.error("获取翻译进度异常", project_id=project_id, error=str(e))
            raise TransHubConnectionError(f"获取翻译进度连接失败: {e}")
    
    async def health_check(self) -> Dict[str, Any]:
        """健康检查"""
        try:
            if not self.session:
                await self.connect()
            
            response = await self.session.get("/health")
            response.raise_for_status()
            
            health_data = response.json()
            logger.debug("健康检查通过", status=health_data.get("status"))
            
            return health_data
            
        except Exception as e:
            logger.error("健康检查失败", error=str(e))
            raise TransHubConnectionError(f"健康检查失败: {e}")
    
    async def _ensure_authenticated(self):
        """确保已认证"""
        if not self.session:
            await self.connect()
        else:
            await self._authenticate()
    
    def is_connected(self) -> bool:
        """检查是否已连接"""
        return self.session is not None and self.auth_token is not None


# ==================== 工厂函数和便捷函数 ====================

def create_transhub_client(
    base_url: str,
    api_key: str,
    app_name: str = "mc-l10n",
    **kwargs
) -> TransHubClient:
    """创建Trans-Hub客户端"""
    config = TransHubConfig(
        base_url=base_url,
        api_key=api_key,
        app_name=app_name,
        **kwargs
    )
    return TransHubClient(config)


async def test_transhub_connection(
    base_url: str,
    api_key: str,
    app_name: str = "mc-l10n"
) -> Dict[str, Any]:
    """测试Trans-Hub连接"""
    client = create_transhub_client(base_url, api_key, app_name)
    
    try:
        async with client:
            health = await client.health_check()
            return {
                "success": True,
                "health": health,
                "message": "连接测试成功"
            }
    except Exception as e:
        return {
            "success": False,
            "error": str(e),
            "message": "连接测试失败"
        }


# ==================== 全局客户端实例（可选） ====================

_global_client: Optional[TransHubClient] = None


def get_global_client() -> Optional[TransHubClient]:
    """获取全局客户端实例"""
    return _global_client


def set_global_client(client: TransHubClient):
    """设置全局客户端实例"""
    global _global_client
    _global_client = client


def initialize_global_client(base_url: str, api_key: str, app_name: str = "mc-l10n"):
    """初始化全局客户端"""
    client = create_transhub_client(base_url, api_key, app_name)
    set_global_client(client)
    logger.info("全局Trans-Hub客户端已初始化", base_url=base_url, app_name=app_name)