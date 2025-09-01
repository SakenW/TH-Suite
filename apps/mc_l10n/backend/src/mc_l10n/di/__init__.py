# apps/mc-l10n/backend/src/mc_l10n/di/__init__.py
"""
依赖注入模块

提供应用级别的依赖注入配置和容器管理
"""

from .container import (
    MCL10nContainer,
    configure_dependencies,
    get_container,
)

__all__ = [
    "MCL10nContainer",
    "get_container",
    "configure_dependencies",
]
