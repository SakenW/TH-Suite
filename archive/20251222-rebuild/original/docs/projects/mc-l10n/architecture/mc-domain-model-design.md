# MC领域模型设计文档

**创建日期**: 2025年8月30日  
**Phase**: 2.1 - MC核心领域模型设计  
**状态**: 设计中  

## 📋 目录
1. [领域模型概述](#领域模型概述)
2. [聚合根设计](#聚合根设计)
3. [实体设计](#实体设计)
4. [值对象设计](#值对象设计)
5. [领域服务设计](#领域服务设计)
6. [仓储接口设计](#仓储接口设计)
7. [领域事件设计](#领域事件设计)

---

## 🌐 领域模型概述

### DDD边界上下文
**MC本地化上下文** (`MC Localization Context`)专注于Minecraft模组的翻译管理，与其他上下文(如用户管理、云端同步)通过定义良好的接口交互。

### 核心聚合识别
基于业务分析，识别出以下核心聚合：

1. **翻译项目聚合** (`Translation Project Aggregate`) - 核心聚合
2. **模组聚合** (`Mod Aggregate`) - 重要聚合  
3. **翻译条目聚合** (`Translation Entry Aggregate`) - 数据聚合
4. **术语库聚合** (`Terminology Aggregate`) - 支持聚合

---

## 🏛 聚合根设计

### 1. TranslationProject (翻译项目聚合根)

**职责**: 管理整个翻译项目的生命周期，协调模组、翻译条目等

```python
# apps/mc-l10n/backend/domain/models/translation_project.py
from typing import List, Dict, Optional
from datetime import datetime
from packages.core.data.models import AggregateRoot
from packages.core.data.models.value_objects import EntityId

class TranslationProject(AggregateRoot):
    """翻译项目聚合根"""
    
    def __init__(
        self,
        project_id: EntityId,
        name: str,
        description: str,
        target_language: LanguageCode,
        source_language: LanguageCode = LanguageCode("en_us"),
        created_at: datetime = None
    ):
        super().__init__(project_id)
        self._name = name
        self._description = description
        self._target_language = target_language
        self._source_language = source_language  
        self._created_at = created_at or datetime.utcnow()
        self._mods: List[ModReference] = []
        self._settings = ProjectSettings()
        self._statistics = ProjectStatistics()
        
    # 核心业务方法
    def add_mod(self, mod: 'Mod') -> None:
        """添加模组到项目"""
        if self._is_mod_already_added(mod.mod_id):
            raise DomainException(f"模组 {mod.mod_id} 已存在于项目中")
            
        mod_ref = ModReference(
            mod_id=mod.mod_id,
            mod_name=mod.name,
            version=mod.version,
            added_at=datetime.utcnow()
        )
        self._mods.append(mod_ref)
        
        # 发布领域事件
        self._add_domain_event(ModAddedToProjectEvent(
            project_id=self.id,
            mod_id=mod.mod_id,
            occurred_at=datetime.utcnow()
        ))
        
    def remove_mod(self, mod_id: ModId) -> None:
        """从项目中移除模组"""
        # 实现移除逻辑...
        pass
        
    def calculate_statistics(self) -> ProjectStatistics:
        """计算项目统计信息"""
        # 计算翻译完成度等统计信息
        pass
        
    # 属性访问器
    @property
    def name(self) -> str:
        return self._name
        
    @property  
    def mods(self) -> List[ModReference]:
        return self._mods.copy()
        
    @property
    def statistics(self) -> ProjectStatistics:
        return self._statistics
```

### 2. Mod (模组聚合根)

**职责**: 管理单个模组的信息、文件结构、翻译内容等

```python
# apps/mc-l10n/backend/domain/models/mod.py
class Mod(AggregateRoot):
    """模组聚合根"""
    
    def __init__(
        self,
        mod_id: ModId,
        name: str,
        version: ModVersion,
        minecraft_version: MinecraftVersion,
        mod_loader: ModLoader,
        file_path: FilePath
    ):
        super().__init__(EntityId(str(mod_id)))
        self._mod_id = mod_id
        self._name = name
        self._version = version
        self._minecraft_version = minecraft_version
        self._mod_loader = mod_loader
        self._file_path = file_path
        self._language_files: Dict[LanguageCode, LanguageFile] = {}
        self._dependencies: List[ModDependency] = []
        self._scan_result: Optional[ModScanResult] = None
        
    def add_language_file(self, language_file: LanguageFile) -> None:
        """添加语言文件"""
        language_code = language_file.language_code
        if language_code in self._language_files:
            # 更新现有文件
            old_file = self._language_files[language_code]
            self._language_files[language_code] = language_file
            
            # 发布语言文件更新事件
            self._add_domain_event(LanguageFileUpdatedEvent(
                mod_id=self._mod_id,
                language_code=language_code,
                old_entry_count=len(old_file.entries),
                new_entry_count=len(language_file.entries)
            ))
        else:
            # 添加新文件
            self._language_files[language_code] = language_file
            
    def get_translation_keys(self) -> List[TranslationKey]:
        """获取所有翻译键"""
        keys = []
        for lang_file in self._language_files.values():
            keys.extend(lang_file.entries.keys())
        return list(set(keys))  # 去重
        
    def get_untranslated_keys(self, target_language: LanguageCode) -> List[TranslationKey]:
        """获取未翻译的键"""
        if target_language not in self._language_files:
            # 如果目标语言文件不存在，返回所有英文键
            en_file = self._language_files.get(LanguageCode("en_us"))
            return list(en_file.entries.keys()) if en_file else []
            
        # 比较英文和目标语言的键
        en_keys = set(self._language_files[LanguageCode("en_us")].entries.keys())
        target_keys = set(self._language_files[target_language].entries.keys())
        return list(en_keys - target_keys)
        
    # 属性访问器
    @property
    def mod_id(self) -> ModId:
        return self._mod_id
        
    @property
    def name(self) -> str:
        return self._name
```

---

## 🏗 实体设计

### 1. LanguageFile (语言文件实体)

```python
# apps/mc-l10n/backend/domain/models/language_file.py
class LanguageFile(Entity):
    """语言文件实体"""
    
    def __init__(
        self,
        file_id: EntityId,
        language_code: LanguageCode,
        file_path: FilePath,
        entries: Dict[TranslationKey, TranslationEntry]
    ):
        super().__init__(file_id)
        self._language_code = language_code
        self._file_path = file_path
        self._entries = entries
        self._last_modified = datetime.utcnow()
        
    def add_entry(self, key: TranslationKey, entry: TranslationEntry) -> None:
        """添加翻译条目"""
        self._entries[key] = entry
        self._last_modified = datetime.utcnow()
        
    def update_entry(self, key: TranslationKey, new_value: str) -> None:
        """更新翻译条目"""
        if key not in self._entries:
            raise DomainException(f"翻译键 {key} 不存在")
            
        old_entry = self._entries[key]
        new_entry = TranslationEntry(
            key=key,
            value=new_value,
            original_value=old_entry.original_value,
            last_modified=datetime.utcnow(),
            status=TranslationStatus.TRANSLATED
        )
        self._entries[key] = new_entry
        self._last_modified = datetime.utcnow()
```

### 2. TranslationEntry (翻译条目实体)

```python
# apps/mc-l10n/backend/domain/models/translation_entry.py
class TranslationEntry(Entity):
    """翻译条目实体"""
    
    def __init__(
        self,
        entry_id: EntityId,
        key: TranslationKey,
        value: str,
        original_value: str,
        status: TranslationStatus = TranslationStatus.UNTRANSLATED,
        context: Optional[str] = None,
        notes: Optional[str] = None
    ):
        super().__init__(entry_id)
        self._key = key
        self._value = value
        self._original_value = original_value
        self._status = status
        self._context = context
        self._notes = notes
        self._last_modified = datetime.utcnow()
        self._translator: Optional[str] = None
        self._reviewer: Optional[str] = None
        
    def translate(self, new_value: str, translator: str) -> None:
        """执行翻译"""
        self._value = new_value
        self._status = TranslationStatus.TRANSLATED
        self._translator = translator
        self._last_modified = datetime.utcnow()
        
    def review(self, reviewer: str, approved: bool) -> None:
        """审核翻译"""
        self._reviewer = reviewer
        self._status = TranslationStatus.APPROVED if approved else TranslationStatus.NEEDS_REVIEW
        self._last_modified = datetime.utcnow()
```

---

## 💎 值对象设计

### 1. ModId (模组ID值对象)

```python
# apps/mc-l10n/backend/domain/models/value_objects/mod_id.py
from packages.core.data.models import ValueObject

class ModId(ValueObject):
    """模组ID值对象"""
    
    def __init__(self, value: str):
        if not value or not self._is_valid_mod_id(value):
            raise ValueError(f"无效的模组ID: {value}")
        self._value = value.lower()  # 模组ID通常是小写
        
    @staticmethod
    def _is_valid_mod_id(value: str) -> bool:
        """验证模组ID格式"""
        import re
        # 模组ID只能包含字母、数字、下划线和连字符
        pattern = r'^[a-zA-Z][a-zA-Z0-9_-]*$'
        return bool(re.match(pattern, value)) and len(value) <= 64
        
    @property
    def value(self) -> str:
        return self._value
        
    def __str__(self) -> str:
        return self._value
```

### 2. TranslationKey (翻译键值对象)

```python
# apps/mc-l10n/backend/domain/models/value_objects/translation_key.py
class TranslationKey(ValueObject):
    """翻译键值对象"""
    
    def __init__(self, value: str):
        if not value:
            raise ValueError("翻译键不能为空")
        self._value = value
        self._parsed = self._parse_key(value)
        
    def _parse_key(self, key: str) -> Dict[str, str]:
        """解析翻译键结构"""
        parts = key.split('.')
        if len(parts) < 2:
            return {"type": "unknown", "identifier": key}
            
        return {
            "type": parts[0],  # item, block, gui, etc.
            "mod_id": parts[1] if len(parts) > 2 else "minecraft",
            "identifier": '.'.join(parts[2:]) if len(parts) > 2 else parts[1],
            "full_key": key
        }
        
    @property
    def value(self) -> str:
        return self._value
        
    @property
    def type(self) -> str:
        """获取翻译键类型 (item, block, gui等)"""
        return self._parsed["type"]
        
    @property
    def mod_id(self) -> str:
        """获取关联的模组ID"""
        return self._parsed["mod_id"]
        
    def is_item_key(self) -> bool:
        return self.type == "item"
        
    def is_block_key(self) -> bool:
        return self.type == "block"
        
    def is_gui_key(self) -> bool:
        return self.type == "gui"
```

### 3. LanguageCode (语言代码值对象)

```python
# apps/mc-l10n/backend/domain/models/value_objects/language_code.py
class LanguageCode(ValueObject):
    """语言代码值对象"""
    
    # 支持的语言代码映射
    SUPPORTED_LANGUAGES = {
        "en_us": "English (US)",
        "zh_cn": "简体中文", 
        "zh_tw": "繁體中文",
        "ja_jp": "日本語",
        "ko_kr": "한국어",
        "fr_fr": "Français",
        "de_de": "Deutsch",
        "es_es": "Español",
        "ru_ru": "Русский"
    }
    
    def __init__(self, code: str):
        normalized_code = code.lower().replace('-', '_')
        if normalized_code not in self.SUPPORTED_LANGUAGES:
            raise ValueError(f"不支持的语言代码: {code}")
        self._code = normalized_code
        
    @property
    def code(self) -> str:
        return self._code
        
    @property 
    def display_name(self) -> str:
        return self.SUPPORTED_LANGUAGES[self._code]
        
    def is_chinese(self) -> bool:
        return self._code in ["zh_cn", "zh_tw"]
        
    def is_english(self) -> bool:
        return self._code == "en_us"
```

### 4. ModVersion (模组版本值对象)

```python
# apps/mc-l10n/backend/domain/models/value_objects/mod_version.py
class ModVersion(ValueObject):
    """模组版本值对象"""
    
    def __init__(self, version_string: str):
        if not version_string:
            raise ValueError("版本号不能为空")
        self._version_string = version_string
        self._parsed = self._parse_version(version_string)
        
    def _parse_version(self, version: str) -> Dict:
        """解析版本号"""
        import re
        
        # 尝试解析语义化版本号 (major.minor.patch)
        semver_pattern = r'^(\d+)\.(\d+)\.(\d+)(?:-(.+))?(?:\+(.+))?$'
        match = re.match(semver_pattern, version)
        
        if match:
            return {
                "major": int(match.group(1)),
                "minor": int(match.group(2)), 
                "patch": int(match.group(3)),
                "pre_release": match.group(4),
                "build": match.group(5),
                "type": "semver"
            }
        
        # 如果不是标准语义化版本，作为普通字符串处理
        return {
            "raw": version,
            "type": "string"
        }
        
    def is_newer_than(self, other: 'ModVersion') -> bool:
        """比较版本新旧"""
        if self._parsed["type"] == "semver" and other._parsed["type"] == "semver":
            # 语义化版本比较
            for field in ["major", "minor", "patch"]:
                if self._parsed[field] > other._parsed[field]:
                    return True
                elif self._parsed[field] < other._parsed[field]:
                    return False
            return False
        
        # 字符串比较
        return self._version_string > other._version_string
```

---

## 🎯 枚举类型设计

```python
# apps/mc-l10n/backend/domain/models/enums.py
from enum import Enum

class TranslationStatus(Enum):
    """翻译状态"""
    UNTRANSLATED = "untranslated"      # 未翻译
    IN_PROGRESS = "in_progress"        # 翻译中
    TRANSLATED = "translated"          # 已翻译
    NEEDS_REVIEW = "needs_review"      # 需要审核
    APPROVED = "approved"              # 已审核通过
    REJECTED = "rejected"              # 审核不通过

class ModLoader(Enum):
    """模组加载器类型"""
    FORGE = "forge"
    FABRIC = "fabric"
    QUILT = "quilt"
    NEOFORGE = "neoforge"
    
class FileType(Enum):
    """文件类型"""
    JSON = "json"
    PROPERTIES = "properties"
    YAML = "yaml"
    
class ProjectStatus(Enum):
    """项目状态"""
    ACTIVE = "active"
    COMPLETED = "completed"
    ARCHIVED = "archived"
    SUSPENDED = "suspended"
```

---

## 🎭 领域服务设计

基于业务分析识别的复杂业务逻辑，设计以下领域服务：

### 1. ModAnalyzerService (模组分析服务)

```python
# apps/mc-l10n/backend/domain/services/mod_analyzer_service.py
class ModAnalyzerService:
    """模组分析领域服务"""
    
    def analyze_mod(self, file_path: FilePath) -> ModAnalysisResult:
        """分析模组文件，提取基本信息"""
        pass
        
    def extract_mod_metadata(self, mod_content: bytes) -> ModMetadata:
        """提取模组元数据"""
        pass
        
    def detect_mod_loader(self, mod_content: bytes) -> ModLoader:
        """检测模组加载器类型"""
        pass
```

### 2. TranslationConsistencyService (翻译一致性服务)

```python 
# apps/mc-l10n/backend/domain/services/translation_consistency_service.py
class TranslationConsistencyService:
    """翻译一致性领域服务"""
    
    def check_terminology_consistency(
        self, 
        entries: List[TranslationEntry],
        terminology: TerminologyDict
    ) -> List[ConsistencyIssue]:
        """检查术语一致性"""
        pass
        
    def suggest_translations(
        self,
        key: TranslationKey,
        original_text: str,
        translation_memory: TranslationMemory
    ) -> List[TranslationSuggestion]:
        """基于翻译记忆提供翻译建议"""
        pass
```

---

## 📦 仓储接口设计

```python
# apps/mc-l10n/backend/domain/repositories/
from abc import ABC, abstractmethod

class ITranslationProjectRepository(ABC):
    """翻译项目仓储接口"""
    
    @abstractmethod
    async def find_by_id(self, project_id: EntityId) -> Optional[TranslationProject]:
        pass
        
    @abstractmethod
    async def save(self, project: TranslationProject) -> None:
        pass
        
    @abstractmethod
    async def find_by_name(self, name: str) -> Optional[TranslationProject]:
        pass

class IModRepository(ABC):
    """模组仓储接口"""
    
    @abstractmethod
    async def find_by_mod_id(self, mod_id: ModId) -> Optional[Mod]:
        pass
        
    @abstractmethod
    async def save(self, mod: Mod) -> None:
        pass
        
    @abstractmethod
    async def find_mods_by_project(self, project_id: EntityId) -> List[Mod]:
        pass

class ITranslationEntryRepository(ABC):
    """翻译条目仓储接口"""
    
    @abstractmethod
    async def find_by_mod_and_language(
        self, 
        mod_id: ModId, 
        language: LanguageCode
    ) -> List[TranslationEntry]:
        pass
        
    @abstractmethod
    async def save_entries(self, entries: List[TranslationEntry]) -> None:
        pass
```

---

## 📡 领域事件设计

```python
# apps/mc-l10n/backend/domain/events/
from packages.core.framework.events import DomainEvent

class ProjectCreatedEvent(DomainEvent):
    """项目创建事件"""
    def __init__(self, project_id: EntityId, project_name: str):
        super().__init__()
        self.project_id = project_id
        self.project_name = project_name

class ModAddedToProjectEvent(DomainEvent):
    """模组添加到项目事件"""
    def __init__(self, project_id: EntityId, mod_id: ModId):
        super().__init__()
        self.project_id = project_id
        self.mod_id = mod_id

class TranslationCompletedEvent(DomainEvent):
    """翻译完成事件"""  
    def __init__(self, entry_id: EntityId, translator: str):
        super().__init__()
        self.entry_id = entry_id
        self.translator = translator
```

---

## 📋 总结

这个领域模型设计完成了：

1. **✅ 聚合根设计** - TranslationProject和Mod作为核心聚合
2. **✅ 实体设计** - LanguageFile、TranslationEntry等核心实体
3. **✅ 值对象设计** - ModId、TranslationKey、LanguageCode等强类型值对象
4. **✅ 领域服务设计** - 处理复杂业务逻辑的服务
5. **✅ 仓储接口** - 数据访问的抽象接口
6. **✅ 领域事件** - 支持事件驱动架构

**下一步**: 开始Phase 2.2 - 实现领域服务，然后进入Phase 2.3基础设施层开发。