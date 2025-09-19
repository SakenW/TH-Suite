"""
版本管理系统集成配置 - TH-Suite MC L10n
将版本管理系统整合到主应用的配置和初始化
"""

import logging
from typing import Dict, Any, Optional
from contextlib import asynccontextmanager

from infrastructure.services.version_management_service import get_version_management_service
from infrastructure.services.version_operations_engine import get_version_operations_engine
from infrastructure.services.version_diff_engine import VersionDiffEngine
from infrastructure.services.version_sync_integration import get_version_sync_integration
from infrastructure.services.version_performance_optimizer import get_version_performance_optimizer
from infrastructure.repositories.repository_factory import get_repository_factory

logger = logging.getLogger(__name__)


class VersionManagementIntegration:
    """版本管理系统集成器"""
    
    def __init__(self):
        self.version_service = None
        self.operations_engine = None
        self.diff_engine = None
        self.sync_integration = None
        self.performance_optimizer = None
        self.factory = None
        
        self.config = {
            "enabled": True,
            "auto_init_database": True,
            "auto_create_repositories": True,
            "performance_monitoring": True,
            "sync_integration": True,
            "cache_optimization": True,
            "compression_enabled": True
        }
        
        self._initialized = False
    
    async def initialize(self) -> Dict[str, Any]:
        """初始化版本管理系统"""
        if self._initialized:
            return {
                "success": True,
                "message": "版本管理系统已初始化"
            }
        
        try:
            logger.info("开始初始化版本管理系统...")
            
            # 1. 初始化数据库
            if self.config["auto_init_database"]:
                db_init_result = await self._initialize_database()
                if not db_init_result["success"]:
                    return db_init_result
            
            # 2. 初始化服务实例
            await self._initialize_services()
            
            # 3. 验证系统状态
            validation_result = await self._validate_system()
            if not validation_result["success"]:
                return validation_result
            
            # 4. 配置性能优化
            if self.config["performance_monitoring"]:
                await self._configure_performance_monitoring()
            
            self._initialized = True
            
            logger.info("版本管理系统初始化完成")
            
            return {
                "success": True,
                "message": "版本管理系统初始化成功",
                "features": {
                    "version_control": True,
                    "branch_management": True,
                    "rollback_operations": True,
                    "merge_operations": True,
                    "diff_calculation": True,
                    "sync_integration": self.config["sync_integration"],
                    "performance_optimization": self.config["cache_optimization"],
                    "compression": self.config["compression_enabled"]
                }
            }
            
        except Exception as e:
            logger.error(f"版本管理系统初始化失败: {e}")
            return {
                "success": False,
                "message": f"初始化失败: {str(e)}"
            }
    
    async def _initialize_database(self) -> Dict[str, Any]:
        """初始化版本管理数据库表"""
        try:
            self.factory = get_repository_factory()
            
            # 检查数据库连接
            async with self.factory.get_db_connection() as conn:
                # 检查版本管理表是否存在
                cursor = await conn.execute("""
                    SELECT name FROM sqlite_master 
                    WHERE type='table' AND name LIKE 'version_%'
                """)
                
                existing_tables = [row[0] for row in await cursor.fetchall()]
                
                if not existing_tables:
                    logger.warning("版本管理表不存在，需要运行数据库迁移")
                    return {
                        "success": False,
                        "message": "版本管理表不存在，请运行数据库迁移: 010_create_version_management_tables.sql 和 011_extend_core_tables_for_versioning.sql"
                    }
                
                logger.info(f"发现版本管理表: {len(existing_tables)} 个")
            
            return {
                "success": True,
                "message": "数据库检查通过",
                "tables_found": len(existing_tables)
            }
            
        except Exception as e:
            logger.error(f"数据库初始化失败: {e}")
            return {
                "success": False,
                "message": f"数据库初始化失败: {str(e)}"
            }
    
    async def _initialize_services(self) -> None:
        """初始化所有服务实例"""
        self.version_service = get_version_management_service()
        self.operations_engine = get_version_operations_engine()
        self.diff_engine = VersionDiffEngine()
        
        if self.config["sync_integration"]:
            self.sync_integration = get_version_sync_integration()
        
        if self.config["cache_optimization"]:
            self.performance_optimizer = get_version_performance_optimizer()
        
        logger.info("版本管理服务实例初始化完成")
    
    async def _validate_system(self) -> Dict[str, Any]:
        """验证系统状态"""
        try:
            # 测试基本功能
            test_results = {}
            
            # 测试版本服务
            if self.version_service:
                test_results["version_service"] = True
            
            # 测试操作引擎
            if self.operations_engine:
                test_results["operations_engine"] = True
            
            # 测试差异引擎
            if self.diff_engine:
                # 简单的差异计算测试
                test_diff = self.diff_engine.calculate_diff({"a": 1}, {"a": 2})
                test_results["diff_engine"] = len(test_diff.operations) > 0
            
            # 测试同步集成
            if self.sync_integration:
                test_results["sync_integration"] = True
            
            # 测试性能优化器
            if self.performance_optimizer:
                test_results["performance_optimizer"] = True
            
            all_passed = all(test_results.values())
            
            return {
                "success": all_passed,
                "message": "系统验证完成" if all_passed else "系统验证发现问题",
                "test_results": test_results
            }
            
        except Exception as e:
            logger.error(f"系统验证失败: {e}")
            return {
                "success": False,
                "message": f"系统验证失败: {str(e)}"
            }
    
    async def _configure_performance_monitoring(self) -> None:
        """配置性能监控"""
        try:
            if self.performance_optimizer:
                # 配置性能监控参数
                self.performance_optimizer.config.update({
                    "monitoring_enabled": True,
                    "metrics_retention": 1000,
                    "auto_gc": True
                })
                
                logger.info("性能监控配置完成")
        except Exception as e:
            logger.error(f"性能监控配置失败: {e}")
    
    async def get_system_status(self) -> Dict[str, Any]:
        """获取系统状态"""
        try:
            if not self._initialized:
                return {
                    "initialized": False,
                    "message": "系统尚未初始化"
                }
            
            # 收集各组件状态
            status = {
                "initialized": True,
                "timestamp": __import__('datetime').datetime.now().isoformat(),
                "components": {
                    "version_service": self.version_service is not None,
                    "operations_engine": self.operations_engine is not None,
                    "diff_engine": self.diff_engine is not None,
                    "sync_integration": self.sync_integration is not None,
                    "performance_optimizer": self.performance_optimizer is not None
                },
                "config": self.config.copy()
            }
            
            # 获取性能统计
            if self.performance_optimizer:
                perf_stats = await self.performance_optimizer.get_performance_stats()
                if perf_stats["success"]:
                    status["performance"] = perf_stats.get("stats", {})
            
            return status
            
        except Exception as e:
            logger.error(f"获取系统状态失败: {e}")
            return {
                "initialized": self._initialized,
                "error": str(e)
            }
    
    async def shutdown(self) -> Dict[str, Any]:
        """关闭版本管理系统"""
        try:
            logger.info("开始关闭版本管理系统...")
            
            # 保存性能统计
            if self.performance_optimizer:
                stats = await self.performance_optimizer.get_performance_stats()
                if stats["success"]:
                    logger.info(f"性能统计: {stats['stats']}")
            
            # 清理资源
            self.version_service = None
            self.operations_engine = None
            self.diff_engine = None
            self.sync_integration = None
            self.performance_optimizer = None
            self.factory = None
            
            self._initialized = False
            
            logger.info("版本管理系统关闭完成")
            
            return {
                "success": True,
                "message": "版本管理系统关闭成功"
            }
            
        except Exception as e:
            logger.error(f"版本管理系统关闭失败: {e}")
            return {
                "success": False,
                "message": f"关闭失败: {str(e)}"
            }


# 全局集成实例
_version_integration: Optional[VersionManagementIntegration] = None


def get_version_integration() -> VersionManagementIntegration:
    """获取版本管理集成实例"""
    global _version_integration
    if _version_integration is None:
        _version_integration = VersionManagementIntegration()
    return _version_integration


@asynccontextmanager
async def version_management_lifespan():
    """版本管理系统生命周期管理器"""
    integration = get_version_integration()
    
    try:
        # 启动
        init_result = await integration.initialize()
        if not init_result["success"]:
            logger.error(f"版本管理系统启动失败: {init_result['message']}")
        else:
            logger.info("版本管理系统启动成功")
        
        yield integration
        
    finally:
        # 关闭
        shutdown_result = await integration.shutdown()
        if shutdown_result["success"]:
            logger.info("版本管理系统关闭成功")
        else:
            logger.error(f"版本管理系统关闭失败: {shutdown_result['message']}")


# FastAPI集成函数
def register_version_management_routes(app):
    """注册版本管理路由到FastAPI应用"""
    try:
        from api.routes.version_routes import register_version_routes
        register_version_routes(app)
        logger.info("版本管理API路由注册成功")
    except ImportError as e:
        logger.error(f"版本管理API路由注册失败: {e}")


async def initialize_version_management_for_app():
    """为应用初始化版本管理系统"""
    integration = get_version_integration()
    return await integration.initialize()


# 中间件集成
class VersionManagementMiddleware:
    """版本管理中间件"""
    
    def __init__(self, app):
        self.app = app
        self.integration = get_version_integration()
    
    async def __call__(self, scope, receive, send):
        if scope["type"] == "http":
            # 在HTTP请求中添加版本管理信息
            if hasattr(scope, "state") and self.integration._initialized:
                scope["state"].version_management = self.integration
        
        await self.app(scope, receive, send)