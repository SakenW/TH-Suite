# apps/mc-l10n/backend/src/mc_l10n/domain/scan_models.py
"""
扫描领域模型

定义扫描过程中的核心业务对象，包含纯业务逻辑，不依赖外部技术实现。
"""

from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass
from pathlib import Path

from packages.core import (
    FileType,
    LoaderType,
    ProjectType,
)


@dataclass
class FileFingerprint:
    """文件指纹信息"""

    path: Path
    size: int
    hash_md5: str
    hash_sha256: str
    modified_time: float

    @classmethod
    def create_from_file(cls, file_path: Path) -> FileFingerprint:
        """从文件创建指纹"""
        if not file_path.exists() or not file_path.is_file():
            raise FileNotFoundError(f"File not found: {file_path}")

        stat = file_path.stat()
        content = file_path.read_bytes()

        return cls(
            path=file_path,
            size=stat.st_size,
            hash_md5=hashlib.md5(content).hexdigest(),
            hash_sha256=hashlib.sha256(content).hexdigest(),
            modified_time=stat.st_mtime,
        )


@dataclass
class LanguageFileInfo:
    """语言文件信息"""

    path: Path
    relative_path: Path  # 相对于MOD根目录的路径
    file_type: FileType
    locale: str
    encoding: str = "utf-8"
    key_count: int = 0
    fingerprint: FileFingerprint | None = None
    parse_errors: list[str] = None

    def __post_init__(self):
        if self.parse_errors is None:
            self.parse_errors = []

    @property
    def has_errors(self) -> bool:
        """是否有解析错误"""
        return len(self.parse_errors) > 0

    def detect_locale_from_path(self) -> str | None:
        """从路径检测语言代码"""
        path_str = str(self.relative_path).lower()

        # 常见的语言文件路径模式
        patterns = [
            r"/lang/([a-z]{2}_[a-z]{2})\.json$",  # /lang/en_us.json
            r"/lang/([a-z]{2}_[a-z]{2})\.lang$",  # /lang/en_us.lang
            r"/localization/([a-z]{2}_[a-z]{2})\.",  # /localization/en_us.*
            r"/i18n/([a-z]{2}_[a-z]{2})\.",  # /i18n/en_us.*
        ]

        for pattern in patterns:
            match = re.search(pattern, path_str)
            if match:
                return match.group(1)

        # 从文件名检测
        stem = self.path.stem.lower()
        if re.match(r"^[a-z]{2}_[a-z]{2}$", stem):
            return stem

        return None


@dataclass
class ModInfo:
    """MOD信息"""

    mod_id: str
    name: str
    version: str | None = None
    description: str | None = None
    authors: list[str] = None
    dependencies: list[str] = None
    minecraft_version: str | None = None
    loader_type: LoaderType | None = None

    # 文件信息
    file_path: Path = None
    file_size: int = 0
    fingerprint: FileFingerprint | None = None

    # 语言文件
    language_files: list[LanguageFileInfo] = None
    supported_locales: set[str] = None

    def __post_init__(self):
        if self.authors is None:
            self.authors = []
        if self.dependencies is None:
            self.dependencies = []
        if self.language_files is None:
            self.language_files = []
        if self.supported_locales is None:
            self.supported_locales = set()

    @property
    def total_language_files(self) -> int:
        """语言文件总数"""
        return len(self.language_files)

    @property
    def estimated_segments(self) -> int:
        """估算的翻译片段数量"""
        return sum(lf.key_count for lf in self.language_files)

    def add_language_file(self, lang_file: LanguageFileInfo) -> None:
        """添加语言文件"""
        self.language_files.append(lang_file)
        if lang_file.locale:
            self.supported_locales.add(lang_file.locale)

    def get_language_files_by_locale(self, locale: str) -> list[LanguageFileInfo]:
        """获取指定语言的文件"""
        return [lf for lf in self.language_files if lf.locale == locale]

    def has_locale(self, locale: str) -> bool:
        """是否支持指定语言"""
        return locale in self.supported_locales


@dataclass
class ProjectInfo:
    """项目信息"""

    name: str
    path: Path
    project_type: ProjectType
    loader_type: LoaderType | None = None

    # 版本信息
    minecraft_version: str | None = None
    loader_version: str | None = None

    # MOD信息
    mods: list[ModInfo] = None
    source_locale: str = "en_us"
    supported_locales: set[str] = None

    # 统计信息
    fingerprint: str | None = None  # 项目指纹，用于去重

    def __post_init__(self):
        if self.mods is None:
            self.mods = []
        if self.supported_locales is None:
            self.supported_locales = set()

    @property
    def total_mods(self) -> int:
        """MOD总数"""
        return len(self.mods)

    @property
    def total_language_files(self) -> int:
        """语言文件总数"""
        return sum(mod.total_language_files for mod in self.mods)

    @property
    def estimated_segments(self) -> int:
        """估算的翻译片段总数"""
        return sum(mod.estimated_segments for mod in self.mods)

    def add_mod(self, mod_info: ModInfo) -> None:
        """添加MOD"""
        self.mods.append(mod_info)
        self.supported_locales.update(mod_info.supported_locales)

    def get_mods_by_loader(self, loader_type: LoaderType) -> list[ModInfo]:
        """获取指定加载器的MOD"""
        return [mod for mod in self.mods if mod.loader_type == loader_type]

    def generate_fingerprint(self) -> str:
        """生成项目指纹"""
        # 使用项目路径和主要属性生成唯一指纹
        content = f"{self.path}:{self.project_type.value}:{self.loader_type.value if self.loader_type else 'none'}"
        self.fingerprint = hashlib.sha256(content.encode()).hexdigest()[:16]
        return self.fingerprint


# 扫描规则和策略
class ScanRule:
    """扫描规则基类"""

    def matches(self, path: Path) -> bool:
        """判断路径是否匹配此规则"""
        raise NotImplementedError

    def extract_info(self, path: Path) -> dict:
        """从路径提取信息"""
        raise NotImplementedError


class MinecraftModScanRule(ScanRule):
    """Minecraft MOD扫描规则"""

    # 支持的文件扩展名
    SUPPORTED_EXTENSIONS = {".jar", ".zip"}

    # 语言文件模式
    LANGUAGE_FILE_PATTERNS = [
        re.compile(r"assets/[^/]+/lang/[^/]+\.(json|lang)$"),
        re.compile(r"data/[^/]+/lang/[^/]+\.(json|lang)$"),
        re.compile(r"lang/[^/]+\.(json|lang)$"),  # 旧版本
    ]

    # 加载器检测模式
    LOADER_PATTERNS = {
        LoaderType.FORGE: [
            re.compile(r"META-INF/mods\.toml$"),
            re.compile(r"mcmod\.info$"),
        ],
        LoaderType.FABRIC: [
            re.compile(r"fabric\.mod\.json$"),
        ],
        LoaderType.QUILT: [
            re.compile(r"quilt\.mod\.json$"),
        ],
        LoaderType.NEOFORGE: [
            re.compile(r"META-INF/neoforge\.mods\.toml$"),
        ],
    }

    def matches(self, path: Path) -> bool:
        """判断是否为MOD文件"""
        return path.suffix.lower() in self.SUPPORTED_EXTENSIONS

    def is_language_file(self, internal_path: str) -> bool:
        """判断是否为语言文件"""
        return any(
            pattern.search(internal_path) for pattern in self.LANGUAGE_FILE_PATTERNS
        )

    def detect_loader_type(self, internal_files: list[str]) -> LoaderType | None:
        """检测加载器类型"""
        for loader_type, patterns in self.LOADER_PATTERNS.items():
            if any(
                any(pattern.search(file) for pattern in patterns)
                for file in internal_files
            ):
                return loader_type
        return None

    def extract_namespace_from_path(self, lang_file_path: str) -> str | None:
        """从语言文件路径提取命名空间"""
        # assets/{namespace}/lang/{locale}.json
        match = re.search(r"assets/([^/]+)/lang/", lang_file_path)
        if match:
            return match.group(1)

        # data/{namespace}/lang/{locale}.json
        match = re.search(r"data/([^/]+)/lang/", lang_file_path)
        if match:
            return match.group(1)

        return None


class ModpackScanRule(ScanRule):
    """整合包扫描规则"""

    # 整合包标识文件
    MODPACK_INDICATORS = [
        "manifest.json",  # CurseForge
        "instance.cfg",  # MultiMC
        "mmc-pack.json",  # MultiMC
        "modrinth.index.json",  # Modrinth
    ]

    # MOD目录名称
    MOD_DIRECTORIES = ["mods", "Mods", ".minecraft/mods"]

    def matches(self, path: Path) -> bool:
        """判断是否为整合包目录"""
        if not path.is_dir():
            return False

        # 检查整合包标识文件
        for indicator in self.MODPACK_INDICATORS:
            if (path / indicator).exists():
                return True

        # 检查是否有mods目录且包含MOD文件
        for mod_dir in self.MOD_DIRECTORIES:
            mod_path = path / mod_dir
            if mod_path.exists() and mod_path.is_dir():
                if any(
                    f.suffix.lower() in {".jar", ".zip"} for f in mod_path.iterdir()
                ):
                    return True

        return False

    def find_mod_directories(self, path: Path) -> list[Path]:
        """查找MOD目录"""
        mod_dirs = []
        for mod_dir in self.MOD_DIRECTORIES:
            mod_path = path / mod_dir
            if mod_path.exists() and mod_path.is_dir():
                mod_dirs.append(mod_path)
        return mod_dirs


@dataclass
class ScanProgress:
    """扫描进度信息"""

    current_file: str | None = None
    processed_files: int = 0
    total_files: int = 0
    current_step: str = "初始化"
    errors: list[str] = None

    def __post_init__(self):
        if self.errors is None:
            self.errors = []

    @property
    def progress_percentage(self) -> float:
        """进度百分比（0-100）"""
        if self.total_files == 0:
            return 0.0
        return (self.processed_files / self.total_files) * 100
    
    @property
    def progress_ratio(self) -> float:
        """进度比例（0-1）"""
        if self.total_files == 0:
            return 0.0
        return self.processed_files / self.total_files

    def add_error(self, error: str) -> None:
        """添加错误"""
        self.errors.append(error)

    def update_progress(self, current_file: str, step: str) -> None:
        """更新进度"""
        self.current_file = current_file
        self.current_step = step
        self.processed_files += 1


@dataclass
class ScanResult:
    """扫描结果"""

    success: bool
    project_info: ProjectInfo | None = None
    errors: list[str] = None
    warnings: list[str] = None
    scan_time: float = 0.0

    def __post_init__(self):
        if self.errors is None:
            self.errors = []
        if self.warnings is None:
            self.warnings = []

    @property
    def has_errors(self) -> bool:
        """是否有错误"""
        return len(self.errors) > 0

    @property
    def has_warnings(self) -> bool:
        """是否有警告"""
        return len(self.warnings) > 0

    def add_error(self, error: str) -> None:
        """添加错误"""
        self.errors.append(error)
        self.success = False

    def add_warning(self, warning: str) -> None:
        """添加警告"""
        self.warnings.append(warning)
