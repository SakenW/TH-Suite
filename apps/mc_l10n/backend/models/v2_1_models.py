"""
TH-Suite v2.1 优化数据库模型
基于 docs/optimization/02-database-optimization.md 的新架构设计

特性:
- 细粒度版本管理
- 数据分层设计 (本地 vs 同步)
- 统一内容映射
- 强大的查询能力
"""

import json
from datetime import datetime
from typing import Any, Dict, List, Optional, Set
from dataclasses import dataclass, field
from enum import Enum

from .data_layer_config import DataLayerConfig, DataLayerValidator


# ============================================================
# 枚举类型定义
# ============================================================

class ProjectType(Enum):
    """项目类型"""
    MODPACK = "modpack"        # 整合包
    MOD = "mod"               # 单独MOD
    RESOURCEPACK = "resourcepack"  # 资源包
    QUESTPACK = "questpack"   # 任务包


class GameType(Enum):
    """游戏类型"""
    MINECRAFT = "minecraft"
    RUSTED_WARFARE = "rusted_warfare"


class LoaderType(Enum):
    """MOD加载器类型"""
    FORGE = "forge"
    FABRIC = "fabric"
    QUILT = "quilt"
    NEOFORGE = "neoforge"


class RelationType(Enum):
    """包-MOD关系类型"""
    INCLUDED = "included"     # 包含
    OPTIONAL = "optional"     # 可选
    DISABLED = "disabled"     # 禁用


class ContentSource(Enum):
    """内容来源类型"""
    MOD_JAR = "mod_jar"           # MOD的JAR文件内容
    PACK_RESOURCE = "pack_resource"  # 整合包资源包
    QUEST_PACK = "quest_pack"     # 任务包内容
    CONFIG_FILE = "config_file"   # 配置文件本地化
    PACK_DOCS = "pack_docs"       # 整合包文档
    OVERRIDE = "override"         # 覆盖性内容


class ContentType(Enum):
    """内容类型"""
    TRANSLATION = "translation"  # 翻译内容
    QUEST = "quest"              # 任务内容
    CONFIG = "config"            # 配置内容


class ChangeType(Enum):
    """变更类型"""
    STABLE = "stable"        # 稳定内容
    MODIFIED = "modified"    # 已修改
    NEW = "new"             # 新增内容
    REMOVED = "removed"     # 已移除


# ============================================================
# 数据模型基类
# ============================================================

@dataclass
class BaseModel:
    """数据模型基类"""
    id: Optional[int] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    
    def to_dict(self, include_none: bool = False) -> Dict[str, Any]:
        """转换为字典"""
        result = {}
        
        for key, value in self.__dict__.items():
            if not include_none and value is None:
                continue
                
            if isinstance(value, Enum):
                result[key] = value.value
            elif isinstance(value, datetime):
                result[key] = value.isoformat()
            elif isinstance(value, (list, dict)):
                result[key] = json.dumps(value) if isinstance(value, (list, dict)) else value
            else:
                result[key] = value
                
        return result
    
    def get_sync_data(self, table_name: str) -> Dict[str, Any]:
        """获取需要同步的数据"""
        full_data = self.to_dict()
        return DataLayerValidator.validate_sync_payload(table_name, full_data)
    
    def get_local_data(self, table_name: str) -> Dict[str, Any]:
        """获取本地数据"""
        return DataLayerValidator.prepare_local_data(table_name, self.to_dict())


# ============================================================
# 核心数据模型
# ============================================================

@dataclass
class Pack(BaseModel):
    """整合包模型"""
    # 同步字段 (业务数据)
    name: str = ""
    project_type: ProjectType = ProjectType.MODPACK
    game_type: GameType = GameType.MINECRAFT
    description: str = ""
    author: str = ""
    
    # 本地字段 (构建数据)
    path: str = ""
    sync_config: Dict[str, Any] = field(default_factory=dict)
    build_config: Dict[str, Any] = field(default_factory=dict)
    
    # 状态字段
    is_active: bool = True
    
    def __post_init__(self):
        if isinstance(self.project_type, str):
            self.project_type = ProjectType(self.project_type)
        if isinstance(self.game_type, str):
            self.game_type = GameType(self.game_type)


@dataclass 
class PackVersion(BaseModel):
    """整合包版本模型"""
    pack_id: int = 0
    
    # 同步字段 (业务数据)
    version_tag: str = ""
    minecraft_version: str = ""
    loader_type: LoaderType = LoaderType.FORGE
    loader_version: str = ""
    display_name: str = ""
    changelog: str = ""
    is_default: bool = False
    is_stable: bool = True
    
    # 本地字段 (构建数据)
    local_path: str = ""
    build_timestamp: Optional[datetime] = None
    
    def __post_init__(self):
        if isinstance(self.loader_type, str):
            self.loader_type = LoaderType(self.loader_type)


@dataclass
class ModVersionInstance(BaseModel):
    """MOD版本实例模型"""
    # 同步字段 (业务数据)
    mod_id: str = ""
    mod_version: str = ""
    mod_name: str = ""
    description: str = ""
    authors: List[str] = field(default_factory=list)
    homepage_url: str = ""
    minecraft_versions: List[str] = field(default_factory=list)
    dependencies: List[Dict[str, Any]] = field(default_factory=list)
    
    # 本地字段 (构建数据)
    jar_file_path: str = ""
    jar_file_size: int = 0
    jar_file_hash: str = ""
    extraction_path: str = ""


@dataclass
class PackModRelation(BaseModel):
    """整合包-MOD关系模型"""
    pack_version_id: int = 0
    mod_instance_id: int = 0
    
    # 同步字段 (业务数据)
    relation_type: RelationType = RelationType.INCLUDED
    load_order: Optional[int] = None
    config_overrides: Dict[str, Any] = field(default_factory=dict)
    
    # 本地字段 (构建数据)
    detected_at: Optional[datetime] = None
    detection_method: str = ""
    
    def __post_init__(self):
        if isinstance(self.relation_type, str):
            self.relation_type = RelationType(self.relation_type)


@dataclass
class ContentInstance(BaseModel):
    """统一内容实例模型"""
    # 同步字段 (业务数据)
    content_key: str = ""
    content_source: ContentSource = ContentSource.MOD_JAR
    source_identifier: str = ""
    source_text: str = ""
    language_code: str = ""
    content_type: ContentType = ContentType.TRANSLATION
    category: str = ""
    comment: str = ""
    priority: int = 0
    is_override: bool = False
    
    # 本地字段 (构建数据)
    file_path: str = ""
    file_format: str = ""
    line_number: Optional[int] = None
    raw_content: str = ""
    
    def __post_init__(self):
        if isinstance(self.content_source, str):
            self.content_source = ContentSource(self.content_source)
        if isinstance(self.content_type, str):
            self.content_type = ContentType(self.content_type)


@dataclass
class PackContentRelation(BaseModel):
    """整合包-内容关系模型"""
    pack_version_id: int = 0
    content_instance_id: int = 0
    
    # 同步字段 (业务数据)
    inclusion_reason: str = ""
    relative_path: str = ""
    overrides_content_id: Optional[int] = None
    override_reason: str = ""
    first_appeared_version: str = ""
    last_modified_version: str = ""
    change_type: ChangeType = ChangeType.STABLE
    
    # 本地字段 (构建数据)
    detected_at: Optional[datetime] = None
    detection_method: str = ""
    
    def __post_init__(self):
        if isinstance(self.change_type, str):
            self.change_type = ChangeType(self.change_type)


# ============================================================
# 统计数据模型
# ============================================================

@dataclass
class PackVersionStats:
    """整合包版本统计数据 (视图模型)"""
    pack_id: int = 0
    pack_name: str = ""
    version_id: int = 0
    version_tag: str = ""
    minecraft_version: str = ""
    
    # MOD统计
    total_mods: int = 0
    included_mods: int = 0
    
    # 内容统计
    total_content: int = 0
    mod_content: int = 0
    pack_resources: int = 0
    quest_content: int = 0
    
    # 语言统计
    supported_languages: int = 0


# ============================================================
# 查询结果模型
# ============================================================

@dataclass
class ContentChangeResult:
    """内容变更查询结果"""
    content_key: str = ""
    content_source: str = ""
    version_1_text: str = ""
    version_2_text: str = ""
    change_type: str = ""


@dataclass
class CrossVersionTrackingResult:
    """跨版本追踪查询结果"""
    pack_name: str = ""
    pack_version: str = ""
    minecraft_version: str = ""
    mod_id: str = ""
    mod_version: str = ""
    source_text: str = ""
    change_type: str = ""
    first_appeared_version: str = ""


@dataclass
class ModDistributionResult:
    """MOD分布查询结果"""
    pack_name: str = ""
    pack_version: str = ""
    minecraft_version: str = ""
    mod_version: str = ""
    relation_type: str = ""
    load_order: Optional[int] = None
    translation_count: int = 0


# ============================================================
# 数据模型工厂
# ============================================================

class ModelFactory:
    """数据模型工厂"""
    
    MODEL_MAPPING = {
        'packs': Pack,
        'pack_versions': PackVersion,
        'mod_version_instances': ModVersionInstance,
        'pack_mod_relations': PackModRelation,
        'content_instances': ContentInstance,
        'pack_content_relations': PackContentRelation,
    }
    
    @classmethod
    def create_model(cls, table_name: str, data: Dict[str, Any]) -> BaseModel:
        """创建数据模型实例"""
        model_class = cls.MODEL_MAPPING.get(table_name)
        if not model_class:
            raise ValueError(f"未知的表名: {table_name}")
        
        # 处理特殊字段
        processed_data = cls._process_data(data)
        
        return model_class(**processed_data)
    
    @classmethod
    def _process_data(cls, data: Dict[str, Any]) -> Dict[str, Any]:
        """预处理数据"""
        processed = data.copy()
        
        # 处理JSON字段
        for key, value in processed.items():
            if isinstance(value, str):
                # 尝试解析JSON字段
                if key in ['sync_config', 'build_config', 'authors', 
                          'minecraft_versions', 'dependencies', 'config_overrides']:
                    try:
                        processed[key] = json.loads(value)
                    except (json.JSONDecodeError, TypeError):
                        pass
                
                # 处理时间戳
                elif key in ['created_at', 'updated_at', 'detected_at', 'build_timestamp']:
                    try:
                        processed[key] = datetime.fromisoformat(value.replace('Z', '+00:00'))
                    except (ValueError, AttributeError):
                        pass
        
        return processed


# ============================================================
# 数据验证器
# ============================================================

class ModelValidator:
    """数据模型验证器"""
    
    @staticmethod
    def validate_pack(pack: Pack) -> List[str]:
        """验证Pack模型"""
        errors = []
        
        if not pack.name.strip():
            errors.append("包名称不能为空")
        
        if not pack.path.strip():
            errors.append("路径不能为空")
        
        return errors
    
    @staticmethod
    def validate_pack_version(version: PackVersion) -> List[str]:
        """验证PackVersion模型"""
        errors = []
        
        if not version.version_tag.strip():
            errors.append("版本标签不能为空")
        
        if not version.minecraft_version.strip():
            errors.append("Minecraft版本不能为空")
        
        return errors
    
    @staticmethod
    def validate_content_instance(content: ContentInstance) -> List[str]:
        """验证ContentInstance模型"""
        errors = []
        
        if not content.content_key.strip():
            errors.append("内容键不能为空")
        
        if not content.source_text.strip():
            errors.append("源文本不能为空")
        
        if not content.language_code.strip():
            errors.append("语言代码不能为空")
        
        return errors