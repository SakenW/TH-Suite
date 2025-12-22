"""
值对象基类

DDD中的值对象（Value Object）基类
值对象的特征：
- 不可变性
- 相等性基于属性值而非标识
- 无标识
"""

from abc import ABC
from typing import Any


class ValueObject(ABC):
    """值对象基类"""

    def __init__(self, **kwargs):
        # 设置属性并冻结对象
        for key, value in kwargs.items():
            object.__setattr__(self, key, value)

        # 计算哈希值（用于比较和缓存）
        self._hash = self._compute_hash()

    def __setattr__(self, name: str, value: Any) -> None:
        """禁止修改属性（不可变性）"""
        if hasattr(self, "_hash"):
            raise AttributeError(f"值对象是不可变的，无法设置属性 '{name}'")
        object.__setattr__(self, name, value)

    def __delattr__(self, name: str) -> None:
        """禁止删除属性"""
        raise AttributeError("值对象是不可变的，无法删除属性")

    def __eq__(self, other) -> bool:
        """基于属性值的相等性比较"""
        if not isinstance(other, self.__class__):
            return False

        return self._get_attributes() == other._get_attributes()

    def __hash__(self) -> int:
        """基于属性值的哈希"""
        return self._hash

    def __repr__(self) -> str:
        """字符串表示"""
        attrs = self._get_attributes()
        attr_str = ", ".join(f"{k}={repr(v)}" for k, v in attrs.items())
        return f"{self.__class__.__name__}({attr_str})"

    def __str__(self) -> str:
        """用户友好的字符串表示"""
        return self.__repr__()

    def _get_attributes(self) -> dict[str, Any]:
        """获取所有属性（排除私有属性）"""
        return {
            key: value
            for key, value in self.__dict__.items()
            if not key.startswith("_")
        }

    def _compute_hash(self) -> int:
        """计算对象哈希值"""
        attrs = self._get_attributes()

        # 创建可序列化的属性元组
        hashable_attrs = []
        for key in sorted(attrs.keys()):
            value = attrs[key]
            try:
                # 尝试创建哈希
                hash(value)
                hashable_attrs.append((key, value))
            except TypeError:
                # 如果值不可哈希，使用字符串表示
                hashable_attrs.append((key, str(value)))

        return hash(tuple(hashable_attrs))

    def to_dict(self) -> dict[str, Any]:
        """转换为字典"""
        return self._get_attributes().copy()

    def copy(self, **changes) -> "ValueObject":
        """创建修改后的副本"""
        attrs = self._get_attributes()
        attrs.update(changes)
        return self.__class__(**attrs)


# 常用的值对象实现


class Money(ValueObject):
    """货币值对象"""

    def __init__(self, amount: float, currency: str = "USD"):
        if amount < 0:
            raise ValueError("金额不能为负数")
        if not currency or len(currency) != 3:
            raise ValueError("货币代码必须是3位字符")

        super().__init__(amount=amount, currency=currency.upper())

    def add(self, other: "Money") -> "Money":
        """货币相加"""
        if not isinstance(other, Money):
            raise TypeError("只能与其他Money对象相加")
        if self.currency != other.currency:
            raise ValueError("不能将不同货币相加")

        return Money(self.amount + other.amount, self.currency)

    def multiply(self, factor: float) -> "Money":
        """货币乘法"""
        return Money(self.amount * factor, self.currency)


class EmailAddress(ValueObject):
    """邮箱地址值对象"""

    def __init__(self, email: str):
        import re

        if not email:
            raise ValueError("邮箱地址不能为空")

        # 简单的邮箱验证
        email_pattern = r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$"
        if not re.match(email_pattern, email):
            raise ValueError(f"无效的邮箱地址: {email}")

        super().__init__(email=email.lower())


class DateRange(ValueObject):
    """日期范围值对象"""

    def __init__(self, start_date, end_date):
        if start_date > end_date:
            raise ValueError("开始日期不能晚于结束日期")

        super().__init__(start_date=start_date, end_date=end_date)

    def contains(self, check_date) -> bool:
        """检查日期是否在范围内"""
        return self.start_date <= check_date <= self.end_date

    def overlaps(self, other: "DateRange") -> bool:
        """检查是否与另一个日期范围重叠"""
        return self.start_date <= other.end_date and other.start_date <= self.end_date
