"""
Properties解析器

处理Minecraft旧版本的Properties格式语言文件 (.lang, .properties)
"""

import re
from datetime import datetime

from packages.core.framework.logging import get_logger

from domain.models.enums import FileType
from domain.models.value_objects.language_code import LanguageCode
from domain.models.value_objects.translation_key import TranslationKey
from .base_parser import BaseParser, ParsedEntry, ParseResult

logger = get_logger(__name__)


class PropertiesParser(BaseParser):
    """Properties解析器"""

    def __init__(self):
        super().__init__("Properties解析器", {FileType.PROPERTIES})

        # Properties文件的特殊字符转义映射
        self._escape_map = {
            "\\n": "\n",
            "\\t": "\t",
            "\\r": "\r",
            '\\"': '"',
            "\\'": "'",
            "\\\\": "\\",
        }

        # 反向转义映射（用于序列化）
        self._unescape_map = {v: k for k, v in self._escape_map.items()}

    async def parse(
        self,
        content: bytes,
        file_path: str,
        language_code: LanguageCode | None = None,
        encoding: str = "utf-8",
    ) -> ParseResult:
        """解析Properties语言文件"""
        start_time = datetime.utcnow()
        entries = {}
        errors = []
        warnings = []
        metadata = {
            "file_path": file_path,
            "original_size": len(content),
            "encoding": encoding,
            "total_lines": 0,
            "comment_lines": 0,
            "empty_lines": 0,
            "continuation_lines": 0,
        }

        self._logger.info(f"开始解析Properties文件: {file_path}")

        try:
            # 尝试多种编码解码
            text_content = await self._decode_with_fallback(content, encoding)
            metadata["decoded_size"] = len(text_content)

            # 按行分割并预处理
            raw_lines = text_content.splitlines()
            metadata["total_lines"] = len(raw_lines)

            # 处理行连续和合并
            processed_lines = await self._process_line_continuations(raw_lines)

            # 解析每一行
            for line_num, line_data in enumerate(processed_lines, 1):
                try:
                    original_line = line_data["content"]
                    original_line_num = line_data["line_number"]

                    # 统计不同类型的行
                    if not original_line.strip():
                        metadata["empty_lines"] += 1
                        continue

                    if original_line.strip().startswith(
                        "#"
                    ) or original_line.strip().startswith("!"):
                        metadata["comment_lines"] += 1
                        continue

                    # 解析键值对
                    key_value_pair = await self._parse_key_value_line(
                        original_line, original_line_num
                    )
                    if not key_value_pair:
                        continue  # 不是有效的键值对行

                    key_str, value_str, comment = key_value_pair

                    # 验证翻译键
                    key_errors = self._validate_translation_key(
                        key_str, original_line_num
                    )
                    if key_errors:
                        errors.extend(key_errors)
                        continue

                    # 处理转义字符
                    unescaped_value = self._unescape_value(value_str)

                    # 验证翻译值
                    value_warnings = self._validate_translation_value(
                        unescaped_value, key_str, original_line_num
                    )
                    warnings.extend(value_warnings)

                    # 创建翻译键
                    translation_key = TranslationKey(key_str)

                    # 检查重复键
                    if translation_key in entries:
                        warnings.append(
                            f"重复的翻译键: '{key_str}' (行 {original_line_num})"
                        )
                        continue

                    # 创建解析条目
                    parsed_entry = ParsedEntry(
                        key=translation_key,
                        value=unescaped_value,
                        line_number=original_line_num,
                        comment=comment,
                        context=self._extract_context_from_key(key_str),
                    )

                    entries[translation_key] = parsed_entry

                except Exception as e:
                    error_msg = f"处理行失败 (行 {line_num}): {str(e)}"
                    errors.append(error_msg)
                    continue

            # 更新元数据
            metadata["total_entries"] = len(entries)
            metadata["has_placeholders"] = self._count_entries_with_placeholders(
                entries
            )
            metadata["duplicate_keys"] = len(
                [w for w in warnings if "重复的翻译键" in w]
            )

            result = await self._create_parse_result(
                entries,
                FileType.PROPERTIES,
                language_code,
                metadata,
                errors,
                warnings,
                start_time,
            )

            self._log_parsing_summary(result)
            return result

        except Exception as e:
            error_msg = f"Properties解析失败: {str(e)}"
            errors.append(error_msg)
            self._logger.error(f"Properties解析异常 {file_path}: {error_msg}")

            return await self._create_parse_result(
                {},
                FileType.PROPERTIES,
                language_code,
                metadata,
                errors,
                warnings,
                start_time,
            )

    async def serialize(
        self,
        entries: dict[TranslationKey, ParsedEntry],
        file_type: FileType,
        language_code: LanguageCode | None = None,
        encoding: str = "utf-8",
    ) -> bytes:
        """将翻译条目序列化为Properties格式"""
        if file_type != FileType.PROPERTIES:
            raise ValueError(f"Properties解析器不支持文件类型: {file_type}")

        try:
            lines = []

            # 添加文件头注释
            if language_code:
                lines.append(
                    f"# Language: {language_code.display_name} ({language_code.code})"
                )
            lines.append("# Generated by TH-Suite MC L10n")
            lines.append(f"# Total entries: {len(entries)}")
            lines.append("")  # 空行

            # 按键排序
            sorted_entries = sorted(entries.items(), key=lambda x: x[0].value)

            # 处理每个条目
            for translation_key, parsed_entry in sorted_entries:
                # 添加注释（如果有）
                if parsed_entry.comment:
                    lines.append(f"# {parsed_entry.comment}")

                # 转义值
                escaped_value = self._escape_value(parsed_entry.value)

                # 构建键值对行
                key_value_line = f"{translation_key.value}={escaped_value}"
                lines.append(key_value_line)

                # 在条目间添加空行（可选，美化格式）
                if parsed_entry.context and len(lines) > 0:
                    lines.append("")

            # 合并所有行
            properties_text = "\n".join(lines)

            return properties_text.encode(encoding)

        except Exception as e:
            self._logger.error(f"Properties序列化失败: {str(e)}")
            raise

    async def _decode_with_fallback(
        self, content: bytes, preferred_encoding: str
    ) -> str:
        """使用回退机制解码内容"""
        # 尝试多种编码
        encodings_to_try = [
            preferred_encoding,
            "utf-8",
            "utf-8-sig",  # UTF-8 with BOM
            "latin1",  # ISO-8859-1，几乎不会失败
            "cp1252",  # Windows-1252
            "gbk",  # 中文
            "big5",  # 繁体中文
        ]

        for encoding in encodings_to_try:
            try:
                return content.decode(encoding)
            except UnicodeDecodeError:
                continue

        # 如果所有编码都失败，使用utf-8并忽略错误
        self._logger.warning("所有编码解码都失败，使用UTF-8并忽略错误")
        return content.decode("utf-8", errors="replace")

    async def _process_line_continuations(self, raw_lines: list[str]) -> list[dict]:
        """处理行连续（反斜杠结尾的行）"""
        processed_lines = []
        i = 0

        while i < len(raw_lines):
            current_line = raw_lines[i]
            line_number = i + 1

            # 检查是否有行连续
            while current_line.endswith("\\") and i + 1 < len(raw_lines):
                # 移除尾部的反斜杠并连接下一行
                current_line = current_line[:-1] + raw_lines[i + 1]
                i += 1

            processed_lines.append(
                {
                    "content": current_line,
                    "line_number": line_number,
                    "is_continuation": i > line_number - 1,
                }
            )

            i += 1

        return processed_lines

    async def _parse_key_value_line(
        self, line: str, line_number: int
    ) -> tuple[str, str, str | None] | None:
        """解析键值对行"""
        original_line = line
        line = line.strip()

        # 跳过空行和注释行
        if not line or line.startswith("#") or line.startswith("!"):
            return None

        # 查找分隔符（= 或 :）
        # Properties格式支持 =, :, 或空格作为分隔符
        separator_match = re.search(r"(?<!\\)[=:]", line)
        if not separator_match:
            # 尝试空格分隔符（第一个非转义空格）
            space_match = re.search(r"(?<!\\)\s", line)
            if space_match:
                separator_pos = space_match.start()
            else:
                self._logger.warning(
                    f"行 {line_number}: 未找到键值分隔符: '{original_line}'"
                )
                return None
        else:
            separator_pos = separator_match.start()

        # 提取键和值
        key = line[:separator_pos].strip()
        value_part = line[separator_pos + 1 :].strip()

        # 检查行末注释
        comment = None
        comment_match = re.search(r"(?<!\\)#(.*)$", value_part)
        if comment_match:
            comment = comment_match.group(1).strip()
            value_part = value_part[: comment_match.start()].strip()

        if not key:
            self._logger.warning(f"行 {line_number}: 键为空: '{original_line}'")
            return None

        return key, value_part, comment

    def _unescape_value(self, value: str) -> str:
        """处理Properties转义字符"""
        if not value:
            return value

        result = value

        # 处理转义字符
        for escaped, unescaped in self._escape_map.items():
            result = result.replace(escaped, unescaped)

        # 处理Unicode转义 (\\uxxxx)
        def replace_unicode(match):
            try:
                unicode_value = int(match.group(1), 16)
                return chr(unicode_value)
            except (ValueError, OverflowError):
                return match.group(0)  # 保持原样如果转换失败

        result = re.sub(r"\\u([0-9a-fA-F]{4})", replace_unicode, result)

        return result

    def _escape_value(self, value: str) -> str:
        """转义Properties值"""
        if not value:
            return value

        result = value

        # 转义特殊字符
        for unescaped, escaped in self._unescape_map.items():
            result = result.replace(unescaped, escaped)

        # 转义非ASCII字符为Unicode转义（可选）
        def escape_unicode(char):
            if ord(char) > 127:
                return f"\\u{ord(char):04x}"
            return char

        # 暂时不自动转义Unicode，保持原样
        # result = ''.join(escape_unicode(char) for char in result)

        return result

    def _extract_context_from_key(self, key: str) -> str | None:
        """从翻译键中提取上下文信息"""
        # Properties文件的键格式通常更简单
        if "." in key:
            key.split(".")
            context_parts = []

            # 常见的Minecraft Properties键模式
            if key.startswith("tile."):
                context_parts.append("类型: 方块")
            elif key.startswith("item."):
                context_parts.append("类型: 物品")
            elif key.startswith("entity."):
                context_parts.append("类型: 实体")
            elif key.startswith("gui."):
                context_parts.append("类型: 界面")
            elif key.startswith("death."):
                context_parts.append("类型: 死亡信息")
            elif key.startswith("achievement."):
                context_parts.append("类型: 成就")

            if context_parts:
                return ", ".join(context_parts)

        return None

    def _count_entries_with_placeholders(
        self, entries: dict[TranslationKey, ParsedEntry]
    ) -> int:
        """统计包含占位符的条目数量"""
        count = 0
        for entry in entries.values():
            placeholders = self._extract_minecraft_placeholders(entry.value)
            if placeholders:
                count += 1
        return count

    async def validate_properties_syntax(self, content: bytes) -> list[str]:
        """验证Properties文件语法"""
        issues = []

        try:
            text_content = await self._decode_with_fallback(content, "utf-8")
            lines = text_content.splitlines()

            for line_num, line in enumerate(lines, 1):
                original_line = line
                line = line.strip()

                # 跳过空行和注释
                if not line or line.startswith("#") or line.startswith("!"):
                    continue

                # 检查分隔符
                if not re.search(r"(?<!\\)[=:\s]", line):
                    issues.append(f"行 {line_num}: 缺少键值分隔符: '{original_line}'")
                    continue

                # 检查未闭合的转义
                if line.count("\\") % 2 == 1 and not line.endswith("\\"):
                    issues.append(
                        f"行 {line_num}: 可能存在未正确转义的字符: '{original_line}'"
                    )

                # 检查Unicode转义
                unicode_escapes = re.findall(r"\\u([0-9a-fA-F]*)", line)
                for escape_seq in unicode_escapes:
                    if len(escape_seq) != 4:
                        issues.append(
                            f"行 {line_num}: 无效的Unicode转义序列: \\u{escape_seq}"
                        )

        except Exception as e:
            issues.append(f"语法验证失败: {str(e)}")

        return issues

    async def convert_to_json_format(
        self, properties_content: bytes, language_code: LanguageCode | None = None
    ) -> bytes:
        """将Properties格式转换为JSON格式"""
        try:
            # 解析Properties
            parse_result = await self.parse(
                properties_content, "temp.properties", language_code
            )

            if parse_result.errors:
                raise ValueError(f"Properties解析失败: {parse_result.errors}")

            # 构建JSON数据
            import json

            json_data = {}

            for translation_key, parsed_entry in parse_result.entries.items():
                json_data[translation_key.value] = parsed_entry.value

            # 序列化为JSON
            json_str = json.dumps(
                json_data,
                ensure_ascii=False,
                indent=2,
                separators=(",", ": "),
                sort_keys=True,
            )

            return json_str.encode("utf-8")

        except Exception as e:
            self._logger.error(f"Properties转JSON失败: {str(e)}")
            raise

    async def merge_properties_files(
        self, base_content: bytes, overlay_content: bytes
    ) -> bytes:
        """合并两个Properties文件"""
        try:
            # 解析两个文件
            base_result = await self.parse(base_content, "base.properties")
            overlay_result = await self.parse(overlay_content, "overlay.properties")

            if base_result.errors or overlay_result.errors:
                raise ValueError("Properties文件解析失败")

            # 合并条目（overlay覆盖base）
            merged_entries = {**base_result.entries, **overlay_result.entries}

            # 序列化结果
            return await self.serialize(merged_entries, FileType.PROPERTIES)

        except Exception as e:
            self._logger.error(f"Properties文件合并失败: {str(e)}")
            raise
