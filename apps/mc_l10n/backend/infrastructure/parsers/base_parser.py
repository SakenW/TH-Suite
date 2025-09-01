"""
基础解析器

定义所有解析器的通用接口和基础功能
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import datetime
from typing import Any

from packages.core.framework.logging import get_logger

from domain.models.enums import FileType
from domain.models.value_objects.language_code import LanguageCode
from domain.models.value_objects.translation_key import TranslationKey

logger = get_logger(__name__)


@dataclass
class ParsedEntry:
    """解析后的翻译条目"""

    key: TranslationKey
    value: str
    line_number: int | None = None
    context: str | None = None
    comment: str | None = None

    def __post_init__(self):
        if not isinstance(self.key, TranslationKey):
            self.key = TranslationKey(str(self.key))


@dataclass
class ParseResult:
    """解析结果"""

    entries: dict[TranslationKey, ParsedEntry]
    file_type: FileType
    language_code: LanguageCode | None
    metadata: dict[str, Any]
    errors: list[str]
    warnings: list[str]
    parsing_time_ms: int

    def __post_init__(self):
        if self.entries is None:
            self.entries = {}
        if self.metadata is None:
            self.metadata = {}
        if self.errors is None:
            self.errors = []
        if self.warnings is None:
            self.warnings = []


@dataclass
class ParsingError:
    """解析错误"""

    message: str
    line_number: int | None = None
    column: int | None = None
    severity: str = "error"  # "error", "warning", "info"
    suggestion: str | None = None


class BaseParser(ABC):
    """基础解析器抽象类"""

    def __init__(self, parser_name: str, supported_file_types: set[FileType]):
        self._parser_name = parser_name
        self._supported_file_types = supported_file_types
        self._logger = get_logger(f"{__name__}.{parser_name}")

    @property
    def parser_name(self) -> str:
        return self._parser_name

    @property
    def supported_file_types(self) -> set[FileType]:
        return self._supported_file_types.copy()

    def can_parse(self, file_type: FileType) -> bool:
        """检查解析器是否能处理指定的文件类型"""
        return file_type in self._supported_file_types

    @abstractmethod
    async def parse(
        self,
        content: bytes,
        file_path: str,
        language_code: LanguageCode | None = None,
        encoding: str = "utf-8",
    ) -> ParseResult:
        """解析文件内容"""
        pass

    @abstractmethod
    async def serialize(
        self,
        entries: dict[TranslationKey, ParsedEntry],
        file_type: FileType,
        language_code: LanguageCode | None = None,
        encoding: str = "utf-8",
    ) -> bytes:
        """将翻译条目序列化为文件内容"""
        pass

    async def _create_parse_result(
        self,
        entries: dict[TranslationKey, ParsedEntry],
        file_type: FileType,
        language_code: LanguageCode | None,
        metadata: dict[str, Any],
        errors: list[str],
        warnings: list[str],
        start_time: datetime,
    ) -> ParseResult:
        """创建解析结果"""
        end_time = datetime.utcnow()
        parsing_time = int((end_time - start_time).total_seconds() * 1000)

        return ParseResult(
            entries=entries,
            file_type=file_type,
            language_code=language_code,
            metadata=metadata,
            errors=errors,
            warnings=warnings,
            parsing_time_ms=parsing_time,
        )

    def _detect_encoding(self, content: bytes) -> str:
        """检测文件编码"""
        # 尝试常见编码
        encodings = ["utf-8", "utf-8-sig", "latin-1", "gbk", "big5"]

        for encoding in encodings:
            try:
                content.decode(encoding)
                return encoding
            except UnicodeDecodeError:
                continue

        # 如果都失败了，使用utf-8并忽略错误
        self._logger.warning("无法检测文件编码，使用UTF-8")
        return "utf-8"

    def _safe_decode(self, content: bytes, encoding: str = "utf-8") -> str:
        """安全解码内容"""
        try:
            return content.decode(encoding)
        except UnicodeDecodeError as e:
            self._logger.warning(f"使用{encoding}编码解码失败，尝试检测编码: {str(e)}")
            detected_encoding = self._detect_encoding(content)
            try:
                return content.decode(detected_encoding, errors="replace")
            except Exception as e:
                self._logger.error(f"解码失败: {str(e)}")
                return content.decode("utf-8", errors="replace")

    def _validate_translation_key(
        self, key: str, line_number: int | None = None
    ) -> list[str]:
        """验证翻译键"""
        errors = []

        if not key:
            errors.append(
                f"翻译键不能为空{f' (行 {line_number})' if line_number else ''}"
            )
            return errors

        if len(key) > 255:
            errors.append(
                f"翻译键过长 '{key[:50]}...' {f' (行 {line_number})' if line_number else ''}"
            )

        # 检查特殊字符
        invalid_chars = set(key) - set(
            "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789._-"
        )
        if invalid_chars:
            errors.append(
                f"翻译键包含无效字符 '{', '.join(invalid_chars)}' in '{key}' "
                f"{f' (行 {line_number})' if line_number else ''}"
            )

        return errors

    def _validate_translation_value(
        self, value: str, key: str, line_number: int | None = None
    ) -> list[str]:
        """验证翻译值"""
        warnings = []

        if not value:
            warnings.append(
                f"翻译值为空 '{key}'{f' (行 {line_number})' if line_number else ''}"
            )
            return warnings

        if len(value) > 1000:
            warnings.append(
                f"翻译值过长 '{key}' ({len(value)}字符){f' (行 {line_number})' if line_number else ''}"
            )

        # 检查可能的格式问题
        if value.startswith(" ") or value.endswith(" "):
            warnings.append(
                f"翻译值前后有空格 '{key}'{f' (行 {line_number})' if line_number else ''}"
            )

        return warnings

    def _extract_minecraft_placeholders(self, text: str) -> set[str]:
        """提取Minecraft占位符"""
        import re

        placeholders = set()

        # 常见的Minecraft占位符模式
        patterns = [
            r"%[sdfc]",  # Java String.format
            r"%\d+\$[sdfc]",  # 位置参数
            r"\{[0-9]+\}",  # {0}, {1}, etc.
            r"\{[a-zA-Z_][a-zA-Z0-9_]*\}",  # {player}, {item}, etc.
            r"§[0-9a-fk-or]",  # 颜色代码
        ]

        for pattern in patterns:
            matches = re.findall(pattern, text)
            placeholders.update(matches)

        return placeholders

    def _log_parsing_summary(self, result: ParseResult):
        """记录解析摘要"""
        entry_count = len(result.entries)
        error_count = len(result.errors)
        warning_count = len(result.warnings)

        self._logger.info(
            f"{self._parser_name}解析完成: "
            f"条目={entry_count}, "
            f"错误={error_count}, "
            f"警告={warning_count}, "
            f"耗时={result.parsing_time_ms}ms"
        )

        if result.errors:
            self._logger.warning(f"解析过程中发现 {error_count} 个错误")
            for error in result.errors[:3]:  # 只显示前3个错误
                self._logger.warning(f"  - {error}")

        if result.warnings:
            self._logger.info(f"解析过程中发现 {warning_count} 个警告")


class ParserRegistry:
    """解析器注册表"""

    def __init__(self):
        self._parsers: dict[FileType, BaseParser] = {}
        self._all_parsers: list[BaseParser] = []
        self._logger = get_logger(__name__ + ".ParserRegistry")

    def register(self, parser: BaseParser):
        """注册解析器"""
        for file_type in parser.supported_file_types:
            if file_type in self._parsers:
                old_parser = self._parsers[file_type]
                self._logger.warning(
                    f"文件类型 {file_type.value} 的解析器被覆盖: "
                    f"{old_parser.parser_name} -> {parser.parser_name}"
                )

            self._parsers[file_type] = parser

        if parser not in self._all_parsers:
            self._all_parsers.append(parser)

        self._logger.info(
            f"注册解析器: {parser.parser_name} (支持: {[ft.value for ft in parser.supported_file_types]})"
        )

    def unregister(self, parser: BaseParser):
        """注销解析器"""
        # 从文件类型映射中移除
        for file_type in list(self._parsers.keys()):
            if self._parsers[file_type] == parser:
                del self._parsers[file_type]

        # 从所有解析器列表中移除
        if parser in self._all_parsers:
            self._all_parsers.remove(parser)

        self._logger.info(f"注销解析器: {parser.parser_name}")

    def get_parser(self, file_type: FileType) -> BaseParser | None:
        """获取指定文件类型的解析器"""
        parser = self._parsers.get(file_type)
        if not parser:
            self._logger.warning(f"未找到文件类型 {file_type.value} 的解析器")
        return parser

    async def parse_with_auto_detection(
        self, content: bytes, file_path: str, language_code: LanguageCode | None = None
    ) -> ParseResult | None:
        """自动检测文件类型并解析"""
        # 从文件扩展名推断类型
        from pathlib import Path

        file_extension = Path(file_path).suffix.lower()

        file_type_map = {
            ".json": FileType.JSON,
            ".properties": FileType.PROPERTIES,
            ".lang": FileType.PROPERTIES,
            ".yml": FileType.YAML,
            ".yaml": FileType.YAML,
        }

        file_type = file_type_map.get(file_extension, FileType.UNKNOWN)

        if file_type == FileType.UNKNOWN:
            self._logger.warning(f"无法识别文件类型: {file_path}")
            return None

        parser = self.get_parser(file_type)
        if not parser:
            return None

        try:
            return await parser.parse(content, file_path, language_code)
        except Exception as e:
            self._logger.error(f"解析文件失败 {file_path}: {str(e)}")
            return None

    def get_supported_file_types(self) -> set[FileType]:
        """获取所有支持的文件类型"""
        return set(self._parsers.keys())

    def get_all_parsers(self) -> list[BaseParser]:
        """获取所有已注册的解析器"""
        return self._all_parsers.copy()


# 全局解析器注册表实例
parser_registry = ParserRegistry()
