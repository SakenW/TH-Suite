"""
Minecraft Game Parser - Minecraft 游戏解析器

职责：
- 处理 Minecraft 模组和资源包的解析
- 识别不同类型的 Minecraft 项目结构
- 提供 MC 特定的内容提取和元数据分析

功能模块：
- mc_game_handler: MC 游戏处理器主接口
- mod_parser: 模组文件解析器
- pack_detector: 组合包检测器
- language_parser: 语言文件解析器
"""

from .mc_game_handler import MinecraftGameHandler

__all__ = ["MinecraftGameHandler"]
__version__ = "1.0.0"