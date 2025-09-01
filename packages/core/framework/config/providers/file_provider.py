"""
文件配置提供者

从配置文件（YAML/JSON）中加载配置
"""

import json
from pathlib import Path
from typing import Any

import yaml

from ..config_manager import IConfigProvider


class FileConfigProvider(IConfigProvider):
    """文件配置提供者"""

    def __init__(self, file_path: Path, priority: int = 50):
        self.file_path = Path(file_path)
        self._priority = priority

    def load_config(self) -> dict[str, Any]:
        """从文件加载配置"""
        if not self.file_path.exists():
            return {}

        try:
            content = self.file_path.read_text(encoding="utf-8")

            if self.file_path.suffix.lower() in [".yml", ".yaml"]:
                return yaml.safe_load(content) or {}
            elif self.file_path.suffix.lower() == ".json":
                return json.loads(content)
            else:
                # 尝试解析为JSON
                return json.loads(content)

        except Exception as e:
            print(f"加载配置文件 {self.file_path} 失败: {e}")
            return {}

    def get_priority(self) -> int:
        """文件配置优先级中等"""
        return self._priority

    def supports_watch(self) -> bool:
        """文件配置支持监视变化"""
        return True

    def watch_changes(self, callback: callable) -> None:
        """监视文件变化"""
        # 这里可以实现文件监视逻辑
        # 为了简化，暂时不实现
        pass
