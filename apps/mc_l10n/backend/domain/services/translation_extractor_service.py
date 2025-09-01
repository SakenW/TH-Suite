"""
翻译提取器领域服务

负责从各种格式的语言文件中提取翻译条目，处理格式转换和数据清理
"""

import json
import re
from dataclasses import dataclass
from datetime import datetime
from typing import Any

from packages.core.framework.logging import get_logger

from domain.models.enums import FileType, TranslationStatus
from domain.models.value_objects.language_code import LanguageCode
from domain.models.value_objects.mod_id import ModId
from domain.models.value_objects.translation_key import TranslationKey

logger = get_logger(__name__)


@dataclass
class TranslationEntry:
    """翻译条目数据"""

    key: TranslationKey
    value: str
    original_value: str
    status: TranslationStatus = TranslationStatus.UNTRANSLATED
    context: str | None = None
    notes: str | None = None
    last_modified: datetime = None

    def __post_init__(self):
        if self.last_modified is None:
            self.last_modified = datetime.utcnow()


@dataclass
class ExtractionResult:
    """提取结果"""

    entries: dict[TranslationKey, TranslationEntry]
    source_file_path: str
    language_code: LanguageCode
    file_type: FileType
    extraction_errors: list[str]
    statistics: "ExtractionStatistics"

    def __post_init__(self):
        if self.extraction_errors is None:
            self.extraction_errors = []


@dataclass
class ExtractionStatistics:
    """提取统计信息"""

    total_entries: int
    valid_entries: int
    invalid_entries: int
    duplicate_keys: int
    empty_values: int
    format_issues: int


class TranslationExtractorService:
    """翻译提取器领域服务"""

    def __init__(self):
        self._format_validators = {
            FileType.JSON: self._validate_json_format,
            FileType.PROPERTIES: self._validate_properties_format,
            FileType.YAML: self._validate_yaml_format,
        }

        self._extractors = {
            FileType.JSON: self._extract_from_json,
            FileType.PROPERTIES: self._extract_from_properties,
            FileType.YAML: self._extract_from_yaml,
        }

    async def extract_translations(
        self,
        file_content: bytes,
        file_path: str,
        language_code: LanguageCode,
        file_type: FileType,
        mod_id: ModId | None = None,
    ) -> ExtractionResult:
        """
        从语言文件中提取翻译条目

        Args:
            file_content: 文件内容
            file_path: 文件路径（用于记录）
            language_code: 语言代码
            file_type: 文件类型
            mod_id: 模组ID（可选，用于验证翻译键）

        Returns:
            ExtractionResult: 提取结果
        """
        logger.info(f"开始提取翻译: {file_path} ({language_code.code})")

        extraction_errors = []

        try:
            # 验证文件格式
            format_validation = await self._validate_file_format(
                file_content, file_type
            )
            if not format_validation.is_valid:
                extraction_errors.extend(format_validation.errors)

            # 提取翻译条目
            extractor = self._extractors.get(file_type)
            if not extractor:
                raise ValueError(f"不支持的文件类型: {file_type}")

            raw_entries = await extractor(file_content, language_code)

            # 处理和验证提取的条目
            (
                processed_entries,
                processing_errors,
            ) = await self._process_extracted_entries(
                raw_entries, mod_id, language_code
            )
            extraction_errors.extend(processing_errors)

            # 计算统计信息
            statistics = self._calculate_extraction_statistics(
                raw_entries, processed_entries, extraction_errors
            )

            return ExtractionResult(
                entries=processed_entries,
                source_file_path=file_path,
                language_code=language_code,
                file_type=file_type,
                extraction_errors=extraction_errors,
                statistics=statistics,
            )

        except Exception as e:
            logger.error(f"提取翻译失败: {file_path} - {str(e)}")
            extraction_errors.append(f"提取失败: {str(e)}")

            return ExtractionResult(
                entries={},
                source_file_path=file_path,
                language_code=language_code,
                file_type=file_type,
                extraction_errors=extraction_errors,
                statistics=ExtractionStatistics(0, 0, 0, 0, 0, len(extraction_errors)),
            )

    async def _validate_file_format(
        self, content: bytes, file_type: FileType
    ) -> "FormatValidationResult":
        """验证文件格式"""
        validator = self._format_validators.get(file_type)
        if not validator:
            return FormatValidationResult(False, [f"不支持的文件类型: {file_type}"])

        return await validator(content)

    async def _validate_json_format(self, content: bytes) -> "FormatValidationResult":
        """验证JSON格式"""
        try:
            text = content.decode("utf-8")
            data = json.loads(text)

            if not isinstance(data, dict):
                return FormatValidationResult(False, ["JSON根元素必须是对象"])

            # 检查键值对格式
            issues = []
            for key, value in data.items():
                if not isinstance(key, str):
                    issues.append(f"无效的键类型: {type(key)}")
                if not isinstance(value, str):
                    issues.append(f"键 '{key}' 的值不是字符串类型: {type(value)}")

            return FormatValidationResult(len(issues) == 0, issues)

        except UnicodeDecodeError:
            return FormatValidationResult(False, ["文件编码不是UTF-8"])
        except json.JSONDecodeError as e:
            return FormatValidationResult(False, [f"JSON格式错误: {str(e)}"])

    async def _validate_properties_format(
        self, content: bytes
    ) -> "FormatValidationResult":
        """验证Properties格式"""
        try:
            text = content.decode("utf-8", errors="ignore")
            lines = text.split("\n")

            issues = []
            for i, line in enumerate(lines, 1):
                line = line.strip()
                if not line or line.startswith("#"):
                    continue

                if "=" not in line:
                    issues.append(f"第{i}行: 缺少等号分隔符")
                    continue

                key, value = line.split("=", 1)
                if not key.strip():
                    issues.append(f"第{i}行: 键不能为空")

            return FormatValidationResult(len(issues) == 0, issues)

        except Exception as e:
            return FormatValidationResult(False, [f"Properties格式验证失败: {str(e)}"])

    async def _validate_yaml_format(self, content: bytes) -> "FormatValidationResult":
        """验证YAML格式"""
        try:
            import yaml

            text = content.decode("utf-8")
            data = yaml.safe_load(text)

            if not isinstance(data, dict):
                return FormatValidationResult(False, ["YAML根元素必须是对象"])

            return FormatValidationResult(True, [])

        except ImportError:
            return FormatValidationResult(False, ["YAML支持未安装"])
        except yaml.YAMLError as e:
            return FormatValidationResult(False, [f"YAML格式错误: {str(e)}"])
        except UnicodeDecodeError:
            return FormatValidationResult(False, ["文件编码不是UTF-8"])

    async def _extract_from_json(
        self, content: bytes, language_code: LanguageCode
    ) -> dict[str, str]:
        """从JSON文件提取翻译条目"""
        try:
            text = content.decode("utf-8")
            data = json.loads(text)

            if not isinstance(data, dict):
                raise ValueError("JSON根元素不是对象")

            # 递归展开嵌套的JSON结构
            flattened = self._flatten_json_dict(data)

            return flattened

        except Exception as e:
            logger.error(f"JSON提取失败: {str(e)}")
            raise

    async def _extract_from_properties(
        self, content: bytes, language_code: LanguageCode
    ) -> dict[str, str]:
        """从Properties文件提取翻译条目"""
        try:
            text = content.decode("utf-8", errors="ignore")
            lines = text.split("\n")

            entries = {}
            for line in lines:
                line = line.strip()

                # 跳过空行和注释行
                if not line or line.startswith("#"):
                    continue

                # 处理等号分隔的键值对
                if "=" in line:
                    key, value = line.split("=", 1)
                    key = key.strip()
                    value = value.strip()

                    # 处理转义字符
                    value = self._unescape_properties_value(value)

                    if key:  # 确保键不为空
                        entries[key] = value

            return entries

        except Exception as e:
            logger.error(f"Properties提取失败: {str(e)}")
            raise

    async def _extract_from_yaml(
        self, content: bytes, language_code: LanguageCode
    ) -> dict[str, str]:
        """从YAML文件提取翻译条目"""
        try:
            import yaml

            text = content.decode("utf-8")
            data = yaml.safe_load(text)

            if not isinstance(data, dict):
                raise ValueError("YAML根元素不是对象")

            # 递归展开嵌套的YAML结构
            flattened = self._flatten_yaml_dict(data)

            return flattened

        except ImportError:
            raise ValueError("YAML支持未安装，请安装PyYAML")
        except Exception as e:
            logger.error(f"YAML提取失败: {str(e)}")
            raise

    def _flatten_json_dict(
        self, data: dict[str, Any], prefix: str = ""
    ) -> dict[str, str]:
        """递归展开嵌套的JSON字典"""
        result = {}

        for key, value in data.items():
            full_key = f"{prefix}.{key}" if prefix else key

            if isinstance(value, dict):
                # 递归处理嵌套字典
                result.update(self._flatten_json_dict(value, full_key))
            elif isinstance(value, str):
                result[full_key] = value
            else:
                # 非字符串值转换为字符串
                result[full_key] = str(value)
                logger.warning(f"键 '{full_key}' 的值不是字符串，已转换: {type(value)}")

        return result

    def _flatten_yaml_dict(
        self, data: dict[str, Any], prefix: str = ""
    ) -> dict[str, str]:
        """递归展开嵌套的YAML字典"""
        result = {}

        for key, value in data.items():
            full_key = f"{prefix}.{key}" if prefix else key

            if isinstance(value, dict):
                result.update(self._flatten_yaml_dict(value, full_key))
            elif isinstance(value, list | tuple):
                # 处理数组类型
                for i, item in enumerate(value):
                    if isinstance(item, str):
                        result[f"{full_key}[{i}]"] = item
                    else:
                        result[f"{full_key}[{i}]"] = str(item)
            elif isinstance(value, str):
                result[full_key] = value
            else:
                result[full_key] = str(value)

        return result

    def _unescape_properties_value(self, value: str) -> str:
        """处理Properties文件中的转义字符"""
        # 处理常见的转义字符
        replacements = {
            "\\\\n": "\n",
            "\\\\t": "\t",
            "\\\\r": "\r",
            '\\\\"': '"',
            "\\\\'": "'",
            "\\\\\\\\": "\\\\",
        }

        for escaped, unescaped in replacements.items():
            value = value.replace(escaped, unescaped)

        return value

    async def _process_extracted_entries(
        self,
        raw_entries: dict[str, str],
        mod_id: ModId | None,
        language_code: LanguageCode,
    ) -> tuple[dict[TranslationKey, TranslationEntry], list[str]]:
        """处理和验证提取的条目"""
        processed_entries = {}
        errors = []
        seen_keys = set()

        for raw_key, raw_value in raw_entries.items():
            try:
                # 验证和清理翻译键
                cleaned_key = self._clean_translation_key(raw_key)
                if not cleaned_key:
                    errors.append(f"无效的翻译键: '{raw_key}'")
                    continue

                # 创建翻译键对象
                translation_key = TranslationKey(cleaned_key)

                # 检查重复键
                if translation_key in seen_keys:
                    errors.append(f"重复的翻译键: '{cleaned_key}'")
                    continue
                seen_keys.add(translation_key)

                # 验证模组ID匹配（如果提供）
                if mod_id and not self._is_key_valid_for_mod(translation_key, mod_id):
                    logger.warning(f"翻译键 '{cleaned_key}' 可能不属于模组 '{mod_id}'")

                # 清理翻译值
                cleaned_value = self._clean_translation_value(raw_value)

                # 确定翻译状态
                status = self._determine_translation_status(
                    cleaned_value, language_code
                )

                # 创建翻译条目
                entry = TranslationEntry(
                    key=translation_key,
                    value=cleaned_value,
                    original_value=cleaned_value,  # 对于新提取的条目，original等于current
                    status=status,
                )

                processed_entries[translation_key] = entry

            except Exception as e:
                errors.append(f"处理条目 '{raw_key}' 失败: {str(e)}")
                continue

        return processed_entries, errors

    def _clean_translation_key(self, key: str) -> str:
        """清理翻译键"""
        if not key:
            return ""

        # 移除前后空白
        cleaned = key.strip()

        # 验证键格式（基本验证）
        if not re.match(r"^[a-zA-Z0-9._-]+$", cleaned):
            logger.warning(f"翻译键包含特殊字符: '{cleaned}'")

        return cleaned

    def _clean_translation_value(self, value: str) -> str:
        """清理翻译值"""
        if not isinstance(value, str):
            return str(value)

        # 移除前后空白但保留内部格式
        cleaned = value.strip()

        # 处理Minecraft特有的格式代码
        # 保留颜色代码如 §a, §c, §r 等
        # 保留格式化占位符如 %s, %d, {0}, {player} 等

        return cleaned

    def _determine_translation_status(
        self, value: str, language_code: LanguageCode
    ) -> TranslationStatus:
        """根据语言和内容确定翻译状态"""
        if not value:
            return TranslationStatus.UNTRANSLATED

        if language_code.is_english():
            # 英文视为原文
            return TranslationStatus.UNTRANSLATED
        else:
            # 非英文且有内容视为已翻译
            return TranslationStatus.TRANSLATED

    def _is_key_valid_for_mod(self, key: TranslationKey, mod_id: ModId) -> bool:
        """检查翻译键是否属于指定模组"""
        # 检查翻译键中的模组ID是否匹配
        key_mod_id = key.mod_id

        # 完全匹配
        if key_mod_id == mod_id.value:
            return True

        # 某些翻译键可能使用minecraft作为命名空间
        if key_mod_id == "minecraft":
            return True

        # 如果翻译键没有明确的模组ID，也认为是有效的
        if key.type in ["gui", "config", "tooltip"] and key_mod_id == "unknown":
            return True

        return False

    def _calculate_extraction_statistics(
        self,
        raw_entries: dict[str, str],
        processed_entries: dict[TranslationKey, TranslationEntry],
        errors: list[str],
    ) -> ExtractionStatistics:
        """计算提取统计信息"""
        total_entries = len(raw_entries)
        valid_entries = len(processed_entries)
        invalid_entries = total_entries - valid_entries

        # 计算空值数量
        empty_values = sum(1 for entry in processed_entries.values() if not entry.value)

        # 从错误信息中统计重复键
        duplicate_keys = len([e for e in errors if "重复的翻译键" in e])

        # 格式问题数量
        format_issues = len(
            [e for e in errors if any(word in e for word in ["格式", "转义", "编码"])]
        )

        return ExtractionStatistics(
            total_entries=total_entries,
            valid_entries=valid_entries,
            invalid_entries=invalid_entries,
            duplicate_keys=duplicate_keys,
            empty_values=empty_values,
            format_issues=format_issues,
        )

    async def extract_translation_keys_only(
        self, file_content: bytes, file_type: FileType
    ) -> set[str]:
        """仅提取翻译键，不处理值（用于快速扫描）"""
        try:
            if file_type == FileType.JSON:
                data = json.loads(file_content.decode("utf-8"))
                return set(self._flatten_json_dict(data).keys())

            elif file_type == FileType.PROPERTIES:
                text = file_content.decode("utf-8", errors="ignore")
                keys = set()
                for line in text.split("\n"):
                    line = line.strip()
                    if line and not line.startswith("#") and "=" in line:
                        key = line.split("=", 1)[0].strip()
                        if key:
                            keys.add(key)
                return keys

            elif file_type == FileType.YAML:
                import yaml

                data = yaml.safe_load(file_content.decode("utf-8"))
                return set(self._flatten_yaml_dict(data).keys())

            else:
                return set()

        except Exception as e:
            logger.error(f"提取翻译键失败: {str(e)}")
            return set()


@dataclass
class FormatValidationResult:
    """格式验证结果"""

    is_valid: bool
    errors: list[str]
