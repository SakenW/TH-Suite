"""
Mod聚合根
Minecraft模组的核心领域模型
"""

from dataclasses import dataclass, field, replace
from datetime import datetime

from ..events import ModScannedEvent, ModTranslatedEvent, TranslationConflictEvent
from ..value_objects import (
    ContentHash,
    FilePath,
    LanguageCode,
    LoaderType,
    QualityScore,
    TranslationKey,
    TranslationText,
)


@dataclass(frozen=True)
class ModId:
    """Mod ID值对象 - 不可变"""

    value: str

    def __post_init__(self):
        if not self.value or not isinstance(self.value, str):
            raise ValueError("ModId must be a non-empty string")
        # 标准化ModId（小写，去除空格）
        normalized = self.value.lower().strip().replace(" ", "_")
        if normalized != self.value:
            object.__setattr__(self, "value", normalized)

    def __str__(self) -> str:
        return self.value

    def __eq__(self, other) -> bool:
        if not isinstance(other, ModId):
            return False
        return self.value == other.value

    def __hash__(self) -> int:
        return hash(self.value)


@dataclass(frozen=True)
class ModVersion:
    """Mod版本值对象 - 不可变"""

    major: int
    minor: int
    patch: int
    build: str | None = None

    def __post_init__(self):
        if self.major < 0 or self.minor < 0 or self.patch < 0:
            raise ValueError("Version numbers cannot be negative")

    @classmethod
    def from_string(cls, version_str: str) -> "ModVersion":
        """从字符串解析版本"""
        # 清理版本字符串
        version_str = version_str.strip()
        if version_str.startswith("v"):
            version_str = version_str[1:]

        parts = version_str.split(".")
        major = int(parts[0]) if len(parts) > 0 else 0
        minor = int(parts[1]) if len(parts) > 1 else 0
        patch = int(parts[2]) if len(parts) > 2 else 0
        build = parts[3] if len(parts) > 3 else None
        return cls(major, minor, patch, build)

    def __str__(self) -> str:
        version = f"{self.major}.{self.minor}.{self.patch}"
        if self.build:
            version += f".{self.build}"
        return version

    def __lt__(self, other: "ModVersion") -> bool:
        return (self.major, self.minor, self.patch) < (
            other.major,
            other.minor,
            other.patch,
        )

    def is_compatible_with(self, other: "ModVersion") -> bool:
        """检查版本兼容性（主版本号相同）"""
        return self.major == other.major


@dataclass
class TranslationEntry:
    """翻译条目实体（可变，因为需要修改状态）"""

    key: TranslationKey
    original: TranslationText
    translated: TranslationText
    status: str = "pending"  # pending, approved, rejected
    translator: str | None = None
    reviewed_by: str | None = None
    quality_score: QualityScore | None = None
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)

    def __post_init__(self):
        # 验证语言一致性
        if self.original.language == self.translated.language:
            raise ValueError(
                "Original and translated text cannot have the same language"
            )

        # 验证状态
        if self.status not in ["pending", "approved", "rejected"]:
            raise ValueError(f"Invalid status: {self.status}")

    def approve(self, reviewer: str, quality_score: QualityScore | None = None):
        """批准翻译"""
        if not reviewer:
            raise ValueError("Reviewer is required")

        self.status = "approved"
        self.reviewed_by = reviewer
        self.quality_score = quality_score or QualityScore(1.0)
        self.updated_at = datetime.now()

    def reject(self, reviewer: str, reason: str | None = None):
        """拒绝翻译"""
        if not reviewer:
            raise ValueError("Reviewer is required")

        self.status = "rejected"
        self.reviewed_by = reviewer
        self.quality_score = QualityScore(0.0)
        self.updated_at = datetime.now()

    def update_translation(self, new_text: TranslationText, translator: str):
        """更新翻译内容"""
        if new_text.language != self.translated.language:
            raise ValueError("Cannot change translation language")

        self.translated = new_text
        self.translator = translator
        self.status = "pending"  # 重置为待审核
        self.reviewed_by = None
        self.quality_score = None
        self.updated_at = datetime.now()


@dataclass(frozen=True)
class ModMetadata:
    """Mod元数据值对象 - 不可变"""

    name: str
    version: ModVersion
    authors: list[str]
    description: str | None = None
    minecraft_version: str | None = None
    loader_type: LoaderType = LoaderType.UNKNOWN
    dependencies: list[str] = field(default_factory=list)
    tags: set[str] = field(default_factory=set)
    homepage: str | None = None
    license: str | None = None

    def __post_init__(self):
        if not self.name:
            raise ValueError("Mod name is required")

        # 冻结可变集合
        object.__setattr__(self, "authors", tuple(self.authors))
        object.__setattr__(self, "dependencies", tuple(self.dependencies))
        object.__setattr__(self, "tags", frozenset(self.tags))

    def with_tag(self, tag: str) -> "ModMetadata":
        """返回添加了标签的新实例"""
        new_tags = set(self.tags)
        new_tags.add(tag)
        return replace(self, tags=new_tags)

    def without_tag(self, tag: str) -> "ModMetadata":
        """返回移除了标签的新实例"""
        new_tags = set(self.tags)
        new_tags.discard(tag)
        return replace(self, tags=new_tags)

    def with_dependency(self, dependency: str) -> "ModMetadata":
        """返回添加了依赖的新实例"""
        new_deps = list(self.dependencies)
        if dependency not in new_deps:
            new_deps.append(dependency)
        return replace(self, dependencies=new_deps)


class Mod:
    """Mod聚合根

    负责维护Mod的完整性和业务规则：
    - 管理Mod的生命周期
    - 确保翻译数据的一致性
    - 处理翻译冲突
    - 发布领域事件
    """

    # 业务常量
    MAX_SCAN_ATTEMPTS = 3
    SCAN_TIMEOUT_SECONDS = 300

    def __init__(self, mod_id: ModId, metadata: ModMetadata, file_path: str):
        # 验证输入
        if not mod_id:
            raise ValueError("ModId is required")
        if not metadata:
            raise ValueError("Metadata is required")
        if not file_path:
            raise ValueError("File path is required")

        self.mod_id = mod_id
        self.metadata = metadata
        self.file_path = FilePath(file_path)
        self.translations: dict[LanguageCode, list[TranslationEntry]] = {}
        self.scan_status = "pending"  # pending, scanning, completed, failed
        self.last_scanned = None
        self.content_hash = None
        self.domain_events = []
        self.created_at = datetime.now()
        self.updated_at = datetime.now()

        # 新增：业务状态
        self.is_active = True
        self.scan_error_message = None
        self.scan_attempt_count = 0
        self.translation_lock = False  # 防止并发修改

    def start_scan(self):
        """开始扫描

        业务规则：
        - 只有激活的Mod才能扫描
        - 扫描时锁定翻译修改
        """
        if not self.is_active:
            raise ValueError("Cannot scan inactive mod")

        if self.scan_status == "scanning":
            raise ValueError("Mod is already being scanned")

        self.scan_status = "scanning"
        self.translation_lock = True
        self.scan_attempt_count += 1
        self.updated_at = datetime.now()

    def scan_completed(self, content_hash: str, translation_count: int):
        """扫描完成

        业务规则：
        - 必须处于扫描状态
        - 解锁翻译修改
        - 重置错误信息
        """
        if self.scan_status != "scanning":
            raise ValueError("Mod is not being scanned")

        if not isinstance(content_hash, ContentHash):
            raise ValueError("Content hash must be a ContentHash instance")

        if translation_count < 0:
            raise ValueError("Translation count cannot be negative")

        self.scan_status = "completed"
        self.last_scanned = datetime.now()
        self.content_hash = content_hash
        self.scan_error_message = None
        self.translation_lock = False
        self.updated_at = datetime.now()

        # 发布领域事件
        self._add_event(
            ModScannedEvent(
                mod_id=str(self.mod_id),
                timestamp=datetime.now(),
                translation_count=translation_count,
                content_hash=content_hash,
            )
        )

    def scan_failed(self, error: str):
        """扫描失败

        业务规则：
        - 记录错误信息
        - 解锁翻译修改
        - 超过最大重试次数后停用Mod
        """
        if self.scan_status != "scanning":
            raise ValueError("Mod is not being scanned")

        self.scan_status = "failed"
        self.scan_error_message = error
        self.translation_lock = False
        self.updated_at = datetime.now()

        # 超过3次失败自动停用
        if self.scan_attempt_count >= 3:
            self.deactivate(f"Scan failed {self.scan_attempt_count} times")

    def add_translation(self, language: LanguageCode, entry: TranslationEntry):
        """添加翻译

        业务规则：
        - 只能添加支持的语言
        - 翻译锁定时不能修改
        - 验证翻译条目的有效性
        - 处理翻译冲突
        """
        # 验证业务规则
        if self.translation_lock:
            raise ValueError("Cannot modify translations while scanning")

        if not self.is_active:
            raise ValueError("Cannot add translations to inactive mod")

        if not isinstance(language, LanguageCode):
            raise ValueError("Language must be a LanguageCode instance")

        # 验证翻译条目
        self._validate_translation_entry(entry)

        if language not in self.translations:
            self.translations[language] = []

        # 检查是否存在相同的key
        existing = next(
            (t for t in self.translations[language] if t.key == entry.key), None
        )

        if existing:
            if existing.translated != entry.translated:
                # 发布冲突事件
                self._add_event(
                    TranslationConflictEvent(
                        mod_id=str(self.mod_id),
                        language=language,
                        key=entry.key,
                        existing_value=existing.translated,
                        new_value=entry.translated,
                        timestamp=datetime.now(),
                    )
                )
            existing.translated = entry.translated
            existing.status = entry.status
        else:
            self.translations[language].append(entry)

        self.updated_at = datetime.now()

    def get_translations(self, language: LanguageCode) -> list[TranslationEntry]:
        """获取指定语言的翻译"""
        return self.translations.get(language, [])

    def get_translation_progress(self, language: LanguageCode) -> float:
        """获取翻译进度

        业务规则：
        - 只计算已批准的翻译
        - 返回百分比（0-100）
        """
        if not isinstance(language, LanguageCode):
            raise ValueError("Language must be a LanguageCode instance")

        translations = self.get_translations(language)
        if not translations:
            return 0.0

        total = len(translations)
        approved = sum(1 for t in translations if t.status == "approved")
        return (approved / total) * 100 if total > 0 else 0.0

    def get_translation_statistics(self) -> dict[str, dict[str, int]]:
        """获取翻译统计信息"""
        stats = {}
        for language, entries in self.translations.items():
            stats[language] = {
                "total": len(entries),
                "pending": sum(1 for e in entries if e.status == "pending"),
                "approved": sum(1 for e in entries if e.status == "approved"),
                "rejected": sum(1 for e in entries if e.status == "rejected"),
                "progress": self.get_translation_progress(language),
            }
        return stats

    def mark_as_translated(self, language: LanguageCode):
        """标记为已翻译"""
        self._add_event(
            ModTranslatedEvent(
                mod_id=str(self.mod_id),
                language=language,
                timestamp=datetime.now(),
                progress=self.get_translation_progress(language),
            )
        )
        self.updated_at = datetime.now()

    def needs_rescan(self, new_hash: ContentHash) -> bool:
        """检查是否需要重新扫描"""
        return self.content_hash != new_hash

    def _add_event(self, event):
        """添加领域事件"""
        self.domain_events.append(event)

    def clear_events(self):
        """清除领域事件"""
        self.domain_events = []

    def activate(self):
        """激活Mod"""
        if self.is_active:
            return

        self.is_active = True
        self.updated_at = datetime.now()

    def deactivate(self, reason: str = None):
        """停用Mod

        业务规则：
        - 停用的Mod不能进行扫描和翻译
        """
        if not self.is_active:
            return

        self.is_active = False
        self.scan_status = (
            "failed" if self.scan_status == "scanning" else self.scan_status
        )
        self.translation_lock = False
        self.updated_at = datetime.now()

        if reason:
            self.scan_error_message = reason

    def can_be_deleted(self) -> bool:
        """检查是否可以删除

        业务规则：
        - 只有没有翻译数据的Mod可以删除
        - 或者已停用的Mod可以删除
        """
        has_translations = any(
            len(entries) > 0 for entries in self.translations.values()
        )
        return not has_translations or not self.is_active

    def merge_translations(self, other_mod: "Mod", strategy: str = "override"):
        """合并其他Mod的翻译

        策略：
        - override: 覆盖现有翻译
        - keep: 保留现有翻译
        - newest: 使用最新的翻译
        """
        if self.translation_lock:
            raise ValueError("Cannot merge translations while scanning")

        if not isinstance(other_mod, Mod):
            raise ValueError("Can only merge with another Mod instance")

        for language, entries in other_mod.translations.items():
            if language not in self.translations:
                self.translations[language] = entries.copy()
            else:
                if strategy == "override":
                    self.translations[language] = entries.copy()
                elif strategy == "keep":
                    # 保留现有翻译，只添加新的key
                    existing_keys = {e.key for e in self.translations[language]}
                    for entry in entries:
                        if entry.key not in existing_keys:
                            self.translations[language].append(entry)
                elif strategy == "newest":
                    # 使用最新的翻译（基于updated_at）
                    if other_mod.updated_at > self.updated_at:
                        self.translations[language] = entries.copy()

        self.updated_at = datetime.now()

    def _validate_translation_entry(self, entry: TranslationEntry):
        """验证翻译条目

        业务规则：
        - 必须是TranslationEntry实例
        - 状态必须是有效值
        """
        if not isinstance(entry, TranslationEntry):
            raise ValueError("Entry must be a TranslationEntry instance")

        if entry.status not in ["pending", "approved", "rejected"]:
            raise ValueError(f"Invalid translation status: {entry.status}")

    def to_dict(self) -> dict:
        """转换为字典"""
        return {
            "mod_id": str(self.mod_id),
            "name": self.metadata.name,
            "version": str(self.metadata.version),
            "authors": self.metadata.authors,
            "description": self.metadata.description,
            "minecraft_version": self.metadata.minecraft_version,
            "loader_type": self.metadata.loader_type,
            "file_path": self.file_path,
            "scan_status": self.scan_status,
            "last_scanned": self.last_scanned.isoformat()
            if self.last_scanned
            else None,
            "content_hash": self.content_hash,
            "translation_languages": list(self.translations.keys()),
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
        }

    @classmethod
    def create(cls, mod_id: str, name: str, version: str, file_path: str) -> "Mod":
        """工厂方法：创建新的Mod"""
        return cls(
            mod_id=ModId(mod_id),
            metadata=ModMetadata(
                name=name, version=ModVersion.from_string(version), authors=[]
            ),
            file_path=file_path,
        )
