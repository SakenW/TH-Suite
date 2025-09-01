"""
应用异常基类

定义应用层的异常类型
"""

from typing import Any


class BaseException(Exception):
    """应用异常基类"""

    def __init__(
        self, message: str, error_code: str = None, details: dict[str, Any] = None
    ):
        super().__init__(message)
        self.message = message
        self.error_code = error_code
        self.details = details or {}


class BaseError(BaseException):
    """应用异常基类"""
    pass


class BusinessException(BaseException):
    """业务异常"""

    def __init__(
        self,
        message: str,
        error_code: str = "BUSINESS_ERROR",
        details: dict[str, Any] = None,
    ):
        super().__init__(message, error_code, details)


class BusinessError(BusinessException):
    """业务异常"""
    pass


class ValidationException(BaseException):
    """验证异常"""

    def __init__(self, message: str, field_errors: dict[str, list] = None):
        super().__init__(message, "VALIDATION_ERROR")
        self.field_errors = field_errors or {}
