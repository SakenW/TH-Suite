"""
扫描应用服务
将业务逻辑从Interface层分离到Application层
"""

import logging
from datetime import datetime
from typing import Any

from core.di_container import get_database_service, get_scanner_service

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

    async def start_project_scan(
        self, directory: str, incremental: bool = True
    ) -> dict[str, Any]:
        """启动项目扫描

        Args:
            directory: 要扫描的目录路径
            incremental: 是否为增量扫描

        Returns:
            包含扫描ID和状态信息的字典
        """
        await self._ensure_services()

        if not directory:
            raise ValueError("directory参数是必需的")

        if not self._scanner_service:
            raise RuntimeError("扫描服务未初始化")

        try:
            # 使用统一扫描服务启动扫描
            scan_info = await self._scanner_service.start_scan(
                target_path=directory, incremental=incremental, options={}
            )

            logger.info(f"扫描已启动: {directory} (增量: {incremental})")

            return {
                "success": True,
                "message": f"扫描已开始: {directory}",
                "job_id": scan_info["scan_id"],
                "scan_id": scan_info["scan_id"],
                "incremental": incremental,
                "started_at": datetime.now().isoformat(),
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
                from core.ddd_scanner import get_scanner_instance

                scanner = get_scanner_instance()
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

    async def get_scan_results(self, scan_id: str) -> dict[str, Any]:
        """获取扫描结果

        Args:
            scan_id: 扫描ID

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

            return {
                "success": True,
                "data": {
                    "scan_id": scan_id,
                    "mods": mod_list,
                    "language_files": lf_list,
                    "statistics": statistics,
                },
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
