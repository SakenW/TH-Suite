"""
CQRS查询基类和查询总线

实现查询模式的基础架构，用于处理读操作
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from typing import Any, TypeVar

from packages.core.framework.events import EventBus
from packages.core.framework.logging import get_logger

logger = get_logger(__name__)

# 泛型类型变量
TQuery = TypeVar("TQuery", bound="BaseQuery")
TResult = TypeVar("TResult")


class QueryStatus(Enum):
    """查询执行状态"""

    PENDING = "pending"
    EXECUTING = "executing"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


@dataclass
class QueryResult[TResult]:
    """查询执行结果"""

    success: bool
    result: TResult | None = None
    error_message: str | None = None
    error_code: str | None = None
    execution_time_ms: int | None = None
    metadata: dict[str, Any] = None
    total_count: int | None = None  # 用于分页查询

    def __post_init__(self):
        if self.metadata is None:
            self.metadata = {}


class BaseQuery(ABC):
    """查询基类"""

    def __init__(
        self, query_id: str = None, user_id: str = None, correlation_id: str = None
    ):
        self.query_id = query_id or self._generate_query_id()
        self.user_id = user_id
        self.correlation_id = correlation_id
        self.created_at = datetime.utcnow()
        self.status = QueryStatus.PENDING

    def _generate_query_id(self) -> str:
        """生成唯一的查询ID"""
        import uuid

        return f"qry_{uuid.uuid4().hex[:8]}"

    @abstractmethod
    def validate(self) -> list[str]:
        """验证查询参数，返回错误列表"""
        pass

    def get_query_type(self) -> str:
        """获取查询类型名称"""
        return self.__class__.__name__


class BaseQueryHandler[TQuery: "BaseQuery", TResult](ABC):
    """查询处理器基类"""

    def __init__(self):
        self._logger = get_logger(f"{__name__}.{self.__class__.__name__}")

    @abstractmethod
    async def handle(self, query: TQuery) -> QueryResult[TResult]:
        """处理查询"""
        pass

    @abstractmethod
    def can_handle(self, query: BaseQuery) -> bool:
        """检查是否能处理此查询"""
        pass

    async def _validate_query(self, query: TQuery) -> list[str]:
        """验证查询"""
        try:
            return query.validate()
        except Exception as e:
            return [f"查询验证失败: {str(e)}"]

    async def _create_success_result(
        self,
        result: TResult,
        execution_time_ms: int,
        metadata: dict[str, Any] = None,
        total_count: int | None = None,
    ) -> QueryResult[TResult]:
        """创建成功结果"""
        return QueryResult(
            success=True,
            result=result,
            execution_time_ms=execution_time_ms,
            metadata=metadata or {},
            total_count=total_count,
        )

    async def _create_error_result(
        self,
        error_message: str,
        error_code: str = None,
        execution_time_ms: int = None,
        metadata: dict[str, Any] = None,
    ) -> QueryResult[TResult]:
        """创建错误结果"""
        return QueryResult(
            success=False,
            error_message=error_message,
            error_code=error_code,
            execution_time_ms=execution_time_ms,
            metadata=metadata or {},
        )


@dataclass
class PaginationQuery:
    """分页查询参数"""

    page: int = 1
    page_size: int = 20
    max_page_size: int = 100

    def __post_init__(self):
        # 验证分页参数
        if self.page < 1:
            self.page = 1
        if self.page_size < 1:
            self.page_size = 20
        if self.page_size > self.max_page_size:
            self.page_size = self.max_page_size

    @property
    def offset(self) -> int:
        """计算偏移量"""
        return (self.page - 1) * self.page_size

    @property
    def limit(self) -> int:
        """获取限制数量"""
        return self.page_size


@dataclass
class SortingQuery:
    """排序查询参数"""

    sort_field: str | None = None
    sort_direction: str = "asc"  # "asc" | "desc"
    secondary_sort_field: str | None = None
    secondary_sort_direction: str = "asc"

    def __post_init__(self):
        if self.sort_direction not in ["asc", "desc"]:
            self.sort_direction = "asc"
        if self.secondary_sort_direction not in ["asc", "desc"]:
            self.secondary_sort_direction = "asc"


@dataclass
class FilterQuery:
    """过滤查询参数"""

    filters: dict[str, Any] = None
    search_text: str | None = None
    date_range_start: datetime | None = None
    date_range_end: datetime | None = None

    def __post_init__(self):
        if self.filters is None:
            self.filters = {}


class QueryBus:
    """查询总线"""

    def __init__(self, event_bus: EventBus | None = None):
        self._handlers: dict[type[BaseQuery], BaseQueryHandler] = {}
        self._middleware: list[QueryMiddleware] = []
        self._event_bus = event_bus
        self._logger = get_logger(__name__ + ".QueryBus")

    def register_handler(
        self, query_type: type[TQuery], handler: BaseQueryHandler[TQuery, Any]
    ):
        """注册查询处理器"""
        if query_type in self._handlers:
            old_handler = self._handlers[query_type]
            self._logger.warning(
                f"查询处理器被覆盖: {query_type.__name__} "
                f"{old_handler.__class__.__name__} -> {handler.__class__.__name__}"
            )

        self._handlers[query_type] = handler
        self._logger.info(
            f"注册查询处理器: {query_type.__name__} -> {handler.__class__.__name__}"
        )

    def add_middleware(self, middleware: "QueryMiddleware"):
        """添加中间件"""
        self._middleware.append(middleware)
        self._logger.info(f"添加查询中间件: {middleware.__class__.__name__}")

    async def execute(self, query: BaseQuery) -> QueryResult:
        """执行查询"""
        start_time = datetime.utcnow()
        query.status = QueryStatus.EXECUTING

        try:
            self._logger.info(
                f"开始执行查询: {query.get_query_type()} (ID: {query.query_id})"
            )

            # 查找处理器
            handler = self._find_handler(query)
            if not handler:
                error_msg = f"未找到查询处理器: {query.get_query_type()}"
                self._logger.error(error_msg)
                query.status = QueryStatus.FAILED
                return QueryResult(
                    success=False,
                    error_message=error_msg,
                    error_code="HANDLER_NOT_FOUND",
                )

            # 执行中间件（前置处理）
            for middleware in self._middleware:
                try:
                    await middleware.before_execute(query)
                except Exception as e:
                    error_msg = f"中间件前置处理失败: {str(e)}"
                    self._logger.error(error_msg)
                    query.status = QueryStatus.FAILED
                    return QueryResult(
                        success=False,
                        error_message=error_msg,
                        error_code="MIDDLEWARE_ERROR",
                    )

            # 执行查询
            result = await handler.handle(query)

            # 更新状态
            if result.success:
                query.status = QueryStatus.COMPLETED
            else:
                query.status = QueryStatus.FAILED

            # 计算执行时间
            end_time = datetime.utcnow()
            execution_time_ms = int((end_time - start_time).total_seconds() * 1000)
            if result.execution_time_ms is None:
                result.execution_time_ms = execution_time_ms

            # 执行中间件（后置处理）
            for middleware in reversed(self._middleware):
                try:
                    await middleware.after_execute(query, result)
                except Exception as e:
                    self._logger.warning(f"中间件后置处理失败: {str(e)}")

            # 发布事件（只在成功时）
            if self._event_bus and result.success:
                await self._publish_query_completed_event(query, result)

            self._logger.info(
                f"查询执行完成: {query.get_query_type()} "
                f"(ID: {query.query_id}, 耗时: {execution_time_ms}ms, 成功: {result.success})"
            )

            return result

        except Exception as e:
            error_msg = f"查询执行异常: {str(e)}"
            self._logger.error(f"查询执行异常 {query.get_query_type()}: {error_msg}")
            query.status = QueryStatus.FAILED

            end_time = datetime.utcnow()
            execution_time_ms = int((end_time - start_time).total_seconds() * 1000)

            return QueryResult(
                success=False,
                error_message=error_msg,
                error_code="EXECUTION_ERROR",
                execution_time_ms=execution_time_ms,
            )

    def _find_handler(self, query: BaseQuery) -> BaseQueryHandler | None:
        """查找查询处理器"""
        query_type = type(query)

        # 精确匹配
        if query_type in self._handlers:
            return self._handlers[query_type]

        # 检查基类匹配
        for registered_type, handler in self._handlers.items():
            if isinstance(query, registered_type):
                return handler

        # 检查处理器的can_handle方法
        for handler in self._handlers.values():
            if handler.can_handle(query):
                return handler

        return None

    async def _publish_query_completed_event(
        self, query: BaseQuery, result: QueryResult
    ):
        """发布查询完成事件"""
        try:
            from packages.core.framework.events import DomainEvent

            class QueryCompletedEvent(DomainEvent):
                def __init__(
                    self,
                    query_id: str,
                    query_type: str,
                    success: bool,
                    result_count: int | None = None,
                ):
                    super().__init__()
                    self.query_id = query_id
                    self.query_type = query_type
                    self.success = success
                    self.result_count = result_count

            event = QueryCompletedEvent(
                query_id=query.query_id,
                query_type=query.get_query_type(),
                success=result.success,
                result_count=result.total_count,
            )

            await self._event_bus.publish(event)

        except Exception as e:
            self._logger.warning(f"发布查询完成事件失败: {str(e)}")

    def get_registered_handlers(self) -> dict[type[BaseQuery], BaseQueryHandler]:
        """获取已注册的处理器"""
        return self._handlers.copy()


class QueryMiddleware(ABC):
    """查询中间件基类"""

    @abstractmethod
    async def before_execute(self, query: BaseQuery):
        """查询执行前处理"""
        pass

    @abstractmethod
    async def after_execute(self, query: BaseQuery, result: QueryResult):
        """查询执行后处理"""
        pass


class LoggingQueryMiddleware(QueryMiddleware):
    """查询日志中间件"""

    def __init__(self):
        self._logger = get_logger(__name__ + ".LoggingQueryMiddleware")

    async def before_execute(self, query: BaseQuery):
        """记录查询开始执行"""
        self._logger.debug(
            f"查询开始执行: {query.get_query_type()} "
            f"(ID: {query.query_id}, 用户: {query.user_id})"
        )

    async def after_execute(self, query: BaseQuery, result: QueryResult):
        """记录查询执行结果"""
        level = "info" if result.success else "error"
        message = (
            f"查询执行结束: {query.get_query_type()} "
            f"(ID: {query.query_id}, 成功: {result.success}"
        )

        if result.execution_time_ms:
            message += f", 耗时: {result.execution_time_ms}ms"

        if result.total_count is not None:
            message += f", 结果数: {result.total_count}"

        if not result.success and result.error_message:
            message += f", 错误: {result.error_message}"

        message += ")"

        if level == "info":
            self._logger.info(message)
        else:
            self._logger.error(message)


class ValidationQueryMiddleware(QueryMiddleware):
    """查询验证中间件"""

    def __init__(self):
        self._logger = get_logger(__name__ + ".ValidationQueryMiddleware")

    async def before_execute(self, query: BaseQuery):
        """执行查询验证"""
        try:
            validation_errors = query.validate()
            if validation_errors:
                error_message = f"查询验证失败: {'; '.join(validation_errors)}"
                self._logger.error(
                    f"{query.get_query_type()} 验证失败: {validation_errors}"
                )
                raise ValueError(error_message)
        except Exception as e:
            if not isinstance(e, ValueError):
                error_message = f"查询验证异常: {str(e)}"
                self._logger.error(error_message)
                raise ValueError(error_message)
            raise

    async def after_execute(self, query: BaseQuery, result: QueryResult):
        """验证执行后无需处理"""
        pass


class CachingQueryMiddleware(QueryMiddleware):
    """查询缓存中间件"""

    def __init__(self, cache_ttl_seconds: int = 300):
        self._cache: dict[str, Any] = {}
        self._cache_timestamps: dict[str, datetime] = {}
        self._cache_ttl_seconds = cache_ttl_seconds
        self._logger = get_logger(__name__ + ".CachingQueryMiddleware")

    async def before_execute(self, query: BaseQuery):
        """检查缓存"""
        cache_key = self._generate_cache_key(query)

        if cache_key in self._cache:
            cache_time = self._cache_timestamps.get(cache_key)
            if (
                cache_time
                and (datetime.utcnow() - cache_time).total_seconds()
                < self._cache_ttl_seconds
            ):
                # 缓存命中且未过期
                cached_result = self._cache[cache_key]
                self._logger.debug(f"查询缓存命中: {query.get_query_type()}")
                # 这里可以直接返回缓存结果，但需要修改架构来支持
                return cached_result

        # 缓存未命中或已过期，清理过期缓存
        self._cleanup_expired_cache()

    async def after_execute(self, query: BaseQuery, result: QueryResult):
        """缓存查询结果"""
        if result.success:
            cache_key = self._generate_cache_key(query)
            self._cache[cache_key] = result
            self._cache_timestamps[cache_key] = datetime.utcnow()
            self._logger.debug(f"查询结果已缓存: {query.get_query_type()}")

    def _generate_cache_key(self, query: BaseQuery) -> str:
        """生成缓存键"""
        # 简化的缓存键生成，实际应该根据查询参数生成更精确的键
        import hashlib

        query_str = f"{query.get_query_type()}_{query.user_id}_{str(vars(query))}"
        return hashlib.md5(query_str.encode()).hexdigest()

    def _cleanup_expired_cache(self):
        """清理过期缓存"""
        current_time = datetime.utcnow()
        expired_keys = []

        for key, timestamp in self._cache_timestamps.items():
            if (current_time - timestamp).total_seconds() >= self._cache_ttl_seconds:
                expired_keys.append(key)

        for key in expired_keys:
            self._cache.pop(key, None)
            self._cache_timestamps.pop(key, None)

        if expired_keys:
            self._logger.debug(f"清理了 {len(expired_keys)} 个过期缓存条目")


# 全局查询总线实例
query_bus = QueryBus()
