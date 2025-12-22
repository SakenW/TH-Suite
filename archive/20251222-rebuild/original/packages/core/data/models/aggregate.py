"""
聚合根基类

DDD中的聚合根（Aggregate Root）基类
聚合根的特征：
- 是聚合的入口点
- 维护聚合的不变性
- 发布领域事件
- 控制聚合内对象的生命周期
"""

from typing import Any

from .base_entity import BaseEntity


class AggregateRoot(BaseEntity):
    """聚合根基类"""

    def __init__(self, entity_id: str | None = None):
        super().__init__(entity_id)
        self._version = 0  # 乐观锁版本号
        self._is_deleted = False
        self._changes: list[str] = []  # 跟踪变更

    @property
    def version(self) -> int:
        """获取版本号"""
        return self._version

    @property
    def is_deleted(self) -> bool:
        """是否已删除"""
        return self._is_deleted

    def mark_deleted(self) -> None:
        """标记为已删除"""
        if not self._is_deleted:
            self._is_deleted = True
            self.mark_updated()
            self._track_change("deleted")

            # 发布删除事件
            from datetime import datetime

            from ...framework.events.event_bus import Event

            delete_event = Event(
                event_type=f"{self.__class__.__name__.lower()}.deleted",
                timestamp=datetime.now(),
                source=self.__class__.__name__,
                data={"aggregate_id": self.id},
            )
            self.add_domain_event(delete_event)

    def increment_version(self) -> None:
        """递增版本号（用于乐观锁）"""
        self._version += 1

    def get_changes(self) -> list[str]:
        """获取变更记录"""
        return self._changes.copy()

    def clear_changes(self) -> None:
        """清除变更记录"""
        self._changes.clear()

    def _track_change(self, change: str) -> None:
        """跟踪变更"""
        if change not in self._changes:
            self._changes.append(change)

    def mark_updated(self) -> None:
        """标记为已更新"""
        super().mark_updated()
        self.increment_version()

    def validate_invariants(self) -> list[str]:
        """验证聚合不变性"""
        errors = []

        # 基础验证
        if self._is_deleted:
            errors.append("已删除的聚合不能进行操作")

        # 子类应该重写此方法添加特定验证
        return errors

    def apply_event(self, event) -> None:
        """应用领域事件（事件溯源模式）"""
        # 子类可以重写此方法处理特定事件
        self.add_domain_event(event)

    def can_be_deleted(self) -> tuple[bool, list[str]]:
        """检查是否可以删除"""
        errors = []

        if self._is_deleted:
            errors.append("聚合已经被删除")

        # 子类可以重写添加特定的删除前检查
        return len(errors) == 0, errors

    def to_dict(self) -> dict[str, Any]:
        """转换为字典"""
        data = super().to_dict()
        data.update(
            {
                "version": self._version,
                "is_deleted": self._is_deleted,
                "changes": self._changes,
            }
        )
        return data

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "AggregateRoot":
        """从字典创建聚合根"""
        instance = cls(data.get("id"))
        instance._version = data.get("version", 0)
        instance._is_deleted = data.get("is_deleted", False)
        instance._changes = data.get("changes", [])

        # 恢复时间戳
        if "created_at" in data:
            from datetime import datetime

            instance.created_at = datetime.fromisoformat(data["created_at"])
        if "updated_at" in data:
            from datetime import datetime

            instance.updated_at = datetime.fromisoformat(data["updated_at"])

        return instance


class AggregateRepository:
    """聚合仓储基类"""

    def __init__(self):
        self._aggregates: dict[str, AggregateRoot] = {}
        self._deleted_ids: set = set()

    async def get_by_id(self, aggregate_id: str) -> AggregateRoot | None:
        """通过ID获取聚合"""
        if aggregate_id in self._deleted_ids:
            return None

        aggregate = self._aggregates.get(aggregate_id)
        if aggregate and not aggregate.is_deleted:
            return aggregate

        return None

    async def save(self, aggregate: AggregateRoot) -> None:
        """保存聚合"""
        # 验证不变性
        errors = aggregate.validate_invariants()
        if errors:
            raise ValueError(f"聚合验证失败: {', '.join(errors)}")

        if aggregate.is_deleted:
            # 标记为已删除
            self._deleted_ids.add(aggregate.id)
            self._aggregates.pop(aggregate.id, None)
        else:
            # 保存聚合
            self._aggregates[aggregate.id] = aggregate

        # 清除变更记录
        aggregate.clear_changes()

    async def delete(self, aggregate: AggregateRoot) -> None:
        """删除聚合"""
        can_delete, errors = aggregate.can_be_deleted()
        if not can_delete:
            raise ValueError(f"无法删除聚合: {', '.join(errors)}")

        aggregate.mark_deleted()
        await self.save(aggregate)

    async def find_all(self) -> list[AggregateRoot]:
        """获取所有未删除的聚合"""
        return [agg for agg in self._aggregates.values() if not agg.is_deleted]

    def get_changes_since_version(
        self, aggregate_id: str, version: int
    ) -> list[AggregateRoot]:
        """获取指定版本后的变更（用于事件溯源）"""
        # 这里是简化实现，实际项目中可能需要事件存储
        aggregate = self._aggregates.get(aggregate_id)
        if aggregate and aggregate.version > version:
            return [aggregate]
        return []
