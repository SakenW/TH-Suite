"""文件路径值对象"""

from pathlib import Path

from packages.core.data.models import ValueObject


class FilePath(ValueObject):
    """文件路径值对象"""

    def __init__(self, path: str):
        if not path:
            raise ValueError("文件路径不能为空")

        self._path = Path(path).resolve()  # 转换为绝对路径
        self._original = path

    @property
    def value(self) -> str:
        """返回原始路径字符串"""
        return self._original

    @property
    def resolved_path(self) -> Path:
        """返回解析后的Path对象"""
        return self._path

    @property
    def exists(self) -> bool:
        """检查路径是否存在"""
        return self._path.exists()

    @property
    def is_file(self) -> bool:
        """检查是否为文件"""
        return self._path.is_file()

    @property
    def is_directory(self) -> bool:
        """检查是否为目录"""
        return self._path.is_dir()

    @property
    def extension(self) -> str:
        """获取文件扩展名"""
        return self._path.suffix.lower()

    @property
    def name(self) -> str:
        """获取文件名"""
        return self._path.name

    @property
    def parent(self) -> "FilePath":
        """获取父目录"""
        return FilePath(str(self._path.parent))

    def __str__(self) -> str:
        return self._original

    def __eq__(self, other) -> bool:
        if not isinstance(other, FilePath):
            return False
        return self._path == other._path

    def __hash__(self) -> int:
        return hash(str(self._path))
