"""
模组查询处理器

实现模组相关的查询操作
"""

from dataclasses import dataclass
from datetime import datetime
from typing import Any

from domain.models.aggregates.mod import Mod
from domain.models.enums import FileType, ModLoaderType
from domain.services.mod_analyzer_service import ModAnalyzerService
from .base_query import (
    BaseQuery,
    BaseQueryHandler,
    FilterQuery,
    PaginationQuery,
    QueryResult,
    SortingQuery,
)


@dataclass
class GetModByIdQuery(BaseQuery):
    """根据ID获取模组查询"""

    project_id: str
    mod_id: str
    include_language_files: bool = True
    include_dependencies: bool = True
    include_statistics: bool = False

    def validate(self) -> list[str]:
        errors = []

        if not self.project_id:
            errors.append("项目ID不能为空")

        if not self.mod_id:
            errors.append("模组ID不能为空")

        return errors


@dataclass
class GetModsQuery(BaseQuery):
    """获取模组列表查询"""

    project_id: str
    pagination: PaginationQuery
    sorting: SortingQuery
    filters: FilterQuery
    loader_type_filter: str | None = None
    mc_version_filter: str | None = None

    def __init__(
        self,
        project_id: str,
        page: int = 1,
        page_size: int = 20,
        sort_field: str = "name",
        sort_direction: str = "asc",
        search_text: str | None = None,
        loader_type_filter: str | None = None,
        mc_version_filter: str | None = None,
        **kwargs,
    ):
        super().__init__(**kwargs)

        self.project_id = project_id
        self.pagination = PaginationQuery(page=page, page_size=page_size)
        self.sorting = SortingQuery(
            sort_field=sort_field, sort_direction=sort_direction
        )

        filters = {}
        if loader_type_filter:
            filters["loader_type"] = loader_type_filter
        if mc_version_filter:
            filters["mc_version"] = mc_version_filter

        self.filters = FilterQuery(filters=filters, search_text=search_text)
        self.loader_type_filter = loader_type_filter
        self.mc_version_filter = mc_version_filter

    def validate(self) -> list[str]:
        errors = []

        if not self.project_id:
            errors.append("项目ID不能为空")

        # 验证模组加载器类型
        if self.loader_type_filter:
            try:
                ModLoaderType(self.loader_type_filter)
            except ValueError:
                errors.append(f"无效的模组加载器类型: {self.loader_type_filter}")

        # 验证排序字段
        allowed_sort_fields = ["name", "mod_id", "version", "loader_type", "created_at"]
        if (
            self.sorting.sort_field
            and self.sorting.sort_field not in allowed_sort_fields
        ):
            errors.append(f"不支持的排序字段: {self.sorting.sort_field}")

        return errors


@dataclass
class GetModLanguageFilesQuery(BaseQuery):
    """获取模组语言文件查询"""

    project_id: str
    mod_id: str
    file_type_filter: str | None = None
    language_filter: str | None = None

    def validate(self) -> list[str]:
        errors = []

        if not self.project_id:
            errors.append("项目ID不能为空")

        if not self.mod_id:
            errors.append("模组ID不能为空")

        # 验证文件类型过滤器
        if self.file_type_filter:
            try:
                FileType(self.file_type_filter)
            except ValueError:
                errors.append(f"无效的文件类型: {self.file_type_filter}")

        return errors


@dataclass
class GetModDependenciesQuery(BaseQuery):
    """获取模组依赖关系查询"""

    project_id: str
    mod_id: str
    include_reverse_dependencies: bool = False
    depth_limit: int = 3

    def validate(self) -> list[str]:
        errors = []

        if not self.project_id:
            errors.append("项目ID不能为空")

        if not self.mod_id:
            errors.append("模组ID不能为空")

        if self.depth_limit < 1 or self.depth_limit > 10:
            errors.append("依赖深度限制必须在1-10之间")

        return errors


@dataclass
class GetModStatisticsQuery(BaseQuery):
    """获取模组统计信息查询"""

    project_id: str
    mod_id: str | None = None  # 如果为空则获取所有模组统计
    include_translation_stats: bool = True
    include_file_stats: bool = True
    group_by_language: bool = False

    def validate(self) -> list[str]:
        errors = []

        if not self.project_id:
            errors.append("项目ID不能为空")

        return errors


@dataclass
class SearchModsQuery(BaseQuery):
    """搜索模组查询"""

    project_id: str
    search_text: str
    search_fields: list[str]
    pagination: PaginationQuery
    filters: FilterQuery

    def __init__(
        self,
        project_id: str,
        search_text: str,
        search_fields: list[str] = None,
        page: int = 1,
        page_size: int = 20,
        **kwargs,
    ):
        super().__init__(**kwargs)

        self.project_id = project_id
        self.search_text = search_text
        self.search_fields = search_fields or ["name", "mod_id", "description"]
        self.pagination = PaginationQuery(page=page, page_size=page_size)
        self.filters = FilterQuery()

    def validate(self) -> list[str]:
        errors = []

        if not self.project_id:
            errors.append("项目ID不能为空")

        if not self.search_text or len(self.search_text.strip()) < 2:
            errors.append("搜索文本至少需要2个字符")

        allowed_search_fields = ["name", "mod_id", "description", "author"]
        for field in self.search_fields:
            if field not in allowed_search_fields:
                errors.append(f"不支持的搜索字段: {field}")

        return errors


class GetModByIdQueryHandler(BaseQueryHandler[GetModByIdQuery, dict[str, Any]]):
    """获取模组详情查询处理器"""

    def __init__(self, mod_analyzer_service: ModAnalyzerService):
        super().__init__()
        self._mod_analyzer_service = mod_analyzer_service

    async def handle(self, query: GetModByIdQuery) -> QueryResult[dict[str, Any]]:
        """处理获取模组详情查询"""
        start_time = datetime.utcnow()

        try:
            self._logger.info(f"开始查询模组详情: {query.mod_id}")

            # 验证查询
            validation_errors = await self._validate_query(query)
            if validation_errors:
                return await self._create_error_result(
                    f"查询验证失败: {'; '.join(validation_errors)}", "VALIDATION_ERROR"
                )

            # 获取模组（简化实现）
            mod = await self._get_mod_by_id(query.project_id, query.mod_id)
            if not mod:
                return await self._create_error_result(
                    f"模组不存在: {query.mod_id}", "MOD_NOT_FOUND"
                )

            # 构建结果
            result_data = await self._build_mod_detail(
                mod,
                query.include_language_files,
                query.include_dependencies,
                query.include_statistics,
            )

            end_time = datetime.utcnow()
            execution_time = int((end_time - start_time).total_seconds() * 1000)

            self._logger.info(f"模组详情查询完成: {mod.name}")

            return await self._create_success_result(
                result_data,
                execution_time,
                {
                    "project_id": query.project_id,
                    "mod_id": query.mod_id,
                    "query_options": {
                        "include_language_files": query.include_language_files,
                        "include_dependencies": query.include_dependencies,
                        "include_statistics": query.include_statistics,
                    },
                },
            )

        except Exception as e:
            error_msg = f"查询模组详情失败: {str(e)}"
            self._logger.error(error_msg)

            end_time = datetime.utcnow()
            execution_time = int((end_time - start_time).total_seconds() * 1000)

            return await self._create_error_result(
                error_msg, "QUERY_ERROR", execution_time
            )

    def can_handle(self, query: BaseQuery) -> bool:
        return isinstance(query, GetModByIdQuery)

    async def _get_mod_by_id(self, project_id: str, mod_id: str) -> Mod | None:
        """获取模组（简化实现）"""
        # 这里应该从数据库查询实际的模组数据
        return None

    async def _build_mod_detail(
        self,
        mod: Mod,
        include_language_files: bool,
        include_dependencies: bool,
        include_statistics: bool,
    ) -> dict[str, Any]:
        """构建模组详情数据"""
        result = {
            "mod_id": mod.mod_id.value,
            "name": mod.name,
            "version": mod.version,
            "description": mod.description,
            "author": mod.author,
            "loader_type": mod.loader_type.value if mod.loader_type else None,
            "minecraft_versions": mod.minecraft_versions,
            "file_path": mod.file_path.value,
            "file_size_bytes": mod.file_size_bytes,
            "created_at": mod.created_at.isoformat(),
            "updated_at": mod.updated_at.isoformat() if mod.updated_at else None,
            "metadata": mod.metadata,
        }

        if include_language_files:
            result["language_files"] = await self._get_mod_language_files(
                mod.mod_id.value
            )

        if include_dependencies:
            result["dependencies"] = await self._get_mod_dependencies(mod.mod_id.value)

        if include_statistics:
            result["statistics"] = await self._get_mod_statistics(mod.mod_id.value)

        return result

    async def _get_mod_language_files(self, mod_id: str) -> list[dict[str, Any]]:
        """获取模组语言文件（简化实现）"""
        return []

    async def _get_mod_dependencies(self, mod_id: str) -> list[dict[str, Any]]:
        """获取模组依赖（简化实现）"""
        return []

    async def _get_mod_statistics(self, mod_id: str) -> dict[str, Any]:
        """获取模组统计（简化实现）"""
        return {
            "total_language_files": 0,
            "total_translation_entries": 0,
            "supported_languages": [],
            "translation_progress": {},
        }


class GetModsQueryHandler(BaseQueryHandler[GetModsQuery, dict[str, Any]]):
    """获取模组列表查询处理器"""

    def __init__(self, mod_analyzer_service: ModAnalyzerService):
        super().__init__()
        self._mod_analyzer_service = mod_analyzer_service

    async def handle(self, query: GetModsQuery) -> QueryResult[dict[str, Any]]:
        """处理获取模组列表查询"""
        start_time = datetime.utcnow()

        try:
            self._logger.info(f"开始查询模组列表: {query.project_id}")

            # 验证查询
            validation_errors = await self._validate_query(query)
            if validation_errors:
                return await self._create_error_result(
                    f"查询验证失败: {'; '.join(validation_errors)}", "VALIDATION_ERROR"
                )

            # 执行查询
            mods, total_count = await self._get_mods_with_filters(query)

            # 构建结果
            mod_list = []
            for mod in mods:
                mod_data = await self._build_mod_summary(mod)
                mod_list.append(mod_data)

            result_data = {
                "mods": mod_list,
                "pagination": {
                    "page": query.pagination.page,
                    "page_size": query.pagination.page_size,
                    "total_count": total_count,
                    "total_pages": (total_count + query.pagination.page_size - 1)
                    // query.pagination.page_size,
                    "has_next": query.pagination.offset + len(mod_list) < total_count,
                    "has_prev": query.pagination.page > 1,
                },
                "filters_applied": {
                    "loader_type_filter": query.loader_type_filter,
                    "mc_version_filter": query.mc_version_filter,
                    "search_text": query.filters.search_text,
                },
            }

            end_time = datetime.utcnow()
            execution_time = int((end_time - start_time).total_seconds() * 1000)

            self._logger.info(f"模组列表查询完成: 返回 {len(mod_list)} 个模组")

            return await self._create_success_result(
                result_data,
                execution_time,
                {
                    "project_id": query.project_id,
                    "applied_filters": query.filters.filters,
                },
                total_count,
            )

        except Exception as e:
            error_msg = f"查询模组列表失败: {str(e)}"
            self._logger.error(error_msg)

            end_time = datetime.utcnow()
            execution_time = int((end_time - start_time).total_seconds() * 1000)

            return await self._create_error_result(
                error_msg, "QUERY_ERROR", execution_time
            )

    def can_handle(self, query: BaseQuery) -> bool:
        return isinstance(query, GetModsQuery)

    async def _get_mods_with_filters(
        self, query: GetModsQuery
    ) -> tuple[list[Mod], int]:
        """根据过滤条件获取模组列表（简化实现）"""
        # 这里应该从数据库查询，应用各种过滤条件
        return [], 0

    async def _build_mod_summary(self, mod: Mod) -> dict[str, Any]:
        """构建模组摘要数据"""
        return {
            "mod_id": mod.mod_id.value,
            "name": mod.name,
            "version": mod.version,
            "author": mod.author,
            "loader_type": mod.loader_type.value if mod.loader_type else None,
            "minecraft_versions": mod.minecraft_versions,
            "file_size_mb": round(mod.file_size_bytes / (1024 * 1024), 2),
            "created_at": mod.created_at.isoformat(),
            "has_language_files": len(mod.language_files) > 0,
        }


class GetModLanguageFilesQueryHandler(
    BaseQueryHandler[GetModLanguageFilesQuery, dict[str, Any]]
):
    """获取模组语言文件查询处理器"""

    def __init__(self, mod_analyzer_service: ModAnalyzerService):
        super().__init__()
        self._mod_analyzer_service = mod_analyzer_service

    async def handle(
        self, query: GetModLanguageFilesQuery
    ) -> QueryResult[dict[str, Any]]:
        """处理获取模组语言文件查询"""
        start_time = datetime.utcnow()

        try:
            self._logger.info(f"开始查询模组语言文件: {query.mod_id}")

            # 验证查询
            validation_errors = await self._validate_query(query)
            if validation_errors:
                return await self._create_error_result(
                    f"查询验证失败: {'; '.join(validation_errors)}", "VALIDATION_ERROR"
                )

            # 获取模组语言文件
            language_files = await self._get_mod_language_files_with_filters(
                query.project_id,
                query.mod_id,
                query.file_type_filter,
                query.language_filter,
            )

            # 构建结果
            files_data = []
            for lang_file in language_files:
                file_data = await self._build_language_file_data(lang_file)
                files_data.append(file_data)

            # 统计信息
            file_type_counts = {}
            language_counts = {}

            for file_data in files_data:
                file_type = file_data["file_type"]
                language = file_data["language_code"]

                file_type_counts[file_type] = file_type_counts.get(file_type, 0) + 1
                language_counts[language] = language_counts.get(language, 0) + 1

            result_data = {
                "mod_id": query.mod_id,
                "language_files": files_data,
                "statistics": {
                    "total_files": len(files_data),
                    "by_file_type": file_type_counts,
                    "by_language": language_counts,
                    "supported_languages": list(language_counts.keys()),
                },
                "filters_applied": {
                    "file_type_filter": query.file_type_filter,
                    "language_filter": query.language_filter,
                },
            }

            end_time = datetime.utcnow()
            execution_time = int((end_time - start_time).total_seconds() * 1000)

            self._logger.info(f"模组语言文件查询完成: 返回 {len(files_data)} 个文件")

            return await self._create_success_result(
                result_data,
                execution_time,
                {"project_id": query.project_id, "mod_id": query.mod_id},
            )

        except Exception as e:
            error_msg = f"查询模组语言文件失败: {str(e)}"
            self._logger.error(error_msg)

            end_time = datetime.utcnow()
            execution_time = int((end_time - start_time).total_seconds() * 1000)

            return await self._create_error_result(
                error_msg, "QUERY_ERROR", execution_time
            )

    def can_handle(self, query: BaseQuery) -> bool:
        return isinstance(query, GetModLanguageFilesQuery)

    async def _get_mod_language_files_with_filters(
        self,
        project_id: str,
        mod_id: str,
        file_type_filter: str | None,
        language_filter: str | None,
    ) -> list:
        """根据过滤条件获取模组语言文件（简化实现）"""
        return []

    async def _build_language_file_data(self, lang_file) -> dict[str, Any]:
        """构建语言文件数据"""
        return {
            "file_id": "temp_id",
            "file_path": "temp_path",
            "language_code": "en_us",
            "file_type": "json",
            "entry_count": 0,
            "file_size_bytes": 0,
            "last_modified": datetime.utcnow().isoformat(),
        }


class GetModStatisticsQueryHandler(
    BaseQueryHandler[GetModStatisticsQuery, dict[str, Any]]
):
    """获取模组统计信息查询处理器"""

    def __init__(self, mod_analyzer_service: ModAnalyzerService):
        super().__init__()
        self._mod_analyzer_service = mod_analyzer_service

    async def handle(self, query: GetModStatisticsQuery) -> QueryResult[dict[str, Any]]:
        """处理获取模组统计信息查询"""
        start_time = datetime.utcnow()

        try:
            self._logger.info(f"开始查询模组统计信息: {query.project_id}")

            # 验证查询
            validation_errors = await self._validate_query(query)
            if validation_errors:
                return await self._create_error_result(
                    f"查询验证失败: {'; '.join(validation_errors)}", "VALIDATION_ERROR"
                )

            # 获取统计信息
            if query.mod_id:
                # 单个模组统计
                statistics = await self._get_single_mod_statistics(
                    query.project_id,
                    query.mod_id,
                    query.include_translation_stats,
                    query.include_file_stats,
                    query.group_by_language,
                )
            else:
                # 所有模组统计
                statistics = await self._get_all_mods_statistics(
                    query.project_id,
                    query.include_translation_stats,
                    query.include_file_stats,
                    query.group_by_language,
                )

            end_time = datetime.utcnow()
            execution_time = int((end_time - start_time).total_seconds() * 1000)

            self._logger.info(f"模组统计信息查询完成: {query.project_id}")

            return await self._create_success_result(
                statistics,
                execution_time,
                {
                    "project_id": query.project_id,
                    "mod_id": query.mod_id,
                    "statistics_options": {
                        "include_translation_stats": query.include_translation_stats,
                        "include_file_stats": query.include_file_stats,
                        "group_by_language": query.group_by_language,
                    },
                },
            )

        except Exception as e:
            error_msg = f"查询模组统计信息失败: {str(e)}"
            self._logger.error(error_msg)

            end_time = datetime.utcnow()
            execution_time = int((end_time - start_time).total_seconds() * 1000)

            return await self._create_error_result(
                error_msg, "QUERY_ERROR", execution_time
            )

    def can_handle(self, query: BaseQuery) -> bool:
        return isinstance(query, GetModStatisticsQuery)

    async def _get_single_mod_statistics(
        self,
        project_id: str,
        mod_id: str,
        include_translation_stats: bool,
        include_file_stats: bool,
        group_by_language: bool,
    ) -> dict[str, Any]:
        """获取单个模组统计信息（简化实现）"""
        return {
            "project_id": project_id,
            "mod_id": mod_id,
            "generated_at": datetime.utcnow().isoformat(),
            "basic_stats": {
                "total_language_files": 0,
                "supported_languages": [],
                "total_size_mb": 0.0,
            },
        }

    async def _get_all_mods_statistics(
        self,
        project_id: str,
        include_translation_stats: bool,
        include_file_stats: bool,
        group_by_language: bool,
    ) -> dict[str, Any]:
        """获取所有模组统计信息（简化实现）"""
        return {
            "project_id": project_id,
            "generated_at": datetime.utcnow().isoformat(),
            "overview": {
                "total_mods": 0,
                "total_language_files": 0,
                "total_translation_entries": 0,
                "average_entries_per_mod": 0.0,
            },
            "by_loader_type": {},
            "by_mc_version": {},
        }
