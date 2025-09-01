# packages/adapters/minecraft/plugin.py
"""
Minecraft 游戏插件实现

实现 GamePlugin 接口，提供 Minecraft 游戏的完整支持。
包含项目扫描器、解析器工厂、仓储等组件的创建。
"""

from __future__ import annotations

from typing import Any

from ...core.interfaces import (
    ParserFactory,
    ProjectRepository,
    ProjectScanner,
)
from .parsers import MinecraftParserFactory
from .repository import MinecraftProjectRepository
from .scanner import MinecraftProjectScanner


class MinecraftGamePlugin:
    """Minecraft 游戏插件实现"""

    @property
    def name(self) -> str:
        """游戏名称"""
        return "minecraft"

    @property
    def display_name(self) -> str:
        """游戏显示名称"""
        return "Minecraft"

    @property
    def version(self) -> str:
        """插件版本"""
        return "1.0.0"

    @property
    def supported_file_extensions(self) -> list[str]:
        """支持的文件扩展名"""
        return [".json", ".lang", ".jar", ".zip"]

    @property
    def supported_project_types(self) -> list[str]:
        """支持的项目类型"""
        return ["modpack", "single_mod", "resource_pack", "datapack"]

    def create_project_scanner(self) -> ProjectScanner:
        """创建项目扫描器"""
        return MinecraftProjectScanner()

    def create_parser_factory(self) -> ParserFactory:
        """创建解析器工厂"""
        return MinecraftParserFactory()

    def create_project_repository(self) -> ProjectRepository[Any]:
        """创建项目仓储"""
        return MinecraftProjectRepository()

    def get_default_config(self) -> dict[str, Any]:
        """获取默认配置"""
        return {
            "scan": {
                "max_file_size": 100 * 1024 * 1024,  # 100MB
                "parallel_scan": True,
                "max_parallel_workers": 4,
                "supported_encodings": ["utf-8", "gbk", "gb2312", "latin1"],
                "ignore_patterns": [
                    ".git",
                    "__pycache__",
                    ".DS_Store",
                    "Thumbs.db",
                    "*.log",
                    "*.tmp",
                    "crash-reports",
                ],
            },
            "loaders": {
                "fabric": {
                    "metadata_files": ["fabric.mod.json"],
                    "lang_path_patterns": ["assets/*/lang/*.json"],
                },
                "forge": {
                    "metadata_files": ["mcmod.info", "META-INF/mods.toml"],
                    "lang_path_patterns": [
                        "assets/*/lang/*.lang",
                        "assets/*/lang/*.json",
                    ],
                },
                "quilt": {
                    "metadata_files": ["quilt.mod.json"],
                    "lang_path_patterns": ["assets/*/lang/*.json"],
                },
                "neoforge": {
                    "metadata_files": ["META-INF/neoforge.mods.toml"],
                    "lang_path_patterns": ["assets/*/lang/*.json"],
                },
            },
            "project_detection": {
                "modpack_indicators": [
                    "manifest.json",  # CurseForge
                    "instance.cfg",  # MultiMC
                    "mmc-pack.json",  # MultiMC
                    "config.json",  # ATLauncher
                    "modpack.json",  # Generic
                    "mods/",  # Mods directory
                    "minecraft/",  # Minecraft directory
                ],
                "mod_file_extensions": [".jar", ".zip"],
                "resource_pack_indicators": ["pack.mcmeta", "assets/"],
                "datapack_indicators": ["pack.mcmeta", "data/"],
            },
            "export": {
                "supported_formats": [
                    "json",
                    "lang",
                    "csv",
                    "xlsx",
                    "po",
                    "properties",
                ],
                "default_encoding": "utf-8",
            },
        }

    def get_loader_detection_patterns(self) -> dict[str, list[str]]:
        """获取加载器检测模式

        Returns:
            加载器名称到检测文件模式的映射
        """
        return {
            "fabric": [
                "fabric.mod.json",
                "quilt.mod.json",  # Quilt 兼容 Fabric
            ],
            "forge": ["mcmod.info", "META-INF/mods.toml"],
            "quilt": ["quilt.mod.json"],
            "neoforge": ["META-INF/neoforge.mods.toml"],
        }

    def validate_project_structure(self, project_path) -> dict[str, Any]:
        """验证项目结构

        Args:
            project_path: 项目路径

        Returns:
            验证结果，包含是否有效和详细信息
        """
        from pathlib import Path

        path = (
            Path(project_path) if not isinstance(project_path, Path) else project_path
        )
        validation_result = {
            "is_valid": False,
            "project_type": None,
            "loader_type": None,
            "issues": [],
            "recommendations": [],
        }

        if not path.exists():
            validation_result["issues"].append(f"Path does not exist: {path}")
            return validation_result

        # 检测项目类型
        config = self.get_default_config()

        if (
            path.is_file()
            and path.suffix in config["project_detection"]["mod_file_extensions"]
        ):
            validation_result["project_type"] = "single_mod"
            validation_result["is_valid"] = True

        elif path.is_dir():
            # 检查整合包指示器
            for indicator in config["project_detection"]["modpack_indicators"]:
                if (path / indicator).exists():
                    validation_result["project_type"] = "modpack"
                    validation_result["is_valid"] = True
                    break

            # 检查资源包指示器
            if not validation_result["is_valid"]:
                for indicator in config["project_detection"][
                    "resource_pack_indicators"
                ]:
                    if (path / indicator).exists():
                        validation_result["project_type"] = "resource_pack"
                        validation_result["is_valid"] = True
                        break

            # 检查数据包指示器
            if not validation_result["is_valid"]:
                for indicator in config["project_detection"]["datapack_indicators"]:
                    if (path / indicator).exists():
                        validation_result["project_type"] = "datapack"
                        validation_result["is_valid"] = True
                        break

        if not validation_result["is_valid"]:
            validation_result["issues"].append(
                "No recognized Minecraft project structure found"
            )
            validation_result["recommendations"].append(
                "Ensure the path contains Minecraft mods, resource packs, or datapacks"
            )

        return validation_result

    def get_supported_minecraft_versions(self) -> list[str]:
        """获取支持的 Minecraft 版本列表

        Returns:
            支持的版本列表
        """
        return [
            "1.20.1",
            "1.20",
            "1.19.4",
            "1.19.3",
            "1.19.2",
            "1.19.1",
            "1.19",
            "1.18.2",
            "1.18.1",
            "1.18",
            "1.17.1",
            "1.17",
            "1.16.5",
            "1.16.4",
            "1.16.3",
            "1.16.2",
            "1.16.1",
            "1.16",
            "1.15.2",
            "1.15.1",
            "1.15",
            "1.14.4",
            "1.14.3",
            "1.14.2",
            "1.14.1",
            "1.14",
            "1.13.2",
            "1.13.1",
            "1.13",
            "1.12.2",
            "1.12.1",
            "1.12",
            "1.11.2",
            "1.11.1",
            "1.11",
            "1.10.2",
            "1.10.1",
            "1.10",
            "1.9.4",
            "1.9.2",
            "1.9",
            "1.8.9",
            "1.8",
        ]

    def get_plugin_capabilities(self) -> dict[str, Any]:
        """获取插件能力描述

        Returns:
            插件能力详细信息
        """
        return {
            "scanning": {
                "can_scan_modpacks": True,
                "can_scan_single_mods": True,
                "can_scan_resource_packs": True,
                "can_scan_datapacks": True,
                "supports_parallel_scanning": True,
                "supports_progress_tracking": True,
            },
            "parsing": {
                "json_language_files": True,
                "lang_language_files": True,
                "mod_metadata_extraction": True,
                "automatic_encoding_detection": True,
                "batch_processing": True,
            },
            "export": {
                "multiple_formats": True,
                "custom_templates": False,  # 待实现
                "batch_export": True,
                "filtered_export": True,
            },
            "integration": {
                "trans_hub_sync": False,  # 待实现
                "external_tools": False,  # 待实现
                "plugin_system": True,
            },
        }
