"""
扫描应用服务 (启用缓存功能)
将业务逻辑从Interface层分离到Application层
"""

import logging
import time
from datetime import datetime
from typing import Any

from core.di_container import get_database_service, get_scanner_service, get_database_manager
from infrastructure.services.cache_service import get_cache_service

logger = logging.getLogger(__name__)


class ScanApplicationService:
    """
    扫描应用服务 - 协调扫描相关的业务操作

    这个服务封装了所有与扫描相关的业务逻辑，包括：
    - 启动项目扫描任务
    - 查询扫描状态和进度
    - 获取扫描结果
    - 取消正在进行的扫描
    - 获取数据库统计信息

    使用依赖注入模式获取底层服务，符合Clean Architecture原则。
    """

    def __init__(self):
        self._scanner_service = None
        self._database_service = None
        self._cache_service = None

    async def _ensure_services(self):
        """
        确保服务已初始化

        通过依赖注入容器懒加载获取所需的服务实例。
        这种方式避免了循环依赖问题，提高了系统的可测试性。
        """
        if self._scanner_service is None:
            self._scanner_service = get_scanner_service()
        if self._database_service is None:
            self._database_service = get_database_service()
        if self._cache_service is None:
            db_manager = get_database_manager()
            self._cache_service = get_cache_service(db_manager)

    async def start_project_scan(
        self, directory: str, incremental: bool = True, use_cache: bool = True
    ) -> dict[str, Any]:
        """启动项目扫描 (支持智能缓存)

        Args:
            directory: 要扫描的目录路径
            incremental: 是否为增量扫描
            use_cache: 是否使用缓存功能

        Returns:
            包含扫描ID和状态信息的字典
        """
        await self._ensure_services()

        if not directory:
            raise ValueError("directory参数是必需的")

        if not self._scanner_service:
            raise RuntimeError("扫描服务未初始化")

        try:
            cache_hit = False
            cached_result = None
            
            # 尝试从缓存获取结果
            if use_cache and self._cache_service:
                logger.info(f"检查缓存: {directory}")
                cache_start_time = time.time()
                
                cached_result = await self._cache_service.get_cached_result(directory)
                cache_check_time = time.time() - cache_start_time
                
                if cached_result:
                    cache_hit = True
                    logger.info(f"🚀 缓存命中! {directory} (检查耗时: {cache_check_time:.2f}秒)")
                    
                    # 模拟扫描ID和状态返回
                    scan_id = f"cached_{int(time.time())}"
                    return {
                        "success": True,
                        "message": f"扫描已开始 (缓存): {directory}",
                        "job_id": scan_id,
                        "scan_id": scan_id,
                        "incremental": incremental,
                        "started_at": datetime.now().isoformat(),
                        "cache_hit": True,
                        "cache_result": cached_result
                    }
                else:
                    logger.info(f"缓存未命中: {directory} (检查耗时: {cache_check_time:.2f}秒)")

            # 缓存未命中，执行实际扫描
            logger.info(f"开始实际扫描: {directory}")
            scan_start_time = time.time()
            
            scan_info = await self._scanner_service.start_scan(
                target_path=directory, incremental=incremental, options={}
            )
            
            scan_time = time.time() - scan_start_time
            logger.info(f"扫描已启动: {directory} (增量: {incremental}, 耗时: {scan_time:.2f}秒)")

            return {
                "success": True,
                "message": f"扫描已开始: {directory}",
                "job_id": scan_info["scan_id"],
                "scan_id": scan_info["scan_id"],
                "incremental": incremental,
                "started_at": datetime.now().isoformat(),
                "cache_hit": False,
                "cache_enabled": use_cache
            }

        except Exception as e:
            logger.error(f"启动扫描失败: {e}")
            raise RuntimeError(f"启动扫描失败: {str(e)}")

    async def get_scan_status(self, scan_id: str) -> dict[str, Any]:
        """获取扫描状态

        Args:
            scan_id: 扫描ID

        Returns:
            包含扫描状态信息的字典
        """
        await self._ensure_services()

        if not self._scanner_service:
            return {"success": False, "message": "扫描服务未初始化"}

        try:
            # 使用统一扫描服务获取状态
            status = await self._scanner_service.get_scan_status(scan_id)

            if status:
                # 如果状态中缺少新字段，从 ddd_scanner 的 active_scans 获取
                from core.ddd_scanner_simple import get_scanner_instance
                from pathlib import Path

                # 使用V6 API数据库路径，保持数据库一致性
                v6_db_path = Path(__file__).parent.parent.parent / "data" / "mc_l10n_v6.db"
                scanner = get_scanner_instance(str(v6_db_path))
                if scan_id in scanner.active_scans:
                    scan_data = scanner.active_scans[scan_id]
                    # 补充新的进度字段
                    status.update(
                        {
                            "scan_phase": scan_data.get("scan_phase"),
                            "phase_text": scan_data.get("phase_text"),
                            "current_batch": scan_data.get("current_batch"),
                            "total_batches": scan_data.get("total_batches"),
                            "batch_progress": scan_data.get("batch_progress"),
                            "files_per_second": scan_data.get("files_per_second"),
                            "estimated_remaining_seconds": scan_data.get(
                                "estimated_remaining_seconds"
                            ),
                            "elapsed_seconds": scan_data.get("elapsed_seconds"),
                        }
                    )

                logger.debug(
                    f"返回扫描状态 {scan_id}: status={status.get('status', 'unknown')}"
                )
                return {"success": True, "data": status}

            # 扫描不存在
            logger.warning(f"未找到扫描任务: {scan_id}")
            return {"success": False, "message": "扫描任务未找到"}

        except Exception as e:
            logger.error(f"获取扫描状态失败: {e}")
            return {"success": False, "message": str(e)}

    async def get_scan_results(self, scan_id: str, cache_results: bool = True) -> dict[str, Any]:
        """获取扫描结果

        Args:
            scan_id: 扫描ID
            cache_results: 是否缓存扫描结果，默认为True

        Returns:
            包含扫描结果的字典
        """
        await self._ensure_services()

        if not self._scanner_service:
            return {"success": False, "message": "扫描服务未初始化"}

        try:
            # 获取扫描状态，检查是否完成
            status = await self._scanner_service.get_scan_status(scan_id)

            if not status:
                return {"success": False, "message": "扫描任务不存在"}

            if status.get("status") != "completed":
                return {"success": False, "message": "扫描未完成"}

            # 获取内容项（模组和语言文件）
            mods = await self._scanner_service.get_content_items(
                content_type="mod", limit=500
            )
            language_files = await self._scanner_service.get_content_items(
                content_type="language_file", limit=1000
            )

            # 处理模组数据
            mod_list = []
            for mod in mods:
                mod_data = {
                    "id": mod.get("content_hash", "")[:8],
                    "name": mod.get("name", "Unknown Mod"),
                    "mod_id": mod.get("metadata", {}).get("mod_id", ""),
                    "version": mod.get("metadata", {}).get("version", ""),
                    "file_path": mod.get("metadata", {}).get("file_path", ""),
                    "language_files": 0,
                    "total_keys": 0,
                }
                # 统计该模组的语言文件数
                for lf in language_files:
                    if lf.get("relationships", {}).get("mod_hash") == mod.get(
                        "content_hash"
                    ):
                        mod_data["language_files"] += 1
                        mod_data["total_keys"] += lf.get("metadata", {}).get(
                            "key_count", 0
                        )
                mod_list.append(mod_data)

            # 处理语言文件数据
            lf_list = []
            for lf in language_files[:100]:  # 限制返回前100个
                lf_list.append(
                    {
                        "id": lf.get("content_hash", "")[:8],
                        "file_name": lf.get("name", ""),
                        "language": lf.get("metadata", {}).get("language", "en_us"),
                        "key_count": lf.get("metadata", {}).get("key_count", 0),
                        "mod_id": lf.get("relationships", {}).get("mod_id", ""),
                    }
                )

            # 获取统计信息
            statistics = {
                "total_mods": len(mods),
                "total_language_files": len(language_files),
                "total_keys": sum(
                    lf.get("metadata", {}).get("key_count", 0) for lf in language_files
                ),
                "scan_duration_ms": status.get("duration_seconds", 0) * 1000,
            }

            result_data = {
                "scan_id": scan_id,
                "mods": mod_list,
                "language_files": lf_list,
                "statistics": statistics,
            }

            # 尝试缓存结果（如果启用缓存且有扫描路径信息）
            if cache_results and self._cache_service:
                try:
                    scan_path = status.get("target_path") or status.get("directory")
                    if scan_path:
                        cache_stored = await self._cache_service.store_cached_result(
                            scan_path=scan_path, 
                            result=result_data,
                            ttl_hours=24  # 默认缓存24小时
                        )
                        if cache_stored:
                            logger.info(f"✅ 扫描结果已缓存: {scan_path}")
                        else:
                            logger.warning(f"⚠️ 缓存存储失败: {scan_path}")
                    else:
                        logger.warning(f"⚠️ 无法获取扫描路径，跳过缓存存储")
                except Exception as cache_error:
                    logger.error(f"缓存存储异常: {cache_error}")
                    # 缓存失败不影响主要功能，继续返回结果

            return {
                "success": True,
                "data": result_data,
            }

        except Exception as e:
            logger.error(f"获取扫描结果失败: {e}")
            return {"success": False, "message": str(e)}

    async def cancel_scan(self, scan_id: str) -> dict[str, Any]:
        """取消扫描

        Args:
            scan_id: 扫描ID

        Returns:
            操作结果
        """
        await self._ensure_services()

        if not self._scanner_service:
            return {"success": False, "message": "扫描服务未初始化"}

        try:
            # 使用统一扫描服务取消扫描
            success = await self._scanner_service.cancel_scan(scan_id)

            if success:
                logger.info(f"扫描已取消: {scan_id}")
                return {"success": True, "message": "扫描已取消"}
            else:
                return {"success": False, "message": "扫描任务不存在或已完成"}

        except Exception as e:
            logger.error(f"取消扫描失败: {e}")
            return {"success": False, "message": str(e)}

    async def get_database_statistics(self) -> dict[str, Any]:
        """获取数据库统计信息"""
        await self._ensure_services()

        if not self._database_service:
            return {
                "success": False,
                "error": {"code": "SERVICE_ERROR", "message": "数据库服务未初始化"},
            }

        try:
            stats = await self._database_service.get_statistics()
            return {"success": True, "data": stats}
        except Exception as e:
            logger.error(f"获取数据库统计失败: {e}")
            return {
                "success": False,
                "error": {"code": "STATS_ERROR", "message": str(e)},
            }

    # 缓存管理相关方法

    async def clear_cache(self, scan_path: str = None) -> dict[str, Any]:
        """清理缓存
        
        Args:
            scan_path: 要清理的特定扫描路径，为None时清理所有过期缓存
            
        Returns:
            清理结果
        """
        await self._ensure_services()
        
        if not self._cache_service:
            return {"success": False, "message": "缓存服务未初始化"}
        
        try:
            if scan_path:
                # 清理特定路径的缓存
                success = await self._cache_service.invalidate_cache(scan_path)
                if success:
                    logger.info(f"✅ 已清理缓存: {scan_path}")
                    return {"success": True, "message": f"已清理缓存: {scan_path}"}
                else:
                    return {"success": False, "message": f"未找到要清理的缓存: {scan_path}"}
            else:
                # 清理所有过期缓存
                deleted_count = await self._cache_service.cleanup_expired_cache()
                logger.info(f"✅ 已清理 {deleted_count} 条过期缓存")
                return {
                    "success": True, 
                    "message": f"已清理 {deleted_count} 条过期缓存",
                    "deleted_count": deleted_count
                }
        except Exception as e:
            logger.error(f"清理缓存失败: {e}")
            return {"success": False, "message": str(e)}

    async def get_cache_statistics(self) -> dict[str, Any]:
        """获取缓存统计信息
        
        Returns:
            缓存统计信息
        """
        await self._ensure_services()
        
        if not self._cache_service:
            return {"success": False, "message": "缓存服务未初始化"}
        
        try:
            stats = await self._cache_service.get_cache_stats()
            return {"success": True, "data": stats}
        except Exception as e:
            logger.error(f"获取缓存统计失败: {e}")
            return {"success": False, "message": str(e)}
