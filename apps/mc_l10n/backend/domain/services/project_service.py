"""
项目领域服务

项目管理的领域服务
"""

from abc import ABC, abstractmethod
from typing import Optional

from domain.models.aggregates.translation_project import TranslationProject
from domain.models.value_objects.project_name import ProjectName
from domain.models.value_objects.language_code import LanguageCode
from domain.models.value_objects.file_path import FilePath


class ProjectService(ABC):
    """项目领域服务接口"""
    
    @abstractmethod
    async def project_exists_by_name(self, name: str) -> bool:
        """检查项目名是否已存在"""
        pass
    
    @abstractmethod
    async def create_project(
        self,
        name: ProjectName,
        description: str,
        mc_version: str,
        target_language: LanguageCode,
        source_path: FilePath,
        output_path: FilePath,
        user_id: str
    ) -> TranslationProject:
        """创建新项目"""
        pass
    
    @abstractmethod
    async def get_project_by_id(self, project_id: str) -> Optional[TranslationProject]:
        """根据ID获取项目"""
        pass
    
    @abstractmethod
    async def update_project(
        self,
        project_id: str,
        name: Optional[ProjectName] = None,
        description: Optional[str] = None,
        mc_version: Optional[str] = None,
        target_language: Optional[LanguageCode] = None,
        source_path: Optional[FilePath] = None,
        output_path: Optional[FilePath] = None,
        user_id: str = None
    ) -> bool:
        """更新项目"""
        pass
    
    @abstractmethod
    async def delete_project(self, project_id: str, user_id: str) -> bool:
        """删除项目"""
        pass
    
    @abstractmethod
    async def can_delete_project(self, project_id: str) -> bool:
        """检查项目是否可以删除"""
        pass
    
    @abstractmethod
    async def archive_project(
        self,
        project_id: str,
        archive_reason: Optional[str],
        user_id: str
    ) -> bool:
        """归档项目"""
        pass