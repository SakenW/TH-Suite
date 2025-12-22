"""
查询模式实现

CQRS中的查询（Query）用于处理读操作
查询的特征：
- 不修改状态
- 返回数据
- 可以被缓存
- 支持分页和过滤
"""

import uuid
from abc import ABC, abstractmethod
from datetime import datetime
from typing import Any, TypeVar

from ..dto.base_dto import BaseDTO

T = TypeVar("T")
R = TypeVar("R")


class Query(BaseDTO):
    """查询基类"""

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.query_id = kwargs.get("query_id", str(uuid.uuid4()))
        self.timestamp = kwargs.get("timestamp", datetime.now())
        self.user_id = kwargs.get("user_id")
        self.correlation_id = kwargs.get("correlation_id")

    def validate(self) -> list[str]:
        """验证查询"""
        errors = []

        # 基础验证
        if not self.query_id:
            errors.append("查询ID不能为空")

        # 子类可以重写添加特定验证
        return errors


class PagedQuery(Query):
    """分页查询基类"""

    def __init__(self, page: int = 1, page_size: int = 20, **kwargs):
        super().__init__(**kwargs)
        self.page = max(1, page)
        self.page_size = max(1, min(100, page_size))  # 限制最大页面大小

    @property
    def offset(self) -> int:
        """计算偏移量"""
        return (self.page - 1) * self.page_size

    def validate(self) -> list[str]:
        """验证分页参数"""
        errors = super().validate()

        if self.page < 1:
            errors.append("页码必须大于0")
        if self.page_size < 1 or self.page_size > 100:
            errors.append("页面大小必须在1-100之间")

        return errors


class SearchQuery(PagedQuery):
    """搜索查询基类"""

    def __init__(
        self,
        search_term: str = "",
        filters: dict[str, Any] = None,
        sort_by: str = "",
        sort_desc: bool = False,
        **kwargs,
    ):
        super().__init__(**kwargs)
        self.search_term = search_term.strip()
        self.filters = filters or {}
        self.sort_by = sort_by
        self.sort_desc = sort_desc


class PagedResult(BaseDTO):
    """分页结果"""

    def __init__(self, items: list[Any], total_count: int, page: int, page_size: int):
        super().__init__()
        self.items = items
        self.total_count = total_count
        self.page = page
        self.page_size = page_size

    @property
    def total_pages(self) -> int:
        """计算总页数"""
        if self.page_size == 0:
            return 0
        return (self.total_count + self.page_size - 1) // self.page_size

    @property
    def has_next_page(self) -> bool:
        """是否有下一页"""
        return self.page < self.total_pages

    @property
    def has_prev_page(self) -> bool:
        """是否有上一页"""
        return self.page > 1


class IQueryHandler[T, R](ABC):
    """查询处理器接口"""

    @abstractmethod
    async def handle(self, query: T) -> R:
        """处理查询"""
        pass

    def can_handle(self, query: Query) -> bool:
        """检查是否能处理此查询"""
        return True


class BaseQueryHandler(IQueryHandler[T, R]):
    """查询处理器基类"""

    def __init__(self, logger=None, cache_manager=None):
        self.logger = logger
        self.cache_manager = cache_manager

    async def handle(self, query: T) -> R:
        """处理查询"""
        # 验证查询
        errors = query.validate()
        if errors:
            raise ValueError(f"查询验证失败: {', '.join(errors)}")

        if self.logger:
            self.logger.info(
                f"处理查询: {query.__class__.__name__}", query_id=query.query_id
            )

        try:
            # 尝试从缓存获取
            if self.cache_manager:
                cache_key = self._generate_cache_key(query)
                cached_result = self.cache_manager.get(cache_key)
                if cached_result is not None:
                    if self.logger:
                        self.logger.info(
                            f"查询缓存命中: {query.__class__.__name__}",
                            query_id=query.query_id,
                        )
                    return cached_result

            # 执行查询
            result = await self.execute(query)

            # 缓存结果
            if self.cache_manager:
                cache_ttl = self.get_cache_ttl(query)
                if cache_ttl > 0:
                    self.cache_manager.set(cache_key, result, ttl=cache_ttl)

            if self.logger:
                self.logger.info(
                    f"查询处理完成: {query.__class__.__name__}", query_id=query.query_id
                )

            return result

        except Exception as e:
            if self.logger:
                self.logger.error(
                    f"查询处理失败: {query.__class__.__name__}",
                    exception=e,
                    query_id=query.query_id,
                )
            raise

    @abstractmethod
    async def execute(self, query: T) -> R:
        """执行查询的业务逻辑"""
        pass

    def _generate_cache_key(self, query: T) -> str:
        """生成缓存键"""
        if hasattr(self.cache_manager, "generate_key"):
            return self.cache_manager.generate_key(
                query.__class__.__name__, query.to_dict()
            )
        return f"{query.__class__.__name__}:{query.query_id}"

    def get_cache_ttl(self, query: T) -> int:
        """获取缓存TTL（秒）"""
        # 默认缓存5分钟，子类可以重写
        return 300


class QueryBus:
    """查询总线"""

    def __init__(self):
        self._handlers: dict[type, IQueryHandler] = {}
        self._middleware: list[callable] = []

    def register_handler(self, query_type: type, handler: IQueryHandler) -> None:
        """注册查询处理器"""
        self._handlers[query_type] = handler

    def add_middleware(self, middleware: callable) -> None:
        """添加中间件"""
        self._middleware.append(middleware)

    async def send(self, query: Query) -> Any:
        """发送查询"""
        query_type = type(query)

        if query_type not in self._handlers:
            raise ValueError(f"未找到查询类型 {query_type} 的处理器")

        handler = self._handlers[query_type]

        if not handler.can_handle(query):
            raise ValueError(f"处理器无法处理查询: {query_type}")

        # 应用中间件
        result = await self._apply_middleware(query, handler)

        return result

    async def _apply_middleware(self, query: Query, handler: IQueryHandler) -> Any:
        """应用中间件"""
        if not self._middleware:
            return await handler.handle(query)

        # 构建中间件链
        async def pipeline(q: Query) -> Any:
            return await handler.handle(q)

        # 倒序应用中间件
        for middleware in reversed(self._middleware):
            pipeline = self._wrap_with_middleware(middleware, pipeline)

        return await pipeline(query)

    def _wrap_with_middleware(
        self, middleware: callable, next_handler: callable
    ) -> callable:
        """包装中间件"""

        async def wrapper(query: Query) -> Any:
            return await middleware(query, next_handler)

        return wrapper


# 预定义的查询中间件


class QueryLoggingMiddleware:
    """查询日志中间件"""

    def __init__(self, logger):
        self.logger = logger

    async def __call__(self, query: Query, next_handler: callable) -> Any:
        """执行中间件"""
        start_time = datetime.now()

        self.logger.info(
            f"开始处理查询: {query.__class__.__name__}", query_id=query.query_id
        )

        try:
            result = await next_handler(query)

            duration = (datetime.now() - start_time).total_seconds()
            self.logger.info(
                f"查询处理成功: {query.__class__.__name__}",
                query_id=query.query_id,
                duration=duration,
            )

            return result

        except Exception as e:
            duration = (datetime.now() - start_time).total_seconds()
            self.logger.error(
                f"查询处理失败: {query.__class__.__name__}",
                exception=e,
                query_id=query.query_id,
                duration=duration,
            )
            raise


class QueryValidationMiddleware:
    """查询验证中间件"""

    async def __call__(self, query: Query, next_handler: callable) -> Any:
        """执行验证"""
        errors = query.validate()
        if errors:
            raise ValueError(f"查询验证失败: {', '.join(errors)}")

        return await next_handler(query)


class QueryCacheMiddleware:
    """查询缓存中间件"""

    def __init__(self, cache_manager, default_ttl: int = 300):
        self.cache_manager = cache_manager
        self.default_ttl = default_ttl

    async def __call__(self, query: Query, next_handler: callable) -> Any:
        """缓存处理"""
        cache_key = self._generate_cache_key(query)

        # 尝试从缓存获取
        cached_result = self.cache_manager.get(cache_key)
        if cached_result is not None:
            return cached_result

        # 执行查询
        result = await next_handler(query)

        # 缓存结果
        ttl = getattr(query, "cache_ttl", self.default_ttl)
        if ttl > 0:
            self.cache_manager.set(cache_key, result, ttl=ttl)

        return result

    def _generate_cache_key(self, query: Query) -> str:
        """生成缓存键"""
        if hasattr(self.cache_manager, "generate_key"):
            return self.cache_manager.generate_key(
                query.__class__.__name__, query.to_dict()
            )
        return f"{query.__class__.__name__}:{query.query_id}"


# 示例查询实现


class GetEntityByIdQuery(Query):
    """根据ID获取实体查询"""

    def __init__(self, entity_id: str, **kwargs):
        super().__init__(**kwargs)
        self.entity_id = entity_id

    def validate(self) -> list[str]:
        """验证查询"""
        errors = super().validate()

        if not self.entity_id:
            errors.append("实体ID不能为空")

        return errors


class ListEntitiesQuery(PagedQuery):
    """列表查询"""

    def __init__(self, entity_type: str = "", **kwargs):
        super().__init__(**kwargs)
        self.entity_type = entity_type


class SearchEntitiesQuery(SearchQuery):
    """搜索实体查询"""

    def __init__(self, entity_type: str = "", **kwargs):
        super().__init__(**kwargs)
        self.entity_type = entity_type
