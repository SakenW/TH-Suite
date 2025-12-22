# packages/adapters/minecraft/__init__.py
"""
Minecraft 游戏适配器

提供 Minecraft 游戏特定的扫描器、解析器和仓储实现。
包含对 Fabric、Forge、Quilt、NeoForge 等多种加载器的支持。
"""

from .parsers import MinecraftParserFactory
from .plugin import MinecraftGamePlugin
from .repository import MinecraftProjectRepository
from .scanner import MinecraftProjectScanner

__all__ = [
    "MinecraftGamePlugin",
    "MinecraftProjectScanner",
    "MinecraftParserFactory",
    "MinecraftProjectRepository",
]
