"""
同步客户端
提供数据同步的基础实现
"""

import hashlib
import json
import logging
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any

logger = logging.getLogger(__name__)


class ConflictResolution(Enum):
    """冲突解决策略"""

    LOCAL_WINS = "local_wins"  # 本地优先
    REMOTE_WINS = "remote_wins"  # 远程优先
    MERGE = "merge"  # 合并
    MANUAL = "manual"  # 手动解决
    NEWEST = "newest"  # 最新优先
    OLDEST = "oldest"  # 最旧优先


@dataclass
class SyncItem:
    """同步项"""

    id: str
    local_version: int | None = None
    remote_version: int | None = None
    local_hash: str | None = None
    remote_hash: str | None = None
    local_data: Any | None = None
    remote_data: Any | None = None
    modified_time: datetime | None = None
    conflict: bool = False

    def has_local_changes(self) -> bool:
        """是否有本地更改"""
        return self.local_hash != self.remote_hash and self.local_data is not None

    def has_remote_changes(self) -> bool:
        """是否有远程更改"""
        return self.local_hash != self.remote_hash and self.remote_data is not None

    def is_conflicted(self) -> bool:
        """是否存在冲突"""
        return self.has_local_changes() and self.has_remote_changes()


@dataclass
class SyncState:
    """同步状态"""

    last_sync_time: datetime | None = None
    sync_token: str | None = None
    pending_items: list[str] = field(default_factory=list)
    failed_items: dict[str, str] = field(default_factory=dict)
    conflict_items: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        """转换为字典"""
        return {
            "last_sync_time": self.last_sync_time.isoformat()
            if self.last_sync_time
            else None,
            "sync_token": self.sync_token,
            "pending_items": self.pending_items,
            "failed_items": self.failed_items,
            "conflict_items": self.conflict_items,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "SyncState":
        """从字典创建"""
        if data.get("last_sync_time"):
            data["last_sync_time"] = datetime.fromisoformat(data["last_sync_time"])
        return cls(**data)


class SyncClient(ABC):
    """同步客户端基类"""

    def __init__(
        self, conflict_resolution: ConflictResolution = ConflictResolution.MANUAL
    ):
        self.conflict_resolution = conflict_resolution
        self.sync_state = SyncState()

    @abstractmethod
    def get_local_items(self) -> list[SyncItem]:
        """获取本地项目"""
        pass

    @abstractmethod
    def get_remote_items(
        self, sync_token: str | None = None
    ) -> tuple[list[SyncItem], str | None]:
        """获取远程项目，返回(项目列表, 新的同步令牌)"""
        pass

    @abstractmethod
    def push_item(self, item: SyncItem) -> bool:
        """推送项目到远程"""
        pass

    @abstractmethod
    def pull_item(self, item: SyncItem) -> bool:
        """从远程拉取项目"""
        pass

    @abstractmethod
    def resolve_conflict(self, item: SyncItem) -> SyncItem:
        """解决冲突"""
        pass

    def calculate_hash(self, data: Any) -> str:
        """计算数据哈希"""
        if isinstance(data, dict | list):
            data_str = json.dumps(data, sort_keys=True)
        else:
            data_str = str(data)

        return hashlib.sha256(data_str.encode()).hexdigest()

    def detect_changes(self) -> tuple[list[SyncItem], list[SyncItem], list[SyncItem]]:
        """检测变化

        Returns:
            (需要推送的项目, 需要拉取的项目, 冲突的项目)
        """
        local_items = {item.id: item for item in self.get_local_items()}
        remote_items, new_token = self.get_remote_items(self.sync_state.sync_token)
        remote_items_dict = {item.id: item for item in remote_items}

        to_push = []
        to_pull = []
        conflicts = []

        # 检查本地项目
        for item_id, local_item in local_items.items():
            if item_id in remote_items_dict:
                remote_item = remote_items_dict[item_id]

                # 计算哈希
                local_item.local_hash = self.calculate_hash(local_item.local_data)
                local_item.remote_hash = self.calculate_hash(remote_item.remote_data)

                if local_item.is_conflicted():
                    conflicts.append(local_item)
                elif local_item.has_local_changes():
                    to_push.append(local_item)
                elif local_item.has_remote_changes():
                    local_item.remote_data = remote_item.remote_data
                    to_pull.append(local_item)
            else:
                # 本地新增
                to_push.append(local_item)

        # 检查远程新增
        for item_id, remote_item in remote_items_dict.items():
            if item_id not in local_items:
                to_pull.append(remote_item)

        # 更新同步令牌
        if new_token:
            self.sync_state.sync_token = new_token

        return to_push, to_pull, conflicts

    def sync(self) -> dict[str, Any]:
        """执行同步"""
        logger.info("Starting sync...")

        # 检测变化
        to_push, to_pull, conflicts = self.detect_changes()

        results = {
            "pushed": 0,
            "pulled": 0,
            "conflicts": 0,
            "errors": 0,
            "details": {
                "pushed_items": [],
                "pulled_items": [],
                "conflict_items": [],
                "error_items": [],
            },
        }

        # 处理冲突
        for item in conflicts:
            try:
                resolved = self._handle_conflict(item)
                if resolved:
                    to_push.append(resolved)
                else:
                    results["conflicts"] += 1
                    results["details"]["conflict_items"].append(item.id)
            except Exception as e:
                logger.error(f"Failed to resolve conflict for {item.id}: {e}")
                results["errors"] += 1
                results["details"]["error_items"].append(item.id)

        # 推送本地更改
        for item in to_push:
            try:
                if self.push_item(item):
                    results["pushed"] += 1
                    results["details"]["pushed_items"].append(item.id)
                    self.sync_state.pending_items.remove(
                        item.id
                    ) if item.id in self.sync_state.pending_items else None
                else:
                    self.sync_state.failed_items[item.id] = "Push failed"
                    results["errors"] += 1
            except Exception as e:
                logger.error(f"Failed to push {item.id}: {e}")
                self.sync_state.failed_items[item.id] = str(e)
                results["errors"] += 1

        # 拉取远程更改
        for item in to_pull:
            try:
                if self.pull_item(item):
                    results["pulled"] += 1
                    results["details"]["pulled_items"].append(item.id)
                else:
                    self.sync_state.failed_items[item.id] = "Pull failed"
                    results["errors"] += 1
            except Exception as e:
                logger.error(f"Failed to pull {item.id}: {e}")
                self.sync_state.failed_items[item.id] = str(e)
                results["errors"] += 1

        # 更新同步状态
        self.sync_state.last_sync_time = datetime.now()
        self.sync_state.conflict_items = results["details"]["conflict_items"]

        logger.info(
            f"Sync completed: pushed={results['pushed']}, pulled={results['pulled']}, "
            f"conflicts={results['conflicts']}, errors={results['errors']}"
        )

        return results

    def _handle_conflict(self, item: SyncItem) -> SyncItem | None:
        """处理冲突"""
        if self.conflict_resolution == ConflictResolution.LOCAL_WINS:
            return item  # 使用本地版本

        elif self.conflict_resolution == ConflictResolution.REMOTE_WINS:
            item.local_data = item.remote_data
            return item

        elif self.conflict_resolution == ConflictResolution.NEWEST:
            # 需要比较时间戳
            if hasattr(item, "local_modified") and hasattr(item, "remote_modified"):
                if item.local_modified > item.remote_modified:
                    return item
                else:
                    item.local_data = item.remote_data
                    return item

        elif self.conflict_resolution == ConflictResolution.MERGE:
            # 尝试合并
            try:
                resolved = self.resolve_conflict(item)
                return resolved
            except Exception as e:
                logger.error(f"Failed to merge conflict for {item.id}: {e}")
                return None

        # MANUAL 或其他情况
        return None


class DeltaSync(SyncClient):
    """增量同步客户端"""

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self._local_snapshot: dict[str, str] = {}
        self._remote_snapshot: dict[str, str] = {}

    def take_snapshot(self, items: list[SyncItem], target: str = "local"):
        """创建快照"""
        snapshot = {}
        for item in items:
            if target == "local" and item.local_data:
                snapshot[item.id] = self.calculate_hash(item.local_data)
            elif target == "remote" and item.remote_data:
                snapshot[item.id] = self.calculate_hash(item.remote_data)

        if target == "local":
            self._local_snapshot = snapshot
        else:
            self._remote_snapshot = snapshot

    def get_delta(
        self, current_items: list[SyncItem], snapshot: dict[str, str]
    ) -> dict[str, str]:
        """获取增量

        Returns:
            变化的项目ID到操作的映射
        """
        delta = {}
        current_ids = set()

        for item in current_items:
            current_ids.add(item.id)
            current_hash = self.calculate_hash(
                item.local_data if item.local_data else item.remote_data
            )

            if item.id not in snapshot:
                delta[item.id] = "added"
            elif snapshot[item.id] != current_hash:
                delta[item.id] = "modified"

        # 检查删除的项目
        for item_id in snapshot:
            if item_id not in current_ids:
                delta[item_id] = "deleted"

        return delta
