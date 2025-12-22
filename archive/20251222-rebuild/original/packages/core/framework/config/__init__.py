"""
配置管理模块

提供统一的配置管理，支持：
- 多环境配置（开发、测试、生产）
- 多种配置源（环境变量、文件、用户设置）
- 热更新配置
- 配置验证和类型安全
"""

from .config_manager import ConfigManager
from .providers.env_provider import EnvironmentConfigProvider
from .providers.file_provider import FileConfigProvider
from .providers.user_provider import UserConfigProvider
from .settings import ConfigValue, Settings

__all__ = [
    "ConfigManager",
    "EnvironmentConfigProvider",
    "FileConfigProvider",
    "UserConfigProvider",
    "Settings",
    "ConfigValue",
]
