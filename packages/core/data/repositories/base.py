"""
仓储模式基类

提供统一的数据访问接口
"""

from abc import ABC, abstractmethod
from typing import Any, TypeVar

T = TypeVar("T")


class IRepository[T](ABC):
    """仓储接口"""

    @abstractmethod
    async def get_by_id(self, entity_id: str) -> T | None:
        """通过ID获取实体"""
        pass

    @abstractmethod
    async def get_all(self) -> list[T]:
        """获取所有实体"""
        pass

    @abstractmethod
    async def add(self, entity: T) -> T:
        """添加实体"""
        pass

    @abstractmethod
    async def update(self, entity: T) -> T:
        """更新实体"""
        pass

    @abstractmethod
    async def delete(self, entity_id: str) -> bool:
        """删除实体"""
        pass

    @abstractmethod
    async def find(self, criteria: dict[str, Any]) -> list[T]:
        """按条件查找"""
        pass


class BaseRepository(IRepository[T]):
    """仓储基类"""

    def __init__(self):
        self._entities: dict[str, T] = {}

    async def get_by_id(self, entity_id: str) -> T | None:
        """通过ID获取实体"""
        return self._entities.get(entity_id)

    async def get_all(self) -> list[T]:
        """获取所有实体"""
        return list(self._entities.values())

    async def add(self, entity: T) -> T:
        """添加实体"""
        entity_id = getattr(entity, "id", None)
        if entity_id:
            self._entities[entity_id] = entity
        return entity

    async def update(self, entity: T) -> T:
        """更新实体"""
        entity_id = getattr(entity, "id", None)
        if entity_id and entity_id in self._entities:
            self._entities[entity_id] = entity
        return entity

    async def delete(self, entity_id: str) -> bool:
        """删除实体"""
        if entity_id in self._entities:
            del self._entities[entity_id]
            return True
        return False

    async def find(self, criteria: dict[str, Any]) -> list[T]:
        """按条件查找（简单实现）"""
        results = []
        for entity in self._entities.values():
            matches = True
            for key, value in criteria.items():
                if not hasattr(entity, key) or getattr(entity, key) != value:
                    matches = False
                    break
            if matches:
                results.append(entity)
        return results
