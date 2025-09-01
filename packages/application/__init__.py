# packages/application/__init__.py
"""
TH-Suite 应用服务层

提供高级的业务用例实现，协调领域模型和基础设施组件。
这一层是游戏无关的，包含可在多个游戏间复用的业务逻辑。

架构模式：Adapters → Application → Domain → Infrastructure → Core
"""

from .game_registry import GamePluginRegistryImpl
from .services import (
    UnifiedFileProcessingService,
    UnifiedProjectManagementService,
)

__all__ = [
    "GamePluginRegistryImpl",
    "UnifiedProjectManagementService",
    "UnifiedFileProcessingService",
]
