"""
应用异常

定义应用层的异常类
"""

from .base_exception import BaseAppError, BusinessError

# For backward compatibility
BusinessException = BusinessError

__all__ = ["BaseAppError", "BusinessException", "BusinessError"]
