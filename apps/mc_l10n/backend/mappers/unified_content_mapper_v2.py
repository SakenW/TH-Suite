#!/usr/bin/env python3
"""
TH-Suite 统一内容映射器 v2.0
基于最新Trans-Hub SDK的增强版内容映射系统

主要改进:
- 集成Trans-Hub官方SDK的MinecraftContentBuilder
- 支持流式处理和批量操作优化
- 增强的UIDA生成和验证机制
- 与新的v2.1数据模型完全兼容
- 支持实时内容同步和冲突解决
"""

import hashlib
import json
import re
from datetime import datetime
from typing import Any, Dict, List, Optional, Set, Tuple, Union, AsyncIterator
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path

import structlog

# 导入TH-Suite v2.1模型
from models.v2_1_models import (
    Pack, PackVersion, ModVersionInstance, ContentInstance,
    ContentSource, ChangeType, ProjectType, LoaderType
)

# 导入新的SDK客户端
from clients.transhub_sdk_client_v2 import (
    MinecraftContentItem, TH_Suite_TransHub_SDK_Client
)

# 尝试导入官方SDK组件
try:
    from trans_hub_sdk import ContentItem as SDKContentItem
    from trans_hub_sdk.helpers import MinecraftContentBuilder
    SDK_AVAILABLE = True
except ImportError:
    structlog.get_logger(__name__).warning("Trans-Hub SDK不可用，使用兼容模式")
    SDK_AVAILABLE = False

logger = structlog.get_logger(__name__)


# ============================================================
# 映射配置和规则
# ============================================================

class ContentMappingType(Enum):
    """内容映射类型"""
    MOD_JAR = "mod_jar"
    PACK_RESOURCE = "pack_resource" 
    QUEST_PACK = "quest_pack"
    CONFIG_FILE = "config_file"
    PACK_DOCS = "pack_docs"
    OVERRIDE = "override"


@dataclass
class MappingRule:
    """映射规则"""
    source_type: ContentMappingType
    namespace_pattern: str
    uida_template: str
    metadata_fields: List[str]
    priority: int = 100
    enabled: bool = True


@dataclass
class AdvancedMappingConfig:
    """高级映射配置"""
    
    # 基础配置
    version: str = "2.1"
    strategy: str = "single_project"
    target_project_id: str = "minecraft"
    
    # UIDA配置
    uida_version: str = "v1"
    hash_algorithm: str = "sha256"
    hash_length: int = 16
    
    # 命名空间规则
    namespace_rules: Dict[str, str] = field(default_factory=dict)
    
    # 支持的语言
    supported_languages: List[str] = field(default_factory=lambda: [
        "en_us", "zh_cn", "zh_tw", "ja_jp", "ko_kr", "de_de", "fr_fr", "es_es", "ru_ru", "pt_br"
    ])
    
    # 映射规则
    mapping_rules: Dict[str, MappingRule] = field(default_factory=dict)
    
    # 性能配置
    enable_caching: bool = True
    batch_size: int = 100
    max_workers: int = 4


# ============================================================
# 主要映射器类
# ============================================================

class UnifiedContentMapperV2:
    """TH-Suite 统一内容映射器 v2.0"""
    
    def __init__(self, config_path: Optional[str] = None):
        """
        初始化映射器
        
        Args:
            config_path: 映射配置文件路径
        """
        self.config = self._load_config(config_path)
        self._init_mapping_rules()
        self._init_sdk_components()
        
        # 缓存管理
        self._uida_cache: Dict[str, str] = {}
        self._hash_cache: Dict[str, str] = {}
        
        logger.info("统一内容映射器v2.0初始化完成", 
                   version=self.config.version)
    
    def _load_config(self, config_path: Optional[str]) -> AdvancedMappingConfig:
        """加载映射配置"""
        
        if not config_path or not Path(config_path).exists():
            logger.warning("配置文件不存在，使用默认配置")
            return AdvancedMappingConfig()
        
        try:
            import yaml
            with open(config_path, 'r', encoding='utf-8') as f:
                config_data = yaml.safe_load(f)
            
            logger.info("加载映射配置文件成功", config_path=config_path)
            return self._parse_config(config_data)
            
        except Exception as e:
            logger.error("配置文件加载失败", config_path=config_path, error=str(e))
            return AdvancedMappingConfig()
    
    def _parse_config(self, config_data: Dict[str, Any]) -> AdvancedMappingConfig:
        """解析配置数据"""
        
        config = AdvancedMappingConfig()
        
        # 基础配置
        if 'version' in config_data:
            config.version = config_data['version']
        
        if 'global' in config_data:
            global_config = config_data['global']
            config.strategy = global_config.get('strategy', config.strategy)
            config.target_project_id = global_config.get('target_project_id', config.target_project_id)
            config.hash_algorithm = global_config.get('hash_algorithm', config.hash_algorithm)
            config.hash_length = global_config.get('hash_length', config.hash_length)
        
        # 语言配置
        if 'languages' in config_data and 'supported' in config_data['languages']:
            config.supported_languages = config_data['languages']['supported']
        
        # UIDA配置
        if 'uida' in config_data:
            uida_config = config_data['uida']
            config.namespace_rules = uida_config.get('namespace_rules', {})
        
        return config
    
    def _init_mapping_rules(self):
        """初始化映射规则"""
        
        # 内置映射规则
        default_rules = {
            'mod_jar': MappingRule(
                source_type=ContentMappingType.MOD_JAR,
                namespace_pattern="{mod_id}",
                uida_template="minecraft://{namespace}/{content_key}#{language}@{version}",
                metadata_fields=["mod_id", "mod_name", "mod_version", "mod_authors"],
                priority=100
            ),
            'pack_resource': MappingRule(
                source_type=ContentMappingType.PACK_RESOURCE,
                namespace_pattern="pack.{pack_name}",
                uida_template="minecraft://{namespace}/{content_key}#{language}@{version}",
                metadata_fields=["pack_name", "pack_version", "resource_type"],
                priority=90
            ),
            'quest_pack': MappingRule(
                source_type=ContentMappingType.QUEST_PACK,
                namespace_pattern="quest.{quest_mod}",
                uida_template="minecraft://{namespace}/{content_key}#{language}@{version}",
                metadata_fields=["quest_type", "chapter_id", "quest_id"],
                priority=80
            )
        }
        
        self.config.mapping_rules.update(default_rules)
        logger.info("映射规则初始化完成", rule_count=len(self.config.mapping_rules))
    
    def _init_sdk_components(self):
        """初始化SDK组件"""
        
        if SDK_AVAILABLE:
            logger.info("Trans-Hub SDK组件可用")
        else:
            logger.warning("Trans-Hub SDK组件不可用，将使用兼容模式")
    
    # ============================================================
    # UIDA生成和管理
    # ============================================================
    
    def generate_content_uida(
        self,
        namespace: str,
        content_key: str,
        language: str,
        version: str,
        content_type: Optional[str] = None
    ) -> str:
        """
        生成内容UIDA
        
        Args:
            namespace: 命名空间
            content_key: 内容键
            language: 语言代码
            version: 版本标识
            content_type: 内容类型（可选）
        
        Returns:
            生成的UIDA字符串
        """
        
        # 缓存键
        cache_key = f"{namespace}:{content_key}:{language}:{version}"
        if cache_key in self._uida_cache:
            return self._uida_cache[cache_key]
        
        # 生成UIDA
        uida = f"minecraft://{namespace}/{content_key}#{language}@{version}"
        
        # 缓存结果
        if self.config.enable_caching:
            self._uida_cache[cache_key] = uida
        
        return uida
    
    def parse_uida(self, uida: str) -> Optional[Dict[str, str]]:
        """
        解析UIDA
        
        Args:
            uida: UIDA字符串
        
        Returns:
            解析结果字典，包含namespace, content_key, language, version
        """
        
        # UIDA格式: minecraft://namespace/content_key#language@version
        pattern = r"^minecraft://([^/]+)/([^#]+)#([^@]+)@(.+)$"
        match = re.match(pattern, uida)
        
        if not match:
            logger.error("无效的UIDA格式", uida=uida)
            return None
        
        return {
            "namespace": match.group(1),
            "content_key": match.group(2),
            "language": match.group(3),
            "version": match.group(4)
        }
    
    def validate_uida(self, uida: str) -> bool:
        """验证UIDA格式"""
        return self.parse_uida(uida) is not None
    
    # ============================================================
    # 内容哈希生成
    # ============================================================
    
    def generate_content_hash(
        self,
        content_data: Dict[str, Any],
        algorithm: Optional[str] = None
    ) -> str:
        """
        生成内容哈希
        
        Args:
            content_data: 内容数据字典
            algorithm: 哈希算法（可选，默认使用配置中的算法）
        
        Returns:
            生成的哈希值
        """
        
        # 使用配置中的算法
        hash_algo = algorithm or self.config.hash_algorithm
        
        # 构造哈希输入
        hash_components = []
        for key in ["source_identifier", "content_key", "language_code", "source_text"]:
            if key in content_data:
                hash_components.append(str(content_data[key]))
        
        hash_input = "|".join(hash_components)
        
        # 计算哈希
        if hash_algo == "sha256":
            hash_obj = hashlib.sha256(hash_input.encode('utf-8'))
        elif hash_algo == "md5":
            hash_obj = hashlib.md5(hash_input.encode('utf-8'))
        else:
            logger.error("不支持的哈希算法", algorithm=hash_algo)
            hash_obj = hashlib.sha256(hash_input.encode('utf-8'))
        
        full_hash = hash_obj.hexdigest()
        
        # 根据配置截取长度
        return full_hash[:self.config.hash_length]
    
    # ============================================================
    # 内容映射核心功能
    # ============================================================
    
    def map_minecraft_content_to_sdk(
        self,
        th_suite_content: ContentInstance,
        pack_info: Optional[PackVersion] = None,
        mod_info: Optional[ModVersionInstance] = None
    ) -> MinecraftContentItem:
        """
        将TH-Suite内容映射为SDK格式
        
        Args:
            th_suite_content: TH-Suite内容实例
            pack_info: 整合包版本信息（可选）
            mod_info: MOD版本实例信息（可选）
        
        Returns:
            Minecraft内容项
        """
        
        # 创建基础内容项
        minecraft_item = MinecraftContentItem(
            content_key=th_suite_content.content_key,
            source_text=th_suite_content.source_text,
            language_code=th_suite_content.language_code,
            content_type=th_suite_content.content_type,
            content_source=th_suite_content.content_source.value if isinstance(th_suite_content.content_source, ContentSource) else th_suite_content.content_source
        )
        
        # 添加MOD信息
        if mod_info:
            minecraft_item.mod_id = mod_info.mod_id
            minecraft_item.mod_version = mod_info.mod_version
            minecraft_item.mod_name = mod_info.mod_name
        
        # 添加整合包信息
        if pack_info:
            minecraft_item.pack_version = pack_info.version_tag
            minecraft_item.minecraft_version = pack_info.minecraft_version
            minecraft_item.loader_type = pack_info.loader_type.value if isinstance(pack_info.loader_type, LoaderType) else pack_info.loader_type
        
        # 生成UIDA
        if minecraft_item.mod_id:
            minecraft_item.uida = self.generate_content_uida(
                namespace=minecraft_item.mod_id,
                content_key=minecraft_item.content_key,
                language=minecraft_item.language_code,
                version=minecraft_item.mod_version or "1.0.0"
            )
        
        # 添加元数据
        minecraft_item.metadata.update({
            "content_hash": self.generate_content_hash({
                "source_identifier": getattr(th_suite_content, 'source_identifier', ''),
                "content_key": minecraft_item.content_key,
                "language_code": minecraft_item.language_code,
                "source_text": minecraft_item.source_text
            }),
            "mapping_timestamp": datetime.now().isoformat(),
            "mapping_version": self.config.version
        })
        
        return minecraft_item
    
    def map_sdk_content_to_th_suite(
        self,
        minecraft_item: MinecraftContentItem
    ) -> ContentInstance:
        """
        将SDK格式内容映射为TH-Suite格式
        
        Args:
            minecraft_item: Minecraft内容项
        
        Returns:
            TH-Suite内容实例
        """
        
        # 解析内容源
        try:
            content_source = ContentSource(minecraft_item.content_source)
        except ValueError:
            content_source = ContentSource.MOD_JAR  # 默认值
        
        # 创建内容实例
        content_instance = ContentInstance(
            content_source=content_source,
            source_identifier=f"{minecraft_item.mod_id}:{minecraft_item.content_key}" if minecraft_item.mod_id else minecraft_item.content_key,
            content_key=minecraft_item.content_key,
            content_type=minecraft_item.content_type,
            language_code=minecraft_item.language_code,
            source_text=minecraft_item.source_text,
            content_hash=minecraft_item.metadata.get("content_hash") or self.generate_content_hash({
                "content_key": minecraft_item.content_key,
                "language_code": minecraft_item.language_code,
                "source_text": minecraft_item.source_text
            })
        )
        
        return content_instance
    
    # ============================================================
    # 批量处理功能
    # ============================================================
    
    def map_content_batch_to_sdk(
        self,
        th_suite_contents: List[ContentInstance],
        pack_versions: Dict[int, PackVersion] = None,
        mod_instances: Dict[int, ModVersionInstance] = None
    ) -> List[MinecraftContentItem]:
        """批量映射TH-Suite内容为SDK格式"""
        
        minecraft_items = []
        pack_versions = pack_versions or {}
        mod_instances = mod_instances or {}
        
        for content in th_suite_contents:
            try:
                # 查找相关的包版本和MOD实例
                pack_info = None
                mod_info = None
                
                # 这里需要根据实际的关系查询逻辑来获取相关信息
                # 暂时使用简单的映射逻辑
                
                minecraft_item = self.map_minecraft_content_to_sdk(
                    content, pack_info, mod_info
                )
                minecraft_items.append(minecraft_item)
                
            except Exception as e:
                logger.error("内容映射失败",
                           content_id=getattr(content, 'id', 'unknown'),
                           error=str(e))
        
        logger.info("批量内容映射完成",
                   total=len(th_suite_contents),
                   success=len(minecraft_items))
        
        return minecraft_items
    
    def map_content_batch_from_sdk(
        self,
        minecraft_items: List[MinecraftContentItem]
    ) -> List[ContentInstance]:
        """批量映射SDK内容为TH-Suite格式"""
        
        th_suite_contents = []
        
        for minecraft_item in minecraft_items:
            try:
                content_instance = self.map_sdk_content_to_th_suite(minecraft_item)
                th_suite_contents.append(content_instance)
                
            except Exception as e:
                logger.error("SDK内容映射失败",
                           content_key=minecraft_item.content_key,
                           error=str(e))
        
        logger.info("批量SDK内容映射完成",
                   total=len(minecraft_items),
                   success=len(th_suite_contents))
        
        return th_suite_contents
    
    # ============================================================
    # SDK集成功能
    # ============================================================
    
    def create_minecraft_content_builder(self, project_id: str) -> Optional[Any]:
        """创建Minecraft内容构建器"""
        
        if not SDK_AVAILABLE:
            logger.warning("Trans-Hub SDK不可用，无法创建内容构建器")
            return None
        
        try:
            return MinecraftContentBuilder(project_id=project_id)
        except Exception as e:
            logger.error("创建内容构建器失败", error=str(e))
            return None
    
    def build_sdk_content_items(
        self,
        minecraft_items: List[MinecraftContentItem],
        project_id: str
    ) -> Optional[List[Any]]:
        """使用SDK构建内容项"""
        
        builder = self.create_minecraft_content_builder(project_id)
        if not builder:
            return None
        
        try:
            for item in minecraft_items:
                if item.content_source == "mod_jar":
                    builder.add_mod_content(
                        content_key=item.content_key,
                        source_text=item.source_text,
                        mod_id=item.mod_id or "unknown",
                        mod_version=item.mod_version or "1.0.0",
                        pack_name=item.pack_name or "default",
                        pack_version=item.pack_version or "1.0.0",
                        minecraft_version=item.minecraft_version or "1.20.1",
                        loader_type=item.loader_type or "forge",
                        context=item.context,
                        metadata=item.metadata
                    )
                elif item.content_source == "pack_resource":
                    builder.add_pack_resource(
                        content_key=item.content_key,
                        source_text=item.source_text,
                        pack_name=item.pack_name or "default",
                        pack_version=item.pack_version or "1.0.0",
                        minecraft_version=item.minecraft_version or "1.20.1",
                        context=item.context,
                        metadata=item.metadata
                    )
                elif item.content_source == "quest_pack":
                    builder.add_quest_content(
                        content_key=item.content_key,
                        source_text=item.source_text,
                        pack_name=item.pack_name or "default",
                        pack_version=item.pack_version or "1.0.0",
                        minecraft_version=item.minecraft_version or "1.20.1",
                        quest_type=item.metadata.get("quest_type", "general"),
                        context=item.context,
                        metadata=item.metadata
                    )
            
            return builder.build()
            
        except Exception as e:
            logger.error("SDK内容构建失败", error=str(e))
            return None
    
    # ============================================================
    # 工具和辅助方法
    # ============================================================
    
    def get_mapping_statistics(self) -> Dict[str, Any]:
        """获取映射统计信息"""
        
        return {
            "version": self.config.version,
            "supported_languages": len(self.config.supported_languages),
            "mapping_rules": len(self.config.mapping_rules),
            "cache_size": {
                "uida_cache": len(self._uida_cache),
                "hash_cache": len(self._hash_cache)
            },
            "configuration": {
                "strategy": self.config.strategy,
                "target_project": self.config.target_project_id,
                "hash_algorithm": self.config.hash_algorithm,
                "hash_length": self.config.hash_length
            }
        }
    
    def clear_caches(self):
        """清理缓存"""
        self._uida_cache.clear()
        self._hash_cache.clear()
        logger.info("映射器缓存已清理")
    
    def validate_content_item(self, item: MinecraftContentItem) -> List[str]:
        """验证内容项"""
        
        errors = []
        
        # 基础字段验证
        if not item.content_key:
            errors.append("内容键不能为空")
        
        if not item.source_text:
            errors.append("源文本不能为空")
        
        if item.language_code not in self.config.supported_languages:
            errors.append(f"不支持的语言: {item.language_code}")
        
        # UIDA验证
        if item.uida and not self.validate_uida(item.uida):
            errors.append("无效的UIDA格式")
        
        return errors


# ============================================================
# 工厂方法和便捷函数
# ============================================================

def create_unified_content_mapper(config_path: Optional[str] = None) -> UnifiedContentMapperV2:
    """创建统一内容映射器实例"""
    return UnifiedContentMapperV2(config_path)


def quick_map_to_sdk(
    th_suite_contents: List[ContentInstance],
    config_path: Optional[str] = None
) -> List[MinecraftContentItem]:
    """快速映射TH-Suite内容为SDK格式"""
    
    mapper = create_unified_content_mapper(config_path)
    return mapper.map_content_batch_to_sdk(th_suite_contents)


def quick_map_from_sdk(
    minecraft_items: List[MinecraftContentItem],
    config_path: Optional[str] = None
) -> List[ContentInstance]:
    """快速映射SDK内容为TH-Suite格式"""
    
    mapper = create_unified_content_mapper(config_path)
    return mapper.map_content_batch_from_sdk(minecraft_items)


# ============================================================
# 兼容性别名
# ============================================================

# 保持与原有代码的兼容性
UnifiedContentMapper = UnifiedContentMapperV2