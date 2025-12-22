"""
Container 数据模型 - 逻辑翻译单元

根据白皮书定义：
- Container 是逻辑翻译单元（MOD、组合包模块、Overlay）
- 属于某个 Artifact
- 包含多个 LanguageFile
"""

import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import TYPE_CHECKING, Any, Optional

if TYPE_CHECKING:
    from .artifact import Artifact
    from .language_file import LanguageFile


class ContainerType(Enum):
    """Container 类型枚举"""

    MOD = "mod"  # MOD（来自 JAR 或文件夹）
    PACK_MODULE = "pack_module"  # 组合包模块（如 FTB Quests、KubeJS）
    OVERLAY = "overlay"  # 覆盖层（资源包形式）


class LoaderType(Enum):
    """MOD 加载器类型"""

    FORGE = "forge"
    FABRIC = "fabric"
    QUILT = "quilt"
    NEOFORGE = "neoforge"
    UNKNOWN = "unknown"


@dataclass
class Container:
    """
    Container 实体 - 逻辑翻译单元

    对应数据库表: containers
    """

    container_id: str
    container_type: ContainerType
    mod_id: str  # MOD ID 或模块标识
    display_name: str  # 显示名称
    version: str | None = None
    loader_type: LoaderType | None = None
    namespace: str | None = None  # 主命名空间
    metadata: dict[str, Any] = field(default_factory=dict)

    # 关联
    artifact: Optional["Artifact"] = None
    artifact_id: str | None = None

    # 运行时属性
    language_files: list["LanguageFile"] = field(default_factory=list)

    @classmethod
    def create_mod_container(
        cls,
        mod_id: str,
        display_name: str,
        version: str,
        loader_type: LoaderType,
        namespace: str | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> "Container":
        """创建 MOD 类型的 Container"""
        return cls(
            container_id=str(uuid.uuid4()),
            container_type=ContainerType.MOD,
            mod_id=mod_id,
            display_name=display_name,
            version=version,
            loader_type=loader_type,
            namespace=namespace or mod_id,
            metadata=metadata or {},
        )

    @classmethod
    def create_pack_module(
        cls,
        module_id: str,
        display_name: str,
        module_type: str,  # "ftb_quests", "kubejs", "custom_npcs" 等
        metadata: dict[str, Any] | None = None,
    ) -> "Container":
        """创建组合包模块类型的 Container"""
        meta = metadata or {}
        meta["module_type"] = module_type

        return cls(
            container_id=str(uuid.uuid4()),
            container_type=ContainerType.PACK_MODULE,
            mod_id=module_id,
            display_name=display_name,
            namespace=module_id,
            metadata=meta,
        )

    @classmethod
    def create_overlay(
        cls,
        overlay_id: str,
        display_name: str,
        target_namespace: str,
        metadata: dict[str, Any] | None = None,
    ) -> "Container":
        """创建 Overlay 类型的 Container"""
        return cls(
            container_id=str(uuid.uuid4()),
            container_type=ContainerType.OVERLAY,
            mod_id=overlay_id,
            display_name=display_name,
            namespace=target_namespace,
            metadata=metadata or {},
        )

    def add_language_file(self, language_file: "LanguageFile") -> None:
        """添加语言文件"""
        if language_file not in self.language_files:
            self.language_files.append(language_file)
            language_file.container = self

    def get_language_file(
        self, locale: str, namespace: str | None = None
    ) -> Optional["LanguageFile"]:
        """获取特定语言的文件"""
        target_namespace = namespace or self.namespace

        for lang_file in self.language_files:
            if lang_file.locale == locale:
                if not target_namespace or lang_file.namespace == target_namespace:
                    return lang_file
        return None

    def get_supported_locales(self) -> list[str]:
        """获取支持的语言列表"""
        locales = set()
        for lang_file in self.language_files:
            locales.add(lang_file.locale)
        return sorted(list(locales))

    def get_total_keys(self) -> int:
        """获取总的翻译键数量"""
        total = 0
        for lang_file in self.language_files:
            total += lang_file.key_count
        return total

    def to_dict(self) -> dict[str, Any]:
        """转换为字典格式"""
        return {
            "container_id": self.container_id,
            "container_type": self.container_type.value,
            "mod_id": self.mod_id,
            "display_name": self.display_name,
            "version": self.version,
            "loader_type": self.loader_type.value if self.loader_type else None,
            "namespace": self.namespace,
            "artifact_id": self.artifact_id,
            "metadata": self.metadata,
            "language_file_count": len(self.language_files),
            "supported_locales": self.get_supported_locales(),
            "total_keys": self.get_total_keys(),
        }
