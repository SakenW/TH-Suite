# apps/mc-l10n/backend/src/mc_l10n/infrastructure/parsers/enhanced_parser.py
"""
增强的文件解析器

基于packages/parsers的基础解析器，增加MC L10n特定的功能和优化
"""

from __future__ import annotations

import json
import re
import zipfile
from pathlib import Path
from typing import Any

from packages.core import (
    FileType,
    UnsupportedFileFormatError,
)
from packages.parsers import BaseParser, ParseResult


class MinecraftLangParser(BaseParser):
    """Minecraft 语言文件解析器"""

    def __init__(self, encoding: str = "utf-8"):
        super().__init__(encoding)
        self.supported_extensions = [".json", ".lang"]

    def can_parse(self, file_path: Path) -> bool:
        """判断是否能解析该文件"""
        if not file_path.exists():
            return False

        # 检查扩展名
        if file_path.suffix.lower() not in self.supported_extensions:
            return False

        # 检查路径模式
        path_str = str(file_path).lower()
        return any(
            pattern in path_str for pattern in ["/lang/", "/localization/", "/i18n/"]
        )

    def parse(self, file_path: Path, **kwargs) -> ParseResult:
        """解析语言文件"""
        try:
            content = self.read_file_content(file_path)
            metadata = self.get_file_metadata(file_path)

            if file_path.suffix.lower() == ".json":
                return self._parse_json(content, file_path, metadata)
            elif file_path.suffix.lower() == ".lang":
                return self._parse_lang(content, file_path, metadata)
            else:
                raise UnsupportedFileFormatError(str(file_path), file_path.suffix)

        except Exception as e:
            return ParseResult(
                segments=[],
                metadata=self.get_file_metadata(file_path),
                warnings=[],
                errors=[f"Failed to parse file: {e}"],
            )

    def _parse_json(self, content: str, file_path: Path, metadata: dict) -> ParseResult:
        """解析JSON格式语言文件"""
        segments = []
        warnings = []
        errors = []

        try:
            data = json.loads(content)
            if not isinstance(data, dict):
                errors.append("JSON root must be an object")
                return ParseResult(segments, metadata, warnings, errors)

            # 扁平化嵌套结构
            flat_data = self._flatten_dict(data)

            for key, value in flat_data.items():
                if not isinstance(value, str):
                    warnings.append(f"Non-string value for key '{key}': {type(value)}")
                    continue

                segment = self.create_segment(
                    uida=self._generate_uida(str(file_path), key),
                    locale=self._detect_locale(file_path),
                    key=key,
                    text=value,
                    metadata={"file_path": str(file_path), "file_type": "json"},
                )
                segments.append(segment)

        except json.JSONDecodeError as e:
            errors.append(f"Invalid JSON syntax: {e}")

        metadata.update(
            {
                "format": "json",
                "key_count": len(segments),
                "encoding_detected": self.encoding,
            }
        )

        return ParseResult(segments, metadata, warnings, errors)

    def _parse_lang(self, content: str, file_path: Path, metadata: dict) -> ParseResult:
        """解析.lang格式语言文件"""
        segments = []
        warnings = []
        errors = []

        lines = content.splitlines()

        for line_num, line in enumerate(lines, 1):
            line = line.strip()

            # 跳过空行和注释
            if not line or line.startswith("#"):
                continue

            # 解析键值对
            if "=" not in line:
                warnings.append(f"Line {line_num}: Missing '=' separator")
                continue

            key, value = line.split("=", 1)
            key = key.strip()
            value = value.strip()

            if not key:
                warnings.append(f"Line {line_num}: Empty key")
                continue

            segment = self.create_segment(
                uida=self._generate_uida(str(file_path), key),
                locale=self._detect_locale(file_path),
                key=key,
                text=value,
                metadata={
                    "file_path": str(file_path),
                    "file_type": "lang",
                    "line_number": line_num,
                },
            )
            segments.append(segment)

        metadata.update(
            {
                "format": "lang",
                "key_count": len(segments),
                "line_count": len(lines),
                "encoding_detected": self.encoding,
            }
        )

        return ParseResult(segments, metadata, warnings, errors)

    def _flatten_dict(self, d: dict, prefix: str = "") -> dict[str, str]:
        """扁平化嵌套字典"""
        result = {}
        for key, value in d.items():
            new_key = f"{prefix}.{key}" if prefix else key

            if isinstance(value, dict):
                result.update(self._flatten_dict(value, new_key))
            else:
                result[new_key] = str(value)

        return result

    def _detect_locale(self, file_path: Path) -> str:
        """从文件路径检测语言代码"""
        # 从文件名检测
        stem = file_path.stem.lower()
        if re.match(r"^[a-z]{2}_[a-z]{2}$", stem):
            return stem

        # 从路径检测
        path_str = str(file_path).lower()
        match = re.search(r"/lang/([a-z]{2}_[a-z]{2})\.[^/]+$", path_str)
        if match:
            return match.group(1)

        return "unknown"

    def _generate_uida(self, file_path: str, key: str) -> str:
        """生成唯一标识符"""
        import hashlib

        content = f"{file_path}:{key}"
        return hashlib.sha256(content.encode()).hexdigest()[:16]

    def write(self, segments: list, file_path: Path, **kwargs) -> None:
        """写入语言文件"""
        file_format = kwargs.get("format", "json")

        if file_format == "json":
            self._write_json(segments, file_path)
        elif file_format == "lang":
            self._write_lang(segments, file_path)
        else:
            raise UnsupportedFileFormatError(str(file_path), file_format)

    def _write_json(self, segments: list, file_path: Path) -> None:
        """写入JSON格式"""
        data = {}
        for segment in segments:
            self._set_nested_value(data, segment.key, segment.text)

        content = json.dumps(data, ensure_ascii=False, indent=2)
        self.write_file_content(file_path, content)

    def _write_lang(self, segments: list, file_path: Path) -> None:
        """写入.lang格式"""
        lines = []
        for segment in segments:
            lines.append(f"{segment.key}={segment.text}")

        content = "\n".join(lines)
        self.write_file_content(file_path, content)

    def _set_nested_value(self, d: dict, key: str, value: str) -> None:
        """在嵌套字典中设置值"""
        parts = key.split(".")
        current = d

        for part in parts[:-1]:
            if part not in current:
                current[part] = {}
            current = current[part]

        current[parts[-1]] = value


class ModFileAnalyzer:
    """MOD文件分析器"""

    def __init__(self):
        self.lang_parser = MinecraftLangParser()

    def analyze_mod_archive(self, mod_path: Path) -> dict[str, Any]:
        """分析MOD压缩文件"""
        if not mod_path.exists():
            raise FileNotFoundError(f"MOD file not found: {mod_path}")

        result = {
            "mod_path": str(mod_path),
            "file_size": mod_path.stat().st_size,
            "language_files": [],
            "metadata_files": [],
            "loader_type": None,
            "mod_info": {},
            "errors": [],
        }

        try:
            with zipfile.ZipFile(mod_path, "r") as zip_file:
                file_list = zip_file.namelist()

                # 分析文件列表
                for file_path in file_list:
                    self._analyze_file_entry(file_path, result)

                # 提取MOD信息
                self._extract_mod_metadata(zip_file, result)

        except zipfile.BadZipFile:
            result["errors"].append(f"Invalid ZIP file: {mod_path}")
        except Exception as e:
            result["errors"].append(f"Error analyzing MOD: {e}")

        return result

    def _analyze_file_entry(self, file_path: str, result: dict) -> None:
        """分析ZIP中的文件条目"""
        file_path.lower()

        # 检测语言文件
        if self._is_language_file(file_path):
            lang_info = {
                "path": file_path,
                "locale": self._extract_locale_from_path(file_path),
                "file_type": self._detect_file_type(file_path),
                "namespace": self._extract_namespace(file_path),
            }
            result["language_files"].append(lang_info)

        # 检测元数据文件
        elif self._is_metadata_file(file_path):
            result["metadata_files"].append(file_path)

        # 检测加载器类型
        loader_type = self._detect_loader_from_file(file_path)
        if loader_type and not result["loader_type"]:
            result["loader_type"] = loader_type

    def _is_language_file(self, file_path: str) -> bool:
        """判断是否为语言文件"""
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

    def _detect_loader_from_file(self, file_path: str) -> str | None:
        """从文件路径检测加载器类型"""
        lower_path = file_path.lower()

        if "fabric.mod.json" in lower_path:
            return "fabric"
        elif "quilt.mod.json" in lower_path:
            return "quilt"
        elif "mods.toml" in lower_path:
            return "forge"
        elif "neoforge.mods.toml" in lower_path:
            return "neoforge"
        elif "mcmod.info" in lower_path:
            return "forge"

        return None

    def _extract_locale_from_path(self, file_path: str) -> str | None:
        """从路径提取语言代码"""
        # 匹配语言文件名
        match = re.search(r"/([a-z]{2}_[a-z]{2})\.[^/]+$", file_path.lower())
        if match:
            return match.group(1)

        return None

    def _detect_file_type(self, file_path: str) -> FileType:
        """检测文件类型"""
        ext = Path(file_path).suffix.lower()

        if ext == ".json":
            return FileType.JSON
        elif ext == ".lang":
            return FileType.LANG
        else:
            return FileType.JSON  # 默认

    def _extract_namespace(self, file_path: str) -> str | None:
        """提取命名空间"""
        # assets/{namespace}/lang/{locale}.json
        match = re.search(r"assets/([^/]+)/lang/", file_path)
        if match:
            return match.group(1)

        # data/{namespace}/lang/{locale}.json
        match = re.search(r"data/([^/]+)/lang/", file_path)
        if match:
            return match.group(1)

        return None

    def _extract_mod_metadata(self, zip_file: zipfile.ZipFile, result: dict) -> None:
        """提取MOD元数据"""
        for metadata_file in result["metadata_files"]:
            try:
                content = zip_file.read(metadata_file).decode("utf-8")

                if metadata_file.endswith("fabric.mod.json"):
                    self._parse_fabric_metadata(content, result)
                elif metadata_file.endswith("mods.toml"):
                    self._parse_forge_metadata(content, result)
                elif metadata_file.endswith("mcmod.info"):
                    self._parse_legacy_forge_metadata(content, result)

            except Exception as e:
                result["errors"].append(f"Error reading {metadata_file}: {e}")

    def _parse_fabric_metadata(self, content: str, result: dict) -> None:
        """解析Fabric MOD信息"""
        try:
            data = json.loads(content)
            result["mod_info"] = {
                "mod_id": data.get("id"),
                "name": data.get("name"),
                "version": data.get("version"),
                "description": data.get("description"),
                "authors": data.get("authors", []),
                "dependencies": list(data.get("depends", {}).keys()),
            }
        except json.JSONDecodeError as e:
            result["errors"].append(f"Invalid fabric.mod.json: {e}")

    def _parse_forge_metadata(self, content: str, result: dict) -> None:
        """解析Forge TOML元数据"""
        # 简化的TOML解析，实际应该使用toml库
        lines = content.splitlines()
        mod_info = {}

        for line in lines:
            line = line.strip()
            if "=" in line and not line.startswith("#"):
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

        result["mod_info"] = mod_info

    def _parse_legacy_forge_metadata(self, content: str, result: dict) -> None:
        """解析旧版Forge mcmod.info"""
        try:
            data = json.loads(content)
            if isinstance(data, list) and data:
                mod_data = data[0]
                result["mod_info"] = {
                    "mod_id": mod_data.get("modid"),
                    "name": mod_data.get("name"),
                    "version": mod_data.get("version"),
                    "description": mod_data.get("description"),
                    "authors": mod_data.get("authorList", []),
                }
        except json.JSONDecodeError as e:
            result["errors"].append(f"Invalid mcmod.info: {e}")


class ParserFactory:
    """解析器工厂"""

    def __init__(self):
        self._parsers = [
            MinecraftLangParser(),
        ]

    def get_parser(self, file_path: Path) -> BaseParser | None:
        """获取适合的解析器"""
        for parser in self._parsers:
            if parser.can_parse(file_path):
                return parser
        return None

    def register_parser(self, parser: BaseParser) -> None:
        """注册新的解析器"""
        self._parsers.append(parser)

    def get_supported_extensions(self) -> set[str]:
        """获取所有支持的文件扩展名"""
        extensions = set()
        for parser in self._parsers:
            extensions.update(parser.supported_extensions)
        return extensions
