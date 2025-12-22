import asyncio
from datetime import datetime, timedelta
from typing import Any

from fastapi import UploadFile

from packages.core.job_manager import JobManager
from packages.core.logging import get_logger
from packages.core.models import JobStatus
from packages.parsers.xml_parser import XMLParser
from packages.protocol.schemas import (
    ModInfo,
    SaveGameAnalysisResult,
    SaveGameBackup,
    SaveGameInfo,
)

logger = get_logger(__name__)


class SaveGameService:
    """存档管理服务"""

    def __init__(self):
        self.job_manager = JobManager()
        self.xml_parser = XMLParser()
        self.saves_cache: dict[str, SaveGameInfo] = {}
        self.backups_cache: dict[str, SaveGameBackup] = {}

    async def list_saves(
        self, search: str | None = None, sort_by: str = "modified_time"
    ) -> list[SaveGameInfo]:
        """获取存档列表"""
        try:
            logger.info(f"Listing saves: search={search}, sort_by={sort_by}")

            # 扫描存档目录
            saves = await self._scan_saves()

            # 应用搜索过滤
            if search:
                search_lower = search.lower()
                saves = [
                    save
                    for save in saves
                    if search_lower in save.name.lower()
                    or search_lower in save.colony_name.lower()
                    or search_lower in save.scenario.lower()
                ]

            # 排序
            if sort_by == "name":
                saves.sort(key=lambda x: x.name.lower())
            elif sort_by == "modified_time":
                saves.sort(key=lambda x: x.modified_time, reverse=True)
            elif sort_by == "created_time":
                saves.sort(key=lambda x: x.created_time, reverse=True)
            elif sort_by == "file_size":
                saves.sort(key=lambda x: x.file_size, reverse=True)

            return saves

        except Exception as e:
            logger.error(f"Failed to list saves: {e}")
            raise

    async def get_save(self, save_id: str) -> SaveGameInfo | None:
        """获取特定存档信息"""
        try:
            logger.info(f"Getting save info for: {save_id}")

            # 先从缓存查找
            if save_id in self.saves_cache:
                return self.saves_cache[save_id]

            # 扫描存档目录
            saves = await self._scan_saves()
            for save in saves:
                if save.id == save_id:
                    return save

            return None

        except Exception as e:
            logger.error(f"Failed to get save {save_id}: {e}")
            raise

    async def backup_save(
        self,
        save_id: str,
        backup_name: str | None = None,
        include_mods: bool = True,
        compress: bool = True,
    ) -> str:
        """备份存档"""
        try:
            logger.info(f"Backing up save: {save_id}, include_mods: {include_mods}")

            # 创建备份任务
            job_id = await self.job_manager.create_job(
                job_type="backup_save",
                description=f"备份存档: {save_id}",
                metadata={
                    "save_id": save_id,
                    "backup_name": backup_name,
                    "include_mods": include_mods,
                    "compress": compress,
                },
            )

            # 异步执行备份
            asyncio.create_task(
                self._backup_save_task(
                    job_id, save_id, backup_name, include_mods, compress
                )
            )

            return job_id

        except Exception as e:
            logger.error(f"Failed to start save backup for {save_id}: {e}")
            raise

    async def restore_save(
        self,
        backup_id: str,
        target_save_id: str | None = None,
        restore_mods: bool = True,
    ) -> str:
        """恢复存档"""
        try:
            logger.info(
                f"Restoring save from backup: {backup_id}, target: {target_save_id}"
            )

            # 创建恢复任务
            job_id = await self.job_manager.create_job(
                job_type="restore_save",
                description=f"恢复存档: {backup_id}",
                metadata={
                    "backup_id": backup_id,
                    "target_save_id": target_save_id,
                    "restore_mods": restore_mods,
                },
            )

            # 异步执行恢复
            asyncio.create_task(
                self._restore_save_task(job_id, backup_id, target_save_id, restore_mods)
            )

            return job_id

        except Exception as e:
            logger.error(f"Failed to start save restore for {backup_id}: {e}")
            raise

    async def list_backups(self, save_id: str | None = None) -> list[SaveGameBackup]:
        """获取存档备份列表"""
        try:
            logger.info(f"Listing save backups for: {save_id}")

            # 扫描备份目录
            backups = await self._scan_backups()

            # 过滤特定存档的备份
            if save_id:
                backups = [
                    backup for backup in backups if backup.original_save_id == save_id
                ]

            # 按创建时间排序
            backups.sort(key=lambda x: x.created_time, reverse=True)

            return backups

        except Exception as e:
            logger.error(f"Failed to list save backups: {e}")
            raise

    async def delete_backup(self, backup_id: str):
        """删除存档备份"""
        try:
            logger.info(f"Deleting save backup: {backup_id}")

            # 这里应该实现删除备份文件的逻辑
            # 从文件系统删除备份文件

            # 从缓存中移除
            if backup_id in self.backups_cache:
                del self.backups_cache[backup_id]

        except Exception as e:
            logger.error(f"Failed to delete save backup {backup_id}: {e}")
            raise

    async def analyze_save(
        self, save_id: str, deep_analysis: bool = False
    ) -> SaveGameAnalysisResult:
        """分析存档"""
        try:
            logger.info(f"Analyzing save: {save_id}, deep: {deep_analysis}")

            save = await self.get_save(save_id)
            if not save:
                raise ValueError(f"Save {save_id} not found")

            # 基本分析
            analysis = SaveGameAnalysisResult(
                save_id=save_id,
                file_size=save.file_size,
                mod_count=len(save.mods),
                colonist_count=save.colonist_count,
                animal_count=save.animal_count,
                wealth_total=save.wealth_total,
                game_day=save.game_day,
                performance_score=0.0,  # 需要计算
                issues=[],
                recommendations=[],
            )

            if deep_analysis:
                # 深度分析：检查模组兼容性、性能问题等
                analysis = await self._perform_deep_analysis(analysis, save)

            return analysis

        except Exception as e:
            logger.error(f"Failed to analyze save {save_id}: {e}")
            raise

    async def get_save_mods(self, save_id: str) -> list[ModInfo]:
        """获取存档使用的模组列表"""
        try:
            logger.info(f"Getting mods for save: {save_id}")

            save = await self.get_save(save_id)
            if not save:
                raise ValueError(f"Save {save_id} not found")

            return save.mods

        except Exception as e:
            logger.error(f"Failed to get save mods for {save_id}: {e}")
            raise

    async def validate_save(
        self, save_id: str, check_mods: bool = True
    ) -> dict[str, Any]:
        """验证存档完整性"""
        try:
            logger.info(f"Validating save: {save_id}, check_mods: {check_mods}")

            save = await self.get_save(save_id)
            if not save:
                raise ValueError(f"Save {save_id} not found")

            validation_result = {
                "valid": True,
                "errors": [],
                "warnings": [],
                "file_integrity": True,
                "mod_compatibility": True if check_mods else None,
            }

            # 检查文件完整性
            if not await self._check_file_integrity(save):
                validation_result["valid"] = False
                validation_result["file_integrity"] = False
                validation_result["errors"].append("存档文件损坏或不完整")

            # 检查模组兼容性
            if check_mods:
                mod_issues = await self._check_mod_compatibility(save)
                if mod_issues:
                    validation_result["mod_compatibility"] = False
                    validation_result["warnings"].extend(mod_issues)

            return validation_result

        except Exception as e:
            logger.error(f"Failed to validate save {save_id}: {e}")
            raise

    async def upload_save(self, file: UploadFile, save_name: str | None = None) -> str:
        """上传存档文件"""
        try:
            logger.info(f"Uploading save file: {file.filename}")

            # 生成存档 ID
            save_id = f"uploaded_{datetime.now().strftime('%Y%m%d_%H%M%S')}"

            # 这里应该实现保存文件和解析存档信息的逻辑

            return save_id

        except Exception as e:
            logger.error(f"Failed to upload save file {file.filename}: {e}")
            raise

    async def export_save(self, save_id: str, include_mods: bool = False) -> str:
        """导出存档文件"""
        try:
            logger.info(f"Exporting save: {save_id}, include_mods: {include_mods}")

            save = await self.get_save(save_id)
            if not save:
                raise ValueError(f"Save {save_id} not found")

            # 这里应该实现导出逻辑
            # 创建包含存档和可选模组的压缩包

            export_path = f"/tmp/{save_id}_export.zip"
            return export_path

        except Exception as e:
            logger.error(f"Failed to export save {save_id}: {e}")
            raise

    async def delete_save(self, save_id: str, delete_backups: bool = False):
        """删除存档"""
        try:
            logger.info(f"Deleting save: {save_id}, delete_backups: {delete_backups}")

            # 删除存档文件
            # 这里应该实现删除文件的逻辑

            # 删除相关备份
            if delete_backups:
                backups = await self.list_backups(save_id)
                for backup in backups:
                    await self.delete_backup(backup.id)

            # 从缓存中移除
            if save_id in self.saves_cache:
                del self.saves_cache[save_id]

        except Exception as e:
            logger.error(f"Failed to delete save {save_id}: {e}")
            raise

    async def cleanup_backups(
        self, older_than_days: int = 30, keep_recent: int = 5
    ) -> dict[str, Any]:
        """清理旧的存档备份"""
        try:
            logger.info(
                f"Cleaning up backups: older_than={older_than_days} days, keep_recent={keep_recent}"
            )

            backups = await self.list_backups()
            cutoff_date = datetime.now() - timedelta(days=older_than_days)

            # 按存档分组
            backups_by_save: dict[str, list[SaveGameBackup]] = {}
            for backup in backups:
                save_id = backup.original_save_id
                if save_id not in backups_by_save:
                    backups_by_save[save_id] = []
                backups_by_save[save_id].append(backup)

            deleted_count = 0
            freed_space = 0

            for save_id, save_backups in backups_by_save.items():
                # 按时间排序，保留最新的
                save_backups.sort(key=lambda x: x.created_time, reverse=True)

                # 保留最近的备份
                save_backups[:keep_recent]
                to_check = save_backups[keep_recent:]

                # 删除超过时间限制的备份
                for backup in to_check:
                    if backup.created_time < cutoff_date:
                        await self.delete_backup(backup.id)
                        deleted_count += 1
                        freed_space += backup.file_size

            return {
                "deleted_count": deleted_count,
                "freed_space": freed_space,
                "message": f"已删除 {deleted_count} 个备份，释放 {freed_space / (1024 * 1024):.1f} MB 空间",
            }

        except Exception as e:
            logger.error(f"Failed to cleanup backups: {e}")
            raise

    async def get_statistics(self) -> dict[str, Any]:
        """获取存档统计信息"""
        try:
            logger.info("Getting save statistics")

            saves = await self.list_saves()
            backups = await self.list_backups()

            total_size = sum(save.file_size for save in saves)
            backup_size = sum(backup.file_size for backup in backups)

            return {
                "total_saves": len(saves),
                "total_backups": len(backups),
                "total_size": total_size,
                "backup_size": backup_size,
                "average_save_size": total_size / len(saves) if saves else 0,
                "oldest_save": min(saves, key=lambda x: x.created_time).created_time
                if saves
                else None,
                "newest_save": max(saves, key=lambda x: x.created_time).created_time
                if saves
                else None,
            }

        except Exception as e:
            logger.error(f"Failed to get save statistics: {e}")
            raise

    async def _scan_saves(self) -> list[SaveGameInfo]:
        """扫描存档目录"""
        try:
            # 这里应该实现实际的存档扫描逻辑
            # 扫描 RimWorld 存档目录，解析存档文件

            # 模拟返回一些存档数据
            return [
                SaveGameInfo(
                    id="save_001",
                    name="我的殖民地",
                    colony_name="新希望",
                    scenario="坠机求生",
                    difficulty="中等",
                    game_version="1.4.0",
                    created_time=datetime.now() - timedelta(days=5),
                    modified_time=datetime.now() - timedelta(hours=2),
                    file_size=1024 * 1024 * 10,  # 10MB
                    file_path="/path/to/save_001.rws",
                    colonist_count=8,
                    animal_count=15,
                    wealth_total=50000,
                    game_day=120,
                    mods=[],
                    screenshot_path=None,
                )
            ]

        except Exception as e:
            logger.error(f"Failed to scan saves: {e}")
            raise

    async def _scan_backups(self) -> list[SaveGameBackup]:
        """扫描备份目录"""
        try:
            # 这里应该实现实际的备份扫描逻辑
            return []

        except Exception as e:
            logger.error(f"Failed to scan backups: {e}")
            raise

    async def _check_file_integrity(self, save: SaveGameInfo) -> bool:
        """检查文件完整性"""
        try:
            # 这里应该实现文件完整性检查
            # 检查文件是否存在、是否可读、格式是否正确等
            return True

        except Exception as e:
            logger.error(f"Failed to check file integrity: {e}")
            return False

    async def _check_mod_compatibility(self, save: SaveGameInfo) -> list[str]:
        """检查模组兼容性"""
        try:
            # 这里应该实现模组兼容性检查
            # 检查模组是否存在、版本是否兼容等
            return []

        except Exception as e:
            logger.error(f"Failed to check mod compatibility: {e}")
            return ["模组兼容性检查失败"]

    async def _perform_deep_analysis(
        self, analysis: SaveGameAnalysisResult, save: SaveGameInfo
    ) -> SaveGameAnalysisResult:
        """执行深度分析"""
        try:
            # 这里应该实现深度分析逻辑
            # 分析性能、模组冲突、资源使用等

            # 计算性能分数
            analysis.performance_score = 85.0  # 模拟分数

            # 添加建议
            analysis.recommendations.append("考虑禁用一些不必要的模组以提高性能")

            return analysis

        except Exception as e:
            logger.error(f"Failed to perform deep analysis: {e}")
            return analysis

    async def _backup_save_task(
        self,
        job_id: str,
        save_id: str,
        backup_name: str | None,
        include_mods: bool,
        compress: bool,
    ):
        """备份存档任务"""
        try:
            await self.job_manager.update_job_status(job_id, JobStatus.RUNNING)

            # 这里实现实际的备份逻辑
            await asyncio.sleep(2)  # 模拟备份过程

            await self.job_manager.update_job_status(job_id, JobStatus.COMPLETED)
            logger.info(f"Save {save_id} backed up successfully")

        except Exception as e:
            await self.job_manager.update_job_status(job_id, JobStatus.FAILED, str(e))
            logger.error(f"Failed to backup save {save_id}: {e}")

    async def _restore_save_task(
        self,
        job_id: str,
        backup_id: str,
        target_save_id: str | None,
        restore_mods: bool,
    ):
        """恢复存档任务"""
        try:
            await self.job_manager.update_job_status(job_id, JobStatus.RUNNING)

            # 这里实现实际的恢复逻辑
            await asyncio.sleep(2)  # 模拟恢复过程

            await self.job_manager.update_job_status(job_id, JobStatus.COMPLETED)
            logger.info(f"Save restored from backup {backup_id} successfully")

        except Exception as e:
            await self.job_manager.update_job_status(job_id, JobStatus.FAILED, str(e))
            logger.error(f"Failed to restore save from backup {backup_id}: {e}")
