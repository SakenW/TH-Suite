# packages/application/services.py
"""
统一应用服务实现

提供游戏无关的高级业务服务，协调各个领域组件完成复杂的业务操作。
这些服务可以被所有游戏项目复用。
"""

from __future__ import annotations

import asyncio
import time
from collections.abc import Callable
from pathlib import Path
from typing import Any
from uuid import UUID, uuid4

from ..core.interfaces import (
    Cache,
    GamePluginRegistry,
    ParseResult,
    ProjectScanResult,
    TaskManager,
    UnitOfWork,
)


class UnifiedProjectManagementService:
    """统一的项目管理服务实现

    提供游戏无关的项目管理功能，通过游戏插件系统支持多种游戏类型
    """

    def __init__(
        self,
        plugin_registry: GamePluginRegistry,
        task_manager: TaskManager | None = None,
        cache: Cache[Any] | None = None,
        uow: UnitOfWork | None = None,
    ):
        self.plugin_registry = plugin_registry
        self.task_manager = task_manager
        self.cache = cache
        self.uow = uow

        # 缓存已扫描的项目
        self._project_cache: dict[str, Any] = {}
        self._active_scans: dict[UUID, dict[str, Any]] = {}

    async def scan_and_import_project(
        self, path: Path, game_type: str | None = None
    ) -> ProjectScanResult:
        """扫描并导入项目

        Args:
            path: 项目路径
            game_type: 指定的游戏类型，如果为 None 则自动检测

        Returns:
            项目扫描结果
        """
        start_time = time.time()

        try:
            # 检查路径是否存在
            if not path.exists():
                return self._create_failed_result(
                    path, [f"Path does not exist: {path}"], start_time
                )

            # 自动检测游戏类型
            if not game_type:
                game_type = self.plugin_registry.detect_game_type(path)
                if not game_type:
                    return self._create_failed_result(
                        path, [f"Unsupported project type at: {path}"], start_time
                    )

            # 获取游戏插件
            plugin = self.plugin_registry.get_plugin(game_type)
            if not plugin:
                return self._create_failed_result(
                    path, [f"Game plugin not found: {game_type}"], start_time
                )

            # 创建扫描器并执行扫描
            scanner = plugin.create_project_scanner()
            scan_result = await scanner.scan_project(path)

            # 缓存扫描结果
            if scan_result.success and hasattr(scan_result, "fingerprint"):
                fingerprint = getattr(scan_result, "fingerprint", None)
                if fingerprint:
                    self._project_cache[fingerprint] = scan_result

            return scan_result

        except Exception as e:
            return self._create_failed_result(path, [f"Scan failed: {e}"], start_time)

    async def start_async_scan(
        self,
        path: Path,
        game_type: str | None = None,
        progress_callback: Callable[..., None] | None = None,
    ) -> UUID:
        """启动异步项目扫描任务

        Args:
            path: 项目路径
            game_type: 游戏类型
            progress_callback: 进度回调函数

        Returns:
            任务ID
        """
        task_id = uuid4()

        # 使用任务管理器
        if self.task_manager:
            task_id = await self.task_manager.submit_task(
                task_type="project_scan",
                payload={
                    "path": str(path),
                    "game_type": game_type,
                    "has_callback": progress_callback is not None,
                },
            )

        # 启动后台扫描任务
        asyncio.create_task(
            self._execute_async_scan(task_id, path, game_type, progress_callback)
        )

        return task_id

    async def get_scan_progress(self, task_id: UUID) -> dict[str, Any] | None:
        """获取扫描进度

        Args:
            task_id: 任务ID

        Returns:
            进度信息，如果任务不存在则返回 None
        """
        if self.task_manager:
            task_status = await self.task_manager.get_task_status(task_id)
            if task_status:
                return {
                    "task_id": str(task_id),
                    "status": task_status.status,
                    "progress": task_status.progress,
                    "current_step": task_status.current_step,
                    "error_message": task_status.error_message,
                }

        # 检查本地活跃扫描
        if task_id in self._active_scans:
            scan_info = self._active_scans[task_id]
            return {
                "task_id": str(task_id),
                "status": scan_info.get("status", "unknown"),
                "progress": scan_info.get("progress", 0.0),
                "current_step": scan_info.get("current_step", ""),
                "error_message": scan_info.get("error_message"),
            }

        return None

    async def get_project_details(self, project_id: UUID) -> dict[str, Any] | None:
        """获取项目详情

        Args:
            project_id: 项目ID

        Returns:
            项目详情，如果不存在则返回 None
        """
        # 这里需要根据具体的项目仓储实现
        # 目前返回 None，待后续实现具体的仓储层
        return None

    async def update_project(self, project_id: UUID, updates: dict[str, Any]) -> bool:
        """更新项目

        Args:
            project_id: 项目ID
            updates: 更新数据

        Returns:
            是否更新成功
        """
        # 这里需要根据具体的项目仓储实现
        # 目前返回 False，待后续实现具体的仓储层
        return False

    async def delete_project(self, project_id: UUID) -> bool:
        """删除项目

        Args:
            project_id: 项目ID

        Returns:
            是否删除成功
        """
        # 这里需要根据具体的项目仓储实现
        # 目前返回 False，待后续实现具体的仓储层
        return False

    async def _execute_async_scan(
        self,
        task_id: UUID,
        path: Path,
        game_type: str | None,
        progress_callback: callable | None,
    ) -> None:
        """执行异步扫描任务

        Args:
            task_id: 任务ID
            path: 项目路径
            game_type: 游戏类型
            progress_callback: 进度回调函数
        """
        # 记录任务信息
        self._active_scans[task_id] = {
            "status": "in_progress",
            "progress": 0.0,
            "current_step": "初始化扫描",
            "error_message": None,
        }

        try:
            # 更新进度
            self._update_scan_progress(task_id, 0.1, "检测游戏类型")

            # 执行扫描
            result = await self.scan_and_import_project(path, game_type)

            # 更新最终状态
            if result.success:
                self._active_scans[task_id].update(
                    {
                        "status": "completed",
                        "progress": 1.0,
                        "current_step": "扫描完成",
                        "result": result,
                    }
                )
            else:
                self._active_scans[task_id].update(
                    {
                        "status": "failed",
                        "progress": 0.0,
                        "current_step": "扫描失败",
                        "error_message": "; ".join(result.errors),
                    }
                )

        except Exception as e:
            self._active_scans[task_id].update(
                {
                    "status": "failed",
                    "progress": 0.0,
                    "current_step": "扫描异常",
                    "error_message": str(e),
                }
            )

    def _update_scan_progress(
        self, task_id: UUID, progress: float, current_step: str
    ) -> None:
        """更新扫描进度

        Args:
            task_id: 任务ID
            progress: 进度值 (0.0-1.0)
            current_step: 当前步骤描述
        """
        if task_id in self._active_scans:
            self._active_scans[task_id].update(
                {"progress": progress, "current_step": current_step}
            )

    def _create_failed_result(
        self, path: Path, errors: list[str], start_time: float
    ) -> ProjectScanResult:
        """创建失败的扫描结果

        Args:
            path: 项目路径
            errors: 错误列表
            start_time: 开始时间

        Returns:
            失败的扫描结果
        """

        # 创建一个简单的失败结果对象
        class FailedScanResult:
            def __init__(self):
                self.success = False
                self.project_type = None
                self.loader_type = None
                self.name = path.name if path else "Unknown"
                self.path = path
                self.total_files = 0
                self.estimated_segments = 0
                self.supported_locales = []
                self.scan_time = time.time() - start_time
                self.errors = errors
                self.warnings = []

        return FailedScanResult()


class UnifiedFileProcessingService:
    """统一的文件处理服务实现

    提供游戏无关的文件解析和处理功能
    """

    def __init__(
        self, plugin_registry: GamePluginRegistry, cache: Cache[Any] | None = None
    ):
        self.plugin_registry = plugin_registry
        self.cache = cache

    async def parse_file(self, file_path: Path) -> ParseResult[Any]:
        """解析文件

        Args:
            file_path: 文件路径

        Returns:
            解析结果
        """
        # 检查缓存
        cache_key = f"parse:{file_path.as_posix()}:{file_path.stat().st_mtime}"
        if self.cache:
            cached_result = await self.cache.get(cache_key)
            if cached_result:
                return cached_result

        # 根据文件扩展名找到支持的插件
        extension = file_path.suffix.lower()
        supporting_plugins = self.plugin_registry.get_plugins_by_file_extension(
            extension
        )

        if not supporting_plugins:
            return self._create_failed_parse_result(
                f"No parser found for file extension: {extension}"
            )

        # 尝试使用第一个支持的插件进行解析
        plugin = supporting_plugins[0]
        parser_factory = plugin.create_parser_factory()
        parser = parser_factory.get_parser(file_path)

        if not parser:
            return self._create_failed_parse_result(
                f"Parser not available for file: {file_path}"
            )

        try:
            result = await parser.parse(file_path)

            # 缓存解析结果
            if self.cache and result.success:
                await self.cache.set(cache_key, result, ttl_seconds=3600)  # 1小时

            return result

        except Exception as e:
            return self._create_failed_parse_result(f"Parse failed: {e}")

    async def batch_parse_files(self, file_paths: list[Path]) -> list[ParseResult[Any]]:
        """批量解析文件

        Args:
            file_paths: 文件路径列表

        Returns:
            解析结果列表
        """
        tasks = []
        for file_path in file_paths:
            task = self.parse_file(file_path)
            tasks.append(task)

        results = await asyncio.gather(*tasks, return_exceptions=True)

        # 处理异常情况
        processed_results = []
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                processed_results.append(
                    self._create_failed_parse_result(f"Exception: {result}")
                )
            else:
                processed_results.append(result)

        return processed_results

    async def export_translations(
        self, project_id: UUID, format_type: str, output_path: Path
    ) -> bool:
        """导出翻译

        Args:
            project_id: 项目ID
            format_type: 导出格式类型
            output_path: 输出路径

        Returns:
            是否导出成功
        """
        # 这里需要实现具体的翻译导出逻辑
        # 目前返回 False，待后续实现
        return False

    def _create_failed_parse_result(self, error_message: str) -> ParseResult[Any]:
        """创建失败的解析结果

        Args:
            error_message: 错误消息

        Returns:
            失败的解析结果
        """

        class FailedParseResult:
            def __init__(self):
                self.success = False
                self.content = None
                self.segments = []
                self.encoding = "utf-8"
                self.errors = [error_message]
                self.warnings = []
                self.metadata = {}

        return FailedParseResult()
