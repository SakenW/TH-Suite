"""
补丁服务 - 生成、管理和应用补丁

提供补丁集的创建、验证、发布等功能
管理补丁项的生成和应用
"""

import logging
import uuid

from sqlalchemy.orm import Session

from ..database.schema import (
    ContainerTable,
    LanguageFileTable,
    PatchItemTable,
    PatchSetTable,
)
from ..models import (
    PatchItem,
    PatchPolicy,
    PatchSet,
    PatchStatus,
)
from .blob_service import BlobService

logger = logging.getLogger(__name__)


class PatchService:
    """
    补丁服务

    核心功能：
    1. 补丁生成：基于翻译差异生成补丁
    2. 补丁管理：创建、更新、发布补丁集
    3. 补丁验证：验证补丁的完整性和适用性
    4. 补丁应用：将补丁应用到目标容器
    """

    def __init__(self, session: Session):
        """
        初始化补丁服务

        Args:
            session: 数据库会话
        """
        self.session = session
        self.blob_service = BlobService(session)

    def create_patch_set(
        self, name: str, description: str | None = None, version: str | None = None
    ) -> PatchSet:
        """
        创建补丁集

        Args:
            name: 补丁集名称
            description: 描述
            version: 版本号

        Returns:
            PatchSet 对象
        """
        patch_set = PatchSet.create(name, description, version)

        # 保存到数据库
        patch_set_table = PatchSetTable(
            patch_set_id=patch_set.patch_set_id,
            name=patch_set.name,
            description=patch_set.description,
            created_at=patch_set.created_at,
            version=patch_set.version,
            status=patch_set.status.value,
            metadata=patch_set.metadata,
        )

        self.session.add(patch_set_table)
        self.session.commit()

        logger.info(f"创建补丁集: {patch_set.name} ({patch_set.patch_set_id})")
        return patch_set

    def generate_patch_item(
        self,
        container_id: str,
        locale: str,
        new_entries: dict[str, str],
        policy: PatchPolicy = PatchPolicy.OVERLAY,
        namespace: str | None = None,
    ) -> PatchItem:
        """
        生成补丁项

        Args:
            container_id: 目标容器 ID
            locale: 目标语言
            new_entries: 新的翻译条目
            policy: 应用策略
            namespace: 命名空间（如果为 None，使用容器的默认命名空间）

        Returns:
            PatchItem 对象
        """
        # 获取容器信息
        container = (
            self.session.query(ContainerTable)
            .filter_by(container_id=container_id)
            .first()
        )

        if not container:
            raise ValueError(f"容器不存在: {container_id}")

        if not namespace:
            namespace = container.namespace or container.mod_id

        # 创建补丁项
        patch_item = PatchItem(
            patch_item_id=str(uuid.uuid4()),
            patch_set_id="",  # 将在添加到补丁集时设置
            target_container_id=container_id,
            namespace=namespace,
            locale=locale,
            policy=policy,
        )

        # 设置内容
        patch_item.set_content(new_entries)

        # 获取当前语言文件（如果存在）
        current_file = (
            self.session.query(LanguageFileTable)
            .filter_by(container_id=container_id, locale=locale, namespace=namespace)
            .first()
        )

        if current_file and current_file.content_hash:
            # 记录上游锚定（用于冲突检测）
            patch_item.upstream_anchor_blob = current_file.content_hash

        logger.debug(
            f"生成补丁项: {container_id}:{namespace}:{locale} "
            f"({len(new_entries)} 条目, 策略: {policy.value})"
        )

        return patch_item

    def generate_diff_patch(
        self,
        container_id: str,
        locale: str,
        source_entries: dict[str, str],
        target_entries: dict[str, str],
        policy: PatchPolicy = PatchPolicy.OVERLAY,
    ) -> PatchItem | None:
        """
        基于差异生成补丁项

        Args:
            container_id: 目标容器 ID
            locale: 目标语言
            source_entries: 源条目（当前）
            target_entries: 目标条目（新的）
            policy: 应用策略

        Returns:
            PatchItem 对象，如果没有差异则返回 None
        """
        # 计算差异
        diff_entries = {}

        for key, value in target_entries.items():
            if key not in source_entries or source_entries[key] != value:
                diff_entries[key] = value

        # 如果策略是替换，包含所有条目
        if policy == PatchPolicy.REPLACE:
            diff_entries = target_entries.copy()

        if not diff_entries:
            logger.debug(f"无差异，不生成补丁: {container_id}:{locale}")
            return None

        # 生成补丁项
        patch_item = self.generate_patch_item(
            container_id=container_id,
            locale=locale,
            new_entries=diff_entries,
            policy=policy,
        )

        return patch_item

    def add_patch_item_to_set(self, patch_set_id: str, patch_item: PatchItem) -> None:
        """
        将补丁项添加到补丁集

        Args:
            patch_set_id: 补丁集 ID
            patch_item: 补丁项
        """
        # 验证补丁集存在
        patch_set_table = (
            self.session.query(PatchSetTable)
            .filter_by(patch_set_id=patch_set_id)
            .first()
        )

        if not patch_set_table:
            raise ValueError(f"补丁集不存在: {patch_set_id}")

        # 设置补丁集 ID
        patch_item.patch_set_id = patch_set_id

        # 保存补丁项
        patch_item_table = PatchItemTable(
            patch_item_id=patch_item.patch_item_id,
            patch_set_id=patch_set_id,
            target_container_id=patch_item.target_container_id,
            namespace=patch_item.namespace,
            locale=patch_item.locale,
            policy=patch_item.policy.value,
            expected_blob_hash=patch_item.expected_blob_hash,
            expected_entry_count=patch_item.expected_entry_count,
            serializer_profile_id=patch_item.serializer_profile_id,
            target_member_path=patch_item.target_member_path,
            upstream_anchor_blob=patch_item.upstream_anchor_blob,
            metadata=patch_item.metadata,
        )

        self.session.add(patch_item_table)

        # 如果有内容，存储为 Blob
        if patch_item.content:
            blob, _ = self.blob_service.store_blob(patch_item.content)
            patch_item_table.expected_blob_hash = blob.blob_hash

        self.session.commit()

        logger.info(
            f"补丁项已添加到补丁集: {patch_item.patch_item_id} -> {patch_set_id}"
        )

    def get_patch_set(self, patch_set_id: str) -> PatchSet | None:
        """
        获取补丁集

        Args:
            patch_set_id: 补丁集 ID

        Returns:
            PatchSet 对象或 None
        """
        patch_set_table = (
            self.session.query(PatchSetTable)
            .filter_by(patch_set_id=patch_set_id)
            .first()
        )

        if not patch_set_table:
            return None

        # 转换为模型对象
        patch_set = PatchSet(
            patch_set_id=patch_set_table.patch_set_id,
            name=patch_set_table.name,
            description=patch_set_table.description,
            created_at=patch_set_table.created_at,
            signature=patch_set_table.signature,
            version=patch_set_table.version,
            status=PatchStatus(patch_set_table.status),
            metadata=patch_set_table.metadata or {},
        )

        # 加载补丁项
        patch_items = (
            self.session.query(PatchItemTable)
            .filter_by(patch_set_id=patch_set_id)
            .all()
        )

        for item_table in patch_items:
            patch_item = self._table_to_patch_item(item_table)
            patch_set.add_patch_item(patch_item)

        return patch_set

    def _table_to_patch_item(self, table: PatchItemTable) -> PatchItem:
        """将数据库表转换为补丁项模型"""
        patch_item = PatchItem(
            patch_item_id=table.patch_item_id,
            patch_set_id=table.patch_set_id,
            target_container_id=table.target_container_id,
            namespace=table.namespace,
            locale=table.locale,
            policy=PatchPolicy(table.policy),
            expected_blob_hash=table.expected_blob_hash,
            expected_entry_count=table.expected_entry_count,
            serializer_profile_id=table.serializer_profile_id,
            target_member_path=table.target_member_path,
            upstream_anchor_blob=table.upstream_anchor_blob,
            metadata=table.metadata or {},
        )

        # 加载内容（如果有）
        if table.expected_blob_hash:
            blob = self.blob_service.get_blob(table.expected_blob_hash)
            if blob:
                blob.load_entries()
                patch_item.content = blob.entries

        return patch_item

    def publish_patch_set(self, patch_set_id: str) -> bool:
        """
        发布补丁集

        Args:
            patch_set_id: 补丁集 ID

        Returns:
            是否成功发布
        """
        patch_set = self.get_patch_set(patch_set_id)
        if not patch_set:
            logger.error(f"补丁集不存在: {patch_set_id}")
            return False

        # 验证并发布
        if patch_set.publish():
            # 更新数据库
            patch_set_table = (
                self.session.query(PatchSetTable)
                .filter_by(patch_set_id=patch_set_id)
                .first()
            )

            patch_set_table.status = PatchStatus.PUBLISHED.value
            patch_set_table.signature = patch_set.signature

            self.session.commit()

            logger.info(f"补丁集已发布: {patch_set.name} ({patch_set_id})")
            return True
        else:
            errors = patch_set.validate()
            logger.error(f"补丁集验证失败: {', '.join(errors)}")
            return False

    def validate_patch_applicability(
        self, patch_item: PatchItem, container_id: str
    ) -> tuple[bool, str | None]:
        """
        验证补丁项的适用性

        Args:
            patch_item: 补丁项
            container_id: 目标容器 ID

        Returns:
            (是否适用, 错误消息)
        """
        # 检查容器是否匹配
        if patch_item.target_container_id != container_id:
            return False, "容器 ID 不匹配"

        # 获取当前语言文件
        current_file = (
            self.session.query(LanguageFileTable)
            .filter_by(
                container_id=container_id,
                locale=patch_item.locale,
                namespace=patch_item.namespace,
            )
            .first()
        )

        # 验证前置条件
        current_hash = current_file.content_hash if current_file else None
        if not patch_item.validate_preconditions(current_hash):
            return False, "前置条件不满足"

        return True, None

    def export_patch_set(self, patch_set_id: str) -> dict | None:
        """
        导出补丁集为 JSON 清单

        Args:
            patch_set_id: 补丁集 ID

        Returns:
            补丁清单字典或 None
        """
        patch_set = self.get_patch_set(patch_set_id)
        if not patch_set:
            return None

        manifest = patch_set.export_manifest()

        logger.info(f"导出补丁集: {patch_set.name} ({len(patch_set.patch_items)} 项)")
        return manifest

    def import_patch_set(self, manifest: dict) -> PatchSet:
        """
        从 JSON 清单导入补丁集

        Args:
            manifest: 补丁清单字典

        Returns:
            PatchSet 对象
        """
        patch_set = PatchSet.from_manifest(manifest)

        # 保存到数据库
        patch_set_table = PatchSetTable(
            patch_set_id=patch_set.patch_set_id,
            name=patch_set.name,
            description=patch_set.description,
            created_at=patch_set.created_at,
            signature=patch_set.signature,
            version=patch_set.version,
            status=patch_set.status.value,
            metadata=patch_set.metadata,
        )

        self.session.add(patch_set_table)

        # 保存补丁项
        for patch_item in patch_set.patch_items:
            self.add_patch_item_to_set(patch_set.patch_set_id, patch_item)

        self.session.commit()

        logger.info(f"导入补丁集: {patch_set.name} ({len(patch_set.patch_items)} 项)")
        return patch_set

    def list_patch_sets(
        self, status: PatchStatus | None = None, limit: int = 50
    ) -> list[PatchSet]:
        """
        列出补丁集

        Args:
            status: 筛选状态
            limit: 最大数量

        Returns:
            补丁集列表
        """
        query = self.session.query(PatchSetTable)

        if status:
            query = query.filter_by(status=status.value)

        query = query.order_by(PatchSetTable.created_at.desc()).limit(limit)

        patch_sets = []
        for table in query.all():
            # 简化版本，不加载所有补丁项
            patch_set = PatchSet(
                patch_set_id=table.patch_set_id,
                name=table.name,
                description=table.description,
                created_at=table.created_at,
                signature=table.signature,
                version=table.version,
                status=PatchStatus(table.status),
                metadata=table.metadata or {},
            )
            patch_sets.append(patch_set)

        return patch_sets
