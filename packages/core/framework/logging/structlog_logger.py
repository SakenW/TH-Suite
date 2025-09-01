"""
Structlog 日志器包装器

基于 Trans-Hub 日志系统设计的日志器实现，提供与现有接口的兼容性。
同时利用 structlog + rich 的强大功能提供优美的控制台输出和结构化日志记录。
"""

import structlog

from .logger import ILogger
from .logger import LogLevel as FrameworkLogLevel
from .logging_config import LogLevel as StructLogLevel
from .logging_config import setup_logging


class StructLogLogger(ILogger):
    """基于 structlog 的日志器实现"""

    def __init__(self, name: str = ""):
        self.name = name
        self._logger = structlog.get_logger(name)

    @staticmethod
    def _convert_level(level: FrameworkLogLevel) -> StructLogLevel:
        """转换框架日志级别到 structlog 级别"""
        level_map = {
            FrameworkLogLevel.TRACE: "DEBUG",  # structlog 没有 TRACE，映射到 DEBUG
            FrameworkLogLevel.DEBUG: "DEBUG",
            FrameworkLogLevel.INFO: "INFO",
            FrameworkLogLevel.WARNING: "WARNING",
            FrameworkLogLevel.ERROR: "ERROR",
            FrameworkLogLevel.CRITICAL: "CRITICAL",
        }
        return level_map.get(level, "INFO")

    def trace(self, message: str, **kwargs) -> None:
        """记录TRACE级别日志"""
        self._logger.debug(message, **kwargs)

    def debug(self, message: str, **kwargs) -> None:
        """记录DEBUG级别日志"""
        self._logger.debug(message, **kwargs)

    def info(self, message: str, **kwargs) -> None:
        """记录INFO级别日志"""
        self._logger.info(message, **kwargs)

    def warning(self, message: str, **kwargs) -> None:
        """记录WARNING级别日志"""
        self._logger.warning(message, **kwargs)

    def error(self, message: str, exception: Exception | None = None, **kwargs) -> None:
        """记录ERROR级别日志"""
        if exception:
            kwargs["exception"] = exception
        self._logger.error(message, **kwargs)

    def critical(
        self, message: str, exception: Exception | None = None, **kwargs
    ) -> None:
        """记录CRITICAL级别日志"""
        if exception:
            kwargs["exception"] = exception
        self._logger.critical(message, **kwargs)

    def log(
        self,
        level: FrameworkLogLevel,
        message: str,
        exception: Exception | None = None,
        **kwargs,
    ) -> None:
        """记录指定级别日志"""
        if exception:
            kwargs["exception"] = exception

        struct_level = self._convert_level(level)

        # 根据级别调用对应的方法
        if struct_level == "DEBUG":
            self._logger.debug(message, **kwargs)
        elif struct_level == "INFO":
            self._logger.info(message, **kwargs)
        elif struct_level == "WARNING":
            self._logger.warning(message, **kwargs)
        elif struct_level == "ERROR":
            self._logger.error(message, **kwargs)
        elif struct_level == "CRITICAL":
            self._logger.critical(message, **kwargs)

    def bind(self, **kwargs) -> "StructLogLogger":
        """绑定上下文信息，返回新的日志器实例"""
        new_logger = StructLogLogger(self.name)
        new_logger._logger = self._logger.bind(**kwargs)
        return new_logger


class StructLogFactory:
    """Structlog 日志器工厂"""

    _initialized = False

    @classmethod
    def initialize_logging(
        cls,
        log_level: StructLogLevel = "INFO",
        log_format: str = "console",
        service: str = "th-suite",
    ) -> None:
        """初始化 structlog 日志系统"""
        if not cls._initialized:
            setup_logging(
                log_level=log_level,
                log_format=log_format,
                service=service,
                show_timestamp=True,
                show_logger_name=True,
            )
            cls._initialized = True

    @classmethod
    def get_logger(cls, name: str = "") -> StructLogLogger:
        """获取 structlog 日志器"""
        if not cls._initialized:
            cls.initialize_logging()

        return StructLogLogger(name)

    @classmethod
    def reset(cls) -> None:
        """重置工厂状态（主要用于测试）"""
        cls._initialized = False
