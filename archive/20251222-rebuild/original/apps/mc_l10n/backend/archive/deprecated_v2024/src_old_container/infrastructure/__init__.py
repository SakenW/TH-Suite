"""
基础设施层
提供技术实现细节
"""

# 导出关键模块
from .cache.memory_cache import MemoryCacheRepository
from .minecraft.mod_scanner import MinecraftModScanner
# 已归档: from .persistence.sqlite_repositories import ...
# 旧的Repository模式已迁移至V6架构
# 新的Repository访问请使用: database.repositories.*

__all__ = [
    # 活跃模块
    "MemoryCacheRepository",
    "MinecraftModScanner",
    # 已归档的Repository已迁移至V6架构: database.repositories.*
]
