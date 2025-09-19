"""
翻译数据提取器模块

提供各种游戏类型的翻译数据提取功能
"""

from .interfaces import (
    BaseTranslationExtractor,
    IFileScanner,
    IGameSpecificParser,
    ITranslationExtractor,
)
from .minecraft_extractor import MinecraftTranslationExtractor

__all__ = [
    "ITranslationExtractor",
    "IFileScanner", 
    "IGameSpecificParser",
    "BaseTranslationExtractor",
    "MinecraftTranslationExtractor",
]