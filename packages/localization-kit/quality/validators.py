"""
质量验证器 - 翻译质量检查

根据白皮书定义的质量门禁：
- 占位符一致性
- 格式校验
- 颜色码校验
- 长度比校验
- 禁止空值覆盖
"""

import json
import re
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class ValidationLevel(Enum):
    """验证级别"""

    INFO = "info"  # 信息
    WARNING = "warning"  # 警告
    ERROR = "error"  # 错误（阻止应用）


@dataclass
class ValidationResult:
    """验证结果"""

    validator: str  # 验证器名称
    passed: bool  # 是否通过
    level: ValidationLevel  # 级别
    message: str  # 消息
    details: dict[str, Any] = field(default_factory=dict)

    @property
    def is_blocking(self) -> bool:
        """是否为阻塞性错误"""
        return not self.passed and self.level == ValidationLevel.ERROR


class QualityValidator(ABC):
    """质量验证器基类"""

    @property
    @abstractmethod
    def name(self) -> str:
        """验证器名称"""
        pass

    @abstractmethod
    def validate(
        self,
        key: str,
        source_value: str,
        target_value: str,
        context: dict[str, Any] | None = None,
    ) -> ValidationResult:
        """
        验证单个翻译条目

        Args:
            key: 翻译键
            source_value: 源语言值
            target_value: 目标语言值
            context: 额外上下文

        Returns:
            验证结果
        """
        pass

    def validate_batch(
        self,
        entries: dict[str, str],
        source_entries: dict[str, str] | None = None,
        context: dict[str, Any] | None = None,
    ) -> list[ValidationResult]:
        """
        批量验证

        Args:
            entries: 目标翻译条目
            source_entries: 源翻译条目（如果有）
            context: 额外上下文

        Returns:
            验证结果列表
        """
        results = []

        for key, target_value in entries.items():
            source_value = source_entries.get(key, "") if source_entries else ""
            result = self.validate(key, source_value, target_value, context)
            results.append(result)

        return results


class PlaceholderValidator(QualityValidator):
    """
    占位符一致性验证器

    确保翻译前后的占位符数量和类型一致
    """

    @property
    def name(self) -> str:
        return "placeholder_consistency"

    def __init__(self):
        # Minecraft 常见占位符模式
        self.patterns = [
            (r"%s", "string_format"),  # Java String.format
            (r"%d", "decimal_format"),  # 十进制数
            (r"%\d+\$s", "indexed_string"),  # 索引格式 %1$s
            (r"%\d+\$d", "indexed_decimal"),  # 索引十进制
            (r"\{(\w+)\}", "named_placeholder"),  # {name}
            (r"\{\d+\}", "indexed_placeholder"),  # {0}, {1}
        ]

    def extract_placeholders(self, text: str) -> dict[str, int]:
        """提取占位符"""
        placeholders = {}

        for pattern, ptype in self.patterns:
            matches = re.findall(pattern, text)
            if matches:
                placeholders[ptype] = len(matches)

        return placeholders

    def validate(
        self,
        key: str,
        source_value: str,
        target_value: str,
        context: dict[str, Any] | None = None,
    ) -> ValidationResult:
        source_placeholders = self.extract_placeholders(source_value)
        target_placeholders = self.extract_placeholders(target_value)

        # 比较占位符
        missing = []
        extra = []

        for ptype, count in source_placeholders.items():
            target_count = target_placeholders.get(ptype, 0)
            if target_count < count:
                missing.append(f"{ptype}({count - target_count})")
            elif target_count > count:
                extra.append(f"{ptype}({target_count - count})")

        for ptype in target_placeholders:
            if ptype not in source_placeholders:
                extra.append(f"{ptype}({target_placeholders[ptype]})")

        if missing or extra:
            message_parts = []
            if missing:
                message_parts.append(f"缺少: {', '.join(missing)}")
            if extra:
                message_parts.append(f"多余: {', '.join(extra)}")

            return ValidationResult(
                validator=self.name,
                passed=False,
                level=ValidationLevel.ERROR,
                message=f"占位符不一致 - {'; '.join(message_parts)}",
                details={
                    "key": key,
                    "source_placeholders": source_placeholders,
                    "target_placeholders": target_placeholders,
                    "missing": missing,
                    "extra": extra,
                },
            )

        return ValidationResult(
            validator=self.name,
            passed=True,
            level=ValidationLevel.INFO,
            message="占位符一致",
            details={"key": key},
        )


class ColorCodeValidator(QualityValidator):
    """
    颜色码验证器

    确保 Minecraft 颜色码（§）的正确使用
    """

    @property
    def name(self) -> str:
        return "color_code"

    def __init__(self):
        # Minecraft 颜色码
        self.color_codes = "0123456789abcdefklmnor"
        self.color_pattern = r"§[" + self.color_codes + "]"

    def extract_color_codes(self, text: str) -> list[str]:
        """提取颜色码"""
        return re.findall(self.color_pattern, text)

    def validate(
        self,
        key: str,
        source_value: str,
        target_value: str,
        context: dict[str, Any] | None = None,
    ) -> ValidationResult:
        source_codes = self.extract_color_codes(source_value)
        target_codes = self.extract_color_codes(target_value)

        # 检查无效的颜色码
        invalid_codes = re.findall(r"§[^" + self.color_codes + "]", target_value)
        if invalid_codes:
            return ValidationResult(
                validator=self.name,
                passed=False,
                level=ValidationLevel.ERROR,
                message=f"无效的颜色码: {', '.join(invalid_codes)}",
                details={"key": key, "invalid_codes": invalid_codes},
            )

        # 检查颜色码数量
        if len(source_codes) != len(target_codes):
            return ValidationResult(
                validator=self.name,
                passed=False,
                level=ValidationLevel.WARNING,
                message=f"颜色码数量不一致 (源: {len(source_codes)}, 目标: {len(target_codes)})",
                details={
                    "key": key,
                    "source_count": len(source_codes),
                    "target_count": len(target_codes),
                },
            )

        return ValidationResult(
            validator=self.name,
            passed=True,
            level=ValidationLevel.INFO,
            message="颜色码正确",
            details={"key": key},
        )


class LengthRatioValidator(QualityValidator):
    """
    长度比验证器

    检查翻译长度是否合理
    """

    @property
    def name(self) -> str:
        return "length_ratio"

    def __init__(self, min_ratio: float = 0.5, max_ratio: float = 2.0):
        """
        初始化长度比验证器

        Args:
            min_ratio: 最小长度比
            max_ratio: 最大长度比
        """
        self.min_ratio = min_ratio
        self.max_ratio = max_ratio

    def validate(
        self,
        key: str,
        source_value: str,
        target_value: str,
        context: dict[str, Any] | None = None,
    ) -> ValidationResult:
        if not source_value:
            # 没有源文本，跳过验证
            return ValidationResult(
                validator=self.name,
                passed=True,
                level=ValidationLevel.INFO,
                message="无源文本，跳过长度验证",
                details={"key": key},
            )

        source_len = len(source_value)
        target_len = len(target_value)

        if source_len == 0:
            ratio = float("inf") if target_len > 0 else 1.0
        else:
            ratio = target_len / source_len

        if ratio < self.min_ratio:
            return ValidationResult(
                validator=self.name,
                passed=False,
                level=ValidationLevel.WARNING,
                message=f"翻译过短 (比例: {ratio:.2f}, 最小: {self.min_ratio})",
                details={
                    "key": key,
                    "source_length": source_len,
                    "target_length": target_len,
                    "ratio": ratio,
                },
            )

        if ratio > self.max_ratio:
            return ValidationResult(
                validator=self.name,
                passed=False,
                level=ValidationLevel.WARNING,
                message=f"翻译过长 (比例: {ratio:.2f}, 最大: {self.max_ratio})",
                details={
                    "key": key,
                    "source_length": source_len,
                    "target_length": target_len,
                    "ratio": ratio,
                },
            )

        return ValidationResult(
            validator=self.name,
            passed=True,
            level=ValidationLevel.INFO,
            message=f"长度比合理 ({ratio:.2f})",
            details={"key": key, "ratio": ratio},
        )


class EmptyValueValidator(QualityValidator):
    """
    空值验证器

    防止非空值被空串替换
    """

    @property
    def name(self) -> str:
        return "empty_value"

    def validate(
        self,
        key: str,
        source_value: str,
        target_value: str,
        context: dict[str, Any] | None = None,
    ) -> ValidationResult:
        # 如果源值非空但目标值为空
        if source_value and not target_value:
            return ValidationResult(
                validator=self.name,
                passed=False,
                level=ValidationLevel.ERROR,
                message="非空值被空串替换",
                details={
                    "key": key,
                    "source_value": source_value[:50] + "..."
                    if len(source_value) > 50
                    else source_value,
                },
            )

        # 如果目标值只包含空白字符
        if (
            target_value
            and target_value.strip() == ""
            and source_value
            and source_value.strip() != ""
        ):
            return ValidationResult(
                validator=self.name,
                passed=False,
                level=ValidationLevel.WARNING,
                message="翻译只包含空白字符",
                details={"key": key},
            )

        return ValidationResult(
            validator=self.name,
            passed=True,
            level=ValidationLevel.INFO,
            message="值非空",
            details={"key": key},
        )


class FormatValidator(QualityValidator):
    """
    格式验证器

    验证 JSON 或其他格式的正确性
    """

    @property
    def name(self) -> str:
        return "format"

    def validate(
        self,
        key: str,
        source_value: str,
        target_value: str,
        context: dict[str, Any] | None = None,
    ) -> ValidationResult:
        # 检查是否包含未转义的引号
        if '"' in target_value:
            # 检查是否在 JSON 字符串中正确转义
            try:
                # 尝试将值包装在 JSON 中
                test_json = f'{{"test": "{target_value}"}}'
                json.loads(test_json)
            except json.JSONDecodeError:
                return ValidationResult(
                    validator=self.name,
                    passed=False,
                    level=ValidationLevel.ERROR,
                    message="包含未转义的引号",
                    details={"key": key},
                )

        # 检查控制字符
        control_chars = [chr(i) for i in range(0, 32) if chr(i) not in "\n\r\t"]
        for char in control_chars:
            if char in target_value:
                return ValidationResult(
                    validator=self.name,
                    passed=False,
                    level=ValidationLevel.ERROR,
                    message=f"包含非法控制字符 (ASCII {ord(char)})",
                    details={"key": key, "char_code": ord(char)},
                )

        return ValidationResult(
            validator=self.name,
            passed=True,
            level=ValidationLevel.INFO,
            message="格式正确",
            details={"key": key},
        )


class LineBreakValidator(QualityValidator):
    """
    换行符验证器

    确保换行符的一致性
    """

    @property
    def name(self) -> str:
        return "line_break"

    def validate(
        self,
        key: str,
        source_value: str,
        target_value: str,
        context: dict[str, Any] | None = None,
    ) -> ValidationResult:
        source_breaks = source_value.count("\n")
        target_breaks = target_value.count("\n")

        # 严格模式：换行符数量必须一致
        if abs(source_breaks - target_breaks) > 2:
            return ValidationResult(
                validator=self.name,
                passed=False,
                level=ValidationLevel.WARNING,
                message=f"换行符数量差异过大 (源: {source_breaks}, 目标: {target_breaks})",
                details={
                    "key": key,
                    "source_breaks": source_breaks,
                    "target_breaks": target_breaks,
                },
            )

        # 检查 Windows 换行符
        if "\r\n" in target_value and "\r\n" not in source_value:
            return ValidationResult(
                validator=self.name,
                passed=False,
                level=ValidationLevel.WARNING,
                message="使用了 Windows 换行符 (\\r\\n)",
                details={"key": key},
            )

        return ValidationResult(
            validator=self.name,
            passed=True,
            level=ValidationLevel.INFO,
            message="换行符正常",
            details={"key": key},
        )
