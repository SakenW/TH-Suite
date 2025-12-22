"""
文本格式化器

传统的文本格式日志格式化器
"""

from ..logger import ILogFormatter, LogRecord


class TextFormatter(ILogFormatter):
    """文本格式化器"""

    def __init__(
        self,
        format_string: str = "{timestamp} [{level:<8}] {logger}: {message}",
        timestamp_format: str = "%Y-%m-%d %H:%M:%S",
    ):
        self.format_string = format_string
        self.timestamp_format = timestamp_format

    def format(self, record: LogRecord) -> str:
        """格式化为文本"""
        try:
            formatted = self.format_string.format(
                timestamp=record.timestamp.strftime(self.timestamp_format),
                level=record.level.name,
                logger=record.logger_name or "root",
                message=record.message,
                thread_id=record.thread_id,
                thread_name=record.thread_name,
            )

            # 添加异常信息
            if record.exception and record.exception_text:
                formatted += "\n" + "".join(record.exception_text)

            # 添加额外字段
            if record.extra:
                extra_parts = [f"{k}={v}" for k, v in record.extra.items()]
                if extra_parts:
                    formatted += f" [{', '.join(extra_parts)}]"

            return formatted

        except Exception as e:
            # 如果格式化失败，返回简单格式
            return f"{record.timestamp} [{record.level.name}] {record.message} [FORMAT_ERROR: {e}]"
