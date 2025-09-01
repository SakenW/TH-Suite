"""
模组扫描命令

实现模组文件的扫描、解析、分析等操作命令
"""

from dataclasses import dataclass
from datetime import datetime
from typing import Any

from domain.models.value_objects.file_path import FilePath
from domain.services.mod_analyzer_service import ModAnalyzerService
from infrastructure import get_scanner_registry
from .base_command import BaseCommand, BaseCommandHandler, CommandResult


@dataclass
class ScanModCommand(BaseCommand):
    """扫描模组命令"""

    project_id: str
    source_path: str
    scan_target: str  # "jar" | "folder" | "both"
    include_patterns: list[str] | None = None
    exclude_patterns: list[str] | None = None
    recursive: bool = True

    def validate(self) -> list[str]:
        errors = []

        if not self.project_id:
            errors.append("项目ID不能为空")

        if not self.source_path:
            errors.append("源文件路径不能为空")

        if self.scan_target not in ["jar", "folder", "both"]:
            errors.append("扫描目标必须是 'jar', 'folder' 或 'both'")

        return errors


@dataclass
class AnalyzeModCommand(BaseCommand):
    """分析模组命令"""

    project_id: str
    mod_file_path: str
    deep_analysis: bool = False
    extract_metadata: bool = True
    validate_structure: bool = True

    def validate(self) -> list[str]:
        errors = []

        if not self.project_id:
            errors.append("项目ID不能为空")

        if not self.mod_file_path:
            errors.append("模组文件路径不能为空")

        return errors


@dataclass
class BatchScanModsCommand(BaseCommand):
    """批量扫描模组命令"""

    project_id: str
    source_paths: list[str]
    scan_target: str = "both"
    parallel_workers: int = 4
    include_patterns: list[str] | None = None
    exclude_patterns: list[str] | None = None

    def validate(self) -> list[str]:
        errors = []

        if not self.project_id:
            errors.append("项目ID不能为空")

        if not self.source_paths:
            errors.append("源文件路径列表不能为空")

        if self.scan_target not in ["jar", "folder", "both"]:
            errors.append("扫描目标必须是 'jar', 'folder' 或 'both'")

        if self.parallel_workers < 1 or self.parallel_workers > 16:
            errors.append("并行工作数必须在1-16之间")

        return errors


@dataclass
class RefreshModCacheCommand(BaseCommand):
    """刷新模组缓存命令"""

    project_id: str
    mod_ids: list[str] | None = None  # 如果为空则刷新所有
    force_refresh: bool = False

    def validate(self) -> list[str]:
        errors = []

        if not self.project_id:
            errors.append("项目ID不能为空")

        return errors


class ScanModCommandHandler(BaseCommandHandler[ScanModCommand, dict[str, Any]]):
    """扫描模组命令处理器"""

    def __init__(self, mod_analyzer_service: ModAnalyzerService):
        super().__init__()
        self._mod_analyzer_service = mod_analyzer_service
        self._scanner_registry = get_scanner_registry()

    async def handle(self, command: ScanModCommand) -> CommandResult[dict[str, Any]]:
        """处理扫描模组命令"""
        start_time = datetime.utcnow()

        try:
            self._logger.info(f"开始扫描模组: {command.source_path}")

            # 验证命令
            validation_errors = await self._validate_command(command)
            if validation_errors:
                return await self._create_error_result(
                    f"命令验证失败: {'; '.join(validation_errors)}", "VALIDATION_ERROR"
                )

            # 验证路径
            try:
                source_path = FilePath(command.source_path)
            except ValueError as e:
                return await self._create_error_result(
                    f"无效的源文件路径: {str(e)}", "INVALID_PATH"
                )

            # 选择合适的扫描器
            scanners = []
            if command.scan_target in ["jar", "both"]:
                jar_scanner = self._scanner_registry.get_scanner("jar")
                if jar_scanner:
                    scanners.append(jar_scanner)

            if command.scan_target in ["folder", "both"]:
                folder_scanner = self._scanner_registry.get_scanner("folder")
                if folder_scanner:
                    scanners.append(folder_scanner)

            if not scanners:
                return await self._create_error_result(
                    f"没有找到合适的扫描器: {command.scan_target}", "NO_SCANNER_FOUND"
                )

            # 创建扫描过滤器
            from infrastructure.scanners.base_scanner import ScanFilter

            scan_filter = ScanFilter(
                include_patterns=set(command.include_patterns or []),
                exclude_patterns=set(command.exclude_patterns or []),
                recursive=command.recursive,
            )

            # 执行扫描
            all_results = []
            total_files = 0
            total_mods = 0

            for scanner in scanners:
                try:
                    scan_result = await scanner.scan(source_path, scan_filter)
                    if scan_result.success:
                        all_results.extend(scan_result.discovered_files)
                        total_files += len(scan_result.discovered_files)

                        # 统计模组文件
                        mod_files = [
                            f
                            for f in scan_result.discovered_files
                            if f.file_path.value.endswith((".jar", ".zip"))
                        ]
                        total_mods += len(mod_files)

                        self._logger.info(
                            f"扫描器 {scanner.scanner_name} 发现 {len(scan_result.discovered_files)} 个文件"
                        )
                    else:
                        self._logger.warning(
                            f"扫描器 {scanner.scanner_name} 扫描失败: {scan_result.error_message}"
                        )

                except Exception as e:
                    self._logger.error(
                        f"扫描器 {scanner.scanner_name} 执行异常: {str(e)}"
                    )
                    continue

            end_time = datetime.utcnow()
            execution_time = int((end_time - start_time).total_seconds() * 1000)

            result_data = {
                "project_id": command.project_id,
                "source_path": command.source_path,
                "scan_target": command.scan_target,
                "total_files_found": total_files,
                "total_mods_found": total_mods,
                "scan_results": [
                    {
                        "file_path": df.file_path.value,
                        "file_type": df.file_type.value,
                        "size_bytes": df.size_bytes,
                        "last_modified": df.last_modified.isoformat()
                        if df.last_modified
                        else None,
                    }
                    for df in all_results
                ],
            }

            self._logger.info(
                f"模组扫描完成: 发现 {total_mods} 个模组文件，{total_files} 个总文件"
            )

            return await self._create_success_result(
                result_data,
                execution_time,
                {
                    "scanners_used": [scanner.scanner_name for scanner in scanners],
                    "scan_filter": {
                        "include_patterns": list(scan_filter.include_patterns),
                        "exclude_patterns": list(scan_filter.exclude_patterns),
                        "recursive": scan_filter.recursive,
                    },
                },
            )

        except Exception as e:
            error_msg = f"扫描模组失败: {str(e)}"
            self._logger.error(error_msg)

            end_time = datetime.utcnow()
            execution_time = int((end_time - start_time).total_seconds() * 1000)

            return await self._create_error_result(
                error_msg, "SCAN_ERROR", execution_time
            )

    def can_handle(self, command: BaseCommand) -> bool:
        return isinstance(command, ScanModCommand)


class AnalyzeModCommandHandler(BaseCommandHandler[AnalyzeModCommand, dict[str, Any]]):
    """分析模组命令处理器"""

    def __init__(self, mod_analyzer_service: ModAnalyzerService):
        super().__init__()
        self._mod_analyzer_service = mod_analyzer_service

    async def handle(self, command: AnalyzeModCommand) -> CommandResult[dict[str, Any]]:
        """处理分析模组命令"""
        start_time = datetime.utcnow()

        try:
            self._logger.info(f"开始分析模组: {command.mod_file_path}")

            # 验证命令
            validation_errors = await self._validate_command(command)
            if validation_errors:
                return await self._create_error_result(
                    f"命令验证失败: {'; '.join(validation_errors)}", "VALIDATION_ERROR"
                )

            # 验证文件路径
            try:
                mod_file_path = FilePath(command.mod_file_path)
            except ValueError as e:
                return await self._create_error_result(
                    f"无效的模组文件路径: {str(e)}", "INVALID_PATH"
                )

            # 执行模组分析
            analysis_result = await self._mod_analyzer_service.analyze_mod(
                mod_file_path
            )

            if not analysis_result.success:
                return await self._create_error_result(
                    f"模组分析失败: {analysis_result.error_message}", "ANALYSIS_ERROR"
                )

            # 深度分析（如果请求）
            deep_analysis_data = {}
            if command.deep_analysis:
                deep_analysis_data = await self._perform_deep_analysis(mod_file_path)

            end_time = datetime.utcnow()
            execution_time = int((end_time - start_time).total_seconds() * 1000)

            result_data = {
                "project_id": command.project_id,
                "mod_file_path": command.mod_file_path,
                "mod_id": analysis_result.mod_id.value
                if analysis_result.mod_id
                else None,
                "mod_name": analysis_result.mod_name,
                "mod_version": analysis_result.mod_version,
                "mod_loader_type": analysis_result.mod_loader_type.value
                if analysis_result.mod_loader_type
                else None,
                "minecraft_versions": analysis_result.minecraft_versions,
                "dependencies": [
                    {
                        "mod_id": dep.mod_id.value,
                        "version_range": dep.version_range,
                        "type": dep.dependency_type.value,
                        "required": dep.required,
                    }
                    for dep in analysis_result.dependencies
                ],
                "language_files": [
                    {
                        "file_path": lf.file_path.value,
                        "language_code": lf.language_code.code,
                        "file_type": lf.file_type.value,
                    }
                    for lf in analysis_result.language_files
                ],
                "metadata": analysis_result.metadata,
                "deep_analysis": deep_analysis_data if command.deep_analysis else None,
            }

            self._logger.info(
                f"模组分析完成: {analysis_result.mod_name} ({analysis_result.mod_id})"
            )

            return await self._create_success_result(
                result_data,
                execution_time,
                {
                    "analysis_options": {
                        "deep_analysis": command.deep_analysis,
                        "extract_metadata": command.extract_metadata,
                        "validate_structure": command.validate_structure,
                    }
                },
            )

        except Exception as e:
            error_msg = f"分析模组失败: {str(e)}"
            self._logger.error(error_msg)

            end_time = datetime.utcnow()
            execution_time = int((end_time - start_time).total_seconds() * 1000)

            return await self._create_error_result(
                error_msg, "ANALYSIS_ERROR", execution_time
            )

    def can_handle(self, command: BaseCommand) -> bool:
        return isinstance(command, AnalyzeModCommand)

    async def _perform_deep_analysis(self, mod_file_path: FilePath) -> dict[str, Any]:
        """执行深度分析"""
        try:
            # 这里可以添加更详细的分析逻辑
            return {
                "file_size_mb": mod_file_path.get_file_size() / (1024 * 1024),
                "creation_time": mod_file_path.get_creation_time().isoformat(),
                "modification_time": mod_file_path.get_modification_time().isoformat(),
                "internal_structure": await self._analyze_internal_structure(
                    mod_file_path
                ),
                "asset_analysis": await self._analyze_assets(mod_file_path),
            }
        except Exception as e:
            self._logger.warning(f"深度分析失败: {str(e)}")
            return {"error": str(e)}

    async def _analyze_internal_structure(
        self, mod_file_path: FilePath
    ) -> dict[str, Any]:
        """分析模组内部结构"""
        # 简化的内部结构分析
        return {
            "has_mcmod_info": False,  # 检查是否有mcmod.info文件
            "has_fabric_mod_json": False,  # 检查是否有fabric.mod.json文件
            "class_count": 0,  # Java类文件数量
            "resource_count": 0,  # 资源文件数量
            "language_file_count": 0,  # 语言文件数量
        }

    async def _analyze_assets(self, mod_file_path: FilePath) -> dict[str, Any]:
        """分析模组资源"""
        return {
            "textures_count": 0,
            "models_count": 0,
            "sounds_count": 0,
            "recipes_count": 0,
            "loot_tables_count": 0,
        }


class BatchScanModsCommandHandler(
    BaseCommandHandler[BatchScanModsCommand, dict[str, Any]]
):
    """批量扫描模组命令处理器"""

    def __init__(self, mod_analyzer_service: ModAnalyzerService):
        super().__init__()
        self._mod_analyzer_service = mod_analyzer_service
        self._scanner_registry = get_scanner_registry()

    async def handle(
        self, command: BatchScanModsCommand
    ) -> CommandResult[dict[str, Any]]:
        """处理批量扫描模组命令"""
        start_time = datetime.utcnow()

        try:
            self._logger.info(f"开始批量扫描 {len(command.source_paths)} 个路径")

            # 验证命令
            validation_errors = await self._validate_command(command)
            if validation_errors:
                return await self._create_error_result(
                    f"命令验证失败: {'; '.join(validation_errors)}", "VALIDATION_ERROR"
                )

            # 批量扫描
            import asyncio
            from concurrent.futures import ThreadPoolExecutor

            all_results = []
            failed_paths = []

            # 使用线程池进行并行扫描
            with ThreadPoolExecutor(max_workers=command.parallel_workers):
                tasks = []
                for source_path in command.source_paths:
                    task = self._scan_single_path(
                        source_path,
                        command.scan_target,
                        command.include_patterns,
                        command.exclude_patterns,
                    )
                    tasks.append(task)

                # 等待所有任务完成
                scan_results = await asyncio.gather(*tasks, return_exceptions=True)

                for i, result in enumerate(scan_results):
                    if isinstance(result, Exception):
                        failed_paths.append(
                            {"path": command.source_paths[i], "error": str(result)}
                        )
                        self._logger.error(
                            f"扫描路径失败 {command.source_paths[i]}: {str(result)}"
                        )
                    else:
                        all_results.extend(result)

            end_time = datetime.utcnow()
            execution_time = int((end_time - start_time).total_seconds() * 1000)

            result_data = {
                "project_id": command.project_id,
                "total_paths_scanned": len(command.source_paths),
                "successful_paths": len(command.source_paths) - len(failed_paths),
                "failed_paths": failed_paths,
                "total_files_found": len(all_results),
                "parallel_workers_used": command.parallel_workers,
                "scan_results": all_results[:1000],  # 限制返回数量
            }

            self._logger.info(
                f"批量扫描完成: 扫描 {len(command.source_paths)} 个路径，发现 {len(all_results)} 个文件"
            )

            return await self._create_success_result(
                result_data,
                execution_time,
                {
                    "scan_summary": {
                        "total_paths": len(command.source_paths),
                        "successful_scans": len(command.source_paths)
                        - len(failed_paths),
                        "failed_scans": len(failed_paths),
                    }
                },
            )

        except Exception as e:
            error_msg = f"批量扫描模组失败: {str(e)}"
            self._logger.error(error_msg)

            end_time = datetime.utcnow()
            execution_time = int((end_time - start_time).total_seconds() * 1000)

            return await self._create_error_result(
                error_msg, "BATCH_SCAN_ERROR", execution_time
            )

    def can_handle(self, command: BaseCommand) -> bool:
        return isinstance(command, BatchScanModsCommand)

    async def _scan_single_path(
        self,
        path: str,
        scan_target: str,
        include_patterns: list[str] | None,
        exclude_patterns: list[str] | None,
    ) -> list[dict[str, Any]]:
        """扫描单个路径"""
        try:
            FilePath(path)

            # 创建扫描命令
            scan_command = ScanModCommand(
                project_id="temp",
                source_path=path,
                scan_target=scan_target,
                include_patterns=include_patterns,
                exclude_patterns=exclude_patterns,
            )

            # 创建处理器并执行
            handler = ScanModCommandHandler(self._mod_analyzer_service)
            result = await handler.handle(scan_command)

            if result.success:
                return result.result.get("scan_results", [])
            else:
                raise Exception(result.error_message)

        except Exception as e:
            self._logger.error(f"扫描单个路径失败 {path}: {str(e)}")
            raise
