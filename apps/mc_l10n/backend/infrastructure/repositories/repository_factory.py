"""
V5架构 - Repository工厂
提供统一的Repository实例管理和依赖注入
"""

from typing import Dict, Any, TypeVar, Type
import structlog

from .core_project_repository import CoreProjectRepository
from .core_pack_repository import CorePackRepository
from .core_mod_repository import CoreModRepository
from .ops_work_queue_repository_v2 import OpsWorkQueueRepository

logger = structlog.get_logger(__name__)

T = TypeVar('T')


class RepositoryFactory:
    """Repository工厂类"""
    
    def __init__(self, db_path: str):
        self.db_path = db_path
        self._repositories: Dict[str, Any] = {}
        self._initialized = False
    
    def initialize(self):
        """初始化所有Repository"""
        if self._initialized:
            return
        
        logger.info("🏗️ 初始化V5架构Repository工厂")
        
        # Core repositories
        self._repositories['core_project'] = CoreProjectRepository(self.db_path)
        self._repositories['core_pack'] = CorePackRepository(self.db_path)
        self._repositories['core_mod'] = CoreModRepository(self.db_path)
        
        # Ops repositories
        self._repositories['ops_work_queue'] = OpsWorkQueueRepository(self.db_path)
        
        # TODO: 添加更多Repository
        # self._repositories['core_pack_version'] = CorePackVersionRepository(self.db_path)
        # self._repositories['core_pack_installation'] = CorePackInstallationRepository(self.db_path)
        # self._repositories['ops_sync_log'] = OpsSyncLogRepository(self.db_path)
        # self._repositories['cfg_local_settings'] = CfgLocalSettingsRepository(self.db_path)
        # self._repositories['cache_entry'] = CacheEntryRepository(self.db_path)
        
        self._initialized = True
        logger.info(f"✅ Repository工厂初始化完成，共 {len(self._repositories)} 个Repository")
    
    def get_core_project_repo(self) -> CoreProjectRepository:
        """获取项目Repository"""
        self._ensure_initialized()
        return self._repositories['core_project']
    
    def get_core_pack_repo(self) -> CorePackRepository:
        """获取整合包Repository"""
        self._ensure_initialized()
        return self._repositories['core_pack']
    
    def get_core_mod_repo(self) -> CoreModRepository:
        """获取MOD Repository"""
        self._ensure_initialized()
        return self._repositories['core_mod']
    
    def get_ops_work_queue_repo(self) -> OpsWorkQueueRepository:
        """获取工作队列Repository"""
        self._ensure_initialized()
        return self._repositories['ops_work_queue']
    
    def get_repository(self, repo_name: str) -> Any:
        """通用Repository获取方法"""
        self._ensure_initialized()
        if repo_name not in self._repositories:
            raise ValueError(f"Repository '{repo_name}' 不存在")
        return self._repositories[repo_name]
    
    def _ensure_initialized(self):
        """确保工厂已初始化"""
        if not self._initialized:
            self.initialize()
    
    def get_all_repositories(self) -> Dict[str, Any]:
        """获取所有Repository"""
        self._ensure_initialized()
        return self._repositories.copy()
    
    def health_check(self) -> Dict[str, bool]:
        """健康检查所有Repository"""
        self._ensure_initialized()
        health_status = {}
        
        for name, repo in self._repositories.items():
            try:
                # 尝试获取表信息来验证Repository健康状态
                repo.get_table_info()
                health_status[name] = True
            except Exception as e:
                logger.error(f"Repository {name} 健康检查失败: {e}")
                health_status[name] = False
        
        return health_status


# 全局Repository工厂实例
_factory_instance: RepositoryFactory = None


def get_repository_factory(db_path: str = "data/mc_l10n.db") -> RepositoryFactory:
    """获取Repository工厂单例"""
    global _factory_instance
    if _factory_instance is None:
        _factory_instance = RepositoryFactory(db_path)
    return _factory_instance


def get_core_project_repo(db_path: str = "data/mc_l10n.db") -> CoreProjectRepository:
    """便捷方法：获取项目Repository"""
    return get_repository_factory(db_path).get_core_project_repo()


def get_core_pack_repo(db_path: str = "data/mc_l10n.db") -> CorePackRepository:
    """便捷方法：获取整合包Repository"""
    return get_repository_factory(db_path).get_core_pack_repo()


def get_core_mod_repo(db_path: str = "data/mc_l10n.db") -> CoreModRepository:
    """便捷方法：获取MOD Repository"""
    return get_repository_factory(db_path).get_core_mod_repo()


def get_ops_work_queue_repo(db_path: str = "data/mc_l10n.db") -> OpsWorkQueueRepository:
    """便捷方法：获取工作队列Repository"""
    return get_repository_factory(db_path).get_ops_work_queue_repo()