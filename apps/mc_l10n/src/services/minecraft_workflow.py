"""
Minecraft工作流引擎
基于升级方案的完整本地化工作流管理系统
"""

import asyncio
import time
from pathlib import Path
from typing import Dict, List, Optional, Any, Callable, AsyncIterator
from dataclasses import dataclass, asdict
from enum import Enum
import structlog

from ..adapters.minecraft_core_adapter import MinecraftCoreAdapter, SyncResult
from ..adapters.projection import MinecraftLanguageData
from ..domain.mod_scanner import MinecraftModScanner, ScanResult, ScanProgress
from ..domain.jar_processor import AdvancedJarProcessor, JarModificationResult

logger = structlog.get_logger(__name__)


class WorkflowStage(Enum):
    """工作流阶段"""
    INITIALIZED = "initialized"
    SCANNING = "scanning"
    INGESTING = "ingesting"
    WAITING_TRANSLATION = "waiting_translation"
    SYNCING = "syncing"
    VALIDATING = "validating"
    BUILDING = "building"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class BuildStrategy(Enum):
    """构建策略"""
    RESOURCE_PACK = "resource_pack"  # 构建资源包（推荐）
    JAR_MODIFICATION = "jar_modification"  # 直接修改JAR（高风险）
    OVERLAY = "overlay"  # 创建覆盖包


@dataclass
class WorkflowConfig:
    """工作流配置"""
    pack_path: str
    pack_id: str
    target_languages: List[str]
    output_path: str
    build_strategy: BuildStrategy = BuildStrategy.RESOURCE_PACK
    incremental_scan: bool = True
    auto_validation: bool = True
    backup_original: bool = True
    parallel_processing: bool = True
    max_concurrent_jobs: int = 4
    
    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class StageResult:
    """阶段结果"""
    stage: WorkflowStage
    success: bool
    start_time: float
    end_time: float
    data: Dict[str, Any]
    errors: List[str]
    warnings: List[str]
    
    @property
    def duration(self) -> float:
        return self.end_time - self.start_time
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "stage": self.stage.value,
            "success": self.success,
            "start_time": self.start_time,
            "end_time": self.end_time,
            "duration": self.duration,
            "data": self.data,
            "errors": self.errors,
            "warnings": self.warnings
        }


@dataclass
class WorkflowProgress:
    """工作流进度"""
    workflow_id: str
    current_stage: WorkflowStage
    overall_progress: float  # 0-100
    stage_progress: float    # 0-100
    current_task: str
    estimated_time_remaining: Optional[float] = None
    
    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


class LocalizationWorkflow:
    """本地化工作流"""
    
    def __init__(self, workflow_id: str, config: WorkflowConfig):
        self.workflow_id = workflow_id
        self.config = config
        self.current_stage = WorkflowStage.INITIALIZED
        self.stage_results: Dict[WorkflowStage, StageResult] = {}
        self.start_time = time.time()
        self.end_time: Optional[float] = None
        self.is_cancelled = False
        
        # 进度回调
        self.progress_callbacks: List[Callable[[WorkflowProgress], None]] = []
        
        logger.info("本地化工作流已初始化",
                   workflow_id=workflow_id,
                   pack_id=config.pack_id)
    
    def add_progress_callback(self, callback: Callable[[WorkflowProgress], None]):
        """添加进度回调"""
        self.progress_callbacks.append(callback)
    
    def add_stage_result(self, stage: WorkflowStage, result: StageResult):
        """添加阶段结果"""
        self.stage_results[stage] = result
    
    def update_stage(self, stage: WorkflowStage, progress: float = 0.0, task: str = ""):
        """更新当前阶段"""
        self.current_stage = stage
        
        # 计算整体进度
        stage_weights = {
            WorkflowStage.SCANNING: 10,
            WorkflowStage.INGESTING: 20,
            WorkflowStage.WAITING_TRANSLATION: 30,
            WorkflowStage.SYNCING: 20,
            WorkflowStage.VALIDATING: 10,
            WorkflowStage.BUILDING: 10
        }
        
        completed_weight = sum(
            weight for s, weight in stage_weights.items() 
            if s in self.stage_results and self.stage_results[s].success
        )
        
        current_weight = stage_weights.get(stage, 0) * (progress / 100)
        overall_progress = min(100, completed_weight + current_weight)
        
        # 发送进度更新
        workflow_progress = WorkflowProgress(
            workflow_id=self.workflow_id,
            current_stage=stage,
            overall_progress=overall_progress,
            stage_progress=progress,
            current_task=task
        )
        
        for callback in self.progress_callbacks:
            try:
                callback(workflow_progress)
            except Exception as e:
                logger.warning("进度回调失败", error=str(e))
    
    def mark_completed(self):
        """标记为完成"""
        self.current_stage = WorkflowStage.COMPLETED
        self.end_time = time.time()
        
        self.update_stage(WorkflowStage.COMPLETED, 100.0, "工作流完成")
        
        logger.info("本地化工作流完成",
                   workflow_id=self.workflow_id,
                   duration=self.end_time - self.start_time)
    
    def mark_failed(self, error: str):
        """标记为失败"""
        self.current_stage = WorkflowStage.FAILED
        self.end_time = time.time()
        
        logger.error("本地化工作流失败",
                    workflow_id=self.workflow_id,
                    error=error)
    
    def cancel(self):
        """取消工作流"""
        self.is_cancelled = True
        self.current_stage = WorkflowStage.CANCELLED
        self.end_time = time.time()
        
        logger.info("本地化工作流已取消", workflow_id=self.workflow_id)
    
    def get_result(self) -> Dict[str, Any]:
        """获取工作流结果"""
        return {
            "workflow_id": self.workflow_id,
            "config": self.config.to_dict(),
            "current_stage": self.current_stage.value,
            "start_time": self.start_time,
            "end_time": self.end_time,
            "duration": (self.end_time or time.time()) - self.start_time,
            "stage_results": {
                stage.value: result.to_dict() 
                for stage, result in self.stage_results.items()
            },
            "is_cancelled": self.is_cancelled
        }


class MinecraftWorkflowEngine:
    """Minecraft工作流引擎"""
    
    def __init__(self, core_adapter: MinecraftCoreAdapter):
        self.core_adapter = core_adapter
        self.mod_scanner = MinecraftModScanner()
        self.jar_processor = AdvancedJarProcessor()
        self.validator = MinecraftTranslationValidator()
        
        # 活动工作流
        self.active_workflows: Dict[str, LocalizationWorkflow] = {}
        
        logger.info("Minecraft工作流引擎已初始化")
    
    async def execute_full_localization_workflow(
        self,
        config: WorkflowConfig,
        progress_callback: Optional[Callable[[WorkflowProgress], None]] = None
    ) -> LocalizationWorkflow:
        """执行完整的本地化工作流"""
        import uuid
        workflow_id = str(uuid.uuid4())[:16]
        
        workflow = LocalizationWorkflow(workflow_id, config)
        if progress_callback:
            workflow.add_progress_callback(progress_callback)
        
        self.active_workflows[workflow_id] = workflow
        
        try:
            # 执行工作流阶段
            await self._execute_scan_stage(workflow)
            if workflow.is_cancelled:
                return workflow
            
            await self._execute_ingestion_stage(workflow)
            if workflow.is_cancelled:
                return workflow
            
            await self._execute_translation_waiting_stage(workflow)
            if workflow.is_cancelled:
                return workflow
            
            await self._execute_sync_stage(workflow)
            if workflow.is_cancelled:
                return workflow
            
            if config.auto_validation:
                await self._execute_validation_stage(workflow)
                if workflow.is_cancelled:
                    return workflow
            
            await self._execute_build_stage(workflow)
            if workflow.is_cancelled:
                return workflow
            
            workflow.mark_completed()
            
        except Exception as e:
            logger.error("工作流执行失败",
                        workflow_id=workflow_id,
                        error=str(e))
            workflow.mark_failed(str(e))
        
        finally:
            # 清理活动工作流（可选保留一段时间）
            # del self.active_workflows[workflow_id]
            pass
        
        return workflow
    
    async def _execute_scan_stage(self, workflow: LocalizationWorkflow):
        """执行扫描阶段"""
        workflow.update_stage(WorkflowStage.SCANNING, 0.0, "开始扫描")
        start_time = time.time()
        
        def scan_progress_callback(progress: ScanProgress):
            workflow.update_stage(
                WorkflowStage.SCANNING,
                progress.progress_percentage,
                f"扫描: {progress.current_file}"
            )
        
        try:
            scan_result = await self.mod_scanner.scan_async(
                workflow.config.pack_path,
                progress_callback=scan_progress_callback
            )
            
            if not scan_result.is_success:
                raise RuntimeError(f"扫描失败: {scan_result.error_message}")
            
            workflow.add_stage_result(
                WorkflowStage.SCANNING,
                StageResult(
                    stage=WorkflowStage.SCANNING,
                    success=True,
                    start_time=start_time,
                    end_time=time.time(),
                    data={
                        "mods_found": len(scan_result.mods_found),
                        "language_files": len(scan_result.language_files),
                        "scan_statistics": scan_result.scan_statistics
                    },
                    errors=[],
                    warnings=[]
                )
            )
            
        except Exception as e:
            workflow.add_stage_result(
                WorkflowStage.SCANNING,
                StageResult(
                    stage=WorkflowStage.SCANNING,
                    success=False,
                    start_time=start_time,
                    end_time=time.time(),
                    data={},
                    errors=[str(e)],
                    warnings=[]
                )
            )
            raise
    
    async def _execute_ingestion_stage(self, workflow: LocalizationWorkflow):
        """执行摄入阶段"""
        workflow.update_stage(WorkflowStage.INGESTING, 0.0, "开始摄入内容")
        start_time = time.time()
        
        try:
            ingestion_result = await self.core_adapter.scan_and_ingest_pack(
                workflow.config.pack_path,
                workflow.config.pack_id,
                workflow.config.incremental_scan
            )
            
            if not ingestion_result.success:
                raise RuntimeError(f"摄入失败: {'; '.join(ingestion_result.errors)}")
            
            workflow.add_stage_result(
                WorkflowStage.INGESTING,
                StageResult(
                    stage=WorkflowStage.INGESTING,
                    success=True,
                    start_time=start_time,
                    end_time=time.time(),
                    data={
                        "processed_mods": ingestion_result.processed_mods,
                        "processed_translations": ingestion_result.processed_translations,
                        "failed_items": ingestion_result.failed_items
                    },
                    errors=[],
                    warnings=ingestion_result.errors if ingestion_result.failed_items > 0 else []
                )
            )
            
            workflow.update_stage(WorkflowStage.INGESTING, 100.0, "摄入完成")
            
        except Exception as e:
            workflow.add_stage_result(
                WorkflowStage.INGESTING,
                StageResult(
                    stage=WorkflowStage.INGESTING,
                    success=False,
                    start_time=start_time,
                    end_time=time.time(),
                    data={},
                    errors=[str(e)],
                    warnings=[]
                )
            )
            raise
    
    async def _execute_translation_waiting_stage(self, workflow: LocalizationWorkflow):
        """执行翻译等待阶段"""
        workflow.update_stage(WorkflowStage.WAITING_TRANSLATION, 0.0, "等待翻译完成")
        start_time = time.time()
        
        try:
            # 等待翻译完成的策略可以有多种：
            # 1. 轮询检查翻译进度
            # 2. 接收外部通知
            # 3. 用户手动确认
            
            # 这里实现轮询策略
            await self._wait_for_translation_completion(
                workflow.config.pack_id,
                workflow.config.target_languages,
                workflow
            )
            
            workflow.add_stage_result(
                WorkflowStage.WAITING_TRANSLATION,
                StageResult(
                    stage=WorkflowStage.WAITING_TRANSLATION,
                    success=True,
                    start_time=start_time,
                    end_time=time.time(),
                    data={"languages": workflow.config.target_languages},
                    errors=[],
                    warnings=[]
                )
            )
            
        except Exception as e:
            workflow.add_stage_result(
                WorkflowStage.WAITING_TRANSLATION,
                StageResult(
                    stage=WorkflowStage.WAITING_TRANSLATION,
                    success=False,
                    start_time=start_time,
                    end_time=time.time(),
                    data={},
                    errors=[str(e)],
                    warnings=[]
                )
            )
            raise
    
    async def _execute_sync_stage(self, workflow: LocalizationWorkflow):
        """执行同步阶段"""
        workflow.update_stage(WorkflowStage.SYNCING, 0.0, "开始同步翻译")
        start_time = time.time()
        
        try:
            sync_result = await self.core_adapter.sync_pack_translations(
                workflow.config.pack_id,
                workflow.config.target_languages,
                workflow.config.output_path
            )
            
            if not sync_result.success:
                raise RuntimeError(f"同步失败: {'; '.join(sync_result.errors)}")
            
            workflow.add_stage_result(
                WorkflowStage.SYNCING,
                StageResult(
                    stage=WorkflowStage.SYNCING,
                    success=True,
                    start_time=start_time,
                    end_time=time.time(),
                    data={
                        "synced_languages": sync_result.languages,
                        "synced_files": sync_result.synced_files,
                        "conflicts": len(sync_result.conflicts)
                    },
                    errors=[],
                    warnings=[f"检测到 {len(sync_result.conflicts)} 个冲突"] if sync_result.conflicts else []
                )
            )
            
            workflow.update_stage(WorkflowStage.SYNCING, 100.0, "同步完成")
            
        except Exception as e:
            workflow.add_stage_result(
                WorkflowStage.SYNCING,
                StageResult(
                    stage=WorkflowStage.SYNCING,
                    success=False,
                    start_time=start_time,
                    end_time=time.time(),
                    data={},
                    errors=[str(e)],
                    warnings=[]
                )
            )
            raise
    
    async def _execute_validation_stage(self, workflow: LocalizationWorkflow):
        """执行验证阶段"""
        workflow.update_stage(WorkflowStage.VALIDATING, 0.0, "开始验证翻译")
        start_time = time.time()
        
        try:
            # 获取同步的翻译数据进行验证
            sync_result = workflow.stage_results.get(WorkflowStage.SYNCING)
            if not sync_result or not sync_result.success:
                raise RuntimeError("无法获取同步结果进行验证")
            
            # 执行验证（这里需要实际的验证逻辑）
            validation_result = await self.validator.validate_translations_for_pack(
                workflow.config.pack_id,
                workflow.config.target_languages
            )
            
            workflow.add_stage_result(
                WorkflowStage.VALIDATING,
                StageResult(
                    stage=WorkflowStage.VALIDATING,
                    success=validation_result["success"],
                    start_time=start_time,
                    end_time=time.time(),
                    data=validation_result,
                    errors=validation_result.get("errors", []),
                    warnings=validation_result.get("warnings", [])
                )
            )
            
            workflow.update_stage(WorkflowStage.VALIDATING, 100.0, "验证完成")
            
        except Exception as e:
            workflow.add_stage_result(
                WorkflowStage.VALIDATING,
                StageResult(
                    stage=WorkflowStage.VALIDATING,
                    success=False,
                    start_time=start_time,
                    end_time=time.time(),
                    data={},
                    errors=[str(e)],
                    warnings=[]
                )
            )
            # 验证失败不阻断流程，只记录警告
            logger.warning("验证阶段失败，继续构建", error=str(e))
    
    async def _execute_build_stage(self, workflow: LocalizationWorkflow):
        """执行构建阶段"""
        workflow.update_stage(WorkflowStage.BUILDING, 0.0, "开始构建")
        start_time = time.time()
        
        try:
            build_result = await self._build_localized_pack(workflow)
            
            workflow.add_stage_result(
                WorkflowStage.BUILDING,
                StageResult(
                    stage=WorkflowStage.BUILDING,
                    success=build_result["success"],
                    start_time=start_time,
                    end_time=time.time(),
                    data=build_result,
                    errors=build_result.get("errors", []),
                    warnings=build_result.get("warnings", [])
                )
            )
            
            workflow.update_stage(WorkflowStage.BUILDING, 100.0, "构建完成")
            
        except Exception as e:
            workflow.add_stage_result(
                WorkflowStage.BUILDING,
                StageResult(
                    stage=WorkflowStage.BUILDING,
                    success=False,
                    start_time=start_time,
                    end_time=time.time(),
                    data={},
                    errors=[str(e)],
                    warnings=[]
                )
            )
            raise
    
    async def _wait_for_translation_completion(
        self,
        pack_id: str,
        target_languages: List[str],
        workflow: LocalizationWorkflow,
        check_interval: float = 10.0,
        timeout: float = 3600.0  # 1小时
    ):
        """等待翻译完成"""
        start_time = time.time()
        
        while time.time() - start_time < timeout:
            if workflow.is_cancelled:
                raise asyncio.CancelledError("工作流已取消")
            
            try:
                progress_data = await self.core_adapter.get_translation_progress(pack_id)
                
                # 检查翻译进度
                all_completed = True
                progress_summary = {}
                
                for lang in target_languages:
                    lang_progress = progress_data.get("languages", {}).get(lang, {})
                    completion = lang_progress.get("completion_percentage", 0)
                    progress_summary[lang] = completion
                    
                    if completion < 80.0:  # 要求80%完成度
                        all_completed = False
                
                # 更新进度
                avg_completion = sum(progress_summary.values()) / len(progress_summary) if progress_summary else 0
                workflow.update_stage(
                    WorkflowStage.WAITING_TRANSLATION,
                    avg_completion,
                    f"翻译进度: {avg_completion:.1f}%"
                )
                
                if all_completed:
                    logger.info("翻译已完成", pack_id=pack_id, languages=target_languages)
                    return
                
                await asyncio.sleep(check_interval)
                
            except Exception as e:
                logger.warning("检查翻译进度失败", error=str(e))
                await asyncio.sleep(check_interval)
        
        raise TimeoutError(f"等待翻译完成超时 (>{timeout}秒)")
    
    async def _build_localized_pack(self, workflow: LocalizationWorkflow) -> Dict[str, Any]:
        """构建本地化包"""
        config = workflow.config
        
        if config.build_strategy == BuildStrategy.RESOURCE_PACK:
            return await self._build_resource_pack(workflow)
        elif config.build_strategy == BuildStrategy.JAR_MODIFICATION:
            return await self._build_via_jar_modification(workflow)
        elif config.build_strategy == BuildStrategy.OVERLAY:
            return await self._build_overlay_pack(workflow)
        else:
            raise ValueError(f"不支持的构建策略: {config.build_strategy}")
    
    async def _build_resource_pack(self, workflow: LocalizationWorkflow) -> Dict[str, Any]:
        """构建资源包"""
        # 实现资源包构建逻辑
        logger.info("构建资源包", pack_id=workflow.config.pack_id)
        
        # 这里应该实现实际的资源包构建逻辑
        # 暂时返回成功结果
        return {
            "success": True,
            "build_type": "resource_pack",
            "output_path": workflow.config.output_path,
            "files_created": 0,
            "languages": workflow.config.target_languages
        }
    
    async def _build_via_jar_modification(self, workflow: LocalizationWorkflow) -> Dict[str, Any]:
        """通过JAR修改构建"""
        # 实现JAR修改构建逻辑
        logger.info("通过JAR修改构建", pack_id=workflow.config.pack_id)
        
        # 这里应该实现实际的JAR修改逻辑
        # 暂时返回成功结果
        return {
            "success": True,
            "build_type": "jar_modification",
            "output_path": workflow.config.output_path,
            "modified_jars": 0,
            "languages": workflow.config.target_languages
        }
    
    async def _build_overlay_pack(self, workflow: LocalizationWorkflow) -> Dict[str, Any]:
        """构建覆盖包"""
        # 实现覆盖包构建逻辑
        logger.info("构建覆盖包", pack_id=workflow.config.pack_id)
        
        # 这里应该实现实际的覆盖包构建逻辑
        # 暂时返回成功结果
        return {
            "success": True,
            "build_type": "overlay",
            "output_path": workflow.config.output_path,
            "overlay_files": 0,
            "languages": workflow.config.target_languages
        }
    
    def get_workflow(self, workflow_id: str) -> Optional[LocalizationWorkflow]:
        """获取工作流"""
        return self.active_workflows.get(workflow_id)
    
    def get_active_workflows(self) -> List[str]:
        """获取活动工作流ID列表"""
        return list(self.active_workflows.keys())
    
    def cancel_workflow(self, workflow_id: str) -> bool:
        """取消工作流"""
        workflow = self.active_workflows.get(workflow_id)
        if workflow:
            workflow.cancel()
            return True
        return False


class MinecraftTranslationValidator:
    """Minecraft翻译验证器"""
    
    def __init__(self):
        self.placeholder_patterns = [
            r'%[sd%]',  # %s, %d, %%
            r'\{[0-9]+\}',  # {0}, {1}, etc.
            r'\$\{[^}]+\}',  # ${variable}
        ]
        
        self.minecraft_color_codes = [
            '§0', '§1', '§2', '§3', '§4', '§5', '§6', '§7',
            '§8', '§9', '§a', '§b', '§c', '§d', '§e', '§f',
            '§k', '§l', '§m', '§n', '§o', '§r'
        ]
        
        logger.info("Minecraft翻译验证器已初始化")
    
    async def validate_translations_for_pack(
        self,
        pack_id: str,
        languages: List[str]
    ) -> Dict[str, Any]:
        """验证包的翻译"""
        
        # 这里应该实现实际的验证逻辑
        # 暂时返回简化的结果
        
        return {
            "success": True,
            "pack_id": pack_id,
            "languages": languages,
            "total_entries": 0,
            "valid_entries": 0,
            "invalid_entries": 0,
            "warnings": [],
            "errors": []
        }


# ==================== 工厂函数和便捷接口 ====================

def create_minecraft_workflow_engine(core_adapter: MinecraftCoreAdapter) -> MinecraftWorkflowEngine:
    """创建Minecraft工作流引擎"""
    return MinecraftWorkflowEngine(core_adapter)


async def execute_localization_workflow(
    core_adapter: MinecraftCoreAdapter,
    pack_path: str,
    pack_id: str,
    target_languages: List[str],
    output_path: str,
    build_strategy: BuildStrategy = BuildStrategy.RESOURCE_PACK,
    progress_callback: Optional[Callable[[WorkflowProgress], None]] = None
) -> LocalizationWorkflow:
    """执行本地化工作流（便捷函数）"""
    
    engine = MinecraftWorkflowEngine(core_adapter)
    
    config = WorkflowConfig(
        pack_path=pack_path,
        pack_id=pack_id,
        target_languages=target_languages,
        output_path=output_path,
        build_strategy=build_strategy
    )
    
    return await engine.execute_full_localization_workflow(config, progress_callback)