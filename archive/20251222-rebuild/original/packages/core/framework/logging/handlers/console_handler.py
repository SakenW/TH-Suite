"""
控制台日志处理器

将日志输出到控制台
"""

import sys
from typing import TextIO

from ..formatters.text_formatter import TextFormatter
from ..logger import ILogFormatter, ILogHandler, LogLevel, LogRecord


class ConsoleHandler(ILogHandler):
    """控制台日志处理器"""

    def __init__(
        self,
        formatter: ILogFormatter | None = None,
        stream: TextIO | None = None,
        use_colors: bool = True,
    ):
        self.formatter = formatter or TextFormatter()
        self.stream = stream or sys.stdout
        self.use_colors = use_colors

        # ANSI颜色代码
        self.colors = {
            LogLevel.TRACE: "\033[36m",  # 青色
            LogLevel.DEBUG: "\033[32m",  # 绿色
            LogLevel.INFO: "\033[37m",  # 白色
            LogLevel.WARNING: "\033[33m",  # 黄色
            LogLevel.ERROR: "\033[31m",  # 红色
            LogLevel.CRITICAL: "\033[35m",  # 紫色
        }
        self.reset_color = "\033[0m"

    def handle(self, record: LogRecord) -> None:
        """处理日志记录"""
        try:
            formatted = self.formatter.format(record)

            if self.use_colors and record.level in self.colors:
                # 错误级别输出到stderr
                if record.level.value >= LogLevel.ERROR.value:
                    stream = sys.stderr
                else:
                    stream = self.stream

                # 添加颜色
                colored_message = (
                    f"{self.colors[record.level]}{formatted}{self.reset_color}"
                )
                stream.write(colored_message + "\n")
                stream.flush()
            else:
                # 无颜色输出
                if record.level.value >= LogLevel.ERROR.value:
                    sys.stderr.write(formatted + "\n")
                    sys.stderr.flush()
                else:
                    self.stream.write(formatted + "\n")
                    self.stream.flush()

        except Exception as e:
            # 避免日志处理器错误
            sys.stderr.write(f"ConsoleHandler error: {e}\n")
            sys.stderr.flush()

    def set_formatter(self, formatter: ILogFormatter) -> None:
        """设置格式化器"""
        self.formatter = formatter
