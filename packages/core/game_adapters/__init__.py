"""
游戏适配器模块
通用游戏文件传输和处理适配器
"""

from .base_adapter import (
    GameAdapter, BaseGameAdapter, GameType, ResourceType,
    GameResource, ProcessingOptions, ProcessingResult
)
from .minecraft_adapter import MinecraftAdapter
from .rimworld_adapter import RimWorldAdapter
from .factorio_adapter import FactorioAdapter
from .registry import AdapterRegistry, get_global_registry

__all__ = [
    'GameAdapter', 'BaseGameAdapter', 'GameType', 'ResourceType',
    'GameResource', 'ProcessingOptions', 'ProcessingResult',
    'MinecraftAdapter', 'RimWorldAdapter', 'FactorioAdapter',
    'AdapterRegistry', 'get_global_registry'
]
