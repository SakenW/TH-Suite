"""
数据库架构定义

使用 SQLAlchemy ORM 定义白皮书中的所有表结构
支持 SQLCipher 加密
"""

from datetime import datetime

from sqlalchemy import (
    JSON,
    Boolean,
    Column,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship

Base = declarative_base()


class ArtifactTable(Base):
    """Artifact 表 - 物理载体"""

    __tablename__ = "artifacts"

    artifact_id = Column(String, primary_key=True)
    artifact_type = Column(
        String, nullable=False
    )  # mod_jar | modpack_dir | resource_pack | data_pack
    path = Column(Text, nullable=False)
    content_hash = Column(String(64), nullable=False)
    size = Column(Integer, nullable=False)
    first_seen = Column(DateTime, default=datetime.now)
    last_seen = Column(DateTime, default=datetime.now, onupdate=datetime.now)
    metadata = Column(JSON)

    # 关系
    containers = relationship(
        "ContainerTable", back_populates="artifact", cascade="all, delete-orphan"
    )

    # 索引
    __table_args__ = (
        Index("idx_artifact_type", "artifact_type"),
        Index("idx_artifact_hash", "content_hash"),
        Index("idx_artifact_path", "path"),
    )


class ContainerTable(Base):
    """Container 表 - 逻辑翻译单元"""

    __tablename__ = "containers"

    container_id = Column(String, primary_key=True)
    artifact_id = Column(String, ForeignKey("artifacts.artifact_id"), nullable=False)
    container_type = Column(String, nullable=False)  # mod | pack_module | overlay
    mod_id = Column(String, nullable=False)
    display_name = Column(Text)
    version = Column(String)
    loader_type = Column(String)  # forge | fabric | quilt | neoforge
    namespace = Column(String)
    metadata = Column(JSON)

    # 关系
    artifact = relationship("ArtifactTable", back_populates="containers")
    language_files = relationship(
        "LanguageFileTable", back_populates="container", cascade="all, delete-orphan"
    )

    # 索引
    __table_args__ = (
        Index("idx_container_mod_id", "mod_id"),
        Index("idx_container_type", "container_type"),
        Index("idx_container_namespace", "namespace"),
        UniqueConstraint(
            "artifact_id", "mod_id", "version", name="uq_container_identity"
        ),
    )


class LanguageFileTable(Base):
    """语言文件表"""

    __tablename__ = "language_files"

    file_id = Column(String, primary_key=True)
    container_id = Column(String, ForeignKey("containers.container_id"), nullable=False)
    locale = Column(String, nullable=False)
    namespace = Column(String, nullable=False)
    file_path = Column(Text, nullable=False)
    content_hash = Column(String(64), ForeignKey("blobs.blob_hash"))
    key_count = Column(Integer, default=0)
    first_seen = Column(DateTime, default=datetime.now)
    last_seen = Column(DateTime, default=datetime.now, onupdate=datetime.now)

    # 关系
    container = relationship("ContainerTable", back_populates="language_files")
    blob = relationship("BlobTable", back_populates="language_files")

    # 索引
    __table_args__ = (
        Index("idx_language_locale", "locale"),
        Index("idx_language_namespace", "namespace"),
        UniqueConstraint(
            "container_id", "locale", "namespace", "file_path", name="uq_language_file"
        ),
    )


class BlobTable(Base):
    """Blob 表 - 内容存储"""

    __tablename__ = "blobs"

    blob_hash = Column(String(64), primary_key=True)
    canonical_json = Column(Text, nullable=False)
    size = Column(Integer, nullable=False)
    entry_count = Column(Integer, nullable=False)
    first_seen = Column(DateTime, default=datetime.now)
    last_seen = Column(DateTime, default=datetime.now, onupdate=datetime.now)

    # 关系
    language_files = relationship("LanguageFileTable", back_populates="blob")

    # 索引
    __table_args__ = (
        Index("idx_blob_size", "size"),
        Index("idx_blob_entry_count", "entry_count"),
    )


class EntryCurrentTable(Base):
    """当前翻译条目表"""

    __tablename__ = "entries_current"

    entry_key = Column(String, primary_key=True)  # blob_hash#translation_key
    blob_hash = Column(String(64), ForeignKey("blobs.blob_hash"), nullable=False)
    translation_key = Column(Text, nullable=False)
    value = Column(Text, nullable=False)
    first_seen = Column(DateTime, default=datetime.now)
    last_seen = Column(DateTime, default=datetime.now, onupdate=datetime.now)

    # 索引
    __table_args__ = (
        Index("idx_entry_blob", "blob_hash"),
        Index("idx_entry_key", "translation_key"),
    )


class EntryVersionTable(Base):
    """翻译条目历史版本表"""

    __tablename__ = "entries_versions"

    version_id = Column(String, primary_key=True)
    entry_key = Column(String, nullable=False)
    blob_hash = Column(String(64), ForeignKey("blobs.blob_hash"), nullable=False)
    translation_key = Column(Text, nullable=False)
    value = Column(Text, nullable=False)
    from_scan_id = Column(String)
    until_scan_id = Column(String)
    created_at = Column(DateTime, default=datetime.now)

    # 索引
    __table_args__ = (
        Index("idx_version_entry", "entry_key"),
        Index("idx_version_scan", "from_scan_id", "until_scan_id"),
    )


class SerializationProfileTable(Base):
    """序列化配置表"""

    __tablename__ = "serialization_profiles"

    profile_id = Column(String, primary_key=True)
    format = Column(String, nullable=False)  # json | lang | properties
    charset = Column(String, default="utf-8")
    newline = Column(String, default="\\n")  # \\n | \\r\\n
    bom = Column(Boolean, default=False)
    escape_style = Column(String)  # unicode | backslash
    sort_policy = Column(String)  # alphabetical | none | custom
    indent = Column(Integer)
    metadata = Column(JSON)

    # 索引
    __table_args__ = (Index("idx_serialization_format", "format"),)


class PatchSetTable(Base):
    """补丁集表"""

    __tablename__ = "patch_sets"

    patch_set_id = Column(String, primary_key=True)
    name = Column(String, nullable=False)
    description = Column(Text)
    created_at = Column(DateTime, default=datetime.now)
    signature = Column(Text)  # 数字签名
    version = Column(String)
    status = Column(String)  # draft | published | applied | archived
    metadata = Column(JSON)

    # 关系
    patch_items = relationship(
        "PatchItemTable", back_populates="patch_set", cascade="all, delete-orphan"
    )

    # 索引
    __table_args__ = (
        Index("idx_patch_set_status", "status"),
        Index("idx_patch_set_created", "created_at"),
    )


class PatchItemTable(Base):
    """补丁项表"""

    __tablename__ = "patch_items"

    patch_item_id = Column(String, primary_key=True)
    patch_set_id = Column(String, ForeignKey("patch_sets.patch_set_id"), nullable=False)
    target_container_id = Column(String, ForeignKey("containers.container_id"))
    namespace = Column(String, nullable=False)
    locale = Column(String, nullable=False)
    policy = Column(
        String, nullable=False
    )  # overlay | replace | merge | create_if_missing
    expected_blob_hash = Column(String(64))
    expected_entry_count = Column(Integer)
    serializer_profile_id = Column(
        String, ForeignKey("serialization_profiles.profile_id")
    )
    target_member_path = Column(Text)
    upstream_anchor_blob = Column(String(64))
    metadata = Column(JSON)

    # 关系
    patch_set = relationship("PatchSetTable", back_populates="patch_items")

    # 索引
    __table_args__ = (
        Index("idx_patch_item_target", "target_container_id"),
        Index("idx_patch_item_locale", "locale"),
        UniqueConstraint(
            "patch_set_id",
            "target_container_id",
            "namespace",
            "locale",
            name="uq_patch_item",
        ),
    )


class WritebackPlanTable(Base):
    """回写计划表"""

    __tablename__ = "writeback_plans"

    plan_id = Column(String, primary_key=True)
    patch_set_id = Column(String, ForeignKey("patch_sets.patch_set_id"), nullable=False)
    created_at = Column(DateTime, default=datetime.now)
    status = Column(String)  # pending | executing | completed | failed
    metadata = Column(JSON)

    # 索引
    __table_args__ = (Index("idx_writeback_status", "status"),)


class ApplyRunTable(Base):
    """应用执行表"""

    __tablename__ = "apply_runs"

    run_id = Column(String, primary_key=True)
    plan_id = Column(String, ForeignKey("writeback_plans.plan_id"), nullable=False)
    started_at = Column(DateTime, default=datetime.now)
    completed_at = Column(DateTime)
    status = Column(String)  # running | success | failed | rolled_back
    trace_id = Column(String)  # 链路追踪 ID
    metadata = Column(JSON)

    # 关系
    results = relationship(
        "ApplyResultTable", back_populates="apply_run", cascade="all, delete-orphan"
    )

    # 索引
    __table_args__ = (
        Index("idx_apply_run_status", "status"),
        Index("idx_apply_run_trace", "trace_id"),
    )


class ApplyResultTable(Base):
    """应用结果表"""

    __tablename__ = "apply_results"

    result_id = Column(String, primary_key=True)
    run_id = Column(String, ForeignKey("apply_runs.run_id"), nullable=False)
    patch_item_id = Column(
        String, ForeignKey("patch_items.patch_item_id"), nullable=False
    )
    status = Column(String)  # success | failed | conflict | skipped
    before_hash = Column(String(64))
    after_hash = Column(String(64))
    expected_hash = Column(String(64))
    conflict_details = Column(JSON)
    rollback_status = Column(String)  # not_needed | success | failed
    metadata = Column(JSON)

    # 关系
    apply_run = relationship("ApplyRunTable", back_populates="results")

    # 索引
    __table_args__ = (Index("idx_apply_result_status", "status"),)


class QualityCheckTable(Base):
    """质量检查表"""

    __tablename__ = "quality_checks"

    check_id = Column(String, primary_key=True)
    entry_key = Column(String, nullable=False)
    check_type = Column(
        String, nullable=False
    )  # placeholder | format | color_code | length
    status = Column(String)  # passed | warning | failed
    details = Column(JSON)
    checked_at = Column(DateTime, default=datetime.now)

    # 索引
    __table_args__ = (
        Index("idx_quality_check_entry", "entry_key"),
        Index("idx_quality_check_type", "check_type"),
        Index("idx_quality_check_status", "status"),
    )


class LocaleAliasTable(Base):
    """语言别名映射表"""

    __tablename__ = "locale_aliases"

    minecraft_locale = Column(String, primary_key=True)  # zh_cn
    bcp47_locale = Column(String, nullable=False)  # zh-CN
    display_name = Column(String)  # 简体中文

    # 索引
    __table_args__ = (Index("idx_locale_bcp47", "bcp47_locale"),)
