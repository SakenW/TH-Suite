# apps/mc-l10n/backend/src/mc_l10n/di/simple_container.py
"""
简化的依赖注入容器

用于快速测试和开发的简单容器实现
"""

from __future__ import annotations

from packages.core import get_config

from src.mc_l10n.application.services.scan_service import ScanService
from src.mc_l10n.infrastructure.parsers import (
    ModFileAnalyzer,
    ParserFactory,
)
from src.mc_l10n.infrastructure.scanners import (
    MinecraftModScanner,
    MinecraftProjectScanner,
)


class SimpleContainer:
    """简单的依赖注入容器"""

    def __init__(self):
        self._instances = {}
        self._setup()

    def _setup(self):
        """设置所有依赖"""
        # 创建所有组件实例
        config = get_config()

        # 解析器组件
        parser_factory = ParserFactory()
        mod_file_analyzer = ModFileAnalyzer()

        # 扫描器组件
        project_scanner = MinecraftProjectScanner(mod_file_analyzer)
        mod_scanner = MinecraftModScanner(parser_factory)

        # 应用服务
        scan_service = ScanService(
            project_scanner=project_scanner,
            mod_scanner=mod_scanner,
            parser_factory=parser_factory,
            task_manager=None,
        )

        # 存储实例
        self._instances = {
            "config": config,
            "parser_factory": parser_factory,
            "mod_file_analyzer": mod_file_analyzer,
            "project_scanner": project_scanner,
            "mod_scanner": mod_scanner,
            "scan_service": scan_service,
        }

    def get(self, name: str):
        """获取服务实例"""
        return self._instances.get(name)

    def get_scan_service(self) -> ScanService:
        """获取扫描服务"""
        return self._instances["scan_service"]


# 全局容器实例
_container: SimpleContainer | None = None


def get_simple_container() -> SimpleContainer:
    """获取简单容器实例"""
    global _container
    if _container is None:
        _container = SimpleContainer()
    return _container
