"""
工作单元模式

管理事务边界，确保数据一致性
工作单元的职责：
- 跟踪对象变更
- 维护事务边界
- 确保原子性操作
- 管理领域事件发布
"""

from abc import ABC, abstractmethod
from contextlib import asynccontextmanager
from typing import Any, TypeVar

from .models.base_entity import BaseEntity
from .repositories.base import IRepository

T = TypeVar("T", bound=BaseEntity)


class IUnitOfWork(ABC):
    """工作单元接口"""

    @abstractmethod
    async def begin(self) -> None:
        """开始事务"""
        pass

    @abstractmethod
    async def commit(self) -> None:
        """提交事务"""
        pass

    @abstractmethod
    async def rollback(self) -> None:
        """回滚事务"""
        pass

    @abstractmethod
    def register_new(self, entity: BaseEntity) -> None:
        """注册新实体"""
        pass

    @abstractmethod
    def register_dirty(self, entity: BaseEntity) -> None:
        """注册已修改实体"""
        pass

    @abstractmethod
    def register_deleted(self, entity: BaseEntity) -> None:
        """注册已删除实体"""
        pass

    @abstractmethod
    async def save_changes(self) -> None:
        """保存所有变更"""
        pass


class UnitOfWork(IUnitOfWork):
    """工作单元实现"""

    def __init__(self):
        self._new_entities: set[BaseEntity] = set()
        self._dirty_entities: set[BaseEntity] = set()
        self._deleted_entities: set[BaseEntity] = set()
        self._repositories: dict[type, IRepository] = {}
        self._transaction_started = False
        self._domain_events: list[Any] = []
        self._committed = False
        self._rolled_back = False

    def register_repository(
        self, entity_type: type[T], repository: IRepository[T]
    ) -> None:
        """注册仓储"""
        self._repositories[entity_type] = repository

    def get_repository(self, entity_type: type[T]) -> IRepository[T]:
        """获取仓储"""
        if entity_type not in self._repositories:
            raise ValueError(f"未注册的实体类型: {entity_type}")
        return self._repositories[entity_type]

    async def begin(self) -> None:
        """开始事务"""
        if self._transaction_started:
            raise RuntimeError("事务已经开始")

        self._transaction_started = True
        self._committed = False
        self._rolled_back = False

        # 清空跟踪集合
        self._new_entities.clear()
        self._dirty_entities.clear()
        self._deleted_entities.clear()
        self._domain_events.clear()

    async def commit(self) -> None:
        """提交事务"""
        if not self._transaction_started:
            raise RuntimeError("事务未开始")
        if self._committed or self._rolled_back:
            raise RuntimeError("事务已经结束")

        try:
            # 保存所有变更
            await self.save_changes()

            # 发布领域事件
            await self._publish_domain_events()

            self._committed = True

        except Exception:
            # 自动回滚
            await self.rollback()
            raise
        finally:
            self._transaction_started = False

    async def rollback(self) -> None:
        """回滚事务"""
        if not self._transaction_started:
            return

        # 清空所有跟踪
        self._new_entities.clear()
        self._dirty_entities.clear()
        self._deleted_entities.clear()
        self._domain_events.clear()

        self._rolled_back = True
        self._transaction_started = False

    def register_new(self, entity: BaseEntity) -> None:
        """注册新实体"""
        if not self._transaction_started:
            raise RuntimeError("事务未开始")

        if entity in self._deleted_entities:
            self._deleted_entities.remove(entity)
        if entity in self._dirty_entities:
            self._dirty_entities.remove(entity)

        self._new_entities.add(entity)

        # 收集领域事件
        self._collect_domain_events(entity)

    def register_dirty(self, entity: BaseEntity) -> None:
        """注册已修改实体"""
        if not self._transaction_started:
            raise RuntimeError("事务未开始")

        if entity not in self._new_entities and entity not in self._deleted_entities:
            self._dirty_entities.add(entity)

        # 收集领域事件
        self._collect_domain_events(entity)

    def register_deleted(self, entity: BaseEntity) -> None:
        """注册已删除实体"""
        if not self._transaction_started:
            raise RuntimeError("事务未开始")

        if entity in self._new_entities:
            self._new_entities.remove(entity)
        if entity in self._dirty_entities:
            self._dirty_entities.remove(entity)

        self._deleted_entities.add(entity)

        # 收集领域事件
        self._collect_domain_events(entity)

    async def save_changes(self) -> None:
        """保存所有变更"""
        if not self._transaction_started:
            raise RuntimeError("事务未开始")

        try:
            # 保存新实体
            for entity in self._new_entities:
                repository = self._get_repository_for_entity(entity)
                await repository.add(entity)

            # 保存修改的实体
            for entity in self._dirty_entities:
                repository = self._get_repository_for_entity(entity)
                await repository.update(entity)

            # 删除实体
            for entity in self._deleted_entities:
                repository = self._get_repository_for_entity(entity)
                await repository.delete(entity.id)

        except Exception as e:
            raise RuntimeError(f"保存变更失败: {e}")

    def _get_repository_for_entity(self, entity: BaseEntity) -> IRepository:
        """获取实体对应的仓储"""
        entity_type = type(entity)

        # 查找直接匹配
        if entity_type in self._repositories:
            return self._repositories[entity_type]

        # 查找父类匹配
        for registered_type, repository in self._repositories.items():
            if issubclass(entity_type, registered_type):
                return repository

        raise ValueError(f"未找到实体类型 {entity_type} 的仓储")

    def _collect_domain_events(self, entity: BaseEntity) -> None:
        """收集领域事件"""
        if hasattr(entity, "get_domain_events"):
            events = entity.get_domain_events()
            self._domain_events.extend(events)

    async def _publish_domain_events(self) -> None:
        """发布领域事件"""
        if not self._domain_events:
            return

        # 获取全局事件总线
        try:
            from ...framework.events.decorators import get_global_event_bus

            event_bus = get_global_event_bus()

            # 发布所有事件
            for event in self._domain_events:
                event_bus.publish(event)

        except ImportError:
            # 如果没有事件总线，跳过事件发布
            pass

        # 清空事件
        self._domain_events.clear()

    def get_tracked_entities(self) -> dict[str, set[BaseEntity]]:
        """获取所有跟踪的实体"""
        return {
            "new": self._new_entities.copy(),
            "dirty": self._dirty_entities.copy(),
            "deleted": self._deleted_entities.copy(),
        }

    def clear_tracking(self) -> None:
        """清空实体跟踪"""
        self._new_entities.clear()
        self._dirty_entities.clear()
        self._deleted_entities.clear()
        self._domain_events.clear()

    @asynccontextmanager
    async def transaction(self):
        """事务上下文管理器"""
        await self.begin()
        try:
            yield self
            await self.commit()
        except Exception:
            await self.rollback()
            raise


class UnitOfWorkManager:
    """工作单元管理器"""

    def __init__(self):
        self._current_uow: UnitOfWork | None = None
        self._uow_stack: list[UnitOfWork] = []

    def create_unit_of_work(self) -> UnitOfWork:
        """创建新的工作单元"""
        return UnitOfWork()

    def set_current(self, uow: UnitOfWork) -> None:
        """设置当前工作单元"""
        if self._current_uow:
            self._uow_stack.append(self._current_uow)
        self._current_uow = uow

    def get_current(self) -> UnitOfWork | None:
        """获取当前工作单元"""
        return self._current_uow

    def pop_current(self) -> UnitOfWork | None:
        """弹出当前工作单元"""
        old_uow = self._current_uow

        if self._uow_stack:
            self._current_uow = self._uow_stack.pop()
        else:
            self._current_uow = None

        return old_uow

    @asynccontextmanager
    async def transaction(self):
        """创建事务上下文"""
        uow = self.create_unit_of_work()
        self.set_current(uow)

        try:
            async with uow.transaction():
                yield uow
        finally:
            self.pop_current()


# 全局工作单元管理器
_global_uow_manager = UnitOfWorkManager()


def get_unit_of_work_manager() -> UnitOfWorkManager:
    """获取全局工作单元管理器"""
    return _global_uow_manager


def get_current_unit_of_work() -> UnitOfWork | None:
    """获取当前工作单元"""
    return _global_uow_manager.get_current()
