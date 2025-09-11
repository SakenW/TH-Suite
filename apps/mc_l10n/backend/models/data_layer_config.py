"""
TH-Suite v2.1 数据分层配置
基于 docs/optimization/02-database-optimization.md 的数据分层设计

数据分类原则:
- 项目元信息: 本地 + 服务器 (同步)
- 版本信息: 本地 + 服务器 (同步)  
- 翻译内容: 本地 + 服务器 (同步)
- 构建数据: 仅本地 (不同步)
- 临时数据: 仅本地 (不同步)
"""

from dataclasses import dataclass
from enum import Enum
from typing import Dict, List, Optional, Set


class DataLayerType(Enum):
    """数据层类型"""
    LOCAL_ONLY = "local_only"          # 仅本地存储
    SYNC_ENABLED = "sync_enabled"      # 本地+服务器同步
    CACHE_ONLY = "cache_only"          # 仅缓存数据


class DataSyncStrategy(Enum):
    """数据同步策略"""
    IMMEDIATE = "immediate"            # 立即同步
    BATCH = "batch"                   # 批量同步
    MANUAL = "manual"                 # 手动同步
    NO_SYNC = "no_sync"               # 不同步


@dataclass
class FieldLayerConfig:
    """字段分层配置"""
    layer_type: DataLayerType
    sync_strategy: DataSyncStrategy
    is_sensitive: bool = False         # 是否敏感数据
    is_pii: bool = False              # 是否个人标识信息
    description: str = ""


class DataLayerConfig:
    """数据分层配置管理"""
    
    # ============================================================
    # packs 表字段分层配置
    # ============================================================
    PACKS_FIELDS = {
        # 同步字段 (业务数据)
        "name": FieldLayerConfig(
            DataLayerType.SYNC_ENABLED,
            DataSyncStrategy.IMMEDIATE,
            description="整合包名称 - 核心业务数据"
        ),
        "project_type": FieldLayerConfig(
            DataLayerType.SYNC_ENABLED,
            DataSyncStrategy.IMMEDIATE,
            description="项目类型 - 业务分类"
        ),
        "game_type": FieldLayerConfig(
            DataLayerType.SYNC_ENABLED,
            DataSyncStrategy.IMMEDIATE,
            description="游戏类型 - 业务分类"
        ),
        "description": FieldLayerConfig(
            DataLayerType.SYNC_ENABLED,
            DataSyncStrategy.BATCH,
            description="项目描述 - 元数据"
        ),
        "author": FieldLayerConfig(
            DataLayerType.SYNC_ENABLED,
            DataSyncStrategy.BATCH,
            description="作者信息 - 元数据"
        ),
        
        # 本地字段 (构建数据)
        "path": FieldLayerConfig(
            DataLayerType.LOCAL_ONLY,
            DataSyncStrategy.NO_SYNC,
            is_sensitive=True,
            description="本地路径 - 敏感的本地配置"
        ),
        "sync_config": FieldLayerConfig(
            DataLayerType.LOCAL_ONLY,
            DataSyncStrategy.NO_SYNC,
            description="同步配置 - 本地设置"
        ),
        "build_config": FieldLayerConfig(
            DataLayerType.LOCAL_ONLY,
            DataSyncStrategy.NO_SYNC,
            description="构建配置 - 本地设置"
        ),
    }
    
    # ============================================================
    # pack_versions 表字段分层配置
    # ============================================================
    PACK_VERSIONS_FIELDS = {
        # 同步字段 (业务数据)
        "version_tag": FieldLayerConfig(
            DataLayerType.SYNC_ENABLED,
            DataSyncStrategy.IMMEDIATE,
            description="版本标签 - 核心业务数据"
        ),
        "minecraft_version": FieldLayerConfig(
            DataLayerType.SYNC_ENABLED,
            DataSyncStrategy.IMMEDIATE,
            description="MC版本 - 兼容性信息"
        ),
        "loader_type": FieldLayerConfig(
            DataLayerType.SYNC_ENABLED,
            DataSyncStrategy.IMMEDIATE,
            description="加载器类型 - 技术规格"
        ),
        "loader_version": FieldLayerConfig(
            DataLayerType.SYNC_ENABLED,
            DataSyncStrategy.BATCH,
            description="加载器版本 - 技术规格"
        ),
        "display_name": FieldLayerConfig(
            DataLayerType.SYNC_ENABLED,
            DataSyncStrategy.BATCH,
            description="显示名称 - 用户界面"
        ),
        "changelog": FieldLayerConfig(
            DataLayerType.SYNC_ENABLED,
            DataSyncStrategy.BATCH,
            description="变更日志 - 版本信息"
        ),
        "is_default": FieldLayerConfig(
            DataLayerType.SYNC_ENABLED,
            DataSyncStrategy.IMMEDIATE,
            description="默认版本标识 - 业务逻辑"
        ),
        "is_stable": FieldLayerConfig(
            DataLayerType.SYNC_ENABLED,
            DataSyncStrategy.BATCH,
            description="稳定版本标识 - 状态信息"
        ),
        
        # 本地字段 (构建数据)
        "local_path": FieldLayerConfig(
            DataLayerType.LOCAL_ONLY,
            DataSyncStrategy.NO_SYNC,
            is_sensitive=True,
            description="本地版本路径 - 敏感本地配置"
        ),
        "build_timestamp": FieldLayerConfig(
            DataLayerType.LOCAL_ONLY,
            DataSyncStrategy.NO_SYNC,
            description="构建时间戳 - 本地构建信息"
        ),
    }
    
    # ============================================================
    # mod_version_instances 表字段分层配置
    # ============================================================
    MOD_VERSION_INSTANCES_FIELDS = {
        # 同步字段 (业务数据)
        "mod_id": FieldLayerConfig(
            DataLayerType.SYNC_ENABLED,
            DataSyncStrategy.IMMEDIATE,
            description="MOD标识符 - 核心业务数据"
        ),
        "mod_version": FieldLayerConfig(
            DataLayerType.SYNC_ENABLED,
            DataSyncStrategy.IMMEDIATE,
            description="MOD版本 - 核心业务数据"
        ),
        "mod_name": FieldLayerConfig(
            DataLayerType.SYNC_ENABLED,
            DataSyncStrategy.IMMEDIATE,
            description="MOD显示名称 - 用户界面"
        ),
        "description": FieldLayerConfig(
            DataLayerType.SYNC_ENABLED,
            DataSyncStrategy.BATCH,
            description="MOD描述 - 元数据"
        ),
        "authors": FieldLayerConfig(
            DataLayerType.SYNC_ENABLED,
            DataSyncStrategy.BATCH,
            description="作者列表 - 元数据"
        ),
        "homepage_url": FieldLayerConfig(
            DataLayerType.SYNC_ENABLED,
            DataSyncStrategy.BATCH,
            description="主页链接 - 元数据"
        ),
        "minecraft_versions": FieldLayerConfig(
            DataLayerType.SYNC_ENABLED,
            DataSyncStrategy.BATCH,
            description="兼容MC版本 - 技术规格"
        ),
        "dependencies": FieldLayerConfig(
            DataLayerType.SYNC_ENABLED,
            DataSyncStrategy.BATCH,
            description="依赖关系 - 技术规格"
        ),
        
        # 本地字段 (构建数据)
        "jar_file_path": FieldLayerConfig(
            DataLayerType.LOCAL_ONLY,
            DataSyncStrategy.NO_SYNC,
            is_sensitive=True,
            description="JAR文件路径 - 敏感本地配置"
        ),
        "jar_file_size": FieldLayerConfig(
            DataLayerType.LOCAL_ONLY,
            DataSyncStrategy.NO_SYNC,
            description="文件大小 - 本地文件信息"
        ),
        "jar_file_hash": FieldLayerConfig(
            DataLayerType.LOCAL_ONLY,
            DataSyncStrategy.NO_SYNC,
            description="文件哈希 - 本地验证信息"
        ),
        "extraction_path": FieldLayerConfig(
            DataLayerType.LOCAL_ONLY,
            DataSyncStrategy.NO_SYNC,
            is_sensitive=True,
            description="解压路径 - 敏感本地配置"
        ),
    }
    
    # ============================================================
    # content_instances 表字段分层配置
    # ============================================================
    CONTENT_INSTANCES_FIELDS = {
        # 同步字段 (业务数据)
        "content_key": FieldLayerConfig(
            DataLayerType.SYNC_ENABLED,
            DataSyncStrategy.IMMEDIATE,
            description="内容键 - 核心翻译数据"
        ),
        "content_source": FieldLayerConfig(
            DataLayerType.SYNC_ENABLED,
            DataSyncStrategy.IMMEDIATE,
            description="内容来源 - 业务分类"
        ),
        "source_identifier": FieldLayerConfig(
            DataLayerType.SYNC_ENABLED,
            DataSyncStrategy.IMMEDIATE,
            description="来源标识符 - 关联数据"
        ),
        "source_text": FieldLayerConfig(
            DataLayerType.SYNC_ENABLED,
            DataSyncStrategy.IMMEDIATE,
            description="源文本 - 核心翻译数据"
        ),
        "language_code": FieldLayerConfig(
            DataLayerType.SYNC_ENABLED,
            DataSyncStrategy.IMMEDIATE,
            description="语言代码 - 核心翻译数据"
        ),
        "content_type": FieldLayerConfig(
            DataLayerType.SYNC_ENABLED,
            DataSyncStrategy.BATCH,
            description="内容类型 - 业务分类"
        ),
        "category": FieldLayerConfig(
            DataLayerType.SYNC_ENABLED,
            DataSyncStrategy.BATCH,
            description="内容分类 - 业务分类"
        ),
        "comment": FieldLayerConfig(
            DataLayerType.SYNC_ENABLED,
            DataSyncStrategy.BATCH,
            description="注释 - 翻译辅助信息"
        ),
        "priority": FieldLayerConfig(
            DataLayerType.SYNC_ENABLED,
            DataSyncStrategy.BATCH,
            description="优先级 - 覆盖逻辑"
        ),
        "is_override": FieldLayerConfig(
            DataLayerType.SYNC_ENABLED,
            DataSyncStrategy.IMMEDIATE,
            description="覆盖标识 - 业务逻辑"
        ),
        
        # 本地字段 (构建数据)
        "file_path": FieldLayerConfig(
            DataLayerType.LOCAL_ONLY,
            DataSyncStrategy.NO_SYNC,
            is_sensitive=True,
            description="文件路径 - 敏感本地配置"
        ),
        "file_format": FieldLayerConfig(
            DataLayerType.LOCAL_ONLY,
            DataSyncStrategy.NO_SYNC,
            description="文件格式 - 本地技术信息"
        ),
        "line_number": FieldLayerConfig(
            DataLayerType.LOCAL_ONLY,
            DataSyncStrategy.NO_SYNC,
            description="行号 - 本地定位信息"
        ),
        "raw_content": FieldLayerConfig(
            DataLayerType.LOCAL_ONLY,
            DataSyncStrategy.NO_SYNC,
            description="原始内容 - 本地缓存"
        ),
    }
    
    @classmethod
    def get_sync_fields(cls, table_name: str) -> Set[str]:
        """获取需要同步的字段"""
        table_config = getattr(cls, f"{table_name.upper()}_FIELDS", {})
        return {
            field for field, config in table_config.items()
            if config.layer_type == DataLayerType.SYNC_ENABLED
        }
    
    @classmethod
    def get_local_only_fields(cls, table_name: str) -> Set[str]:
        """获取仅本地存储的字段"""
        table_config = getattr(cls, f"{table_name.upper()}_FIELDS", {})
        return {
            field for field, config in table_config.items()
            if config.layer_type == DataLayerType.LOCAL_ONLY
        }
    
    @classmethod
    def get_sensitive_fields(cls, table_name: str) -> Set[str]:
        """获取敏感字段"""
        table_config = getattr(cls, f"{table_name.upper()}_FIELDS", {})
        return {
            field for field, config in table_config.items()
            if config.is_sensitive
        }
    
    @classmethod
    def get_immediate_sync_fields(cls, table_name: str) -> Set[str]:
        """获取需要立即同步的字段"""
        table_config = getattr(cls, f"{table_name.upper()}_FIELDS", {})
        return {
            field for field, config in table_config.items()
            if config.sync_strategy == DataSyncStrategy.IMMEDIATE
        }
    
    @classmethod
    def should_sync_field(cls, table_name: str, field_name: str) -> bool:
        """判断字段是否需要同步"""
        table_config = getattr(cls, f"{table_name.upper()}_FIELDS", {})
        field_config = table_config.get(field_name)
        
        if not field_config:
            return False
            
        return field_config.layer_type == DataLayerType.SYNC_ENABLED
    
    @classmethod
    def is_sensitive_field(cls, table_name: str, field_name: str) -> bool:
        """判断字段是否敏感"""
        table_config = getattr(cls, f"{table_name.upper()}_FIELDS", {})
        field_config = table_config.get(field_name)
        
        if not field_config:
            return False
            
        return field_config.is_sensitive


# ============================================================
# 数据分层验证器
# ============================================================

class DataLayerValidator:
    """数据分层验证器"""
    
    @staticmethod
    def validate_sync_payload(table_name: str, data: Dict) -> Dict:
        """验证同步数据负载，过滤本地字段"""
        sync_fields = DataLayerConfig.get_sync_fields(table_name)
        
        return {
            key: value for key, value in data.items()
            if key in sync_fields
        }
    
    @staticmethod
    def mask_sensitive_data(table_name: str, data: Dict) -> Dict:
        """掩码敏感数据"""
        sensitive_fields = DataLayerConfig.get_sensitive_fields(table_name)
        masked_data = data.copy()
        
        for field in sensitive_fields:
            if field in masked_data:
                masked_data[field] = "***MASKED***"
        
        return masked_data
    
    @staticmethod
    def prepare_local_data(table_name: str, data: Dict) -> Dict:
        """准备本地数据（保留所有字段）"""
        return data.copy()
    
    @staticmethod
    def extract_build_data(table_name: str, data: Dict) -> Dict:
        """提取构建数据（仅本地字段）"""
        local_fields = DataLayerConfig.get_local_only_fields(table_name)
        
        return {
            key: value for key, value in data.items()
            if key in local_fields
        }


# ============================================================
# 数据分层查询助手
# ============================================================

class DataLayerQueryHelper:
    """数据分层查询助手"""
    
    @staticmethod
    def get_sync_select_fields(table_name: str, alias: str = "") -> str:
        """获取同步数据的SELECT字段"""
        sync_fields = DataLayerConfig.get_sync_fields(table_name)
        prefix = f"{alias}." if alias else ""
        
        return ", ".join([f"{prefix}{field}" for field in sorted(sync_fields)])
    
    @staticmethod
    def get_local_select_fields(table_name: str, alias: str = "") -> str:
        """获取本地数据的SELECT字段"""
        local_fields = DataLayerConfig.get_local_only_fields(table_name)
        prefix = f"{alias}." if alias else ""
        
        return ", ".join([f"{prefix}{field}" for field in sorted(local_fields)])
    
    @staticmethod
    def get_full_select_fields(table_name: str, alias: str = "") -> str:
        """获取完整数据的SELECT字段"""
        table_config = getattr(DataLayerConfig, f"{table_name.upper()}_FIELDS", {})
        prefix = f"{alias}." if alias else ""
        
        return ", ".join([f"{prefix}{field}" for field in sorted(table_config.keys())])