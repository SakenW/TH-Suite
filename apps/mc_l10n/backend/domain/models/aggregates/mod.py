"""
模组聚合根

模组的聚合根表示
"""

from dataclasses import dataclass
from datetime import datetime
from typing import List, Optional

from domain.models.enums import ModLoaderType
from domain.models.value_objects.mod_id import ModId
from domain.models.value_objects.mod_version import ModVersion
from domain.models.value_objects.file_path import FilePath


@dataclass
class Mod:
    """模组聚合根"""
    
    mod_id: ModId
    name: str
    version: Optional[ModVersion] = None
    description: Optional[str] = None
    authors: List[str] = None
    file_path: Optional[FilePath] = None
    loader_type: Optional[ModLoaderType] = None
    created_at: datetime = None
    
    def __post_init__(self):
        if self.authors is None:
            self.authors = []
        if self.created_at is None:
            self.created_at = datetime.utcnow()