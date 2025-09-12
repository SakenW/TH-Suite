"""
TH-Suite 统一内容映射系统
基于 docs/optimization/04-data-mapping.md 的统一映射策略

特性:
- MOD、整合包、任务包统一处理
- TH-Suite ↔ Trans-Hub 双向映射
- 版本关系完整同步
- UIDA一致性保证
"""

import hashlib
import json
from datetime import datetime
from typing import Any, Dict, List, Optional, Set, Tuple, Union
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path

import structlog

from ..models.v2_1_models import (
    Pack, PackVersion, ModVersionInstance, ContentInstance,
    ContentSource, ContentType, ChangeType
)
from ..clients.transhub_sdk_client import ContentItem, ProjectInfo

logger = structlog.get_logger(__name__)


# ============================================================
# 映射配置和策略
# ============================================================

class MappingStrategy(Enum):
    """映射策略"""
    SINGLE_PROJECT = "single_project"      # 单一项目策略
    MULTI_PROJECT = "multi_project"        # 多项目策略
    HYBRID = "hybrid"                      # 混合策略


@dataclass
class MappingConfig:
    """映射配置"""
    strategy: MappingStrategy = MappingStrategy.SINGLE_PROJECT
    target_project_id: str = "minecraft"
    namespace_separator: str = ":"
    version_separator: str = "@"
    
    # 内容过滤配置
    include_content_sources: Set[ContentSource] = field(default_factory=lambda: {
        ContentSource.MOD_JAR, ContentSource.PACK_RESOURCE, 
        ContentSource.QUEST_PACK, ContentSource.CONFIG_FILE
    })
    
    # 元数据配置
    include_pack_metadata: bool = True
    include_version_metadata: bool = True
    include_mod_metadata: bool = True
    
    # UIDA配置
    uida_hash_length: int = 16
    uida_version: str = "v1"


# ============================================================
# UIDA生成器
# ============================================================

class UIDGenerator:
    """UIDA唯一标识符生成器"""
    
    @staticmethod
    def generate_content_uida(
        content_key: str,
        source_identifier: str,
        language_code: str,
        version: str = "v1"
    ) -> str:
        """生成内容UIDA"""
        # 格式: minecraft://{source_identifier}/{content_key}#{language_code}@{version}
        uida_uri = f"minecraft://{source_identifier}/{content_key}#{language_code}@{version}"
        return uida_uri
    
    @staticmethod
    def generate_content_hash(
        content_key: str,
        source_identifier: str,
        language_code: str,
        source_text: str
    ) -> str:
        """生成内容哈希"""
        # 组合所有关键信息生成稳定的哈希
        content_string = f"{source_identifier}:{content_key}:{language_code}:{source_text}"
        hash_bytes = hashlib.sha256(content_string.encode('utf-8')).hexdigest()
        return hash_bytes[:16]  # 取前16位作为短哈希
    
    @staticmethod
    def generate_pack_version_uida(pack_name: str, version_tag: str) -> str:
        """生成整合包版本UIDA"""
        return f"minecraft-pack://{pack_name}@{version_tag}"
    
    @staticmethod
    def generate_mod_version_uida(mod_id: str, mod_version: str) -> str:
        """生成MOD版本UIDA"""
        return f"minecraft-mod://{mod_id}@{mod_version}"


# ============================================================
# 内容映射器基类
# ============================================================

@dataclass
class MappingResult:
    """映射结果"""
    success: bool
    mapped_items: List[ContentItem] = field(default_factory=list)
    skipped_items: int = 0
    errors: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)


class BaseContentMapper:
    """内容映射器基类"""
    
    def __init__(self, config: MappingConfig):
        self.config = config
        self.uid_generator = UIDGenerator()
    
    def should_map_content(self, instance: ContentInstance) -> bool:
        """判断内容是否应该映射"""
        # 检查内容来源过滤
        if instance.content_source not in self.config.include_content_sources:
            return False
        
        # 检查必要字段
        if not all([
            instance.content_key.strip(),
            instance.source_text.strip(),
            instance.source_identifier.strip(),
            instance.language_code.strip()
        ]):
            return False
        
        return True
    
    def create_base_content_item(
        self,
        instance: ContentInstance,
        pack_version: PackVersion,
        pack: Pack
    ) -> ContentItem:
        """创建基础内容项"""
        # 生成UIDA
        uida_uri = self.uid_generator.generate_content_uida(
            instance.content_key,
            instance.source_identifier,
            instance.language_code,
            self.config.uida_version
        )
        
        uida_hash = self.uid_generator.generate_content_hash(
            instance.content_key,
            instance.source_identifier,
            instance.language_code,
            instance.source_text
        )
        
        # 构建上下文信息
        context = {
            "content_source": instance.content_source.value,
            "content_type": instance.content_type.value,
            "category": instance.category,
            "language": instance.language_code,
        }
        
        # 构建元数据
        metadata = {
            "priority": instance.priority,
            "is_override": instance.is_override,
            "comment": instance.comment,
            "created_at": instance.created_at.isoformat() if instance.created_at else None,
            "updated_at": instance.updated_at.isoformat() if instance.updated_at else None,
        }
        
        # 添加整合包信息
        if self.config.include_pack_metadata:
            metadata.update({
                "pack_name": pack.name,
                "pack_type": pack.project_type.value,
                "pack_description": pack.description,
                "pack_author": pack.author,
            })
        
        # 添加版本信息
        if self.config.include_version_metadata:
            metadata.update({
                "pack_version": pack_version.version_tag,
                "minecraft_version": pack_version.minecraft_version,
                "loader_type": pack_version.loader_type.value,
                "loader_version": pack_version.loader_version,
                "is_default_version": pack_version.is_default,
                "is_stable_version": pack_version.is_stable,
            })
        
        return ContentItem(
            uida_hash=uida_hash,
            uida_uri=uida_uri,
            namespace=instance.source_identifier,
            project_id=self.config.target_project_id,
            keys=[instance.content_key],
            context=context,
            source_text=instance.source_text,
            target_text=None,  # 翻译文本将在后续填充
            metadata=metadata,
            status="active"
        )


# ============================================================
# MOD内容映射器
# ============================================================

class ModContentMapper(BaseContentMapper):
    """MOD内容映射器"""
    
    async def map_mod_content(
        self,
        content_instances: List[ContentInstance],
        mod_instance: ModVersionInstance,
        pack_version: PackVersion,
        pack: Pack
    ) -> MappingResult:
        """映射MOD内容"""
        result = MappingResult(success=True)
        
        try:
            for instance in content_instances:
                if not self.should_map_content(instance):
                    result.skipped_items += 1
                    continue
                
                # 创建基础内容项
                content_item = self.create_base_content_item(instance, pack_version, pack)
                
                # 添加MOD特定元数据
                if self.config.include_mod_metadata:
                    content_item.metadata.update({
                        "mod_id": mod_instance.mod_id,
                        "mod_name": mod_instance.mod_name,
                        "mod_version": mod_instance.mod_version,
                        "mod_description": mod_instance.description,
                        "mod_authors": mod_instance.authors,
                        "mod_homepage": mod_instance.homepage_url,
                        "mod_dependencies": mod_instance.dependencies,
                    })
                
                # 设置MOD特定字段
                content_item.mod_id = mod_instance.mod_id
                content_item.minecraft_version = pack_version.minecraft_version
                content_item.loader_type = pack_version.loader_type.value
                
                result.mapped_items.append(content_item)
            
            logger.info(f"MOD内容映射完成: {len(result.mapped_items)}项")
            
        except Exception as e:
            result.success = False
            result.errors.append(f"MOD内容映射失败: {e}")
            logger.error(f"MOD内容映射失败: {e}")
        
        return result


# ============================================================
# 整合包资源映射器
# ============================================================

class PackResourceMapper(BaseContentMapper):
    """整合包资源映射器"""
    
    async def map_pack_resources(
        self,
        content_instances: List[ContentInstance],
        pack_version: PackVersion,
        pack: Pack
    ) -> MappingResult:
        """映射整合包资源"""
        result = MappingResult(success=True)
        
        try:
            for instance in content_instances:
                if not self.should_map_content(instance):
                    result.skipped_items += 1
                    continue
                
                # 创建基础内容项
                content_item = self.create_base_content_item(instance, pack_version, pack)
                
                # 设置整合包资源特定信息
                content_item.metadata.update({
                    "resource_type": "pack_resource",
                    "is_pack_specific": True,
                })
                
                # 对于覆盖性内容，特殊处理
                if instance.is_override:
                    content_item.metadata.update({
                        "override_priority": instance.priority,
                        "is_override_content": True,
                    })
                
                result.mapped_items.append(content_item)
            
            logger.info(f"整合包资源映射完成: {len(result.mapped_items)}项")
            
        except Exception as e:
            result.success = False
            result.errors.append(f"整合包资源映射失败: {e}")
            logger.error(f"整合包资源映射失败: {e}")
        
        return result


# ============================================================
# 任务包映射器
# ============================================================

class QuestPackMapper(BaseContentMapper):
    """任务包映射器"""
    
    async def map_quest_content(
        self,
        content_instances: List[ContentInstance],
        pack_version: PackVersion,
        pack: Pack
    ) -> MappingResult:
        """映射任务包内容"""
        result = MappingResult(success=True)
        
        try:
            for instance in content_instances:
                if not self.should_map_content(instance):
                    result.skipped_items += 1
                    continue
                
                # 创建基础内容项
                content_item = self.create_base_content_item(instance, pack_version, pack)
                
                # 设置任务包特定信息
                content_item.metadata.update({
                    "content_category": "quest",
                    "quest_type": instance.category,
                    "is_quest_content": True,
                })
                
                # 任务包通常有特殊的命名空间
                quest_namespace = self._extract_quest_namespace(instance.source_identifier)
                content_item.namespace = quest_namespace
                
                result.mapped_items.append(content_item)
            
            logger.info(f"任务包内容映射完成: {len(result.mapped_items)}项")
            
        except Exception as e:
            result.success = False
            result.errors.append(f"任务包内容映射失败: {e}")
            logger.error(f"任务包内容映射失败: {e}")
        
        return result
    
    def _extract_quest_namespace(self, source_identifier: str) -> str:
        """提取任务包命名空间"""
        # 处理常见的任务包标识符格式
        if "ftb" in source_identifier.lower():
            return "ftbquests"
        elif "hqm" in source_identifier.lower():
            return "hardcorequest"
        elif "quest" in source_identifier.lower():
            return source_identifier
        else:
            return f"quest.{source_identifier}"


# ============================================================
# 统一内容映射器
# ============================================================

class UnifiedContentMapper:
    """
    统一内容映射器
    
    协调所有类型内容的映射工作，提供统一的映射接口
    """
    
    def __init__(self, config: Optional[MappingConfig] = None):
        self.config = config or MappingConfig()
        
        # 初始化各类映射器
        self.mod_mapper = ModContentMapper(self.config)
        self.pack_mapper = PackResourceMapper(self.config)
        self.quest_mapper = QuestPackMapper(self.config)
    
    async def map_pack_version_content(
        self,
        pack: Pack,
        pack_version: PackVersion,
        content_data: Dict[str, Any]
    ) -> MappingResult:
        """映射整合包版本的所有内容"""
        result = MappingResult(success=True)
        
        try:
            # 映射不同类型的内容
            for content_source, instances in content_data.items():
                if content_source == ContentSource.MOD_JAR.value:
                    mod_result = await self._map_mod_jar_content(
                        instances, pack_version, pack
                    )
                    self._merge_results(result, mod_result)
                
                elif content_source == ContentSource.PACK_RESOURCE.value:
                    pack_result = await self.pack_mapper.map_pack_resources(
                        instances, pack_version, pack
                    )
                    self._merge_results(result, pack_result)
                
                elif content_source == ContentSource.QUEST_PACK.value:
                    quest_result = await self.quest_mapper.map_quest_content(
                        instances, pack_version, pack
                    )
                    self._merge_results(result, quest_result)
                
                elif content_source in [
                    ContentSource.CONFIG_FILE.value,
                    ContentSource.PACK_DOCS.value,
                    ContentSource.OVERRIDE.value
                ]:
                    # 使用通用映射器处理其他类型
                    generic_result = await self._map_generic_content(
                        instances, pack_version, pack, content_source
                    )
                    self._merge_results(result, generic_result)
            
            # 添加整体元数据
            result.metadata.update({
                "pack_name": pack.name,
                "pack_version": pack_version.version_tag,
                "minecraft_version": pack_version.minecraft_version,
                "total_content_sources": len(content_data),
                "mapping_timestamp": datetime.now().isoformat(),
                "mapping_strategy": self.config.strategy.value,
            })
            
            logger.info(f"整合包版本映射完成: {len(result.mapped_items)}项内容")
            
        except Exception as e:
            result.success = False
            result.errors.append(f"整合包版本映射失败: {e}")
            logger.error(f"整合包版本映射失败: {e}")
        
        return result
    
    async def _map_mod_jar_content(
        self,
        mod_content_data: Dict[str, Any],
        pack_version: PackVersion,
        pack: Pack
    ) -> MappingResult:
        """映射MOD JAR内容"""
        combined_result = MappingResult(success=True)
        
        for mod_id, mod_data in mod_content_data.items():
            # 创建模拟的MOD实例（实际应从数据库获取）
            mod_instance = ModVersionInstance(
                mod_id=mod_id,
                mod_version=mod_data.get('version', '1.0.0'),
                mod_name=mod_data.get('name', mod_id),
                description=mod_data.get('description', ''),
                authors=mod_data.get('authors', []),
            )
            
            # 获取内容实例列表
            content_instances = mod_data.get('content_instances', [])
            
            # 映射MOD内容
            mod_result = await self.mod_mapper.map_mod_content(
                content_instances, mod_instance, pack_version, pack
            )
            
            self._merge_results(combined_result, mod_result)
        
        return combined_result
    
    async def _map_generic_content(
        self,
        instances: List[ContentInstance],
        pack_version: PackVersion,
        pack: Pack,
        content_source: str
    ) -> MappingResult:
        """映射通用内容"""
        result = MappingResult(success=True)
        
        try:
            mapper = BaseContentMapper(self.config)
            
            for instance in instances:
                if not mapper.should_map_content(instance):
                    result.skipped_items += 1
                    continue
                
                content_item = mapper.create_base_content_item(instance, pack_version, pack)
                
                # 添加内容源特定元数据
                content_item.metadata.update({
                    "content_source_type": content_source,
                    "is_generic_content": True,
                })
                
                result.mapped_items.append(content_item)
            
        except Exception as e:
            result.success = False
            result.errors.append(f"通用内容映射失败: {e}")
            logger.error(f"通用内容映射失败: {e}")
        
        return result
    
    def _merge_results(self, target: MappingResult, source: MappingResult):
        """合并映射结果"""
        target.mapped_items.extend(source.mapped_items)
        target.skipped_items += source.skipped_items
        target.errors.extend(source.errors)
        target.warnings.extend(source.warnings)
        target.metadata.update(source.metadata)
        
        if not source.success:
            target.success = False
    
    # ============================================================
    # 反向映射方法
    # ============================================================
    
    async def reverse_map_from_transhub(
        self,
        transhub_content: List[ContentItem]
    ) -> Dict[str, List[ContentInstance]]:
        """从Trans-Hub内容反向映射到本地结构"""
        result = {}
        
        for item in transhub_content:
            try:
                # 从元数据中提取信息
                metadata = item.metadata or {}
                content_source = metadata.get('content_source', 'mod_jar')
                
                # 创建内容实例
                instance = ContentInstance(
                    content_key=item.keys[0] if item.keys else "",
                    content_source=ContentSource(content_source),
                    source_identifier=item.namespace,
                    source_text=item.source_text,
                    language_code=item.context.get('language', 'en_us'),
                    content_type=ContentType(metadata.get('content_type', 'translation')),
                    category=metadata.get('category', ''),
                    comment=metadata.get('comment', ''),
                    priority=metadata.get('priority', 0),
                    is_override=metadata.get('is_override', False),
                )
                
                # 按内容源分组
                if content_source not in result:
                    result[content_source] = []
                
                result[content_source].append(instance)
                
            except Exception as e:
                logger.warning(f"反向映射失败: {e}")
                continue
        
        return result


# ============================================================
# 映射工具类
# ============================================================

class MappingUtilities:
    """映射工具类"""
    
    @staticmethod
    def validate_mapping_config(config: MappingConfig) -> List[str]:
        """验证映射配置"""
        errors = []
        
        if not config.target_project_id.strip():
            errors.append("目标项目ID不能为空")
        
        if config.uida_hash_length < 8 or config.uida_hash_length > 64:
            errors.append("UIDA哈希长度必须在8-64之间")
        
        if not config.include_content_sources:
            errors.append("必须至少包含一种内容源")
        
        return errors
    
    @staticmethod
    def create_default_config() -> MappingConfig:
        """创建默认映射配置"""
        return MappingConfig()
    
    @staticmethod
    def estimate_mapping_size(content_count: int) -> Dict[str, Any]:
        """估算映射大小和性能"""
        # 每个内容项大约的数据大小估算
        avg_item_size_kb = 2  # 平均每项2KB
        
        return {
            "total_items": content_count,
            "estimated_size_mb": (content_count * avg_item_size_kb) / 1024,
            "estimated_mapping_time_sec": content_count * 0.01,  # 每项10ms
            "memory_usage_mb": content_count * 0.05,  # 每项50KB内存
        }