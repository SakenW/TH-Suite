"""
命令模式实现

CQRS中的命令（Command）用于处理写操作
命令的特征：
- 表示用户意图
- 包含执行操作所需的数据
- 可以被验证
- 通过命令处理器执行
"""

import uuid
from abc import ABC, abstractmethod
from datetime import datetime
from typing import Any, TypeVar

from ..dto.base_dto import BaseDTO

T = TypeVar("T")


class Command(BaseDTO):
    """命令基类"""

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.command_id = kwargs.get("command_id", str(uuid.uuid4()))
        self.timestamp = kwargs.get("timestamp", datetime.now())
        self.user_id = kwargs.get("user_id")
        self.correlation_id = kwargs.get("correlation_id")

    def validate(self) -> list[str]:
        """验证命令"""
        errors = []

        # 基础验证
        if not self.command_id:
            errors.append("命令ID不能为空")

        # 子类可以重写添加特定验证
        return errors


class ICommandHandler[T](ABC):
    """命令处理器接口"""

    @abstractmethod
    async def handle(self, command: T) -> Any:
        """处理命令"""
        pass

    def can_handle(self, command: Command) -> bool:
        """检查是否能处理此命令"""
        return True


class BaseCommandHandler(ICommandHandler[T]):
    """命令处理器基类"""

    def __init__(self, logger=None, uow_manager=None):
        self.logger = logger
        self.uow_manager = uow_manager

    async def handle(self, command: T) -> Any:
        """处理命令"""
        # 验证命令
        errors = command.validate()
        if errors:
            raise ValueError(f"命令验证失败: {', '.join(errors)}")

        if self.logger:
            self.logger.info(
                f"处理命令: {command.__class__.__name__}", command_id=command.command_id
            )

        try:
            # 执行业务逻辑
            result = await self.execute(command)

            if self.logger:
                self.logger.info(
                    f"命令处理完成: {command.__class__.__name__}",
                    command_id=command.command_id,
                )

            return result

        except Exception as e:
            if self.logger:
                self.logger.error(
                    f"命令处理失败: {command.__class__.__name__}",
                    exception=e,
                    command_id=command.command_id,
                )
            raise

    @abstractmethod
    async def execute(self, command: T) -> Any:
        """执行命令的业务逻辑"""
        pass


class CommandBus:
    """命令总线"""

    def __init__(self):
        self._handlers: dict[type, ICommandHandler] = {}
        self._middleware: list[callable] = []

    def register_handler(self, command_type: type, handler: ICommandHandler) -> None:
        """注册命令处理器"""
        self._handlers[command_type] = handler

    def add_middleware(self, middleware: callable) -> None:
        """添加中间件"""
        self._middleware.append(middleware)

    async def send(self, command: Command) -> Any:
        """发送命令"""
        command_type = type(command)

        if command_type not in self._handlers:
            raise ValueError(f"未找到命令类型 {command_type} 的处理器")

        handler = self._handlers[command_type]

        if not handler.can_handle(command):
            raise ValueError(f"处理器无法处理命令: {command_type}")

        # 应用中间件
        result = await self._apply_middleware(command, handler)

        return result

    async def _apply_middleware(
        self, command: Command, handler: ICommandHandler
    ) -> Any:
        """应用中间件"""
        if not self._middleware:
            return await handler.handle(command)

        # 构建中间件链
        async def pipeline(cmd: Command) -> Any:
            return await handler.handle(cmd)

        # 倒序应用中间件
        for middleware in reversed(self._middleware):
            pipeline = self._wrap_with_middleware(middleware, pipeline)

        return await pipeline(command)

    def _wrap_with_middleware(
        self, middleware: callable, next_handler: callable
    ) -> callable:
        """包装中间件"""

        async def wrapper(command: Command) -> Any:
            return await middleware(command, next_handler)

        return wrapper


# 预定义的命令中间件


class LoggingMiddleware:
    """日志中间件"""

    def __init__(self, logger):
        self.logger = logger

    async def __call__(self, command: Command, next_handler: callable) -> Any:
        """执行中间件"""
        start_time = datetime.now()

        self.logger.info(
            f"开始处理命令: {command.__class__.__name__}", command_id=command.command_id
        )

        try:
            result = await next_handler(command)

            duration = (datetime.now() - start_time).total_seconds()
            self.logger.info(
                f"命令处理成功: {command.__class__.__name__}",
                command_id=command.command_id,
                duration=duration,
            )

            return result

        except Exception as e:
            duration = (datetime.now() - start_time).total_seconds()
            self.logger.error(
                f"命令处理失败: {command.__class__.__name__}",
                exception=e,
                command_id=command.command_id,
                duration=duration,
            )
            raise


class ValidationMiddleware:
    """验证中间件"""

    async def __call__(self, command: Command, next_handler: callable) -> Any:
        """执行验证"""
        errors = command.validate()
        if errors:
            raise ValueError(f"命令验证失败: {', '.join(errors)}")

        return await next_handler(command)


class TransactionMiddleware:
    """事务中间件"""

    def __init__(self, uow_manager):
        self.uow_manager = uow_manager

    async def __call__(self, command: Command, next_handler: callable) -> Any:
        """在事务中执行命令"""
        async with self.uow_manager.transaction():
            return await next_handler(command)


# 示例命令实现


class CreateEntityCommand(Command):
    """创建实体命令"""

    def __init__(self, entity_data: dict[str, Any], **kwargs):
        super().__init__(**kwargs)
        self.entity_data = entity_data

    def validate(self) -> list[str]:
        """验证命令"""
        errors = super().validate()

        if not self.entity_data:
            errors.append("实体数据不能为空")

        return errors


class UpdateEntityCommand(Command):
    """更新实体命令"""

    def __init__(self, entity_id: str, entity_data: dict[str, Any], **kwargs):
        super().__init__(**kwargs)
        self.entity_id = entity_id
        self.entity_data = entity_data

    def validate(self) -> list[str]:
        """验证命令"""
        errors = super().validate()

        if not self.entity_id:
            errors.append("实体ID不能为空")
        if not self.entity_data:
            errors.append("实体数据不能为空")

        return errors


class DeleteEntityCommand(Command):
    """删除实体命令"""

    def __init__(self, entity_id: str, **kwargs):
        super().__init__(**kwargs)
        self.entity_id = entity_id

    def validate(self) -> list[str]:
        """验证命令"""
        errors = super().validate()

        if not self.entity_id:
            errors.append("实体ID不能为空")

        return errors
