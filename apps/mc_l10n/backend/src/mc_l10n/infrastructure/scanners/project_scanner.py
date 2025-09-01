# apps/mc-l10n/backend/src/mc_l10n/infrastructure/scanners/project_scanner.py
"""
项目扫描器

实现项目目录的深度扫描，识别项目类型、MOD文件和语言文件
"""

from __future__ import annotations

import asyncio
import concurrent.futures
import time
from collections.abc import Callable
from pathlib import Path

from packages.core import (
    LoaderType,
    ProjectScanResult,
    ProjectType,
    UnsupportedProjectTypeError,
    get_config,
)

from src.mc_l10n.domain.scan_models import (
    MinecraftModScanRule,
    ModInfo,
    ModpackScanRule,
    ProjectInfo,
    ScanProgress,
    ScanResult,
)
from src.mc_l10n.infrastructure.parsers import ModFileAnalyzer


class MinecraftProjectScanner:
    """Minecraft项目扫描器"""

    def __init__(self, mod_analyzer: ModFileAnalyzer | None = None):
        self.config = get_config()
        self.mod_analyzer = mod_analyzer or ModFileAnalyzer()
        self.mod_rule = MinecraftModScanRule()
        self.modpack_rule = ModpackScanRule()

        # 扫描配置
        self.max_file_size = self.config.scan.max_file_size
        self.parallel_scan = self.config.scan.parallel_scan
        self.max_workers = self.config.scan.max_parallel_workers
        self.ignore_patterns = set(self.config.scan.ignore_patterns)

        # 进度回调
        self.progress_callback: Callable[[ScanProgress], None] | None = None

    def set_progress_callback(self, callback: Callable[[ScanProgress], None]) -> None:
        """设置进度回调函数"""
        self.progress_callback = callback

    async def scan_project(self, path: Path) -> ScanResult:
        """扫描项目目录"""
        start_time = time.time()

        try:
            # 验证路径
            if not path.exists():
                return ScanResult(
                    success=False, errors=[f"Path does not exist: {path}"]
                )

            if not path.is_dir():
                return ScanResult(
                    success=False, errors=[f"Path is not a directory: {path}"]
                )

            # 检测项目类型
            project_type = await self.detect_project_type(path)
            if not project_type:
                return ScanResult(
                    success=False, errors=[f"Unsupported project type at: {path}"]
                )

            # 创建进度跟踪
            progress = ScanProgress(current_step="初始化扫描")
            self._notify_progress(progress)

            # 根据项目类型执行扫描
            if project_type == ProjectType.MODPACK:
                project_info = await self._scan_modpack(path, progress)
            elif project_type == ProjectType.SINGLE_MOD:
                project_info = await self._scan_single_mod(path, progress)
            else:
                raise UnsupportedProjectTypeError(str(path), project_type.value)

            # 完成扫描
            scan_time = time.time() - start_time
            progress.current_step = "扫描完成"
            self._notify_progress(progress)

            return ScanResult(
                success=True, project_info=project_info, scan_time=scan_time
            )

        except Exception as e:
            scan_time = time.time() - start_time
            return ScanResult(
                success=False, errors=[f"Scan failed: {e}"], scan_time=scan_time
            )

    async def detect_project_type(self, path: Path) -> ProjectType | None:
        """检测项目类型"""
        # 检查是否为单个MOD文件
        if path.is_file() and self.mod_rule.matches(path):
            return ProjectType.SINGLE_MOD

        # 检查是否为整合包目录
        if path.is_dir() and self.modpack_rule.matches(path):
            return ProjectType.MODPACK

        return None

    async def detect_loader_type(self, path: Path) -> LoaderType | None:
        """检测加载器类型"""
        if path.is_file():
            # 单MOD文件
            analysis = self.mod_analyzer.analyze_mod_archive(path)
            loader_str = analysis.get("loader_type")
            if loader_str:
                return LoaderType(loader_str)

        elif path.is_dir():
            # 整合包目录
            mod_dirs = self.modpack_rule.find_mod_directories(path)
            loader_counts = {}

            for mod_dir in mod_dirs:
                for mod_file in mod_dir.glob("*.jar"):
                    if mod_file.stat().st_size > self.max_file_size:
                        continue

                    try:
                        analysis = self.mod_analyzer.analyze_mod_archive(mod_file)
                        loader_str = analysis.get("loader_type")
                        if loader_str:
                            loader_counts[loader_str] = (
                                loader_counts.get(loader_str, 0) + 1
                            )
                    except Exception:
                        continue

            # 返回最常见的加载器类型
            if loader_counts:
                most_common = max(loader_counts.items(), key=lambda x: x[1])
                return LoaderType(most_common[0])

        return None

    async def _scan_modpack(self, path: Path, progress: ScanProgress) -> ProjectInfo:
        """扫描整合包项目"""
        progress.current_step = "分析整合包结构"
        self._notify_progress(progress)

        # 创建项目信息
        project_info = ProjectInfo(
            name=path.name,
            path=path,
            project_type=ProjectType.MODPACK,
            loader_type=await self.detect_loader_type(path),
        )

        # 查找MOD目录
        mod_dirs = self.modpack_rule.find_mod_directories(path)

        # 扫描所有MOD文件
        all_mod_files = []
        for mod_dir in mod_dirs:
            mod_files = list(mod_dir.glob("*.jar")) + list(mod_dir.glob("*.zip"))
            all_mod_files.extend(mod_files)

        # 过滤文件大小
        valid_mod_files = [
            f for f in all_mod_files if f.stat().st_size <= self.max_file_size
        ]

        progress.total_files = len(valid_mod_files)
        progress.current_step = "扫描MOD文件"
        self._notify_progress(progress)

        # 并行扫描MOD文件
        if self.parallel_scan and len(valid_mod_files) > 1:
            mods = await self._scan_mods_parallel(valid_mod_files, progress)
        else:
            mods = await self._scan_mods_sequential(valid_mod_files, progress)

        # 添加MOD到项目
        for mod_info in mods:
            if mod_info:  # 过滤失败的扫描
                project_info.add_mod(mod_info)

        # 生成项目指纹
        project_info.generate_fingerprint()

        return project_info

    async def _scan_single_mod(self, path: Path, progress: ScanProgress) -> ProjectInfo:
        """扫描单个MOD文件"""
        progress.current_step = "分析MOD文件"
        progress.total_files = 1
        self._notify_progress(progress)

        # 创建项目信息
        project_info = ProjectInfo(
            name=path.stem,
            path=path.parent,  # 项目路径是文件所在目录
            project_type=ProjectType.SINGLE_MOD,
            loader_type=await self.detect_loader_type(path),
        )

        # 扫描MOD
        mod_info = await self._scan_single_mod_file(path, progress)
        if mod_info:
            project_info.add_mod(mod_info)

        # 生成项目指纹
        project_info.generate_fingerprint()

        return project_info

    async def _scan_mods_parallel(
        self, mod_files: list[Path], progress: ScanProgress
    ) -> list[ModInfo | None]:
        """并行扫描MOD文件"""
        with concurrent.futures.ThreadPoolExecutor(
            max_workers=self.max_workers
        ) as executor:
            # 提交任务
            futures = []
            for mod_file in mod_files:
                future = executor.submit(self._scan_mod_sync, mod_file)
                futures.append(future)

            # 收集结果
            results = []
            for future in concurrent.futures.as_completed(futures):
                try:
                    result = future.result()
                    results.append(result)

                    # 更新进度
                    progress.processed_files += 1
                    progress.current_file = (
                        str(result.file_path) if result else "unknown"
                    )
                    self._notify_progress(progress)

                except Exception as e:
                    results.append(None)
                    progress.add_error(f"Failed to scan MOD: {e}")
                    progress.processed_files += 1
                    self._notify_progress(progress)

            return results

    async def _scan_mods_sequential(
        self, mod_files: list[Path], progress: ScanProgress
    ) -> list[ModInfo | None]:
        """顺序扫描MOD文件"""
        results = []

        for mod_file in mod_files:
            try:
                result = await self._scan_single_mod_file(mod_file, progress)
                results.append(result)
            except Exception as e:
                results.append(None)
                progress.add_error(f"Failed to scan {mod_file}: {e}")

            progress.processed_files += 1
            progress.current_file = str(mod_file)
            self._notify_progress(progress)

        return results

    def _scan_mod_sync(self, mod_file: Path) -> ModInfo | None:
        """同步扫描单个MOD文件（用于线程池）"""
        try:
            analysis = self.mod_analyzer.analyze_mod_archive(mod_file)

            if analysis["errors"]:
                return None

            mod_info = ModInfo(
                mod_id=analysis["mod_info"].get("mod_id", mod_file.stem),
                name=analysis["mod_info"].get("name", mod_file.stem),
                version=analysis["mod_info"].get("version"),
                description=analysis["mod_info"].get("description"),
                authors=analysis["mod_info"].get("authors", []),
                file_path=mod_file,
                file_size=analysis["file_size"],
                loader_type=LoaderType(analysis["loader_type"])
                if analysis["loader_type"]
                else None,
            )

            # 添加语言文件信息（简化版，详细解析在后续步骤）
            for lang_file in analysis["language_files"]:
                mod_info.supported_locales.add(lang_file.get("locale", "unknown"))

            return mod_info

        except Exception:
            return None

    async def _scan_single_mod_file(
        self, mod_file: Path, progress: ScanProgress
    ) -> ModInfo | None:
        """扫描单个MOD文件"""
        try:
            # 在线程池中执行同步操作
            loop = asyncio.get_event_loop()
            with concurrent.futures.ThreadPoolExecutor() as executor:
                result = await loop.run_in_executor(
                    executor, self._scan_mod_sync, mod_file
                )

            return result

        except Exception as e:
            progress.add_error(f"Failed to scan {mod_file}: {e}")
            return None

    def _notify_progress(self, progress: ScanProgress) -> None:
        """通知进度更新"""
        if self.progress_callback:
            try:
                self.progress_callback(progress)
            except Exception:
                # 进度回调失败不应该影响扫描
                pass

    def _should_ignore_file(self, file_path: Path) -> bool:
        """判断是否应该忽略文件"""
        file_str = str(file_path).lower()

        for pattern in self.ignore_patterns:
            if pattern in file_str:
                return True

        return False


class ProjectScanner:
    """项目扫描器"""

    def __init__(self):
        self.scanner = MinecraftProjectScanner()

    async def scan_project(self, path: Path) -> ProjectScanResult:
        """扫描项目目录"""

        result = await self.scanner.scan_project(path)

        if result.success and result.project_info:
            project_info = result.project_info

            return ProjectScanResult(
                project_type=project_info.project_type,
                loader_type=project_info.loader_type,
                name=project_info.name,
                path=project_info.path,
                mod_files=[mod.file_path for mod in project_info.mods if mod.file_path],
                total_mods=project_info.total_mods,
                estimated_segments=project_info.estimated_segments,
                scan_issues=result.errors + result.warnings,
            )
        else:
            return ProjectScanResult(
                project_type=ProjectType.MODPACK,  # 默认值
                loader_type=None,
                name="Unknown",
                path=path,
                scan_issues=result.errors,
            )

    async def detect_project_type(self, path: Path) -> str | None:
        """检测项目类型"""
        project_type = await self.scanner.detect_project_type(path)
        return project_type.value if project_type else None

    async def detect_loader_type(self, path: Path) -> str | None:
        """检测加载器类型"""
        loader_type = await self.scanner.detect_loader_type(path)
        return loader_type.value if loader_type else None
