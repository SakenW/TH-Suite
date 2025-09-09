"""
指标收集器 - 监控系统性能和业务指标

根据白皮书要求，监控去重率、翻译覆盖率、冲突率、回滚率、P95时延等关键指标
"""

import logging
import time
from collections import deque
from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any

logger = logging.getLogger(__name__)


class MetricType(Enum):
    """指标类型"""

    COUNTER = "counter"  # 计数器（只增不减）
    GAUGE = "gauge"  # 仪表（可增可减）
    HISTOGRAM = "histogram"  # 直方图（分布）
    RATE = "rate"  # 速率（按时间窗口）


@dataclass
class MetricValue:
    """指标值"""

    value: float
    timestamp: float
    labels: dict[str, str] = field(default_factory=dict)

    def age_seconds(self) -> float:
        """值的年龄（秒）"""
        return time.time() - self.timestamp


@dataclass
class Metric:
    """指标定义"""

    name: str
    type: MetricType
    description: str
    unit: str = ""
    values: deque = field(default_factory=lambda: deque(maxlen=1000))

    def record(self, value: float, labels: dict[str, str] | None = None) -> None:
        """记录值"""
        self.values.append(
            MetricValue(value=value, timestamp=time.time(), labels=labels or {})
        )

    def get_current(self) -> float | None:
        """获取当前值"""
        if self.values:
            return self.values[-1].value
        return None

    def get_percentile(self, percentile: float) -> float | None:
        """获取百分位数（仅用于 HISTOGRAM）"""
        if self.type != MetricType.HISTOGRAM or not self.values:
            return None

        sorted_values = sorted([v.value for v in self.values])
        index = int(len(sorted_values) * percentile / 100)
        return sorted_values[min(index, len(sorted_values) - 1)]

    def get_rate(self, window_seconds: int = 60) -> float:
        """获取速率（每秒）"""
        if not self.values:
            return 0.0

        cutoff_time = time.time() - window_seconds
        recent_values = [v for v in self.values if v.timestamp > cutoff_time]

        if len(recent_values) < 2:
            return 0.0

        time_span = recent_values[-1].timestamp - recent_values[0].timestamp
        if time_span == 0:
            return 0.0

        value_change = recent_values[-1].value - recent_values[0].value
        return value_change / time_span


class MetricsCollector:
    """
    指标收集器

    根据白皮书要求，收集以下关键指标：
    - 去重率：Blob 去重效果
    - 翻译覆盖率：已翻译条目比例
    - 冲突率：补丁冲突比例
    - 回滚率：需要回滚的操作比例
    - P95 时延：操作耗时的 95 百分位
    """

    def __init__(self):
        """初始化指标收集器"""
        self.metrics: dict[str, Metric] = {}
        self._timers: dict[str, float] = {}

        # 注册核心指标
        self._register_core_metrics()

        # 回调
        self.on_threshold_exceeded: Callable[[str, float], None] | None = None

    def _register_core_metrics(self) -> None:
        """注册核心指标"""
        # 扫描指标
        self.register_metric(
            "scan_duration", MetricType.HISTOGRAM, "扫描操作耗时", "ms"
        )
        self.register_metric(
            "scan_file_count", MetricType.COUNTER, "扫描文件数量", "files"
        )

        # 去重指标
        self.register_metric("dedup_ratio", MetricType.GAUGE, "去重率", "%")
        self.register_metric("blob_count", MetricType.GAUGE, "Blob 总数", "blobs")
        self.register_metric(
            "blob_reference_count", MetricType.HISTOGRAM, "Blob 引用次数分布", "refs"
        )

        # 翻译指标
        self.register_metric(
            "translation_coverage", MetricType.GAUGE, "翻译覆盖率", "%"
        )
        self.register_metric(
            "translated_entries", MetricType.COUNTER, "已翻译条目数", "entries"
        )
        self.register_metric(
            "untranslated_entries", MetricType.GAUGE, "未翻译条目数", "entries"
        )

        # 补丁指标
        self.register_metric(
            "patch_apply_duration", MetricType.HISTOGRAM, "补丁应用耗时", "ms"
        )
        self.register_metric("patch_conflict_rate", MetricType.GAUGE, "补丁冲突率", "%")
        self.register_metric(
            "patch_success_count", MetricType.COUNTER, "补丁成功数", "patches"
        )
        self.register_metric(
            "patch_failure_count", MetricType.COUNTER, "补丁失败数", "patches"
        )

        # 回滚指标
        self.register_metric("rollback_rate", MetricType.GAUGE, "回滚率", "%")
        self.register_metric("rollback_count", MetricType.COUNTER, "回滚次数", "times")

        # 系统指标
        self.register_metric(
            "api_request_duration", MetricType.HISTOGRAM, "API 请求耗时", "ms"
        )
        self.register_metric(
            "api_request_rate", MetricType.RATE, "API 请求速率", "req/s"
        )
        self.register_metric("memory_usage", MetricType.GAUGE, "内存使用量", "MB")

        logger.info("注册核心指标完成")

    def register_metric(
        self, name: str, metric_type: MetricType, description: str, unit: str = ""
    ) -> None:
        """
        注册指标

        Args:
            name: 指标名称
            metric_type: 指标类型
            description: 描述
            unit: 单位
        """
        self.metrics[name] = Metric(
            name=name, type=metric_type, description=description, unit=unit
        )

    def record(
        self, name: str, value: float, labels: dict[str, str] | None = None
    ) -> None:
        """
        记录指标值

        Args:
            name: 指标名称
            value: 值
            labels: 标签
        """
        if name not in self.metrics:
            logger.warning(f"未注册的指标: {name}")
            return

        metric = self.metrics[name]
        metric.record(value, labels)

        # 检查阈值
        self._check_thresholds(name, value)

        logger.debug(f"记录指标: {name}={value} {metric.unit}")

    def increment(self, name: str, value: float = 1.0) -> None:
        """
        增加计数器

        Args:
            name: 指标名称
            value: 增加的值
        """
        if name not in self.metrics:
            logger.warning(f"未注册的指标: {name}")
            return

        metric = self.metrics[name]
        if metric.type != MetricType.COUNTER:
            logger.warning(f"指标 {name} 不是计数器类型")
            return

        current = metric.get_current() or 0
        self.record(name, current + value)

    def start_timer(self, name: str) -> None:
        """
        开始计时

        Args:
            name: 计时器名称
        """
        self._timers[name] = time.time()

    def stop_timer(self, name: str, metric_name: str) -> float | None:
        """
        停止计时并记录

        Args:
            name: 计时器名称
            metric_name: 指标名称

        Returns:
            耗时（毫秒）
        """
        if name not in self._timers:
            logger.warning(f"计时器不存在: {name}")
            return None

        start_time = self._timers.pop(name)
        duration_ms = (time.time() - start_time) * 1000

        self.record(metric_name, duration_ms)
        return duration_ms

    def calculate_dedup_ratio(self, total_files: int, unique_blobs: int) -> float:
        """
        计算去重率

        Args:
            total_files: 总文件数
            unique_blobs: 唯一 Blob 数

        Returns:
            去重率（百分比）
        """
        if total_files == 0:
            return 0.0

        ratio = (1 - unique_blobs / total_files) * 100
        self.record("dedup_ratio", ratio)
        return ratio

    def calculate_translation_coverage(self, translated: int, total: int) -> float:
        """
        计算翻译覆盖率

        Args:
            translated: 已翻译数
            total: 总数

        Returns:
            覆盖率（百分比）
        """
        if total == 0:
            return 0.0

        coverage = (translated / total) * 100
        self.record("translation_coverage", coverage)
        self.record("translated_entries", translated)
        self.record("untranslated_entries", total - translated)
        return coverage

    def calculate_conflict_rate(self, conflicts: int, total_patches: int) -> float:
        """
        计算冲突率

        Args:
            conflicts: 冲突数
            total_patches: 总补丁数

        Returns:
            冲突率（百分比）
        """
        if total_patches == 0:
            return 0.0

        rate = (conflicts / total_patches) * 100
        self.record("patch_conflict_rate", rate)
        return rate

    def calculate_rollback_rate(self, rollbacks: int, total_operations: int) -> float:
        """
        计算回滚率

        Args:
            rollbacks: 回滚数
            total_operations: 总操作数

        Returns:
            回滚率（百分比）
        """
        if total_operations == 0:
            return 0.0

        rate = (rollbacks / total_operations) * 100
        self.record("rollback_rate", rate)
        self.record("rollback_count", rollbacks)
        return rate

    def get_p95_latency(self, metric_name: str) -> float | None:
        """
        获取 P95 时延

        Args:
            metric_name: 指标名称

        Returns:
            P95 时延值
        """
        if metric_name not in self.metrics:
            return None

        metric = self.metrics[metric_name]
        return metric.get_percentile(95)

    def _check_thresholds(self, name: str, value: float) -> None:
        """检查阈值"""
        # 定义阈值
        thresholds = {
            "scan_duration": 5000,  # 5秒
            "patch_apply_duration": 3000,  # 3秒
            "api_request_duration": 2000,  # 2秒
            "patch_conflict_rate": 10,  # 10%
            "rollback_rate": 5,  # 5%
            "memory_usage": 1024,  # 1GB
        }

        if name in thresholds and value > thresholds[name]:
            logger.warning(f"指标 {name} 超过阈值: {value} > {thresholds[name]}")
            if self.on_threshold_exceeded:
                self.on_threshold_exceeded(name, value)

    def get_summary(self) -> dict[str, Any]:
        """
        获取指标摘要

        Returns:
            指标摘要
        """
        summary = {"timestamp": datetime.now().isoformat(), "metrics": {}}

        for name, metric in self.metrics.items():
            metric_summary = {
                "type": metric.type.value,
                "description": metric.description,
                "unit": metric.unit,
                "current": metric.get_current(),
            }

            # 添加特定类型的额外信息
            if metric.type == MetricType.HISTOGRAM:
                metric_summary.update(
                    {
                        "p50": metric.get_percentile(50),
                        "p95": metric.get_percentile(95),
                        "p99": metric.get_percentile(99),
                    }
                )
            elif metric.type == MetricType.RATE:
                metric_summary["rate"] = metric.get_rate()

            summary["metrics"][name] = metric_summary

        # 添加关键指标
        summary["key_metrics"] = {
            "dedup_ratio": self.metrics["dedup_ratio"].get_current(),
            "translation_coverage": self.metrics["translation_coverage"].get_current(),
            "conflict_rate": self.metrics["patch_conflict_rate"].get_current(),
            "rollback_rate": self.metrics["rollback_rate"].get_current(),
            "p95_scan": self.get_p95_latency("scan_duration"),
            "p95_patch": self.get_p95_latency("patch_apply_duration"),
            "p95_api": self.get_p95_latency("api_request_duration"),
        }

        return summary

    def export_prometheus(self) -> str:
        """
        导出 Prometheus 格式

        Returns:
            Prometheus 格式的指标
        """
        lines = []

        for name, metric in self.metrics.items():
            # 添加 HELP 和 TYPE
            lines.append(f"# HELP {name} {metric.description}")
            lines.append(f"# TYPE {name} {metric.type.value}")

            # 添加值
            current = metric.get_current()
            if current is not None:
                lines.append(f"{name} {current}")

            # 对于直方图，添加百分位数
            if metric.type == MetricType.HISTOGRAM:
                for percentile in [50, 95, 99]:
                    value = metric.get_percentile(percentile)
                    if value is not None:
                        lines.append(f"{name}_p{percentile} {value}")

        return "\n".join(lines)

    def clear(self) -> None:
        """清理所有指标"""
        for metric in self.metrics.values():
            metric.values.clear()
        self._timers.clear()


# 全局指标收集器实例
_global_collector = MetricsCollector()


def get_metrics_collector() -> MetricsCollector:
    """获取全局指标收集器"""
    return _global_collector
