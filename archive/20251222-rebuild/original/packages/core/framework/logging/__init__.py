"""
日志框架

提供统一的日志接口和实现：
- 抽象日志接口（ILogger）
- 多种日志处理器（控制台、文件、网络等）
- 日志格式化器
- 结构化日志支持（基于 structlog + rich）
- Trans-Hub 风格的美观日志输出
"""

from .formatters.json_formatter import JsonFormatter
from .formatters.text_formatter import TextFormatter
from .handlers.console_handler import ConsoleHandler
from .handlers.file_handler import FileHandler
from .logger import ILogger, Logger, LogLevel
from .logging_config import HybridPanelRenderer, setup_logging
from .structlog_logger import StructLogFactory, StructLogLogger


# Convenience function for getting a logger
def get_logger(name: str = "") -> StructLogLogger:
    """获取结构化日志器的便捷函数"""
    return StructLogFactory.get_logger(name)


__all__ = [
    "ILogger",
    "Logger",
    "LogLevel",
    "JsonFormatter",
    "TextFormatter",
    "ConsoleHandler",
    "FileHandler",
    "StructLogLogger",
    "StructLogFactory",
    "setup_logging",
    "HybridPanelRenderer",
    "get_logger",
]
