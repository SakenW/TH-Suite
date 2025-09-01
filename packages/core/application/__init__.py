"""
应用服务层

提供业务逻辑支持，采用CQRS设计模式：
- 应用服务基类
- 命令模式（写操作）
- 查询模式（读操作）
- 异常处理
- 数据传输对象
"""

from .commands.command import Command, CommandBus
from .dto.base_dto import BaseDTO
from .exceptions.base_exception import BaseException, BusinessException
from .queries.query import Query, QueryBus
from .services.base_service import BaseService, IApplicationService

__all__ = [
    "BaseService",
    "IApplicationService",
    "Command",
    "CommandHandler",
    "CommandBus",
    "Query",
    "QueryHandler",
    "QueryBus",
    "BaseException",
    "BusinessException",
    "BaseDTO",
]
