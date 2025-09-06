"""
Mod聚合根
Minecraft模组的核心领域模型
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Dict, List, Optional, Set
from uuid import UUID, uuid4

from ..events import ModScannedEvent, ModTranslatedEvent, TranslationConflictEvent
from ..repositories import ModRepository


@dataclass
class ModId:
    """Mod ID值对象"""
    value: str
    
    def __post_init__(self):
        if not self.value or not isinstance(self.value, str):
            raise ValueError("ModId must be a non-empty string")
    
    def __str__(self) -> str:
        return self.value
    
    def __eq__(self, other) -> bool:
        if not isinstance(other, ModId):
            return False
        return self.value == other.value
    
    def __hash__(self) -> int:
        return hash(self.value)


@dataclass
class ModVersion:
    """Mod版本值对象"""
    major: int
    minor: int
    patch: int
    build: Optional[str] = None
    
    @classmethod
    def from_string(cls, version_str: str) -> 'ModVersion':
        """从字符串解析版本"""
        parts = version_str.split('.')
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
    
    def __lt__(self, other: 'ModVersion') -> bool:
        return (self.major, self.minor, self.patch) < (other.major, other.minor, other.patch)


@dataclass
class TranslationEntry:
    """翻译条目值对象"""
    key: str
    original: str
    translated: str
    language: str
    status: str = "pending"  # pending, approved, rejected
    translator: Optional[str] = None
    reviewed_by: Optional[str] = None
    
    def approve(self, reviewer: str):
        """批准翻译"""
        self.status = "approved"
        self.reviewed_by = reviewer
    
    def reject(self, reviewer: str):
        """拒绝翻译"""
        self.status = "rejected"
        self.reviewed_by = reviewer


@dataclass
class ModMetadata:
    """Mod元数据值对象"""
    name: str
    version: ModVersion
    authors: List[str]
    description: Optional[str] = None
    minecraft_version: Optional[str] = None
    loader_type: Optional[str] = None  # forge, fabric, quilt
    dependencies: List[str] = field(default_factory=list)
    tags: Set[str] = field(default_factory=set)
    
    def add_tag(self, tag: str):
        """添加标签"""
        self.tags.add(tag)
    
    def remove_tag(self, tag: str):
        """移除标签"""
        self.tags.discard(tag)


class Mod:
    """Mod聚合根"""
    
    def __init__(
        self,
        mod_id: ModId,
        metadata: ModMetadata,
        file_path: str
    ):
        self.mod_id = mod_id
        self.metadata = metadata
        self.file_path = file_path
        self.translations: Dict[str, List[TranslationEntry]] = {}
        self.scan_status = "pending"  # pending, scanning, completed, failed
        self.last_scanned = None
        self.content_hash = None
        self.domain_events = []
        self.created_at = datetime.now()
        self.updated_at = datetime.now()
    
    def scan_completed(self, content_hash: str, translation_count: int):
        """扫描完成"""
        self.scan_status = "completed"
        self.last_scanned = datetime.now()
        self.content_hash = content_hash
        self.updated_at = datetime.now()
        
        # 发布领域事件
        self._add_event(ModScannedEvent(
            mod_id=str(self.mod_id),
            timestamp=datetime.now(),
            translation_count=translation_count,
            content_hash=content_hash
        ))
    
    def scan_failed(self, error: str):
        """扫描失败"""
        self.scan_status = "failed"
        self.updated_at = datetime.now()
    
    def add_translation(self, language: str, entry: TranslationEntry):
        """添加翻译"""
        if language not in self.translations:
            self.translations[language] = []
        
        # 检查是否存在相同的key
        existing = next(
            (t for t in self.translations[language] if t.key == entry.key),
            None
        )
        
        if existing:
            if existing.translated != entry.translated:
                # 发布冲突事件
                self._add_event(TranslationConflictEvent(
                    mod_id=str(self.mod_id),
                    language=language,
                    key=entry.key,
                    existing_value=existing.translated,
                    new_value=entry.translated,
                    timestamp=datetime.now()
                ))
            existing.translated = entry.translated
            existing.status = entry.status
        else:
            self.translations[language].append(entry)
        
        self.updated_at = datetime.now()
    
    def get_translations(self, language: str) -> List[TranslationEntry]:
        """获取指定语言的翻译"""
        return self.translations.get(language, [])
    
    def get_translation_progress(self, language: str) -> float:
        """获取翻译进度"""
        translations = self.get_translations(language)
        if not translations:
            return 0.0
        
        total = len(translations)
        approved = sum(1 for t in translations if t.status == "approved")
        return (approved / total) * 100 if total > 0 else 0.0
    
    def mark_as_translated(self, language: str):
        """标记为已翻译"""
        self._add_event(ModTranslatedEvent(
            mod_id=str(self.mod_id),
            language=language,
            timestamp=datetime.now(),
            progress=self.get_translation_progress(language)
        ))
        self.updated_at = datetime.now()
    
    def needs_rescan(self, new_hash: str) -> bool:
        """检查是否需要重新扫描"""
        return self.content_hash != new_hash
    
    def _add_event(self, event):
        """添加领域事件"""
        self.domain_events.append(event)
    
    def clear_events(self):
        """清除领域事件"""
        self.domain_events = []
    
    def to_dict(self) -> Dict:
        """转换为字典"""
        return {
            'mod_id': str(self.mod_id),
            'name': self.metadata.name,
            'version': str(self.metadata.version),
            'authors': self.metadata.authors,
            'description': self.metadata.description,
            'minecraft_version': self.metadata.minecraft_version,
            'loader_type': self.metadata.loader_type,
            'file_path': self.file_path,
            'scan_status': self.scan_status,
            'last_scanned': self.last_scanned.isoformat() if self.last_scanned else None,
            'content_hash': self.content_hash,
            'translation_languages': list(self.translations.keys()),
            'created_at': self.created_at.isoformat(),
            'updated_at': self.updated_at.isoformat()
        }
    
    @classmethod
    def create(cls, mod_id: str, name: str, version: str, file_path: str) -> 'Mod':
        """工厂方法：创建新的Mod"""
        return cls(
            mod_id=ModId(mod_id),
            metadata=ModMetadata(
                name=name,
                version=ModVersion.from_string(version),
                authors=[]
            ),
            file_path=file_path
        )