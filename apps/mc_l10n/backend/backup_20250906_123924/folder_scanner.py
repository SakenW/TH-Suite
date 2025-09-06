"""
文件夹扫描器

处理解包的模组文件夹、开发环境中的模组源码等
"""

import os
from datetime import datetime
from pathlib import Path
from typing import Any

from packages.core.framework.logging import get_logger

from domain.models.enums import ScanStatus
from domain.models.value_objects.file_path import FilePath
from domain.models.value_objects.language_code import LanguageCode
from domain.models.value_objects.mod_id import ModId
from .base_scanner import BaseScanner, DiscoveredFile, ScanFilter, ScanResult

logger = get_logger(__name__)


class FolderScanner(BaseScanner):
    """文件夹扫描器"""

    def __init__(self):
        super().__init__("文件夹扫描器")

        # 需要扫描的目录模式
        self._scan_patterns = {
            "assets": "assets",
            "src_main_resources": "src/main/resources",
            "src_main_resources_assets": "src/main/resources/assets",
            "resources": "resources",
            "lang": "lang",  # 直接的lang目录
        }

        # 需要忽略的目录和文件
        self._ignore_patterns = {
            ".git",
            ".svn",
            ".hg",  # 版本控制
            "__pycache__",
            ".pytest_cache",  # Python缓存
            "node_modules",  # Node.js
            ".gradle",
            "build",
            "target",  # 构建目录
            ".idea",
            ".vscode",  # IDE目录
            "Thumbs.db",
            ".DS_Store",  # 系统文件
        }

    async def can_handle(self, file_path: FilePath) -> bool:
        """检查是否能处理文件夹"""
        if not file_path.exists:
            return False

        if not file_path.is_directory:
            return False

        folder_path = file_path.resolved_path

        # 检查是否包含模组相关的目录结构
        for pattern_name, pattern_path in self._scan_patterns.items():
            if (folder_path / pattern_path).exists():
                self._logger.debug(f"找到模组目录结构: {pattern_path} in {folder_path}")
                return True

        # 检查是否直接包含语言文件
        if await self._has_language_files_directly(folder_path):
            return True

        # 检查是否包含模组元数据文件
        metadata_files = [
            "mcmod.info",
            "fabric.mod.json",
            "quilt.mod.json",
            "META-INF/mods.toml",
        ]

        for metadata_file in metadata_files:
            if (folder_path / metadata_file).exists():
                self._logger.debug(
                    f"找到模组元数据文件: {metadata_file} in {folder_path}"
                )
                return True

        return False

    async def scan(
        self, file_path: FilePath, scan_filter: ScanFilter | None = None
    ) -> ScanResult:
        """扫描文件夹"""
        start_time = datetime.utcnow()
        discovered_files = []
        errors = []
        metadata = {
            "scanner_type": "folder",
            "folder_size": 0,
            "total_files": 0,
            "total_directories": 0,
            "scan_depth": 0,
        }

        self._logger.info(f"开始扫描文件夹: {file_path}")

        try:
            folder_path = file_path.resolved_path

            # 获取文件夹基本信息
            folder_stat = folder_path.stat()
            metadata["last_modified"] = datetime.fromtimestamp(folder_stat.st_mtime)

            # 递归扫描文件夹
            scan_results = await self._recursive_scan(
                folder_path,
                folder_path,  # 根路径，用于计算相对路径
                0,  # 当前深度
                scan_filter,
            )

            discovered_files = scan_results["files"]
            errors.extend(scan_results["errors"])
            metadata.update(scan_results["metadata"])

            # 分析文件夹结构
            structure_info = await self._analyze_folder_structure(
                discovered_files, folder_path
            )
            metadata.update(structure_info)

            # 应用过滤器
            if scan_filter:
                discovered_files = await self._apply_filter(
                    discovered_files, scan_filter
                )

            # 创建扫描结果
            scan_status = ScanStatus.COMPLETED if not errors else ScanStatus.COMPLETED
            result = await self._create_scan_result(
                file_path, scan_status, discovered_files, metadata, errors, start_time
            )

            self._log_scan_summary(result)
            return result

        except Exception as e:
            error_msg = f"文件夹扫描失败: {str(e)}"
            errors.append(error_msg)
            self._logger.error(f"文件夹扫描异常: {file_path} - {error_msg}")

        # 扫描失败的情况
        return await self._create_scan_result(
            file_path, ScanStatus.FAILED, [], metadata, errors, start_time
        )

    async def _recursive_scan(
        self,
        current_path: Path,
        root_path: Path,
        depth: int,
        scan_filter: ScanFilter | None,
        max_depth: int = 20,
    ) -> dict[str, Any]:
        """递归扫描文件夹"""
        result = {
            "files": [],
            "errors": [],
            "metadata": {
                "total_files": 0,
                "total_directories": 0,
                "folder_size": 0,
                "scan_depth": depth,
            },
        }

        if depth > max_depth:
            result["errors"].append(f"扫描深度超过限制: {max_depth}")
            return result

        try:
            for item in current_path.iterdir():
                try:
                    # 检查是否应该忽略
                    if self._should_ignore(item):
                        continue

                    if item.is_file():
                        # 处理文件
                        discovered_file = await self._create_discovered_file_from_path(
                            item, root_path
                        )
                        if discovered_file:
                            result["files"].append(discovered_file)
                            result["metadata"]["total_files"] += 1
                            result["metadata"]["folder_size"] += (
                                discovered_file.file_size
                            )

                    elif item.is_dir():
                        # 处理子目录
                        result["metadata"]["total_directories"] += 1

                        # 递归扫描子目录
                        sub_result = await self._recursive_scan(
                            item, root_path, depth + 1, scan_filter, max_depth
                        )

                        # 合并结果
                        result["files"].extend(sub_result["files"])
                        result["errors"].extend(sub_result["errors"])
                        result["metadata"]["total_files"] += sub_result["metadata"][
                            "total_files"
                        ]
                        result["metadata"]["total_directories"] += sub_result[
                            "metadata"
                        ]["total_directories"]
                        result["metadata"]["folder_size"] += sub_result["metadata"][
                            "folder_size"
                        ]
                        result["metadata"]["scan_depth"] = max(
                            result["metadata"]["scan_depth"],
                            sub_result["metadata"]["scan_depth"],
                        )

                except PermissionError:
                    error_msg = f"权限不足，无法访问: {item}"
                    result["errors"].append(error_msg)
                    self._logger.warning(error_msg)
                    continue

                except Exception as e:
                    error_msg = f"处理路径失败 '{item}': {str(e)}"
                    result["errors"].append(error_msg)
                    self._logger.warning(error_msg)
                    continue

        except Exception as e:
            error_msg = f"扫描目录失败 '{current_path}': {str(e)}"
            result["errors"].append(error_msg)
            self._logger.error(error_msg)

        return result

    async def _create_discovered_file_from_path(
        self, file_path: Path, root_path: Path
    ) -> DiscoveredFile | None:
        """从文件路径创建发现文件信息"""
        try:
            # 计算相对路径
            relative_path = file_path.relative_to(root_path)
            relative_path_str = str(relative_path).replace("\\", "/")  # 统一使用正斜杠

            # 获取文件信息
            file_stat = file_path.stat()

            # 检测文件类型
            file_type = self._detect_file_type(relative_path_str)

            # 提取语言代码
            language_code = self._extract_language_code(relative_path_str)

            # 提取模组ID
            mod_id = self._extract_mod_id_from_path(relative_path_str)

            # 判断是否为语言文件
            is_language_file = self._is_language_file(relative_path_str)

            discovered_file = DiscoveredFile(
                relative_path=relative_path_str,
                full_path=str(file_path),
                file_type=file_type,
                file_size=file_stat.st_size,
                language_code=language_code,
                mod_id=mod_id,
                is_language_file=is_language_file,
                last_modified=datetime.fromtimestamp(file_stat.st_mtime),
            )

            return discovered_file

        except Exception as e:
            self._logger.warning(f"创建发现文件信息失败 '{file_path}': {str(e)}")
            return None

    def _should_ignore(self, path: Path) -> bool:
        """判断是否应该忽略此路径"""
        name = path.name

        # 检查忽略模式
        if name in self._ignore_patterns:
            return True

        # 检查隐藏文件/目录（以.开头，但不包括.lang等文件）
        if name.startswith(".") and not name.endswith(
            (".lang", ".json", ".properties")
        ):
            return True

        # 检查临时文件
        if name.endswith((".tmp", ".temp", ".bak", ".backup")):
            return True

        # 检查编译输出目录
        if path.is_dir() and name in ("bin", "out", "dist", "classes"):
            return True

        return False

    async def _has_language_files_directly(self, folder_path: Path) -> bool:
        """检查文件夹是否直接包含语言文件"""
        try:
            for item in folder_path.iterdir():
                if item.is_file() and self._is_language_file(item.name):
                    return True
                elif item.is_dir() and item.name == "lang":
                    # 检查lang子目录
                    lang_dir = item
                    try:
                        for lang_file in lang_dir.iterdir():
                            if lang_file.is_file() and self._is_language_file(
                                lang_file.name
                            ):
                                return True
                    except Exception:
                        pass
        except Exception:
            pass

        return False

    async def _analyze_folder_structure(
        self, discovered_files: list[DiscoveredFile], root_path: Path
    ) -> dict[str, Any]:
        """分析文件夹结构"""
        structure_info = {
            "has_assets": False,
            "has_src_structure": False,
            "has_mod_info": False,
            "mod_loader_type": "unknown",
            "assets_structure": {},
            "language_files_count": 0,
            "unique_mod_ids": set(),
            "supported_languages": set(),
            "directory_structure": set(),
        }

        try:
            # 分析目录结构
            for file_info in discovered_files:
                relative_path = file_info.relative_path
                path_parts = Path(relative_path).parts

                # 记录目录结构
                if len(path_parts) > 1:
                    structure_info["directory_structure"].add(path_parts[0])
                    if len(path_parts) > 2:
                        structure_info["directory_structure"].add(
                            f"{path_parts[0]}/{path_parts[1]}"
                        )

                # 检查特定结构
                if "assets" in path_parts:
                    structure_info["has_assets"] = True

                if "src" in path_parts and "main" in path_parts:
                    structure_info["has_src_structure"] = True

                # 分析语言文件
                if file_info.is_language_file:
                    structure_info["language_files_count"] += 1

                    if file_info.mod_id:
                        structure_info["unique_mod_ids"].add(file_info.mod_id.value)

                    if file_info.language_code:
                        structure_info["supported_languages"].add(
                            file_info.language_code.code
                        )

                # 检查模组元数据文件
                filename = Path(relative_path).name
                if filename in ["mcmod.info", "fabric.mod.json", "quilt.mod.json"]:
                    structure_info["has_mod_info"] = True
                    if "fabric" in filename:
                        structure_info["mod_loader_type"] = "fabric"
                    elif "quilt" in filename:
                        structure_info["mod_loader_type"] = "quilt"
                    else:
                        structure_info["mod_loader_type"] = "forge"
                elif relative_path.endswith("META-INF/mods.toml"):
                    structure_info["has_mod_info"] = True
                    structure_info["mod_loader_type"] = "forge"

            # 分析assets结构
            if structure_info["has_assets"]:
                structure_info["assets_structure"] = (
                    self._analyze_assets_structure_from_files(discovered_files)
                )

            # 转换set为list以便序列化
            structure_info["unique_mod_ids"] = list(structure_info["unique_mod_ids"])
            structure_info["supported_languages"] = list(
                structure_info["supported_languages"]
            )
            structure_info["directory_structure"] = list(
                structure_info["directory_structure"]
            )

        except Exception as e:
            self._logger.warning(f"分析文件夹结构时发生错误: {str(e)}")

        return structure_info

    def _analyze_assets_structure_from_files(
        self, discovered_files: list[DiscoveredFile]
    ) -> dict[str, dict[str, int]]:
        """从文件列表分析assets结构"""
        structure = {}

        for file_info in discovered_files:
            relative_path = file_info.relative_path
            if "assets" in relative_path:
                parts = Path(relative_path).parts
                try:
                    assets_index = parts.index("assets")
                    if assets_index + 2 < len(parts):  # assets/modid/type/...
                        mod_id = parts[assets_index + 1]
                        asset_type = parts[assets_index + 2]

                        if mod_id not in structure:
                            structure[mod_id] = {}

                        if asset_type not in structure[mod_id]:
                            structure[mod_id][asset_type] = 0

                        structure[mod_id][asset_type] += 1
                except ValueError:
                    continue

        return structure

    async def read_file_content(self, file_path: Path) -> bytes | None:
        """读取文件内容"""
        try:
            with open(file_path, "rb") as f:
                return f.read()
        except Exception as e:
            self._logger.error(f"读取文件内容失败 {file_path}: {str(e)}")
            return None

    async def find_language_files(
        self,
        folder_path: FilePath,
        language_code: LanguageCode | None = None,
        mod_id: ModId | None = None,
    ) -> list[Path]:
        """查找特定语言或模组的语言文件"""
        language_files = []

        try:
            # 递归查找语言文件
            for root, dirs, files in os.walk(folder_path.resolved_path):
                # 过滤需要忽略的目录
                dirs[:] = [d for d in dirs if not self._should_ignore(Path(root) / d)]

                for file in files:
                    file_path = Path(root) / file
                    relative_path = file_path.relative_to(folder_path.resolved_path)
                    relative_path_str = str(relative_path).replace("\\", "/")

                    if self._is_language_file(relative_path_str):
                        # 检查语言代码匹配
                        if language_code:
                            file_lang_code = self._extract_language_code(
                                relative_path_str
                            )
                            if not file_lang_code or file_lang_code != language_code:
                                continue

                        # 检查模组ID匹配
                        if mod_id:
                            file_mod_id = self._extract_mod_id_from_path(
                                relative_path_str
                            )
                            if not file_mod_id or file_mod_id != mod_id:
                                continue

                        language_files.append(file_path)

        except Exception as e:
            self._logger.error(f"查找语言文件失败: {str(e)}")

        return language_files

    async def get_folder_statistics(self, folder_path: FilePath) -> dict[str, Any]:
        """获取文件夹统计信息"""
        stats = {
            "total_files": 0,
            "total_directories": 0,
            "total_size": 0,
            "language_files": 0,
            "asset_files": 0,
            "largest_file": {"path": "", "size": 0},
            "file_types": {},
        }

        try:
            for root, dirs, files in os.walk(folder_path.resolved_path):
                stats["total_directories"] += len(dirs)

                for file in files:
                    file_path = Path(root) / file

                    try:
                        file_stat = file_path.stat()
                        file_size = file_stat.st_size

                        stats["total_files"] += 1
                        stats["total_size"] += file_size

                        # 记录最大文件
                        if file_size > stats["largest_file"]["size"]:
                            stats["largest_file"] = {
                                "path": str(
                                    file_path.relative_to(folder_path.resolved_path)
                                ),
                                "size": file_size,
                            }

                        # 统计文件类型
                        extension = file_path.suffix.lower()
                        stats["file_types"][extension] = (
                            stats["file_types"].get(extension, 0) + 1
                        )

                        # 特殊文件统计
                        relative_path = str(
                            file_path.relative_to(folder_path.resolved_path)
                        ).replace("\\", "/")
                        if self._is_language_file(relative_path):
                            stats["language_files"] += 1
                        elif "assets" in relative_path:
                            stats["asset_files"] += 1

                    except Exception as e:
                        self._logger.warning(f"获取文件统计失败 {file_path}: {str(e)}")
                        continue

        except Exception as e:
            self._logger.error(f"获取文件夹统计失败: {str(e)}")

        return stats
