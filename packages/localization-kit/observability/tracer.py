"""
链路追踪器 - 全链路追踪实现

根据白皮书要求，实现从扫描到回写的全链路追踪
"""

import uuid
import time
import logging
from typing import Dict, List, Optional, Any, Callable
from dataclasses import dataclass, field
from datetime import datetime
from contextlib import contextmanager
from enum import Enum

logger = logging.getLogger(__name__)


class SpanStatus(Enum):
    """Span 状态"""
    RUNNING = "running"
    SUCCESS = "success"
    FAILED = "failed"
    CANCELLED = "cancelled"


@dataclass
class Span:
    """追踪 Span"""
    span_id: str
    trace_id: str
    parent_span_id: Optional[str]
    operation_name: str
    start_time: float
    end_time: Optional[float] = None
    status: SpanStatus = SpanStatus.RUNNING
    tags: Dict[str, Any] = field(default_factory=dict)
    logs: List[Dict[str, Any]] = field(default_factory=list)
    
    @property
    def duration_ms(self) -> float:
        """持续时间（毫秒）"""
        if self.end_time:
            return (self.end_time - self.start_time) * 1000
        return (time.time() - self.start_time) * 1000
    
    def set_tag(self, key: str, value: Any) -> None:
        """设置标签"""
        self.tags[key] = value
    
    def log(self, message: str, **kwargs) -> None:
        """添加日志"""
        log_entry = {
            'timestamp': time.time(),
            'message': message,
            **kwargs
        }
        self.logs.append(log_entry)
    
    def finish(self, status: SpanStatus = SpanStatus.SUCCESS) -> None:
        """结束 Span"""
        self.end_time = time.time()
        self.status = status
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            'span_id': self.span_id,
            'trace_id': self.trace_id,
            'parent_span_id': self.parent_span_id,
            'operation_name': self.operation_name,
            'start_time': self.start_time,
            'end_time': self.end_time,
            'duration_ms': self.duration_ms,
            'status': self.status.value,
            'tags': self.tags,
            'logs': self.logs
        }


@dataclass
class Trace:
    """追踪记录"""
    trace_id: str
    root_span_id: str
    start_time: float
    end_time: Optional[float] = None
    spans: Dict[str, Span] = field(default_factory=dict)
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def add_span(self, span: Span) -> None:
        """添加 Span"""
        self.spans[span.span_id] = span
    
    def get_span(self, span_id: str) -> Optional[Span]:
        """获取 Span"""
        return self.spans.get(span_id)
    
    def finish(self) -> None:
        """结束追踪"""
        self.end_time = time.time()
    
    @property
    def duration_ms(self) -> float:
        """总持续时间（毫秒）"""
        if self.end_time:
            return (self.end_time - self.start_time) * 1000
        return (time.time() - self.start_time) * 1000
    
    @property
    def span_count(self) -> int:
        """Span 数量"""
        return len(self.spans)
    
    @property
    def failed_spans(self) -> List[Span]:
        """失败的 Spans"""
        return [s for s in self.spans.values() if s.status == SpanStatus.FAILED]
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            'trace_id': self.trace_id,
            'root_span_id': self.root_span_id,
            'start_time': self.start_time,
            'end_time': self.end_time,
            'duration_ms': self.duration_ms,
            'span_count': self.span_count,
            'spans': [span.to_dict() for span in self.spans.values()],
            'metadata': self.metadata
        }


class Tracer:
    """
    链路追踪器
    
    提供分布式追踪能力，跟踪操作的执行流程
    """
    
    def __init__(self):
        """初始化追踪器"""
        self.traces: Dict[str, Trace] = {}
        self.active_spans: Dict[str, Span] = {}
        self._current_trace_id: Optional[str] = None
        self._current_span_id: Optional[str] = None
        
        # 回调
        self.on_span_start: Optional[Callable[[Span], None]] = None
        self.on_span_finish: Optional[Callable[[Span], None]] = None
        self.on_trace_finish: Optional[Callable[[Trace], None]] = None
    
    def start_trace(
        self,
        operation_name: str,
        trace_id: Optional[str] = None,
        **tags
    ) -> Trace:
        """
        开始新的追踪
        
        Args:
            operation_name: 操作名称
            trace_id: 追踪 ID（可选）
            **tags: 标签
            
        Returns:
            Trace 对象
        """
        if not trace_id:
            trace_id = f"trace_{uuid.uuid4().hex[:16]}"
        
        # 创建根 Span
        root_span = self.start_span(
            operation_name=operation_name,
            trace_id=trace_id,
            **tags
        )
        
        # 创建 Trace
        trace = Trace(
            trace_id=trace_id,
            root_span_id=root_span.span_id,
            start_time=time.time()
        )
        
        trace.add_span(root_span)
        self.traces[trace_id] = trace
        self._current_trace_id = trace_id
        
        logger.info(f"开始追踪: {trace_id} - {operation_name}")
        return trace
    
    def start_span(
        self,
        operation_name: str,
        trace_id: Optional[str] = None,
        parent_span_id: Optional[str] = None,
        **tags
    ) -> Span:
        """
        开始新的 Span
        
        Args:
            operation_name: 操作名称
            trace_id: 追踪 ID
            parent_span_id: 父 Span ID
            **tags: 标签
            
        Returns:
            Span 对象
        """
        # 使用当前追踪 ID
        if not trace_id:
            trace_id = self._current_trace_id
        
        if not trace_id:
            raise ValueError("没有活动的追踪")
        
        # 使用当前 Span 作为父级
        if not parent_span_id and self._current_span_id:
            parent_span_id = self._current_span_id
        
        # 创建 Span
        span_id = f"span_{uuid.uuid4().hex[:16]}"
        span = Span(
            span_id=span_id,
            trace_id=trace_id,
            parent_span_id=parent_span_id,
            operation_name=operation_name,
            start_time=time.time(),
            tags=tags
        )
        
        # 添加到追踪
        if trace_id in self.traces:
            self.traces[trace_id].add_span(span)
        
        self.active_spans[span_id] = span
        self._current_span_id = span_id
        
        # 回调
        if self.on_span_start:
            self.on_span_start(span)
        
        logger.debug(f"开始 Span: {span_id} - {operation_name}")
        return span
    
    def finish_span(
        self,
        span_id: Optional[str] = None,
        status: SpanStatus = SpanStatus.SUCCESS
    ) -> None:
        """
        结束 Span
        
        Args:
            span_id: Span ID（默认为当前 Span）
            status: 状态
        """
        if not span_id:
            span_id = self._current_span_id
        
        if not span_id or span_id not in self.active_spans:
            return
        
        span = self.active_spans[span_id]
        span.finish(status)
        
        # 更新当前 Span
        if span_id == self._current_span_id:
            self._current_span_id = span.parent_span_id
        
        del self.active_spans[span_id]
        
        # 回调
        if self.on_span_finish:
            self.on_span_finish(span)
        
        logger.debug(
            f"结束 Span: {span_id} - {span.operation_name} "
            f"({span.duration_ms:.2f}ms, {status.value})"
        )
    
    def finish_trace(self, trace_id: Optional[str] = None) -> None:
        """
        结束追踪
        
        Args:
            trace_id: 追踪 ID（默认为当前追踪）
        """
        if not trace_id:
            trace_id = self._current_trace_id
        
        if not trace_id or trace_id not in self.traces:
            return
        
        trace = self.traces[trace_id]
        
        # 结束所有活动 Span
        for span_id in list(self.active_spans.keys()):
            if self.active_spans[span_id].trace_id == trace_id:
                self.finish_span(span_id, SpanStatus.CANCELLED)
        
        trace.finish()
        
        # 清理当前追踪
        if trace_id == self._current_trace_id:
            self._current_trace_id = None
            self._current_span_id = None
        
        # 回调
        if self.on_trace_finish:
            self.on_trace_finish(trace)
        
        logger.info(
            f"结束追踪: {trace_id} "
            f"({trace.duration_ms:.2f}ms, {trace.span_count} spans)"
        )
    
    @contextmanager
    def trace(self, operation_name: str, **tags):
        """
        追踪上下文管理器
        
        使用示例：
            with tracer.trace("scan_directory", path="/mods"):
                # 执行操作
                pass
        """
        trace = self.start_trace(operation_name, **tags)
        try:
            yield trace
            self.finish_trace(trace.trace_id)
        except Exception as e:
            # 标记失败
            if trace.root_span_id in self.active_spans:
                self.finish_span(trace.root_span_id, SpanStatus.FAILED)
            self.finish_trace(trace.trace_id)
            raise
    
    @contextmanager
    def span(self, operation_name: str, **tags):
        """
        Span 上下文管理器
        
        使用示例：
            with tracer.span("parse_jar", file="mod.jar"):
                # 执行操作
                pass
        """
        span = self.start_span(operation_name, **tags)
        try:
            yield span
            self.finish_span(span.span_id, SpanStatus.SUCCESS)
        except Exception as e:
            span.log(f"错误: {str(e)}", level="error")
            self.finish_span(span.span_id, SpanStatus.FAILED)
            raise
    
    def get_trace(self, trace_id: str) -> Optional[Trace]:
        """获取追踪记录"""
        return self.traces.get(trace_id)
    
    def get_current_trace(self) -> Optional[Trace]:
        """获取当前追踪"""
        if self._current_trace_id:
            return self.traces.get(self._current_trace_id)
        return None
    
    def get_current_span(self) -> Optional[Span]:
        """获取当前 Span"""
        if self._current_span_id:
            return self.active_spans.get(self._current_span_id)
        return None
    
    def log(self, message: str, **kwargs) -> None:
        """记录日志到当前 Span"""
        span = self.get_current_span()
        if span:
            span.log(message, **kwargs)
    
    def set_tag(self, key: str, value: Any) -> None:
        """设置标签到当前 Span"""
        span = self.get_current_span()
        if span:
            span.set_tag(key, value)
    
    def clear(self) -> None:
        """清理所有追踪记录"""
        self.traces.clear()
        self.active_spans.clear()
        self._current_trace_id = None
        self._current_span_id = None


# 全局追踪器实例
_global_tracer = Tracer()


def get_tracer() -> Tracer:
    """获取全局追踪器"""
    return _global_tracer