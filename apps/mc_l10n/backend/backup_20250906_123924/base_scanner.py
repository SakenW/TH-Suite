"""
基础文件扫描器

定义所有扫描器的通用接口和基础功能
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any

from packages.core.framework.logging import get_logger

from domain.models.enums import FileType, ScanStatus
from domain.models.value_objects.file_path import FilePath
from domain.models.value_objects.language_code import LanguageCode
from domain.models.value_objects.mod_id import ModId

logger = get_logger(__name__)


@dataclass
class ScanResult:
    """扫描结果数据类"""

    file_path: FilePath
    scan_status: ScanStatus
    discovered_files: list["DiscoveredFile"]
    metadata: dict[str, Any]
    errors: list[str]
    scan_duration_ms: int
    scanned_at: datetime

    def __post_init__(self):
        if self.discovered_files is None:
            self.discovered_files = []
        if self.metadata is None:
            self.metadata = {}
        if self.errors is None:
            self.errors = []


@dataclass
class DiscoveredFile:
    """发现的文件信息"""

    relative_path: str
    full_path: str
    file_type: FileType
    file_size: int
    language_code: LanguageCode | None = None
    mod_id: ModId | None = None
    is_language_file: bool = False
    last_modified: datetime | None = None

    def __post_init__(self):
        if self.last_modified is None:
            self.last_modified = datetime.utcnow()


class ScanFilter:
    """扫描过滤器"""

    def __init__(self):
        self.include_patterns: set[str] = set()
        self.exclude_patterns: set[str] = set()
        self.file_types: set[FileType] = set()
        self.languages: set[LanguageCode] = set()
        self.max_file_size: int | None = None
        self.min_file_size: int | None = None

    def should_include_file(self, file_info: DiscoveredFile) -> bool:
        """判断文件是否应该被包含"""
        # 文件大小过滤
        if self.max_file_size and file_info.file_size > self.max_file_size:
            return False
        if self.min_file_size and file_info.file_size < self.min_file_size:
            return False

        # 文件类型过滤
        if self.file_types and file_info.file_type not in self.file_types:
            return False

        # 语言过滤
        if self.languages and file_info.language_code:
            if file_info.language_code not in self.languages:
                return False

        # 路径模式过滤
        relative_path = file_info.relative_path

        # 排除模式检查
        for exclude_pattern in self.exclude_patterns:
            if self._matches_pattern(relative_path, exclude_pattern):
                return False

        # 包含模式检查（如果有包含模式，则必须匹配其中一个）
        if self.include_patterns:
            for include_pattern in self.include_patterns:
                if self._matches_pattern(relative_path, include_pattern):
                    return True
            return False  # 如果有包含模式但都不匹配

        return True

    def _matches_pattern(self, path: str, pattern: str) -> bool:
        """检查路径是否匹配模式（支持简单的通配符）"""
        import fnmatch

        return fnmatch.fnmatch(path.lower(), pattern.lower())


class BaseScanner(ABC):
    """基础扫描器抽象类"""

    def __init__(self, scanner_name: str):
        self._scanner_name = scanner_name
        self._logger = get_logger(f"{__name__}.{scanner_name}")

    @property
    def scanner_name(self) -> str:
        return self._scanner_name

    @abstractmethod
    async def can_handle(self, file_path: FilePath) -> bool:
        """检查扫描器是否能处理指定的文件/路径"""
        pass

    @abstractmethod
    async def scan(
        self, file_path: FilePath, scan_filter: ScanFilter | None = None
    ) -> ScanResult:
        """执行扫描操作"""
        pass

    async def _create_scan_result(
        self,
        file_path: FilePath,
        status: ScanStatus,
        discovered_files: list[DiscoveredFile],
        metadata: dict[str, Any],
        errors: list[str],
        start_time: datetime,
    ) -> ScanResult:
        """创建扫描结果"""
        end_time = datetime.utcnow()
        duration_ms = int((end_time - start_time).total_seconds() * 1000)

        return ScanResult(
            file_path=file_path,
            scan_status=status,
            discovered_files=discovered_files,
            metadata=metadata,
            errors=errors,
            scan_duration_ms=duration_ms,
            scanned_at=end_time,
        )

    def _detect_file_type(self, file_path: str) -> FileType:
        """根据文件扩展名检测文件类型"""
        path = Path(file_path)
        extension = path.suffix.lower()

        type_mapping = {
            ".json": FileType.JSON,
            ".properties": FileType.PROPERTIES,
            ".lang": FileType.PROPERTIES,
            ".yml": FileType.YAML,
            ".yaml": FileType.YAML,
        }

        return type_mapping.get(extension, FileType.UNKNOWN)

    def _extract_language_code(self, file_path: str) -> LanguageCode | None:
        """从文件路径中提取语言代码"""
        path = Path(file_path)

        # 检查是否在lang目录中
        if "lang" not in path.parts:
            return None

        # 从文件名中提取语言代码
        filename = path.stem  # 不带扩展名的文件名

        try:
            return LanguageCode(filename)
        except ValueError:
            # 不是有效的语言代码
            return None

    def _extract_mod_id_from_path(self, file_path: str) -> ModId | None:
        """从文件路径中提取模组ID"""
        path = Path(file_path)
        parts = path.parts

        # 寻找assets目录
        try:
            assets_index = parts.index("assets")
            if assets_index + 1 < len(parts):
                potential_mod_id = parts[assets_index + 1]
                try:
                    return ModId(potential_mod_id)
                except ValueError:
                    # 不是有效的模组ID
                    pass
        except ValueError:
            # 路径中没有assets目录
            pass

        return None

    def _is_language_file(self, file_path: str) -> bool:
        """判断是否为语言文件"""
        path = Path(file_path)

        # 必须在lang目录中
        if "lang" not in path.parts:
            return False

        # 必须是支持的文件类型
        file_type = self._detect_file_type(file_path)
        return file_type in [FileType.JSON, FileType.PROPERTIES, FileType.YAML]

    async def _apply_filter(
        self, discovered_files: list[DiscoveredFile], scan_filter: ScanFilter | None
    ) -> list[DiscoveredFile]:
        """应用扫描过滤器"""
        if not scan_filter:
            return discovered_files

        filtered_files = []
        for file_info in discovered_files:
            if scan_filter.should_include_file(file_info):
                filtered_files.append(file_info)
            else:
                self._logger.debug(f"文件被过滤器排除: {file_info.relative_path}")

        return filtered_files

    def _log_scan_summary(self, result: ScanResult):
        """记录扫描摘要"""
        total_files = len(result.discovered_files)
        language_files = len([f for f in result.discovered_files if f.is_language_file])

        self._logger.info(
            f"{self._scanner_name}扫描完成: "
            f"路径={result.file_path}, "
            f"状态={result.scan_status.value}, "
            f"发现文件={total_files}, "
            f"语言文件={language_files}, "
            f"耗时={result.scan_duration_ms}ms"
        )

        if result.errors:
            self._logger.warning(f"扫描过程中发现 {len(result.errors)} 个错误")
            for error in result.errors[:3]:  # 只显示前3个错误
                self._logger.warning(f"  - {error}")


class ScannerRegistry:
    """扫描器注册表"""

    def __init__(self):
        self._scanners: list[BaseScanner] = []
        self._logger = get_logger(__name__ + ".ScannerRegistry")

    def register(self, scanner: BaseScanner):
        """注册扫描器"""
        self._scanners.append(scanner)
        self._logger.info(f"注册扫描器: {scanner.scanner_name}")

    def unregister(self, scanner: BaseScanner):
        """注销扫描器"""
        if scanner in self._scanners:
            self._scanners.remove(scanner)
            self._logger.info(f"注销扫描器: {scanner.scanner_name}")

    async def find_suitable_scanner(self, file_path: FilePath) -> BaseScanner | None:
        """查找适合处理指定路径的扫描器"""
        for scanner in self._scanners:
            try:
                if await scanner.can_handle(file_path):
                    self._logger.debug(
                        f"找到适合的扫描器: {scanner.scanner_name} for {file_path}"
                    )
                    return scanner
            except Exception as e:
                self._logger.warning(
                    f"检查扫描器 {scanner.scanner_name} 时发生错误: {e}"
                )

        self._logger.warning(f"未找到适合的扫描器: {file_path}")
        return None

    async def scan_with_best_scanner(
        self, file_path: FilePath, scan_filter: ScanFilter | None = None
    ) -> ScanResult | None:
        """使用最合适的扫描器进行扫描"""
        scanner = await self.find_suitable_scanner(file_path)
        if not scanner:
            return None

        try:
            return await scanner.scan(file_path, scan_filter)
        except Exception as e:
            self._logger.error(f"扫描器 {scanner.scanner_name} 执行失败: {e}")
            return None

    def get_registered_scanners(self) -> list[BaseScanner]:
        """获取所有已注册的扫描器"""
        return self._scanners.copy()


# 全局扫描器注册表实例
scanner_registry = ScannerRegistry()
