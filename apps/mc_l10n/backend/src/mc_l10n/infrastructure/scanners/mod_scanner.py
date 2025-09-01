# apps/mc-l10n/backend/src/mc_l10n/infrastructure/scanners/mod_scanner.py
"""
MOD扫描器

专门处理单个MOD文件的详细扫描，包括深度语言文件分析和翻译片段提取
"""

from __future__ import annotations

import asyncio
import concurrent.futures
import tempfile
import zipfile
from pathlib import Path
from typing import Any

from packages.core import (
    BaseModScanner,
    FileType,
    ModParsingError,
    ModScanResult,
    get_config,
)
from packages.core import (
    ModScanner as CoreModScanner,
)

from src.mc_l10n.domain.scan_models import (
    FileFingerprint,
    LanguageFileInfo,
    ModInfo,
)
from src.mc_l10n.infrastructure.parsers import MinecraftLangParser, ParserFactory


class MinecraftModScanner:
    """Minecraft MOD文件扫描器"""

    def __init__(self, parser_factory: ParserFactory | None = None):
        self.config = get_config()
        self.parser_factory = parser_factory or ParserFactory()
        self.lang_parser = MinecraftLangParser()

        # 扫描配置
        self.max_file_size = self.config.scan.max_file_size
        self.supported_encodings = self.config.scan.supported_encodings

    async def scan_mod(self, mod_path: Path) -> ModInfo:
        """深度扫描MOD文件"""
        if not mod_path.exists():
            raise FileNotFoundError(f"MOD file not found: {mod_path}")

        if mod_path.stat().st_size > self.max_file_size:
            raise ModParsingError(
                str(mod_path), f"File too large: {mod_path.stat().st_size} bytes"
            )

        # 创建MOD信息对象
        mod_info = ModInfo(
            mod_id=mod_path.stem,
            name=mod_path.stem,
            file_path=mod_path,
            file_size=mod_path.stat().st_size,
        )

        try:
            # 创建文件指纹
            mod_info.fingerprint = FileFingerprint.create_from_file(mod_path)

            # 提取MOD内容
            await self._extract_mod_content(mod_path, mod_info)

            # 深度分析语言文件
            await self._analyze_language_files(mod_info)

        except Exception as e:
            raise ModParsingError(str(mod_path), f"Failed to scan MOD: {e}")

        return mod_info

    async def extract_mod_info(self, mod_path: Path) -> dict[str, Any]:
        """提取MOD基本信息"""
        try:
            with zipfile.ZipFile(mod_path, "r") as zip_file:
                file_list = zip_file.namelist()

                # 查找元数据文件
                metadata_info = {}
                for file_path in file_list:
                    if self._is_metadata_file(file_path):
                        try:
                            content = zip_file.read(file_path).decode("utf-8")
                            metadata_info.update(
                                self._parse_metadata_file(file_path, content)
                            )
                        except Exception:
                            continue

                return metadata_info

        except zipfile.BadZipFile:
            raise ModParsingError(str(mod_path), "Invalid ZIP file")

    async def scan_language_files(self, mod_path: Path) -> list[Path]:
        """扫描MOD中的语言文件"""
        language_files = []

        try:
            with zipfile.ZipFile(mod_path, "r") as zip_file:
                for file_path in zip_file.namelist():
                    if self._is_language_file(file_path):
                        language_files.append(Path(file_path))

        except zipfile.BadZipFile:
            raise ModParsingError(str(mod_path), "Invalid ZIP file")

        return language_files

    async def _extract_mod_content(self, mod_path: Path, mod_info: ModInfo) -> None:
        """提取MOD内容到临时目录进行分析"""
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)

            try:
                with zipfile.ZipFile(mod_path, "r") as zip_file:
                    # 提取所有文件
                    zip_file.extractall(temp_path)

                    # 分析文件结构
                    await self._analyze_mod_structure(temp_path, mod_info)

            except zipfile.BadZipFile:
                raise ModParsingError(str(mod_path), "Invalid ZIP file")

    async def _analyze_mod_structure(self, temp_path: Path, mod_info: ModInfo) -> None:
        """分析MOD结构"""
        all_files = list(temp_path.rglob("*"))

        for file_path in all_files:
            if not file_path.is_file():
                continue

            relative_path = file_path.relative_to(temp_path)

            # 处理元数据文件
            if self._is_metadata_file(str(relative_path)):
                await self._process_metadata_file(file_path, mod_info)

            # 处理语言文件
            elif self._is_language_file(str(relative_path)):
                await self._process_language_file(file_path, relative_path, mod_info)

    async def _process_metadata_file(self, file_path: Path, mod_info: ModInfo) -> None:
        """处理元数据文件"""
        try:
            content = file_path.read_text(encoding="utf-8")
            metadata = self._parse_metadata_file(file_path.name, content)

            # 更新MOD信息
            if "mod_id" in metadata:
                mod_info.mod_id = metadata["mod_id"]
            if "name" in metadata:
                mod_info.name = metadata["name"]
            if "version" in metadata:
                mod_info.version = metadata["version"]
            if "description" in metadata:
                mod_info.description = metadata["description"]
            if "authors" in metadata:
                mod_info.authors = metadata["authors"]
            if "minecraft_version" in metadata:
                mod_info.minecraft_version = metadata["minecraft_version"]
            if "loader_type" in metadata:
                from packages.core import LoaderType

                mod_info.loader_type = LoaderType(metadata["loader_type"])

        except Exception:
            # 元数据解析失败不应该阻止整个扫描
            pass

    async def _process_language_file(
        self, file_path: Path, relative_path: Path, mod_info: ModInfo
    ) -> None:
        """处理语言文件"""
        try:
            # 检测语言代码
            locale = self._detect_locale_from_path(relative_path)
            if not locale:
                locale = "unknown"

            # 检测文件类型
            file_type = self._detect_file_type(file_path)

            # 创建语言文件信息
            lang_file_info = LanguageFileInfo(
                path=file_path,
                relative_path=relative_path,
                file_type=file_type,
                locale=locale,
                fingerprint=FileFingerprint.create_from_file(file_path),
            )

            # 检测编码
            lang_file_info.encoding = await self._detect_encoding(file_path)

            # 添加到MOD信息
            mod_info.add_language_file(lang_file_info)

        except Exception:
            # 单个语言文件失败不应该阻止整个扫描
            pass

    async def _analyze_language_files(self, mod_info: ModInfo) -> None:
        """深度分析语言文件"""
        for lang_file in mod_info.language_files:
            try:
                await self._analyze_single_language_file(lang_file)
            except Exception as e:
                lang_file.parse_errors.append(f"Analysis failed: {e}")

    async def _analyze_single_language_file(self, lang_file: LanguageFileInfo) -> None:
        """分析单个语言文件"""
        try:
            # 使用解析器解析文件
            parser = self.parser_factory.get_parser(lang_file.path)
            if not parser:
                lang_file.parse_errors.append("No suitable parser found")
                return

            # 在线程池中执行解析
            loop = asyncio.get_event_loop()
            with concurrent.futures.ThreadPoolExecutor() as executor:
                parse_result = await loop.run_in_executor(
                    executor, lambda: parser.parse(lang_file.path)
                )

            # 更新语言文件信息
            lang_file.key_count = len(parse_result.segments)
            lang_file.parse_errors.extend(parse_result.errors)

            # 如果有警告，也记录
            if parse_result.warnings:
                lang_file.parse_errors.extend(
                    [f"Warning: {w}" for w in parse_result.warnings]
                )

        except Exception as e:
            lang_file.parse_errors.append(f"Parse failed: {e}")

    def _is_language_file(self, file_path: str) -> bool:
        """判断是否为语言文件"""
        import re

        patterns = [
            r"assets/[^/]+/lang/[^/]+\.(json|lang)$",
            r"data/[^/]+/lang/[^/]+\.(json|lang)$",
            r"lang/[^/]+\.(json|lang)$",
        ]

        return any(re.search(pattern, file_path, re.IGNORECASE) for pattern in patterns)

    def _is_metadata_file(self, file_path: str) -> bool:
        """判断是否为元数据文件"""
        metadata_files = [
            "mcmod.info",
            "fabric.mod.json",
            "quilt.mod.json",
            "meta-inf/mods.toml",
            "meta-inf/neoforge.mods.toml",
        ]

        return any(file_path.lower().endswith(mf) for mf in metadata_files)

    def _detect_locale_from_path(self, path: Path) -> str | None:
        """从路径检测语言代码"""
        import re

        # 从文件名检测
        stem = path.stem.lower()
        if re.match(r"^[a-z]{2}_[a-z]{2}$", stem):
            return stem

        # 从路径检测
        path_str = str(path).lower()
        match = re.search(r"/lang/([a-z]{2}_[a-z]{2})\.[^/]+$", path_str)
        if match:
            return match.group(1)

        return None

    def _detect_file_type(self, file_path: Path) -> FileType:
        """检测文件类型"""
        ext = file_path.suffix.lower()

        if ext == ".json":
            return FileType.JSON
        elif ext == ".lang":
            return FileType.LANG
        else:
            return FileType.JSON  # 默认

    async def _detect_encoding(self, file_path: Path) -> str:
        """检测文件编码"""
        for encoding in self.supported_encodings:
            try:
                file_path.read_text(encoding=encoding)
                return encoding
            except UnicodeDecodeError:
                continue

        return "utf-8"  # 默认编码

    def _parse_metadata_file(self, file_name: str, content: str) -> dict[str, Any]:
        """解析元数据文件"""
        import json

        result = {}

        try:
            if file_name.endswith("fabric.mod.json"):
                data = json.loads(content)
                result.update(
                    {
                        "mod_id": data.get("id"),
                        "name": data.get("name"),
                        "version": data.get("version"),
                        "description": data.get("description"),
                        "authors": data.get("authors", []),
                        "loader_type": "fabric",
                    }
                )

            elif file_name.endswith("quilt.mod.json"):
                data = json.loads(content)
                quilt_loader = data.get("quilt_loader", {})
                result.update(
                    {
                        "mod_id": quilt_loader.get("id"),
                        "name": quilt_loader.get("metadata", {}).get("name"),
                        "version": quilt_loader.get("version"),
                        "description": quilt_loader.get("metadata", {}).get(
                            "description"
                        ),
                        "authors": quilt_loader.get("metadata", {})
                        .get("contributors", {})
                        .get("author", []),
                        "loader_type": "quilt",
                    }
                )

            elif file_name.endswith("mcmod.info"):
                data = json.loads(content)
                if isinstance(data, list) and data:
                    mod_data = data[0]
                    result.update(
                        {
                            "mod_id": mod_data.get("modid"),
                            "name": mod_data.get("name"),
                            "version": mod_data.get("version"),
                            "description": mod_data.get("description"),
                            "authors": mod_data.get("authorList", []),
                            "minecraft_version": mod_data.get("mcversion"),
                            "loader_type": "forge",
                        }
                    )

            elif file_name.endswith("mods.toml"):
                # 简化的TOML解析
                result.update(self._parse_toml_metadata(content, "forge"))

            elif file_name.endswith("neoforge.mods.toml"):
                # 简化的TOML解析
                result.update(self._parse_toml_metadata(content, "neoforge"))

        except Exception:
            pass

        return result

    def _parse_toml_metadata(self, content: str, loader_type: str) -> dict[str, Any]:
        """简化的TOML元数据解析"""
        result = {"loader_type": loader_type}

        lines = content.splitlines()
        current_section = None

        for line in lines:
            line = line.strip()

            if line.startswith("[") and line.endswith("]"):
                current_section = line[1:-1]
                continue

            if "=" in line and not line.startswith("#"):
                key, value = line.split("=", 1)
                key = key.strip()
                value = value.strip().strip("\"'")

                if current_section == "mods" or current_section is None:
                    if key == "modId":
                        result["mod_id"] = value
                    elif key == "displayName":
                        result["name"] = value
                    elif key == "version":
                        result["version"] = value
                    elif key == "description":
                        result["description"] = value
                    elif key == "authors":
                        result["authors"] = [a.strip() for a in value.split(",")]

        return result


# 实现核心接口
class ModScannerImpl(CoreModScanner):
    """MOD扫描器实现类，实现核心接口"""

    def __init__(self):
        self.scanner = MinecraftModScanner()


class ModScanner(BaseModScanner):
    def __init__(self):
        self.scanner = MinecraftModScanner()

    async def scan_mod(self, mod_path: Path) -> ModScanResult:
        """扫描MOD文件"""

        try:
            mod_info = await self.scanner.scan_mod(mod_path)

            return ModScanResult(
                mod_id=mod_info.mod_id,
                name=mod_info.name,
                version=mod_info.version,
                description=mod_info.description,
                authors=mod_info.authors,
                file_path=mod_info.file_path,
                file_size=mod_info.file_size,
                file_hash=mod_info.fingerprint.hash_sha256
                if mod_info.fingerprint
                else "",
                language_files=[lf.path for lf in mod_info.language_files],
                supported_locales=list(mod_info.supported_locales),
                total_segments=mod_info.estimated_segments,
            )

        except Exception as e:
            return ModScanResult(
                mod_id=mod_path.stem,
                name=mod_path.stem,
                file_path=mod_path,
                file_size=mod_path.stat().st_size if mod_path.exists() else 0,
                scan_issues=[f"Scan failed: {e}"],
            )

    async def extract_mod_info(self, mod_path: Path) -> dict[str, Any]:
        """提取MOD信息"""
        return await self.scanner.extract_mod_info(mod_path)

    async def scan_language_files(self, mod_path: Path) -> list[Path]:
        """扫描语言文件"""
        return await self.scanner.scan_language_files(mod_path)
