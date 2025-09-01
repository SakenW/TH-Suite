# apps/mc-l10n/backend/src/mc_l10n/di/container.py
"""
依赖注入容器配置

配置MC L10n应用的所有依赖关系，实现松耦合的组件管理
"""

from __future__ import annotations

from packages.core import DIContainer, get_config

from src.mc_l10n.application.services.scan_service import ScanService
from src.mc_l10n.domain.scan_models import MinecraftModScanRule, ModpackScanRule
from src.mc_l10n.infrastructure.parsers import (
    MinecraftLangParser,
    ModFileAnalyzer,
    ParserFactory,
)
from src.mc_l10n.infrastructure.scanners import (
    MinecraftModScanner,
    MinecraftProjectScanner,
    ModScannerImpl,
    ProjectScannerImpl,
)


class MCL10nContainer:
    """MC L10n应用的依赖注入容器"""

    def __init__(self):
        self.container = DIContainer()
        self._register_dependencies()

    def _register_dependencies(self) -> None:
        """注册所有依赖"""

        # 配置
        config = get_config()
        self.container.register_singleton(type(config), lambda: config)

        # 核心规则
        self.container.register_singleton(
            "mod_scan_rule", lambda: MinecraftModScanRule()
        )
        self.container.register_singleton(
            "modpack_scan_rule", lambda: ModpackScanRule()
        )

        # 解析器组件
        self.container.register_singleton("lang_parser", lambda: MinecraftLangParser())

        self.container.register_singleton(
            "mod_file_analyzer", lambda: ModFileAnalyzer()
        )

        self.container.register_transient("parser_factory", lambda: ParserFactory())

        # 扫描器组件
        self.container.register_transient(
            "project_scanner",
            lambda: MinecraftProjectScanner(
                mod_analyzer=self.container.resolve("mod_file_analyzer")
            ),
        )

        self.container.register_transient(
            "mod_scanner",
            lambda: MinecraftModScanner(
                parser_factory=self.container.resolve("parser_factory")
            ),
        )

        # 核心接口实现
        self.container.register_transient(
            "project_scanner_impl", lambda: ProjectScannerImpl()
        )

        self.container.register_transient("mod_scanner_impl", lambda: ModScannerImpl())

        # 应用服务
        self.container.register_transient(
            "scan_service",
            lambda: ScanService(
                project_scanner=self.container.resolve("project_scanner"),
                mod_scanner=self.container.resolve("mod_scanner"),
                parser_factory=self.container.resolve("parser_factory"),
                task_manager=None,  # 可选：稍后集成任务管理器
            ),
        )

    def resolve(self, service_name: str):
        """解析服务"""
        return self.container.resolve(service_name)

    def get_scan_service(self) -> ScanService:
        """获取扫描服务"""
        return self.resolve("scan_service")


# 全局容器实例
_container: MCL10nContainer | None = None


def get_container() -> MCL10nContainer:
    """获取全局容器实例"""
    global _container
    if _container is None:
        _container = MCL10nContainer()
    return _container


def configure_dependencies() -> MCL10nContainer:
    """配置依赖（用于应用启动时调用）"""
    return get_container()
