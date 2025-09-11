"""
Repository接口定义
定义领域层的仓储接口（端口）
"""

from abc import ABC, abstractmethod
from datetime import datetime
from typing import Any

from .models.mod import Mod, ModId
from .models.translation_project import TranslationProject


class ModRepository(ABC):
    """Mod仓储接口"""

    @abstractmethod
    def find_by_id(self, mod_id: ModId) -> Mod | None:
        """根据ID查找Mod"""
        pass

    @abstractmethod
    def find_by_file_path(self, file_path: str) -> Mod | None:
        """根据文件路径查找Mod"""
        pass

    @abstractmethod
    def find_by_content_hash(self, content_hash: str) -> Mod | None:
        """根据内容哈希查找Mod"""
        pass

    @abstractmethod
    def find_all(self, limit: int = 100, offset: int = 0) -> list[Mod]:
        """查找所有Mod"""
        pass

    @abstractmethod
    def find_by_status(self, status: str) -> list[Mod]:
        """根据状态查找Mod"""
        pass

    @abstractmethod
    def find_needs_rescan(self) -> list[Mod]:
        """查找需要重新扫描的Mod"""
        pass

    @abstractmethod
    def save(self, mod: Mod) -> Mod:
        """保存Mod"""
        pass

    @abstractmethod
    def update(self, mod: Mod) -> Mod:
        """更新Mod"""
        pass

    @abstractmethod
    def delete(self, mod_id: ModId) -> bool:
        """删除Mod"""
        pass

    @abstractmethod
    def exists(self, mod_id: ModId) -> bool:
        """检查Mod是否存在"""
        pass

    @abstractmethod
    def count(self) -> int:
        """统计Mod数量"""
        pass

    @abstractmethod
    def count_by_status(self, status: str) -> int:
        """统计指定状态的Mod数量"""
        pass

    @abstractmethod
    def search(self, query: str) -> list[Mod]:
        """搜索Mod"""
        pass


class TranslationProjectRepository(ABC):
    """翻译项目仓储接口"""

    @abstractmethod
    def find_by_id(self, project_id: str) -> TranslationProject | None:
        """根据ID查找项目"""
        pass

    @abstractmethod
    def find_all(self, limit: int = 100, offset: int = 0) -> list[TranslationProject]:
        """查找所有项目"""
        pass

    @abstractmethod
    def find_by_status(self, status: str) -> list[TranslationProject]:
        """根据状态查找项目"""
        pass

    @abstractmethod
    def find_by_contributor(self, user_id: str) -> list[TranslationProject]:
        """查找用户参与的项目"""
        pass

    @abstractmethod
    def find_containing_mod(self, mod_id: ModId) -> list[TranslationProject]:
        """查找包含指定Mod的项目"""
        pass

    @abstractmethod
    def save(self, project: TranslationProject) -> TranslationProject:
        """保存项目"""
        pass

    @abstractmethod
    def update(self, project: TranslationProject) -> TranslationProject:
        """更新项目"""
        pass

    @abstractmethod
    def delete(self, project_id: str) -> bool:
        """删除项目"""
        pass

    @abstractmethod
    def exists(self, project_id: str) -> bool:
        """检查项目是否存在"""
        pass


class TranslationRepository(ABC):
    """翻译仓储接口"""

    @abstractmethod
    def find_by_mod_and_language(self, mod_id: ModId, language: str) -> dict[str, str]:
        """查找指定Mod和语言的翻译"""
        pass

    @abstractmethod
    def find_by_key(self, key: str, language: str) -> list[dict[str, Any]]:
        """根据键查找翻译"""
        pass

    @abstractmethod
    def save_translations(
        self, mod_id: ModId, language: str, translations: dict[str, str]
    ) -> bool:
        """保存翻译"""
        pass

    @abstractmethod
    def update_translation(
        self, mod_id: ModId, language: str, key: str, value: str
    ) -> bool:
        """更新单个翻译"""
        pass

    @abstractmethod
    def delete_translations(self, mod_id: ModId, language: str) -> bool:
        """删除翻译"""
        pass

    @abstractmethod
    def get_translation_stats(self, mod_id: ModId) -> dict[str, int]:
        """获取翻译统计"""
        pass

    @abstractmethod
    def get_untranslated_keys(self, mod_id: ModId, language: str) -> list[str]:
        """获取未翻译的键"""
        pass

    @abstractmethod
    def search_translations(
        self, query: str, language: str | None = None
    ) -> list[dict[str, Any]]:
        """搜索翻译"""
        pass


class EventRepository(ABC):
    """事件仓储接口"""

    @abstractmethod
    def save_event(self, event: Any) -> bool:
        """保存事件"""
        pass

    @abstractmethod
    def find_by_aggregate_id(self, aggregate_id: str) -> list[Any]:
        """根据聚合ID查找事件"""
        pass

    @abstractmethod
    def find_by_type(self, event_type: str, limit: int = 100) -> list[Any]:
        """根据类型查找事件"""
        pass

    @abstractmethod
    def find_between(self, start: datetime, end: datetime) -> list[Any]:
        """查找时间范围内的事件"""
        pass

    @abstractmethod
    def get_event_stream(self, aggregate_id: str, from_version: int = 0) -> list[Any]:
        """获取事件流"""
        pass


class ScanResultRepository(ABC):
    """扫描结果仓储接口"""

    @abstractmethod
    def save_scan_result(self, mod_id: ModId, result: dict[str, Any]) -> bool:
        """保存扫描结果"""
        pass

    @abstractmethod
    def find_latest_scan(self, mod_id: ModId) -> dict[str, Any] | None:
        """查找最新的扫描结果"""
        pass

    @abstractmethod
    def find_scan_history(self, mod_id: ModId, limit: int = 10) -> list[dict[str, Any]]:
        """查找扫描历史"""
        pass

    @abstractmethod
    def delete_old_scans(self, before: datetime) -> int:
        """删除旧的扫描结果"""
        pass


class CacheRepository(ABC):
    """缓存仓储接口"""

    @abstractmethod
    def get(self, key: str) -> Any | None:
        """获取缓存值"""
        pass

    @abstractmethod
    def set(self, key: str, value: Any, ttl: int | None = None) -> bool:
        """设置缓存值"""
        pass

    @abstractmethod
    def delete(self, key: str) -> bool:
        """删除缓存值"""
        pass

    @abstractmethod
    def exists(self, key: str) -> bool:
        """检查键是否存在"""
        pass

    @abstractmethod
    def clear(self) -> bool:
        """清空缓存"""
        pass
