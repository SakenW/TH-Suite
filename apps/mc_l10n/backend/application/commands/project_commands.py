"""
项目管理命令

实现翻译项目的创建、修改、删除等操作命令
"""

from dataclasses import dataclass
from datetime import datetime

from domain.models.value_objects.file_path import FilePath
from domain.models.value_objects.language_code import LanguageCode
from domain.models.value_objects.project_name import ProjectName
from domain.services.project_service import ProjectService
from .base_command import BaseCommand, BaseCommandHandler, CommandResult


@dataclass
class CreateProjectCommand(BaseCommand):
    """创建翻译项目命令"""

    name: str
    description: str
    mc_version: str
    target_language: str
    source_path: str
    output_path: str

    def validate(self) -> list[str]:
        errors = []

        if not self.name or len(self.name.strip()) == 0:
            errors.append("项目名称不能为空")

        if len(self.name) > 100:
            errors.append("项目名称不能超过100个字符")

        if not self.mc_version:
            errors.append("Minecraft版本不能为空")

        if not self.target_language:
            errors.append("目标语言不能为空")

        if not self.source_path:
            errors.append("源文件路径不能为空")

        if not self.output_path:
            errors.append("输出路径不能为空")

        # 验证语言代码格式
        try:
            LanguageCode(self.target_language)
        except ValueError as e:
            errors.append(f"无效的语言代码: {str(e)}")

        return errors


@dataclass
class UpdateProjectCommand(BaseCommand):
    """更新翻译项目命令"""

    project_id: str
    name: str | None = None
    description: str | None = None
    mc_version: str | None = None
    target_language: str | None = None
    source_path: str | None = None
    output_path: str | None = None

    def validate(self) -> list[str]:
        errors = []

        if not self.project_id:
            errors.append("项目ID不能为空")

        if self.name is not None and len(self.name.strip()) == 0:
            errors.append("项目名称不能为空")

        if self.name is not None and len(self.name) > 100:
            errors.append("项目名称不能超过100个字符")

        # 验证语言代码（如果提供）
        if self.target_language:
            try:
                LanguageCode(self.target_language)
            except ValueError as e:
                errors.append(f"无效的语言代码: {str(e)}")

        return errors


@dataclass
class DeleteProjectCommand(BaseCommand):
    """删除翻译项目命令"""

    project_id: str
    force: bool = False

    def validate(self) -> list[str]:
        errors = []

        if not self.project_id:
            errors.append("项目ID不能为空")

        return errors


@dataclass
class ArchiveProjectCommand(BaseCommand):
    """归档翻译项目命令"""

    project_id: str
    archive_reason: str | None = None

    def validate(self) -> list[str]:
        errors = []

        if not self.project_id:
            errors.append("项目ID不能为空")

        return errors


class CreateProjectCommandHandler(BaseCommandHandler[CreateProjectCommand, str]):
    """创建项目命令处理器"""

    def __init__(self, project_service: ProjectService):
        super().__init__()
        self._project_service = project_service

    async def handle(self, command: CreateProjectCommand) -> CommandResult[str]:
        """处理创建项目命令"""
        start_time = datetime.utcnow()

        try:
            self._logger.info(f"开始创建项目: {command.name}")

            # 验证命令
            validation_errors = await self._validate_command(command)
            if validation_errors:
                return await self._create_error_result(
                    f"命令验证失败: {'; '.join(validation_errors)}", "VALIDATION_ERROR"
                )

            # 检查项目名称是否已存在
            if await self._project_service.project_exists_by_name(command.name):
                return await self._create_error_result(
                    f"项目名称已存在: {command.name}", "PROJECT_EXISTS"
                )

            # 验证路径
            try:
                source_path = FilePath(command.source_path)
                output_path = FilePath(command.output_path)
            except ValueError as e:
                return await self._create_error_result(
                    f"无效的文件路径: {str(e)}", "INVALID_PATH"
                )

            # 创建项目
            project = await self._project_service.create_project(
                name=ProjectName(command.name),
                description=command.description,
                mc_version=command.mc_version,
                target_language=LanguageCode(command.target_language),
                source_path=source_path,
                output_path=output_path,
                user_id=command.user_id,
            )

            end_time = datetime.utcnow()
            execution_time = int((end_time - start_time).total_seconds() * 1000)

            self._logger.info(f"项目创建成功: {project.project_id.value}")

            return await self._create_success_result(
                project.project_id.value,
                execution_time,
                {
                    "project_name": command.name,
                    "project_id": project.project_id.value,
                    "created_at": project.created_at.isoformat(),
                },
            )

        except Exception as e:
            error_msg = f"创建项目失败: {str(e)}"
            self._logger.error(error_msg)

            end_time = datetime.utcnow()
            execution_time = int((end_time - start_time).total_seconds() * 1000)

            return await self._create_error_result(
                error_msg, "CREATION_ERROR", execution_time
            )

    def can_handle(self, command: BaseCommand) -> bool:
        return isinstance(command, CreateProjectCommand)


class UpdateProjectCommandHandler(BaseCommandHandler[UpdateProjectCommand, bool]):
    """更新项目命令处理器"""

    def __init__(self, project_service: ProjectService):
        super().__init__()
        self._project_service = project_service

    async def handle(self, command: UpdateProjectCommand) -> CommandResult[bool]:
        """处理更新项目命令"""
        start_time = datetime.utcnow()

        try:
            self._logger.info(f"开始更新项目: {command.project_id}")

            # 验证命令
            validation_errors = await self._validate_command(command)
            if validation_errors:
                return await self._create_error_result(
                    f"命令验证失败: {'; '.join(validation_errors)}", "VALIDATION_ERROR"
                )

            # 检查项目是否存在
            project = await self._project_service.get_project_by_id(command.project_id)
            if not project:
                return await self._create_error_result(
                    f"项目不存在: {command.project_id}", "PROJECT_NOT_FOUND"
                )

            # 执行更新
            updated = await self._project_service.update_project(
                project_id=command.project_id,
                name=ProjectName(command.name) if command.name else None,
                description=command.description,
                mc_version=command.mc_version,
                target_language=LanguageCode(command.target_language)
                if command.target_language
                else None,
                source_path=FilePath(command.source_path)
                if command.source_path
                else None,
                output_path=FilePath(command.output_path)
                if command.output_path
                else None,
                user_id=command.user_id,
            )

            end_time = datetime.utcnow()
            execution_time = int((end_time - start_time).total_seconds() * 1000)

            if updated:
                self._logger.info(f"项目更新成功: {command.project_id}")
            else:
                self._logger.warning(f"项目更新无变化: {command.project_id}")

            return await self._create_success_result(
                updated,
                execution_time,
                {
                    "project_id": command.project_id,
                    "updated_fields": self._get_updated_fields(command),
                },
            )

        except Exception as e:
            error_msg = f"更新项目失败: {str(e)}"
            self._logger.error(error_msg)

            end_time = datetime.utcnow()
            execution_time = int((end_time - start_time).total_seconds() * 1000)

            return await self._create_error_result(
                error_msg, "UPDATE_ERROR", execution_time
            )

    def can_handle(self, command: BaseCommand) -> bool:
        return isinstance(command, UpdateProjectCommand)

    def _get_updated_fields(self, command: UpdateProjectCommand) -> list[str]:
        """获取更新的字段列表"""
        fields = []
        if command.name is not None:
            fields.append("name")
        if command.description is not None:
            fields.append("description")
        if command.mc_version is not None:
            fields.append("mc_version")
        if command.target_language is not None:
            fields.append("target_language")
        if command.source_path is not None:
            fields.append("source_path")
        if command.output_path is not None:
            fields.append("output_path")
        return fields


class DeleteProjectCommandHandler(BaseCommandHandler[DeleteProjectCommand, bool]):
    """删除项目命令处理器"""

    def __init__(self, project_service: ProjectService):
        super().__init__()
        self._project_service = project_service

    async def handle(self, command: DeleteProjectCommand) -> CommandResult[bool]:
        """处理删除项目命令"""
        start_time = datetime.utcnow()

        try:
            self._logger.info(f"开始删除项目: {command.project_id}")

            # 验证命令
            validation_errors = await self._validate_command(command)
            if validation_errors:
                return await self._create_error_result(
                    f"命令验证失败: {'; '.join(validation_errors)}", "VALIDATION_ERROR"
                )

            # 检查项目是否存在
            project = await self._project_service.get_project_by_id(command.project_id)
            if not project:
                return await self._create_error_result(
                    f"项目不存在: {command.project_id}", "PROJECT_NOT_FOUND"
                )

            # 检查项目是否可以删除
            if not command.force:
                can_delete = await self._project_service.can_delete_project(
                    command.project_id
                )
                if not can_delete:
                    return await self._create_error_result(
                        "项目包含重要数据，无法删除。使用 force=True 强制删除",
                        "PROJECT_HAS_DATA",
                    )

            # 执行删除
            deleted = await self._project_service.delete_project(
                project_id=command.project_id, user_id=command.user_id
            )

            end_time = datetime.utcnow()
            execution_time = int((end_time - start_time).total_seconds() * 1000)

            self._logger.info(f"项目删除成功: {command.project_id}")

            return await self._create_success_result(
                deleted,
                execution_time,
                {"project_id": command.project_id, "force_delete": command.force},
            )

        except Exception as e:
            error_msg = f"删除项目失败: {str(e)}"
            self._logger.error(error_msg)

            end_time = datetime.utcnow()
            execution_time = int((end_time - start_time).total_seconds() * 1000)

            return await self._create_error_result(
                error_msg, "DELETE_ERROR", execution_time
            )

    def can_handle(self, command: BaseCommand) -> bool:
        return isinstance(command, DeleteProjectCommand)


class ArchiveProjectCommandHandler(BaseCommandHandler[ArchiveProjectCommand, bool]):
    """归档项目命令处理器"""

    def __init__(self, project_service: ProjectService):
        super().__init__()
        self._project_service = project_service

    async def handle(self, command: ArchiveProjectCommand) -> CommandResult[bool]:
        """处理归档项目命令"""
        start_time = datetime.utcnow()

        try:
            self._logger.info(f"开始归档项目: {command.project_id}")

            # 验证命令
            validation_errors = await self._validate_command(command)
            if validation_errors:
                return await self._create_error_result(
                    f"命令验证失败: {'; '.join(validation_errors)}", "VALIDATION_ERROR"
                )

            # 检查项目是否存在
            project = await self._project_service.get_project_by_id(command.project_id)
            if not project:
                return await self._create_error_result(
                    f"项目不存在: {command.project_id}", "PROJECT_NOT_FOUND"
                )

            # 执行归档
            archived = await self._project_service.archive_project(
                project_id=command.project_id,
                archive_reason=command.archive_reason,
                user_id=command.user_id,
            )

            end_time = datetime.utcnow()
            execution_time = int((end_time - start_time).total_seconds() * 1000)

            self._logger.info(f"项目归档成功: {command.project_id}")

            return await self._create_success_result(
                archived,
                execution_time,
                {
                    "project_id": command.project_id,
                    "archive_reason": command.archive_reason,
                },
            )

        except Exception as e:
            error_msg = f"归档项目失败: {str(e)}"
            self._logger.error(error_msg)

            end_time = datetime.utcnow()
            execution_time = int((end_time - start_time).total_seconds() * 1000)

            return await self._create_error_result(
                error_msg, "ARCHIVE_ERROR", execution_time
            )

    def can_handle(self, command: BaseCommand) -> bool:
        return isinstance(command, ArchiveProjectCommand)
