"""
环境变量配置提供者

从环境变量中加载配置
"""

import os
from typing import Any

from ..config_manager import IConfigProvider


class EnvironmentConfigProvider(IConfigProvider):
    """环境变量配置提供者"""

    def __init__(self, prefix: str = "TH_"):
        self.prefix = prefix

    def load_config(self) -> dict[str, Any]:
        """从环境变量加载配置"""
        config = {}

        for key, value in os.environ.items():
            if self.prefix and key.startswith(self.prefix):
                # 移除前缀
                config_key = key[len(self.prefix) :]
                config[config_key] = value
            elif not self.prefix:
                config[key] = value

        return config

    def get_priority(self) -> int:
        """环境变量优先级最高"""
        return 100

    def supports_watch(self) -> bool:
        """环境变量不支持监视变化"""
        return False
