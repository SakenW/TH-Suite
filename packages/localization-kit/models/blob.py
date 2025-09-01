"""
Blob 数据模型 - 内容存储

根据白皮书定义：
- Blob 存储语言文件的规范化内容
- 使用内容哈希作为主键，实现去重
- 存储 canonical_json 格式
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Dict, Any, List, Optional, Set
import hashlib
import json


@dataclass
class Blob:
    """
    Blob 实体 - 内容存储单元
    
    对应数据库表: blobs
    
    特点：
    1. 内容寻址：使用 SHA256 哈希作为主键
    2. 去重存储：相同内容只存储一次
    3. 规范化格式：按键排序的 JSON
    """
    blob_hash: str                 # SHA256 哈希（主键）
    canonical_json: str            # 规范化的 JSON 内容
    size: int                      # 内容大小（字节）
    entry_count: int               # 条目数量
    first_seen: datetime = field(default_factory=datetime.now)
    last_seen: datetime = field(default_factory=datetime.now)
    
    # 运行时属性
    entries: Dict[str, str] = field(default_factory=dict)
    references: List[str] = field(default_factory=list)  # 引用此 Blob 的文件 ID
    
    @classmethod
    def from_entries(cls, entries: Dict[str, str]) -> 'Blob':
        """从条目字典创建 Blob"""
        # 规范化 JSON（按键排序，确保一致性）
        canonical_json = json.dumps(entries, sort_keys=True, ensure_ascii=False, indent=2)
        
        # 计算哈希
        blob_hash = hashlib.sha256(canonical_json.encode('utf-8')).hexdigest()
        
        return cls(
            blob_hash=blob_hash,
            canonical_json=canonical_json,
            size=len(canonical_json.encode('utf-8')),
            entry_count=len(entries),
            entries=entries.copy()
        )
    
    @classmethod
    def from_json(cls, json_content: str) -> 'Blob':
        """从 JSON 字符串创建 Blob"""
        # 解析 JSON
        try:
            entries = json.loads(json_content)
            if not isinstance(entries, dict):
                raise ValueError("JSON content must be a dictionary")
        except json.JSONDecodeError as e:
            raise ValueError(f"Invalid JSON content: {e}")
        
        # 验证所有值都是字符串
        for key, value in entries.items():
            if not isinstance(key, str):
                raise ValueError(f"Key must be string, got {type(key)}: {key}")
            if not isinstance(value, str):
                raise ValueError(f"Value must be string for key '{key}', got {type(value)}")
        
        return cls.from_entries(entries)
    
    def load_entries(self) -> Dict[str, str]:
        """从规范化 JSON 加载条目"""
        if not self.entries and self.canonical_json:
            self.entries = json.loads(self.canonical_json)
        return self.entries
    
    def get_entry(self, key: str) -> Optional[str]:
        """获取特定条目"""
        self.load_entries()
        return self.entries.get(key)
    
    def get_keys(self) -> Set[str]:
        """获取所有键"""
        self.load_entries()
        return set(self.entries.keys())
    
    def diff_with(self, other: 'Blob') -> Dict[str, Dict[str, Optional[str]]]:
        """
        与另一个 Blob 比较差异
        
        返回格式：
        {
            "key": {
                "old": "旧值" or None,
                "new": "新值" or None
            }
        }
        """
        self.load_entries()
        other.load_entries()
        
        diff = {}
        all_keys = self.get_keys() | other.get_keys()
        
        for key in all_keys:
            old_value = self.entries.get(key)
            new_value = other.entries.get(key)
            
            if old_value != new_value:
                diff[key] = {
                    "old": old_value,
                    "new": new_value
                }
        
        return diff
    
    def merge_with(self, other: 'Blob', strategy: str = 'overwrite') -> 'Blob':
        """
        与另一个 Blob 合并
        
        策略：
        - overwrite: 新值覆盖旧值
        - keep: 保留旧值
        - union: 合并所有键值对
        """
        self.load_entries()
        other.load_entries()
        
        if strategy == 'overwrite':
            merged_entries = {**self.entries, **other.entries}
        elif strategy == 'keep':
            merged_entries = {**other.entries, **self.entries}
        elif strategy == 'union':
            merged_entries = {**self.entries}
            for key, value in other.entries.items():
                if key not in merged_entries:
                    merged_entries[key] = value
        else:
            raise ValueError(f"Unknown merge strategy: {strategy}")
        
        return Blob.from_entries(merged_entries)
    
    def add_reference(self, file_id: str) -> None:
        """添加引用此 Blob 的文件 ID"""
        if file_id not in self.references:
            self.references.append(file_id)
            self.last_seen = datetime.now()
    
    def remove_reference(self, file_id: str) -> bool:
        """移除引用"""
        if file_id in self.references:
            self.references.remove(file_id)
            self.last_seen = datetime.now()
            return True
        return False
    
    def is_orphaned(self) -> bool:
        """检查是否为孤立 Blob（无引用）"""
        return len(self.references) == 0
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典格式"""
        return {
            'blob_hash': self.blob_hash,
            'size': self.size,
            'entry_count': self.entry_count,
            'reference_count': len(self.references),
            'first_seen': self.first_seen.isoformat(),
            'last_seen': self.last_seen.isoformat()
        }
    
    def export_json(self, pretty: bool = False) -> str:
        """导出为 JSON 字符串"""
        if pretty:
            return json.dumps(self.entries, ensure_ascii=False, indent=2)
        return self.canonical_json