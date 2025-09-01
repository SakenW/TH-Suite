"""
翻译项目聚合根

翻译项目的聚合根表示
"""

from dataclasses import dataclass
from datetime import datetime
from typing import List, Optional

from domain.models.value_objects.file_path import FilePath
from domain.models.value_objects.language_code import LanguageCode


@dataclass
class ProjectId:
    """项目ID值对象"""
    value: str
    
    def __post_init__(self):
        if not self.value or not self.value.strip():
            raise ValueError("项目ID不能为空")


@dataclass 
class TranslationProject:
    """翻译项目聚合根"""
    
    project_id: ProjectId
    name: str
    description: Optional[str] = None
    source_path: Optional[FilePath] = None
    target_language: Optional[LanguageCode] = None
    created_at: datetime = None
    updated_at: Optional[datetime] = None
    
    def __post_init__(self):
        if self.created_at is None:
            self.created_at = datetime.utcnow()