"""
翻译数据同步器模块

提供翻译数据的增量同步、冲突解决和版本管理功能
"""

from .interfaces import (
    BaseTranslationSynchronizer,
    IConflictResolver,
    IRemoteTranslationClient,
    ITranslationCache,
    ITranslationRepository,
    ITranslationSynchronizer,
)
from .translation_synchronizer import (
    ConflictResolver,
    IncrementalTransferManager,
    TranslationDataCompressor,
    TranslationSynchronizer,
)

__all__ = [
    # 接口
    "ITranslationSynchronizer",
    "ITranslationRepository",
    "IRemoteTranslationClient", 
    "IConflictResolver",
    "ITranslationCache",
    "BaseTranslationSynchronizer",
    
    # 实现
    "TranslationSynchronizer",
    "ConflictResolver",
    "IncrementalTransferManager",
    "TranslationDataCompressor",
]