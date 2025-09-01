"""
HTTP客户端

提供HTTP通信功能
"""

from typing import Any


class HttpClient:
    """HTTP客户端"""

    def __init__(self, base_url: str = ""):
        self.base_url = base_url

    async def get(self, url: str, headers: dict[str, str] = None) -> dict[str, Any]:
        """GET请求"""
        # 简化实现
        return {"status": "ok", "data": "mock_data"}

    async def post(
        self, url: str, data: Any = None, headers: dict[str, str] = None
    ) -> dict[str, Any]:
        """POST请求"""
        # 简化实现
        return {"status": "ok", "data": data}
