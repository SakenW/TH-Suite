# apps/mc-l10n/backend/src/mc_l10n/application/services/scan_service.py
"""
扫描应用服务

应用层服务，负责编排扫描业务流程，协调各个组件完成复杂的扫描任务。
基于新的架构设计，遵循严格的分层原则。
"""

from __future__ import annotations

import asyncio
from collections.abc import Callable
from pathlib import Path
from typing import Any
from uuid import UUID, uuid4

from packages.core import (
    LoaderType,
    ProjectAlreadyExistsError,
    ProjectType,
    ScanError,
    Task,
    TaskManager,
    TaskStatus,
    get_config,
)

from src.mc_l10n.domain.scan_models import (
    ModInfo,
    ProjectInfo,
    ScanProgress,
    ScanResult,
)
from src.mc_l10n.infrastructure.parsers import ParserFactory
from src.mc_l10n.infrastructure.scanners import (
    MinecraftModScanner,
    MinecraftProjectScanner,
)


class ScanService:
    """扫描服务

    负责管理项目和MOD的扫描任务，提供高级扫描接口
    """

    def __init__(
        self,
        project_scanner: MinecraftProjectScanner | None = None,
        mod_scanner: MinecraftModScanner | None = None,
        parser_factory: ParserFactory | None = None,
        task_manager: TaskManager | None = None,
    ):
        self.config = get_config()
        self.project_scanner = project_scanner or MinecraftProjectScanner()
        self.mod_scanner = mod_scanner or MinecraftModScanner(parser_factory)
        self.task_manager = task_manager

        # 缓存已扫描的项目
        self._project_cache: dict[str, ProjectInfo] = {}
        self._active_scans: dict[UUID, Task] = {}

    async def start_project_scan(
        self, path: Path, callback: Callable[[ScanProgress], None] | None = None
    ) -> UUID:
        """启动项目扫描任务

        Args:
            path: 项目路径
            callback: 进度回调函数

        Returns:
            任务ID
        """
        # 检查路径
        if not path.exists():
            raise ScanError(f"Path does not exist: {path}")

        # 生成项目指纹
        project_fingerprint = self._generate_project_fingerprint(path)

        # 检查是否已有相同项目在扫描
        for task_id, task in self._active_scans.items():
            if task.payload.get("project_fingerprint") == project_fingerprint:
                if task.status in [TaskStatus.PENDING, TaskStatus.IN_PROGRESS]:
                    raise ProjectAlreadyExistsError(str(path))

        # 创建扫描任务
        task_id = uuid4()

        if self.task_manager:
            # 使用任务管理器
            task_id = await self.task_manager.submit_task(
                task_type="project_scan",
                payload={
                    "path": str(path),
                    "project_fingerprint": project_fingerprint,
                    "callback_enabled": callback is not None,
                },
            )

        # 设置进度回调
        if callback:
            self.project_scanner.set_progress_callback(callback)

        # 启动异步扫描
        asyncio.create_task(
            self._execute_project_scan(task_id, path, project_fingerprint)
        )

        return task_id

    async def get_scan_progress(self, task_id: UUID) -> dict[str, Any] | None:
        """获取扫描进度"""
        if self.task_manager:
            task_status = await self.task_manager.get_task_status(task_id)
            # 确保progress是0-1之间的数值
            progress_value = task_status.progress
            if progress_value is not None and progress_value > 1.0:
                progress_value = progress_value / 100.0  # 转换百分比到比例
            
            return {
                "task_id": str(task_id),
                "status": task_status.status.value,
                "progress": progress_value,
                "current_step": task_status.current_step,
                "error_message": task_status.error_message,
            }

        # 检查活跃扫描
        if task_id in self._active_scans:
            task = self._active_scans[task_id]
            # 如果task有scan_progress信息，使用它
            progress_value = getattr(task, 'progress', None)
            if hasattr(task, 'scan_progress') and task.scan_progress:
                progress_value = task.scan_progress.progress_ratio
            
            return {
                "task_id": str(task_id),
                "status": task.status.value,
                "progress": progress_value,
                "current_step": getattr(task, 'current_step', None),
                "error_message": getattr(task, 'error_message', None),
            }

        return None

    async def quick_scan_project(self, path: Path) -> ScanResult:
        """快速扫描项目（同步扫描）

        适用于需要立即获取结果的场景，如项目创建时的预检查
        """
        try:
            # 检测项目类型
            project_type = await self.project_scanner.detect_project_type(path)
            if not project_type:
                return ScanResult(
                    success=False, errors=[f"Unsupported project type: {path}"]
                )

            # 检测加载器类型
            loader_type = await self.project_scanner.detect_loader_type(path)

            # 基本信息扫描
            project_info = ProjectInfo(
                name=path.name,
                path=path,
                project_type=project_type,
                loader_type=loader_type,
            )

            # 快速统计
            if project_type == ProjectType.SINGLE_MOD:
                project_info.mods = [await self._quick_scan_mod(path)]
            else:
                # 整合包 - 统计MOD数量但不深度扫描
                mod_count = await self._count_mod_files(path)
                project_info.mods = [None] * mod_count  # 占位符

            project_info.generate_fingerprint()

            return ScanResult(success=True, project_info=project_info)

        except Exception as e:
            return ScanResult(success=False, errors=[f"Quick scan failed: {e}"])

    async def scan_single_mod(self, mod_path: Path) -> ModInfo:
        """扫描单个MOD文件"""
        return await self.mod_scanner.scan_mod(mod_path)

    async def _execute_project_scan(
        self, task_id: UUID, path: Path, fingerprint: str
    ) -> None:
        """执行项目扫描任务"""
        try:
            # 创建任务记录
            task = Task(
                id=task_id,
                task_type="project_scan",
                status=TaskStatus.IN_PROGRESS,
                payload={"path": str(path), "fingerprint": fingerprint},
            )
            self._active_scans[task_id] = task

            # 设置进度跟踪回调
            def progress_callback(progress: ScanProgress):
                """进度更新回调"""
                task.scan_progress = progress
                task.current_step = progress.current_step
                task.progress = progress.progress_ratio
                
            # 设置进度回调
            self.project_scanner.set_progress_callback(progress_callback)

            # 执行扫描
            result = await self.project_scanner.scan_project(path)

            # 更新任务状态
            if result.success:
                task.status = TaskStatus.COMPLETED
                task.progress = 1.0  # 完成时设置为100%
                task.current_step = "扫描完成"
                task.result = {
                    "project_info": result.project_info,
                    "scan_time": result.scan_time,
                }

                # 缓存结果
                if result.project_info:
                    await self.cache_project(result.project_info)

            else:
                task.status = TaskStatus.FAILED
                task.error_message = "; ".join(result.errors)

        except Exception as e:
            # 更新任务状态为失败
            if task_id in self._active_scans:
                task = self._active_scans[task_id]
                task.status = TaskStatus.FAILED
                task.error_message = f"Scan execution failed: {e}"

    async def cache_project(self, project_info: ProjectInfo) -> None:
        """缓存项目信息"""
        if project_info.fingerprint:
            self._project_cache[project_info.fingerprint] = project_info

    async def _quick_scan_mod(self, mod_path: Path) -> ModInfo:
        """快速扫描MOD（仅基本信息）"""

        try:
            mod_info_data = await self.mod_scanner.extract_mod_info(mod_path)

            return ModInfo(
                mod_id=mod_info_data.get("mod_id", mod_path.stem),
                name=mod_info_data.get("name", mod_path.stem),
                version=mod_info_data.get("version"),
                file_path=mod_path,
                file_size=mod_path.stat().st_size,
                loader_type=LoaderType(mod_info_data["loader_type"])
                if mod_info_data.get("loader_type")
                else None,
            )
        except Exception:
            return ModInfo(
                mod_id=mod_path.stem,
                name=mod_path.stem,
                file_path=mod_path,
                file_size=mod_path.stat().st_size if mod_path.exists() else 0,
            )

    async def _count_mod_files(self, project_path: Path) -> int:
        """统计项目中的MOD文件数量"""
        count = 0
        try:
            from ...domain.scan_models import ModpackScanRule

            modpack_rule = ModpackScanRule()

            mod_dirs = modpack_rule.find_mod_directories(project_path)
            for mod_dir in mod_dirs:
                jar_files = list(mod_dir.glob("*.jar"))
                zip_files = list(mod_dir.glob("*.zip"))
                count += len(jar_files) + len(zip_files)
        except Exception:
            pass

        return count

    def _generate_project_fingerprint(self, path: Path) -> str:
        """生成项目指纹"""
        import hashlib

        content = f"{path.absolute()}"
        return hashlib.sha256(content.encode()).hexdigest()[:16]
