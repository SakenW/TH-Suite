"""
日志管理器

统一的日志接口和实现
"""

import threading
import traceback
from abc import ABC, abstractmethod
from datetime import datetime
from enum import Enum
from typing import Any


class LogLevel(Enum):
    """日志级别"""

    TRACE = 0
    DEBUG = 10
    INFO = 20
    WARNING = 30
    ERROR = 40
    CRITICAL = 50


class LogRecord:
    """日志记录"""

    def __init__(
        self,
        level: LogLevel,
        message: str,
        logger_name: str = "",
        timestamp: datetime | None = None,
        extra: dict[str, Any] | None = None,
        exception: Exception | None = None,
    ):
        self.level = level
        self.message = message
        self.logger_name = logger_name
        self.timestamp = timestamp or datetime.now()
        self.extra = extra or {}
        self.exception = exception
        self.thread_id = threading.get_ident()
        self.thread_name = threading.current_thread().name

        if exception:
            self.exception_text = traceback.format_exception(
                type(exception), exception, exception.__traceback__
            )
        else:
            self.exception_text = None


class ILogFormatter(ABC):
    """日志格式化器接口"""

    @abstractmethod
    def format(self, record: LogRecord) -> str:
        """格式化日志记录"""
        pass


class ILogHandler(ABC):
    """日志处理器接口"""

    @abstractmethod
    def handle(self, record: LogRecord) -> None:
        """处理日志记录"""
        pass

    @abstractmethod
    def set_formatter(self, formatter: ILogFormatter) -> None:
        """设置格式化器"""
        pass


class ILogger(ABC):
    """日志器接口"""

    @abstractmethod
    def trace(self, message: str, **kwargs) -> None:
        """记录TRACE级别日志"""
        pass

    @abstractmethod
    def debug(self, message: str, **kwargs) -> None:
        """记录DEBUG级别日志"""
        pass

    @abstractmethod
    def info(self, message: str, **kwargs) -> None:
        """记录INFO级别日志"""
        pass

    @abstractmethod
    def warning(self, message: str, **kwargs) -> None:
        """记录WARNING级别日志"""
        pass

    @abstractmethod
    def error(self, message: str, exception: Exception | None = None, **kwargs) -> None:
        """记录ERROR级别日志"""
        pass

    @abstractmethod
    def critical(
        self, message: str, exception: Exception | None = None, **kwargs
    ) -> None:
        """记录CRITICAL级别日志"""
        pass

    @abstractmethod
    def log(self, level: LogLevel, message: str, **kwargs) -> None:
        """记录指定级别日志"""
        pass


class Logger(ILogger):
    """日志器实现"""

    def __init__(self, name: str = "", min_level: LogLevel = LogLevel.INFO):
        self.name = name
        self.min_level = min_level
        self.handlers: list[ILogHandler] = []
        self._lock = threading.RLock()

    def add_handler(self, handler: ILogHandler) -> "Logger":
        """添加日志处理器"""
        with self._lock:
            self.handlers.append(handler)
        return self

    def remove_handler(self, handler: ILogHandler) -> "Logger":
        """移除日志处理器"""
        with self._lock:
            if handler in self.handlers:
                self.handlers.remove(handler)
        return self

    def set_level(self, level: LogLevel) -> "Logger":
        """设置最小日志级别"""
        self.min_level = level
        return self

    def trace(self, message: str, **kwargs) -> None:
        """记录TRACE级别日志"""
        self.log(LogLevel.TRACE, message, **kwargs)

    def debug(self, message: str, **kwargs) -> None:
        """记录DEBUG级别日志"""
        self.log(LogLevel.DEBUG, message, **kwargs)

    def info(self, message: str, **kwargs) -> None:
        """记录INFO级别日志"""
        self.log(LogLevel.INFO, message, **kwargs)

    def warning(self, message: str, **kwargs) -> None:
        """记录WARNING级别日志"""
        self.log(LogLevel.WARNING, message, **kwargs)

    def error(self, message: str, exception: Exception | None = None, **kwargs) -> None:
        """记录ERROR级别日志"""
        self.log(LogLevel.ERROR, message, exception=exception, **kwargs)

    def critical(
        self, message: str, exception: Exception | None = None, **kwargs
    ) -> None:
        """记录CRITICAL级别日志"""
        self.log(LogLevel.CRITICAL, message, exception=exception, **kwargs)

    def log(
        self,
        level: LogLevel,
        message: str,
        exception: Exception | None = None,
        **kwargs,
    ) -> None:
        """记录指定级别日志"""
        if level.value < self.min_level.value:
            return

        record = LogRecord(
            level=level,
            message=message,
            logger_name=self.name,
            extra=kwargs,
            exception=exception,
        )

        with self._lock:
            for handler in self.handlers:
                try:
                    handler.handle(record)
                except Exception as e:
                    # 避免日志处理器错误导致应用崩溃
                    print(f"日志处理器错误: {e}")

    def is_enabled_for(self, level: LogLevel) -> bool:
        """检查是否启用指定级别"""
        return level.value >= self.min_level.value


class LoggerFactory:
    """日志器工厂"""

    _loggers: dict[str, Logger] = {}
    _default_handlers: list[ILogHandler] = []
    _default_level: LogLevel = LogLevel.INFO
    _lock = threading.RLock()

    @classmethod
    def get_logger(cls, name: str = "") -> Logger:
        """获取日志器"""
        with cls._lock:
            if name not in cls._loggers:
                logger = Logger(name, cls._default_level)

                # 添加默认处理器
                for handler in cls._default_handlers:
                    logger.add_handler(handler)

                cls._loggers[name] = logger

            return cls._loggers[name]

    @classmethod
    def add_default_handler(cls, handler: ILogHandler) -> None:
        """添加默认处理器"""
        with cls._lock:
            cls._default_handlers.append(handler)

            # 为现有日志器添加处理器
            for logger in cls._loggers.values():
                logger.add_handler(handler)

    @classmethod
    def set_default_level(cls, level: LogLevel) -> None:
        """设置默认日志级别"""
        with cls._lock:
            cls._default_level = level

            # 更新现有日志器的级别
            for logger in cls._loggers.values():
                logger.set_level(level)

    @classmethod
    def clear_loggers(cls) -> None:
        """清除所有日志器"""
        with cls._lock:
            cls._loggers.clear()
