"""
Minecraft游戏特定处理器

职责：
- 实现Minecraft特有的项目检测逻辑
- 处理MOD文件的内容提取
- 识别组合包类型和配置
- 提供MC特有的文件分析功能

设计原则：
- 单一游戏：仅处理Minecraft相关逻辑
- 接口实现：严格实现GameSpecificHandler接口
- 可复用：可被多个MC工具应用复用
"""

import json
import logging
import os
import re
import sys
import zipfile
from pathlib import Path
from typing import Any

# Add universal-scanner to path
current_dir = os.path.dirname(__file__)
packages_dir = os.path.abspath(os.path.join(current_dir, "..", ".."))
universal_scanner_dir = os.path.join(packages_dir, "universal-scanner")
sys.path.insert(0, universal_scanner_dir)

from core.scanner_interface import (  # noqa: E402
    ContentItem,
    ContentType,
    GameSpecificHandler,
)

logger = logging.getLogger(__name__)


class MinecraftGameHandler(GameSpecificHandler):
    """Minecraft游戏处理器"""

    def __init__(self):
        self.modpack_indicators = [
            "manifest.json",  # CurseForge
            "modrinth.index.json",  # Modrinth
            "instance.cfg",  # MultiMC
            "mmc-pack.json",  # MultiMC新格式
        ]

        self.mod_metadata_files = {
            "forge": ["META-INF/mods.toml", "mcmod.info"],
            "fabric": ["fabric.mod.json"],
            "quilt": ["quilt.mod.json"],
            "neoforge": ["META-INF/neoforge.mods.toml"],
        }

    @property
    def game_type(self) -> str:
        return "minecraft"

    async def detect_project_info(self, path: Path) -> dict[str, Any]:
        """检测Minecraft项目信息"""
        project_info = {
            "detected": False,
            "game_type": "minecraft",
            "project_type": "unknown",
            "name": path.name,
            "path": str(path),
        }

        if not path.exists():
            return project_info

        try:
            # 检测组合包
            modpack_info = await self._detect_modpack_info(path)
            if modpack_info:
                project_info.update(modpack_info)
                project_info["detected"] = True
                project_info["project_type"] = "modpack"
                return project_info

            # 检测单个MOD
            if path.is_file() and path.suffix.lower() in [".jar", ".zip"]:
                mod_info = await self._detect_mod_info(path)
                if mod_info:
                    project_info.update(mod_info)
                    project_info["detected"] = True
                    project_info["project_type"] = "mod"
                    return project_info

            # 检测MOD开发环境
            if path.is_dir():
                dev_info = await self._detect_dev_environment(path)
                if dev_info:
                    project_info.update(dev_info)
                    project_info["detected"] = True
                    project_info["project_type"] = "mod_development"
                    return project_info

        except Exception as e:
            logger.error(f"Error detecting Minecraft project: {e}")

        return project_info

    async def _detect_modpack_info(self, path: Path) -> dict[str, Any] | None:
        """检测组合包信息"""
        if not path.is_dir():
            return None

        # CurseForge 格式
        manifest_path = path / "manifest.json"
        if manifest_path.exists():
            try:
                with open(manifest_path, encoding="utf-8") as f:
                    manifest = json.load(f)
                    if manifest.get("manifestType") == "minecraftModpack":
                        minecraft_info = manifest.get("minecraft", {})
                        mod_loaders = minecraft_info.get("modLoaders", [])

                        return {
                            "platform": "CurseForge",
                            "name": manifest.get("name", path.name),
                            "version": manifest.get("version", "unknown"),
                            "minecraft_version": minecraft_info.get(
                                "version", "unknown"
                            ),
                            "mod_loader": mod_loaders[0]
                            .get("id", "unknown")
                            .split("-")[0]
                            if mod_loaders
                            else "unknown",
                            "author": manifest.get("author", "unknown"),
                            "expected_mod_count": len(manifest.get("files", [])),
                            "manifest_version": manifest.get("manifestVersion", 1),
                            "overrides": manifest.get("overrides", "overrides"),
                            "files_info": manifest.get("files", []),
                        }
            except Exception as e:
                logger.warning(f"Failed to parse CurseForge manifest: {e}")

        # Modrinth 格式
        modrinth_path = path / "modrinth.index.json"
        if modrinth_path.exists():
            try:
                with open(modrinth_path, encoding="utf-8") as f:
                    modrinth = json.load(f)
                    dependencies = modrinth.get("dependencies", {})

                    return {
                        "platform": "Modrinth",
                        "name": modrinth.get("name", path.name),
                        "version": modrinth.get("versionId", "unknown"),
                        "minecraft_version": dependencies.get("minecraft", "unknown"),
                        "mod_loader": next(
                            (k for k in dependencies.keys() if k != "minecraft"),
                            "unknown",
                        ),
                        "expected_mod_count": len(modrinth.get("files", [])),
                        "format_version": modrinth.get("formatVersion", 1),
                        "game": modrinth.get("game", "minecraft"),
                        "dependencies": dependencies,
                        "files_info": modrinth.get("files", []),
                    }
            except Exception as e:
                logger.warning(f"Failed to parse Modrinth index: {e}")

        # MultiMC 格式
        mmc_pack_path = path / "mmc-pack.json"
        instance_cfg_path = path / "instance.cfg"
        if mmc_pack_path.exists() or instance_cfg_path.exists():
            multimc_info = {"platform": "MultiMC"}

            try:
                if mmc_pack_path.exists():
                    with open(mmc_pack_path, encoding="utf-8") as f:
                        mmc_pack = json.load(f)
                        multimc_info.update(
                            {
                                "name": mmc_pack.get("name", path.name),
                                "version": mmc_pack.get("version", "unknown"),
                                "format_version": mmc_pack.get("formatVersion", 1),
                                "components": mmc_pack.get("components", []),
                            }
                        )

                if instance_cfg_path.exists():
                    with open(instance_cfg_path, encoding="utf-8") as f:
                        for line in f:
                            line = line.strip()
                            if line.startswith("name="):
                                multimc_info["name"] = line.split("=", 1)[1]
                            elif line.startswith("IntendedVersion="):
                                multimc_info["minecraft_version"] = line.split("=", 1)[
                                    1
                                ]
                            elif line.startswith("iconKey="):
                                multimc_info["icon"] = line.split("=", 1)[1]

                return multimc_info

            except Exception as e:
                logger.warning(f"Failed to parse MultiMC config: {e}")

        # 通用目录结构检测
        mods_dir = path / "mods"
        if mods_dir.exists() and mods_dir.is_dir():
            jar_files = list(mods_dir.glob("*.jar"))
            if jar_files:
                return {
                    "platform": "Generic",
                    "expected_mod_count": len(jar_files),
                    "mods_directory": str(mods_dir),
                    "sample_mods": [f.name for f in jar_files[:5]],  # 前5个作为示例
                }

        return None

    async def _detect_mod_info(self, jar_path: Path) -> dict[str, Any] | None:
        """检测单个MOD信息"""
        try:
            with zipfile.ZipFile(jar_path, "r") as jar:
                file_list = jar.namelist()

                # 检测加载器类型和元数据
                for loader, metadata_files in self.mod_metadata_files.items():
                    for metadata_file in metadata_files:
                        if metadata_file in file_list:
                            mod_info = await self._parse_mod_metadata(
                                jar, metadata_file, loader
                            )
                            if mod_info:
                                mod_info.update(
                                    {
                                        "file_path": str(jar_path),
                                        "file_size": jar_path.stat().st_size,
                                        "mod_loader": loader,
                                    }
                                )
                                return mod_info

                # 如果没有找到标准元数据，返回基本信息
                return {
                    "mod_id": jar_path.stem,
                    "name": jar_path.stem,
                    "version": "unknown",
                    "file_path": str(jar_path),
                    "file_size": jar_path.stat().st_size,
                    "mod_loader": "unknown",
                }

        except Exception as e:
            logger.warning(f"Failed to detect mod info for {jar_path}: {e}")

        return None

    async def _parse_mod_metadata(
        self, jar: zipfile.ZipFile, metadata_file: str, loader: str
    ) -> dict[str, Any] | None:
        """解析MOD元数据"""
        try:
            with jar.open(metadata_file) as f:
                content = f.read().decode("utf-8")

                if metadata_file.endswith(".json"):
                    # JSON格式 (Fabric/Quilt)
                    data = json.loads(content)
                    if loader == "fabric":
                        return {
                            "mod_id": data.get("id"),
                            "name": data.get("name"),
                            "version": data.get("version"),
                            "description": data.get("description"),
                            "authors": data.get("authors", []),
                            "dependencies": list(data.get("depends", {}).keys()),
                            "homepage": data.get("contact", {}).get("homepage"),
                            "source": data.get("contact", {}).get("sources"),
                        }
                    elif loader == "quilt":
                        if "quilt_loader" in data:
                            loader_data = data["quilt_loader"]
                            metadata = loader_data.get("metadata", {})
                            return {
                                "mod_id": loader_data.get("id"),
                                "name": metadata.get("name"),
                                "version": loader_data.get("version"),
                                "description": metadata.get("description"),
                                "authors": metadata.get("contributors", {}).get(
                                    "author", []
                                ),
                            }
                    elif metadata_file == "mcmod.info":
                        # 旧版Forge格式
                        if isinstance(data, list) and data:
                            mod_data = data[0]
                            return {
                                "mod_id": mod_data.get("modid"),
                                "name": mod_data.get("name"),
                                "version": mod_data.get("version"),
                                "description": mod_data.get("description"),
                                "authors": mod_data.get("authorList", []),
                                "homepage": mod_data.get("url"),
                            }

                elif metadata_file.endswith(".toml"):
                    # TOML格式 (Forge/NeoForge)
                    return self._parse_toml_metadata(content)

        except Exception as e:
            logger.warning(f"Failed to parse {metadata_file}: {e}")

        return None

    def _parse_toml_metadata(self, toml_content: str) -> dict[str, Any]:
        """简单的TOML解析（用于mods.toml）"""
        mod_info = {}
        current_section = None

        for line in toml_content.split("\n"):
            line = line.strip()

            # 跳过注释和空行
            if not line or line.startswith("#"):
                continue

            # 检测section
            if line.startswith("[") and line.endswith("]"):
                current_section = line[1:-1]
                continue

            # 解析键值对
            if "=" in line and current_section in [None, "mods"]:
                key, value = line.split("=", 1)
                key = key.strip()
                value = value.strip().strip("\"'")

                if key == "modId":
                    mod_info["mod_id"] = value
                elif key == "displayName":
                    mod_info["name"] = value
                elif key == "version":
                    mod_info["version"] = value
                elif key == "description":
                    mod_info["description"] = value
                elif key == "authors":
                    mod_info["authors"] = [value]  # 简化处理

        return mod_info

    async def _detect_dev_environment(self, path: Path) -> dict[str, Any] | None:
        """检测MOD开发环境"""
        # 检查Gradle构建文件
        if (path / "build.gradle").exists() or (path / "build.gradle.kts").exists():
            # 检查是否为Minecraft Mod开发
            gradle_files = list(path.glob("*.gradle*"))
            for gradle_file in gradle_files:
                try:
                    content = gradle_file.read_text(encoding="utf-8")
                    if any(
                        keyword in content.lower()
                        for keyword in ["minecraft", "forge", "fabric", "quilt"]
                    ):
                        return {
                            "build_system": "gradle",
                            "development_environment": True,
                        }
                except (UnicodeDecodeError, OSError):
                    continue

        return None

    async def extract_content_items(self, file_path: Path) -> list[ContentItem]:
        """从Minecraft文件提取内容项"""
        content_items = []

        try:
            if file_path.suffix.lower() == ".jar":
                # 处理JAR文件
                content_items.extend(await self._extract_from_jar(file_path))
            elif file_path.suffix.lower() in [".json", ".lang"]:
                # 处理独立语言文件
                content_items.extend(await self._extract_from_language_file(file_path))

        except Exception as e:
            logger.error(f"Failed to extract content from {file_path}: {e}")

        return content_items

    async def _extract_from_jar(self, jar_path: Path) -> list[ContentItem]:
        """从JAR文件提取内容"""
        content_items = []

        try:
            # 首先创建MOD内容项
            mod_info = await self._detect_mod_info(jar_path)
            if mod_info:
                # 计算MOD文件哈希
                import hashlib

                with open(jar_path, "rb") as f:
                    mod_hash = hashlib.sha256(f.read()).hexdigest()

                mod_item = ContentItem(
                    content_hash=mod_hash,
                    content_type=ContentType.MOD,
                    name=mod_info.get("name", jar_path.stem),
                    metadata=mod_info,
                )
                content_items.append(mod_item)

                # 提取语言文件
                with zipfile.ZipFile(jar_path, "r") as jar:
                    for file_info in jar.filelist:
                        if self._is_language_file(file_info.filename):
                            try:
                                lang_item = await self._extract_language_from_jar(
                                    jar, file_info, mod_hash, jar_path
                                )
                                if lang_item:
                                    content_items.append(lang_item)
                            except Exception as e:
                                logger.warning(
                                    f"Failed to extract language file {file_info.filename}: {e}"
                                )

        except Exception as e:
            logger.error(f"Failed to extract from JAR {jar_path}: {e}")

        return content_items

    def _is_language_file(self, file_path: str) -> bool:
        """判断是否为语言文件"""
        patterns = [
            r"assets/[^/]+/lang/[^/]+\.(json|lang)$",
            r"data/[^/]+/lang/[^/]+\.(json|lang)$",
            r"lang/[^/]+\.(json|lang)$",
        ]
        return any(re.search(pattern, file_path, re.IGNORECASE) for pattern in patterns)

    async def _extract_language_from_jar(
        self,
        jar: zipfile.ZipFile,
        file_info: zipfile.ZipInfo,
        parent_mod_hash: str,
        jar_path: Path,
    ) -> ContentItem | None:
        """从JAR中提取语言文件内容项"""
        try:
            with jar.open(file_info) as f:
                content = f.read().decode("utf-8")

                if file_info.filename.endswith(".json"):
                    entries = json.loads(content)
                elif file_info.filename.endswith(".lang"):
                    # 解析.lang格式
                    entries = {}
                    for line in content.split("\n"):
                        line = line.strip()
                        if line and "=" in line and not line.startswith("#"):
                            key, value = line.split("=", 1)
                            entries[key.strip()] = value.strip()
                else:
                    return None

                if not isinstance(entries, dict):
                    return None

                # 提取语言信息
                locale = self._extract_locale_from_path(file_info.filename)
                namespace = self._extract_namespace_from_path(file_info.filename)

                # 计算语言文件内容哈希
                import hashlib

                lang_hash = hashlib.sha256(
                    json.dumps(entries, sort_keys=True).encode("utf-8")
                ).hexdigest()

                lang_item = ContentItem(
                    content_hash=lang_hash,
                    content_type=ContentType.LANGUAGE_FILE,
                    name=f"{namespace}:{locale}",
                    metadata={
                        "locale": locale,
                        "namespace": namespace,
                        "key_count": len(entries),
                        "file_path": file_info.filename,
                        "source_jar": str(jar_path),
                        "entries": entries,
                    },
                    relationships={"parent_mod": parent_mod_hash},
                )

                return lang_item

        except Exception as e:
            logger.warning(f"Failed to extract language file {file_info.filename}: {e}")

        return None

    def _extract_locale_from_path(self, file_path: str) -> str:
        """从文件路径提取语言代码"""
        match = re.search(r"/([a-z]{2}_[a-z]{2})\.[^/]+$", file_path.lower())
        return match.group(1) if match else "unknown"

    def _extract_namespace_from_path(self, file_path: str) -> str:
        """从文件路径提取命名空间"""
        # assets/{namespace}/lang/{locale}.json
        match = re.search(r"assets/([^/]+)/lang/", file_path)
        if match:
            return match.group(1)

        # data/{namespace}/lang/{locale}.json
        match = re.search(r"data/([^/]+)/lang/", file_path)
        if match:
            return match.group(1)

        return "minecraft"

    async def _extract_from_language_file(self, file_path: Path) -> list[ContentItem]:
        """从独立语言文件提取内容"""
        content_items = []

        try:
            content = file_path.read_text(encoding="utf-8")

            if file_path.suffix.lower() == ".json":
                entries = json.loads(content)
            else:
                # .lang格式
                entries = {}
                for line in content.split("\n"):
                    line = line.strip()
                    if line and "=" in line and not line.startswith("#"):
                        key, value = line.split("=", 1)
                        entries[key.strip()] = value.strip()

            if isinstance(entries, dict) and entries:
                # 计算内容哈希
                import hashlib

                lang_hash = hashlib.sha256(
                    json.dumps(entries, sort_keys=True).encode("utf-8")
                ).hexdigest()

                locale = self._extract_locale_from_path(str(file_path))

                lang_item = ContentItem(
                    content_hash=lang_hash,
                    content_type=ContentType.LANGUAGE_FILE,
                    name=f"standalone:{locale}",
                    metadata={
                        "locale": locale,
                        "namespace": "standalone",
                        "key_count": len(entries),
                        "file_path": str(file_path),
                        "entries": entries,
                    },
                )
                content_items.append(lang_item)

        except Exception as e:
            logger.error(f"Failed to extract from language file {file_path}: {e}")

        return content_items

    async def analyze_file_metadata(self, file_path: Path) -> dict[str, Any]:
        """分析文件元数据"""
        metadata = {
            "file_path": str(file_path),
            "file_name": file_path.name,
            "file_size": 0,
            "file_type": "unknown",
        }

        try:
            if file_path.exists():
                stat = file_path.stat()
                metadata.update(
                    {
                        "file_size": stat.st_size,
                        "last_modified": stat.st_mtime,
                        "file_type": self._determine_file_type(file_path),
                    }
                )

                # 特定类型的额外分析
                if file_path.suffix.lower() == ".jar":
                    metadata.update(await self._analyze_jar_metadata(file_path))

        except Exception as e:
            logger.error(f"Failed to analyze metadata for {file_path}: {e}")

        return metadata

    def _determine_file_type(self, file_path: Path) -> str:
        """确定文件类型"""
        suffix = file_path.suffix.lower()

        if suffix == ".jar":
            return "minecraft_mod"
        elif suffix in [".json", ".lang"]:
            if self._is_language_file(str(file_path)):
                return "language_file"
            return "json_file"
        elif suffix == ".toml":
            return "toml_config"
        else:
            return "unknown"

    async def _analyze_jar_metadata(self, jar_path: Path) -> dict[str, Any]:
        """分析JAR文件元数据"""
        metadata = {}

        try:
            with zipfile.ZipFile(jar_path, "r") as jar:
                file_list = jar.namelist()
                metadata.update(
                    {
                        "total_entries": len(file_list),
                        "has_assets": any(f.startswith("assets/") for f in file_list),
                        "language_files_count": len(
                            [f for f in file_list if self._is_language_file(f)]
                        ),
                        "metadata_files": [
                            f
                            for f in file_list
                            if any(
                                mf in f
                                for loader_files in self.mod_metadata_files.values()
                                for mf in loader_files
                            )
                        ],
                    }
                )

                # 计算压缩信息
                compressed_size = sum(jar.getinfo(f).compress_size for f in file_list)
                uncompressed_size = sum(jar.getinfo(f).file_size for f in file_list)
                metadata.update(
                    {
                        "compressed_size": compressed_size,
                        "uncompressed_size": uncompressed_size,
                        "compression_ratio": compressed_size
                        / max(uncompressed_size, 1),
                    }
                )

        except Exception as e:
            logger.warning(f"Failed to analyze JAR metadata: {e}")

        return metadata
