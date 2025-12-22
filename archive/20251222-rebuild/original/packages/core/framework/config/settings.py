"""
配置定义和验证

定义系统的配置结构和验证规则
"""

from __future__ import annotations

from collections.abc import Callable
from enum import Enum
from pathlib import Path
from typing import Any, TypeVar

T = TypeVar("T")


class ConfigValue[T]:
    """配置值包装器"""

    def __init__(
        self,
        key: str,
        default: T | None = None,
        description: str = "",
        required: bool = False,
        validator: Callable[[T], bool] | None = None,
    ):
        self.key = key
        self.default = default
        self.description = description
        self.required = required
        self.validator = validator
        self._value: T | None = None
        self._is_set = False

    def get_value(self) -> T:
        """获取配置值"""
        if not self._is_set and self.required and self.default is None:
            raise ValueError(f"必需的配置项 {self.key} 未设置")

        return self._value if self._is_set else self.default

    def set_value(self, value: Any) -> None:
        """设置配置值"""
        if self.validator and not self.validator(value):
            raise ValueError(f"配置项 {self.key} 的值 {value} 验证失败")

        self._value = value
        self._is_set = True

    def reset(self) -> None:
        """重置为默认值"""
        self._value = None
        self._is_set = False


class Environment(Enum):
    """环境类型"""

    DEVELOPMENT = "development"
    TESTING = "testing"
    PRODUCTION = "production"


class Settings:
    """系统配置定义"""

    def __init__(self):
        # 基础配置
        self.app_name = ConfigValue[str](
            "APP_NAME", default="TH-Suite", description="应用程序名称"
        )

        self.environment = ConfigValue[str](
            "ENVIRONMENT", default=Environment.DEVELOPMENT.value, description="运行环境"
        )

        self.debug = ConfigValue[bool]("DEBUG", default=True, description="调试模式")

        # 路径配置
        self.data_dir = ConfigValue[Path](
            "DATA_DIR", default=Path.home() / ".th-suite", description="数据目录"
        )

        self.log_dir = ConfigValue[Path](
            "LOG_DIR",
            default=Path.home() / ".th-suite" / "logs",
            description="日志目录",
        )

        self.cache_dir = ConfigValue[Path](
            "CACHE_DIR",
            default=Path.home() / ".th-suite" / "cache",
            description="缓存目录",
        )

        # 数据库配置
        self.database_url = ConfigValue[str](
            "DATABASE_URL", default="sqlite:///th-suite.db", description="数据库连接URL"
        )

        self.database_encrypt = ConfigValue[bool](
            "DATABASE_ENCRYPT", default=True, description="是否加密数据库"
        )

        # Web服务配置
        self.host = ConfigValue[str](
            "HOST", default="127.0.0.1", description="服务器主机地址"
        )

        self.port = ConfigValue[int]("PORT", default=8000, description="服务器端口")

        # Trans-Hub集成配置
        self.transhub_api_url = ConfigValue[str](
            "TRANSHUB_API_URL",
            default="https://api.trans-hub.com",
            description="Trans-Hub API地址",
        )

        self.transhub_api_key = ConfigValue[str | None](
            "TRANSHUB_API_KEY", default=None, description="Trans-Hub API密钥"
        )

        # 缓存配置
        self.cache_enabled = ConfigValue[bool](
            "CACHE_ENABLED", default=True, description="是否启用缓存"
        )

        self.cache_ttl = ConfigValue[int](
            "CACHE_TTL", default=3600, description="缓存过期时间（秒）"
        )

        # 日志配置
        self.log_level = ConfigValue[str](
            "LOG_LEVEL", default="INFO", description="日志级别"
        )

        self.log_format = ConfigValue[str](
            "LOG_FORMAT", default="console", description="日志格式（console 或 json）"
        )

        # 任务配置
        self.task_worker_count = ConfigValue[int](
            "TASK_WORKER_COUNT", default=4, description="任务工作线程数"
        )

        self.task_queue_size = ConfigValue[int](
            "TASK_QUEUE_SIZE", default=1000, description="任务队列大小"
        )

    def get_all_config_values(self) -> dict[str, ConfigValue]:
        """获取所有配置值"""
        return {
            name: getattr(self, name)
            for name in dir(self)
            if isinstance(getattr(self, name), ConfigValue)
        }

    def validate_all(self) -> list[str]:
        """验证所有配置"""
        errors = []

        for name, config_value in self.get_all_config_values().items():
            try:
                value = config_value.get_value()
                if config_value.validator and not config_value.validator(value):
                    errors.append(f"配置项 {name} 验证失败")
            except Exception as e:
                errors.append(f"配置项 {name} 错误: {e}")

        return errors

    def to_dict(self) -> dict[str, Any]:
        """转换为字典"""
        result = {}
        for name, config_value in self.get_all_config_values().items():
            try:
                result[name] = config_value.get_value()
            except Exception:
                result[name] = None
        return result
