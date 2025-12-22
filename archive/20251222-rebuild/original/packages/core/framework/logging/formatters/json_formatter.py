"""
JSON格式化器

将日志记录格式化为JSON格式，便于结构化日志分析
"""

import json

from ..logger import ILogFormatter, LogRecord


class JsonFormatter(ILogFormatter):
    """JSON格式化器"""

    def __init__(
        self, include_extra: bool = True, timestamp_format: str = "%Y-%m-%d %H:%M:%S"
    ):
        self.include_extra = include_extra
        self.timestamp_format = timestamp_format

    def format(self, record: LogRecord) -> str:
        """格式化为JSON"""
        log_data = {
            "timestamp": record.timestamp.strftime(self.timestamp_format),
            "level": record.level.name,
            "logger": record.logger_name,
            "message": record.message,
            "thread_id": record.thread_id,
            "thread_name": record.thread_name,
        }

        # 添加额外字段
        if self.include_extra and record.extra:
            log_data["extra"] = record.extra

        # 添加异常信息
        if record.exception:
            log_data["exception"] = {
                "type": type(record.exception).__name__,
                "message": str(record.exception),
                "traceback": record.exception_text,
            }

        try:
            return json.dumps(log_data, ensure_ascii=False, separators=(",", ":"))
        except Exception:
            # 如果JSON序列化失败，返回简单格式
            return json.dumps(
                {
                    "timestamp": log_data["timestamp"],
                    "level": log_data["level"],
                    "message": str(record.message),
                    "error": "JSON serialization failed",
                },
                ensure_ascii=False,
            )
