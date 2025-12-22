"""
质量门禁模块

提供翻译质量验证和控制功能
"""

from .gate import QualityGate
from .validators import (
    ColorCodeValidator,
    EmptyValueValidator,
    FormatValidator,
    LengthRatioValidator,
    LineBreakValidator,
    PlaceholderValidator,
    QualityValidator,
    ValidationLevel,
    ValidationResult,
)

__all__ = [
    # 基础类
    "QualityValidator",
    "ValidationResult",
    "ValidationLevel",
    # 验证器
    "PlaceholderValidator",
    "ColorCodeValidator",
    "LengthRatioValidator",
    "EmptyValueValidator",
    "FormatValidator",
    "LineBreakValidator",
    # 门禁服务
    "QualityGate",
]
