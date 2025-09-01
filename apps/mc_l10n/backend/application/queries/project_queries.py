"""
项目查询处理器

实现翻译项目相关的查询操作
"""

from dataclasses import dataclass
from datetime import datetime
from typing import Any

from domain.models.aggregates.translation_project import TranslationProject
from domain.services.project_service import ProjectService
from .base_query import (
    BaseQuery,
    BaseQueryHandler,
    FilterQuery,
    PaginationQuery,
    QueryResult,
    SortingQuery,
)


@dataclass
class GetProjectByIdQuery(BaseQuery):
    """根据ID获取项目查询"""

    project_id: str
    include_statistics: bool = True

    def validate(self) -> list[str]:
        errors = []

        if not self.project_id:
            errors.append("项目ID不能为空")

        return errors


@dataclass
class GetProjectsQuery(BaseQuery):
    """获取项目列表查询"""

    pagination: PaginationQuery
    sorting: SortingQuery
    filters: FilterQuery
    include_archived: bool = False
    include_statistics: bool = False

    def __init__(
        self,
        page: int = 1,
        page_size: int = 20,
        sort_field: str = "created_at",
        sort_direction: str = "desc",
        search_text: str | None = None,
        mc_version_filter: str | None = None,
        language_filter: str | None = None,
        include_archived: bool = False,
        include_statistics: bool = False,
        **kwargs,
    ):
        super().__init__(**kwargs)

        self.pagination = PaginationQuery(page=page, page_size=page_size)
        self.sorting = SortingQuery(
            sort_field=sort_field, sort_direction=sort_direction
        )

        filters = {}
        if mc_version_filter:
            filters["mc_version"] = mc_version_filter
        if language_filter:
            filters["target_language"] = language_filter

        self.filters = FilterQuery(filters=filters, search_text=search_text)
        self.include_archived = include_archived
        self.include_statistics = include_statistics

    def validate(self) -> list[str]:
        errors = []

        # 验证排序字段
        allowed_sort_fields = [
            "name",
            "created_at",
            "updated_at",
            "mc_version",
            "target_language",
        ]
        if (
            self.sorting.sort_field
            and self.sorting.sort_field not in allowed_sort_fields
        ):
            errors.append(f"不支持的排序字段: {self.sorting.sort_field}")

        return errors


@dataclass
class GetProjectStatisticsQuery(BaseQuery):
    """获取项目统计信息查询"""

    project_id: str
    include_translation_progress: bool = True
    include_file_statistics: bool = True
    include_mod_statistics: bool = True

    def validate(self) -> list[str]:
        errors = []

        if not self.project_id:
            errors.append("项目ID不能为空")

        return errors


@dataclass
class SearchProjectsQuery(BaseQuery):
    """搜索项目查询"""

    search_text: str
    search_fields: list[str]
    pagination: PaginationQuery
    filters: FilterQuery

    def __init__(
        self,
        search_text: str,
        search_fields: list[str] = None,
        page: int = 1,
        page_size: int = 20,
        **kwargs,
    ):
        super().__init__(**kwargs)

        self.search_text = search_text
        self.search_fields = search_fields or ["name", "description"]
        self.pagination = PaginationQuery(page=page, page_size=page_size)
        self.filters = FilterQuery()

    def validate(self) -> list[str]:
        errors = []

        if not self.search_text or len(self.search_text.strip()) < 2:
            errors.append("搜索文本至少需要2个字符")

        allowed_search_fields = ["name", "description", "mc_version"]
        for field in self.search_fields:
            if field not in allowed_search_fields:
                errors.append(f"不支持的搜索字段: {field}")

        return errors


class GetProjectByIdQueryHandler(BaseQueryHandler[GetProjectByIdQuery, dict[str, Any]]):
    """获取项目详情查询处理器"""

    def __init__(self, project_service: ProjectService):
        super().__init__()
        self._project_service = project_service

    async def handle(self, query: GetProjectByIdQuery) -> QueryResult[dict[str, Any]]:
        """处理获取项目详情查询"""
        start_time = datetime.utcnow()

        try:
            self._logger.info(f"开始查询项目详情: {query.project_id}")

            # 验证查询
            validation_errors = await self._validate_query(query)
            if validation_errors:
                return await self._create_error_result(
                    f"查询验证失败: {'; '.join(validation_errors)}", "VALIDATION_ERROR"
                )

            # 获取项目
            project = await self._project_service.get_project_by_id(query.project_id)
            if not project:
                return await self._create_error_result(
                    f"项目不存在: {query.project_id}", "PROJECT_NOT_FOUND"
                )

            # 构建结果
            result_data = await self._build_project_detail(
                project, query.include_statistics
            )

            end_time = datetime.utcnow()
            execution_time = int((end_time - start_time).total_seconds() * 1000)

            self._logger.info(f"项目详情查询完成: {project.name.value}")

            return await self._create_success_result(
                result_data,
                execution_time,
                {
                    "project_id": query.project_id,
                    "include_statistics": query.include_statistics,
                },
            )

        except Exception as e:
            error_msg = f"查询项目详情失败: {str(e)}"
            self._logger.error(error_msg)

            end_time = datetime.utcnow()
            execution_time = int((end_time - start_time).total_seconds() * 1000)

            return await self._create_error_result(
                error_msg, "QUERY_ERROR", execution_time
            )

    def can_handle(self, query: BaseQuery) -> bool:
        return isinstance(query, GetProjectByIdQuery)

    async def _build_project_detail(
        self, project: TranslationProject, include_statistics: bool
    ) -> dict[str, Any]:
        """构建项目详情数据"""
        result = {
            "project_id": project.project_id.value,
            "name": project.name.value,
            "description": project.description,
            "mc_version": project.mc_version,
            "target_language": project.target_language.code,
            "source_path": project.source_path.value,
            "output_path": project.output_path.value,
            "created_at": project.created_at.isoformat(),
            "updated_at": project.updated_at.isoformat()
            if project.updated_at
            else None,
            "is_archived": project.is_archived,
            "archive_reason": project.archive_reason,
        }

        if include_statistics:
            # 获取项目统计信息
            statistics = await self._get_project_statistics(project.project_id.value)
            result["statistics"] = statistics

        return result

    async def _get_project_statistics(self, project_id: str) -> dict[str, Any]:
        """获取项目统计信息（简化实现）"""
        return {
            "total_mods": 0,
            "total_translation_files": 0,
            "total_translation_entries": 0,
            "translated_entries": 0,
            "translation_progress": 0.0,
            "last_translation_update": None,
        }


class GetProjectsQueryHandler(BaseQueryHandler[GetProjectsQuery, dict[str, Any]]):
    """获取项目列表查询处理器"""

    def __init__(self, project_service: ProjectService):
        super().__init__()
        self._project_service = project_service

    async def handle(self, query: GetProjectsQuery) -> QueryResult[dict[str, Any]]:
        """处理获取项目列表查询"""
        start_time = datetime.utcnow()

        try:
            self._logger.info("开始查询项目列表")

            # 验证查询
            validation_errors = await self._validate_query(query)
            if validation_errors:
                return await self._create_error_result(
                    f"查询验证失败: {'; '.join(validation_errors)}", "VALIDATION_ERROR"
                )

            # 执行查询
            projects, total_count = await self._project_service.get_projects(
                offset=query.pagination.offset,
                limit=query.pagination.limit,
                sort_field=query.sorting.sort_field,
                sort_direction=query.sorting.sort_direction,
                filters=query.filters.filters,
                search_text=query.filters.search_text,
                include_archived=query.include_archived,
            )

            # 构建结果
            project_list = []
            for project in projects:
                project_data = await self._build_project_summary(
                    project, query.include_statistics
                )
                project_list.append(project_data)

            result_data = {
                "projects": project_list,
                "pagination": {
                    "page": query.pagination.page,
                    "page_size": query.pagination.page_size,
                    "total_count": total_count,
                    "total_pages": (total_count + query.pagination.page_size - 1)
                    // query.pagination.page_size,
                    "has_next": query.pagination.offset + len(project_list)
                    < total_count,
                    "has_prev": query.pagination.page > 1,
                },
            }

            end_time = datetime.utcnow()
            execution_time = int((end_time - start_time).total_seconds() * 1000)

            self._logger.info(f"项目列表查询完成: 返回 {len(project_list)} 个项目")

            return await self._create_success_result(
                result_data,
                execution_time,
                {
                    "query_filters": query.filters.filters,
                    "search_text": query.filters.search_text,
                },
                total_count,
            )

        except Exception as e:
            error_msg = f"查询项目列表失败: {str(e)}"
            self._logger.error(error_msg)

            end_time = datetime.utcnow()
            execution_time = int((end_time - start_time).total_seconds() * 1000)

            return await self._create_error_result(
                error_msg, "QUERY_ERROR", execution_time
            )

    def can_handle(self, query: BaseQuery) -> bool:
        return isinstance(query, GetProjectsQuery)

    async def _build_project_summary(
        self, project: TranslationProject, include_statistics: bool
    ) -> dict[str, Any]:
        """构建项目摘要数据"""
        result = {
            "project_id": project.project_id.value,
            "name": project.name.value,
            "description": project.description,
            "mc_version": project.mc_version,
            "target_language": project.target_language.code,
            "created_at": project.created_at.isoformat(),
            "updated_at": project.updated_at.isoformat()
            if project.updated_at
            else None,
            "is_archived": project.is_archived,
        }

        if include_statistics:
            # 获取基础统计信息
            statistics = await self._get_project_basic_statistics(
                project.project_id.value
            )
            result["statistics"] = statistics

        return result

    async def _get_project_basic_statistics(self, project_id: str) -> dict[str, Any]:
        """获取项目基础统计信息（简化实现）"""
        return {"total_mods": 0, "total_entries": 0, "translation_progress": 0.0}


class GetProjectStatisticsQueryHandler(
    BaseQueryHandler[GetProjectStatisticsQuery, dict[str, Any]]
):
    """获取项目统计信息查询处理器"""

    def __init__(self, project_service: ProjectService):
        super().__init__()
        self._project_service = project_service

    async def handle(
        self, query: GetProjectStatisticsQuery
    ) -> QueryResult[dict[str, Any]]:
        """处理获取项目统计信息查询"""
        start_time = datetime.utcnow()

        try:
            self._logger.info(f"开始查询项目统计信息: {query.project_id}")

            # 验证查询
            validation_errors = await self._validate_query(query)
            if validation_errors:
                return await self._create_error_result(
                    f"查询验证失败: {'; '.join(validation_errors)}", "VALIDATION_ERROR"
                )

            # 检查项目是否存在
            project = await self._project_service.get_project_by_id(query.project_id)
            if not project:
                return await self._create_error_result(
                    f"项目不存在: {query.project_id}", "PROJECT_NOT_FOUND"
                )

            # 构建统计信息
            statistics = await self._build_comprehensive_statistics(
                query.project_id,
                query.include_translation_progress,
                query.include_file_statistics,
                query.include_mod_statistics,
            )

            end_time = datetime.utcnow()
            execution_time = int((end_time - start_time).total_seconds() * 1000)

            self._logger.info(f"项目统计信息查询完成: {query.project_id}")

            return await self._create_success_result(
                statistics,
                execution_time,
                {
                    "project_id": query.project_id,
                    "statistics_options": {
                        "include_translation_progress": query.include_translation_progress,
                        "include_file_statistics": query.include_file_statistics,
                        "include_mod_statistics": query.include_mod_statistics,
                    },
                },
            )

        except Exception as e:
            error_msg = f"查询项目统计信息失败: {str(e)}"
            self._logger.error(error_msg)

            end_time = datetime.utcnow()
            execution_time = int((end_time - start_time).total_seconds() * 1000)

            return await self._create_error_result(
                error_msg, "QUERY_ERROR", execution_time
            )

    def can_handle(self, query: BaseQuery) -> bool:
        return isinstance(query, GetProjectStatisticsQuery)

    async def _build_comprehensive_statistics(
        self,
        project_id: str,
        include_translation_progress: bool,
        include_file_statistics: bool,
        include_mod_statistics: bool,
    ) -> dict[str, Any]:
        """构建综合统计信息"""
        statistics = {
            "project_id": project_id,
            "generated_at": datetime.utcnow().isoformat(),
        }

        if include_translation_progress:
            statistics[
                "translation_progress"
            ] = await self._get_translation_progress_statistics(project_id)

        if include_file_statistics:
            statistics["file_statistics"] = await self._get_file_statistics(project_id)

        if include_mod_statistics:
            statistics["mod_statistics"] = await self._get_mod_statistics(project_id)

        return statistics

    async def _get_translation_progress_statistics(
        self, project_id: str
    ) -> dict[str, Any]:
        """获取翻译进度统计（简化实现）"""
        return {
            "total_entries": 0,
            "translated_entries": 0,
            "untranslated_entries": 0,
            "progress_percentage": 0.0,
            "by_mod": {},
            "by_category": {},
        }

    async def _get_file_statistics(self, project_id: str) -> dict[str, Any]:
        """获取文件统计（简化实现）"""
        return {
            "total_files": 0,
            "json_files": 0,
            "properties_files": 0,
            "by_mod": {},
            "average_entries_per_file": 0.0,
        }

    async def _get_mod_statistics(self, project_id: str) -> dict[str, Any]:
        """获取模组统计（简化实现）"""
        return {
            "total_mods": 0,
            "by_loader_type": {},
            "by_mc_version": {},
            "top_mods_by_entries": [],
        }


class SearchProjectsQueryHandler(BaseQueryHandler[SearchProjectsQuery, dict[str, Any]]):
    """搜索项目查询处理器"""

    def __init__(self, project_service: ProjectService):
        super().__init__()
        self._project_service = project_service

    async def handle(self, query: SearchProjectsQuery) -> QueryResult[dict[str, Any]]:
        """处理搜索项目查询"""
        start_time = datetime.utcnow()

        try:
            self._logger.info(f"开始搜索项目: '{query.search_text}'")

            # 验证查询
            validation_errors = await self._validate_query(query)
            if validation_errors:
                return await self._create_error_result(
                    f"查询验证失败: {'; '.join(validation_errors)}", "VALIDATION_ERROR"
                )

            # 执行搜索
            projects, total_count = await self._project_service.search_projects(
                search_text=query.search_text,
                search_fields=query.search_fields,
                offset=query.pagination.offset,
                limit=query.pagination.limit,
                filters=query.filters.filters,
            )

            # 构建结果
            project_list = []
            for project in projects:
                project_data = await self._build_search_result(
                    project, query.search_text
                )
                project_list.append(project_data)

            result_data = {
                "projects": project_list,
                "search_query": {
                    "search_text": query.search_text,
                    "search_fields": query.search_fields,
                },
                "pagination": {
                    "page": query.pagination.page,
                    "page_size": query.pagination.page_size,
                    "total_count": total_count,
                    "total_pages": (total_count + query.pagination.page_size - 1)
                    // query.pagination.page_size,
                },
            }

            end_time = datetime.utcnow()
            execution_time = int((end_time - start_time).total_seconds() * 1000)

            self._logger.info(f"项目搜索完成: 找到 {len(project_list)} 个匹配项目")

            return await self._create_success_result(
                result_data,
                execution_time,
                {
                    "search_text": query.search_text,
                    "search_fields": query.search_fields,
                },
                total_count,
            )

        except Exception as e:
            error_msg = f"搜索项目失败: {str(e)}"
            self._logger.error(error_msg)

            end_time = datetime.utcnow()
            execution_time = int((end_time - start_time).total_seconds() * 1000)

            return await self._create_error_result(
                error_msg, "SEARCH_ERROR", execution_time
            )

    def can_handle(self, query: BaseQuery) -> bool:
        return isinstance(query, SearchProjectsQuery)

    async def _build_search_result(
        self, project: TranslationProject, search_text: str
    ) -> dict[str, Any]:
        """构建搜索结果数据"""
        result = {
            "project_id": project.project_id.value,
            "name": project.name.value,
            "description": project.description,
            "mc_version": project.mc_version,
            "target_language": project.target_language.code,
            "created_at": project.created_at.isoformat(),
            "match_highlights": await self._get_match_highlights(project, search_text),
        }

        return result

    async def _get_match_highlights(
        self, project: TranslationProject, search_text: str
    ) -> list[dict[str, str]]:
        """获取搜索匹配高亮（简化实现）"""
        highlights = []

        # 检查名称匹配
        if search_text.lower() in project.name.value.lower():
            highlights.append(
                {"field": "name", "text": project.name.value, "match": search_text}
            )

        # 检查描述匹配
        if project.description and search_text.lower() in project.description.lower():
            highlights.append(
                {
                    "field": "description",
                    "text": project.description[:100]
                    + ("..." if len(project.description) > 100 else ""),
                    "match": search_text,
                }
            )

        return highlights
