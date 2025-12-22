# packages/core/framework/logging/logging_config.py
"""
集中配置项目日志系统：structlog ⇄ 标准 logging，并与 Rich 深度集成。

提供两种输出：
- console：开发环境的面板式人类友好输出（本地时间，配色/对齐/长值折行）。
- json   ：生产环境的结构化日志（ISO-8601 且 UTC），便于日志平台聚合。

要点：
1) 使用 structlog 官方推荐的 ProcessorFormatter 桥接到标准 logging；
2) 自定义 HybridPanelRenderer 实现完美对齐、长值折行与首行空行；
3) console 用本地时间，json 统一 UTC；
4) 新增 setup_logging_from_config(cfg, service=...) 一步到位；
5) 可选屏蔽第三方噪声 logger（urllib3/sqlalchemy.engine 等）。
"""

from __future__ import annotations

import logging
from collections.abc import MutableMapping
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any, Literal, Protocol

import structlog
from structlog.typing import Processor

# ----------------------------
# 可选依赖：rich（软依赖处理）
# ----------------------------
if TYPE_CHECKING:
    from rich.console import Console, Group, RenderableType
    from rich.panel import Panel
    from rich.table import Table
    from rich.text import Text
else:
    try:
        from rich.console import Console, Group
        from rich.panel import Panel
        from rich.table import Table
        from rich.text import Text

        RenderableType = Any
    except ImportError:
        Console = Group = Panel = Table = Text = RenderableType = None


# ----------------------------
# 类型定义
# ----------------------------
class LogRenderer(Protocol):
    """日志渲染器协议。"""

    def __call__(
        self, logger: Any, name: str, event_dict: MutableMapping[str, Any]
    ) -> str:
        """渲染日志事件为字符串。"""
        ...


# 类型别名
LogLevel = Literal["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]
LogFormat = Literal["json", "console"]
LevelStyle = tuple[str, str]  # (border_style, level_text)
PanelPadding = tuple[int, int]  # (vertical, horizontal)


# 预定义的日志级别样式配置
DEFAULT_LEVEL_STYLES: dict[str, LevelStyle] = {
    "debug": ("cyan", "DEBUG   "),
    "info": ("green", "INFO    "),
    "warning": ("yellow", "WARNING "),
    "error": ("bold red", "ERROR   "),
    "critical": ("magenta", "CRITICAL"),
}

# 常见的噪声日志库列表
NOISY_LOGGERS = (
    "urllib3",
    "httpcore",
    "httpx",
    "asyncio",
    "sqlalchemy.engine.Engine",  # 细粒度：引擎 SQL 回显
)


@dataclass
class LogMetadata:
    """日志元数据容器。"""

    timestamp: str
    level: str
    logger_name: str
    extra_fields: MutableMapping[str, Any]


class HybridPanelRenderer:
    """
    structlog 处理器：将日志渲染为 Rich 面板。

    设计目标：
    - 标题等宽级别标签（保证对齐）
    - 值的长文本可折行显示（去引号改善折行）
    - 首次打印前插入换行，避免与上文粘连
    - 可配置是否显示时间戳与 logger 名称、键列宽度与截断长度
    """

    def __init__(
        self,
        *,
        log_level: LogLevel = "INFO",
        kv_truncate_at: int = 256,
        show_timestamp: bool = True,
        show_logger_name: bool = True,
        kv_key_width: int = 15,
        panel_padding: PanelPadding = (1, 2),
        level_styles: dict[str, LevelStyle] | None = None,
    ) -> None:
        self._validate_dependencies()

        self._console = Console()
        self._log_level = log_level
        self._kv_truncate_at = max(1, kv_truncate_at)  # 确保至少为1
        self._show_timestamp = show_timestamp
        self._show_logger_name = show_logger_name
        self._kv_key_width = max(1, kv_key_width)  # 确保至少为1
        self._panel_padding = panel_padding
        self._is_first_render = True

        # 使用自定义样式或默认样式
        self._level_styles = level_styles or DEFAULT_LEVEL_STYLES.copy()

    @staticmethod
    def _validate_dependencies() -> None:
        """验证Rich依赖是否可用。"""
        if Console is None:
            raise ImportError(
                "要使用 HybridPanelRenderer，请先安装 rich：\n"
                "  poetry add rich --group dev\n"
                "或：pip install rich"
            )

    def __call__(
        self, logger: Any, name: str, event_dict: MutableMapping[str, Any]
    ) -> str:
        """渲染日志事件为Rich面板格式的字符串。"""
        # 提取并验证核心字段
        event_msg = str(event_dict.pop("event", "")).strip()
        if not event_msg:
            return ""  # 无消息不输出

        # 提取日志元数据
        log_data = self._extract_log_metadata(event_dict)

        # 获取级别样式
        border_style, level_text = self._get_level_style(log_data.level)

        # 渲染面板
        rendered_output = self._render_as_panel(
            timestamp=log_data.timestamp,
            level_text=level_text,
            border_style=border_style,
            logger_name=log_data.logger_name,
            event=event_msg,
            kv=log_data.extra_fields,
        )

        # 首次渲染时添加前导换行
        return self._format_first_render(rendered_output)

    def _extract_log_metadata(
        self, event_dict: MutableMapping[str, Any]
    ) -> LogMetadata:
        """提取日志元数据。"""
        timestamp = event_dict.pop("timestamp", "")
        level = event_dict.pop("level", "info").lower()
        logger_name = event_dict.pop("logger", "unknown")

        # 清理 structlog 注入但我们不直接展示的内部字段
        event_dict.pop("_record", None)
        event_dict.pop("_logger", None)

        return LogMetadata(
            timestamp=timestamp,
            level=level,
            logger_name=logger_name,
            extra_fields=event_dict,
        )

    def _get_level_style(self, level: str) -> LevelStyle:
        """获取日志级别对应的样式。"""
        return self._level_styles.get(level, ("dim", level.upper()))

    def _format_first_render(self, rendered_output: str) -> str:
        """处理首次渲染的格式化。"""
        if self._is_first_render and rendered_output:
            self._is_first_render = False
            return f"\n{rendered_output}"
        return rendered_output

    def _render_as_panel(
        self,
        *,
        timestamp: str,
        level_text: str,
        border_style: str,
        logger_name: str,
        event: str,
        kv: MutableMapping[str, Any],
    ) -> str:
        """将日志数据渲染为Rich面板。"""
        # 构建面板标题
        title = self._build_panel_title(level_text, border_style, logger_name)

        # 构建面板内容
        renderables = self._build_panel_content(event, kv)

        # 构建面板副标题（时间戳）
        subtitle = self._build_panel_subtitle(timestamp)

        # 渲染面板并返回字符串
        return self._render_panel_to_string(renderables, title, border_style, subtitle)

    def _build_panel_title(
        self, level_text: str, border_style: str, logger_name: str
    ) -> Text:
        """构建面板标题。"""
        title_parts = [f"[{border_style}]{level_text}[/]"]
        if self._show_logger_name:
            title_parts.append(f"[cyan dim]({logger_name})[/]")
        return Text.from_markup(" ".join(title_parts))

    def _build_panel_content(
        self, event: str, kv: MutableMapping[str, Any]
    ) -> list[RenderableType]:
        """构建面板内容。"""
        renderables: list[RenderableType] = [Text(event, justify="left")]

        # 添加键值对表格（如果有额外字段）
        if kv:
            kv_table = self._create_kv_table(kv)
            renderables.append(kv_table)

        return renderables

    def _create_kv_table(self, kv: MutableMapping[str, Any]) -> Table:
        """创建键值对表格。"""
        kv_table = Table(show_header=False, show_edge=False, box=None, padding=(0, 1))
        kv_table.add_column(style="dim", justify="right", width=self._kv_key_width)
        kv_table.add_column(style="bright_white", overflow="fold")

        for key, value in sorted(kv.items()):
            formatted_value = self._format_kv_value(value)
            kv_table.add_row(f"{key} :", Text(formatted_value))

        return kv_table

    def _format_kv_value(self, value: Any) -> str:
        """格式化键值对的值，处理长文本和引号。"""
        try:
            value_repr = repr(value)
        except Exception:
            # 如果 repr() 失败，使用安全的回退方案
            try:
                value_repr = str(value)
            except Exception:
                value_repr = f"<{type(value).__name__} object>"

        # 对超长字符串或包含换行的字符串去引号以提升折行效果
        if len(value_repr) > self._kv_truncate_at or "\n" in value_repr:
            if (value_repr.startswith("'") and value_repr.endswith("'")) or (
                value_repr.startswith('"') and value_repr.endswith('"')
            ):
                value_repr = value_repr[1:-1]

        return value_repr

    def _build_panel_subtitle(self, timestamp: str) -> Text | None:
        """构建面板副标题（时间戳）。"""
        if self._show_timestamp and timestamp:
            return Text(str(timestamp), style="dim")
        return None

    def _render_panel_to_string(
        self,
        renderables: list[RenderableType],
        title: Text,
        border_style: str,
        subtitle: Text | None,
    ) -> str:
        """将面板渲染为字符串。"""
        render_group = Group(*renderables)

        with self._console.capture() as capture:
            self._console.print(
                Panel(
                    render_group,
                    title=title,
                    border_style=border_style,
                    subtitle=subtitle,
                    subtitle_align="right",
                    expand=False,
                    title_align="left",
                    padding=self._panel_padding,
                )
            )
        return capture.get().rstrip()


def setup_logging(
    *,
    log_level: LogLevel = "INFO",
    log_format: LogFormat = "console",
    show_timestamp: bool = True,
    show_logger_name: bool = True,
    kv_truncate_at: int = 256,
    kv_key_width: int = 15,
    root_level: LogLevel | None = None,
    service: str | None = None,
    silence_noisy_libs: bool = True,
    custom_level_styles: dict[str, LevelStyle] | None = None,
    panel_padding: PanelPadding = (1, 2),
) -> None:
    """
    配置全局 structlog 日志系统。

    Args:
        log_level: 应用 logger 的最低级别（DEBUG/INFO/WARNING/ERROR/CRITICAL）。
        log_format: 'console'（开发美观输出）或 'json'（生产结构化输出）。
        show_timestamp: console 面板右下角是否显示时间戳。
        show_logger_name: console 标题是否显示 logger 名称。
        kv_truncate_at: console 值字段的截断阈值。
        kv_key_width: console 键列固定宽度，用于对齐。
        root_level: 根 logger 级别；默认 None 表示使用 WARNING 以降低第三方噪声。
        service: 统一绑定到日志的服务名（通过 contextvars 注入）。
        silence_noisy_libs: 是否下调常见噪声 logger 的级别（默认 True）。
        custom_level_styles: 自定义级别样式配置。
        panel_padding: console 面板内边距。

    Raises:
        ImportError: 当使用 console 格式但 rich 未安装时。
        ValueError: 当配置参数无效时。
    """
    # 验证配置参数
    _validate_logging_config(
        level=log_level,
        format_type=log_format,
        kv_truncate_at=kv_truncate_at,
        kv_key_width=kv_key_width,
        panel_padding=panel_padding,
    )

    # 结构化处理链（官方推荐 ProcessorFormatter 桥接范式）
    pre_chain: list[Processor] = [
        structlog.contextvars.merge_contextvars,
        structlog.stdlib.add_logger_name,
        structlog.stdlib.add_log_level,
    ]

    # 默认本地时间；如为 JSON 模式会在下方覆盖为 ISO+UTC
    timestamper_local = structlog.processors.TimeStamper(
        fmt="%Y-%m-%d %H:%M:%S", utc=False
    )

    processors: list[Processor] = [
        *pre_chain,
        timestamper_local,
        structlog.stdlib.PositionalArgumentsFormatter(),
        structlog.processors.StackInfoRenderer(),
        structlog.processors.format_exc_info,
        structlog.stdlib.ProcessorFormatter.wrap_for_formatter,
    ]

    # JSON：ISO + UTC
    if log_format == "json":
        processors[3] = structlog.processors.TimeStamper(
            fmt="iso", utc=True
        )  # 覆盖为 ISO+UTC

    structlog.configure(
        processors=processors,
        logger_factory=structlog.stdlib.LoggerFactory(),
        wrapper_class=structlog.stdlib.BoundLogger,
        cache_logger_on_first_use=True,
    )

    # 最终渲染器
    if log_format == "console":
        final_renderer: Processor = HybridPanelRenderer(
            log_level=log_level,
            kv_truncate_at=kv_truncate_at,
            show_timestamp=show_timestamp,
            show_logger_name=show_logger_name,
            kv_key_width=kv_key_width,
            level_styles=custom_level_styles,
            panel_padding=panel_padding,
        )
    else:
        final_renderer = structlog.processors.JSONRenderer()

    formatter = structlog.stdlib.ProcessorFormatter(
        processor=final_renderer,
        foreign_pre_chain=[
            structlog.contextvars.merge_contextvars,
            structlog.stdlib.add_log_level,
            structlog.stdlib.add_logger_name,
        ],
    )

    handler = logging.StreamHandler()
    handler.setFormatter(formatter)

    # 根记录器：默认 WARNING 抑制第三方噪声；如需覆盖可传 root_level
    root_logger = logging.getLogger()
    if root_logger.hasHandlers():
        root_logger.handlers.clear()
    root_logger.addHandler(handler)
    root_logger.setLevel((root_level or "WARNING").upper())

    # 应用 logger：按入参设定
    app_logger = logging.getLogger("th_suite")
    app_logger.setLevel(log_level.upper())
    app_logger.propagate = True

    # 绑定全局上下文（service 等），所有日志都会带上
    structlog.contextvars.clear_contextvars()
    if service:
        structlog.contextvars.bind_contextvars(service=service)

    # 静音常见噪声（可选）
    if silence_noisy_libs:
        for noisy in NOISY_LOGGERS:
            logging.getLogger(noisy).setLevel(logging.WARNING)

    # 配置完成日志（使用 structlog）
    s_logger = structlog.get_logger("th_suite.logging_config")
    s_logger.info(
        "日志系统已配置完成。",
        log_format=log_format,
        app_log_level=log_level.upper(),
        root_log_level=(root_level or "WARNING").upper(),
        service=service,
    )


def _validate_logging_config(
    *,
    level: LogLevel,
    format_type: LogFormat,
    kv_truncate_at: int,
    kv_key_width: int,
    panel_padding: PanelPadding,
) -> None:
    """验证日志配置参数。

    Raises:
        ValueError: 当配置参数无效时。
        ImportError: 当使用 console 格式但 rich 未安装时。
    """
    # 验证日志级别
    valid_levels = {"DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"}
    if level.upper() not in valid_levels:
        raise ValueError(f"Invalid log level: {level}. Must be one of {valid_levels}")

    # 验证日志格式
    valid_formats = {"json", "console"}
    if format_type not in valid_formats:
        raise ValueError(
            f"Invalid format type: {format_type}. Must be one of {valid_formats}"
        )

    # 验证 rich 依赖
    if format_type == "console" and Console is None:
        raise ImportError(
            "要使用 'console' 日志格式，请先安装 rich：\n"
            "  poetry add rich --group dev\n"
            "或：pip install rich"
        )

    # 验证数值参数
    if len(panel_padding) != 2 or any(p < 0 for p in panel_padding):
        raise ValueError("panel_padding must be a tuple of two non-negative integers")

    if kv_key_width < 1:
        raise ValueError("kv_key_width must be at least 1")

    if kv_truncate_at < 1:
        raise ValueError("kv_truncate_at must be at least 1")
