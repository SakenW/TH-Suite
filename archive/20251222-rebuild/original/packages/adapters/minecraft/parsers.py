# packages/adapters/minecraft/parsers.py
"""
Minecraft 文件解析器实现

实现 ParserFactory 和各种文件解析器，支持 Minecraft 的多种语言文件格式。
包括 JSON、.lang、Properties 等格式的解析和编码检测。
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from typing import Any

import chardet

from ...core.errors import FileParsingError, UnsupportedFileFormatError
from ...core.interfaces import FileParser
from ...core.types import LanguageEntry, ParseResult


class MinecraftFileFormat(Enum):
    """Minecraft 文件格式枚举"""

    JSON = "json"
    LANG = "lang"
    PROPERTIES = "properties"
    TOML = "toml"
    UNKNOWN = "unknown"


@dataclass
class ParseContext:
    """解析上下文"""

    file_path: Path
    file_format: MinecraftFileFormat
    encoding: str = "utf-8"
    preserve_order: bool = False
    allow_comments: bool = True


class MinecraftJsonParser:
    """Minecraft JSON 语言文件解析器"""

    def __init__(self):
        self.format = MinecraftFileFormat.JSON

    def can_parse(self, file_path: Path) -> bool:
        """检查是否能解析该文件"""
        return file_path.suffix.lower() == ".json"

    async def parse(self, file_path: Path, encoding: str = "utf-8") -> ParseResult:
        """解析 JSON 语言文件

        Args:
            file_path: 文件路径
            encoding: 文件编码

        Returns:
            解析结果

        Raises:
            FileParsingError: 解析失败
        """
        try:
            with open(file_path, encoding=encoding) as f:
                content = f.read()

            # 解析 JSON
            data = json.loads(content)

            if not isinstance(data, dict):
                raise FileParsingError(
                    f"JSON 文件格式不正确，期望对象类型: {file_path}"
                )

            # 转换为语言条目
            entries = self._convert_to_entries(data)

            return ParseResult(
                success=True,
                entries=entries,
                file_format=self.format.value,
                encoding=encoding,
                total_keys=len(entries),
                metadata={
                    "json_structure": "flat"
                    if self._is_flat_structure(data)
                    else "nested",
                    "has_empty_values": any(not entry.value for entry in entries),
                    "max_nesting_level": self._get_max_nesting_level(data),
                },
            )

        except json.JSONDecodeError as e:
            raise FileParsingError(f"JSON 解析错误: {e}") from e
        except Exception as e:
            raise FileParsingError(f"解析文件时发生错误: {e}") from e

    async def serialize(
        self,
        entries: list[LanguageEntry],
        file_path: Path,
        encoding: str = "utf-8",
        preserve_structure: bool = True,
    ) -> None:
        """序列化语言条目为 JSON 文件

        Args:
            entries: 语言条目列表
            file_path: 输出文件路径
            encoding: 文件编码
            preserve_structure: 是否保持嵌套结构
        """
        try:
            # 转换条目为字典
            if preserve_structure:
                data = self._convert_to_nested_dict(entries)
            else:
                data = {entry.key: entry.value for entry in entries}

            # 写入文件
            file_path.parent.mkdir(parents=True, exist_ok=True)
            with open(file_path, "w", encoding=encoding) as f:
                json.dump(data, f, ensure_ascii=False, indent=2)

        except Exception as e:
            raise FileParsingError(f"序列化 JSON 文件时发生错误: {e}") from e

    def _convert_to_entries(
        self, data: dict[str, Any], prefix: str = ""
    ) -> list[LanguageEntry]:
        """将 JSON 数据转换为语言条目"""
        entries = []

        for key, value in data.items():
            full_key = f"{prefix}.{key}" if prefix else key

            if isinstance(value, dict):
                # 递归处理嵌套对象
                entries.extend(self._convert_to_entries(value, full_key))
            elif isinstance(value, str):
                entries.append(
                    LanguageEntry(
                        key=full_key,
                        value=value,
                        comment="",
                        metadata={"source_type": "json"},
                    )
                )
            else:
                # 非字符串值转换为字符串
                entries.append(
                    LanguageEntry(
                        key=full_key,
                        value=str(value),
                        comment="",
                        metadata={
                            "source_type": "json",
                            "original_type": type(value).__name__,
                        },
                    )
                )

        return entries

    def _convert_to_nested_dict(self, entries: list[LanguageEntry]) -> dict[str, Any]:
        """将语言条目转换为嵌套字典"""
        result = {}

        for entry in entries:
            keys = entry.key.split(".")
            current = result

            # 创建嵌套结构
            for i, key in enumerate(keys[:-1]):
                if key not in current:
                    current[key] = {}
                current = current[key]

            # 设置最终值
            current[keys[-1]] = entry.value

        return result

    def _is_flat_structure(self, data: dict[str, Any]) -> bool:
        """检查是否为扁平结构"""
        return all(not isinstance(value, dict) for value in data.values())

    def _get_max_nesting_level(self, data: dict[str, Any], level: int = 1) -> int:
        """获取最大嵌套层级"""
        max_level = level
        for value in data.values():
            if isinstance(value, dict):
                max_level = max(
                    max_level, self._get_max_nesting_level(value, level + 1)
                )
        return max_level


class MinecraftLangParser:
    """Minecraft .lang 文件解析器 (旧版格式)"""

    def __init__(self):
        self.format = MinecraftFileFormat.LANG
        # .lang 文件的键值对正则表达式
        self.line_pattern = re.compile(r"^([^=]+)=(.*)$")
        self.comment_pattern = re.compile(r"^\s*#.*$")

    def can_parse(self, file_path: Path) -> bool:
        """检查是否能解析该文件"""
        return file_path.suffix.lower() == ".lang"

    async def parse(self, file_path: Path, encoding: str = "utf-8") -> ParseResult:
        """解析 .lang 语言文件

        Args:
            file_path: 文件路径
            encoding: 文件编码

        Returns:
            解析结果
        """
        try:
            with open(file_path, encoding=encoding) as f:
                lines = f.readlines()

            entries = []
            comments_count = 0
            empty_lines_count = 0

            for line_num, line in enumerate(lines, 1):
                line = line.rstrip("\n\r")

                # 跳过空行
                if not line.strip():
                    empty_lines_count += 1
                    continue

                # 处理注释行
                if self.comment_pattern.match(line):
                    comments_count += 1
                    continue

                # 解析键值对
                match = self.line_pattern.match(line)
                if match:
                    key = match.group(1).strip()
                    value = match.group(2)

                    entries.append(
                        LanguageEntry(
                            key=key,
                            value=value,
                            comment="",
                            metadata={"line_number": line_num, "source_type": "lang"},
                        )
                    )
                else:
                    # 格式不正确的行，记录但不中断解析
                    continue

            return ParseResult(
                success=True,
                entries=entries,
                file_format=self.format.value,
                encoding=encoding,
                total_keys=len(entries),
                metadata={
                    "total_lines": len(lines),
                    "comments_count": comments_count,
                    "empty_lines_count": empty_lines_count,
                    "malformed_lines": len(lines)
                    - len(entries)
                    - comments_count
                    - empty_lines_count,
                },
            )

        except Exception as e:
            raise FileParsingError(f"解析 .lang 文件时发生错误: {e}") from e

    async def serialize(
        self,
        entries: list[LanguageEntry],
        file_path: Path,
        encoding: str = "utf-8",
        add_header_comment: bool = True,
    ) -> None:
        """序列化语言条目为 .lang 文件"""
        try:
            file_path.parent.mkdir(parents=True, exist_ok=True)

            with open(file_path, "w", encoding=encoding) as f:
                if add_header_comment:
                    f.write("# Generated language file\n")
                    f.write(f"# Total entries: {len(entries)}\n\n")

                for entry in entries:
                    if entry.comment:
                        f.write(f"# {entry.comment}\n")
                    f.write(f"{entry.key}={entry.value}\n")

        except Exception as e:
            raise FileParsingError(f"序列化 .lang 文件时发生错误: {e}") from e


class MinecraftPropertiesParser:
    """Properties 文件解析器"""

    def __init__(self):
        self.format = MinecraftFileFormat.PROPERTIES
        self.line_pattern = re.compile(r"^([^=:]+)[\s]*[=:]\s*(.*)$")
        self.comment_pattern = re.compile(r"^\s*[#!].*$")

    def can_parse(self, file_path: Path) -> bool:
        """检查是否能解析该文件"""
        return file_path.suffix.lower() in [".properties", ".cfg"]

    async def parse(self, file_path: Path, encoding: str = "utf-8") -> ParseResult:
        """解析 Properties 文件"""
        try:
            with open(file_path, encoding=encoding) as f:
                lines = f.readlines()

            entries = []

            for line_num, line in enumerate(lines, 1):
                line = line.strip()

                if not line or self.comment_pattern.match(line):
                    continue

                match = self.line_pattern.match(line)
                if match:
                    key = match.group(1).strip()
                    value = match.group(2).strip()

                    entries.append(
                        LanguageEntry(
                            key=key,
                            value=value,
                            comment="",
                            metadata={
                                "line_number": line_num,
                                "source_type": "properties",
                            },
                        )
                    )

            return ParseResult(
                success=True,
                entries=entries,
                file_format=self.format.value,
                encoding=encoding,
                total_keys=len(entries),
            )

        except Exception as e:
            raise FileParsingError(f"解析 Properties 文件时发生错误: {e}") from e

    async def serialize(
        self, entries: list[LanguageEntry], file_path: Path, encoding: str = "utf-8"
    ) -> None:
        """序列化为 Properties 文件"""
        try:
            file_path.parent.mkdir(parents=True, exist_ok=True)

            with open(file_path, "w", encoding=encoding) as f:
                for entry in entries:
                    f.write(f"{entry.key}={entry.value}\n")

        except Exception as e:
            raise FileParsingError(f"序列化 Properties 文件时发生错误: {e}") from e


class EncodingDetector:
    """文件编码检测器"""

    @staticmethod
    def detect_encoding(file_path: Path) -> str:
        """检测文件编码

        Args:
            file_path: 文件路径

        Returns:
            检测到的编码名称
        """
        try:
            with open(file_path, "rb") as f:
                raw_data = f.read(8192)  # 读取前8KB用于检测

            result = chardet.detect(raw_data)
            encoding = result.get("encoding", "utf-8")
            confidence = result.get("confidence", 0.0)

            # 如果置信度太低，使用默认编码
            if confidence < 0.7:
                return "utf-8"

            # 标准化编码名称
            encoding = encoding.lower()
            if encoding in ["gb2312", "gbk", "gb18030"]:
                return "gbk"
            elif encoding.startswith("utf-8"):
                return "utf-8"
            elif encoding in ["ascii", "latin1", "iso-8859-1"]:
                return "latin1"
            else:
                return encoding

        except Exception:
            return "utf-8"

    @staticmethod
    def validate_encoding(file_path: Path, encoding: str) -> bool:
        """验证编码是否正确

        Args:
            file_path: 文件路径
            encoding: 编码名称

        Returns:
            是否能正确解码
        """
        try:
            with open(file_path, encoding=encoding) as f:
                f.read()
            return True
        except UnicodeDecodeError:
            return False
        except Exception:
            return False


class MinecraftParserFactory:
    """Minecraft 解析器工厂实现"""

    def __init__(self):
        self.parsers = {
            MinecraftFileFormat.JSON: MinecraftJsonParser(),
            MinecraftFileFormat.LANG: MinecraftLangParser(),
            MinecraftFileFormat.PROPERTIES: MinecraftPropertiesParser(),
        }
        self.encoding_detector = EncodingDetector()

    def get_parser(self, file_path: Path) -> FileParser | None:
        """获取文件解析器

        Args:
            file_path: 文件路径

        Returns:
            对应的解析器实例，如果没有找到则返回 None
        """
        for parser in self.parsers.values():
            if parser.can_parse(file_path):
                return parser
        return None

    def detect_format(self, file_path: Path) -> MinecraftFileFormat:
        """检测文件格式

        Args:
            file_path: 文件路径

        Returns:
            检测到的文件格式
        """
        suffix = file_path.suffix.lower()

        if suffix == ".json":
            return MinecraftFileFormat.JSON
        elif suffix == ".lang":
            return MinecraftFileFormat.LANG
        elif suffix in [".properties", ".cfg"]:
            return MinecraftFileFormat.PROPERTIES
        elif suffix == ".toml":
            return MinecraftFileFormat.TOML
        else:
            return MinecraftFileFormat.UNKNOWN

    async def parse_file(
        self, file_path: Path, encoding: str | None = None
    ) -> ParseResult:
        """解析文件

        Args:
            file_path: 文件路径
            encoding: 指定编码，如果为 None 则自动检测

        Returns:
            解析结果

        Raises:
            UnsupportedFileFormatError: 不支持的文件格式
            FileParsingError: 解析失败
        """
        # 获取解析器
        parser = self.get_parser(file_path)
        if not parser:
            file_format = self.detect_format(file_path)
            raise UnsupportedFileFormatError(f"不支持的文件格式: {file_format.value}")

        # 检测编码
        if encoding is None:
            encoding = self.encoding_detector.detect_encoding(file_path)

        # 验证编码
        if not self.encoding_detector.validate_encoding(file_path, encoding):
            # 尝试常用编码
            for fallback_encoding in ["utf-8", "gbk", "latin1"]:
                if self.encoding_detector.validate_encoding(
                    file_path, fallback_encoding
                ):
                    encoding = fallback_encoding
                    break
            else:
                raise FileParsingError(f"无法确定文件编码: {file_path}")

        # 解析文件
        return await parser.parse(file_path, encoding)

    def get_supported_formats(self) -> list[str]:
        """获取支持的文件格式列表

        Returns:
            支持的格式名称列表
        """
        return [fmt.value for fmt in self.parsers.keys()]

    def get_format_extensions(self) -> dict[str, list[str]]:
        """获取格式对应的文件扩展名

        Returns:
            格式到扩展名列表的映射
        """
        return {
            MinecraftFileFormat.JSON.value: [".json"],
            MinecraftFileFormat.LANG.value: [".lang"],
            MinecraftFileFormat.PROPERTIES.value: [".properties", ".cfg"],
            MinecraftFileFormat.TOML.value: [".toml"],
        }

    async def convert_format(
        self,
        source_path: Path,
        target_path: Path,
        target_format: str,
        source_encoding: str | None = None,
        target_encoding: str = "utf-8",
    ) -> None:
        """转换文件格式

        Args:
            source_path: 源文件路径
            target_path: 目标文件路径
            target_format: 目标格式
            source_encoding: 源文件编码
            target_encoding: 目标文件编码
        """
        # 解析源文件
        result = await self.parse_file(source_path, source_encoding)

        # 获取目标格式解析器
        target_format_enum = MinecraftFileFormat(target_format)
        target_parser = self.parsers.get(target_format_enum)

        if not target_parser:
            raise UnsupportedFileFormatError(f"不支持的目标格式: {target_format}")

        # 序列化为目标格式
        await target_parser.serialize(result.entries, target_path, target_encoding)
