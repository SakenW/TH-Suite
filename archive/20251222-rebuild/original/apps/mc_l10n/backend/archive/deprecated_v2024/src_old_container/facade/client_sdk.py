"""
MC L10n 客户端SDK
提供简化的Python客户端接口，方便其他应用程序集成
"""

import logging
from dataclasses import dataclass
from typing import Any

import httpx

logger = logging.getLogger(__name__)


@dataclass
class ScanResult:
    """扫描结果"""

    total_files: int
    mods_found: int
    translations_found: int
    errors: list[str]
    duration: float
    success: bool

    @classmethod
    def from_dict(cls, data: dict) -> "ScanResult":
        return cls(
            total_files=data["total_files"],
            mods_found=data["mods_found"],
            translations_found=data["translations_found"],
            errors=data.get("errors", []),
            duration=data["duration"],
            success=data.get("success", len(data.get("errors", [])) == 0),
        )


@dataclass
class TranslationResult:
    """翻译结果"""

    mod_id: str
    language: str
    translated_count: int
    failed_count: int
    progress: float
    quality_score: float | None = None

    @classmethod
    def from_dict(cls, data: dict) -> "TranslationResult":
        return cls(
            mod_id=data["mod_id"],
            language=data["language"],
            translated_count=data["translated_count"],
            failed_count=data["failed_count"],
            progress=data["progress"],
            quality_score=data.get("quality_score"),
        )


@dataclass
class SyncResult:
    """同步结果"""

    synced_count: int
    conflict_count: int
    error_count: int
    duration: float

    @classmethod
    def from_dict(cls, data: dict) -> "SyncResult":
        return cls(
            synced_count=data["synced_count"],
            conflict_count=data["conflict_count"],
            error_count=data["error_count"],
            duration=data["duration"],
        )


@dataclass
class ProjectInfo:
    """项目信息"""

    id: str
    name: str
    status: str
    progress: dict[str, float]
    statistics: dict[str, Any]
    estimated_completion: str | None = None

    @classmethod
    def from_dict(cls, data: dict) -> "ProjectInfo":
        return cls(
            id=data["id"],
            name=data["name"],
            status=data["status"],
            progress=data["progress"],
            statistics=data["statistics"],
            estimated_completion=data.get("estimated_completion"),
        )


@dataclass
class QualityReport:
    """质量报告"""

    mod_id: str
    language: str
    total_translations: int
    approved: int
    rejected: int
    pending: int
    approval_rate: float
    average_quality: float
    needs_review: bool

    @classmethod
    def from_dict(cls, data: dict) -> "QualityReport":
        return cls(
            mod_id=data["mod_id"],
            language=data["language"],
            total_translations=data["total_translations"],
            approved=data["approved"],
            rejected=data["rejected"],
            pending=data["pending"],
            approval_rate=data["approval_rate"],
            average_quality=data["average_quality"],
            needs_review=data["needs_review"],
        )


class MCL10nSDKError(Exception):
    """SDK 异常基类"""

    pass


class MCL10nConnectionError(MCL10nSDKError):
    """连接异常"""

    pass


class MCL10nAPIError(MCL10nSDKError):
    """API 异常"""

    def __init__(self, message: str, status_code: int, response_data: dict = None):
        super().__init__(message)
        self.status_code = status_code
        self.response_data = response_data or {}


class MCL10nClient:
    """MC L10n 客户端

    提供简化的API访问接口：
    - 自动处理HTTP通信
    - 类型安全的请求/响应
    - 错误处理和重试
    - 异步支持

    使用示例:
        client = MCL10nClient("http://localhost:18000")
        result = client.scan_mods("/path/to/mods")
        if result.success:
            print(f"找到 {result.mods_found} 个模组")
    """

    def __init__(
        self,
        base_url: str = "http://localhost:18000",
        timeout: float = 30.0,
        retry_count: int = 3,
        api_key: str | None = None,
    ):
        """初始化客户端

        Args:
            base_url: 服务器地址
            timeout: 请求超时时间（秒）
            retry_count: 重试次数
            api_key: API密钥（如果需要）
        """
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout
        self.retry_count = retry_count

        # 构建HTTP客户端
        headers = {"Content-Type": "application/json"}
        if api_key:
            headers["Authorization"] = f"Bearer {api_key}"

        self._client = httpx.Client(
            base_url=self.base_url,
            headers=headers,
            timeout=timeout,
        )

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()

    def close(self):
        """关闭客户端"""
        self._client.close()

    # ========== 扫描相关方法 ==========

    def scan_mods(
        self,
        path: str,
        recursive: bool = True,
        auto_extract: bool = True,
    ) -> ScanResult:
        """扫描MOD目录

        Args:
            path: 扫描路径
            recursive: 是否递归扫描
            auto_extract: 是否自动提取JAR文件

        Returns:
            扫描结果
        """
        data = {
            "path": path,
            "recursive": recursive,
            "auto_extract": auto_extract,
        }

        response = self._post("/api/v2/scan", data)
        return ScanResult.from_dict(response["data"])

    def quick_scan(self, path: str) -> dict[str, Any]:
        """快速扫描（仅统计）

        Args:
            path: 扫描路径

        Returns:
            扫描统计信息
        """
        params = {"path": path}
        response = self._get("/api/v2/scan/quick", params=params)
        return response["data"]

    # ========== 翻译相关方法 ==========

    def translate_mod(
        self,
        mod_id: str,
        language: str,
        translations: dict[str, str],
        translator: str | None = None,
        auto_approve: bool = False,
    ) -> TranslationResult:
        """翻译MOD

        Args:
            mod_id: MOD ID
            language: 目标语言
            translations: 翻译映射 {key: translated_text}
            translator: 翻译者ID
            auto_approve: 是否自动批准

        Returns:
            翻译结果
        """
        data = {
            "mod_id": mod_id,
            "language": language,
            "translations": translations,
            "translator": translator,
            "auto_approve": auto_approve,
        }

        response = self._post("/api/v2/translate", data)
        return TranslationResult.from_dict(response["data"])

    def batch_translate(
        self,
        mod_ids: list[str],
        language: str,
        quality_threshold: float = 0.8,
    ) -> list[TranslationResult]:
        """批量翻译多个MOD

        Args:
            mod_ids: MOD ID列表
            language: 目标语言
            quality_threshold: 质量阈值

        Returns:
            翻译结果列表
        """
        data = {
            "mod_ids": mod_ids,
            "language": language,
            "quality_threshold": quality_threshold,
        }

        response = self._post("/api/v2/translate/batch", data)
        results_data = response["data"]["results"]

        return [
            TranslationResult(
                mod_id=r["mod_id"],
                language=language,
                translated_count=r["translated_count"],
                failed_count=0,  # 批量接口没有返回失败数
                progress=r["progress"],
            )
            for r in results_data
        ]

    # ========== 项目管理方法 ==========

    def create_project(
        self,
        name: str,
        mod_ids: list[str],
        target_languages: list[str] | None = None,
        auto_assign: bool = False,
    ) -> str:
        """创建翻译项目

        Args:
            name: 项目名称
            mod_ids: 包含的MOD ID列表
            target_languages: 目标语言列表
            auto_assign: 是否自动分配任务

        Returns:
            项目ID
        """
        data = {
            "name": name,
            "mod_ids": mod_ids,
            "target_languages": target_languages,
            "auto_assign": auto_assign,
        }

        response = self._post("/api/v2/projects", data)
        return response["data"]["project_id"]

    def get_project(self, project_id: str) -> ProjectInfo:
        """获取项目信息

        Args:
            project_id: 项目ID

        Returns:
            项目信息
        """
        response = self._get(f"/api/v2/projects/{project_id}")
        return ProjectInfo.from_dict(response["data"])

    # ========== 同步方法 ==========

    def sync_with_server(
        self,
        server_url: str | None = None,
        conflict_strategy: str | None = None,
    ) -> SyncResult:
        """同步到服务器

        Args:
            server_url: 服务器地址
            conflict_strategy: 冲突解决策略

        Returns:
            同步结果
        """
        data = {
            "server_url": server_url,
            "conflict_strategy": conflict_strategy,
        }

        response = self._post("/api/v2/sync", data)
        return SyncResult.from_dict(response["data"])

    # ========== 质量管理方法 ==========

    def check_quality(self, mod_id: str, language: str) -> QualityReport:
        """检查翻译质量

        Args:
            mod_id: MOD ID
            language: 语言代码

        Returns:
            质量报告
        """
        params = {"language": language}
        response = self._get(f"/api/v2/quality/{mod_id}", params=params)
        return QualityReport.from_dict(response["data"])

    # ========== 快捷方法 ==========

    def scan_and_translate(
        self,
        path: str,
        language: str,
        auto_approve: bool = False,
    ) -> dict[str, Any]:
        """一键扫描并翻译

        Args:
            path: 扫描路径
            language: 目标语言
            auto_approve: 是否自动批准

        Returns:
            操作结果
        """
        data = {
            "path": path,
            "language": language,
            "auto_approve": auto_approve,
        }

        response = self._post("/api/v2/quick/scan-and-translate", data)
        return response["data"]

    def get_system_status(self) -> dict[str, Any]:
        """获取系统状态

        Returns:
            系统状态信息
        """
        response = self._get("/api/v2/status")
        return response["data"]

    # ========== 便利方法 ==========

    def is_server_available(self) -> bool:
        """检查服务器是否可用

        Returns:
            服务器是否可用
        """
        try:
            self.get_system_status()
            return True
        except Exception:
            return False

    def get_supported_languages(self) -> list[str]:
        """获取支持的语言列表

        Returns:
            支持的语言代码列表
        """
        # 这里返回常用语言，实际应该从API获取
        return ["zh_cn", "zh_tw", "ja_jp", "ko_kr", "en_us", "de_de", "fr_fr"]

    # ========== 内部方法 ==========

    def _get(self, url: str, params: dict = None) -> dict:
        """发送GET请求"""
        return self._request("GET", url, params=params)

    def _post(self, url: str, data: dict) -> dict:
        """发送POST请求"""
        return self._request("POST", url, json=data)

    def _request(
        self, method: str, url: str, params: dict = None, json: dict = None
    ) -> dict:
        """发送HTTP请求"""
        for attempt in range(self.retry_count + 1):
            try:
                response = self._client.request(
                    method=method,
                    url=url,
                    params=params,
                    json=json,
                )

                # 检查HTTP状态码
                if response.status_code >= 400:
                    error_data = {}
                    try:
                        error_data = response.json()
                    except json.JSONDecodeError:
                        pass

                    raise MCL10nAPIError(
                        message=f"API error: {response.status_code}",
                        status_code=response.status_code,
                        response_data=error_data,
                    )

                # 解析响应
                try:
                    data = response.json()
                except json.JSONDecodeError as e:
                    raise MCL10nAPIError(f"Invalid JSON response: {e}", 500)

                # 检查API层面的错误
                if not data.get("success", True):
                    error_msg = "API request failed"
                    if "errors" in data:
                        error_msg = f"API errors: {', '.join(data['errors'])}"
                    elif "message" in data:
                        error_msg = data["message"]

                    raise MCL10nAPIError(error_msg, response.status_code, data)

                return data

            except (httpx.RequestError, httpx.TimeoutException) as e:
                if attempt == self.retry_count:
                    raise MCL10nConnectionError(f"Connection failed: {e}")

                logger.warning(f"Request attempt {attempt + 1} failed: {e}")
                continue

        raise MCL10nConnectionError("Max retries exceeded")


# ========== 异步客户端 ==========


class AsyncMCL10nClient:
    """异步MC L10n客户端

    提供异步API访问接口，适用于高并发场景
    """

    def __init__(
        self,
        base_url: str = "http://localhost:18000",
        timeout: float = 30.0,
        retry_count: int = 3,
        api_key: str | None = None,
    ):
        """初始化异步客户端"""
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout
        self.retry_count = retry_count

        headers = {"Content-Type": "application/json"}
        if api_key:
            headers["Authorization"] = f"Bearer {api_key}"

        self._client = httpx.AsyncClient(
            base_url=self.base_url,
            headers=headers,
            timeout=timeout,
        )

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.close()

    async def close(self):
        """关闭异步客户端"""
        await self._client.aclose()

    async def scan_mods(
        self,
        path: str,
        recursive: bool = True,
        auto_extract: bool = True,
    ) -> ScanResult:
        """异步扫描MOD目录"""
        data = {
            "path": path,
            "recursive": recursive,
            "auto_extract": auto_extract,
        }

        response = await self._post("/api/v2/scan", data)
        return ScanResult.from_dict(response["data"])

    async def translate_mod(
        self,
        mod_id: str,
        language: str,
        translations: dict[str, str],
        translator: str | None = None,
        auto_approve: bool = False,
    ) -> TranslationResult:
        """异步翻译MOD"""
        data = {
            "mod_id": mod_id,
            "language": language,
            "translations": translations,
            "translator": translator,
            "auto_approve": auto_approve,
        }

        response = await self._post("/api/v2/translate", data)
        return TranslationResult.from_dict(response["data"])

    async def _get(self, url: str, params: dict = None) -> dict:
        """发送异步GET请求"""
        return await self._request("GET", url, params=params)

    async def _post(self, url: str, data: dict) -> dict:
        """发送异步POST请求"""
        return await self._request("POST", url, json=data)

    async def _request(
        self, method: str, url: str, params: dict = None, json: dict = None
    ) -> dict:
        """发送异步HTTP请求"""
        for attempt in range(self.retry_count + 1):
            try:
                response = await self._client.request(
                    method=method,
                    url=url,
                    params=params,
                    json=json,
                )

                if response.status_code >= 400:
                    error_data = {}
                    try:
                        error_data = response.json()
                    except json.JSONDecodeError:
                        pass

                    raise MCL10nAPIError(
                        message=f"API error: {response.status_code}",
                        status_code=response.status_code,
                        response_data=error_data,
                    )

                try:
                    data = response.json()
                except json.JSONDecodeError as e:
                    raise MCL10nAPIError(f"Invalid JSON response: {e}", 500)

                if not data.get("success", True):
                    error_msg = "API request failed"
                    if "errors" in data:
                        error_msg = f"API errors: {', '.join(data['errors'])}"
                    elif "message" in data:
                        error_msg = data["message"]

                    raise MCL10nAPIError(error_msg, response.status_code, data)

                return data

            except (httpx.RequestError, httpx.TimeoutException) as e:
                if attempt == self.retry_count:
                    raise MCL10nConnectionError(f"Connection failed: {e}")

                logger.warning(f"Async request attempt {attempt + 1} failed: {e}")
                continue

        raise MCL10nConnectionError("Max retries exceeded")


# ========== 工厂函数 ==========


def create_client(
    base_url: str = "http://localhost:18000",
    timeout: float = 30.0,
    api_key: str | None = None,
) -> MCL10nClient:
    """创建同步客户端

    Args:
        base_url: 服务器地址
        timeout: 超时时间
        api_key: API密钥

    Returns:
        客户端实例
    """
    return MCL10nClient(base_url=base_url, timeout=timeout, api_key=api_key)


def create_async_client(
    base_url: str = "http://localhost:18000",
    timeout: float = 30.0,
    api_key: str | None = None,
) -> AsyncMCL10nClient:
    """创建异步客户端

    Args:
        base_url: 服务器地址
        timeout: 超时时间
        api_key: API密钥

    Returns:
        异步客户端实例
    """
    return AsyncMCL10nClient(base_url=base_url, timeout=timeout, api_key=api_key)
