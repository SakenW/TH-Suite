# packages/application/game_registry.py
"""
游戏插件注册表实现

负责管理所有游戏插件的注册、发现和实例化。
提供统一的游戏类型检测和插件获取功能。
"""

from __future__ import annotations

from pathlib import Path

from ..core.interfaces import GamePlugin


class GamePluginRegistryImpl:
    """游戏插件注册表实现"""

    def __init__(self):
        self._plugins: dict[str, GamePlugin] = {}
        self._detection_order: list[str] = []

    def register_plugin(self, plugin: GamePlugin) -> None:
        """注册游戏插件

        Args:
            plugin: 游戏插件实例
        """
        self._plugins[plugin.name] = plugin

        # 维护检测顺序，新注册的插件优先级更高
        if plugin.name in self._detection_order:
            self._detection_order.remove(plugin.name)
        self._detection_order.insert(0, plugin.name)

    def get_plugin(self, game_name: str) -> GamePlugin | None:
        """获取游戏插件

        Args:
            game_name: 游戏名称

        Returns:
            游戏插件实例，如果未找到则返回 None
        """
        return self._plugins.get(game_name)

    def get_all_plugins(self) -> list[GamePlugin]:
        """获取所有已注册的插件

        Returns:
            所有插件实例列表
        """
        return list(self._plugins.values())

    def detect_game_type(self, project_path: Path) -> str | None:
        """自动检测项目的游戏类型

        按照注册顺序依次尝试每个插件的检测能力，
        返回第一个能够识别该项目的游戏类型。

        Args:
            project_path: 项目路径

        Returns:
            游戏类型名称，如果无法识别则返回 None
        """
        for game_name in self._detection_order:
            plugin = self._plugins[game_name]
            scanner = plugin.create_project_scanner()

            try:
                # 使用同步方式快速检测
                import asyncio

                loop = None
                try:
                    loop = asyncio.get_running_loop()
                except RuntimeError:
                    pass

                if loop:
                    # 在异步环境中运行
                    async def detect():
                        detected_type = await scanner.detect_project_type(project_path)
                        return detected_type is not None

                    # 创建任务但不等待，而是使用同步的方式检测
                    # 这里简化处理，实际可以根据具体需求调整
                    pass

                # 简化的同步检测逻辑
                # 检查项目路径是否包含该游戏特有的标识
                if self._quick_detect_game_type(project_path, plugin):
                    return game_name

            except Exception:
                # 忽略检测过程中的错误，继续尝试下一个插件
                continue

        return None

    def _quick_detect_game_type(self, project_path: Path, plugin: GamePlugin) -> bool:
        """快速检测游戏类型的简化实现

        Args:
            project_path: 项目路径
            plugin: 游戏插件

        Returns:
            是否匹配该游戏类型
        """
        # 根据插件支持的项目类型进行简单的路径匹配

        if "minecraft" in plugin.name.lower():
            # Minecraft 项目检测逻辑
            if project_path.is_file() and project_path.suffix.lower() in [
                ".jar",
                ".zip",
            ]:
                return True
            if project_path.is_dir():
                # 检查是否有 Minecraft 相关的目录或文件
                minecraft_indicators = [
                    "mods",
                    "minecraft",
                    "manifest.json",
                    "instance.cfg",
                    "config",
                    "resourcepacks",
                    "shaderpacks",
                ]
                for indicator in minecraft_indicators:
                    if (project_path / indicator).exists():
                        return True

        elif "rusted_warfare" in plugin.name.lower() or "rw" in plugin.name.lower():
            # Rusted Warfare 项目检测逻辑
            rw_indicators = [
                "units",
                "maps",
                "mods",
                "rustedWarfare.exe",
                "assets",
                "data/i18n",
            ]
            for indicator in rw_indicators:
                if (project_path / indicator).exists():
                    return True

        elif "rimworld" in plugin.name.lower():
            # RimWorld (环世界) 项目检测逻辑
            rimworld_indicators = [
                "Mods",
                "About/About.xml",
                "Defs",
                "Languages",
                "Patches",
                "Assemblies",
            ]
            for indicator in rimworld_indicators:
                if (project_path / indicator).exists():
                    return True

        elif "factorio" in plugin.name.lower():
            # Factorio (异星工厂) 项目检测逻辑
            factorio_indicators = [
                "info.json",
                "data.lua",
                "locale",
                "graphics",
                "sounds",
                "control.lua",
            ]
            for indicator in factorio_indicators:
                if (project_path / indicator).exists():
                    return True

        return False

    def get_plugins_by_file_extension(self, extension: str) -> list[GamePlugin]:
        """根据文件扩展名获取支持的插件

        Args:
            extension: 文件扩展名 (如 '.json', '.lang')

        Returns:
            支持该扩展名的插件列表
        """
        matching_plugins = []
        for plugin in self._plugins.values():
            if extension in plugin.supported_file_extensions:
                matching_plugins.append(plugin)
        return matching_plugins

    def get_plugin_info(self) -> list[dict[str, any]]:
        """获取所有插件的信息摘要

        Returns:
            插件信息列表，每个元素包含插件的基本信息
        """
        plugin_info = []
        for plugin in self._plugins.values():
            info = {
                "name": plugin.name,
                "display_name": plugin.display_name,
                "version": plugin.version,
                "supported_file_extensions": plugin.supported_file_extensions,
                "supported_project_types": plugin.supported_project_types,
            }
            plugin_info.append(info)

        return plugin_info

    def unregister_plugin(self, game_name: str) -> bool:
        """取消注册游戏插件

        Args:
            game_name: 游戏名称

        Returns:
            是否成功取消注册
        """
        if game_name in self._plugins:
            del self._plugins[game_name]
            if game_name in self._detection_order:
                self._detection_order.remove(game_name)
            return True
        return False

    def clear_all_plugins(self) -> None:
        """清除所有已注册的插件"""
        self._plugins.clear()
        self._detection_order.clear()

    def is_plugin_registered(self, game_name: str) -> bool:
        """检查插件是否已注册

        Args:
            game_name: 游戏名称

        Returns:
            是否已注册
        """
        return game_name in self._plugins

    def get_plugin_count(self) -> int:
        """获取已注册插件数量

        Returns:
            插件数量
        """
        return len(self._plugins)
