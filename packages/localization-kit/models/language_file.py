"""
LanguageFile 数据模型 - 语言文件

根据白皮书定义：
- 属于某个 Container
- 关联到一个 Blob（内容存储）
- 包含多个翻译条目（Entries）
"""

from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Optional, Dict, Any, List, TYPE_CHECKING
import uuid

if TYPE_CHECKING:
    from .container import Container
    from .blob import Blob


@dataclass
class LanguageFile:
    """
    语言文件实体
    
    对应数据库表: language_files
    """
    file_id: str
    locale: str                    # 语言代码，如 "zh_cn", "en_us"
    namespace: str                 # 命名空间，如 "minecraft", "modid"
    file_path: str                 # 文件在容器中的路径
    key_count: int = 0            # 键值对数量
    first_seen: datetime = field(default_factory=datetime.now)
    last_seen: datetime = field(default_factory=datetime.now)
    
    # 关联
    container: Optional['Container'] = None
    container_id: Optional[str] = None
    blob: Optional['Blob'] = None
    content_hash: Optional[str] = None  # 关联到 Blob 的哈希
    
    # 运行时属性
    entries: Dict[str, str] = field(default_factory=dict)  # 键值对缓存
    
    @classmethod
    def create(
        cls,
        locale: str,
        namespace: str,
        file_path: str,
        entries: Optional[Dict[str, str]] = None
    ) -> 'LanguageFile':
        """创建语言文件"""
        lang_file = cls(
            file_id=str(uuid.uuid4()),
            locale=locale,
            namespace=namespace,
            file_path=file_path,
            key_count=len(entries) if entries else 0
        )
        
        if entries:
            lang_file.entries = entries.copy()
            
        return lang_file
    
    def normalize_locale(self) -> str:
        """
        规范化语言代码
        
        Minecraft 使用小写下划线格式（zh_cn），
        但标准 BCP-47 使用连字符（zh-CN）
        """
        # Minecraft 格式到 BCP-47
        if '_' in self.locale:
            parts = self.locale.split('_')
            if len(parts) == 2:
                return f"{parts[0]}-{parts[1].upper()}"
        return self.locale
    
    @staticmethod
    def minecraft_locale(bcp47_locale: str) -> str:
        """
        将 BCP-47 格式转换为 Minecraft 格式
        
        例如: zh-CN -> zh_cn
        """
        return bcp47_locale.lower().replace('-', '_')
    
    def get_standard_path(self) -> str:
        """
        获取标准化的文件路径
        
        格式: assets/{namespace}/lang/{locale}.json
        """
        return f"assets/{self.namespace}/lang/{self.locale}.json"
    
    def add_entry(self, key: str, value: str) -> None:
        """添加或更新翻译条目"""
        self.entries[key] = value
        self.key_count = len(self.entries)
        self.last_seen = datetime.now()
    
    def remove_entry(self, key: str) -> bool:
        """删除翻译条目"""
        if key in self.entries:
            del self.entries[key]
            self.key_count = len(self.entries)
            self.last_seen = datetime.now()
            return True
        return False
    
    def get_entry(self, key: str) -> Optional[str]:
        """获取翻译条目"""
        return self.entries.get(key)
    
    def merge_entries(self, new_entries: Dict[str, str], overwrite: bool = True) -> Dict[str, str]:
        """
        合并新的翻译条目
        
        返回冲突的条目（旧值）
        """
        conflicts = {}
        
        for key, value in new_entries.items():
            if key in self.entries and self.entries[key] != value:
                conflicts[key] = self.entries[key]
                if overwrite:
                    self.entries[key] = value
            elif key not in self.entries:
                self.entries[key] = value
        
        self.key_count = len(self.entries)
        self.last_seen = datetime.now()
        
        return conflicts
    
    def calculate_content_hash(self) -> str:
        """计算内容哈希（用于关联 Blob）"""
        import hashlib
        import json
        
        # 规范化 JSON（排序键）
        canonical_json = json.dumps(self.entries, sort_keys=True, ensure_ascii=False)
        return hashlib.sha256(canonical_json.encode('utf-8')).hexdigest()
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典格式"""
        return {
            'file_id': self.file_id,
            'locale': self.locale,
            'namespace': self.namespace,
            'file_path': self.file_path,
            'key_count': self.key_count,
            'container_id': self.container_id,
            'content_hash': self.content_hash,
            'first_seen': self.first_seen.isoformat(),
            'last_seen': self.last_seen.isoformat()
        }
    
    def export_entries(self) -> Dict[str, str]:
        """导出所有翻译条目"""
        return self.entries.copy()