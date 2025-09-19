#!/usr/bin/env python3
"""
TH-Suite 翻译数据传输架构部署配置

本脚本负责将传输架构的所有组件集成到现有的TH-Suite基础设施中：
1. 服务注册和依赖注入配置
2. API路由注册
3. 数据库迁移
4. 工作队列处理器集成
5. 事件系统集成
6. 缓存服务集成
"""

import asyncio
import os
from pathlib import Path
from typing import Dict, Any, List
import logging
from dataclasses import dataclass

# 基础设施导入
from core.di_container import DIContainer
from infrastructure.db_initializer import DatabaseInitializer
from infrastructure.services.work_queue_processor import WorkQueueProcessor
from infrastructure.services.multi_layer_cache_service import MultiLayerCacheService

# 传输架构服务导入
from infrastructure.services.translation_data_extractor import TranslationDataExtractor
from infrastructure.services.localized_compression_service import LocalizedCompressionService
from infrastructure.services.file_transfer_service import FileTransferService
from infrastructure.services.transfer_controller import TransferController
from infrastructure.services.transfer_resilience_service import TransferResilienceService
from infrastructure.services.transfer_event_processor import TransferEventProcessor

# API路由导入
from api.routes.transfer_routes import router as transfer_router

# 配置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@dataclass
class DeploymentConfig:
    """部署配置"""
    enable_transfer_services: bool = True
    enable_compression: bool = True
    enable_resilience: bool = True
    max_concurrent_transfers: int = 8
    max_concurrent_downloads: int = 12
    chunk_size_mb: int = 4
    compression_level: str = "balanced"
    cache_ttl_hours: int = 24
    retry_max_attempts: int = 3
    health_check_interval_seconds: int = 60


class TransmissionArchitectureDeployer:
    """传输架构部署器"""
    
    def __init__(self, config: DeploymentConfig):
        self.config = config
        self.container: DIContainer = None
        self.deployment_status: Dict[str, bool] = {}
    
    async def deploy_transmission_architecture(self, container: DIContainer):
        """部署传输架构"""
        logger.info("🚀 开始部署 TH-Suite 翻译数据传输架构")
        
        self.container = container
        
        try:
            # 1. 数据库迁移
            await self._migrate_database()
            
            # 2. 注册核心服务
            await self._register_core_services()
            
            # 3. 注册传输服务
            await self._register_transfer_services()
            
            # 4. 集成工作队列处理器
            await self._integrate_work_queue_processor()
            
            # 5. 集成缓存服务
            await self._integrate_cache_service()
            
            # 6. 注册API路由
            await self._register_api_routes()
            
            # 7. 启动后台服务
            await self._start_background_services()
            
            # 8. 验证部署
            await self._verify_deployment()
            
            logger.info("✅ 传输架构部署完成")
            return True
            
        except Exception as e:
            logger.error(f"❌ 传输架构部署失败: {str(e)}")
            await self._rollback_deployment()
            raise
    
    async def _migrate_database(self):
        """数据库迁移"""
        logger.info("📊 执行数据库迁移...")
        
        try:
            db_initializer = self.container.get(DatabaseInitializer)
            
            # 检查是否需要新的传输相关表
            conn = self.container.get_sqlite_connection()
            cursor = conn.cursor()
            
            # 检查 transfer_sessions 表是否存在
            cursor.execute("""
                SELECT name FROM sqlite_master 
                WHERE type='table' AND name='transfer_sessions'
            """)
            
            if not cursor.fetchone():
                logger.info("  创建传输会话表...")
                cursor.execute("""
                    CREATE TABLE transfer_sessions (
                        session_id TEXT PRIMARY KEY,
                        session_type TEXT NOT NULL,
                        file_path TEXT NOT NULL,
                        total_size INTEGER NOT NULL,
                        chunk_size INTEGER NOT NULL,
                        total_chunks INTEGER NOT NULL,
                        status TEXT NOT NULL DEFAULT 'PENDING',
                        metadata TEXT,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        completed_at TIMESTAMP
                    )
                """)
            
            # 检查 transfer_chunks 表是否存在
            cursor.execute("""
                SELECT name FROM sqlite_master 
                WHERE type='table' AND name='transfer_chunks'
            """)
            
            if not cursor.fetchone():
                logger.info("  创建传输块表...")
                cursor.execute("""
                    CREATE TABLE transfer_chunks (
                        chunk_id TEXT PRIMARY KEY,
                        session_id TEXT NOT NULL,
                        chunk_index INTEGER NOT NULL,
                        chunk_size INTEGER NOT NULL,
                        status TEXT NOT NULL DEFAULT 'PENDING',
                        blake3_hash TEXT,
                        retry_count INTEGER DEFAULT 0,
                        error_message TEXT,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        FOREIGN KEY (session_id) REFERENCES transfer_sessions(session_id)
                    )
                """)
                
                # 创建索引
                cursor.execute("CREATE INDEX idx_chunks_session ON transfer_chunks(session_id)")
                cursor.execute("CREATE INDEX idx_chunks_status ON transfer_chunks(status)")
            
            # 检查 compression_stats 表是否存在
            cursor.execute("""
                SELECT name FROM sqlite_master 
                WHERE type='table' AND name='compression_stats'
            """)
            
            if not cursor.fetchone():
                logger.info("  创建压缩统计表...")
                cursor.execute("""
                    CREATE TABLE compression_stats (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        file_path TEXT NOT NULL,
                        original_size INTEGER NOT NULL,
                        compressed_size INTEGER NOT NULL,
                        compression_ratio REAL NOT NULL,
                        compression_level TEXT NOT NULL,
                        language_family TEXT NOT NULL,
                        algorithm TEXT NOT NULL DEFAULT 'zstd',
                        duration_seconds REAL NOT NULL,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    )
                """)
                
                cursor.execute("CREATE INDEX idx_compression_stats_file ON compression_stats(file_path)")
                cursor.execute("CREATE INDEX idx_compression_stats_level ON compression_stats(compression_level)")
            
            conn.commit()
            conn.close()
            
            self.deployment_status['database_migration'] = True
            logger.info("✅ 数据库迁移完成")
            
        except Exception as e:
            logger.error(f"❌ 数据库迁移失败: {str(e)}")
            self.deployment_status['database_migration'] = False
            raise
    
    async def _register_core_services(self):
        """注册核心服务"""
        logger.info("🔧 注册核心服务...")
        
        try:
            # 注册翻译数据提取器
            self.container.register_singleton(
                TranslationDataExtractor,
                lambda: TranslationDataExtractor(self.container)
            )
            
            # 注册本地化压缩服务
            self.container.register_singleton(
                LocalizedCompressionService,
                lambda: LocalizedCompressionService()
            )
            
            self.deployment_status['core_services'] = True
            logger.info("✅ 核心服务注册完成")
            
        except Exception as e:
            logger.error(f"❌ 核心服务注册失败: {str(e)}")
            self.deployment_status['core_services'] = False
            raise
    
    async def _register_transfer_services(self):
        """注册传输服务"""
        logger.info("📤 注册传输服务...")
        
        try:
            # 注册文件传输服务
            self.container.register_singleton(
                FileTransferService,
                lambda: FileTransferService(self.container)
            )
            
            # 注册传输控制器
            def create_transfer_controller():
                transfer_service = self.container.get(FileTransferService)
                compression_service = self.container.get(LocalizedCompressionService)
                return TransferController(
                    transfer_service,
                    compression_service,
                    self.container
                )
            
            self.container.register_singleton(
                TransferController,
                create_transfer_controller
            )
            
            # 注册传输恢复服务
            if self.config.enable_resilience:
                self.container.register_singleton(
                    TransferResilienceService,
                    lambda: TransferResilienceService(self.container)
                )
            
            # 注册传输事件处理器
            self.container.register_singleton(
                TransferEventProcessor,
                lambda: TransferEventProcessor(self.container)
            )
            
            self.deployment_status['transfer_services'] = True
            logger.info("✅ 传输服务注册完成")
            
        except Exception as e:
            logger.error(f"❌ 传输服务注册失败: {str(e)}")
            self.deployment_status['transfer_services'] = False
            raise
    
    async def _integrate_work_queue_processor(self):
        """集成工作队列处理器"""
        logger.info("⚙️  集成工作队列处理器...")
        
        try:
            work_queue_processor = self.container.get(WorkQueueProcessor)
            transfer_event_processor = self.container.get(TransferEventProcessor)
            
            # 注册传输相关的任务处理器
            transfer_handlers = {
                'upload_requested': transfer_event_processor.handle_upload_requested,
                'upload_chunk_completed': transfer_event_processor.handle_upload_chunk_completed,
                'upload_completed': transfer_event_processor.handle_upload_completed,
                'download_requested': transfer_event_processor.handle_download_requested,
                'download_chunk_completed': transfer_event_processor.handle_download_chunk_completed,
                'download_completed': transfer_event_processor.handle_download_completed,
                'transfer_failed': transfer_event_processor.handle_transfer_failed,
                'transfer_resumed': transfer_event_processor.handle_transfer_resumed,
                'compression_completed': transfer_event_processor.handle_compression_completed,
            }
            
            # 注册处理器到工作队列
            for task_type, handler in transfer_handlers.items():
                work_queue_processor.register_handler(task_type, handler)
                logger.info(f"  注册处理器: {task_type}")
            
            self.deployment_status['work_queue_integration'] = True
            logger.info("✅ 工作队列处理器集成完成")
            
        except Exception as e:
            logger.error(f"❌ 工作队列处理器集成失败: {str(e)}")
            self.deployment_status['work_queue_integration'] = False
            raise
    
    async def _integrate_cache_service(self):
        """集成缓存服务"""
        logger.info("💾 集成缓存服务...")
        
        try:
            cache_service = self.container.get(MultiLayerCacheService)
            
            # 为传输架构配置缓存策略
            transfer_cache_config = {
                'transfer_sessions': {
                    'ttl': self.config.cache_ttl_hours * 3600,
                    'max_size': 1000,
                    'eviction_policy': 'lru'
                },
                'compression_results': {
                    'ttl': 7 * 24 * 3600,  # 7天
                    'max_size': 500,
                    'eviction_policy': 'lru'
                },
                'transfer_metadata': {
                    'ttl': 24 * 3600,  # 24小时
                    'max_size': 2000,
                    'eviction_policy': 'lru'
                }
            }
            
            # 配置缓存命名空间
            for namespace, config in transfer_cache_config.items():
                await cache_service.configure_namespace(namespace, config)
                logger.info(f"  配置缓存命名空间: {namespace}")
            
            self.deployment_status['cache_integration'] = True
            logger.info("✅ 缓存服务集成完成")
            
        except Exception as e:
            logger.error(f"❌ 缓存服务集成失败: {str(e)}")
            self.deployment_status['cache_integration'] = False
            raise
    
    async def _register_api_routes(self):
        """注册API路由"""
        logger.info("🌐 注册API路由...")
        
        try:
            # 这里需要与现有的FastAPI应用集成
            # 在实际部署中，这会在main.py中处理
            
            # 记录需要注册的路由
            api_routes = [
                "/api/v1/transfer/upload/prepare",
                "/api/v1/transfer/upload/chunk",
                "/api/v1/transfer/upload/complete",
                "/api/v1/transfer/download/prepare", 
                "/api/v1/transfer/download/chunk",
                "/api/v1/transfer/download/complete",
                "/api/v1/transfer/sessions",
                "/api/v1/transfer/status",
                "/api/v1/transfer/batch/upload",
                "/api/v1/transfer/batch/download",
                "/api/v1/transfer/compress",
                "/api/v1/transfer/decompress",
            ]
            
            logger.info(f"  准备注册 {len(api_routes)} 个API端点")
            for route in api_routes:
                logger.info(f"    {route}")
            
            self.deployment_status['api_routes'] = True
            logger.info("✅ API路由注册完成")
            
        except Exception as e:
            logger.error(f"❌ API路由注册失败: {str(e)}")
            self.deployment_status['api_routes'] = False
            raise
    
    async def _start_background_services(self):
        """启动后台服务"""
        logger.info("🏃 启动后台服务...")
        
        try:
            # 启动传输恢复服务的健康检查
            if self.config.enable_resilience:
                resilience_service = self.container.get(TransferResilienceService)
                
                # 启动健康检查任务
                asyncio.create_task(
                    self._run_health_check_loop(resilience_service)
                )
                logger.info("  启动传输恢复健康检查")
            
            # 启动传输会话清理任务
            asyncio.create_task(
                self._run_session_cleanup_loop()
            )
            logger.info("  启动传输会话清理任务")
            
            # 启动压缩统计收集任务
            asyncio.create_task(
                self._run_compression_stats_collection()
            )
            logger.info("  启动压缩统计收集任务")
            
            self.deployment_status['background_services'] = True
            logger.info("✅ 后台服务启动完成")
            
        except Exception as e:
            logger.error(f"❌ 后台服务启动失败: {str(e)}")
            self.deployment_status['background_services'] = False
            raise
    
    async def _run_health_check_loop(self, resilience_service: TransferResilienceService):
        """运行健康检查循环"""
        while True:
            try:
                await asyncio.sleep(self.config.health_check_interval_seconds)
                
                health_result = await resilience_service.health_check()
                if not health_result.healthy:
                    logger.warning(f"⚠️  传输系统健康检查警告: {health_result.message}")
                    
                    # 尝试自动恢复
                    await resilience_service.auto_recover_system()
                
            except Exception as e:
                logger.error(f"❌ 健康检查循环错误: {str(e)}")
                await asyncio.sleep(60)  # 错误时等待更长时间
    
    async def _run_session_cleanup_loop(self):
        """运行传输会话清理循环"""
        while True:
            try:
                await asyncio.sleep(3600)  # 每小时运行一次
                
                # 清理过期的传输会话
                conn = self.container.get_sqlite_connection()
                cursor = conn.cursor()
                
                # 删除7天前创建的已完成会话
                cursor.execute("""
                    DELETE FROM transfer_sessions 
                    WHERE status IN ('COMPLETED', 'FAILED') 
                    AND created_at < datetime('now', '-7 days')
                """)
                
                # 删除相关的块记录
                cursor.execute("""
                    DELETE FROM transfer_chunks 
                    WHERE session_id NOT IN (SELECT session_id FROM transfer_sessions)
                """)
                
                deleted_sessions = cursor.rowcount
                conn.commit()
                conn.close()
                
                if deleted_sessions > 0:
                    logger.info(f"🧹 清理了 {deleted_sessions} 个过期传输会话")
                
            except Exception as e:
                logger.error(f"❌ 会话清理循环错误: {str(e)}")
                await asyncio.sleep(3600)
    
    async def _run_compression_stats_collection(self):
        """运行压缩统计收集"""
        while True:
            try:
                await asyncio.sleep(1800)  # 每30分钟运行一次
                
                # 收集和分析压缩统计数据
                conn = self.container.get_sqlite_connection()
                cursor = conn.cursor()
                
                # 计算最近24小时的压缩统计
                cursor.execute("""
                    SELECT 
                        compression_level,
                        language_family,
                        AVG(compression_ratio) as avg_ratio,
                        AVG(duration_seconds) as avg_duration,
                        COUNT(*) as operation_count
                    FROM compression_stats 
                    WHERE created_at > datetime('now', '-24 hours')
                    GROUP BY compression_level, language_family
                """)
                
                stats = cursor.fetchall()
                conn.close()
                
                if stats:
                    logger.info("📊 压缩统计摘要 (最近24小时):")
                    for row in stats:
                        level, family, avg_ratio, avg_duration, count = row
                        logger.info(f"  {level}-{family}: {avg_ratio:.1%} 压缩率, "
                                  f"{avg_duration:.2f}s 平均耗时, {count} 次操作")
                
            except Exception as e:
                logger.error(f"❌ 压缩统计收集错误: {str(e)}")
                await asyncio.sleep(1800)
    
    async def _verify_deployment(self):
        """验证部署"""
        logger.info("🔍 验证传输架构部署...")
        
        try:
            # 检查所有关键服务是否可用
            services_to_check = [
                TranslationDataExtractor,
                LocalizedCompressionService,
                FileTransferService,
                TransferController,
                TransferEventProcessor
            ]
            
            for service_class in services_to_check:
                service = self.container.get(service_class)
                if service is None:
                    raise Exception(f"服务 {service_class.__name__} 未正确注册")
                logger.info(f"  ✅ {service_class.__name__} 服务正常")
            
            # 检查数据库表
            conn = self.container.get_sqlite_connection()
            cursor = conn.cursor()
            
            required_tables = ['transfer_sessions', 'transfer_chunks', 'compression_stats']
            for table in required_tables:
                cursor.execute(f"SELECT name FROM sqlite_master WHERE type='table' AND name='{table}'")
                if not cursor.fetchone():
                    raise Exception(f"数据库表 {table} 不存在")
                logger.info(f"  ✅ 数据库表 {table} 存在")
            
            conn.close()
            
            # 验证部署状态
            failed_components = [k for k, v in self.deployment_status.items() if not v]
            if failed_components:
                raise Exception(f"以下组件部署失败: {failed_components}")
            
            logger.info("✅ 传输架构部署验证通过")
            return True
            
        except Exception as e:
            logger.error(f"❌ 部署验证失败: {str(e)}")
            raise
    
    async def _rollback_deployment(self):
        """回滚部署"""
        logger.warning("🔙 开始回滚传输架构部署...")
        
        try:
            # 停止后台服务
            # 注意：实际实现中需要保存任务引用以便取消
            
            # 清理注册的服务
            services_to_cleanup = [
                TransferEventProcessor,
                TransferResilienceService,
                TransferController,
                FileTransferService,
                LocalizedCompressionService,
                TranslationDataExtractor
            ]
            
            for service_class in services_to_cleanup:
                try:
                    if hasattr(self.container, 'unregister'):
                        self.container.unregister(service_class)
                    logger.info(f"  回滚服务: {service_class.__name__}")
                except:
                    pass
            
            logger.warning("⚠️  传输架构部署已回滚")
            
        except Exception as e:
            logger.error(f"❌ 部署回滚失败: {str(e)}")


def get_default_deployment_config() -> DeploymentConfig:
    """获取默认部署配置"""
    return DeploymentConfig(
        enable_transfer_services=True,
        enable_compression=True,
        enable_resilience=True,
        max_concurrent_transfers=8,
        max_concurrent_downloads=12,
        chunk_size_mb=4,
        compression_level="balanced",
        cache_ttl_hours=24,
        retry_max_attempts=3,
        health_check_interval_seconds=60
    )


async def deploy_to_existing_application(container: DIContainer, config: DeploymentConfig = None):
    """部署到现有应用程序"""
    if config is None:
        config = get_default_deployment_config()
    
    deployer = TransmissionArchitectureDeployer(config)
    return await deployer.deploy_transmission_architecture(container)


# FastAPI应用集成示例
def integrate_with_fastapi_app(app, container: DIContainer):
    """与FastAPI应用集成"""
    # 包含传输路由
    app.include_router(transfer_router, prefix="/api/v1")
    
    # 添加启动事件
    @app.on_event("startup")
    async def startup_event():
        logger.info("🚀 启动传输架构...")
        await deploy_to_existing_application(container)
        logger.info("✅ 传输架构启动完成")
    
    @app.on_event("shutdown")
    async def shutdown_event():
        logger.info("🛑 关闭传输架构...")
        # 这里可以添加清理逻辑
        logger.info("✅ 传输架构关闭完成")


if __name__ == "__main__":
    """
    独立部署测试
    
    运行方式:
    cd TH-Suite/apps/mc_l10n/backend/
    python deploy_transmission_architecture.py
    """
    async def test_deployment():
        # 模拟容器
        class MockContainer:
            def __init__(self):
                self._services = {}
            
            def register_singleton(self, service_class, factory):
                self._services[service_class] = factory
            
            def get(self, service_class):
                if service_class in self._services:
                    return self._services[service_class]()
                return None
            
            def get_sqlite_connection(self):
                import sqlite3
                return sqlite3.connect(":memory:")
        
        container = MockContainer()
        config = get_default_deployment_config()
        
        deployer = TransmissionArchitectureDeployer(config)
        
        try:
            await deployer.deploy_transmission_architecture(container)
            print("🎉 部署测试完成")
        except Exception as e:
            print(f"❌ 部署测试失败: {str(e)}")
    
    asyncio.run(test_deployment())