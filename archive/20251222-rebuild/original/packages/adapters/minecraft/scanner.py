# packages/adapters/minecraft/scanner.py
"""
Minecraft 项目扫描器实现

实现 ProjectScanner 接口，提供 Minecraft 项目的扫描功能。
支持整合包、单个MOD、资源包、数据包等多种项目类型。
"""

from __future__ import annotations

import asyncio
import json
import zipfile
from collections.abc import Callable
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any

from ...core.errors import ProjectScanError, UnsupportedProjectTypeError
from ...core.types import LanguageFileInfo, ModInfo, ProjectInfo, ProjectScanResult


class MinecraftProjectType(Enum):
    """Minecraft 项目类型枚举"""

    MODPACK = "modpack"
    SINGLE_MOD = "single_mod"
    RESOURCE_PACK = "resource_pack"
    DATAPACK = "datapack"
    UNKNOWN = "unknown"


class MinecraftLoader(Enum):
    """Minecraft 加载器类型"""

    FABRIC = "fabric"
    FORGE = "forge"
    QUILT = "quilt"
    NEOFORGE = "neoforge"
    UNKNOWN = "unknown"


@dataclass
class MinecraftProjectMetadata:
    """Minecraft 项目元数据"""

    project_type: MinecraftProjectType
    loader_type: MinecraftLoader = MinecraftLoader.UNKNOWN
    minecraft_versions: list[str] = field(default_factory=list)
    mod_count: int = 0
    total_files: int = 0
    language_files_count: int = 0
    supported_languages: set[str] = field(default_factory=set)
    modpack_manifest: dict[str, Any] | None = None


class MinecraftProjectScanner:
    """Minecraft 项目扫描器实现"""

    def __init__(
        self,
        max_file_size: int = 100 * 1024 * 1024,  # 100MB
        parallel_workers: int = 4,
        supported_encodings: list[str] | None = None,
    ):
        self.max_file_size = max_file_size
        self.parallel_workers = parallel_workers
        self.supported_encodings = supported_encodings or [
            "utf-8",
            "gbk",
            "gb2312",
            "latin1",
        ]

        # 文件扩展名映射
        self.language_extensions = {".json", ".lang"}
        self.mod_extensions = {".jar", ".zip"}
        self.archive_extensions = {".zip", ".jar", ".rar", ".7z"}

        # 项目检测模式
        self.modpack_indicators = {
            "manifest.json",  # CurseForge
            "instance.cfg",  # MultiMC
            "mmc-pack.json",  # MultiMC
            "config.json",  # ATLauncher
            "modpack.json",  # Generic
            "mods/",  # Mods directory
            "minecraft/",  # Minecraft directory
        }

        self.resource_pack_indicators = {"pack.mcmeta", "assets/"}
        self.datapack_indicators = {"pack.mcmeta", "data/"}

        # 加载器检测文件
        self.loader_detection = {
            MinecraftLoader.FABRIC: ["fabric.mod.json"],
            MinecraftLoader.FORGE: ["mcmod.info", "META-INF/mods.toml"],
            MinecraftLoader.QUILT: ["quilt.mod.json"],
            MinecraftLoader.NEOFORGE: ["META-INF/neoforge.mods.toml"],
        }

    async def scan_project(
        self,
        project_path: Path,
        progress_callback: Callable[[str, float], None] | None = None,
    ) -> ProjectScanResult:
        """扫描 Minecraft 项目

        Args:
            project_path: 项目路径
            progress_callback: 进度回调函数 (message, progress_percent)

        Returns:
            项目扫描结果

        Raises:
            ProjectScanError: 扫描失败
            UnsupportedProjectTypeError: 不支持的项目类型
        """
        try:
            if progress_callback:
                progress_callback("开始扫描项目...", 0.0)

            # 验证路径
            if not project_path.exists():
                raise ProjectScanError(f"项目路径不存在: {project_path}")

            # 检测项目类型
            project_type = await self._detect_project_type(project_path)
            if project_type == MinecraftProjectType.UNKNOWN:
                raise UnsupportedProjectTypeError(
                    f"无法识别的 Minecraft 项目类型: {project_path}"
                )

            if progress_callback:
                progress_callback(f"检测到项目类型: {project_type.value}", 10.0)

            # 创建项目元数据
            metadata = MinecraftProjectMetadata(project_type=project_type)

            # 扫描文件结构
            if progress_callback:
                progress_callback("扫描文件结构...", 20.0)

            mods_info = []
            language_files = []

            if project_type == MinecraftProjectType.MODPACK:
                mods_info, language_files = await self._scan_modpack(
                    project_path, metadata, progress_callback
                )
            elif project_type == MinecraftProjectType.SINGLE_MOD:
                mod_info, mod_lang_files = await self._scan_single_mod(
                    project_path, progress_callback
                )
                if mod_info:
                    mods_info.append(mod_info)
                    language_files.extend(mod_lang_files)
            elif project_type == MinecraftProjectType.RESOURCE_PACK:
                language_files = await self._scan_resource_pack(
                    project_path, progress_callback
                )
            elif project_type == MinecraftProjectType.DATAPACK:
                language_files = await self._scan_datapack(
                    project_path, progress_callback
                )

            # 更新元数据统计
            metadata.mod_count = len(mods_info)
            metadata.language_files_count = len(language_files)
            metadata.supported_languages = {
                lang_file.language_code
                for lang_file in language_files
                if lang_file.language_code
            }

            if progress_callback:
                progress_callback("扫描完成", 100.0)

            # 创建项目信息
            # 序列化 metadata，确保枚举值被转换为字符串
            serializable_metadata = {
                "project_type": metadata.project_type.value,
                "loader_type": metadata.loader_type.value,
                "minecraft_versions": metadata.minecraft_versions,
                "mod_count": metadata.mod_count,
                "total_files": metadata.total_files,
                "language_files_count": metadata.language_files_count,
                "supported_languages": list(metadata.supported_languages),
                "modpack_manifest": metadata.modpack_manifest,
            }

            project_info = ProjectInfo(
                name=project_path.name,
                path=str(project_path),
                project_type=project_type.value,
                game_type="minecraft",
                loader_type=metadata.loader_type.value,
                minecraft_versions=metadata.minecraft_versions,
                total_mods=len(mods_info),
                total_language_files=len(language_files),
                supported_languages=list(metadata.supported_languages),
                metadata=serializable_metadata,
            )

            return ProjectScanResult(
                success=True,
                project_info=project_info,
                mods_info=mods_info,
                language_files=language_files,
                scan_summary={
                    "project_type": project_type.value,
                    "loader_type": metadata.loader_type.value,
                    "mods_count": len(mods_info),
                    "language_files_count": len(language_files),
                    "supported_languages_count": len(metadata.supported_languages),
                },
            )

        except Exception as e:
            if isinstance(e, ProjectScanError | UnsupportedProjectTypeError):
                raise
            raise ProjectScanError(f"扫描项目时发生错误: {str(e)}") from e

    async def _detect_project_type(self, project_path: Path) -> MinecraftProjectType:
        """检测项目类型"""
        if project_path.is_file():
            # 单个文件，检查是否为 MOD
            if project_path.suffix in self.mod_extensions:
                return MinecraftProjectType.SINGLE_MOD
            return MinecraftProjectType.UNKNOWN

        if not project_path.is_dir():
            return MinecraftProjectType.UNKNOWN

        # 检查整合包指示器
        for indicator in self.modpack_indicators:
            indicator_path = project_path / indicator
            if indicator_path.exists():
                return MinecraftProjectType.MODPACK

        # 检查资源包指示器
        has_pack_mcmeta = (project_path / "pack.mcmeta").exists()
        has_assets = (project_path / "assets").exists()
        has_data = (project_path / "data").exists()

        if has_pack_mcmeta:
            if has_assets and not has_data:
                return MinecraftProjectType.RESOURCE_PACK
            elif has_data and not has_assets:
                return MinecraftProjectType.DATAPACK
            elif has_data and has_assets:
                # 同时包含 assets 和 data，优先判断为资源包
                return MinecraftProjectType.RESOURCE_PACK

        # 检查是否包含 MOD 文件
        mod_files = list(project_path.glob("*.jar")) + list(project_path.glob("*.zip"))
        if mod_files:
            return MinecraftProjectType.MODPACK

        return MinecraftProjectType.UNKNOWN

    async def _scan_modpack(
        self,
        modpack_path: Path,
        metadata: MinecraftProjectMetadata,
        progress_callback: Callable[[str, float], None] | None = None,
    ) -> tuple[list[ModInfo], list[LanguageFileInfo]]:
        """扫描整合包"""
        mods_info = []
        language_files = []

        # 读取整合包清单
        await self._read_modpack_manifest(modpack_path, metadata)

        # 扫描 mods 目录
        mods_dir = modpack_path / "mods"
        if mods_dir.exists():
            mod_files = []
            for ext in self.mod_extensions:
                mod_files.extend(mods_dir.glob(f"*{ext}"))

            if progress_callback:
                progress_callback(f"发现 {len(mod_files)} 个 MOD 文件", 30.0)

            # 并行扫描 MOD
            semaphore = asyncio.Semaphore(self.parallel_workers)

            async def scan_mod_with_semaphore(
                mod_file: Path, index: int
            ) -> tuple[ModInfo | None, list[LanguageFileInfo]]:
                async with semaphore:
                    if progress_callback:
                        progress = 30.0 + (index / len(mod_files)) * 60.0
                        progress_callback(f"扫描 MOD: {mod_file.name}", progress)
                    return await self._scan_single_mod(mod_file)

            tasks = [
                scan_mod_with_semaphore(mod_file, i)
                for i, mod_file in enumerate(mod_files)
            ]

            results = await asyncio.gather(*tasks, return_exceptions=True)

            for result in results:
                if isinstance(result, Exception):
                    continue  # 跳过失败的 MOD
                mod_info, mod_lang_files = result
                if mod_info:
                    mods_info.append(mod_info)
                    language_files.extend(mod_lang_files)

        # 扫描整合包级别的语言文件（如配置文件等）
        pack_lang_files = await self._scan_directory_language_files(
            modpack_path, exclude_dirs={"mods"}
        )
        language_files.extend(pack_lang_files)

        return mods_info, language_files

    async def _scan_single_mod(
        self,
        mod_path: Path,
        progress_callback: Callable[[str, float], None] | None = None,
    ) -> tuple[ModInfo | None, list[LanguageFileInfo]]:
        """扫描单个 MOD"""
        try:
            if mod_path.is_file() and mod_path.suffix in self.archive_extensions:
                return await self._scan_mod_archive(mod_path)
            elif mod_path.is_dir():
                return await self._scan_mod_directory(mod_path)
            else:
                return None, []
        except Exception:
            # 记录错误但不中断整体扫描
            return None, []

    async def _scan_mod_archive(
        self, archive_path: Path
    ) -> tuple[ModInfo | None, list[LanguageFileInfo]]:
        """扫描 MOD 压缩包"""
        language_files = []

        try:
            with zipfile.ZipFile(archive_path, "r") as zip_file:
                # 检测加载器类型
                loader_type = self._detect_loader_from_zip(zip_file)

                # 提取 MOD 元数据
                mod_metadata = await self._extract_mod_metadata(zip_file, loader_type)

                # 扫描语言文件
                for file_info in zip_file.filelist:
                    if self._is_language_file(file_info.filename):
                        lang_info = await self._create_language_file_info(
                            file_info.filename, archive_path, is_archived=True
                        )
                        if lang_info:
                            language_files.append(lang_info)

                # 创建 MOD 信息
                mod_info = ModInfo(
                    name=mod_metadata.get("name", archive_path.stem),
                    mod_id=mod_metadata.get("modid", archive_path.stem),
                    version=mod_metadata.get("version", "unknown"),
                    description=mod_metadata.get("description", ""),
                    authors=mod_metadata.get("authors", []),
                    file_path=str(archive_path),
                    file_size=archive_path.stat().st_size,
                    loader_type=loader_type.value,
                    minecraft_versions=mod_metadata.get("minecraft_versions", []),
                    dependencies=mod_metadata.get("dependencies", []),
                    language_files_count=len(language_files),
                    supported_languages=list(
                        {
                            lang.language_code
                            for lang in language_files
                            if lang.language_code
                        }
                    ),
                    metadata=mod_metadata,
                )

                return mod_info, language_files

        except Exception:
            return None, []

    async def _scan_mod_directory(
        self, mod_dir: Path
    ) -> tuple[ModInfo | None, list[LanguageFileInfo]]:
        """扫描 MOD 目录"""
        # 检测加载器类型
        loader_type = self._detect_loader_from_directory(mod_dir)

        # 提取 MOD 元数据
        mod_metadata = await self._extract_mod_metadata_from_directory(
            mod_dir, loader_type
        )

        # 扫描语言文件
        language_files = await self._scan_directory_language_files(mod_dir)

        # 创建 MOD 信息
        mod_info = ModInfo(
            name=mod_metadata.get("name", mod_dir.name),
            mod_id=mod_metadata.get("modid", mod_dir.name),
            version=mod_metadata.get("version", "unknown"),
            description=mod_metadata.get("description", ""),
            authors=mod_metadata.get("authors", []),
            file_path=str(mod_dir),
            file_size=await self._calculate_directory_size(mod_dir),
            loader_type=loader_type.value,
            minecraft_versions=mod_metadata.get("minecraft_versions", []),
            dependencies=mod_metadata.get("dependencies", []),
            language_files_count=len(language_files),
            supported_languages=list(
                {lang.language_code for lang in language_files if lang.language_code}
            ),
            metadata=mod_metadata,
        )

        return mod_info, language_files

    async def _scan_resource_pack(
        self,
        pack_path: Path,
        progress_callback: Callable[[str, float], None] | None = None,
    ) -> list[LanguageFileInfo]:
        """扫描资源包"""
        if progress_callback:
            progress_callback("扫描资源包语言文件...", 50.0)

        return await self._scan_directory_language_files(pack_path)

    async def _scan_datapack(
        self,
        pack_path: Path,
        progress_callback: Callable[[str, float], None] | None = None,
    ) -> list[LanguageFileInfo]:
        """扫描数据包"""
        if progress_callback:
            progress_callback("扫描数据包语言文件...", 50.0)

        return await self._scan_directory_language_files(pack_path)

    async def _scan_directory_language_files(
        self, directory: Path, exclude_dirs: set[str] | None = None
    ) -> list[LanguageFileInfo]:
        """扫描目录中的语言文件"""
        language_files = []
        exclude_dirs = exclude_dirs or set()

        for file_path in directory.rglob("*"):
            # 跳过排除的目录
            if any(part in exclude_dirs for part in file_path.parts):
                continue

            if file_path.is_file() and self._is_language_file(str(file_path)):
                lang_info = await self._create_language_file_info(
                    str(file_path.relative_to(directory)), file_path
                )
                if lang_info:
                    language_files.append(lang_info)

        return language_files

    def _is_language_file(self, file_path: str) -> bool:
        """检查是否为语言文件"""
        path_obj = Path(file_path)

        # 检查扩展名
        if path_obj.suffix not in self.language_extensions:
            return False

        # 检查路径模式
        path_str = str(path_obj).lower()
        return (
            "/lang/" in path_str
            or "\\lang\\" in path_str
            or path_obj.parent.name == "lang"
        )

    async def _create_language_file_info(
        self, relative_path: str, full_path: Path, is_archived: bool = False
    ) -> LanguageFileInfo | None:
        """创建语言文件信息"""
        try:
            # 提取语言代码
            path_obj = Path(relative_path)
            language_code = path_obj.stem

            # 基础信息
            lang_info = LanguageFileInfo(
                file_path=relative_path,
                full_path=str(full_path),
                language_code=language_code,
                file_format=path_obj.suffix[1:],  # 去掉点号
                file_size=0 if is_archived else full_path.stat().st_size,
                is_archived=is_archived,
                encoding="utf-8",  # 默认编码，稍后可检测
                keys_count=0,
                metadata={},
            )

            return lang_info

        except Exception:
            return None

    def _detect_loader_from_zip(self, zip_file: zipfile.ZipFile) -> MinecraftLoader:
        """从 ZIP 文件检测加载器类型"""
        file_list = zip_file.namelist()

        for loader, patterns in self.loader_detection.items():
            for pattern in patterns:
                if pattern in file_list:
                    return loader

        return MinecraftLoader.UNKNOWN

    def _detect_loader_from_directory(self, mod_dir: Path) -> MinecraftLoader:
        """从目录检测加载器类型"""
        for loader, patterns in self.loader_detection.items():
            for pattern in patterns:
                if (mod_dir / pattern).exists():
                    return loader

        return MinecraftLoader.UNKNOWN

    async def _extract_mod_metadata(
        self, zip_file: zipfile.ZipFile, loader_type: MinecraftLoader
    ) -> dict[str, Any]:
        """从 ZIP 文件提取 MOD 元数据"""
        metadata = {}

        try:
            if loader_type == MinecraftLoader.FABRIC:
                if "fabric.mod.json" in zip_file.namelist():
                    with zip_file.open("fabric.mod.json") as f:
                        fabric_json = json.loads(f.read().decode("utf-8"))
                        metadata.update(self._parse_fabric_metadata(fabric_json))

            elif loader_type == MinecraftLoader.FORGE:
                # 尝试读取 mods.toml
                for path in ["META-INF/mods.toml", "mcmod.info"]:
                    if path in zip_file.namelist():
                        with zip_file.open(path) as f:
                            content = f.read().decode("utf-8")
                            if path.endswith(".toml"):
                                metadata.update(
                                    self._parse_forge_toml_metadata(content)
                                )
                            else:
                                metadata.update(
                                    self._parse_forge_info_metadata(content)
                                )
                        break

            # 其他加载器的元数据解析...

        except Exception:
            pass  # 解析失败时使用默认值

        return metadata

    async def _extract_mod_metadata_from_directory(
        self, mod_dir: Path, loader_type: MinecraftLoader
    ) -> dict[str, Any]:
        """从目录提取 MOD 元数据"""
        metadata = {}

        try:
            if loader_type == MinecraftLoader.FABRIC:
                fabric_json_path = mod_dir / "fabric.mod.json"
                if fabric_json_path.exists():
                    with open(fabric_json_path, encoding="utf-8") as f:
                        fabric_json = json.load(f)
                        metadata.update(self._parse_fabric_metadata(fabric_json))

            # 其他加载器的处理...

        except Exception:
            pass

        return metadata

    def _parse_fabric_metadata(self, fabric_json: dict[str, Any]) -> dict[str, Any]:
        """解析 Fabric 元数据"""
        return {
            "name": fabric_json.get("name", ""),
            "modid": fabric_json.get("id", ""),
            "version": fabric_json.get("version", ""),
            "description": fabric_json.get("description", ""),
            "authors": fabric_json.get("authors", []),
            "minecraft_versions": [],  # 需要从 depends 中解析
            "dependencies": fabric_json.get("depends", {}),
        }

    def _parse_forge_toml_metadata(self, toml_content: str) -> dict[str, Any]:
        """解析 Forge TOML 元数据"""
        # 简化的 TOML 解析，实际项目中应使用 toml 库
        metadata = {}
        # 这里需要实现 TOML 解析逻辑
        return metadata

    def _parse_forge_info_metadata(self, info_content: str) -> dict[str, Any]:
        """解析 Forge mcmod.info 元数据"""
        try:
            info_json = json.loads(info_content)
            if isinstance(info_json, list) and info_json:
                mod_info = info_json[0]
                return {
                    "name": mod_info.get("name", ""),
                    "modid": mod_info.get("modid", ""),
                    "version": mod_info.get("version", ""),
                    "description": mod_info.get("description", ""),
                    "authors": mod_info.get("authorList", []),
                    "minecraft_versions": mod_info.get("mcversion", "").split(",")
                    if mod_info.get("mcversion")
                    else [],
                }
        except Exception:
            pass
        return {}

    async def _read_modpack_manifest(
        self, modpack_path: Path, metadata: MinecraftProjectMetadata
    ) -> None:
        """读取整合包清单文件"""
        manifest_files = [
            "manifest.json",
            "modpack.json",
            "instance.cfg",
            "mmc-pack.json",
        ]

        for manifest_name in manifest_files:
            manifest_path = modpack_path / manifest_name
            if manifest_path.exists():
                try:
                    with open(manifest_path, encoding="utf-8") as f:
                        if manifest_name.endswith(".json"):
                            manifest_data = json.load(f)
                            metadata.modpack_manifest = manifest_data

                            # 提取 Minecraft 版本信息
                            if "minecraft" in manifest_data:
                                mc_info = manifest_data["minecraft"]
                                if "version" in mc_info:
                                    metadata.minecraft_versions = [mc_info["version"]]

                            # 提取加载器信息
                            if "modLoaders" in manifest_data:
                                loaders = manifest_data["modLoaders"]
                                if loaders and "id" in loaders[0]:
                                    loader_id = loaders[0]["id"].lower()
                                    if "fabric" in loader_id:
                                        metadata.loader_type = MinecraftLoader.FABRIC
                                    elif "forge" in loader_id:
                                        metadata.loader_type = MinecraftLoader.FORGE
                                    elif "quilt" in loader_id:
                                        metadata.loader_type = MinecraftLoader.QUILT
                                    elif "neoforge" in loader_id:
                                        metadata.loader_type = MinecraftLoader.NEOFORGE
                        break
                except Exception:
                    continue

    async def _calculate_directory_size(self, directory: Path) -> int:
        """计算目录大小"""
        total_size = 0
        try:
            for file_path in directory.rglob("*"):
                if file_path.is_file():
                    total_size += file_path.stat().st_size
        except Exception:
            pass
        return total_size
