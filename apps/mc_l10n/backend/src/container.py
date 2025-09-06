"""
依赖注入容器
管理应用中的所有服务和依赖
"""

from typing import Dict, Any, Optional
from functools import lru_cache
import logging
import os

from domain.repositories import (
    ModRepository,
    TranslationProjectRepository,
    TranslationRepository,
    EventRepository,
    ScanResultRepository,
    CacheRepository
)

from infrastructure.persistence.sqlite_repositories import (
    SqliteModRepository,
    SqliteTranslationProjectRepository,
    SqliteTranslationRepository,
    SqliteEventRepository,
    SqliteScanResultRepository
)

from infrastructure.cache.memory_cache import MemoryCacheRepository
from infrastructure.minecraft.mod_scanner import MinecraftModScanner

from application.services.scan_service import ScanService

from domain.services import (
    TranslationService,
    ConflictResolutionService,
    TerminologyService
)

from infrastructure.unit_of_work import UnitOfWorkFactory
from facade import MCL10nFacade

logger = logging.getLogger(__name__)


class ServiceContainer:
    """服务容器 - 管理所有依赖注入"""
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        self.config = config or self._load_default_config()
        self._services: Dict[str, Any] = {}
        self._repositories: Dict[str, Any] = {}
        self._initialized = False
    
    def _load_default_config(self) -> Dict[str, Any]:
        """加载默认配置"""
        return {
            'database_path': os.getenv('DATABASE_PATH', 'mc_l10n_local.db'),
            'cache_max_size': int(os.getenv('CACHE_MAX_SIZE', '10000')),
            'scan_workers': int(os.getenv('SCAN_WORKERS', '4')),
            'api_port': int(os.getenv('API_PORT', '8000')),
            'debug': os.getenv('DEBUG', 'false').lower() == 'true'
        }
    
    def initialize(self):
        """初始化容器"""
        if self._initialized:
            return
        
        logger.info("Initializing service container...")
        
        # 初始化Repository
        self._init_repositories()
        
        # 初始化领域服务
        self._init_domain_services()
        
        # 初始化应用服务
        self._init_application_services()
        
        # 初始化基础设施服务
        self._init_infrastructure_services()
        
        self._initialized = True
        logger.info("Service container initialized successfully")
    
    def _init_repositories(self):
        """初始化Repository层"""
        db_path = self.config['database_path']
        
        # 数据库Repository
        self._repositories['mod'] = SqliteModRepository(db_path)
        self._repositories['project'] = SqliteTranslationProjectRepository(db_path)
        self._repositories['translation'] = SqliteTranslationRepository(db_path)
        self._repositories['event'] = SqliteEventRepository(db_path)
        self._repositories['scan_result'] = SqliteScanResultRepository(db_path)
        
        # 缓存Repository
        self._repositories['cache'] = MemoryCacheRepository(
            max_size=self.config['cache_max_size']
        )
        
        logger.debug(f"Initialized {len(self._repositories)} repositories")
    
    def _init_domain_services(self):
        """初始化领域服务"""
        # 翻译服务
        self._services['translation_service'] = TranslationService(
            mod_repository=self.get_repository('mod'),
            translation_repository=self.get_repository('translation')
        )
        
        # 冲突解决服务
        self._services['conflict_resolution'] = ConflictResolutionService(
            translation_repository=self.get_repository('translation')
        )
        
        # 术语服务
        self._services['terminology'] = TerminologyService()
        
        logger.debug("Initialized domain services")
    
    def _init_application_services(self):
        """初始化应用服务"""
        # 扫描服务
        self._services['scan'] = ScanService(
            mod_repository=self.get_repository('mod'),
            scan_result_repository=self.get_repository('scan_result'),
            scanner=MinecraftModScanner()
        )
        
        # TODO: 添加其他应用服务
        # self._services['project'] = ProjectService(...)
        # self._services['sync'] = SyncService(...)
        
        logger.debug("Initialized application services")
    
    def _init_infrastructure_services(self):
        """初始化基础设施服务"""
        # Minecraft扫描器
        self._services['minecraft_scanner'] = MinecraftModScanner()
        
        # Unit of Work工厂
        self._services['uow_factory'] = UnitOfWorkFactory(
            mod_repository=self.get_repository('mod'),
            project_repository=self.get_repository('project')
        )
        
        # 门面服务
        self._services['facade'] = MCL10nFacade(self)
        
        logger.debug("Initialized infrastructure services")
    
    def get_repository(self, name: str) -> Any:
        """获取Repository实例"""
        if name not in self._repositories:
            raise KeyError(f"Repository '{name}' not found")
        
        return self._repositories[name]
    
    def get_service(self, name: str) -> Any:
        """获取服务实例"""
        if name not in self._services:
            raise KeyError(f"Service '{name}' not found")
        
        return self._services[name]
    
    def register_service(self, name: str, service: Any):
        """注册自定义服务"""
        self._services[name] = service
        logger.debug(f"Registered service: {name}")
    
    def register_repository(self, name: str, repository: Any):
        """注册自定义Repository"""
        self._repositories[name] = repository
        logger.debug(f"Registered repository: {name}")
    
    def cleanup(self):
        """清理资源"""
        logger.info("Cleaning up service container...")
        
        # 清理Repository连接
        for name, repo in self._repositories.items():
            if hasattr(repo, 'close'):
                try:
                    repo.close()
                    logger.debug(f"Closed repository: {name}")
                except Exception as e:
                    logger.error(f"Failed to close repository {name}: {e}")
        
        # 清理服务
        for name, service in self._services.items():
            if hasattr(service, 'cleanup'):
                try:
                    service.cleanup()
                    logger.debug(f"Cleaned up service: {name}")
                except Exception as e:
                    logger.error(f"Failed to cleanup service {name}: {e}")
        
        self._repositories.clear()
        self._services.clear()
        self._initialized = False
        
        logger.info("Service container cleanup complete")
    
    def get_stats(self) -> Dict[str, Any]:
        """获取容器统计信息"""
        stats = {
            'initialized': self._initialized,
            'repositories': list(self._repositories.keys()),
            'services': list(self._services.keys()),
            'config': self.config
        }
        
        # 添加缓存统计
        if 'cache' in self._repositories:
            cache = self._repositories['cache']
            if hasattr(cache, 'get_stats'):
                stats['cache_stats'] = cache.get_stats()
        
        return stats


# 全局容器实例
_container: Optional[ServiceContainer] = None


@lru_cache()
def get_container() -> ServiceContainer:
    """获取全局容器实例（单例）"""
    global _container
    
    if _container is None:
        _container = ServiceContainer()
        _container.initialize()
    
    return _container


def reset_container():
    """重置容器（用于测试）"""
    global _container
    
    if _container:
        _container.cleanup()
        _container = None


# 便捷函数
def get_service(name: str) -> Any:
    """获取服务的便捷函数"""
    return get_container().get_service(name)


def get_repository(name: str) -> Any:
    """获取Repository的便捷函数"""
    return get_container().get_repository(name)


def get_facade() -> MCL10nFacade:
    """获取门面服务"""
    return get_container().get_service('facade')