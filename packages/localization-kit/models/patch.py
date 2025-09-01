"""
补丁数据模型 - PatchSet 和 PatchItem

根据白皮书定义：
- PatchSet: 补丁集，包含多个补丁项
- PatchItem: 单个补丁项，定义如何更新特定容器的特定语言文件
"""

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Optional, Dict, Any, List
import uuid
import hashlib
import json


class PatchPolicy(Enum):
    """补丁策略枚举"""
    OVERLAY = "overlay"              # 覆盖层（资源包）
    REPLACE = "replace"              # 替换原文件
    MERGE = "merge"                  # 合并内容
    CREATE_IF_MISSING = "create_if_missing"  # 仅在文件不存在时创建


class PatchStatus(Enum):
    """补丁状态枚举"""
    DRAFT = "draft"                  # 草稿
    PUBLISHED = "published"          # 已发布
    APPLIED = "applied"              # 已应用
    ARCHIVED = "archived"            # 已归档


@dataclass
class PatchItem:
    """
    补丁项 - 单个翻译更新单元
    
    对应数据库表: patch_items
    """
    patch_item_id: str
    patch_set_id: str
    target_container_id: str         # 目标容器 ID
    namespace: str                   # 命名空间
    locale: str                      # 目标语言
    policy: PatchPolicy              # 应用策略
    expected_blob_hash: Optional[str] = None  # 期望的内容哈希
    expected_entry_count: Optional[int] = None  # 期望的条目数
    serializer_profile_id: Optional[str] = None  # 序列化配置
    target_member_path: Optional[str] = None  # JAR 内的目标路径
    upstream_anchor_blob: Optional[str] = None  # 上游锚定 Blob（用于三方合并）
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    # 运行时属性
    content: Dict[str, str] = field(default_factory=dict)  # 实际的翻译内容
    
    def set_content(self, entries: Dict[str, str]) -> None:
        """设置补丁内容"""
        self.content = entries.copy()
        # 计算期望的哈希
        canonical_json = json.dumps(entries, sort_keys=True, ensure_ascii=False)
        self.expected_blob_hash = hashlib.sha256(canonical_json.encode('utf-8')).hexdigest()
        self.expected_entry_count = len(entries)
    
    def validate_preconditions(self, current_hash: Optional[str]) -> bool:
        """
        验证前置条件
        
        Args:
            current_hash: 当前文件的内容哈希
            
        Returns:
            是否满足应用条件
        """
        if self.policy == PatchPolicy.CREATE_IF_MISSING:
            # 只在文件不存在时创建
            return current_hash is None
        
        if self.upstream_anchor_blob:
            # 如果指定了上游锚定，当前哈希必须匹配
            return current_hash == self.upstream_anchor_blob
        
        # 其他策略总是可以应用
        return True
    
    def get_target_path(self) -> str:
        """获取目标文件路径"""
        if self.target_member_path:
            return self.target_member_path
        # 标准路径格式
        return f"assets/{self.namespace}/lang/{self.locale}.json"
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典格式"""
        return {
            'patch_item_id': self.patch_item_id,
            'patch_set_id': self.patch_set_id,
            'target_container_id': self.target_container_id,
            'namespace': self.namespace,
            'locale': self.locale,
            'policy': self.policy.value,
            'expected_blob_hash': self.expected_blob_hash,
            'expected_entry_count': self.expected_entry_count,
            'serializer_profile_id': self.serializer_profile_id,
            'target_member_path': self.target_member_path,
            'upstream_anchor_blob': self.upstream_anchor_blob,
            'metadata': self.metadata,
            'has_content': len(self.content) > 0
        }


@dataclass
class PatchSet:
    """
    补丁集 - 一组相关的补丁项
    
    对应数据库表: patch_sets
    """
    patch_set_id: str
    name: str
    description: Optional[str] = None
    created_at: datetime = field(default_factory=datetime.now)
    signature: Optional[str] = None  # 数字签名
    version: Optional[str] = None
    status: PatchStatus = PatchStatus.DRAFT
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    # 运行时属性
    patch_items: List[PatchItem] = field(default_factory=list)
    
    @classmethod
    def create(
        cls,
        name: str,
        description: Optional[str] = None,
        version: Optional[str] = None
    ) -> 'PatchSet':
        """创建补丁集"""
        return cls(
            patch_set_id=str(uuid.uuid4()),
            name=name,
            description=description,
            version=version or "1.0.0"
        )
    
    def add_patch_item(self, patch_item: PatchItem) -> None:
        """添加补丁项"""
        patch_item.patch_set_id = self.patch_set_id
        if patch_item not in self.patch_items:
            self.patch_items.append(patch_item)
    
    def remove_patch_item(self, patch_item_id: str) -> bool:
        """移除补丁项"""
        for item in self.patch_items:
            if item.patch_item_id == patch_item_id:
                self.patch_items.remove(item)
                return True
        return False
    
    def get_patch_item(self, patch_item_id: str) -> Optional[PatchItem]:
        """获取特定补丁项"""
        for item in self.patch_items:
            if item.patch_item_id == patch_item_id:
                return item
        return None
    
    def get_items_by_container(self, container_id: str) -> List[PatchItem]:
        """获取特定容器的所有补丁项"""
        return [
            item for item in self.patch_items
            if item.target_container_id == container_id
        ]
    
    def get_items_by_locale(self, locale: str) -> List[PatchItem]:
        """获取特定语言的所有补丁项"""
        return [
            item for item in self.patch_items
            if item.locale == locale
        ]
    
    def get_affected_containers(self) -> List[str]:
        """获取受影响的容器 ID 列表"""
        container_ids = set()
        for item in self.patch_items:
            container_ids.add(item.target_container_id)
        return list(container_ids)
    
    def get_affected_locales(self) -> List[str]:
        """获取受影响的语言列表"""
        locales = set()
        for item in self.patch_items:
            locales.add(item.locale)
        return sorted(list(locales))
    
    def calculate_signature(self) -> str:
        """
        计算补丁集的签名
        
        基于所有补丁项的内容哈希
        """
        # 收集所有补丁项的哈希
        hashes = []
        for item in sorted(self.patch_items, key=lambda x: x.patch_item_id):
            if item.expected_blob_hash:
                hashes.append(item.expected_blob_hash)
        
        # 计算总体签名
        combined = '|'.join(hashes)
        signature = hashlib.sha256(combined.encode('utf-8')).hexdigest()
        self.signature = signature
        return signature
    
    def validate(self) -> List[str]:
        """
        验证补丁集的完整性
        
        Returns:
            错误消息列表
        """
        errors = []
        
        if not self.patch_items:
            errors.append("补丁集不包含任何补丁项")
        
        # 检查重复的目标
        targets = set()
        for item in self.patch_items:
            target_key = f"{item.target_container_id}:{item.namespace}:{item.locale}"
            if target_key in targets:
                errors.append(f"重复的补丁目标: {target_key}")
            targets.add(target_key)
        
        # 验证每个补丁项
        for item in self.patch_items:
            if not item.content and not item.expected_blob_hash:
                errors.append(f"补丁项 {item.patch_item_id} 缺少内容")
            
            if item.policy == PatchPolicy.MERGE and not item.upstream_anchor_blob:
                errors.append(f"合并策略的补丁项 {item.patch_item_id} 缺少上游锚定")
        
        return errors
    
    def publish(self) -> bool:
        """
        发布补丁集
        
        Returns:
            是否成功发布
        """
        # 验证
        errors = self.validate()
        if errors:
            return False
        
        # 计算签名
        self.calculate_signature()
        
        # 更新状态
        self.status = PatchStatus.PUBLISHED
        
        return True
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典格式"""
        return {
            'patch_set_id': self.patch_set_id,
            'name': self.name,
            'description': self.description,
            'created_at': self.created_at.isoformat(),
            'signature': self.signature,
            'version': self.version,
            'status': self.status.value,
            'metadata': self.metadata,
            'patch_item_count': len(self.patch_items),
            'affected_containers': self.get_affected_containers(),
            'affected_locales': self.get_affected_locales()
        }
    
    def export_manifest(self) -> Dict[str, Any]:
        """
        导出补丁清单（用于传输）
        
        Returns:
            补丁清单字典
        """
        manifest = {
            'version': '1.0',
            'patch_set': self.to_dict(),
            'patch_items': [item.to_dict() for item in self.patch_items],
            'created_at': datetime.now().isoformat()
        }
        
        # 添加内容数据
        for i, item in enumerate(self.patch_items):
            if item.content:
                manifest['patch_items'][i]['content'] = item.content
        
        return manifest
    
    @classmethod
    def from_manifest(cls, manifest: Dict[str, Any]) -> 'PatchSet':
        """
        从清单创建补丁集
        
        Args:
            manifest: 补丁清单字典
            
        Returns:
            PatchSet 对象
        """
        # 创建补丁集
        patch_set_data = manifest['patch_set']
        patch_set = cls(
            patch_set_id=patch_set_data['patch_set_id'],
            name=patch_set_data['name'],
            description=patch_set_data.get('description'),
            version=patch_set_data.get('version'),
            signature=patch_set_data.get('signature'),
            metadata=patch_set_data.get('metadata', {})
        )
        
        # 设置状态
        patch_set.status = PatchStatus(patch_set_data.get('status', 'draft'))
        
        # 添加补丁项
        for item_data in manifest.get('patch_items', []):
            patch_item = PatchItem(
                patch_item_id=item_data['patch_item_id'],
                patch_set_id=patch_set.patch_set_id,
                target_container_id=item_data['target_container_id'],
                namespace=item_data['namespace'],
                locale=item_data['locale'],
                policy=PatchPolicy(item_data['policy']),
                expected_blob_hash=item_data.get('expected_blob_hash'),
                expected_entry_count=item_data.get('expected_entry_count'),
                serializer_profile_id=item_data.get('serializer_profile_id'),
                target_member_path=item_data.get('target_member_path'),
                upstream_anchor_blob=item_data.get('upstream_anchor_blob'),
                metadata=item_data.get('metadata', {})
            )
            
            # 设置内容
            if 'content' in item_data:
                patch_item.content = item_data['content']
            
            patch_set.add_patch_item(patch_item)
        
        return patch_set