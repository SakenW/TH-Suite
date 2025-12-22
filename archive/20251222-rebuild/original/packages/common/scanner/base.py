"""
通用扫描框架基类
提供文件扫描的抽象接口和基础实现
"""

import hashlib
import json
import logging
from abc import ABC, abstractmethod
from collections.abc import Callable, Generator
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)


@dataclass
class ScanResult:
    """扫描结果"""

    path: str
    file_type: str
    size: int
    modified_time: datetime
    content_hash: str
    metadata: dict[str, Any] = field(default_factory=dict)
    errors: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        """转换为字典"""
        return {
            "path": self.path,
            "file_type": self.file_type,
            "size": self.size,
            "modified_time": self.modified_time.isoformat(),
            "content_hash": self.content_hash,
            "metadata": self.metadata,
            "errors": self.errors,
        }


@dataclass
class ScanProgress:
    """扫描进度"""

    total_files: int = 0
    processed_files: int = 0
    failed_files: int = 0
    current_file: str | None = None
    start_time: datetime = field(default_factory=datetime.now)

    @property
    def progress_percentage(self) -> float:
        """进度百分比"""
        if self.total_files == 0:
            return 0.0
        return (self.processed_files / self.total_files) * 100

    @property
    def elapsed_time(self) -> float:
        """已用时间（秒）"""
        return (datetime.now() - self.start_time).total_seconds()

    @property
    def estimated_remaining_time(self) -> float | None:
        """预估剩余时间（秒）"""
        if self.processed_files == 0:
            return None

        rate = self.processed_files / self.elapsed_time
        remaining_files = self.total_files - self.processed_files
        return remaining_files / rate if rate > 0 else None


class BaseScanner(ABC):
    """基础扫描器抽象类"""

    def __init__(
        self,
        root_path: str | Path,
        include_patterns: list[str] | None = None,
        exclude_patterns: list[str] | None = None,
        max_workers: int = 4,
    ):
        self.root_path = Path(root_path)
        self.include_patterns = include_patterns or ["*"]
        self.exclude_patterns = exclude_patterns or []
        self.max_workers = max_workers
        self.progress = ScanProgress()
        self._progress_callbacks: list[Callable[[ScanProgress], None]] = []

    def add_progress_callback(self, callback: Callable[[ScanProgress], None]):
        """添加进度回调"""
        self._progress_callbacks.append(callback)

    def _notify_progress(self):
        """通知进度更新"""
        for callback in self._progress_callbacks:
            try:
                callback(self.progress)
            except Exception as e:
                logger.error(f"Progress callback error: {e}")

    def _should_scan_file(self, file_path: Path) -> bool:
        """判断是否应该扫描文件"""
        # 检查排除模式
        for pattern in self.exclude_patterns:
            if file_path.match(pattern):
                return False

        # 检查包含模式
        for pattern in self.include_patterns:
            if file_path.match(pattern):
                return True

        return False

    def _calculate_file_hash(self, file_path: Path, algorithm: str = "sha256") -> str:
        """计算文件哈希"""
        hash_obj = hashlib.new(algorithm)

        try:
            with open(file_path, "rb") as f:
                for chunk in iter(lambda: f.read(8192), b""):
                    hash_obj.update(chunk)
            return hash_obj.hexdigest()
        except Exception as e:
            logger.error(f"Failed to calculate hash for {file_path}: {e}")
            return ""

    def _get_file_metadata(self, file_path: Path) -> dict[str, Any]:
        """获取文件元数据"""
        try:
            stat = file_path.stat()
            return {
                "size": stat.st_size,
                "modified_time": datetime.fromtimestamp(stat.st_mtime),
                "created_time": datetime.fromtimestamp(stat.st_ctime),
                "is_symlink": file_path.is_symlink(),
                "absolute_path": str(file_path.absolute()),
            }
        except Exception as e:
            logger.error(f"Failed to get metadata for {file_path}: {e}")
            return {}

    @abstractmethod
    def scan_file(self, file_path: Path) -> ScanResult | None:
        """扫描单个文件（子类实现）"""
        pass

    def scan(self) -> Generator[ScanResult, None, None]:
        """执行扫描"""
        # 收集所有需要扫描的文件
        files_to_scan = self._collect_files()
        self.progress.total_files = len(files_to_scan)
        self.progress.start_time = datetime.now()

        logger.info(f"Starting scan of {len(files_to_scan)} files")

        # 并行扫描
        with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            future_to_file = {
                executor.submit(self._scan_file_safe, file_path): file_path
                for file_path in files_to_scan
            }

            for future in as_completed(future_to_file):
                file_path = future_to_file[future]
                self.progress.current_file = str(file_path)

                try:
                    result = future.result()
                    if result:
                        self.progress.processed_files += 1
                        yield result
                    else:
                        self.progress.failed_files += 1
                except Exception as e:
                    logger.error(f"Failed to scan {file_path}: {e}")
                    self.progress.failed_files += 1

                self._notify_progress()

        logger.info(
            f"Scan completed: {self.progress.processed_files} processed, "
            f"{self.progress.failed_files} failed"
        )

    def _scan_file_safe(self, file_path: Path) -> ScanResult | None:
        """安全地扫描文件（捕获异常）"""
        try:
            return self.scan_file(file_path)
        except Exception as e:
            logger.error(f"Error scanning {file_path}: {e}")
            return None

    def _collect_files(self) -> list[Path]:
        """收集需要扫描的文件"""
        files = []

        if self.root_path.is_file():
            # 单个文件
            if self._should_scan_file(self.root_path):
                files.append(self.root_path)
        else:
            # 目录递归扫描
            for pattern in self.include_patterns:
                for file_path in self.root_path.rglob(pattern):
                    if file_path.is_file() and self._should_scan_file(file_path):
                        files.append(file_path)

        return files


class IncrementalScanner(BaseScanner):
    """增量扫描器"""

    def __init__(self, root_path: str | Path, cache_path: str | Path, **kwargs):
        super().__init__(root_path, **kwargs)
        self.cache_path = Path(cache_path)
        self._cache = self._load_cache()

    def _load_cache(self) -> dict[str, dict[str, Any]]:
        """加载缓存"""
        if self.cache_path.exists():
            try:
                with open(self.cache_path) as f:
                    return json.load(f)
            except Exception as e:
                logger.error(f"Failed to load cache: {e}")
        return {}

    def _save_cache(self):
        """保存缓存"""
        try:
            self.cache_path.parent.mkdir(parents=True, exist_ok=True)
            with open(self.cache_path, "w") as f:
                json.dump(self._cache, f, indent=2)
        except Exception as e:
            logger.error(f"Failed to save cache: {e}")

    def _is_file_changed(self, file_path: Path) -> bool:
        """检查文件是否变化"""
        path_str = str(file_path)

        if path_str not in self._cache:
            return True

        cached_info = self._cache[path_str]

        try:
            stat = file_path.stat()
            # 比较修改时间和大小
            if stat.st_mtime != cached_info.get(
                "mtime"
            ) or stat.st_size != cached_info.get("size"):
                return True
        except Exception:
            return True

        return False

    def scan_file(self, file_path: Path) -> ScanResult | None:
        """扫描文件（仅扫描变化的文件）"""
        if not self._is_file_changed(file_path):
            logger.debug(f"Skipping unchanged file: {file_path}")
            return None

        # 执行实际扫描
        result = self._do_scan_file(file_path)

        if result:
            # 更新缓存
            stat = file_path.stat()
            self._cache[str(file_path)] = {
                "mtime": stat.st_mtime,
                "size": stat.st_size,
                "hash": result.content_hash,
                "scanned_at": datetime.now().isoformat(),
            }

        return result

    @abstractmethod
    def _do_scan_file(self, file_path: Path) -> ScanResult | None:
        """实际执行文件扫描（子类实现）"""
        pass

    def scan(self) -> Generator[ScanResult, None, None]:
        """执行增量扫描"""
        try:
            # 执行扫描
            yield from super().scan()
        finally:
            # 保存缓存
            self._save_cache()


class BatchScanner:
    """批量扫描器（组合多个扫描器）"""

    def __init__(self, scanners: list[BaseScanner]):
        self.scanners = scanners

    def scan(self) -> Generator[ScanResult, None, None]:
        """执行批量扫描"""
        for scanner in self.scanners:
            logger.info(f"Running scanner: {scanner.__class__.__name__}")
            yield from scanner.scan()
