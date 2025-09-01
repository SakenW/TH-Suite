"""
翻译管理命令

实现翻译条目的提取、导入、导出、更新等操作命令
"""

from dataclasses import dataclass
from datetime import datetime
from typing import Any

from domain.models.enums import FileType
from domain.models.value_objects.file_path import FilePath
from domain.models.value_objects.language_code import LanguageCode
from domain.models.value_objects.translation_key import TranslationKey
from domain.services.translation_extractor_service import TranslationExtractorService
from infrastructure import get_parser_registry
from .base_command import BaseCommand, BaseCommandHandler, CommandResult


@dataclass
class ExtractTranslationsCommand(BaseCommand):
    """提取翻译命令"""

    project_id: str
    source_file_paths: list[str]
    target_language: str
    source_language: str | None = "en_us"  # 默认英语为源语言
    overwrite_existing: bool = False
    validate_format: bool = True

    def validate(self) -> list[str]:
        errors = []

        if not self.project_id:
            errors.append("项目ID不能为空")

        if not self.source_file_paths:
            errors.append("源文件路径列表不能为空")

        if not self.target_language:
            errors.append("目标语言不能为空")

        # 验证语言代码
        try:
            LanguageCode(self.target_language)
        except ValueError as e:
            errors.append(f"无效的目标语言代码: {str(e)}")

        if self.source_language:
            try:
                LanguageCode(self.source_language)
            except ValueError as e:
                errors.append(f"无效的源语言代码: {str(e)}")

        return errors


@dataclass
class ImportTranslationsCommand(BaseCommand):
    """导入翻译命令"""

    project_id: str
    translation_file_path: str
    language_code: str
    merge_strategy: str = "overwrite"  # "overwrite", "merge", "skip_existing"
    validate_keys: bool = True
    backup_existing: bool = True

    def validate(self) -> list[str]:
        errors = []

        if not self.project_id:
            errors.append("项目ID不能为空")

        if not self.translation_file_path:
            errors.append("翻译文件路径不能为空")

        if not self.language_code:
            errors.append("语言代码不能为空")

        if self.merge_strategy not in ["overwrite", "merge", "skip_existing"]:
            errors.append("合并策略必须是 'overwrite', 'merge' 或 'skip_existing'")

        # 验证语言代码
        try:
            LanguageCode(self.language_code)
        except ValueError as e:
            errors.append(f"无效的语言代码: {str(e)}")

        return errors


@dataclass
class ExportTranslationsCommand(BaseCommand):
    """导出翻译命令"""

    project_id: str
    output_file_path: str
    language_code: str
    file_format: str  # "json", "properties"
    include_empty: bool = False
    include_comments: bool = True
    sort_keys: bool = True

    def validate(self) -> list[str]:
        errors = []

        if not self.project_id:
            errors.append("项目ID不能为空")

        if not self.output_file_path:
            errors.append("输出文件路径不能为空")

        if not self.language_code:
            errors.append("语言代码不能为空")

        if self.file_format not in ["json", "properties"]:
            errors.append("文件格式必须是 'json' 或 'properties'")

        # 验证语言代码
        try:
            LanguageCode(self.language_code)
        except ValueError as e:
            errors.append(f"无效的语言代码: {str(e)}")

        return errors


@dataclass
class UpdateTranslationCommand(BaseCommand):
    """更新翻译条目命令"""

    project_id: str
    translation_key: str
    language_code: str
    new_value: str
    comment: str | None = None
    validate_placeholders: bool = True

    def validate(self) -> list[str]:
        errors = []

        if not self.project_id:
            errors.append("项目ID不能为空")

        if not self.translation_key:
            errors.append("翻译键不能为空")

        if not self.language_code:
            errors.append("语言代码不能为空")

        if not self.new_value:
            errors.append("新值不能为空")

        # 验证翻译键格式
        try:
            TranslationKey(self.translation_key)
        except ValueError as e:
            errors.append(f"无效的翻译键: {str(e)}")

        # 验证语言代码
        try:
            LanguageCode(self.language_code)
        except ValueError as e:
            errors.append(f"无效的语言代码: {str(e)}")

        return errors


@dataclass
class BatchUpdateTranslationsCommand(BaseCommand):
    """批量更新翻译命令"""

    project_id: str
    language_code: str
    translations: dict[str, str]  # key -> value
    overwrite_existing: bool = True
    validate_all_keys: bool = True

    def validate(self) -> list[str]:
        errors = []

        if not self.project_id:
            errors.append("项目ID不能为空")

        if not self.language_code:
            errors.append("语言代码不能为空")

        if not self.translations:
            errors.append("翻译数据不能为空")

        # 验证语言代码
        try:
            LanguageCode(self.language_code)
        except ValueError as e:
            errors.append(f"无效的语言代码: {str(e)}")

        # 验证翻译键（如果启用验证）
        if self.validate_all_keys:
            for key in self.translations.keys():
                try:
                    TranslationKey(key)
                except ValueError as e:
                    errors.append(f"无效的翻译键 '{key}': {str(e)}")
                    if len(errors) > 10:  # 限制错误数量
                        errors.append("...更多翻译键验证错误")
                        break

        return errors


class ExtractTranslationsCommandHandler(
    BaseCommandHandler[ExtractTranslationsCommand, dict[str, Any]]
):
    """提取翻译命令处理器"""

    def __init__(self, translation_extractor_service: TranslationExtractorService):
        super().__init__()
        self._translation_extractor_service = translation_extractor_service
        self._parser_registry = get_parser_registry()

    async def handle(
        self, command: ExtractTranslationsCommand
    ) -> CommandResult[dict[str, Any]]:
        """处理提取翻译命令"""
        start_time = datetime.utcnow()

        try:
            self._logger.info(f"开始提取翻译: {len(command.source_file_paths)} 个文件")

            # 验证命令
            validation_errors = await self._validate_command(command)
            if validation_errors:
                return await self._create_error_result(
                    f"命令验证失败: {'; '.join(validation_errors)}", "VALIDATION_ERROR"
                )

            # 验证文件路径
            source_file_paths = []
            for path in command.source_file_paths:
                try:
                    source_file_paths.append(FilePath(path))
                except ValueError as e:
                    return await self._create_error_result(
                        f"无效的文件路径 '{path}': {str(e)}", "INVALID_PATH"
                    )

            # 执行翻译提取
            target_language = LanguageCode(command.target_language)
            source_language = (
                LanguageCode(command.source_language)
                if command.source_language
                else None
            )

            extraction_results = []
            total_entries = 0
            failed_files = []

            for file_path in source_file_paths:
                try:
                    result = (
                        await self._translation_extractor_service.extract_translations(
                            file_path=file_path,
                            target_language=target_language,
                            source_language=source_language,
                            project_id=command.project_id,
                        )
                    )

                    if result.success:
                        extraction_results.append(
                            {
                                "file_path": file_path.value,
                                "entries_count": len(result.translation_entries),
                                "file_type": result.file_type.value,
                                "language_code": result.language_code.code
                                if result.language_code
                                else None,
                            }
                        )
                        total_entries += len(result.translation_entries)
                    else:
                        failed_files.append(
                            {
                                "file_path": file_path.value,
                                "error": result.error_message,
                            }
                        )

                except Exception as e:
                    failed_files.append({"file_path": file_path.value, "error": str(e)})
                    continue

            end_time = datetime.utcnow()
            execution_time = int((end_time - start_time).total_seconds() * 1000)

            result_data = {
                "project_id": command.project_id,
                "target_language": command.target_language,
                "source_language": command.source_language,
                "total_files_processed": len(command.source_file_paths),
                "successful_extractions": len(extraction_results),
                "failed_extractions": len(failed_files),
                "total_entries_extracted": total_entries,
                "extraction_results": extraction_results,
                "failed_files": failed_files,
            }

            self._logger.info(
                f"翻译提取完成: 提取 {total_entries} 个条目，成功 {len(extraction_results)} 个文件"
            )

            return await self._create_success_result(
                result_data,
                execution_time,
                {
                    "extraction_options": {
                        "overwrite_existing": command.overwrite_existing,
                        "validate_format": command.validate_format,
                    }
                },
            )

        except Exception as e:
            error_msg = f"提取翻译失败: {str(e)}"
            self._logger.error(error_msg)

            end_time = datetime.utcnow()
            execution_time = int((end_time - start_time).total_seconds() * 1000)

            return await self._create_error_result(
                error_msg, "EXTRACTION_ERROR", execution_time
            )

    def can_handle(self, command: BaseCommand) -> bool:
        return isinstance(command, ExtractTranslationsCommand)


class ImportTranslationsCommandHandler(
    BaseCommandHandler[ImportTranslationsCommand, dict[str, Any]]
):
    """导入翻译命令处理器"""

    def __init__(self, translation_extractor_service: TranslationExtractorService):
        super().__init__()
        self._translation_extractor_service = translation_extractor_service
        self._parser_registry = get_parser_registry()

    async def handle(
        self, command: ImportTranslationsCommand
    ) -> CommandResult[dict[str, Any]]:
        """处理导入翻译命令"""
        start_time = datetime.utcnow()

        try:
            self._logger.info(f"开始导入翻译: {command.translation_file_path}")

            # 验证命令
            validation_errors = await self._validate_command(command)
            if validation_errors:
                return await self._create_error_result(
                    f"命令验证失败: {'; '.join(validation_errors)}", "VALIDATION_ERROR"
                )

            # 验证文件路径
            try:
                translation_file_path = FilePath(command.translation_file_path)
            except ValueError as e:
                return await self._create_error_result(
                    f"无效的翻译文件路径: {str(e)}", "INVALID_PATH"
                )

            # 检查文件是否存在
            if not translation_file_path.exists():
                return await self._create_error_result(
                    f"翻译文件不存在: {command.translation_file_path}", "FILE_NOT_FOUND"
                )

            # 自动检测文件类型并选择解析器
            parse_result = await self._parser_registry.parse_with_auto_detection(
                content=translation_file_path.read_bytes(),
                file_path=command.translation_file_path,
                language_code=LanguageCode(command.language_code),
            )

            if not parse_result:
                return await self._create_error_result(
                    "无法解析翻译文件，可能是不支持的文件格式", "UNSUPPORTED_FORMAT"
                )

            if parse_result.errors:
                return await self._create_error_result(
                    f"解析翻译文件失败: {'; '.join(parse_result.errors)}", "PARSE_ERROR"
                )

            # 根据合并策略执行导入
            import_result = await self._execute_import_strategy(
                command, parse_result.entries
            )

            end_time = datetime.utcnow()
            execution_time = int((end_time - start_time).total_seconds() * 1000)

            self._logger.info(
                f"翻译导入完成: 导入 {import_result['imported_count']} 个条目"
            )

            return await self._create_success_result(
                import_result,
                execution_time,
                {
                    "file_info": {
                        "file_path": command.translation_file_path,
                        "file_type": parse_result.file_type.value,
                        "language_code": command.language_code,
                        "total_entries_in_file": len(parse_result.entries),
                    },
                    "import_options": {
                        "merge_strategy": command.merge_strategy,
                        "validate_keys": command.validate_keys,
                        "backup_existing": command.backup_existing,
                    },
                },
            )

        except Exception as e:
            error_msg = f"导入翻译失败: {str(e)}"
            self._logger.error(error_msg)

            end_time = datetime.utcnow()
            execution_time = int((end_time - start_time).total_seconds() * 1000)

            return await self._create_error_result(
                error_msg, "IMPORT_ERROR", execution_time
            )

    def can_handle(self, command: BaseCommand) -> bool:
        return isinstance(command, ImportTranslationsCommand)

    async def _execute_import_strategy(
        self, command: ImportTranslationsCommand, entries: dict
    ) -> dict[str, Any]:
        """执行导入策略"""
        imported_count = 0
        skipped_count = 0
        updated_count = 0
        errors = []

        # 这里简化实现，实际应该与数据库交互
        for translation_key, parsed_entry in entries.items():
            try:
                if command.merge_strategy == "overwrite":
                    # 总是覆盖
                    imported_count += 1
                elif command.merge_strategy == "merge":
                    # 合并（更新存在的，添加新的）
                    imported_count += 1
                elif command.merge_strategy == "skip_existing":
                    # 跳过已存在的
                    # 这里需要检查是否存在
                    imported_count += 1

            except Exception as e:
                errors.append(f"导入条目失败 '{translation_key.value}': {str(e)}")

        return {
            "project_id": command.project_id,
            "language_code": command.language_code,
            "imported_count": imported_count,
            "skipped_count": skipped_count,
            "updated_count": updated_count,
            "errors": errors,
            "merge_strategy": command.merge_strategy,
        }


class ExportTranslationsCommandHandler(
    BaseCommandHandler[ExportTranslationsCommand, dict[str, Any]]
):
    """导出翻译命令处理器"""

    def __init__(self, translation_extractor_service: TranslationExtractorService):
        super().__init__()
        self._translation_extractor_service = translation_extractor_service
        self._parser_registry = get_parser_registry()

    async def handle(
        self, command: ExportTranslationsCommand
    ) -> CommandResult[dict[str, Any]]:
        """处理导出翻译命令"""
        start_time = datetime.utcnow()

        try:
            self._logger.info(f"开始导出翻译: {command.output_file_path}")

            # 验证命令
            validation_errors = await self._validate_command(command)
            if validation_errors:
                return await self._create_error_result(
                    f"命令验证失败: {'; '.join(validation_errors)}", "VALIDATION_ERROR"
                )

            # 确定文件类型
            file_type = (
                FileType.JSON if command.file_format == "json" else FileType.PROPERTIES
            )

            # 获取对应的解析器
            parser = self._parser_registry.get_parser(file_type)
            if not parser:
                return await self._create_error_result(
                    f"找不到 {file_type.value} 格式的解析器", "NO_PARSER_FOUND"
                )

            # 获取翻译数据（这里简化实现，实际应该从数据库查询）
            translation_entries = await self._get_project_translations(
                command.project_id,
                LanguageCode(command.language_code),
                command.include_empty,
            )

            if not translation_entries:
                return await self._create_error_result(
                    f"项目 {command.project_id} 中没有找到 {command.language_code} 语言的翻译",
                    "NO_TRANSLATIONS_FOUND",
                )

            # 序列化翻译数据
            serialized_content = await parser.serialize(
                entries=translation_entries,
                file_type=file_type,
                language_code=LanguageCode(command.language_code),
            )

            # 写入文件
            try:
                output_path = FilePath(command.output_file_path)
                output_path.write_bytes(serialized_content)
            except Exception as e:
                return await self._create_error_result(
                    f"写入文件失败: {str(e)}", "WRITE_ERROR"
                )

            end_time = datetime.utcnow()
            execution_time = int((end_time - start_time).total_seconds() * 1000)

            result_data = {
                "project_id": command.project_id,
                "language_code": command.language_code,
                "output_file_path": command.output_file_path,
                "file_format": command.file_format,
                "exported_entries_count": len(translation_entries),
                "file_size_bytes": len(serialized_content),
            }

            self._logger.info(
                f"翻译导出完成: 导出 {len(translation_entries)} 个条目到 {command.output_file_path}"
            )

            return await self._create_success_result(
                result_data,
                execution_time,
                {
                    "export_options": {
                        "include_empty": command.include_empty,
                        "include_comments": command.include_comments,
                        "sort_keys": command.sort_keys,
                    }
                },
            )

        except Exception as e:
            error_msg = f"导出翻译失败: {str(e)}"
            self._logger.error(error_msg)

            end_time = datetime.utcnow()
            execution_time = int((end_time - start_time).total_seconds() * 1000)

            return await self._create_error_result(
                error_msg, "EXPORT_ERROR", execution_time
            )

    def can_handle(self, command: BaseCommand) -> bool:
        return isinstance(command, ExportTranslationsCommand)

    async def _get_project_translations(
        self, project_id: str, language_code: LanguageCode, include_empty: bool
    ) -> dict:
        """获取项目翻译数据（简化实现）"""
        # 这里应该从数据库查询实际的翻译数据
        # 现在返回空字典作为占位
        return {}


class UpdateTranslationCommandHandler(
    BaseCommandHandler[UpdateTranslationCommand, bool]
):
    """更新翻译命令处理器"""

    def __init__(self, translation_extractor_service: TranslationExtractorService):
        super().__init__()
        self._translation_extractor_service = translation_extractor_service

    async def handle(self, command: UpdateTranslationCommand) -> CommandResult[bool]:
        """处理更新翻译命令"""
        start_time = datetime.utcnow()

        try:
            self._logger.info(f"开始更新翻译: {command.translation_key}")

            # 验证命令
            validation_errors = await self._validate_command(command)
            if validation_errors:
                return await self._create_error_result(
                    f"命令验证失败: {'; '.join(validation_errors)}", "VALIDATION_ERROR"
                )

            # 验证占位符（如果启用）
            if command.validate_placeholders:
                placeholder_errors = await self._validate_placeholders(
                    command.translation_key, command.new_value
                )
                if placeholder_errors:
                    return await self._create_error_result(
                        f"占位符验证失败: {'; '.join(placeholder_errors)}",
                        "PLACEHOLDER_VALIDATION_ERROR",
                    )

            # 执行更新（简化实现）
            updated = await self._update_translation_entry(
                project_id=command.project_id,
                translation_key=TranslationKey(command.translation_key),
                language_code=LanguageCode(command.language_code),
                new_value=command.new_value,
                comment=command.comment,
            )

            end_time = datetime.utcnow()
            execution_time = int((end_time - start_time).total_seconds() * 1000)

            if updated:
                self._logger.info(f"翻译更新成功: {command.translation_key}")
            else:
                self._logger.warning(f"翻译更新无变化: {command.translation_key}")

            return await self._create_success_result(
                updated,
                execution_time,
                {
                    "project_id": command.project_id,
                    "translation_key": command.translation_key,
                    "language_code": command.language_code,
                    "old_value": None,  # 应该从数据库获取
                    "new_value": command.new_value,
                },
            )

        except Exception as e:
            error_msg = f"更新翻译失败: {str(e)}"
            self._logger.error(error_msg)

            end_time = datetime.utcnow()
            execution_time = int((end_time - start_time).total_seconds() * 1000)

            return await self._create_error_result(
                error_msg, "UPDATE_ERROR", execution_time
            )

    def can_handle(self, command: BaseCommand) -> bool:
        return isinstance(command, UpdateTranslationCommand)

    async def _validate_placeholders(
        self, translation_key: str, new_value: str
    ) -> list[str]:
        """验证占位符"""
        errors = []

        # 简化的占位符验证逻辑
        # 实际应该与源语言对比，确保占位符数量和类型匹配

        import re

        re.findall(r"%[sdfc]|\{[0-9]+\}|\{[a-zA-Z_][a-zA-Z0-9_]*\}", new_value)

        # 这里可以添加更复杂的验证逻辑

        return errors

    async def _update_translation_entry(
        self,
        project_id: str,
        translation_key: TranslationKey,
        language_code: LanguageCode,
        new_value: str,
        comment: str | None,
    ) -> bool:
        """更新翻译条目（简化实现）"""
        # 这里应该与数据库交互，更新翻译条目
        return True
