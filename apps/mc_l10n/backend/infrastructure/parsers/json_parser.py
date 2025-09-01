"""
JSON解析器

处理Minecraft现代版本的JSON格式语言文件
"""

import json
from datetime import datetime

from packages.core.framework.logging import get_logger

from domain.models.enums import FileType
from domain.models.value_objects.language_code import LanguageCode
from domain.models.value_objects.translation_key import TranslationKey
from .base_parser import BaseParser, ParsedEntry, ParseResult

logger = get_logger(__name__)


class JsonParser(BaseParser):
    """JSON解析器"""

    def __init__(self):
        super().__init__("JSON解析器", {FileType.JSON})

    async def parse(
        self,
        content: bytes,
        file_path: str,
        language_code: LanguageCode | None = None,
        encoding: str = "utf-8",
    ) -> ParseResult:
        """解析JSON语言文件"""
        start_time = datetime.utcnow()
        entries = {}
        errors = []
        warnings = []
        metadata = {
            "file_path": file_path,
            "original_size": len(content),
            "encoding": encoding,
            "nested_structure": False,
            "max_nesting_level": 0,
        }

        self._logger.info(f"开始解析JSON文件: {file_path}")

        try:
            # 安全解码内容
            text_content = self._safe_decode(content, encoding)
            metadata["decoded_size"] = len(text_content)

            # 解析JSON
            try:
                json_data = json.loads(text_content)
            except json.JSONDecodeError as e:
                error_msg = f"JSON格式错误: {str(e)}"
                if hasattr(e, "lineno"):
                    error_msg += f" (行 {e.lineno})"
                errors.append(error_msg)

                # 尝试修复常见的JSON错误
                fixed_content = await self._attempt_json_repair(text_content)
                if fixed_content:
                    try:
                        json_data = json.loads(fixed_content)
                        warnings.append("JSON文件已自动修复")
                        metadata["auto_repaired"] = True
                    except json.JSONDecodeError:
                        # 修复失败，返回错误结果
                        return await self._create_parse_result(
                            {},
                            FileType.JSON,
                            language_code,
                            metadata,
                            errors,
                            warnings,
                            start_time,
                        )
                else:
                    return await self._create_parse_result(
                        {},
                        FileType.JSON,
                        language_code,
                        metadata,
                        errors,
                        warnings,
                        start_time,
                    )

            # 验证JSON结构
            if not isinstance(json_data, dict):
                errors.append("JSON根元素必须是对象")
                return await self._create_parse_result(
                    {},
                    FileType.JSON,
                    language_code,
                    metadata,
                    errors,
                    warnings,
                    start_time,
                )

            # 分析和扁平化JSON结构
            flattened_data, structure_info = await self._flatten_json_structure(
                json_data
            )
            metadata.update(structure_info)

            # 处理每个翻译条目
            for key_str, value in flattened_data.items():
                try:
                    # 验证翻译键
                    key_errors = self._validate_translation_key(key_str)
                    if key_errors:
                        errors.extend(key_errors)
                        continue

                    # 验证翻译值
                    if not isinstance(value, str):
                        if isinstance(value, int | float | bool):
                            # 自动转换基本类型
                            value = str(value)
                            warnings.append(
                                f"键 '{key_str}' 的值已自动转换为字符串: {type(value).__name__}"
                            )
                        else:
                            errors.append(
                                f"键 '{key_str}' 的值不是字符串类型: {type(value)}"
                            )
                            continue

                    value_warnings = self._validate_translation_value(value, key_str)
                    warnings.extend(value_warnings)

                    # 创建翻译键
                    translation_key = TranslationKey(key_str)

                    # 创建解析条目
                    parsed_entry = ParsedEntry(
                        key=translation_key,
                        value=value,
                        context=self._extract_context_from_key(key_str),
                    )

                    entries[translation_key] = parsed_entry

                except Exception as e:
                    error_msg = f"处理条目失败 '{key_str}': {str(e)}"
                    errors.append(error_msg)
                    continue

            # 更新元数据
            metadata["total_entries"] = len(entries)
            metadata["has_placeholders"] = self._count_entries_with_placeholders(
                entries
            )

            result = await self._create_parse_result(
                entries,
                FileType.JSON,
                language_code,
                metadata,
                errors,
                warnings,
                start_time,
            )

            self._log_parsing_summary(result)
            return result

        except Exception as e:
            error_msg = f"JSON解析失败: {str(e)}"
            errors.append(error_msg)
            self._logger.error(f"JSON解析异常 {file_path}: {error_msg}")

            return await self._create_parse_result(
                {}, FileType.JSON, language_code, metadata, errors, warnings, start_time
            )

    async def serialize(
        self,
        entries: dict[TranslationKey, ParsedEntry],
        file_type: FileType,
        language_code: LanguageCode | None = None,
        encoding: str = "utf-8",
    ) -> bytes:
        """将翻译条目序列化为JSON格式"""
        if file_type != FileType.JSON:
            raise ValueError(f"JSON解析器不支持文件类型: {file_type}")

        try:
            # 构建JSON数据
            json_data = {}

            for translation_key, parsed_entry in entries.items():
                key_str = translation_key.value
                value = parsed_entry.value

                # 处理嵌套键（如果需要还原嵌套结构）
                if "." in key_str and await self._should_create_nested_structure(
                    entries
                ):
                    self._set_nested_value(json_data, key_str, value)
                else:
                    json_data[key_str] = value

            # 序列化为JSON
            json_str = json.dumps(
                json_data,
                ensure_ascii=False,  # 允许Unicode字符
                indent=2,  # 美化格式
                separators=(",", ": "),  # 标准分隔符
                sort_keys=True,  # 按键排序
            )

            return json_str.encode(encoding)

        except Exception as e:
            self._logger.error(f"JSON序列化失败: {str(e)}")
            raise

    async def _flatten_json_structure(self, json_data: dict) -> tuple[dict, dict]:
        """扁平化JSON结构并返回结构信息"""
        flattened = {}
        structure_info = {
            "nested_structure": False,
            "max_nesting_level": 0,
            "nested_keys": [],
        }

        def _flatten_recursive(obj, prefix="", level=0):
            structure_info["max_nesting_level"] = max(
                structure_info["max_nesting_level"], level
            )

            if isinstance(obj, dict):
                if level > 0:
                    structure_info["nested_structure"] = True

                for key, value in obj.items():
                    full_key = f"{prefix}.{key}" if prefix else key

                    if isinstance(value, dict):
                        structure_info["nested_keys"].append(full_key)
                        _flatten_recursive(value, full_key, level + 1)
                    elif isinstance(value, list):
                        # 处理数组
                        for i, item in enumerate(value):
                            array_key = f"{full_key}[{i}]"
                            if isinstance(item, str):
                                flattened[array_key] = item
                            else:
                                _flatten_recursive(item, array_key, level + 1)
                    else:
                        flattened[full_key] = value
            else:
                flattened[prefix] = obj

        _flatten_recursive(json_data)
        return flattened, structure_info

    def _set_nested_value(self, json_data: dict, key_path: str, value: str):
        """在嵌套的JSON结构中设置值"""
        keys = key_path.split(".")
        current = json_data

        for key in keys[:-1]:
            if key not in current:
                current[key] = {}
            elif not isinstance(current[key], dict):
                # 如果已存在但不是字典，转换为字典
                current[key] = {}
            current = current[key]

        current[keys[-1]] = value

    async def _should_create_nested_structure(
        self, entries: dict[TranslationKey, ParsedEntry]
    ) -> bool:
        """判断是否应该创建嵌套结构"""
        # 如果大部分键都有共同前缀，可能需要嵌套结构
        key_prefixes = set()
        for key in entries.keys():
            parts = key.value.split(".")
            if len(parts) > 1:
                key_prefixes.add(parts[0])

        # 如果有多个不同的前缀，可能需要嵌套
        return len(key_prefixes) > 5

    def _extract_context_from_key(self, key: str) -> str | None:
        """从翻译键中提取上下文信息"""
        parts = key.split(".")
        if len(parts) >= 2:
            context_parts = []

            # 添加类型信息
            key_type = parts[0]
            if key_type in [
                "item",
                "block",
                "entity",
                "biome",
                "enchantment",
                "effect",
            ]:
                context_parts.append(f"类型: {key_type}")

            # 添加模组信息
            if len(parts) >= 3:
                mod_id = parts[1]
                if mod_id != "minecraft":
                    context_parts.append(f"模组: {mod_id}")

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

    async def _attempt_json_repair(self, json_text: str) -> str | None:
        """尝试修复常见的JSON格式错误"""
        try:
            # 修复常见问题
            repaired = json_text

            # 1. 移除尾随逗号
            import re

            repaired = re.sub(r",(\s*[}\]])", r"\1", repaired)

            # 2. 修复单引号
            repaired = re.sub(r"'([^']*)'(?=\s*:)", r'"\1"', repaired)

            # 3. 修复未引用的键
            repaired = re.sub(
                r"([{,]\s*)([a-zA-Z_][a-zA-Z0-9_]*)\s*:", r'\1"\2":', repaired
            )

            # 验证修复结果
            json.loads(repaired)
            self._logger.info("JSON文件修复成功")
            return repaired

        except Exception as e:
            self._logger.warning(f"JSON修复失败: {str(e)}")
            return None

    async def validate_json_structure(self, content: bytes) -> list[str]:
        """验证JSON结构并返回问题列表"""
        issues = []

        try:
            text_content = self._safe_decode(content)
            json_data = json.loads(text_content)

            if not isinstance(json_data, dict):
                issues.append("根元素必须是对象")
                return issues

            # 检查空对象
            if not json_data:
                issues.append("JSON对象为空")

            # 检查键值对
            for key, value in json_data.items():
                if not isinstance(key, str):
                    issues.append(f"键必须是字符串: {type(key)}")

                if not key:
                    issues.append("键不能为空")

                if not isinstance(value, str):
                    if not isinstance(
                        value, dict | list | int | float | bool | type(None)
                    ):
                        issues.append(f"值类型不支持: {type(value)} for key '{key}'")

        except json.JSONDecodeError as e:
            issues.append(f"JSON格式错误: {str(e)}")
        except Exception as e:
            issues.append(f"验证失败: {str(e)}")

        return issues

    async def format_json_content(self, content: bytes, indent: int = 2) -> bytes:
        """格式化JSON内容"""
        try:
            text_content = self._safe_decode(content)
            json_data = json.loads(text_content)

            formatted_json = json.dumps(
                json_data,
                ensure_ascii=False,
                indent=indent,
                separators=(",", ": "),
                sort_keys=True,
            )

            return formatted_json.encode("utf-8")

        except Exception as e:
            self._logger.error(f"JSON格式化失败: {str(e)}")
            return content  # 返回原内容

    async def merge_json_files(
        self, base_content: bytes, overlay_content: bytes
    ) -> bytes:
        """合并两个JSON语言文件"""
        try:
            base_data = json.loads(self._safe_decode(base_content))
            overlay_data = json.loads(self._safe_decode(overlay_content))

            if not isinstance(base_data, dict) or not isinstance(overlay_data, dict):
                raise ValueError("JSON文件必须是对象")

            # 合并数据（overlay覆盖base）
            merged_data = {**base_data, **overlay_data}

            # 序列化结果
            merged_json = json.dumps(
                merged_data,
                ensure_ascii=False,
                indent=2,
                separators=(",", ": "),
                sort_keys=True,
            )

            return merged_json.encode("utf-8")

        except Exception as e:
            self._logger.error(f"JSON文件合并失败: {str(e)}")
            raise
