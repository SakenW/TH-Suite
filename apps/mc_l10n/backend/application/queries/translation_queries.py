"""
翻译查询处理器

实现翻译条目相关的查询操作
"""

from dataclasses import dataclass
from datetime import datetime
from typing import Any

from domain.models.entities.translation_entry import TranslationEntry
from domain.models.value_objects.language_code import LanguageCode
from domain.models.value_objects.translation_key import TranslationKey
from domain.services.translation_extractor_service import TranslationExtractorService
from .base_query import (
    BaseQuery,
    BaseQueryHandler,
    FilterQuery,
    PaginationQuery,
    QueryResult,
    SortingQuery,
)


@dataclass
class GetTranslationQuery(BaseQuery):
    """获取单个翻译条目查询"""

    project_id: str
    translation_key: str
    language_code: str
    include_metadata: bool = True

    def validate(self) -> list[str]:
        errors = []

        if not self.project_id:
            errors.append("项目ID不能为空")

        if not self.translation_key:
            errors.append("翻译键不能为空")

        if not self.language_code:
            errors.append("语言代码不能为空")

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
class GetTranslationsQuery(BaseQuery):
    """获取翻译条目列表查询"""

    project_id: str
    language_code: str
    pagination: PaginationQuery
    sorting: SortingQuery
    filters: FilterQuery
    status_filter: str | None = None  # "translated", "untranslated", "needs_review"
    mod_filter: str | None = None
    category_filter: str | None = None

    def __init__(
        self,
        project_id: str,
        language_code: str,
        page: int = 1,
        page_size: int = 50,
        sort_field: str = "key",
        sort_direction: str = "asc",
        search_text: str | None = None,
        status_filter: str | None = None,
        mod_filter: str | None = None,
        category_filter: str | None = None,
        **kwargs,
    ):
        super().__init__(**kwargs)

        self.project_id = project_id
        self.language_code = language_code
        self.pagination = PaginationQuery(page=page, page_size=page_size)
        self.sorting = SortingQuery(
            sort_field=sort_field, sort_direction=sort_direction
        )

        filters = {}
        if mod_filter:
            filters["mod_id"] = mod_filter
        if category_filter:
            filters["category"] = category_filter

        self.filters = FilterQuery(filters=filters, search_text=search_text)
        self.status_filter = status_filter
        self.mod_filter = mod_filter
        self.category_filter = category_filter

    def validate(self) -> list[str]:
        errors = []

        if not self.project_id:
            errors.append("项目ID不能为空")

        if not self.language_code:
            errors.append("语言代码不能为空")

        # 验证语言代码
        try:
            LanguageCode(self.language_code)
        except ValueError as e:
            errors.append(f"无效的语言代码: {str(e)}")

        # 验证状态过滤器
        if self.status_filter:
            allowed_statuses = [
                "translated",
                "untranslated",
                "needs_review",
                "outdated",
            ]
            if self.status_filter not in allowed_statuses:
                errors.append(f"无效的状态过滤器: {self.status_filter}")

        # 验证排序字段
        allowed_sort_fields = ["key", "value", "created_at", "updated_at", "mod_id"]
        if (
            self.sorting.sort_field
            and self.sorting.sort_field not in allowed_sort_fields
        ):
            errors.append(f"不支持的排序字段: {self.sorting.sort_field}")

        return errors


@dataclass
class GetTranslationProgressQuery(BaseQuery):
    """获取翻译进度查询"""

    project_id: str
    language_code: str | None = None  # 如果为空则获取所有语言
    group_by_mod: bool = True
    group_by_category: bool = False
    include_details: bool = False

    def validate(self) -> list[str]:
        errors = []

        if not self.project_id:
            errors.append("项目ID不能为空")

        # 验证语言代码（如果提供）
        if self.language_code:
            try:
                LanguageCode(self.language_code)
            except ValueError as e:
                errors.append(f"无效的语言代码: {str(e)}")

        return errors


@dataclass
class GetUntranslatedEntriesQuery(BaseQuery):
    """获取未翻译条目查询"""

    project_id: str
    language_code: str
    pagination: PaginationQuery
    priority_order: bool = True  # 是否按优先级排序
    mod_filter: str | None = None

    def __init__(
        self,
        project_id: str,
        language_code: str,
        page: int = 1,
        page_size: int = 50,
        priority_order: bool = True,
        mod_filter: str | None = None,
        **kwargs,
    ):
        super().__init__(**kwargs)

        self.project_id = project_id
        self.language_code = language_code
        self.pagination = PaginationQuery(page=page, page_size=page_size)
        self.priority_order = priority_order
        self.mod_filter = mod_filter

    def validate(self) -> list[str]:
        errors = []

        if not self.project_id:
            errors.append("项目ID不能为空")

        if not self.language_code:
            errors.append("语言代码不能为空")

        # 验证语言代码
        try:
            LanguageCode(self.language_code)
        except ValueError as e:
            errors.append(f"无效的语言代码: {str(e)}")

        return errors


@dataclass
class SearchTranslationsQuery(BaseQuery):
    """搜索翻译条目查询"""

    project_id: str
    search_text: str
    pagination: PaginationQuery
    search_in_keys: bool = True
    search_in_values: bool = True
    search_in_comments: bool = False
    language_codes: list[str] | None = None

    def __init__(
        self,
        project_id: str,
        search_text: str,
        search_in_keys: bool = True,
        search_in_values: bool = True,
        search_in_comments: bool = False,
        language_codes: list[str] | None = None,
        page: int = 1,
        page_size: int = 50,
        **kwargs,
    ):
        super().__init__(**kwargs)

        self.project_id = project_id
        self.search_text = search_text
        self.search_in_keys = search_in_keys
        self.search_in_values = search_in_values
        self.search_in_comments = search_in_comments
        self.language_codes = language_codes
        self.pagination = PaginationQuery(page=page, page_size=page_size)

    def validate(self) -> list[str]:
        errors = []

        if not self.project_id:
            errors.append("项目ID不能为空")

        if not self.search_text or len(self.search_text.strip()) < 2:
            errors.append("搜索文本至少需要2个字符")

        if not any(
            [self.search_in_keys, self.search_in_values, self.search_in_comments]
        ):
            errors.append("至少需要选择一个搜索范围")

        # 验证语言代码列表
        if self.language_codes:
            for code in self.language_codes:
                try:
                    LanguageCode(code)
                except ValueError as e:
                    errors.append(f"无效的语言代码 '{code}': {str(e)}")

        return errors


class GetTranslationQueryHandler(BaseQueryHandler[GetTranslationQuery, dict[str, Any]]):
    """获取翻译条目查询处理器"""

    def __init__(self, translation_extractor_service: TranslationExtractorService):
        super().__init__()
        self._translation_extractor_service = translation_extractor_service

    async def handle(self, query: GetTranslationQuery) -> QueryResult[dict[str, Any]]:
        """处理获取翻译条目查询"""
        start_time = datetime.utcnow()

        try:
            self._logger.info(f"开始查询翻译条目: {query.translation_key}")

            # 验证查询
            validation_errors = await self._validate_query(query)
            if validation_errors:
                return await self._create_error_result(
                    f"查询验证失败: {'; '.join(validation_errors)}", "VALIDATION_ERROR"
                )

            # 获取翻译条目（简化实现）
            translation_entry = await self._get_translation_entry(
                query.project_id,
                TranslationKey(query.translation_key),
                LanguageCode(query.language_code),
            )

            if not translation_entry:
                return await self._create_error_result(
                    f"翻译条目不存在: {query.translation_key}", "TRANSLATION_NOT_FOUND"
                )

            # 构建结果
            result_data = await self._build_translation_detail(
                translation_entry, query.include_metadata
            )

            end_time = datetime.utcnow()
            execution_time = int((end_time - start_time).total_seconds() * 1000)

            self._logger.info(f"翻译条目查询完成: {query.translation_key}")

            return await self._create_success_result(
                result_data,
                execution_time,
                {
                    "project_id": query.project_id,
                    "translation_key": query.translation_key,
                    "language_code": query.language_code,
                },
            )

        except Exception as e:
            error_msg = f"查询翻译条目失败: {str(e)}"
            self._logger.error(error_msg)

            end_time = datetime.utcnow()
            execution_time = int((end_time - start_time).total_seconds() * 1000)

            return await self._create_error_result(
                error_msg, "QUERY_ERROR", execution_time
            )

    def can_handle(self, query: BaseQuery) -> bool:
        return isinstance(query, GetTranslationQuery)

    async def _get_translation_entry(
        self,
        project_id: str,
        translation_key: TranslationKey,
        language_code: LanguageCode,
    ) -> TranslationEntry | None:
        """获取翻译条目（简化实现）"""
        # 这里应该从数据库查询实际的翻译条目
        return None

    async def _build_translation_detail(
        self, entry: TranslationEntry, include_metadata: bool
    ) -> dict[str, Any]:
        """构建翻译条目详情"""
        result = {
            "entry_id": entry.entry_id.value,
            "translation_key": entry.translation_key.value,
            "source_value": entry.source_value,
            "translated_value": entry.translated_value,
            "status": entry.status.value,
            "created_at": entry.created_at.isoformat(),
            "updated_at": entry.updated_at.isoformat() if entry.updated_at else None,
            "comment": entry.comment,
            "context": entry.context,
        }

        if include_metadata:
            result["metadata"] = {
                "placeholders": await self._extract_placeholders(entry.source_value),
                "character_count": len(entry.translated_value or ""),
                "has_formatting": await self._has_formatting_codes(entry.source_value),
            }

        return result

    async def _extract_placeholders(self, text: str) -> list[str]:
        """提取占位符（简化实现）"""
        import re

        placeholders = []

        # 提取常见占位符模式
        patterns = [
            r"%[sdfc]",
            r"%\d+\$[sdfc]",
            r"\{[0-9]+\}",
            r"\{[a-zA-Z_][a-zA-Z0-9_]*\}",
        ]

        for pattern in patterns:
            matches = re.findall(pattern, text)
            placeholders.extend(matches)

        return list(set(placeholders))

    async def _has_formatting_codes(self, text: str) -> bool:
        """检查是否包含格式化代码"""
        import re

        return bool(re.search(r"§[0-9a-fk-or]", text))


class GetTranslationsQueryHandler(
    BaseQueryHandler[GetTranslationsQuery, dict[str, Any]]
):
    """获取翻译条目列表查询处理器"""

    def __init__(self, translation_extractor_service: TranslationExtractorService):
        super().__init__()
        self._translation_extractor_service = translation_extractor_service

    async def handle(self, query: GetTranslationsQuery) -> QueryResult[dict[str, Any]]:
        """处理获取翻译条目列表查询"""
        start_time = datetime.utcnow()

        try:
            self._logger.info(f"开始查询翻译条目列表: {query.project_id}")

            # 验证查询
            validation_errors = await self._validate_query(query)
            if validation_errors:
                return await self._create_error_result(
                    f"查询验证失败: {'; '.join(validation_errors)}", "VALIDATION_ERROR"
                )

            # 执行查询
            translations, total_count = await self._get_translations_with_filters(query)

            # 构建结果
            translation_list = []
            for translation in translations:
                translation_data = await self._build_translation_summary(translation)
                translation_list.append(translation_data)

            result_data = {
                "translations": translation_list,
                "pagination": {
                    "page": query.pagination.page,
                    "page_size": query.pagination.page_size,
                    "total_count": total_count,
                    "total_pages": (total_count + query.pagination.page_size - 1)
                    // query.pagination.page_size,
                    "has_next": query.pagination.offset + len(translation_list)
                    < total_count,
                    "has_prev": query.pagination.page > 1,
                },
                "filters_applied": {
                    "status_filter": query.status_filter,
                    "mod_filter": query.mod_filter,
                    "category_filter": query.category_filter,
                    "search_text": query.filters.search_text,
                },
            }

            end_time = datetime.utcnow()
            execution_time = int((end_time - start_time).total_seconds() * 1000)

            self._logger.info(
                f"翻译条目列表查询完成: 返回 {len(translation_list)} 个条目"
            )

            return await self._create_success_result(
                result_data,
                execution_time,
                {"project_id": query.project_id, "language_code": query.language_code},
                total_count,
            )

        except Exception as e:
            error_msg = f"查询翻译条目列表失败: {str(e)}"
            self._logger.error(error_msg)

            end_time = datetime.utcnow()
            execution_time = int((end_time - start_time).total_seconds() * 1000)

            return await self._create_error_result(
                error_msg, "QUERY_ERROR", execution_time
            )

    def can_handle(self, query: BaseQuery) -> bool:
        return isinstance(query, GetTranslationsQuery)

    async def _get_translations_with_filters(
        self, query: GetTranslationsQuery
    ) -> tuple[list[TranslationEntry], int]:
        """根据过滤条件获取翻译条目（简化实现）"""
        # 这里应该从数据库查询，应用各种过滤条件
        return [], 0

    async def _build_translation_summary(
        self, entry: TranslationEntry
    ) -> dict[str, Any]:
        """构建翻译条目摘要"""
        return {
            "entry_id": entry.entry_id.value,
            "translation_key": entry.translation_key.value,
            "source_value": entry.source_value,
            "translated_value": entry.translated_value,
            "status": entry.status.value,
            "updated_at": entry.updated_at.isoformat() if entry.updated_at else None,
            "has_comment": bool(entry.comment),
        }


class GetTranslationProgressQueryHandler(
    BaseQueryHandler[GetTranslationProgressQuery, dict[str, Any]]
):
    """获取翻译进度查询处理器"""

    def __init__(self, translation_extractor_service: TranslationExtractorService):
        super().__init__()
        self._translation_extractor_service = translation_extractor_service

    async def handle(
        self, query: GetTranslationProgressQuery
    ) -> QueryResult[dict[str, Any]]:
        """处理获取翻译进度查询"""
        start_time = datetime.utcnow()

        try:
            self._logger.info(f"开始查询翻译进度: {query.project_id}")

            # 验证查询
            validation_errors = await self._validate_query(query)
            if validation_errors:
                return await self._create_error_result(
                    f"查询验证失败: {'; '.join(validation_errors)}", "VALIDATION_ERROR"
                )

            # 获取翻译进度统计
            progress_data = await self._calculate_translation_progress(query)

            end_time = datetime.utcnow()
            execution_time = int((end_time - start_time).total_seconds() * 1000)

            self._logger.info(f"翻译进度查询完成: {query.project_id}")

            return await self._create_success_result(
                progress_data,
                execution_time,
                {
                    "project_id": query.project_id,
                    "language_code": query.language_code,
                    "grouping_options": {
                        "group_by_mod": query.group_by_mod,
                        "group_by_category": query.group_by_category,
                    },
                },
            )

        except Exception as e:
            error_msg = f"查询翻译进度失败: {str(e)}"
            self._logger.error(error_msg)

            end_time = datetime.utcnow()
            execution_time = int((end_time - start_time).total_seconds() * 1000)

            return await self._create_error_result(
                error_msg, "QUERY_ERROR", execution_time
            )

    def can_handle(self, query: BaseQuery) -> bool:
        return isinstance(query, GetTranslationProgressQuery)

    async def _calculate_translation_progress(
        self, query: GetTranslationProgressQuery
    ) -> dict[str, Any]:
        """计算翻译进度（简化实现）"""
        progress_data = {
            "project_id": query.project_id,
            "generated_at": datetime.utcnow().isoformat(),
            "overall_progress": {
                "total_entries": 0,
                "translated_entries": 0,
                "untranslated_entries": 0,
                "progress_percentage": 0.0,
            },
        }

        if query.language_code:
            progress_data["language_code"] = query.language_code
            progress_data["language_progress"] = await self._get_language_progress(
                query.project_id, LanguageCode(query.language_code)
            )
        else:
            progress_data["by_language"] = await self._get_all_languages_progress(
                query.project_id
            )

        if query.group_by_mod:
            progress_data["by_mod"] = await self._get_progress_by_mod(
                query.project_id, query.language_code
            )

        if query.group_by_category:
            progress_data["by_category"] = await self._get_progress_by_category(
                query.project_id, query.language_code
            )

        if query.include_details:
            progress_data["details"] = await self._get_progress_details(
                query.project_id, query.language_code
            )

        return progress_data

    async def _get_language_progress(
        self, project_id: str, language_code: LanguageCode
    ) -> dict[str, Any]:
        """获取特定语言的翻译进度（简化实现）"""
        return {
            "total_entries": 0,
            "translated_entries": 0,
            "progress_percentage": 0.0,
            "last_updated": None,
        }

    async def _get_all_languages_progress(
        self, project_id: str
    ) -> dict[str, dict[str, Any]]:
        """获取所有语言的翻译进度（简化实现）"""
        return {}

    async def _get_progress_by_mod(
        self, project_id: str, language_code: str | None
    ) -> dict[str, dict[str, Any]]:
        """按模组获取翻译进度（简化实现）"""
        return {}

    async def _get_progress_by_category(
        self, project_id: str, language_code: str | None
    ) -> dict[str, dict[str, Any]]:
        """按分类获取翻译进度（简化实现）"""
        return {}

    async def _get_progress_details(
        self, project_id: str, language_code: str | None
    ) -> dict[str, Any]:
        """获取进度详细信息（简化实现）"""
        return {
            "recent_updates": [],
            "most_active_translators": [],
            "completion_estimate": None,
        }
