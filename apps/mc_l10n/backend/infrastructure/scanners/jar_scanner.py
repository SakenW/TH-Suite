"""
JAR文件扫描器

专门处理Minecraft模组JAR文件的扫描，提取其中的语言文件和资源
"""

import zipfile
from datetime import datetime
from typing import Any

from packages.core.framework.logging import get_logger

from domain.models.enums import ScanStatus
from domain.models.value_objects.file_path import FilePath
from domain.models.value_objects.language_code import LanguageCode
from domain.models.value_objects.mod_id import ModId
from .base_scanner import BaseScanner, DiscoveredFile, ScanFilter, ScanResult

logger = get_logger(__name__)


class JarScanner(BaseScanner):
    """JAR文件扫描器"""

    def __init__(self):
        super().__init__("JAR扫描器")

        # JAR文件中需要关注的路径模式
        self._important_paths = {
            "assets": "assets/",
            "meta_inf": "META-INF/",
            "mod_info_forge_new": "META-INF/mods.toml",
            "mod_info_forge_old": "mcmod.info",
            "mod_info_fabric": "fabric.mod.json",
            "mod_info_quilt": "quilt.mod.json",
        }

    async def can_handle(self, file_path: FilePath) -> bool:
        """检查是否能处理JAR文件"""
        if not file_path.exists:
            return False

        if not file_path.is_file:
            return False

        # 检查文件扩展名
        if file_path.extension.lower() != ".jar":
            return False

        # 尝试打开JAR文件验证格式
        try:
            with zipfile.ZipFile(file_path.resolved_path, "r") as jar:
                # 简单验证：检查是否能读取文件列表
                jar.namelist()
                return True
        except (zipfile.BadZipFile, Exception):
            return False

    async def scan(
        self, file_path: FilePath, scan_filter: ScanFilter | None = None
    ) -> ScanResult:
        """扫描JAR文件"""
        start_time = datetime.utcnow()
        discovered_files = []
        errors = []
        metadata = {
            "scanner_type": "jar",
            "file_size": 0,
            "total_entries": 0,
            "compressed_size": 0,
            "uncompressed_size": 0,
        }

        self._logger.info(f"开始扫描JAR文件: {file_path}")

        try:
            # 获取文件基本信息
            file_stat = file_path.resolved_path.stat()
            metadata["file_size"] = file_stat.st_size
            metadata["last_modified"] = datetime.fromtimestamp(file_stat.st_mtime)

            # 打开JAR文件进行扫描
            with zipfile.ZipFile(file_path.resolved_path, "r") as jar:
                file_list = jar.namelist()
                metadata["total_entries"] = len(file_list)

                # 收集压缩信息统计
                compressed_total = 0
                uncompressed_total = 0

                for entry_name in file_list:
                    try:
                        # 获取条目信息
                        entry_info = jar.getinfo(entry_name)

                        # 跳过目录条目
                        if entry_name.endswith("/"):
                            continue

                        # 统计压缩信息
                        compressed_total += entry_info.compress_size
                        uncompressed_total += entry_info.file_size

                        # 创建发现的文件信息
                        discovered_file = await self._create_discovered_file(
                            entry_name, entry_info, file_path
                        )

                        if discovered_file:
                            discovered_files.append(discovered_file)

                    except Exception as e:
                        error_msg = f"处理JAR条目失败 '{entry_name}': {str(e)}"
                        errors.append(error_msg)
                        self._logger.warning(error_msg)
                        continue

                metadata["compressed_size"] = compressed_total
                metadata["uncompressed_size"] = uncompressed_total

                # 分析JAR结构
                structure_info = await self._analyze_jar_structure(jar, file_list)
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

        except zipfile.BadZipFile:
            error_msg = "文件不是有效的ZIP/JAR格式"
            errors.append(error_msg)
            self._logger.error(f"JAR文件格式错误: {file_path} - {error_msg}")

        except Exception as e:
            error_msg = f"JAR扫描失败: {str(e)}"
            errors.append(error_msg)
            self._logger.error(f"JAR扫描异常: {file_path} - {error_msg}")

        # 扫描失败的情况
        return await self._create_scan_result(
            file_path, ScanStatus.FAILED, [], metadata, errors, start_time
        )

    async def _create_discovered_file(
        self, entry_name: str, entry_info: zipfile.ZipInfo, jar_path: FilePath
    ) -> DiscoveredFile | None:
        """从JAR条目创建发现文件信息"""
        try:
            # 检测文件类型
            file_type = self._detect_file_type(entry_name)

            # 提取语言代码
            language_code = self._extract_language_code(entry_name)

            # 提取模组ID
            mod_id = self._extract_mod_id_from_path(entry_name)

            # 判断是否为语言文件
            is_language_file = self._is_language_file(entry_name)

            # 构建完整路径（JAR内路径）
            full_path = f"{jar_path}!/{entry_name}"

            # 获取修改时间
            last_modified = None
            if entry_info.date_time:
                # ZipInfo.date_time是6元组 (年, 月, 日, 时, 分, 秒)
                last_modified = datetime(*entry_info.date_time)

            discovered_file = DiscoveredFile(
                relative_path=entry_name,
                full_path=full_path,
                file_type=file_type,
                file_size=entry_info.file_size,
                language_code=language_code,
                mod_id=mod_id,
                is_language_file=is_language_file,
                last_modified=last_modified,
            )

            return discovered_file

        except Exception as e:
            self._logger.warning(f"创建发现文件信息失败 '{entry_name}': {str(e)}")
            return None

    async def _analyze_jar_structure(
        self, jar: zipfile.ZipFile, file_list: list[str]
    ) -> dict[str, Any]:
        """分析JAR文件结构"""
        structure_info = {
            "has_assets": False,
            "has_mod_info": False,
            "mod_loader_type": "unknown",
            "mod_info_file": None,
            "assets_structure": {},
            "language_files_count": 0,
            "unique_mod_ids": set(),
            "supported_languages": set(),
        }

        try:
            # 检查是否包含assets
            assets_files = [f for f in file_list if f.startswith("assets/")]
            if assets_files:
                structure_info["has_assets"] = True
                structure_info["assets_structure"] = self._analyze_assets_structure(
                    assets_files
                )

            # 检查模组信息文件并确定模组加载器类型
            for path_key, path_pattern in self._important_paths.items():
                if path_key.startswith("mod_info_") and path_pattern in file_list:
                    structure_info["has_mod_info"] = True
                    structure_info["mod_info_file"] = path_pattern

                    # 确定模组加载器类型
                    if "forge" in path_key:
                        structure_info["mod_loader_type"] = "forge"
                    elif "fabric" in path_key:
                        structure_info["mod_loader_type"] = "fabric"
                    elif "quilt" in path_key:
                        structure_info["mod_loader_type"] = "quilt"
                    break

            # 分析语言文件
            language_files = [f for f in file_list if self._is_language_file(f)]
            structure_info["language_files_count"] = len(language_files)

            # 收集模组ID和支持的语言
            for lang_file in language_files:
                mod_id = self._extract_mod_id_from_path(lang_file)
                if mod_id:
                    structure_info["unique_mod_ids"].add(mod_id.value)

                lang_code = self._extract_language_code(lang_file)
                if lang_code:
                    structure_info["supported_languages"].add(lang_code.code)

            # 转换set为list以便序列化
            structure_info["unique_mod_ids"] = list(structure_info["unique_mod_ids"])
            structure_info["supported_languages"] = list(
                structure_info["supported_languages"]
            )

        except Exception as e:
            self._logger.warning(f"分析JAR结构时发生错误: {str(e)}")

        return structure_info

    def _analyze_assets_structure(
        self, assets_files: list[str]
    ) -> dict[str, dict[str, int]]:
        """分析assets目录结构"""
        structure = {}

        for file_path in assets_files:
            if file_path.endswith("/"):  # 跳过目录条目
                continue

            parts = file_path.split("/")
            if len(parts) >= 3:  # assets/modid/type/...
                mod_id = parts[1]
                asset_type = parts[2]

                if mod_id not in structure:
                    structure[mod_id] = {}

                if asset_type not in structure[mod_id]:
                    structure[mod_id][asset_type] = 0

                structure[mod_id][asset_type] += 1

        return structure

    async def extract_file_content(
        self, jar_path: FilePath, internal_path: str
    ) -> bytes | None:
        """从JAR文件中提取指定文件的内容"""
        try:
            with zipfile.ZipFile(jar_path.resolved_path, "r") as jar:
                if internal_path in jar.namelist():
                    return jar.read(internal_path)
                else:
                    self._logger.warning(f"JAR文件中不存在路径: {internal_path}")
                    return None
        except Exception as e:
            self._logger.error(f"从JAR提取文件内容失败 {internal_path}: {str(e)}")
            return None

    async def extract_language_file_content(
        self,
        jar_path: FilePath,
        language_code: LanguageCode,
        mod_id: ModId | None = None,
    ) -> bytes | None:
        """提取特定语言的语言文件内容"""
        # 构建可能的语言文件路径
        possible_paths = []

        if mod_id:
            # 有模组ID的情况
            possible_paths.extend(
                [
                    f"assets/{mod_id.value}/lang/{language_code.code}.json",
                    f"assets/{mod_id.value}/lang/{language_code.code}.lang",
                    f"assets/{mod_id.value}/lang/{language_code.code}.properties",
                ]
            )
        else:
            # 没有模组ID，需要搜索所有可能的路径
            try:
                with zipfile.ZipFile(jar_path.resolved_path, "r") as jar:
                    lang_files = [
                        f
                        for f in jar.namelist()
                        if f"/lang/{language_code.code}." in f
                        and self._is_language_file(f)
                    ]
                    possible_paths.extend(lang_files)
            except Exception as e:
                self._logger.error(f"搜索语言文件路径失败: {str(e)}")
                return None

        # 尝试提取第一个找到的文件
        for path in possible_paths:
            content = await self.extract_file_content(jar_path, path)
            if content is not None:
                return content

        self._logger.warning(
            f"未在JAR文件中找到语言文件: {language_code.code} "
            f"(mod_id: {mod_id.value if mod_id else 'unknown'})"
        )
        return None

    async def list_available_languages(self, jar_path: FilePath) -> list[LanguageCode]:
        """列出JAR文件中可用的语言"""
        languages = set()

        try:
            with zipfile.ZipFile(jar_path.resolved_path, "r") as jar:
                for file_path in jar.namelist():
                    if self._is_language_file(file_path):
                        lang_code = self._extract_language_code(file_path)
                        if lang_code:
                            languages.add(lang_code)
        except Exception as e:
            self._logger.error(f"列出可用语言失败: {str(e)}")

        return list(languages)

    async def get_jar_metadata_info(self, jar_path: FilePath) -> dict[str, Any]:
        """获取JAR文件的元数据信息"""
        metadata = {}

        try:
            with zipfile.ZipFile(jar_path.resolved_path, "r") as jar:
                # 尝试读取各种模组信息文件
                for info_file in [
                    "META-INF/mods.toml",
                    "mcmod.info",
                    "fabric.mod.json",
                ]:
                    if info_file in jar.namelist():
                        try:
                            content = jar.read(info_file).decode("utf-8")
                            metadata[info_file] = content
                        except Exception as e:
                            self._logger.warning(
                                f"读取元数据文件失败 {info_file}: {str(e)}"
                            )
        except Exception as e:
            self._logger.error(f"获取JAR元数据信息失败: {str(e)}")

        return metadata
