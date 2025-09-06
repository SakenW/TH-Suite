"""
冲突解决
提供多种冲突解决策略
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Union
from datetime import datetime
import json
import difflib
import logging

logger = logging.getLogger(__name__)


@dataclass
class ConflictItem:
    """冲突项"""
    id: str
    local_value: Any
    remote_value: Any
    base_value: Optional[Any] = None
    local_timestamp: Optional[datetime] = None
    remote_timestamp: Optional[datetime] = None
    metadata: Dict[str, Any] = None
    
    def __post_init__(self):
        if self.metadata is None:
            self.metadata = {}


@dataclass
class ConflictResolution:
    """冲突解决结果"""
    resolved_value: Any
    strategy_used: str
    confidence: float  # 0.0-1.0
    manual_review_required: bool = False
    notes: Optional[str] = None


class ConflictResolver(ABC):
    """冲突解决器基类"""
    
    @abstractmethod
    def resolve(self, conflict: ConflictItem) -> ConflictResolution:
        """解决冲突"""
        pass
    
    def can_resolve(self, conflict: ConflictItem) -> bool:
        """是否能解决此冲突"""
        return True


class TimestampResolver(ConflictResolver):
    """基于时间戳的解决器"""
    
    def __init__(self, prefer_newest: bool = True):
        self.prefer_newest = prefer_newest
    
    def can_resolve(self, conflict: ConflictItem) -> bool:
        """检查是否有时间戳信息"""
        return conflict.local_timestamp is not None and conflict.remote_timestamp is not None
    
    def resolve(self, conflict: ConflictItem) -> ConflictResolution:
        """使用时间戳解决冲突"""
        if not self.can_resolve(conflict):
            raise ValueError("Missing timestamp information")
        
        if self.prefer_newest:
            if conflict.local_timestamp > conflict.remote_timestamp:
                return ConflictResolution(
                    resolved_value=conflict.local_value,
                    strategy_used="newest_wins",
                    confidence=0.9
                )
            else:
                return ConflictResolution(
                    resolved_value=conflict.remote_value,
                    strategy_used="newest_wins",
                    confidence=0.9
                )
        else:
            if conflict.local_timestamp < conflict.remote_timestamp:
                return ConflictResolution(
                    resolved_value=conflict.local_value,
                    strategy_used="oldest_wins",
                    confidence=0.9
                )
            else:
                return ConflictResolution(
                    resolved_value=conflict.remote_value,
                    strategy_used="oldest_wins",
                    confidence=0.9
                )


class ThreeWayMergeResolver(ConflictResolver):
    """三路合并解决器"""
    
    def can_resolve(self, conflict: ConflictItem) -> bool:
        """检查是否有基础版本"""
        return conflict.base_value is not None
    
    def resolve(self, conflict: ConflictItem) -> ConflictResolution:
        """使用三路合并解决冲突"""
        if not self.can_resolve(conflict):
            raise ValueError("Missing base value for three-way merge")
        
        # 如果是字符串，使用diff3算法
        if isinstance(conflict.local_value, str):
            return self._merge_strings(conflict)
        
        # 如果是字典，尝试合并
        elif isinstance(conflict.local_value, dict):
            return self._merge_dicts(conflict)
        
        # 如果是列表，尝试合并
        elif isinstance(conflict.local_value, list):
            return self._merge_lists(conflict)
        
        # 其他类型，无法自动合并
        else:
            return ConflictResolution(
                resolved_value=conflict.local_value,
                strategy_used="three_way_merge_failed",
                confidence=0.0,
                manual_review_required=True,
                notes="Cannot automatically merge this type"
            )
    
    def _merge_strings(self, conflict: ConflictItem) -> ConflictResolution:
        """合并字符串"""
        base_lines = conflict.base_value.splitlines(keepends=True)
        local_lines = conflict.local_value.splitlines(keepends=True)
        remote_lines = conflict.remote_value.splitlines(keepends=True)
        
        # 使用difflib进行三路合并
        merger = difflib.Differ()
        
        # 计算差异
        local_diff = list(merger.compare(base_lines, local_lines))
        remote_diff = list(merger.compare(base_lines, remote_lines))
        
        # 简单的合并策略：如果只有一方修改，使用修改的版本
        local_changed = any(line.startswith(('+', '-')) for line in local_diff)
        remote_changed = any(line.startswith(('+', '-')) for line in remote_diff)
        
        if local_changed and not remote_changed:
            return ConflictResolution(
                resolved_value=conflict.local_value,
                strategy_used="three_way_merge_local",
                confidence=0.95
            )
        elif remote_changed and not local_changed:
            return ConflictResolution(
                resolved_value=conflict.remote_value,
                strategy_used="three_way_merge_remote",
                confidence=0.95
            )
        else:
            # 两边都有修改，需要手动解决
            return ConflictResolution(
                resolved_value=conflict.local_value,
                strategy_used="three_way_merge_conflict",
                confidence=0.0,
                manual_review_required=True,
                notes="Both sides modified the same content"
            )
    
    def _merge_dicts(self, conflict: ConflictItem) -> ConflictResolution:
        """合并字典"""
        base_dict = conflict.base_value
        local_dict = conflict.local_value
        remote_dict = conflict.remote_value
        
        merged = {}
        all_keys = set(local_dict.keys()) | set(remote_dict.keys())
        conflicts_found = False
        
        for key in all_keys:
            base_val = base_dict.get(key)
            local_val = local_dict.get(key)
            remote_val = remote_dict.get(key)
            
            # 如果只有一方修改
            if local_val == base_val and remote_val != base_val:
                merged[key] = remote_val
            elif remote_val == base_val and local_val != base_val:
                merged[key] = local_val
            elif local_val == remote_val:
                merged[key] = local_val
            else:
                # 冲突，使用本地值但标记需要审查
                merged[key] = local_val
                conflicts_found = True
        
        return ConflictResolution(
            resolved_value=merged,
            strategy_used="three_way_merge_dict",
            confidence=0.7 if not conflicts_found else 0.3,
            manual_review_required=conflicts_found,
            notes="Dictionary merged with conflicts" if conflicts_found else "Dictionary merged successfully"
        )
    
    def _merge_lists(self, conflict: ConflictItem) -> ConflictResolution:
        """合并列表"""
        # 简单策略：合并两个列表的唯一元素
        local_set = set(conflict.local_value)
        remote_set = set(conflict.remote_value)
        
        merged = list(local_set | remote_set)
        
        return ConflictResolution(
            resolved_value=merged,
            strategy_used="three_way_merge_list_union",
            confidence=0.6,
            manual_review_required=True,
            notes="Lists merged using union strategy"
        )


class FieldLevelResolver(ConflictResolver):
    """字段级别解决器（适用于结构化数据）"""
    
    def __init__(self, field_strategies: Dict[str, str]):
        """
        Args:
            field_strategies: 字段到策略的映射
                - 'local': 使用本地值
                - 'remote': 使用远程值
                - 'merge': 合并值
                - 'newest': 使用最新值
        """
        self.field_strategies = field_strategies
    
    def resolve(self, conflict: ConflictItem) -> ConflictResolution:
        """解决字段级冲突"""
        if not isinstance(conflict.local_value, dict):
            raise ValueError("Field-level resolver requires dict values")
        
        merged = {}
        confidence_scores = []
        
        for field, strategy in self.field_strategies.items():
            local_field = conflict.local_value.get(field)
            remote_field = conflict.remote_value.get(field)
            
            if strategy == 'local':
                merged[field] = local_field
                confidence_scores.append(1.0)
            elif strategy == 'remote':
                merged[field] = remote_field
                confidence_scores.append(1.0)
            elif strategy == 'merge':
                if isinstance(local_field, list) and isinstance(remote_field, list):
                    merged[field] = list(set(local_field + remote_field))
                    confidence_scores.append(0.7)
                else:
                    merged[field] = local_field  # 无法合并，使用本地
                    confidence_scores.append(0.3)
            elif strategy == 'newest':
                # 需要额外的时间戳信息
                merged[field] = local_field
                confidence_scores.append(0.5)
        
        # 处理未指定策略的字段
        all_fields = set(conflict.local_value.keys()) | set(conflict.remote_value.keys())
        for field in all_fields:
            if field not in merged:
                merged[field] = conflict.local_value.get(field, conflict.remote_value.get(field))
                confidence_scores.append(0.5)
        
        avg_confidence = sum(confidence_scores) / len(confidence_scores) if confidence_scores else 0.0
        
        return ConflictResolution(
            resolved_value=merged,
            strategy_used="field_level",
            confidence=avg_confidence,
            manual_review_required=avg_confidence < 0.7
        )


class ChainResolver(ConflictResolver):
    """链式解决器（组合多个解决器）"""
    
    def __init__(self, resolvers: List[ConflictResolver]):
        self.resolvers = resolvers
    
    def resolve(self, conflict: ConflictItem) -> ConflictResolution:
        """依次尝试解决器"""
        for resolver in self.resolvers:
            if resolver.can_resolve(conflict):
                try:
                    resolution = resolver.resolve(conflict)
                    if resolution.confidence > 0.5 and not resolution.manual_review_required:
                        return resolution
                except Exception as e:
                    logger.debug(f"Resolver {resolver.__class__.__name__} failed: {e}")
                    continue
        
        # 所有解决器都失败
        return ConflictResolution(
            resolved_value=conflict.local_value,
            strategy_used="chain_failed",
            confidence=0.0,
            manual_review_required=True,
            notes="No resolver could handle this conflict"
        )


class InteractiveResolver(ConflictResolver):
    """交互式解决器（需要用户输入）"""
    
    def __init__(self, prompt_callback: callable):
        """
        Args:
            prompt_callback: 用于获取用户输入的回调函数
        """
        self.prompt_callback = prompt_callback
    
    def resolve(self, conflict: ConflictItem) -> ConflictResolution:
        """通过用户交互解决冲突"""
        # 准备选项
        options = {
            '1': ('Use local version', conflict.local_value),
            '2': ('Use remote version', conflict.remote_value),
            '3': ('Merge manually', None)
        }
        
        # 调用回调获取用户选择
        choice = self.prompt_callback(conflict, options)
        
        if choice == '1':
            return ConflictResolution(
                resolved_value=conflict.local_value,
                strategy_used="interactive_local",
                confidence=1.0
            )
        elif choice == '2':
            return ConflictResolution(
                resolved_value=conflict.remote_value,
                strategy_used="interactive_remote",
                confidence=1.0
            )
        else:
            # 需要手动合并
            return ConflictResolution(
                resolved_value=conflict.local_value,
                strategy_used="interactive_manual",
                confidence=0.0,
                manual_review_required=True,
                notes="User requested manual merge"
            )