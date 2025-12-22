"""
文件日志处理器

将日志输出到文件，支持日志轮转
"""

from pathlib import Path

from ..formatters.text_formatter import TextFormatter
from ..logger import ILogFormatter, ILogHandler, LogRecord


class FileHandler(ILogHandler):
    """文件日志处理器"""

    def __init__(
        self,
        file_path: Path,
        formatter: ILogFormatter | None = None,
        max_size: int = 10 * 1024 * 1024,  # 10MB
        backup_count: int = 5,
        encoding: str = "utf-8",
    ):
        self.file_path = Path(file_path)
        self.formatter = formatter or TextFormatter()
        self.max_size = max_size
        self.backup_count = backup_count
        self.encoding = encoding

        # 确保目录存在
        self.file_path.parent.mkdir(parents=True, exist_ok=True)

    def handle(self, record: LogRecord) -> None:
        """处理日志记录"""
        try:
            # 检查是否需要轮转
            self._rotate_if_needed()

            formatted = self.formatter.format(record)

            with open(self.file_path, "a", encoding=self.encoding) as f:
                f.write(formatted + "\n")
                f.flush()

        except Exception as e:
            # 避免日志处理器错误
            print(f"FileHandler error: {e}")

    def set_formatter(self, formatter: ILogFormatter) -> None:
        """设置格式化器"""
        self.formatter = formatter

    def _rotate_if_needed(self) -> None:
        """检查并执行日志轮转"""
        if not self.file_path.exists():
            return

        # 检查文件大小
        if self.file_path.stat().st_size >= self.max_size:
            self._rotate_files()

    def _rotate_files(self) -> None:
        """执行日志文件轮转"""
        try:
            # 删除最老的备份文件
            oldest_backup = self.file_path.with_suffix(
                f"{self.file_path.suffix}.{self.backup_count}"
            )
            if oldest_backup.exists():
                oldest_backup.unlink()

            # 轮转备份文件
            for i in range(self.backup_count, 0, -1):
                src = self.file_path.with_suffix(f"{self.file_path.suffix}.{i}")
                dst = self.file_path.with_suffix(f"{self.file_path.suffix}.{i + 1}")

                if src.exists():
                    src.rename(dst)

            # 将当前文件重命名为.1
            if self.file_path.exists():
                backup_path = self.file_path.with_suffix(f"{self.file_path.suffix}.1")
                self.file_path.rename(backup_path)

        except Exception as e:
            print(f"日志轮转失败: {e}")
