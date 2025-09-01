"""
CQRS命令基类和命令总线

实现命令模式的基础架构，用于处理写操作
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from typing import Any, TypeVar

from packages.core.framework.events import EventBus
from packages.core.framework.logging import get_logger

logger = get_logger(__name__)

# 泛型类型变量
TCommand = TypeVar("TCommand", bound="BaseCommand")
TResult = TypeVar("TResult")


class CommandStatus(Enum):
    """命令执行状态"""

    PENDING = "pending"
    EXECUTING = "executing"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


@dataclass
class CommandResult[TResult]:
    """命令执行结果"""

    success: bool
    result: TResult | None = None
    error_message: str | None = None
    error_code: str | None = None
    execution_time_ms: int | None = None
    metadata: dict[str, Any] = None

    def __post_init__(self):
        if self.metadata is None:
            self.metadata = {}


class BaseCommand(ABC):
    """命令基类"""

    def __init__(
        self, command_id: str = None, user_id: str = None, correlation_id: str = None
    ):
        self.command_id = command_id or self._generate_command_id()
        self.user_id = user_id
        self.correlation_id = correlation_id
        self.created_at = datetime.utcnow()
        self.status = CommandStatus.PENDING

    def _generate_command_id(self) -> str:
        """生成唯一的命令ID"""
        import uuid

        return f"cmd_{uuid.uuid4().hex[:8]}"

    @abstractmethod
    def validate(self) -> list[str]:
        """验证命令参数，返回错误列表"""
        pass

    def get_command_type(self) -> str:
        """获取命令类型名称"""
        return self.__class__.__name__


class BaseCommandHandler[TCommand: "BaseCommand", TResult](ABC):
    """命令处理器基类"""

    def __init__(self):
        self._logger = get_logger(f"{__name__}.{self.__class__.__name__}")

    @abstractmethod
    async def handle(self, command: TCommand) -> CommandResult[TResult]:
        """处理命令"""
        pass

    @abstractmethod
    def can_handle(self, command: BaseCommand) -> bool:
        """检查是否能处理此命令"""
        pass

    async def _validate_command(self, command: TCommand) -> list[str]:
        """验证命令"""
        try:
            return command.validate()
        except Exception as e:
            return [f"命令验证失败: {str(e)}"]

    async def _create_success_result(
        self, result: TResult, execution_time_ms: int, metadata: dict[str, Any] = None
    ) -> CommandResult[TResult]:
        """创建成功结果"""
        return CommandResult(
            success=True,
            result=result,
            execution_time_ms=execution_time_ms,
            metadata=metadata or {},
        )

    async def _create_error_result(
        self,
        error_message: str,
        error_code: str = None,
        execution_time_ms: int = None,
        metadata: dict[str, Any] = None,
    ) -> CommandResult[TResult]:
        """创建错误结果"""
        return CommandResult(
            success=False,
            error_message=error_message,
            error_code=error_code,
            execution_time_ms=execution_time_ms,
            metadata=metadata or {},
        )


class CommandBus:
    """命令总线"""

    def __init__(self, event_bus: EventBus | None = None):
        self._handlers: dict[type[BaseCommand], BaseCommandHandler] = {}
        self._middleware: list[CommandMiddleware] = []
        self._event_bus = event_bus
        self._logger = get_logger(__name__ + ".CommandBus")

    def register_handler(
        self, command_type: type[TCommand], handler: BaseCommandHandler[TCommand, Any]
    ):
        """注册命令处理器"""
        if command_type in self._handlers:
            old_handler = self._handlers[command_type]
            self._logger.warning(
                f"命令处理器被覆盖: {command_type.__name__} "
                f"{old_handler.__class__.__name__} -> {handler.__class__.__name__}"
            )

        self._handlers[command_type] = handler
        self._logger.info(
            f"注册命令处理器: {command_type.__name__} -> {handler.__class__.__name__}"
        )

    def add_middleware(self, middleware: "CommandMiddleware"):
        """添加中间件"""
        self._middleware.append(middleware)
        self._logger.info(f"添加命令中间件: {middleware.__class__.__name__}")

    async def execute(self, command: BaseCommand) -> CommandResult:
        """执行命令"""
        start_time = datetime.utcnow()
        command.status = CommandStatus.EXECUTING

        try:
            self._logger.info(
                f"开始执行命令: {command.get_command_type()} (ID: {command.command_id})"
            )

            # 查找处理器
            handler = self._find_handler(command)
            if not handler:
                error_msg = f"未找到命令处理器: {command.get_command_type()}"
                self._logger.error(error_msg)
                command.status = CommandStatus.FAILED
                return CommandResult(
                    success=False,
                    error_message=error_msg,
                    error_code="HANDLER_NOT_FOUND",
                )

            # 执行中间件（前置处理）
            for middleware in self._middleware:
                try:
                    await middleware.before_execute(command)
                except Exception as e:
                    error_msg = f"中间件前置处理失败: {str(e)}"
                    self._logger.error(error_msg)
                    command.status = CommandStatus.FAILED
                    return CommandResult(
                        success=False,
                        error_message=error_msg,
                        error_code="MIDDLEWARE_ERROR",
                    )

            # 执行命令
            result = await handler.handle(command)

            # 更新状态
            if result.success:
                command.status = CommandStatus.COMPLETED
            else:
                command.status = CommandStatus.FAILED

            # 计算执行时间
            end_time = datetime.utcnow()
            execution_time_ms = int((end_time - start_time).total_seconds() * 1000)
            if result.execution_time_ms is None:
                result.execution_time_ms = execution_time_ms

            # 执行中间件（后置处理）
            for middleware in reversed(self._middleware):
                try:
                    await middleware.after_execute(command, result)
                except Exception as e:
                    self._logger.warning(f"中间件后置处理失败: {str(e)}")

            # 发布事件
            if self._event_bus and result.success:
                await self._publish_command_completed_event(command, result)

            self._logger.info(
                f"命令执行完成: {command.get_command_type()} "
                f"(ID: {command.command_id}, 耗时: {execution_time_ms}ms, 成功: {result.success})"
            )

            return result

        except Exception as e:
            error_msg = f"命令执行异常: {str(e)}"
            self._logger.error(
                f"命令执行异常 {command.get_command_type()}: {error_msg}"
            )
            command.status = CommandStatus.FAILED

            end_time = datetime.utcnow()
            execution_time_ms = int((end_time - start_time).total_seconds() * 1000)

            return CommandResult(
                success=False,
                error_message=error_msg,
                error_code="EXECUTION_ERROR",
                execution_time_ms=execution_time_ms,
            )

    def _find_handler(self, command: BaseCommand) -> BaseCommandHandler | None:
        """查找命令处理器"""
        command_type = type(command)

        # 精确匹配
        if command_type in self._handlers:
            return self._handlers[command_type]

        # 检查基类匹配
        for registered_type, handler in self._handlers.items():
            if isinstance(command, registered_type):
                return handler

        # 检查处理器的can_handle方法
        for handler in self._handlers.values():
            if handler.can_handle(command):
                return handler

        return None

    async def _publish_command_completed_event(
        self, command: BaseCommand, result: CommandResult
    ):
        """发布命令完成事件"""
        try:
            from packages.core.framework.events import DomainEvent

            class CommandCompletedEvent(DomainEvent):
                def __init__(self, command_id: str, command_type: str, success: bool):
                    super().__init__()
                    self.command_id = command_id
                    self.command_type = command_type
                    self.success = success

            event = CommandCompletedEvent(
                command_id=command.command_id,
                command_type=command.get_command_type(),
                success=result.success,
            )

            await self._event_bus.publish(event)

        except Exception as e:
            self._logger.warning(f"发布命令完成事件失败: {str(e)}")

    def get_registered_handlers(self) -> dict[type[BaseCommand], BaseCommandHandler]:
        """获取已注册的处理器"""
        return self._handlers.copy()


class CommandMiddleware(ABC):
    """命令中间件基类"""

    @abstractmethod
    async def before_execute(self, command: BaseCommand):
        """命令执行前处理"""
        pass

    @abstractmethod
    async def after_execute(self, command: BaseCommand, result: CommandResult):
        """命令执行后处理"""
        pass


class LoggingMiddleware(CommandMiddleware):
    """日志中间件"""

    def __init__(self):
        self._logger = get_logger(__name__ + ".LoggingMiddleware")

    async def before_execute(self, command: BaseCommand):
        """记录命令开始执行"""
        self._logger.debug(
            f"命令开始执行: {command.get_command_type()} "
            f"(ID: {command.command_id}, 用户: {command.user_id})"
        )

    async def after_execute(self, command: BaseCommand, result: CommandResult):
        """记录命令执行结果"""
        level = "info" if result.success else "error"
        message = (
            f"命令执行结束: {command.get_command_type()} "
            f"(ID: {command.command_id}, 成功: {result.success}"
        )

        if result.execution_time_ms:
            message += f", 耗时: {result.execution_time_ms}ms"

        if not result.success and result.error_message:
            message += f", 错误: {result.error_message}"

        message += ")"

        if level == "info":
            self._logger.info(message)
        else:
            self._logger.error(message)


class ValidationMiddleware(CommandMiddleware):
    """验证中间件"""

    def __init__(self):
        self._logger = get_logger(__name__ + ".ValidationMiddleware")

    async def before_execute(self, command: BaseCommand):
        """执行命令验证"""
        try:
            validation_errors = command.validate()
            if validation_errors:
                error_message = f"命令验证失败: {'; '.join(validation_errors)}"
                self._logger.error(
                    f"{command.get_command_type()} 验证失败: {validation_errors}"
                )
                raise ValueError(error_message)
        except Exception as e:
            if not isinstance(e, ValueError):
                error_message = f"命令验证异常: {str(e)}"
                self._logger.error(error_message)
                raise ValueError(error_message)
            raise

    async def after_execute(self, command: BaseCommand, result: CommandResult):
        """验证执行后无需处理"""
        pass


# 全局命令总线实例
command_bus = CommandBus()
