"""
翻译数据传输系统

专注于传输翻译条目数据而非文件的轻量级传输架构
"""

from .models import (
    # 枚举类型
    GameType,
    ModLoader,
    TranslationStatus,
    SyncStrategy,
    ConflictType,
    ConflictResolution,
    
    # 数据模型
    Comment,
    Contributor,
    ModInfo,
    MinecraftModInfo,
    RimWorldModInfo,
    FactorioModInfo,
    TranslationEntry,
    EntryMove,
    TranslationProject,
    TranslationDelta,
    TranslationConflict,
    SyncResult,
    IncrementalSyncPlan,
    
    # 工厂函数
    create_mod_info,
    generate_entry_id,
    generate_project_id,
    generate_delta_id,
)

__all__ = [
    # 枚举类型
    "GameType",
    "ModLoader", 
    "TranslationStatus",
    "SyncStrategy",
    "ConflictType",
    "ConflictResolution",
    
    # 数据模型
    "Comment",
    "Contributor",
    "ModInfo",
    "MinecraftModInfo",
    "RimWorldModInfo", 
    "FactorioModInfo",
    "TranslationEntry",
    "EntryMove",
    "TranslationProject",
    "TranslationDelta",
    "TranslationConflict",
    "SyncResult",
    "IncrementalSyncPlan",
    
    # 工厂函数
    "create_mod_info",
    "generate_entry_id",
    "generate_project_id",
    "generate_delta_id",
]