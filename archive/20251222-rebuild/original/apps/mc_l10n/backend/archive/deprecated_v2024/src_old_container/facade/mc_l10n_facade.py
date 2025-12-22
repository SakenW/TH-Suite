"""
MC L10n 门面服务
提供简化的统一接口，隐藏内部复杂性
"""

import logging
from dataclasses import dataclass
from datetime import datetime
from typing import Any

from ..domain.models.mod import Mod, ModId
from ..domain.models.translation_project import TranslationProject
from ..domain.services import (
    ConflictResolutionStrategy,
    Glossary,
)
from ..domain.value_objects import (
    ContentHash,
    FilePath,
    LanguageCode,
)
from ..infrastructure.cache.cache_decorator import cache_5min
from ..infrastructure.event_bus import get_event_bus
from ..infrastructure.unit_of_work import UnitOfWork

logger = logging.getLogger(__name__)


@dataclass
class ScanResult:
    """扫描结果"""

    total_files: int
    mods_found: int
    translations_found: int
    errors: list[str]
    duration: float

    @property
    def success(self) -> bool:
        return len(self.errors) == 0


@dataclass
class TranslationResult:
    """翻译结果"""

    mod_id: str
    language: str
    translated_count: int
    failed_count: int
    progress: float
    quality_score: float | None = None


@dataclass
class SyncResult:
    """同步结果"""

    synced_count: int
    conflict_count: int
    error_count: int
    duration: float


class MCL10nFacade:
    """MC L10n 统一门面接口

    提供简化的API，隐藏内部复杂性：
    - 一个方法完成复杂操作
    - 自动处理事务和错误
    - 提供合理的默认值
    - 返回简单的结果对象
    """

    def __init__(self, service_container):
        """初始化门面

        Args:
            service_container: 依赖注入容器
        """
        self.container = service_container

        # 获取核心服务
        self.scan_service = service_container.get_service("scan")
        self.translation_service = service_container.get_service("translation_service")
        self.conflict_service = service_container.get_service("conflict_resolution")
        self.terminology_service = service_container.get_service("terminology")
        self.uow_factory = service_container.get_service("uow_factory")

        # 事件总线
        self.event_bus = get_event_bus()

        # 默认配置
        self.default_languages = [
            LanguageCode.ZH_CN,
            LanguageCode.ZH_TW,
            LanguageCode.JA_JP,
            LanguageCode.KO_KR,
        ]
        self.default_conflict_strategy = ConflictResolutionStrategy.KEEP_HIGHEST_QUALITY

    # ========== 扫描相关 ==========

    def scan_mods(
        self, path: str, recursive: bool = True, auto_extract: bool = True
    ) -> ScanResult:
        """扫描MOD目录

        一个方法完成所有扫描操作：
        - 扫描目录
        - 识别MOD文件
        - 提取语言文件
        - 解析翻译内容
        - 保存到数据库

        Args:
            path: 扫描路径
            recursive: 是否递归扫描
            auto_extract: 是否自动提取JAR文件

        Returns:
            扫描结果
        """
        start_time = datetime.now()
        errors = []

        try:
            with self.uow_factory.create() as uow:
                # 执行扫描
                scan_context = self.scan_service.scan_directory(
                    FilePath(path), recursive=recursive, extract_jars=auto_extract
                )

                # 处理扫描结果
                mods_found = 0
                translations_found = 0

                for mod_info in scan_context.discovered_mods:
                    try:
                        # 创建或更新Mod实体
                        self._create_or_update_mod(mod_info, uow)
                        mods_found += 1

                        # 处理翻译
                        for lang, entries in mod_info.translations.items():
                            translations_found += len(entries)

                    except Exception as e:
                        errors.append(f"Error processing mod {mod_info.id}: {str(e)}")
                        logger.error(f"Error processing mod: {e}")

                # 提交事务
                uow.commit()

                duration = (datetime.now() - start_time).total_seconds()

                return ScanResult(
                    total_files=scan_context.total_files,
                    mods_found=mods_found,
                    translations_found=translations_found,
                    errors=errors,
                    duration=duration,
                )

        except Exception as e:
            logger.error(f"Scan failed: {e}")
            return ScanResult(
                total_files=0,
                mods_found=0,
                translations_found=0,
                errors=[str(e)],
                duration=(datetime.now() - start_time).total_seconds(),
            )

    @cache_5min
    def quick_scan(self, path: str) -> dict[str, Any]:
        """快速扫描（仅统计，不保存）

        使用5分钟缓存避免重复扫描

        Args:
            path: 扫描路径

        Returns:
            扫描统计信息
        """
        try:
            stats = self.scan_service.quick_scan(FilePath(path))
            return {
                "total_mods": stats.get("mod_count", 0),
                "total_jars": stats.get("jar_count", 0),
                "total_languages": len(stats.get("languages", [])),
                "languages": stats.get("languages", []),
                "estimated_translations": stats.get("translation_count", 0),
            }
        except Exception as e:
            logger.error(f"Quick scan failed: {e}")
            return {
                "error": str(e),
                "total_mods": 0,
                "total_jars": 0,
                "total_languages": 0,
            }

    # ========== 翻译相关 ==========

    def translate_mod(
        self,
        mod_id: str,
        language: str,
        translations: dict[str, str],
        translator: str | None = None,
        auto_approve: bool = False,
    ) -> TranslationResult:
        """翻译MOD

        Args:
            mod_id: MOD ID
            language: 目标语言
            translations: 翻译映射 {key: translated_text}
            translator: 翻译者ID
            auto_approve: 是否自动批准

        Returns:
            翻译结果
        """
        try:
            with self.uow_factory.create() as uow:
                # 获取MOD
                mod = uow.get_by_id(Mod, mod_id)
                if not mod:
                    raise ValueError(f"Mod {mod_id} not found")

                # 转换语言代码
                lang_code = LanguageCode.from_string(language) or LanguageCode.ZH_CN

                # 应用翻译
                success, failed = self.translation_service.apply_translations(
                    mod=mod,
                    translations=self._prepare_translations(translations),
                    language=lang_code,
                    translator=translator,
                )

                # 自动批准
                if auto_approve and success > 0:
                    keys = list(translations.keys())[:success]
                    self.translation_service.approve_translations(
                        mod=mod, language=lang_code, keys=keys, reviewer="system"
                    )

                # 计算进度
                progress = mod.get_translation_progress(lang_code)

                # 提交
                uow.commit()

                return TranslationResult(
                    mod_id=mod_id,
                    language=language,
                    translated_count=success,
                    failed_count=failed,
                    progress=progress,
                )

        except Exception as e:
            logger.error(f"Translation failed: {e}")
            return TranslationResult(
                mod_id=mod_id,
                language=language,
                translated_count=0,
                failed_count=len(translations),
                progress=0.0,
            )

    def batch_translate(
        self,
        mod_ids: list[str],
        language: str,
        glossary: Glossary | None = None,
        quality_threshold: float = 0.8,
    ) -> list[TranslationResult]:
        """批量翻译多个MOD

        Args:
            mod_ids: MOD ID列表
            language: 目标语言
            glossary: 术语表（可选）
            quality_threshold: 质量阈值

        Returns:
            翻译结果列表
        """
        results = []

        for mod_id in mod_ids:
            try:
                # 获取待翻译内容
                translations = self._get_pending_translations(mod_id, language)

                # 应用术语表
                if glossary:
                    translations = self._apply_glossary(
                        translations, glossary, language
                    )

                # 执行翻译
                result = self.translate_mod(
                    mod_id=mod_id,
                    language=language,
                    translations=translations,
                    auto_approve=(quality_threshold <= 0.5),
                )

                results.append(result)

            except Exception as e:
                logger.error(f"Failed to translate mod {mod_id}: {e}")
                results.append(
                    TranslationResult(
                        mod_id=mod_id,
                        language=language,
                        translated_count=0,
                        failed_count=0,
                        progress=0.0,
                    )
                )

        return results

    # ========== 同步相关 ==========

    def sync_with_server(
        self,
        server_url: str | None = None,
        conflict_strategy: ConflictResolutionStrategy | None = None,
    ) -> SyncResult:
        """同步到服务器

        自动处理：
        - 连接服务器
        - 上传本地更改
        - 下载远程更改
        - 解决冲突
        - 更新本地数据

        Args:
            server_url: 服务器地址（使用默认值如果未提供）
            conflict_strategy: 冲突解决策略

        Returns:
            同步结果
        """
        start_time = datetime.now()

        try:
            # 这里应该实现实际的同步逻辑
            # 现在只是示例

            synced = 0
            conflicts = 0
            errors = 0

            # 模拟同步过程
            with self.uow_factory.create() as uow:
                # 获取需要同步的实体
                # 检测冲突
                # 解决冲突
                # 执行同步
                # 提交更改
                uow.commit()

            duration = (datetime.now() - start_time).total_seconds()

            return SyncResult(
                synced_count=synced,
                conflict_count=conflicts,
                error_count=errors,
                duration=duration,
            )

        except Exception as e:
            logger.error(f"Sync failed: {e}")
            return SyncResult(
                synced_count=0,
                conflict_count=0,
                error_count=1,
                duration=(datetime.now() - start_time).total_seconds(),
            )

    # ========== 项目管理 ==========

    def create_project(
        self,
        name: str,
        mod_ids: list[str],
        target_languages: list[str] | None = None,
        auto_assign: bool = False,
    ) -> str:
        """创建翻译项目

        Args:
            name: 项目名称
            mod_ids: 包含的MOD ID列表
            target_languages: 目标语言列表
            auto_assign: 是否自动分配任务

        Returns:
            项目ID
        """
        try:
            with self.uow_factory.create() as uow:
                # 创建项目
                project = TranslationProject(
                    project_id=self._generate_project_id(),
                    name=name,
                    target_languages=set(
                        target_languages or [lang.value for lang in self.default_languages]
                    ),
                )

                # 添加MOD
                for mod_id in mod_ids:
                    project.add_mod(ModId(mod_id))

                # 启用自动分配
                if auto_assign:
                    project.enable_auto_assignment()

                # 激活项目
                project.activate()

                # 保存
                uow.register_new(project)
                uow.commit()

                return project.project_id

        except Exception as e:
            logger.error(f"Failed to create project: {e}")
            raise

    def get_project_status(self, project_id: str) -> dict[str, Any]:
        """获取项目状态

        Args:
            project_id: 项目ID

        Returns:
            项目状态信息
        """
        try:
            with self.uow_factory.create() as uow:
                project = uow.get_by_id(TranslationProject, project_id)
                if not project:
                    return {"error": "Project not found"}

                return {
                    "id": project.project_id,
                    "name": project.name,
                    "status": project.status.value,
                    "progress": project.get_progress(),
                    "statistics": project.get_statistics(),
                    "estimated_completion": project.calculate_estimated_completion(),
                }

        except Exception as e:
            logger.error(f"Failed to get project status: {e}")
            return {"error": str(e)}

    # ========== 质量管理 ==========

    def check_quality(self, mod_id: str, language: str) -> dict[str, Any]:
        """检查翻译质量

        Args:
            mod_id: MOD ID
            language: 语言

        Returns:
            质量报告
        """
        try:
            with self.uow_factory.create() as uow:
                mod = uow.get_by_id(Mod, mod_id)
                if not mod:
                    return {"error": "Mod not found"}

                lang_code = LanguageCode.from_string(language)
                if not lang_code:
                    return {"error": "Invalid language"}

                # 获取翻译
                translations = mod.get_translations(lang_code)

                # 计算质量指标
                total = len(translations)
                approved = sum(1 for t in translations if t.status == "approved")
                rejected = sum(1 for t in translations if t.status == "rejected")
                pending = sum(1 for t in translations if t.status == "pending")

                # 计算平均质量分数
                scores = [
                    t.quality_score.value for t in translations if t.quality_score
                ]
                avg_score = sum(scores) / len(scores) if scores else 0

                return {
                    "mod_id": mod_id,
                    "language": language,
                    "total_translations": total,
                    "approved": approved,
                    "rejected": rejected,
                    "pending": pending,
                    "approval_rate": (approved / total * 100) if total else 0,
                    "average_quality": avg_score,
                    "needs_review": pending > 0,
                }

        except Exception as e:
            logger.error(f"Quality check failed: {e}")
            return {"error": str(e)}

    # ========== 辅助方法 ==========

    def _create_or_update_mod(self, mod_info: Any, uow: UnitOfWork) -> Mod:
        """创建或更新MOD"""
        existing = uow.get_by_id(Mod, mod_info.id)

        if existing:
            # 更新现有MOD
            if existing.needs_rescan(ContentHash.from_content(mod_info.content)):
                existing.scan_completed(
                    ContentHash.from_content(mod_info.content),
                    len(mod_info.translations),
                )
                uow.register_modified(existing)
            return existing
        else:
            # 创建新MOD
            mod = Mod.create(
                mod_id=mod_info.id,
                name=mod_info.name,
                version=mod_info.version,
                file_path=mod_info.path,
            )
            uow.register_new(mod)
            return mod

    def _prepare_translations(
        self, translations: dict[str, str]
    ) -> dict[str, tuple[str, str]]:
        """准备翻译数据"""
        # 这里应该获取原文，现在简化处理
        return {k: ("", v) for k, v in translations.items()}

    def _get_pending_translations(self, mod_id: str, language: str) -> dict[str, str]:
        """获取待翻译内容"""
        # 实现获取待翻译内容的逻辑
        return {}

    def _apply_glossary(
        self, translations: dict[str, str], glossary: Glossary, language: str
    ) -> dict[str, str]:
        """应用术语表"""
        # 实现术语表应用逻辑
        return translations

    def _generate_project_id(self) -> str:
        """生成项目ID"""
        import uuid

        return f"proj_{uuid.uuid4().hex[:8]}"
