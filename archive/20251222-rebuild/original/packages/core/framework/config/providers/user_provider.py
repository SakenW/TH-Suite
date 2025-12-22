"""
用户自定义配置提供者

从用户设置文件中加载配置
"""

import json
from pathlib import Path
from typing import Any

from ..config_manager import IConfigProvider


class UserConfigProvider(IConfigProvider):
    """用户自定义配置提供者"""

    def __init__(self, user_config_dir: Path = None):
        if user_config_dir is None:
            user_config_dir = Path.home() / ".th-suite"

        self.user_config_dir = Path(user_config_dir)
        self.config_file = self.user_config_dir / "config.json"

    def load_config(self) -> dict[str, Any]:
        """从用户配置文件加载配置"""
        if not self.config_file.exists():
            return {}

        try:
            with open(self.config_file, encoding="utf-8") as f:
                return json.load(f)
        except Exception as e:
            print(f"加载用户配置文件 {self.config_file} 失败: {e}")
            return {}

    def save_config(self, config: dict[str, Any]) -> None:
        """保存用户配置"""
        try:
            # 确保目录存在
            self.user_config_dir.mkdir(parents=True, exist_ok=True)

            with open(self.config_file, "w", encoding="utf-8") as f:
                json.dump(config, f, indent=2, ensure_ascii=False)
        except Exception as e:
            print(f"保存用户配置文件 {self.config_file} 失败: {e}")

    def get_priority(self) -> int:
        """用户配置优先级较高"""
        return 80

    def supports_watch(self) -> bool:
        """用户配置支持监视变化"""
        return True
