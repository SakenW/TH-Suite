"""
Unit of Work模式实现
管理事务边界和聚合根的持久化
"""

import logging
import sqlite3
from abc import ABC, abstractmethod
from contextlib import contextmanager
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any

from ..domain.models.mod import Mod, ModId
from ..domain.models.translation_project import TranslationProject
from ..domain.repositories import ModRepository, TranslationProjectRepository

logger = logging.getLogger(__name__)


class EntityState:
    """实体状态枚举"""

    CLEAN = "clean"  # 干净的（未修改）
    NEW = "new"  # 新增的
    MODIFIED = "modified"  # 已修改的
    DELETED = "deleted"  # 已删除的


@dataclass
class TrackedEntity:
    """被跟踪的实体"""

    entity: Any
    state: str
    original_data: dict | None = None
    modified_fields: set[str] = field(default_factory=set)

    def mark_modified(self, field_name: str):
        """标记字段为已修改"""
        if self.state == EntityState.CLEAN:
            self.state = EntityState.MODIFIED
        self.modified_fields.add(field_name)

    def mark_deleted(self):
        """标记为已删除"""
        self.state = EntityState.DELETED

    def is_dirty(self) -> bool:
        """检查是否有未保存的更改"""
        return self.state != EntityState.CLEAN


class IUnitOfWork(ABC):
    """工作单元接口"""

    @abstractmethod
    def register_new(self, entity: Any):
        """注册新实体"""
        pass

    @abstractmethod
    def register_modified(self, entity: Any):
        """注册已修改的实体"""
        pass

    @abstractmethod
    def register_deleted(self, entity: Any):
        """注册已删除的实体"""
        pass

    @abstractmethod
    def commit(self):
        """提交所有更改"""
        pass

    @abstractmethod
    def rollback(self):
        """回滚所有更改"""
        pass


class UnitOfWork(IUnitOfWork):
    """工作单元实现"""

    def __init__(
        self,
        mod_repository: ModRepository,
        project_repository: TranslationProjectRepository,
        connection: sqlite3.Connection | None = None,
    ):
        self.mod_repository = mod_repository
        self.project_repository = project_repository
        self.connection = connection

        # 实体跟踪
        self._identity_map: dict[str, TrackedEntity] = {}
        self._new_entities: list[TrackedEntity] = []
        self._modified_entities: list[TrackedEntity] = []
        self._deleted_entities: list[TrackedEntity] = []

        # 事件收集
        self._collected_events: list[Any] = []

        # 事务状态
        self._in_transaction = False
        self._transaction_id = None

    def register_new(self, entity: Any):
        """注册新实体"""
        entity_id = self._get_entity_id(entity)

        if entity_id in self._identity_map:
            raise ValueError(f"Entity {entity_id} already exists in identity map")

        tracked = TrackedEntity(entity=entity, state=EntityState.NEW)

        self._new_entities.append(tracked)
        self._identity_map[entity_id] = tracked

        # 收集领域事件
        self._collect_domain_events(entity)

        logger.debug(f"Registered new entity: {entity_id}")

    def register_modified(self, entity: Any):
        """注册已修改的实体"""
        entity_id = self._get_entity_id(entity)

        if entity_id in self._identity_map:
            tracked = self._identity_map[entity_id]
            if tracked.state == EntityState.NEW:
                # 新实体不需要标记为已修改
                return
            elif tracked.state != EntityState.DELETED:
                tracked.state = EntityState.MODIFIED
                if tracked not in self._modified_entities:
                    self._modified_entities.append(tracked)
        else:
            # 首次跟踪这个实体
            tracked = TrackedEntity(
                entity=entity,
                state=EntityState.MODIFIED,
                original_data=self._snapshot_entity(entity),
            )
            self._modified_entities.append(tracked)
            self._identity_map[entity_id] = tracked

        # 收集领域事件
        self._collect_domain_events(entity)

        logger.debug(f"Registered modified entity: {entity_id}")

    def register_deleted(self, entity: Any):
        """注册已删除的实体"""
        entity_id = self._get_entity_id(entity)

        if entity_id in self._identity_map:
            tracked = self._identity_map[entity_id]

            if tracked.state == EntityState.NEW:
                # 新实体直接从列表中移除
                self._new_entities.remove(tracked)
                del self._identity_map[entity_id]
            else:
                tracked.mark_deleted()
                if tracked not in self._deleted_entities:
                    self._deleted_entities.append(tracked)
        else:
            # 首次跟踪这个实体（作为删除）
            tracked = TrackedEntity(entity=entity, state=EntityState.DELETED)
            self._deleted_entities.append(tracked)
            self._identity_map[entity_id] = tracked

        logger.debug(f"Registered deleted entity: {entity_id}")

    def commit(self):
        """提交所有更改"""
        if not self._has_changes():
            logger.debug("No changes to commit")
            return

        try:
            self._begin_transaction()

            # 按顺序处理：先删除，再更新，最后新增
            self._process_deletions()
            self._process_modifications()
            self._process_additions()

            # 发布收集的领域事件
            self._publish_events()

            self._commit_transaction()

            # 清理状态
            self._clear()

            logger.info("Unit of work committed successfully")

        except Exception as e:
            logger.error(f"Error during commit: {e}")
            self._rollback_transaction()
            raise

    def rollback(self):
        """回滚所有更改"""
        try:
            if self._in_transaction:
                self._rollback_transaction()

            # 恢复实体状态
            for tracked in self._modified_entities:
                if tracked.original_data:
                    self._restore_entity(tracked.entity, tracked.original_data)

            # 清理状态
            self._clear()

            logger.info("Unit of work rolled back")

        except Exception as e:
            logger.error(f"Error during rollback: {e}")
            raise

    def get_by_id(self, entity_type: type, entity_id: str) -> Any | None:
        """通过ID获取实体（先检查身份映射）"""
        # 先从身份映射中查找
        map_key = f"{entity_type.__name__}:{entity_id}"
        if map_key in self._identity_map:
            tracked = self._identity_map[map_key]
            if tracked.state != EntityState.DELETED:
                return tracked.entity

        # 从仓储加载
        if entity_type == Mod:
            entity = self.mod_repository.get_by_id(ModId(entity_id))
        elif entity_type == TranslationProject:
            entity = self.project_repository.get_by_id(entity_id)
        else:
            return None

        if entity:
            # 加入身份映射
            tracked = TrackedEntity(entity=entity, state=EntityState.CLEAN)
            self._identity_map[map_key] = tracked

        return entity

    @contextmanager
    def transaction(self):
        """事务上下文管理器"""
        try:
            self._begin_transaction()
            yield self
            self.commit()
        except Exception:
            self.rollback()
            raise

    def _has_changes(self) -> bool:
        """检查是否有未提交的更改"""
        return bool(
            self._new_entities or self._modified_entities or self._deleted_entities
        )

    def _begin_transaction(self):
        """开始事务"""
        if self.connection and not self._in_transaction:
            self.connection.execute("BEGIN")
            self._in_transaction = True
            self._transaction_id = datetime.now().isoformat()
            logger.debug(f"Transaction started: {self._transaction_id}")

    def _commit_transaction(self):
        """提交事务"""
        if self.connection and self._in_transaction:
            self.connection.commit()
            self._in_transaction = False
            logger.debug(f"Transaction committed: {self._transaction_id}")

    def _rollback_transaction(self):
        """回滚事务"""
        if self.connection and self._in_transaction:
            self.connection.rollback()
            self._in_transaction = False
            logger.debug(f"Transaction rolled back: {self._transaction_id}")

    def _process_additions(self):
        """处理新增实体"""
        for tracked in self._new_entities:
            entity = tracked.entity

            if isinstance(entity, Mod):
                self.mod_repository.save(entity)
            elif isinstance(entity, TranslationProject):
                self.project_repository.save(entity)

            logger.debug(f"Added entity: {self._get_entity_id(entity)}")

    def _process_modifications(self):
        """处理修改的实体"""
        for tracked in self._modified_entities:
            entity = tracked.entity

            if isinstance(entity, Mod):
                self.mod_repository.update(entity)
            elif isinstance(entity, TranslationProject):
                self.project_repository.update(entity)

            logger.debug(f"Updated entity: {self._get_entity_id(entity)}")

    def _process_deletions(self):
        """处理删除的实体"""
        for tracked in self._deleted_entities:
            entity = tracked.entity

            if isinstance(entity, Mod):
                self.mod_repository.delete(entity.mod_id)
            elif isinstance(entity, TranslationProject):
                self.project_repository.delete(entity.project_id)

            logger.debug(f"Deleted entity: {self._get_entity_id(entity)}")

    def _collect_domain_events(self, entity: Any):
        """收集实体的领域事件"""
        if hasattr(entity, "domain_events"):
            self._collected_events.extend(entity.domain_events)
            entity.clear_events()

    def _publish_events(self):
        """发布收集的领域事件"""
        # 这里应该集成事件总线
        for event in self._collected_events:
            logger.info(f"Publishing event: {type(event).__name__}")
            # EventBus.publish(event)

        self._collected_events.clear()

    def _get_entity_id(self, entity: Any) -> str:
        """获取实体的唯一标识"""
        entity_type = type(entity).__name__

        if isinstance(entity, Mod):
            return f"{entity_type}:{entity.mod_id}"
        elif isinstance(entity, TranslationProject):
            return f"{entity_type}:{entity.project_id}"
        else:
            raise ValueError(f"Unknown entity type: {entity_type}")

    def _snapshot_entity(self, entity: Any) -> dict:
        """创建实体快照"""
        if hasattr(entity, "to_dict"):
            return entity.to_dict()
        else:
            # 简单的属性复制
            return {
                key: value
                for key, value in entity.__dict__.items()
                if not key.startswith("_")
            }

    def _restore_entity(self, entity: Any, snapshot: dict):
        """从快照恢复实体"""
        for key, value in snapshot.items():
            if hasattr(entity, key):
                setattr(entity, key, value)

    def _clear(self):
        """清理内部状态"""
        self._identity_map.clear()
        self._new_entities.clear()
        self._modified_entities.clear()
        self._deleted_entities.clear()
        self._collected_events.clear()
        self._transaction_id = None


class UnitOfWorkFactory:
    """工作单元工厂"""

    def __init__(
        self,
        mod_repository: ModRepository,
        project_repository: TranslationProjectRepository,
        connection_factory=None,
    ):
        self.mod_repository = mod_repository
        self.project_repository = project_repository
        self.connection_factory = connection_factory

    def create(self) -> UnitOfWork:
        """创建新的工作单元实例"""
        connection = self.connection_factory() if self.connection_factory else None

        return UnitOfWork(
            mod_repository=self.mod_repository,
            project_repository=self.project_repository,
            connection=connection,
        )
