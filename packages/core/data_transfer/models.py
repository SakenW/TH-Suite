"""
翻译数据传输模型定义

定义了翻译数据传输系统的核心数据结构和类型
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional, Union

import blake3


class GameType(Enum):
    """支持的游戏类型"""
    MINECRAFT = "minecraft"
    RIMWORLD = "rimworld" 
    FACTORIO = "factorio"
    UNKNOWN = "unknown"


class ModLoader(Enum):
    """Minecraft MOD加载器类型"""
    FORGE = "forge"
    FABRIC = "fabric"
    QUILT = "quilt"
    NEOFORGE = "neoforge"
    UNKNOWN = "unknown"


class TranslationStatus(Enum):
    """翻译状态"""
    SOURCE = "source"          # 源文本
    PENDING = "pending"        # 待翻译
    TRANSLATED = "translated"  # 已翻译
    REVIEWED = "reviewed"      # 已审核
    APPROVED = "approved"      # 已批准
    REJECTED = "rejected"      # 已拒绝


class SyncStrategy(Enum):
    """同步策略"""
    FULL = "full"              # 完整同步
    INCREMENTAL = "incremental"  # 增量同步
    FORCE_PUSH = "force_push"  # 强制推送
    FORCE_PULL = "force_pull"  # 强制拉取


class ConflictType(Enum):
    """冲突类型"""
    MODIFY_MODIFY = "modify_modify"  # 双方都修改
    MODIFY_DELETE = "modify_delete"  # 一方修改，一方删除
    ADD_ADD = "add_add"              # 双方都添加相同key


class ConflictResolution(Enum):
    """冲突解决策略"""
    LOCAL = "local"            # 使用本地版本
    REMOTE = "remote"          # 使用远程版本
    MANUAL = "manual"          # 手动解决
    MERGE = "merge"            # 智能合并


@dataclass
class Comment:
    """评论信息"""
    comment_id: str
    author: str
    content: str
    created_at: datetime
    parent_id: Optional[str] = None


@dataclass
class Contributor:
    """贡献者信息"""
    user_id: str
    username: str
    email: Optional[str]
    role: str  # translator, reviewer, admin
    contributions: int = 0


@dataclass
class ModInfo:
    """MOD基础信息"""
    mod_id: str
    name: str
    version: str
    description: Optional[str] = None
    author: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "mod_id": self.mod_id,
            "name": self.name,
            "version": self.version,
            "description": self.description,
            "author": self.author
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> ModInfo:
        return cls(**data)


@dataclass
class MinecraftModInfo(ModInfo):
    """Minecraft MOD信息"""
    loader_type: ModLoader = ModLoader.UNKNOWN
    mc_version: str = ""
    dependencies: List[str] = field(default_factory=list)
    
    def to_dict(self) -> Dict[str, Any]:
        data = super().to_dict()
        data.update({
            "loader_type": self.loader_type.value,
            "mc_version": self.mc_version,
            "dependencies": self.dependencies
        })
        return data
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> MinecraftModInfo:
        data["loader_type"] = ModLoader(data.get("loader_type", "unknown"))
        return cls(**data)


@dataclass
class RimWorldModInfo(ModInfo):
    """RimWorld MOD信息"""
    package_id: str = ""
    supported_versions: List[str] = field(default_factory=list)
    dependencies: List[str] = field(default_factory=list)
    
    def to_dict(self) -> Dict[str, Any]:
        data = super().to_dict()
        data.update({
            "package_id": self.package_id,
            "supported_versions": self.supported_versions,
            "dependencies": self.dependencies
        })
        return data
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> RimWorldModInfo:
        return cls(**data)


@dataclass
class FactorioModInfo(ModInfo):
    """Factorio MOD信息"""
    factorio_version: str = ""
    dependencies: List[str] = field(default_factory=list)
    optional_dependencies: List[str] = field(default_factory=list)
    
    def to_dict(self) -> Dict[str, Any]:
        data = super().to_dict()
        data.update({
            "factorio_version": self.factorio_version,
            "dependencies": self.dependencies,
            "optional_dependencies": self.optional_dependencies
        })
        return data
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> FactorioModInfo:
        return cls(**data)


@dataclass
class TranslationEntry:
    """统一翻译条目模型"""
    
    # 标识信息
    entry_id: str                          # 全局唯一标识
    namespace: str                         # 命名空间 (minecraft, mod:techguns)
    key: str                              # 翻译键名
    
    # 内容信息
    source_text: str                       # 源文本 (通常为英文)
    target_text: Optional[str] = None      # 目标翻译文本
    target_language: str = "zh_cn"         # 目标语言代码
    
    # 上下文信息
    game_type: GameType = GameType.UNKNOWN
    mod_info: Optional[ModInfo] = None
    file_path: str = ""
    category: Optional[str] = None         # 分类 (item, block, entity)
    
    # 元数据
    version: int = 1                       # 版本号
    last_modified: datetime = field(default_factory=datetime.now)
    checksum: str = ""                     # 内容校验和
    status: TranslationStatus = TranslationStatus.PENDING
    
    # 协作信息
    translator: Optional[str] = None       # 翻译者
    reviewer: Optional[str] = None         # 审核者
    comments: List[Comment] = field(default_factory=list)
    
    def __post_init__(self):
        """计算校验和"""
        if not self.checksum:
            self.checksum = self._calculate_checksum()
    
    def _calculate_checksum(self) -> str:
        """计算条目内容校验和"""
        content = f"{self.namespace}:{self.key}:{self.source_text}:{self.target_text or ''}"
        return blake3.blake3(content.encode()).hexdigest()[:16]
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典格式"""
        return {
            "entry_id": self.entry_id,
            "namespace": self.namespace,
            "key": self.key,
            "source_text": self.source_text,
            "target_text": self.target_text,
            "target_language": self.target_language,
            "game_type": self.game_type.value,
            "mod_info": self.mod_info.to_dict() if self.mod_info else None,
            "file_path": self.file_path,
            "category": self.category,
            "version": self.version,
            "last_modified": self.last_modified.isoformat(),
            "checksum": self.checksum,
            "status": self.status.value,
            "translator": self.translator,
            "reviewer": self.reviewer,
            "comments": [
                {
                    "comment_id": c.comment_id,
                    "author": c.author,
                    "content": c.content,
                    "created_at": c.created_at.isoformat(),
                    "parent_id": c.parent_id
                }
                for c in self.comments
            ]
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> TranslationEntry:
        """从字典创建实例"""
        
        # 处理枚举类型
        data["game_type"] = GameType(data.get("game_type", "unknown"))
        data["status"] = TranslationStatus(data.get("status", "pending"))
        
        # 处理日期时间
        if isinstance(data["last_modified"], str):
            data["last_modified"] = datetime.fromisoformat(data["last_modified"])
        
        # 处理MOD信息
        mod_info_data = data.get("mod_info")
        if mod_info_data:
            game_type = data["game_type"]
            if game_type == GameType.MINECRAFT:
                data["mod_info"] = MinecraftModInfo.from_dict(mod_info_data)
            elif game_type == GameType.RIMWORLD:
                data["mod_info"] = RimWorldModInfo.from_dict(mod_info_data)
            elif game_type == GameType.FACTORIO:
                data["mod_info"] = FactorioModInfo.from_dict(mod_info_data)
            else:
                data["mod_info"] = ModInfo.from_dict(mod_info_data)
        
        # 处理评论
        comments_data = data.get("comments", [])
        data["comments"] = [
            Comment(
                comment_id=c["comment_id"],
                author=c["author"],
                content=c["content"],
                created_at=datetime.fromisoformat(c["created_at"]),
                parent_id=c.get("parent_id")
            )
            for c in comments_data
        ]
        
        return cls(**data)


@dataclass
class EntryMove:
    """条目移动记录"""
    entry_id: str
    old_namespace: str
    new_namespace: str
    old_key: str
    new_key: str


@dataclass
class TranslationProject:
    """翻译项目模型"""
    
    project_id: str                        # 项目标识
    name: str                             # 项目名称
    game_type: GameType                   # 游戏类型
    source_language: str = "en_us"        # 源语言
    target_languages: List[str] = field(default_factory=lambda: ["zh_cn"])
    
    # 项目配置
    root_path: str = ""                   # 项目根路径
    includes: List[str] = field(default_factory=list)  # 包含的MOD/包列表
    excludes: List[str] = field(default_factory=list)  # 排除的模式
    
    # 状态统计
    total_entries: int = 0                # 总条目数
    translated_entries: int = 0           # 已翻译数
    reviewed_entries: int = 0             # 已审核数
    
    # 版本信息
    current_version: int = 1              # 当前版本号
    
    # 元数据
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)
    contributors: List[Contributor] = field(default_factory=list)
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典格式"""
        return {
            "project_id": self.project_id,
            "name": self.name,
            "game_type": self.game_type.value,
            "source_language": self.source_language,
            "target_languages": self.target_languages,
            "root_path": self.root_path,
            "includes": self.includes,
            "excludes": self.excludes,
            "total_entries": self.total_entries,
            "translated_entries": self.translated_entries,
            "reviewed_entries": self.reviewed_entries,
            "current_version": self.current_version,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
            "contributors": [
                {
                    "user_id": c.user_id,
                    "username": c.username,
                    "email": c.email,
                    "role": c.role,
                    "contributions": c.contributions
                }
                for c in self.contributors
            ]
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> TranslationProject:
        """从字典创建实例"""
        
        # 处理枚举类型
        data["game_type"] = GameType(data.get("game_type", "unknown"))
        
        # 处理日期时间
        if isinstance(data["created_at"], str):
            data["created_at"] = datetime.fromisoformat(data["created_at"])
        if isinstance(data["updated_at"], str):
            data["updated_at"] = datetime.fromisoformat(data["updated_at"])
        
        # 处理贡献者
        contributors_data = data.get("contributors", [])
        data["contributors"] = [
            Contributor(**c) for c in contributors_data
        ]
        
        return cls(**data)


@dataclass
class TranslationDelta:
    """翻译变更记录"""
    
    delta_id: str                         # 变更标识
    project_id: str                       # 项目标识
    base_version: int                     # 基础版本
    target_version: int                   # 目标版本
    
    # 变更内容
    added: List[TranslationEntry] = field(default_factory=list)     # 新增条目
    modified: List[TranslationEntry] = field(default_factory=list)  # 修改条目
    deleted: List[str] = field(default_factory=list)               # 删除的条目ID
    moved: List[EntryMove] = field(default_factory=list)           # 移动的条目
    
    # 元数据
    timestamp: datetime = field(default_factory=datetime.now)
    author: str = ""
    commit_message: str = ""
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典格式"""
        return {
            "delta_id": self.delta_id,
            "project_id": self.project_id,
            "base_version": self.base_version,
            "target_version": self.target_version,
            "added": [entry.to_dict() for entry in self.added],
            "modified": [entry.to_dict() for entry in self.modified],
            "deleted": self.deleted,
            "moved": [
                {
                    "entry_id": m.entry_id,
                    "old_namespace": m.old_namespace,
                    "new_namespace": m.new_namespace,
                    "old_key": m.old_key,
                    "new_key": m.new_key
                }
                for m in self.moved
            ],
            "timestamp": self.timestamp.isoformat(),
            "author": self.author,
            "commit_message": self.commit_message
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> TranslationDelta:
        """从字典创建实例"""
        
        # 处理日期时间
        if isinstance(data["timestamp"], str):
            data["timestamp"] = datetime.fromisoformat(data["timestamp"])
        
        # 处理条目列表
        data["added"] = [TranslationEntry.from_dict(e) for e in data.get("added", [])]
        data["modified"] = [TranslationEntry.from_dict(e) for e in data.get("modified", [])]
        
        # 处理移动记录
        moved_data = data.get("moved", [])
        data["moved"] = [EntryMove(**m) for m in moved_data]
        
        return cls(**data)


@dataclass
class TranslationConflict:
    """翻译冲突信息"""
    
    entry_id: str                         # 冲突条目ID
    local_entry: TranslationEntry         # 本地条目
    remote_entry: TranslationEntry        # 远程条目
    conflict_type: ConflictType           # 冲突类型
    resolution: Optional[ConflictResolution] = None  # 解决策略
    resolved_entry: Optional[TranslationEntry] = None  # 解决后的条目


@dataclass
class SyncResult:
    """同步结果"""
    
    project_id: str
    success: bool = True
    error: Optional[str] = None
    
    # 统计信息
    pushed_entries: int = 0               # 推送的条目数
    pulled_entries: int = 0               # 拉取的条目数
    conflicts_detected: int = 0           # 检测到的冲突数
    conflicts_resolved: int = 0           # 解决的冲突数
    
    # 详细信息
    conflicts: List[TranslationConflict] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典格式"""
        return {
            "project_id": self.project_id,
            "success": self.success,
            "error": self.error,
            "pushed_entries": self.pushed_entries,
            "pulled_entries": self.pulled_entries,
            "conflicts_detected": self.conflicts_detected,
            "conflicts_resolved": self.conflicts_resolved,
            "warnings": self.warnings
        }


@dataclass 
class IncrementalSyncPlan:
    """增量同步计划"""
    
    to_download: List[str]                # 需要下载的条目ID
    to_upload: List[TranslationEntry]     # 需要上传的条目
    total_entries: int                    # 总条目数
    transfer_ratio: float                 # 传输比例 (0.0-1.0)
    
    estimated_size: int = 0               # 预估传输大小 (字节)
    estimated_time: float = 0.0           # 预估传输时间 (秒)


# 工厂函数
def create_mod_info(game_type: GameType, **kwargs) -> ModInfo:
    """创建对应游戏类型的MOD信息"""
    
    if game_type == GameType.MINECRAFT:
        return MinecraftModInfo(**kwargs)
    elif game_type == GameType.RIMWORLD:
        return RimWorldModInfo(**kwargs)
    elif game_type == GameType.FACTORIO:
        return FactorioModInfo(**kwargs)
    else:
        return ModInfo(**kwargs)


def generate_entry_id(namespace: str, key: str, language: str) -> str:
    """生成翻译条目唯一标识"""
    content = f"{namespace}:{key}:{language}"
    return blake3.blake3(content.encode()).hexdigest()[:16]


def generate_project_id(name: str, game_type: GameType) -> str:
    """生成项目唯一标识"""
    content = f"{game_type.value}:{name}:{datetime.now().isoformat()}"
    return blake3.blake3(content.encode()).hexdigest()[:16]


def generate_delta_id(project_id: str, base_version: int, target_version: int) -> str:
    """生成变更记录唯一标识"""
    content = f"{project_id}:{base_version}:{target_version}:{datetime.now().isoformat()}"
    return blake3.blake3(content.encode()).hexdigest()[:16]