"""
应用服务基类

封装业务逻辑，协调领域对象完成业务操作
"""

from abc import ABC, abstractmethod
from typing import Any

from ...framework.logging.logger import ILogger


class IApplicationService(ABC):
    """应用服务接口"""

    @abstractmethod
    async def execute(self, *args, **kwargs) -> Any:
        """执行服务"""
        pass


class BaseService(IApplicationService):
    """应用服务基类"""

    def __init__(self, logger: ILogger | None = None):
        self.logger = logger

    def log_info(self, message: str, **kwargs) -> None:
        """记录信息日志"""
        if self.logger:
            self.logger.info(message, **kwargs)

    def log_error(
        self, message: str, exception: Exception | None = None, **kwargs
    ) -> None:
        """记录错误日志"""
        if self.logger:
            self.logger.error(message, exception=exception, **kwargs)

    async def execute(self, *args, **kwargs) -> Any:
        """执行服务"""
        pass
