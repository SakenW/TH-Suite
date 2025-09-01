"""MC领域模型枚举类型"""

from enum import Enum


class TranslationStatus(Enum):
    """翻译状态"""

    UNTRANSLATED = "untranslated"  # 未翻译
    IN_PROGRESS = "in_progress"  # 翻译中
    TRANSLATED = "translated"  # 已翻译
    NEEDS_REVIEW = "needs_review"  # 需要审核
    APPROVED = "approved"  # 已审核通过
    REJECTED = "rejected"  # 审核不通过


class ModLoader(Enum):
    """模组加载器类型"""

    FORGE = "forge"
    FABRIC = "fabric"
    QUILT = "quilt"
    NEOFORGE = "neoforge"
    UNKNOWN = "unknown"


class FileType(Enum):
    """文件类型"""

    JSON = "json"
    PROPERTIES = "properties"
    YAML = "yaml"
    UNKNOWN = "unknown"


class ProjectStatus(Enum):
    """项目状态"""

    ACTIVE = "active"  # 活跃
    COMPLETED = "completed"  # 已完成
    ARCHIVED = "archived"  # 已归档
    SUSPENDED = "suspended"  # 已暂停


class MinecraftVersion(Enum):
    """Minecraft版本枚举"""

    MC_1_7_10 = "1.7.10"
    MC_1_12_2 = "1.12.2"
    MC_1_16_5 = "1.16.5"
    MC_1_18_2 = "1.18.2"
    MC_1_19_2 = "1.19.2"
    MC_1_20_1 = "1.20.1"
    MC_1_20_4 = "1.20.4"
    MC_1_21_0 = "1.21.0"
    UNKNOWN = "unknown"

    @classmethod
    def from_string(cls, version_string: str) -> "MinecraftVersion":
        """从字符串转换为版本枚举"""
        for version in cls:
            if version.value == version_string:
                return version
        return cls.UNKNOWN


class ScanStatus(Enum):
    """扫描状态"""

    PENDING = "pending"  # 待扫描
    SCANNING = "scanning"  # 扫描中
    COMPLETED = "completed"  # 扫描完成
    FAILED = "failed"  # 扫描失败
    CANCELLED = "cancelled"  # 已取消


# 类型别名，用于向后兼容
ModLoaderType = ModLoader
