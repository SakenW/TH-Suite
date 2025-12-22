"""
Blob 服务 - 内容存储和去重

提供基于内容哈希的去重存储服务
管理 Blob 的创建、查询、合并等操作
"""

import logging
from datetime import datetime
from typing import Any

from sqlalchemy import func
from sqlalchemy.orm import Session

from ..database.schema import BlobTable, EntryCurrentTable, LanguageFileTable
from ..models import Blob, LanguageFile

logger = logging.getLogger(__name__)


class BlobService:
    """
    Blob 存储服务

    核心功能：
    1. 内容去重：相同内容只存储一次
    2. 引用计数：跟踪 Blob 的使用情况
    3. 差异计算：比较不同版本的内容
    4. 垃圾回收：清理无引用的 Blob
    """

    def __init__(self, session: Session):
        """
        初始化 Blob 服务

        Args:
            session: 数据库会话
        """
        self.session = session

    def store_blob(self, entries: dict[str, str]) -> tuple[Blob, bool]:
        """
        存储 Blob（自动去重）

        Args:
            entries: 翻译条目字典

        Returns:
            (Blob 对象, 是否为新创建)
        """
        # 创建 Blob 对象
        blob = Blob.from_entries(entries)

        # 检查是否已存在
        existing = (
            self.session.query(BlobTable).filter_by(blob_hash=blob.blob_hash).first()
        )

        if existing:
            # 更新最后访问时间
            existing.last_seen = datetime.now()
            self.session.commit()

            # 转换为模型对象
            blob_model = self._table_to_model(existing)
            logger.debug(f"Blob 已存在: {blob.blob_hash[:8]}...")
            return blob_model, False

        # 创建新 Blob
        blob_table = BlobTable(
            blob_hash=blob.blob_hash,
            canonical_json=blob.canonical_json,
            size=blob.size,
            entry_count=blob.entry_count,
            first_seen=blob.first_seen,
            last_seen=blob.last_seen,
        )

        self.session.add(blob_table)

        # 存储条目
        self._store_entries(blob)

        self.session.commit()

        logger.info(
            f"新 Blob 已存储: {blob.blob_hash[:8]}... ({blob.entry_count} 条目)"
        )
        return blob, True

    def _store_entries(self, blob: Blob) -> None:
        """存储 Blob 的条目"""
        blob.load_entries()

        for key, value in blob.entries.items():
            entry_key = f"{blob.blob_hash}#{key}"

            # 检查是否已存在
            existing = (
                self.session.query(EntryCurrentTable)
                .filter_by(entry_key=entry_key)
                .first()
            )

            if not existing:
                entry = EntryCurrentTable(
                    entry_key=entry_key,
                    blob_hash=blob.blob_hash,
                    translation_key=key,
                    value=value,
                )
                self.session.add(entry)
            else:
                # 更新值和时间
                existing.value = value
                existing.last_seen = datetime.now()

    def get_blob(self, blob_hash: str) -> Blob | None:
        """
        获取 Blob

        Args:
            blob_hash: Blob 哈希

        Returns:
            Blob 对象或 None
        """
        blob_table = (
            self.session.query(BlobTable).filter_by(blob_hash=blob_hash).first()
        )

        if blob_table:
            return self._table_to_model(blob_table)
        return None

    def find_similar_blobs(
        self, blob: Blob, threshold: float = 0.8
    ) -> list[tuple[Blob, float]]:
        """
        查找相似的 Blob

        Args:
            blob: 参考 Blob
            threshold: 相似度阈值（0-1）

        Returns:
            [(Blob, 相似度)] 列表
        """
        similar_blobs = []
        blob.load_entries()
        reference_keys = blob.get_keys()

        # 查询所有 Blob
        all_blobs = (
            self.session.query(BlobTable)
            .filter(BlobTable.blob_hash != blob.blob_hash)
            .all()
        )

        for blob_table in all_blobs:
            other_blob = self._table_to_model(blob_table)
            other_blob.load_entries()
            other_keys = other_blob.get_keys()

            # 计算 Jaccard 相似度
            intersection = len(reference_keys & other_keys)
            union = len(reference_keys | other_keys)

            if union > 0:
                similarity = intersection / union
                if similarity >= threshold:
                    similar_blobs.append((other_blob, similarity))

        # 按相似度排序
        similar_blobs.sort(key=lambda x: x[1], reverse=True)

        return similar_blobs

    def merge_blobs(self, blob_hashes: list[str], strategy: str = "union") -> Blob:
        """
        合并多个 Blob

        Args:
            blob_hashes: 要合并的 Blob 哈希列表
            strategy: 合并策略（union, intersection, first_win）

        Returns:
            合并后的新 Blob
        """
        if not blob_hashes:
            raise ValueError("至少需要一个 Blob 哈希")

        blobs = []
        for hash_val in blob_hashes:
            blob = self.get_blob(hash_val)
            if blob:
                blob.load_entries()
                blobs.append(blob)

        if not blobs:
            raise ValueError("未找到任何有效的 Blob")

        # 执行合并
        if strategy == "union":
            # 合并所有键值对
            merged_entries = {}
            for blob in blobs:
                merged_entries.update(blob.entries)

        elif strategy == "intersection":
            # 只保留所有 Blob 都有的键
            if len(blobs) == 1:
                merged_entries = blobs[0].entries.copy()
            else:
                common_keys = set(blobs[0].entries.keys())
                for blob in blobs[1:]:
                    common_keys &= set(blob.entries.keys())

                merged_entries = {}
                for key in common_keys:
                    # 使用第一个 Blob 的值
                    merged_entries[key] = blobs[0].entries[key]

        elif strategy == "first_win":
            # 第一个 Blob 的值优先
            merged_entries = {}
            for blob in reversed(blobs):
                merged_entries.update(blob.entries)
        else:
            raise ValueError(f"未知的合并策略: {strategy}")

        # 创建新 Blob
        merged_blob, _ = self.store_blob(merged_entries)

        logger.info(
            f"合并 {len(blobs)} 个 Blob，策略: {strategy}，"
            f"结果: {merged_blob.entry_count} 条目"
        )

        return merged_blob

    def diff_blobs(
        self, blob_hash1: str, blob_hash2: str
    ) -> dict[str, dict[str, str | None]]:
        """
        比较两个 Blob 的差异

        Args:
            blob_hash1: 第一个 Blob 哈希
            blob_hash2: 第二个 Blob 哈希

        Returns:
            差异字典
        """
        blob1 = self.get_blob(blob_hash1)
        blob2 = self.get_blob(blob_hash2)

        if not blob1 or not blob2:
            raise ValueError("Blob 不存在")

        return blob1.diff_with(blob2)

    def get_blob_references(self, blob_hash: str) -> list[LanguageFile]:
        """
        获取引用此 Blob 的所有语言文件

        Args:
            blob_hash: Blob 哈希

        Returns:
            语言文件列表
        """
        lang_files = []

        # 查询引用此 Blob 的语言文件
        file_tables = (
            self.session.query(LanguageFileTable)
            .filter_by(content_hash=blob_hash)
            .all()
        )

        for file_table in file_tables:
            lang_file = LanguageFile(
                file_id=file_table.file_id,
                locale=file_table.locale,
                namespace=file_table.namespace,
                file_path=file_table.file_path,
                key_count=file_table.key_count,
                container_id=file_table.container_id,
                content_hash=file_table.content_hash,
            )
            lang_files.append(lang_file)

        return lang_files

    def update_references(self, blob_hash: str, file_ids: list[str]) -> None:
        """
        更新 Blob 的引用

        Args:
            blob_hash: Blob 哈希
            file_ids: 引用此 Blob 的文件 ID 列表
        """
        # 更新语言文件的 content_hash
        for file_id in file_ids:
            lang_file = (
                self.session.query(LanguageFileTable).filter_by(file_id=file_id).first()
            )

            if lang_file:
                lang_file.content_hash = blob_hash
                lang_file.last_seen = datetime.now()

        self.session.commit()

    def garbage_collect(self, dry_run: bool = True) -> list[str]:
        """
        垃圾回收：删除无引用的 Blob

        Args:
            dry_run: 如果为 True，只返回要删除的 Blob，不实际删除

        Returns:
            被删除（或将被删除）的 Blob 哈希列表
        """
        # 查找无引用的 Blob
        orphaned_blobs = (
            self.session.query(BlobTable)
            .filter(
                ~BlobTable.blob_hash.in_(
                    self.session.query(LanguageFileTable.content_hash).filter(
                        LanguageFileTable.content_hash.isnot(None)
                    )
                )
            )
            .all()
        )

        orphaned_hashes = [blob.blob_hash for blob in orphaned_blobs]

        if not dry_run and orphaned_hashes:
            # 删除孤立的 Blob
            for blob in orphaned_blobs:
                # 删除相关条目
                self.session.query(EntryCurrentTable).filter_by(
                    blob_hash=blob.blob_hash
                ).delete()

                # 删除 Blob
                self.session.delete(blob)

            self.session.commit()
            logger.info(f"垃圾回收: 删除 {len(orphaned_hashes)} 个无引用 Blob")
        else:
            logger.info(f"垃圾回收（预演）: 发现 {len(orphaned_hashes)} 个无引用 Blob")

        return orphaned_hashes

    def get_statistics(self) -> dict[str, Any]:
        """
        获取 Blob 统计信息

        Returns:
            统计信息字典
        """
        stats = {
            "total_blobs": self.session.query(func.count(BlobTable.blob_hash)).scalar(),
            "total_entries": self.session.query(
                func.count(EntryCurrentTable.entry_key)
            ).scalar(),
            "total_size": self.session.query(func.sum(BlobTable.size)).scalar() or 0,
            "avg_entry_count": self.session.query(
                func.avg(BlobTable.entry_count)
            ).scalar()
            or 0,
            "max_entry_count": self.session.query(
                func.max(BlobTable.entry_count)
            ).scalar()
            or 0,
            "orphaned_count": len(self.garbage_collect(dry_run=True)),
        }

        # 去重率计算
        total_references = (
            self.session.query(func.count(LanguageFileTable.file_id))
            .filter(LanguageFileTable.content_hash.isnot(None))
            .scalar()
        )

        if total_references > 0:
            stats["dedup_ratio"] = 1 - (stats["total_blobs"] / total_references)
        else:
            stats["dedup_ratio"] = 0

        return stats

    def _table_to_model(self, table: BlobTable) -> Blob:
        """将数据库表转换为模型对象"""
        blob = Blob(
            blob_hash=table.blob_hash,
            canonical_json=table.canonical_json,
            size=table.size,
            entry_count=table.entry_count,
            first_seen=table.first_seen,
            last_seen=table.last_seen,
        )
        return blob
