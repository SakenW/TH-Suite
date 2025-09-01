"""
验证器

提供数据验证功能
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any


@dataclass
class ValidationResult:
    """验证结果"""

    is_valid: bool
    errors: list[str]
    field_errors: dict[str, list[str]]

    def add_error(self, error: str, field: str | None = None):
        """添加错误"""
        self.is_valid = False
        self.errors.append(error)

        if field:
            if field not in self.field_errors:
                self.field_errors[field] = []
            self.field_errors[field].append(error)


class ValidationRule(ABC):
    """验证规则基类"""

    @abstractmethod
    def validate(self, value: Any, context: dict[str, Any] = None) -> ValidationResult:
        """验证值"""
        pass


class RequiredRule(ValidationRule):
    """必需字段规则"""

    def __init__(self, message: str = "This field is required"):
        self.message = message

    def validate(self, value: Any, context: dict[str, Any] = None) -> ValidationResult:
        """验证必需字段"""
        result = ValidationResult(True, [], {})

        if value is None or value == "":
            result.add_error(self.message)

        return result


class Validator:
    """验证器"""

    def __init__(self):
        self.rules: dict[str, list[ValidationRule]] = {}

    def add_rule(self, field: str, rule: ValidationRule):
        """添加验证规则"""
        if field not in self.rules:
            self.rules[field] = []
        self.rules[field].append(rule)

    def validate(self, data: dict[str, Any]) -> ValidationResult:
        """验证数据"""
        result = ValidationResult(True, [], {})

        for field, rules in self.rules.items():
            value = data.get(field)

            for rule in rules:
                rule_result = rule.validate(value, data)
                if not rule_result.is_valid:
                    result.is_valid = False
                    result.errors.extend(rule_result.errors)

                    for error in rule_result.errors:
                        result.add_error(error, field)

        return result
