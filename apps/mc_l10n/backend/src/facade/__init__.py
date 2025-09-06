"""
门面模式实现
提供简化的统一接口
"""

from .mc_l10n_facade import (
    MCL10nFacade,
    ScanResult,
    TranslationResult,
    SyncResult
)

__all__ = [
    'MCL10nFacade',
    'ScanResult',
    'TranslationResult',
    'SyncResult',
]