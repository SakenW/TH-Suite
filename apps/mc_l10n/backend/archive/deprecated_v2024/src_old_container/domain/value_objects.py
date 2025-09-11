"""
领域值对象
不可变的、没有身份标识的领域概念
"""

import hashlib
import blake3
import re
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Optional


class LoaderType(Enum):
    """Mod加载器类型"""

    FORGE = "forge"
    FABRIC = "fabric"
    QUILT = "quilt"
    NEOFORGE = "neoforge"
    UNKNOWN = "unknown"


class ProjectType(Enum):
    """项目类型"""

    MODPACK = "modpack"
    SINGLE_MOD = "single_mod"
    RESOURCE_PACK = "resource_pack"
    UNKNOWN = "unknown"


class LanguageCode(Enum):
    """支持的语言代码"""

    ZH_CN = "zh_cn"  # 简体中文
    ZH_TW = "zh_tw"  # 繁体中文
    EN_US = "en_us"  # 英语(美国)
    EN_GB = "en_gb"  # 英语(英国)
    JA_JP = "ja_jp"  # 日语
    KO_KR = "ko_kr"  # 韩语
    DE_DE = "de_de"  # 德语
    FR_FR = "fr_fr"  # 法语
    ES_ES = "es_es"  # 西班牙语
    IT_IT = "it_it"  # 意大利语
    PT_BR = "pt_br"  # 葡萄牙语(巴西)
    RU_RU = "ru_ru"  # 俄语
    PL_PL = "pl_pl"  # 波兰语
    NL_NL = "nl_nl"  # 荷兰语

    @classmethod
    def is_valid(cls, code: str) -> bool:
        """检查语言代码是否有效"""
        return code in cls._value2member_map_

    @classmethod
    def from_string(cls, code: str) -> Optional["LanguageCode"]:
        """从字符串创建语言代码"""
        try:
            return cls(code.lower())
        except ValueError:
            return None


@dataclass(frozen=True)
class FilePath:
    """文件路径值对象"""

    value: str

    def __post_init__(self):
        if not self.value:
            raise ValueError("File path cannot be empty")

        # 标准化路径
        path = Path(self.value)
        object.__setattr__(self, "value", str(path.resolve()))

    @property
    def exists(self) -> bool:
        """检查文件是否存在"""
        return Path(self.value).exists()

    @property
    def is_file(self) -> bool:
        """检查是否为文件"""
        return Path(self.value).is_file()

    @property
    def is_directory(self) -> bool:
        """检查是否为目录"""
        return Path(self.value).is_dir()

    @property
    def extension(self) -> str:
        """获取文件扩展名"""
        return Path(self.value).suffix

    @property
    def name(self) -> str:
        """获取文件名"""
        return Path(self.value).name

    @property
    def parent(self) -> "FilePath":
        """获取父目录"""
        return FilePath(str(Path(self.value).parent))

    def __str__(self) -> str:
        return self.value


@dataclass(frozen=True)
class ContentHash:
    """内容哈希值对象"""

    value: str
    algorithm: str = "blake3"

    def __post_init__(self):
        if not self.value:
            raise ValueError("Hash value cannot be empty")

        # 验证哈希格式
        if self.algorithm == "blake3" and len(self.value) != 64:
            raise ValueError("Invalid BLAKE3 hash length")
        elif self.algorithm == "sha256" and len(self.value) != 64:
            raise ValueError("Invalid SHA256 hash length")
        elif self.algorithm == "md5" and len(self.value) != 32:
            raise ValueError("Invalid MD5 hash length")

        # 确保小写
        object.__setattr__(self, "value", self.value.lower())

    @classmethod
    def from_content(cls, content: bytes, algorithm: str = "blake3") -> "ContentHash":
        """从内容生成哈希"""
        if algorithm == "blake3":
            hasher = blake3.blake3()
            hasher.update(content)
            return cls(hasher.hexdigest(), algorithm)
        elif algorithm == "sha256":
            hash_obj = hashlib.sha256()
            hash_obj.update(content)
            return cls(hash_obj.hexdigest(), algorithm)
        elif algorithm == "md5":
            hash_obj = hashlib.md5()
            hash_obj.update(content)
            return cls(hash_obj.hexdigest(), algorithm)
        else:
            raise ValueError(f"Unsupported algorithm: {algorithm}")

    @classmethod
    def from_file(cls, file_path: str, algorithm: str = "blake3") -> "ContentHash":
        """从文件生成哈希"""
        with open(file_path, "rb") as f:
            return cls.from_content(f.read(), algorithm)

    def __str__(self) -> str:
        return f"{self.algorithm}:{self.value}"

    def __eq__(self, other) -> bool:
        if not isinstance(other, ContentHash):
            return False
        return self.value == other.value and self.algorithm == other.algorithm


@dataclass(frozen=True)
class TranslationKey:
    """翻译键值对象"""

    value: str
    namespace: str | None = None

    # 业务规则常量
    MAX_KEY_LENGTH = 256
    VALID_KEY_PATTERN = re.compile(r"^[a-zA-Z0-9._-]+$")

    def __post_init__(self):
        if not self.value:
            raise ValueError("Translation key cannot be empty")

        if len(self.value) > self.MAX_KEY_LENGTH:
            raise ValueError(
                f"Translation key exceeds maximum length of {self.MAX_KEY_LENGTH}"
            )

        # 验证key格式
        if not self.VALID_KEY_PATTERN.match(self.value):
            raise ValueError(f"Invalid translation key format: {self.value}")

        # 如果有命名空间，验证命名空间
        if self.namespace and not self.VALID_KEY_PATTERN.match(self.namespace):
            raise ValueError(f"Invalid namespace format: {self.namespace}")

    @property
    def full_key(self) -> str:
        """获取完整的键（包含命名空间）"""
        if self.namespace:
            return f"{self.namespace}:{self.value}"
        return self.value

    def __str__(self) -> str:
        return self.full_key

    def __hash__(self) -> int:
        return hash(self.full_key)


@dataclass(frozen=True)
class TranslationText:
    """翻译文本值对象"""

    value: str
    language: LanguageCode

    # 业务规则常量
    MAX_TEXT_LENGTH = 4096
    MIN_TEXT_LENGTH = 1

    def __post_init__(self):
        if not self.value:
            raise ValueError("Translation text cannot be empty")

        if len(self.value) < self.MIN_TEXT_LENGTH:
            raise ValueError(
                f"Translation text must be at least {self.MIN_TEXT_LENGTH} characters"
            )

        if len(self.value) > self.MAX_TEXT_LENGTH:
            raise ValueError(
                f"Translation text exceeds maximum length of {self.MAX_TEXT_LENGTH}"
            )

        # 清理文本（去除首尾空白，但保留内部格式）
        cleaned = self.value.strip()
        if cleaned != self.value:
            object.__setattr__(self, "value", cleaned)

    @property
    def word_count(self) -> int:
        """获取单词数量"""
        return len(self.value.split())

    @property
    def char_count(self) -> int:
        """获取字符数量"""
        return len(self.value)

    def contains_placeholder(self) -> bool:
        """检查是否包含占位符"""
        # 检查常见的占位符格式
        patterns = [
            r"%[sd]",  # %s, %d
            r"\{[^}]+\}",  # {placeholder}
            r"\$\{[^}]+\}",  # ${placeholder}
            r"%\([^)]+\)[sd]",  # %(name)s
        ]
        for pattern in patterns:
            if re.search(pattern, self.value):
                return True
        return False

    def __str__(self) -> str:
        return self.value


@dataclass(frozen=True)
class ScanProgress:
    """扫描进度值对象"""

    total_files: int
    processed_files: int
    current_file: str | None = None
    start_time: datetime = field(default_factory=datetime.now)

    def __post_init__(self):
        if self.total_files < 0:
            raise ValueError("Total files cannot be negative")

        if self.processed_files < 0:
            raise ValueError("Processed files cannot be negative")

        if self.processed_files > self.total_files:
            raise ValueError("Processed files cannot exceed total files")

    @property
    def percentage(self) -> float:
        """获取进度百分比"""
        if self.total_files == 0:
            return 100.0
        return (self.processed_files / self.total_files) * 100

    @property
    def is_complete(self) -> bool:
        """检查是否完成"""
        return self.processed_files >= self.total_files

    @property
    def elapsed_time(self) -> float:
        """获取已用时间（秒）"""
        return (datetime.now() - self.start_time).total_seconds()

    @property
    def estimated_remaining_time(self) -> float | None:
        """获取预估剩余时间（秒）"""
        if self.processed_files == 0:
            return None

        rate = self.processed_files / self.elapsed_time
        remaining = self.total_files - self.processed_files
        return remaining / rate if rate > 0 else None

    def next_file(self, file_path: str) -> "ScanProgress":
        """处理下一个文件"""
        return ScanProgress(
            total_files=self.total_files,
            processed_files=self.processed_files + 1,
            current_file=file_path,
            start_time=self.start_time,
        )


@dataclass(frozen=True)
class QualityScore:
    """翻译质量分数值对象"""

    value: float

    # 业务规则常量
    MIN_SCORE = 0.0
    MAX_SCORE = 1.0
    PASS_THRESHOLD = 0.8

    def __post_init__(self):
        if not self.MIN_SCORE <= self.value <= self.MAX_SCORE:
            raise ValueError(
                f"Quality score must be between {self.MIN_SCORE} and {self.MAX_SCORE}"
            )

    @property
    def is_passing(self) -> bool:
        """检查是否达标"""
        return self.value >= self.PASS_THRESHOLD

    @property
    def grade(self) -> str:
        """获取评级"""
        if self.value >= 0.95:
            return "A+"
        elif self.value >= 0.90:
            return "A"
        elif self.value >= 0.85:
            return "B+"
        elif self.value >= 0.80:
            return "B"
        elif self.value >= 0.75:
            return "C+"
        elif self.value >= 0.70:
            return "C"
        elif self.value >= 0.60:
            return "D"
        else:
            return "F"

    @classmethod
    def from_percentage(cls, percentage: float) -> "QualityScore":
        """从百分比创建"""
        return cls(percentage / 100)

    def to_percentage(self) -> float:
        """转换为百分比"""
        return self.value * 100

    def __str__(self) -> str:
        return f"{self.to_percentage():.1f}% ({self.grade})"


@dataclass(frozen=True)
class TimeRange:
    """时间范围值对象"""

    start: datetime
    end: datetime

    def __post_init__(self):
        if self.start >= self.end:
            raise ValueError("Start time must be before end time")

    @property
    def duration(self) -> float:
        """获取持续时间（秒）"""
        return (self.end - self.start).total_seconds()

    @property
    def duration_minutes(self) -> float:
        """获取持续时间（分钟）"""
        return self.duration / 60

    @property
    def duration_hours(self) -> float:
        """获取持续时间（小时）"""
        return self.duration / 3600

    def contains(self, time: datetime) -> bool:
        """检查时间是否在范围内"""
        return self.start <= time <= self.end

    def overlaps(self, other: "TimeRange") -> bool:
        """检查是否与另一个时间范围重叠"""
        return not (self.end <= other.start or other.end <= self.start)

    def merge(self, other: "TimeRange") -> "TimeRange":
        """合并两个时间范围"""
        if not self.overlaps(other):
            raise ValueError("Cannot merge non-overlapping time ranges")

        return TimeRange(min(self.start, other.start), max(self.end, other.end))


@dataclass(frozen=True)
class ResourceLocation:
    """资源位置值对象（Minecraft风格）"""

    namespace: str
    path: str

    # 业务规则常量
    DEFAULT_NAMESPACE = "minecraft"
    VALID_PATTERN = re.compile(r"^[a-z0-9_-]+$")

    def __post_init__(self):
        # 验证命名空间
        if not self.namespace:
            object.__setattr__(self, "namespace", self.DEFAULT_NAMESPACE)

        if not self.VALID_PATTERN.match(self.namespace):
            raise ValueError(f"Invalid namespace: {self.namespace}")

        # 验证路径
        if not self.path:
            raise ValueError("Path cannot be empty")

        # 路径可以包含斜杠
        path_parts = self.path.split("/")
        for part in path_parts:
            if not self.VALID_PATTERN.match(part):
                raise ValueError(f"Invalid path component: {part}")

    @classmethod
    def from_string(cls, location: str) -> "ResourceLocation":
        """从字符串解析资源位置"""
        if ":" in location:
            namespace, path = location.split(":", 1)
        else:
            namespace = cls.DEFAULT_NAMESPACE
            path = location

        return cls(namespace, path)

    @property
    def full_location(self) -> str:
        """获取完整位置字符串"""
        return f"{self.namespace}:{self.path}"

    def __str__(self) -> str:
        return self.full_location

    def __hash__(self) -> int:
        return hash(self.full_location)


@dataclass(frozen=True)
class Priority:
    """优先级值对象"""

    value: int

    # 优先级级别
    LOW = 0
    NORMAL = 1
    HIGH = 2
    URGENT = 3
    CRITICAL = 4

    def __post_init__(self):
        if not 0 <= self.value <= 4:
            raise ValueError("Priority must be between 0 and 4")

    @property
    def name(self) -> str:
        """获取优先级名称"""
        names = {0: "Low", 1: "Normal", 2: "High", 3: "Urgent", 4: "Critical"}
        return names.get(self.value, "Unknown")

    @property
    def color(self) -> str:
        """获取优先级对应的颜色（用于UI显示）"""
        colors = {
            0: "#808080",  # 灰色
            1: "#0000FF",  # 蓝色
            2: "#FFA500",  # 橙色
            3: "#FF0000",  # 红色
            4: "#8B0000",  # 深红色
        }
        return colors.get(self.value, "#000000")

    def __lt__(self, other: "Priority") -> bool:
        return self.value < other.value

    def __str__(self) -> str:
        return self.name


@dataclass(frozen=True)
class Percentage:
    """百分比值对象"""

    value: float

    def __post_init__(self):
        if not 0 <= self.value <= 100:
            raise ValueError("Percentage must be between 0 and 100")

    @classmethod
    def from_ratio(cls, numerator: float, denominator: float) -> "Percentage":
        """从比率创建百分比"""
        if denominator == 0:
            return cls(0)
        return cls((numerator / denominator) * 100)

    @property
    def as_decimal(self) -> float:
        """转换为小数"""
        return self.value / 100

    @property
    def is_complete(self) -> bool:
        """检查是否完成（100%）"""
        return self.value >= 100

    def __str__(self) -> str:
        return f"{self.value:.1f}%"

    def __add__(self, other: "Percentage") -> "Percentage":
        return Percentage(min(self.value + other.value, 100))

    def __sub__(self, other: "Percentage") -> "Percentage":
        return Percentage(max(self.value - other.value, 0))
