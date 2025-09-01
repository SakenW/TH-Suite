"""
配置管理器

负责加载、管理和热更新配置
"""

import threading
from abc import ABC, abstractmethod
from datetime import datetime
from pathlib import Path
from typing import Any, TypeVar

from .settings import ConfigValue, Settings

T = TypeVar("T")


class IConfigProvider(ABC):
    """配置提供者接口"""

    @abstractmethod
    def load_config(self) -> dict[str, Any]:
        """加载配置"""
        pass

    @abstractmethod
    def get_priority(self) -> int:
        """获取优先级（数字越大优先级越高）"""
        pass

    @abstractmethod
    def supports_watch(self) -> bool:
        """是否支持监视变化"""
        pass

    def watch_changes(self, callback: callable) -> None:
        """监视配置变化"""
        pass


class ConfigManager:
    """配置管理器"""

    def __init__(self, settings: Settings | None = None):
        self._settings = settings or Settings()
        self._providers: list[IConfigProvider] = []
        self._config_cache: dict[str, Any] = {}
        self._lock = threading.RLock()
        self._last_reload = datetime.now()
        self._reload_interval = 60  # 秒
        self._auto_reload = True
        self._change_callbacks: list[callable] = []

    def add_provider(self, provider: IConfigProvider) -> "ConfigManager":
        """添加配置提供者"""
        with self._lock:
            self._providers.append(provider)
            # 按优先级排序
            self._providers.sort(key=lambda p: p.get_priority(), reverse=True)
        return self

    def load_config(self) -> None:
        """加载配置"""
        with self._lock:
            # 从所有提供者加载配置
            merged_config = {}

            # 按优先级从低到高合并配置
            for provider in reversed(self._providers):
                try:
                    config = provider.load_config()
                    merged_config.update(config)
                except Exception as e:
                    print(f"加载配置提供者 {provider} 失败: {e}")

            # 应用配置到Settings
            self._apply_config(merged_config)
            self._config_cache = merged_config
            self._last_reload = datetime.now()

            # 通知配置变化
            self._notify_changes()

    def _apply_config(self, config: dict[str, Any]) -> None:
        """应用配置到Settings"""
        config_values = self._settings.get_all_config_values()

        for name, config_value in config_values.items():
            key = config_value.key

            # 查找配置值
            value = None
            if key in config:
                value = config[key]
            elif key.upper() in config:
                value = config[key.upper()]
            elif key.lower() in config:
                value = config[key.lower()]

            if value is not None:
                try:
                    # 类型转换
                    converted_value = self._convert_value(value, config_value)
                    config_value.set_value(converted_value)
                except Exception as e:
                    print(f"设置配置项 {key} = {value} 失败: {e}")

    def _convert_value(self, value: Any, config_value: ConfigValue[T]) -> T:
        """转换配置值类型"""
        if value is None:
            return None

        # 获取目标类型
        target_type = (
            type(config_value.default) if config_value.default is not None else str
        )

        # 特殊处理
        if isinstance(target_type, type) and issubclass(target_type, bool):
            if isinstance(value, str):
                return value.lower() in ("true", "1", "yes", "on")
            return bool(value)
        elif target_type == Path:
            return Path(str(value))
        elif target_type in (int, float):
            return target_type(value)

        return value

    def get_value(self, key: str, default: Any = None) -> Any:
        """获取配置值"""
        # 检查是否需要重新加载
        if self._auto_reload and self._should_reload():
            self.reload_config()

        with self._lock:
            return self._config_cache.get(key, default)

    def get_setting(self, setting_name: str) -> Any:
        """获取设置值"""
        if hasattr(self._settings, setting_name):
            config_value = getattr(self._settings, setting_name)
            if isinstance(config_value, ConfigValue):
                return config_value.get_value()
        return None

    def set_value(self, key: str, value: Any) -> None:
        """设置配置值"""
        with self._lock:
            self._config_cache[key] = value

            # 更新Settings
            config_values = self._settings.get_all_config_values()
            for name, config_value in config_values.items():
                if config_value.key == key:
                    try:
                        converted_value = self._convert_value(value, config_value)
                        config_value.set_value(converted_value)
                    except Exception as e:
                        print(f"设置配置项 {key} = {value} 失败: {e}")
                    break

        self._notify_changes()

    def reload_config(self) -> None:
        """重新加载配置"""
        self.load_config()

    def _should_reload(self) -> bool:
        """检查是否应该重新加载"""
        return (datetime.now() - self._last_reload).seconds >= self._reload_interval

    def set_auto_reload(self, enabled: bool, interval: int = 60) -> None:
        """设置自动重载"""
        self._auto_reload = enabled
        self._reload_interval = interval

    def add_change_callback(self, callback: callable) -> None:
        """添加配置变化回调"""
        self._change_callbacks.append(callback)

    def _notify_changes(self) -> None:
        """通知配置变化"""
        for callback in self._change_callbacks:
            try:
                callback(self._config_cache)
            except Exception as e:
                print(f"配置变化回调执行失败: {e}")

    def validate_config(self) -> list[str]:
        """验证配置"""
        return self._settings.validate_all()

    def get_config_dict(self) -> dict[str, Any]:
        """获取配置字典"""
        with self._lock:
            return self._config_cache.copy()

    def get_settings(self) -> Settings:
        """获取设置对象"""
        return self._settings
