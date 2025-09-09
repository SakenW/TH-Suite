"""
覆盖链处理系统
实现resource_pack > mod > data_pack > override优先级处理
管理翻译条目的优先级合并和锁定字段
"""

from enum import Enum
from dataclasses import dataclass
from typing import List, Dict, Optional, Any, Set, Tuple
import structlog
from database.repositories.translation_entry_repository import TranslationEntry

logger = structlog.get_logger(__name__)


class OverridePriority(Enum):
    """覆盖优先级枚举"""
    RESOURCE_PACK = 1    # 最高优先级：资源包
    MOD = 2              # MOD翻译
    DATA_PACK = 3        # 数据包
    OVERRIDE = 4         # 手动覆盖
    DEFAULT = 5          # 默认/原始翻译
    
    def __lt__(self, other):
        if isinstance(other, OverridePriority):
            return self.value < other.value
        return NotImplemented
    
    def __le__(self, other):
        if isinstance(other, OverridePriority):
            return self.value <= other.value
        return NotImplemented


@dataclass
class OverrideSource:
    """覆盖来源信息"""
    source_type: OverridePriority
    source_id: str  # MOD ID, 资源包名称等
    source_name: str
    version: Optional[str] = None
    pack_uid: Optional[str] = None
    language_file_uid: Optional[str] = None
    
    def get_display_name(self) -> str:
        """获取显示名称"""
        if self.version:
            return f"{self.source_name} v{self.version}"
        return self.source_name


@dataclass
class TranslationOverride:
    """翻译覆盖条目"""
    key: str
    locale: str
    src_text: str
    dst_text: str
    status: str
    source: OverrideSource
    priority: OverridePriority
    locked_fields: Set[str]  # 锁定的字段
    metadata: Dict[str, Any]
    created_at: str
    updated_at: str
    
    # 用于追踪覆盖历史
    overrides: Optional[str] = None  # 被覆盖的条目UID
    overridden_by: Optional[str] = None  # 被哪个条目覆盖
    
    def is_field_locked(self, field: str) -> bool:
        """检查字段是否被锁定"""
        return field in self.locked_fields
    
    def can_be_overridden_by(self, other_priority: OverridePriority) -> bool:
        """检查是否可以被指定优先级覆盖"""
        return other_priority < self.priority
    
    def get_effective_value(self, field: str, fallback_value: Any) -> Any:
        """获取字段的有效值（考虑锁定状态）"""
        if self.is_field_locked(field):
            return getattr(self, field, fallback_value)
        return fallback_value


class OverrideChainProcessor:
    """覆盖链处理器"""
    
    def __init__(self):
        # 预定义优先级映射
        self.priority_mapping = {
            "resource_pack": OverridePriority.RESOURCE_PACK,
            "mod": OverridePriority.MOD,
            "data_pack": OverridePriority.DATA_PACK,
            "override": OverridePriority.OVERRIDE,
            "default": OverridePriority.DEFAULT,
        }
        
        # 默认锁定字段配置
        self.default_locked_fields = {
            OverridePriority.RESOURCE_PACK: {"key", "src_text", "dst_text"},
            OverridePriority.MOD: {"key", "src_text"},
            OverridePriority.DATA_PACK: {"key"},
            OverridePriority.OVERRIDE: set(),
            OverridePriority.DEFAULT: set(),
        }
        
        logger.info("覆盖链处理器初始化完成")
    
    def determine_source_priority(self, source_info: Dict[str, Any]) -> OverridePriority:
        """确定来源优先级"""
        source_type = source_info.get("type", "default").lower()
        
        # 特殊判断逻辑
        if source_type == "resource_pack" or "resource" in source_type:
            return OverridePriority.RESOURCE_PACK
        elif source_type == "mod" or source_info.get("is_mod", False):
            return OverridePriority.MOD
        elif source_type == "data_pack" or "data" in source_type:
            return OverridePriority.DATA_PACK
        elif source_type == "override" or source_info.get("is_manual_override", False):
            return OverridePriority.OVERRIDE
        else:
            return OverridePriority.DEFAULT
    
    def create_override_source(
        self,
        source_type: str,
        source_id: str,
        source_name: str,
        **kwargs
    ) -> OverrideSource:
        """创建覆盖来源"""
        priority = self.priority_mapping.get(source_type.lower(), OverridePriority.DEFAULT)
        
        return OverrideSource(
            source_type=priority,
            source_id=source_id,
            source_name=source_name,
            version=kwargs.get("version"),
            pack_uid=kwargs.get("pack_uid"),
            language_file_uid=kwargs.get("language_file_uid"),
        )
    
    def convert_translation_entry(
        self,
        entry: TranslationEntry,
        source: OverrideSource,
        locked_fields: Optional[Set[str]] = None
    ) -> TranslationOverride:
        """将TranslationEntry转换为TranslationOverride"""
        
        if locked_fields is None:
            locked_fields = self.default_locked_fields.get(source.source_type, set()).copy()
        
        return TranslationOverride(
            key=entry.key,
            locale=entry.locale if hasattr(entry, 'locale') else 'unknown',
            src_text=entry.src_text,
            dst_text=entry.dst_text,
            status=entry.status,
            source=source,
            priority=source.source_type,
            locked_fields=locked_fields,
            metadata=entry.metadata if hasattr(entry, 'metadata') else {},
            created_at=entry.created_at,
            updated_at=entry.updated_at,
        )
    
    def process_override_chain(
        self,
        translations: List[TranslationOverride],
        key: str,
        locale: str
    ) -> Optional[TranslationOverride]:
        """处理单个key的覆盖链"""
        
        # 过滤出相同key和locale的翻译
        matching_translations = [
            t for t in translations
            if t.key == key and t.locale == locale
        ]
        
        if not matching_translations:
            return None
        
        # 按优先级排序（数值越小优先级越高）
        sorted_translations = sorted(matching_translations, key=lambda t: t.priority)
        
        # 获取最高优先级的翻译作为基础
        base_translation = sorted_translations[0]
        
        # 如果只有一个翻译，直接返回
        if len(sorted_translations) == 1:
            return base_translation
        
        # 执行字段级别的覆盖合并
        return self._merge_translation_overrides(sorted_translations)
    
    def _merge_translation_overrides(
        self,
        translations: List[TranslationOverride]
    ) -> TranslationOverride:
        """合并多个翻译覆盖"""
        if not translations:
            raise ValueError("翻译列表不能为空")
        
        # 最高优先级的翻译作为基础
        result = translations[0]
        
        # 记录覆盖历史
        override_sources = []
        
        # 从低优先级到高优先级逐一合并
        for i in range(1, len(translations)):
            current = translations[i]
            
            # 检查每个字段是否可以被覆盖
            mergeable_fields = ["dst_text", "status"]  # 可合并的字段
            
            for field in mergeable_fields:
                # 如果当前字段没有被锁定，且有更高优先级的值，则使用高优先级的值
                if not result.is_field_locked(field):
                    current_value = getattr(current, field)
                    if current_value and current_value != getattr(result, field):
                        setattr(result, field, current_value)
                        
                        # 记录覆盖来源
                        override_sources.append(f"{current.source.get_display_name()}:{field}")
            
            # 合并锁定字段
            if current.priority < result.priority:  # 更高优先级
                result.locked_fields.update(current.locked_fields)
        
        # 更新元数据
        if override_sources:
            result.metadata["override_chain"] = override_sources
            result.metadata["final_priority"] = result.priority.name
        
        logger.debug("翻译覆盖合并完成",
                    key=result.key,
                    final_priority=result.priority.name,
                    override_sources=len(override_sources))
        
        return result
    
    def batch_process_overrides(
        self,
        translations: List[TranslationOverride],
        locale: str
    ) -> Dict[str, TranslationOverride]:
        """批量处理覆盖链"""
        
        # 按key分组
        translations_by_key: Dict[str, List[TranslationOverride]] = {}
        for translation in translations:
            if translation.locale == locale:
                key = translation.key
                if key not in translations_by_key:
                    translations_by_key[key] = []
                translations_by_key[key].append(translation)
        
        # 处理每个key的覆盖链
        results = {}
        for key, key_translations in translations_by_key.items():
            processed = self.process_override_chain(key_translations, key, locale)
            if processed:
                results[key] = processed
        
        logger.info("批量覆盖链处理完成",
                   total_keys=len(translations_by_key),
                   processed_keys=len(results),
                   locale=locale)
        
        return results
    
    def create_manual_override(
        self,
        key: str,
        locale: str,
        dst_text: str,
        user_id: str,
        reason: Optional[str] = None
    ) -> TranslationOverride:
        """创建手动覆盖"""
        
        source = OverrideSource(
            source_type=OverridePriority.OVERRIDE,
            source_id=f"manual_override_{user_id}",
            source_name="手动覆盖",
            version=None
        )
        
        import time
        current_time = str(int(time.time()))
        
        override = TranslationOverride(
            key=key,
            locale=locale,
            src_text="",  # 手动覆盖通常不改变源文本
            dst_text=dst_text,
            status="approved",  # 手动覆盖默认为已审核
            source=source,
            priority=OverridePriority.OVERRIDE,
            locked_fields={"dst_text", "status"},  # 锁定翻译文本和状态
            metadata={
                "user_id": user_id,
                "reason": reason or "手动覆盖",
                "override_type": "manual"
            },
            created_at=current_time,
            updated_at=current_time,
        )
        
        logger.info("创建手动覆盖",
                   key=key,
                   locale=locale,
                   user_id=user_id,
                   reason=reason)
        
        return override
    
    def validate_override_chain(self, translations: List[TranslationOverride]) -> List[Dict[str, Any]]:
        """验证覆盖链的完整性"""
        issues = []
        
        # 按key分组检查
        translations_by_key = {}
        for t in translations:
            key = f"{t.key}:{t.locale}"
            if key not in translations_by_key:
                translations_by_key[key] = []
            translations_by_key[key].append(t)
        
        for key, key_translations in translations_by_key.items():
            # 检查优先级冲突
            priorities = [t.priority for t in key_translations]
            duplicate_priorities = [p for p in set(priorities) if priorities.count(p) > 1]
            
            if duplicate_priorities:
                issues.append({
                    "type": "duplicate_priority",
                    "key": key,
                    "message": f"存在重复优先级: {[p.name for p in duplicate_priorities]}",
                    "severity": "warning"
                })
            
            # 检查锁定字段冲突
            for t in key_translations:
                if t.is_field_locked("key") and any(
                    other.key != t.key for other in key_translations if other != t
                ):
                    issues.append({
                        "type": "locked_key_conflict",
                        "key": key,
                        "message": "key字段被锁定但存在不同值",
                        "severity": "error"
                    })
        
        return issues
    
    def get_override_statistics(self, translations: List[TranslationOverride]) -> Dict[str, Any]:
        """获取覆盖链统计信息"""
        stats = {
            "total_translations": len(translations),
            "by_priority": {},
            "locked_fields_count": {},
            "override_chains": 0,
        }
        
        # 按优先级统计
        for priority in OverridePriority:
            count = len([t for t in translations if t.priority == priority])
            stats["by_priority"][priority.name] = count
        
        # 锁定字段统计
        all_locked_fields = set()
        for t in translations:
            all_locked_fields.update(t.locked_fields)
        
        for field in all_locked_fields:
            count = len([t for t in translations if t.is_field_locked(field)])
            stats["locked_fields_count"][field] = count
        
        # 覆盖链统计
        keys_with_overrides = set()
        for t in translations:
            if t.overrides or t.overridden_by:
                keys_with_overrides.add(f"{t.key}:{t.locale}")
        
        stats["override_chains"] = len(keys_with_overrides)
        
        return stats


# ==================== 全局处理器实例 ====================

_global_override_processor: Optional[OverrideChainProcessor] = None


def get_override_processor() -> OverrideChainProcessor:
    """获取全局覆盖链处理器"""
    global _global_override_processor
    if _global_override_processor is None:
        _global_override_processor = OverrideChainProcessor()
    return _global_override_processor


# ==================== 便捷函数 ====================

def process_translation_overrides(
    entries: List[TranslationEntry],
    locale: str,
    source_mapping: Dict[str, Dict[str, Any]]
) -> Dict[str, TranslationOverride]:
    """便捷函数：处理翻译条目的覆盖链
    
    Args:
        entries: 翻译条目列表
        locale: 目标语言
        source_mapping: 条目UID到来源信息的映射
    
    Returns:
        处理后的覆盖链结果
    """
    processor = get_override_processor()
    overrides = []
    
    for entry in entries:
        source_info = source_mapping.get(entry.uid, {})
        source = processor.create_override_source(
            source_type=source_info.get("type", "default"),
            source_id=source_info.get("id", entry.language_file_uid),
            source_name=source_info.get("name", "Unknown"),
            **source_info
        )
        
        override = processor.convert_translation_entry(entry, source)
        overrides.append(override)
    
    return processor.batch_process_overrides(overrides, locale)


def create_manual_translation_override(
    key: str,
    locale: str,
    dst_text: str,
    user_id: str,
    reason: str = "手动覆盖"
) -> TranslationOverride:
    """便捷函数：创建手动翻译覆盖"""
    processor = get_override_processor()
    return processor.create_manual_override(key, locale, dst_text, user_id, reason)