"""
依赖注入容器
解决架构层违反问题，实现Clean Architecture的依赖反转
"""

import logging
from abc import ABC, abstractmethod
from collections.abc import Callable
from typing import Any, TypeVar

# 设置日志
logger = logging.getLogger(__name__)

T = TypeVar("T")


class DIContainer:
    """
    简单的依赖注入容器

    实现了基础的服务注册和解析功能，支持：
    - 单例模式服务注册（register_singleton）
    - 工厂方法注册（register_factory）
    - 服务实例获取（get）
    - 容器清理（clear）

    用于解决Clean Architecture中的依赖反转问题，
    让高层模块不依赖于低层模块的具体实现。
    """

    def __init__(self):
        self._services: dict[str, Any] = {}
        self._factories: dict[str, Callable] = {}
        self._singletons: dict[str, Any] = {}

    def register_singleton(self, service_type: type[T], instance: T) -> None:
        """
        注册单例服务

        Args:
            service_type: 服务的类型（通常是接口类型）
            instance: 服务的实例对象

        注册后，每次调用get()都会返回同一个实例。
        适用于数据库连接、配置对象等需要共享状态的服务。
        """
        key = service_type.__name__
        self._singletons[key] = instance
        logger.debug(f"注册单例服务: {key}")

    def register_factory(self, service_type: type[T], factory: Callable[[], T]) -> None:
        """
        注册工厂方法

        Args:
            service_type: 服务的类型（通常是接口类型）
            factory: 创建服务实例的工厂函数

        每次调用get()都会通过工厂函数创建新的实例。
        适用于有复杂初始化逻辑或需要延迟创建的服务。
        """
        key = service_type.__name__
        self._factories[key] = factory
        logger.debug(f"注册工厂服务: {key}")

    def get(self, service_type: type[T]) -> T | None:
        """
        获取服务实例

        Args:
            service_type: 要获取的服务类型

        Returns:
            服务实例，如果未找到则返回None

        解析顺序：
        1. 优先返回已注册的单例实例
        2. 如果没有单例，使用工厂方法创建
        3. 都没有则返回None并记录警告
        """
        key = service_type.__name__

        # 优先返回单例
        if key in self._singletons:
            return self._singletons[key]

        # 使用工厂创建
        if key in self._factories:
            instance = self._factories[key]()
            logger.debug(f"通过工厂创建服务: {key}")
            return instance

        logger.warning(f"未找到服务: {key}")
        return None

    def clear(self) -> None:
        """清理容器（用于测试）"""
        self._services.clear()
        self._factories.clear()
        self._singletons.clear()


# 全局容器实例
_container = DIContainer()


def get_container() -> DIContainer:
    """获取全局依赖注入容器"""
    return _container


# 服务接口定义
class IScannerService(ABC):
    """扫描服务接口"""

    @abstractmethod
    async def start_scan(
        self, target_path: str, incremental: bool = True, options: dict = None
    ) -> dict:
        """启动扫描"""
        pass

    @abstractmethod
    async def get_scan_status(self, scan_id: str) -> dict | None:
        """获取扫描状态"""
        pass

    @abstractmethod
    async def cancel_scan(self, scan_id: str) -> bool:
        """取消扫描"""
        pass

    @abstractmethod
    async def get_content_items(self, content_type: str, limit: int = 100) -> list:
        """获取内容项"""
        pass


class IDatabaseService(ABC):
    """数据库服务接口"""

    @abstractmethod
    async def get_statistics(self) -> dict:
        """获取数据库统计信息"""
        pass

    @abstractmethod
    async def initialize(self) -> bool:
        """初始化数据库"""
        pass


class IInfrastructureService(ABC):
    """基础设施服务接口"""

    @abstractmethod
    async def initialize(self) -> bool:
        """初始化基础设施"""
        pass

    @abstractmethod
    async def cleanup(self) -> None:
        """清理资源"""
        pass


# 实现类适配器 - 将现有服务包装成接口实现
class ScannerServiceAdapter(IScannerService):
    """扫描服务适配器"""

    def __init__(self, scanner_instance):
        self._scanner = scanner_instance

    async def start_scan(
        self, target_path: str, incremental: bool = True, options: dict = None
    ) -> dict:
        """启动扫描"""
        if options is None:
            options = {}
        return await self._scanner.start_scan(target_path, incremental, options)

    async def get_scan_status(self, scan_id: str) -> dict | None:
        """获取扫描状态"""
        return await self._scanner.get_scan_status(scan_id)

    async def cancel_scan(self, scan_id: str) -> bool:
        """取消扫描"""
        return await self._scanner.cancel_scan(scan_id)

    async def get_content_items(self, content_type: str, limit: int = 100) -> list:
        """获取内容项"""
        return await self._scanner.get_content_items(content_type, limit)


class DatabaseServiceAdapter(IDatabaseService):
    """数据库服务适配器"""

    def __init__(self):
        self._initialized = False

    async def get_statistics(self) -> dict:
        """获取数据库统计信息"""
        import os
        import sqlite3

        db_path = "data/mc_l10n_v6.db"
        stats = {
            "total_mods": 0,
            "total_language_files": 0,
            "total_translation_keys": 0,
            "languages": {},
            "mod_details": [],
            "total_entries": 0,
        }

        if os.path.exists(db_path):
            try:
                conn = sqlite3.connect(db_path)
                cursor = conn.cursor()

                # 获取模组数量 - 使用V6架构的core_mods表
                cursor.execute("SELECT COUNT(DISTINCT modid) FROM core_mods")
                stats["total_mods"] = cursor.fetchone()[0]

                # 获取语言文件数量 - 使用V6架构的core_language_files表
                cursor.execute("SELECT COUNT(*) FROM core_language_files")
                stats["total_language_files"] = cursor.fetchone()[0]

                # 获取翻译键数量 - 使用V6架构的core_translation_entries表
                cursor.execute("SELECT COUNT(*) FROM core_translation_entries")
                stats["total_translation_keys"] = cursor.fetchone()[0]

                # 获取语言分布 - 使用V6表结构
                cursor.execute("""
                    SELECT locale_code, COUNT(*)
                    FROM core_language_files
                    GROUP BY locale_code
                """)
                stats["languages"] = dict(cursor.fetchall())

                # 获取模组详情（前10个最大的模组）- 使用V6表结构
                cursor.execute("""
                    SELECT m.modid, m.display_name,
                           COUNT(DISTINCT lf.locale_code) as lang_count,
                           COUNT(DISTINCT te.translation_key) as key_count
                    FROM core_mods m
                    LEFT JOIN core_language_files lf ON m.modid = lf.mod_id
                    LEFT JOIN core_translation_entries te ON lf.file_id = te.file_id
                    GROUP BY m.modid, m.display_name
                    ORDER BY key_count DESC
                    LIMIT 10
                """)

                mod_rows = cursor.fetchall()
                stats["mod_details"] = [
                    {
                        "mod_id": row[0],
                        "mod_name": row[1] or row[0],
                        "language_count": row[2],
                        "key_count": row[3],
                    }
                    for row in mod_rows
                ]

                stats["total_entries"] = stats["total_translation_keys"]
                conn.close()

            except Exception as e:
                logger.warning(f"读取数据库统计失败: {e}")

        return stats

    async def initialize(self) -> bool:
        """初始化数据库 - 使用V6架构"""
        try:
            # 使用v2.1数据库架构
            from repositories.v2_1_repositories import PackRepository
            
            # v2.1数据库使用Repository模式，无需额外初始化
            self._initialized = True
            logger.info("v2.1数据库初始化成功")
            return True
        except Exception as e:
            logger.error(f"v2.1数据库初始化失败: {e}")
            return False


class InfrastructureServiceAdapter(IInfrastructureService):
    """基础设施服务适配器"""

    def __init__(self):
        self._initialized = False

    async def initialize(self) -> bool:
        """初始化基础设施"""
        try:
            from infrastructure import initialize_infrastructure

            initialize_infrastructure()
            self._initialized = True
            logger.info("基础设施初始化成功")
            return True
        except Exception as e:
            logger.error(f"基础设施初始化失败: {e}")
            return False

    async def cleanup(self) -> None:
        """清理资源"""
        logger.info("基础设施资源清理完成")


# 容器初始化函数
async def initialize_container() -> DIContainer:
    """
    初始化依赖注入容器

    按照依赖关系顺序初始化所有服务：
    1. 数据库服务（DatabaseServiceAdapter）
    2. 基础设施服务（InfrastructureServiceAdapter）
    3. 扫描服务工厂（延迟创建，依赖于基础设施）

    Returns:
        配置完成的依赖注入容器实例

    注意：扫描服务使用工厂模式延迟创建，避免循环依赖问题
    """
    container = get_container()

    # 注册数据库服务
    db_service = DatabaseServiceAdapter()
    container.register_singleton(IDatabaseService, db_service)

    # 注册基础设施服务
    infra_service = InfrastructureServiceAdapter()
    container.register_singleton(IInfrastructureService, infra_service)

    # 延迟注册扫描服务（需要在基础设施初始化后）
    def scanner_factory() -> IScannerService:
        # 不包装ScanApplicationService，因为它本身不是扫描服务
        # 直接返回一个简化的扫描服务适配器
        from application.services.scan_application_service import ScanApplicationService
        
        class SimpleScannerAdapter(IScannerService):
            def __init__(self):
                self.scan_service = ScanApplicationService()
                
            async def start_scan(self, target_path: str, incremental: bool = True, options: dict = None) -> dict:
                return await self.scan_service.start_project_scan(target_path, incremental, scan_options=options)
                
            async def get_scan_status(self, scan_id: str) -> dict | None:
                result = await self.scan_service.get_scan_status(scan_id)
                return result.get("data") if result and result.get("success") else None
                
            async def cancel_scan(self, scan_id: str) -> bool:
                result = await self.scan_service.cancel_scan(scan_id)
                return result.get("success", False)
                
            async def get_content_items(self, content_type: str, limit: int = 100) -> list:
                # 临时实现，返回空列表
                return []
        
        return SimpleScannerAdapter()

    container.register_factory(IScannerService, scanner_factory)

    logger.info("依赖注入容器初始化完成")
    return container


# 便捷的服务获取函数
def get_scanner_service() -> IScannerService | None:
    """获取扫描服务"""
    return get_container().get(IScannerService)


def get_database_service() -> IDatabaseService | None:
    """获取数据库服务"""
    return get_container().get(IDatabaseService)


def get_infrastructure_service() -> IInfrastructureService | None:
    """获取基础设施服务"""
    return get_container().get(IInfrastructureService)


def get_database_manager():
    """获取数据库管理器（兼容旧代码）"""
    from repositories.v2_1_repositories import PackRepository
    from pathlib import Path
    
    # 使用与其他服务一致的v2.1数据库路径
    db_path = str(Path(__file__).parent.parent / "data" / "mc_l10n_v2_1.db")
    return PackRepository(db_path)
