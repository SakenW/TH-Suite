"""
SLO (Service Level Objective) 性能监控系统
提供全面的性能指标监控、SLA追踪和告警功能
"""

import time
import asyncio
from typing import Dict, List, Optional, Any, Callable, Union
from datetime import datetime, timedelta
from dataclasses import dataclass, field
from enum import Enum
import json
import statistics
from collections import defaultdict, deque
import structlog

logger = structlog.get_logger(__name__)


class SLOType(Enum):
    """SLO类型"""
    AVAILABILITY = "availability"           # 可用性
    LATENCY = "latency"                    # 延迟
    THROUGHPUT = "throughput"              # 吞吐量
    ERROR_RATE = "error_rate"              # 错误率
    RESPONSE_TIME = "response_time"        # 响应时间
    SUCCESS_RATE = "success_rate"          # 成功率


class SLOStatus(Enum):
    """SLO状态"""
    HEALTHY = "healthy"                    # 健康
    WARNING = "warning"                    # 警告
    CRITICAL = "critical"                  # 严重
    BREACH = "breach"                      # 违反


class AlertSeverity(Enum):
    """告警严重程度"""
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"


@dataclass
class SLOTarget:
    """SLO目标定义"""
    name: str
    slo_type: SLOType
    target_value: float                    # 目标值
    threshold_warning: float               # 警告阈值
    threshold_critical: float             # 严重阈值
    measurement_window_seconds: int        # 测量窗口(秒)
    evaluation_interval_seconds: int       # 评估间隔(秒)
    
    # 计算方式相关
    aggregation_method: str = "average"    # average, p95, p99, max, min
    error_budget_percentage: float = 1.0   # 错误预算百分比
    
    # 元数据
    description: str = ""
    tags: Dict[str, str] = field(default_factory=dict)
    enabled: bool = True


@dataclass
class SLOMetric:
    """SLO指标数据点"""
    timestamp: float
    value: float
    labels: Dict[str, str] = field(default_factory=dict)
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class SLOAlert:
    """SLO告警"""
    id: str
    slo_name: str
    severity: AlertSeverity
    status: SLOStatus
    message: str
    current_value: float
    target_value: float
    threshold_value: float
    created_at: float
    resolved_at: Optional[float] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def is_active(self) -> bool:
        """检查告警是否活跃"""
        return self.resolved_at is None
    
    def duration_seconds(self) -> float:
        """获取告警持续时间"""
        end_time = self.resolved_at or time.time()
        return end_time - self.created_at


@dataclass
class SLOEvaluation:
    """SLO评估结果"""
    slo_name: str
    timestamp: float
    status: SLOStatus
    current_value: float
    target_value: float
    error_budget_remaining: float
    sample_count: int
    evaluation_window_seconds: int
    
    # 计算的统计信息
    statistics: Dict[str, float] = field(default_factory=dict)
    
    def is_healthy(self) -> bool:
        """检查是否健康"""
        return self.status == SLOStatus.HEALTHY
    
    def get_compliance_percentage(self) -> float:
        """获取合规百分比"""
        if self.target_value == 0:
            return 100.0
        return (self.current_value / self.target_value) * 100.0


class SLODataCollector:
    """SLO数据收集器"""
    
    def __init__(self, max_data_points: int = 10000):
        self.max_data_points = max_data_points
        self.data: Dict[str, deque] = defaultdict(lambda: deque(maxlen=max_data_points))
        self.lock = asyncio.Lock()
    
    async def record_metric(
        self,
        slo_name: str,
        value: float,
        labels: Dict[str, str] = None,
        metadata: Dict[str, Any] = None,
        timestamp: float = None
    ):
        """记录指标数据"""
        if timestamp is None:
            timestamp = time.time()
        
        metric = SLOMetric(
            timestamp=timestamp,
            value=value,
            labels=labels or {},
            metadata=metadata or {}
        )
        
        async with self.lock:
            self.data[slo_name].append(metric)
        
        logger.debug("SLO指标已记录",
                    slo_name=slo_name,
                    value=value,
                    timestamp=timestamp)
    
    async def get_metrics(
        self,
        slo_name: str,
        start_time: float = None,
        end_time: float = None,
        limit: int = None
    ) -> List[SLOMetric]:
        """获取指标数据"""
        async with self.lock:
            if slo_name not in self.data:
                return []
            
            metrics = list(self.data[slo_name])
        
        # 时间过滤
        if start_time is not None:
            metrics = [m for m in metrics if m.timestamp >= start_time]
        if end_time is not None:
            metrics = [m for m in metrics if m.timestamp <= end_time]
        
        # 限制数量
        if limit is not None:
            metrics = metrics[-limit:]
        
        return metrics
    
    async def cleanup_old_data(self, retention_seconds: int = 86400):
        """清理旧数据"""
        cutoff_time = time.time() - retention_seconds
        
        async with self.lock:
            for slo_name in list(self.data.keys()):
                # 过滤掉旧数据
                old_deque = self.data[slo_name]
                new_deque = deque(
                    (m for m in old_deque if m.timestamp > cutoff_time),
                    maxlen=self.max_data_points
                )
                self.data[slo_name] = new_deque
        
        logger.debug("SLO数据清理完成", cutoff_time=cutoff_time)


class SLOEvaluator:
    """SLO评估器"""
    
    def __init__(self, data_collector: SLODataCollector):
        self.data_collector = data_collector
    
    async def evaluate_slo(self, target: SLOTarget) -> SLOEvaluation:
        """评估单个SLO"""
        end_time = time.time()
        start_time = end_time - target.measurement_window_seconds
        
        # 获取测量窗口内的数据
        metrics = await self.data_collector.get_metrics(
            target.name,
            start_time=start_time,
            end_time=end_time
        )
        
        if not metrics:
            # 没有数据，返回默认评估
            return SLOEvaluation(
                slo_name=target.name,
                timestamp=end_time,
                status=SLOStatus.CRITICAL,
                current_value=0.0,
                target_value=target.target_value,
                error_budget_remaining=0.0,
                sample_count=0,
                evaluation_window_seconds=target.measurement_window_seconds
            )
        
        # 计算统计值
        values = [m.value for m in metrics]
        current_value = self._calculate_aggregated_value(values, target.aggregation_method)
        
        # 计算统计信息
        stats = self._calculate_statistics(values)
        
        # 确定状态
        status = self._determine_status(current_value, target)
        
        # 计算错误预算
        error_budget_remaining = self._calculate_error_budget_remaining(
            current_value,
            target
        )
        
        return SLOEvaluation(
            slo_name=target.name,
            timestamp=end_time,
            status=status,
            current_value=current_value,
            target_value=target.target_value,
            error_budget_remaining=error_budget_remaining,
            sample_count=len(metrics),
            evaluation_window_seconds=target.measurement_window_seconds,
            statistics=stats
        )
    
    def _calculate_aggregated_value(self, values: List[float], method: str) -> float:
        """计算聚合值"""
        if not values:
            return 0.0
        
        if method == "average":
            return statistics.mean(values)
        elif method == "median":
            return statistics.median(values)
        elif method == "p95":
            return self._percentile(values, 95)
        elif method == "p99":
            return self._percentile(values, 99)
        elif method == "max":
            return max(values)
        elif method == "min":
            return min(values)
        elif method == "sum":
            return sum(values)
        else:
            return statistics.mean(values)
    
    def _percentile(self, values: List[float], percentile: int) -> float:
        """计算百分位数"""
        if not values:
            return 0.0
        
        sorted_values = sorted(values)
        index = (percentile / 100.0) * (len(sorted_values) - 1)
        
        if index.is_integer():
            return sorted_values[int(index)]
        else:
            lower_index = int(index)
            upper_index = lower_index + 1
            weight = index - lower_index
            
            if upper_index < len(sorted_values):
                return sorted_values[lower_index] * (1 - weight) + sorted_values[upper_index] * weight
            else:
                return sorted_values[lower_index]
    
    def _calculate_statistics(self, values: List[float]) -> Dict[str, float]:
        """计算统计信息"""
        if not values:
            return {}
        
        return {
            "count": len(values),
            "mean": statistics.mean(values),
            "median": statistics.median(values),
            "min": min(values),
            "max": max(values),
            "std_dev": statistics.stdev(values) if len(values) > 1 else 0.0,
            "p95": self._percentile(values, 95),
            "p99": self._percentile(values, 99),
        }
    
    def _determine_status(self, current_value: float, target: SLOTarget) -> SLOStatus:
        """确定SLO状态"""
        if target.slo_type in [SLOType.ERROR_RATE, SLOType.LATENCY, SLOType.RESPONSE_TIME]:
            # 越小越好的指标 - 正确的阈值逻辑
            # critical < warning < target
            if current_value <= target.threshold_critical:
                return SLOStatus.HEALTHY
            elif current_value <= target.threshold_warning:
                return SLOStatus.WARNING
            elif current_value <= target.target_value:
                return SLOStatus.CRITICAL
            else:
                return SLOStatus.BREACH
        else:
            # 越大越好的指标 (如可用性、吞吐量、成功率)
            # target > warning > critical
            if current_value >= target.target_value:
                return SLOStatus.HEALTHY
            elif current_value >= target.threshold_warning:
                return SLOStatus.WARNING
            elif current_value >= target.threshold_critical:
                return SLOStatus.CRITICAL
            else:
                return SLOStatus.BREACH
    
    def _calculate_error_budget_remaining(
        self,
        current_value: float,
        target: SLOTarget
    ) -> float:
        """计算剩余错误预算"""
        if target.target_value == 0:
            return 0.0
        
        if target.slo_type in [SLOType.ERROR_RATE]:
            # 错误率：预算用完程度 = 当前错误率 / 目标错误率
            budget_used = current_value / target.target_value
        else:
            # 其他指标：预算用完程度 = (目标值 - 当前值) / 目标值
            budget_used = max(0, (target.target_value - current_value) / target.target_value)
        
        return max(0.0, 1.0 - budget_used)


class SLOAlertManager:
    """SLO告警管理器"""
    
    def __init__(self):
        self.active_alerts: Dict[str, SLOAlert] = {}
        self.alert_history: List[SLOAlert] = []
        self.alert_handlers: List[Callable[[SLOAlert], None]] = []
        self.lock = asyncio.Lock()
    
    def add_alert_handler(self, handler: Callable[[SLOAlert], None]):
        """添加告警处理器"""
        self.alert_handlers.append(handler)
    
    async def process_evaluation(self, evaluation: SLOEvaluation, target: SLOTarget):
        """处理SLO评估结果，生成告警"""
        alert_key = f"{evaluation.slo_name}_{evaluation.status.value}"
        
        async with self.lock:
            if evaluation.status in [SLOStatus.WARNING, SLOStatus.CRITICAL, SLOStatus.BREACH]:
                # 需要告警
                if alert_key not in self.active_alerts:
                    # 创建新告警
                    alert = self._create_alert(evaluation, target)
                    self.active_alerts[alert_key] = alert
                    self.alert_history.append(alert)
                    
                    # 触发告警处理器
                    await self._trigger_alert_handlers(alert)
                    
                    logger.warning("SLO告警触发",
                                  slo_name=evaluation.slo_name,
                                  status=evaluation.status.value,
                                  current_value=evaluation.current_value,
                                  target_value=evaluation.target_value)
            else:
                # 状态正常，检查是否需要解除告警
                alerts_to_resolve = [
                    key for key in self.active_alerts.keys()
                    if key.startswith(f"{evaluation.slo_name}_")
                ]
                
                for key in alerts_to_resolve:
                    alert = self.active_alerts[key]
                    alert.resolved_at = time.time()
                    del self.active_alerts[key]
                    
                    logger.info("SLO告警已解除",
                               slo_name=evaluation.slo_name,
                               alert_id=alert.id,
                               duration_seconds=alert.duration_seconds())
    
    def _create_alert(self, evaluation: SLOEvaluation, target: SLOTarget) -> SLOAlert:
        """创建告警"""
        severity = self._map_status_to_severity(evaluation.status)
        threshold_value = self._get_threshold_value(evaluation.status, target)
        
        message = self._generate_alert_message(evaluation, target)
        
        alert_id = f"{evaluation.slo_name}_{int(evaluation.timestamp)}_{evaluation.status.value}"
        
        return SLOAlert(
            id=alert_id,
            slo_name=evaluation.slo_name,
            severity=severity,
            status=evaluation.status,
            message=message,
            current_value=evaluation.current_value,
            target_value=evaluation.target_value,
            threshold_value=threshold_value,
            created_at=evaluation.timestamp,
            metadata={
                "error_budget_remaining": evaluation.error_budget_remaining,
                "sample_count": evaluation.sample_count,
                "statistics": evaluation.statistics,
            }
        )
    
    def _map_status_to_severity(self, status: SLOStatus) -> AlertSeverity:
        """映射状态到告警严重程度"""
        mapping = {
            SLOStatus.WARNING: AlertSeverity.WARNING,
            SLOStatus.CRITICAL: AlertSeverity.ERROR,
            SLOStatus.BREACH: AlertSeverity.CRITICAL,
        }
        return mapping.get(status, AlertSeverity.INFO)
    
    def _get_threshold_value(self, status: SLOStatus, target: SLOTarget) -> float:
        """获取阈值"""
        if status == SLOStatus.WARNING:
            return target.threshold_warning
        elif status == SLOStatus.CRITICAL:
            return target.threshold_critical
        else:
            return target.target_value
    
    def _generate_alert_message(self, evaluation: SLOEvaluation, target: SLOTarget) -> str:
        """生成告警消息"""
        return (
            f"SLO '{evaluation.slo_name}' {evaluation.status.value}: "
            f"Current value {evaluation.current_value:.3f} "
            f"{'exceeds' if evaluation.status == SLOStatus.BREACH else 'approaches'} "
            f"target {evaluation.target_value:.3f}. "
            f"Error budget remaining: {evaluation.error_budget_remaining:.1%}"
        )
    
    async def _trigger_alert_handlers(self, alert: SLOAlert):
        """触发告警处理器"""
        for handler in self.alert_handlers:
            try:
                if asyncio.iscoroutinefunction(handler):
                    await handler(alert)
                else:
                    handler(alert)
            except Exception as e:
                logger.error("告警处理器执行失败",
                           alert_id=alert.id,
                           handler=str(handler),
                           error=str(e))
    
    def get_active_alerts(self) -> List[SLOAlert]:
        """获取活跃告警"""
        return list(self.active_alerts.values())
    
    def get_alert_history(self, limit: int = 100) -> List[SLOAlert]:
        """获取告警历史"""
        return self.alert_history[-limit:]


class SLOMonitoringService:
    """SLO监控服务"""
    
    def __init__(self):
        self.data_collector = SLODataCollector()
        self.evaluator = SLOEvaluator(self.data_collector)
        self.alert_manager = SLOAlertManager()
        self.targets: Dict[str, SLOTarget] = {}
        self.evaluation_tasks: Dict[str, asyncio.Task] = {}
        self.cleanup_task: Optional[asyncio.Task] = None
        self.running = False
        
        logger.info("SLO监控服务初始化完成")
    
    async def start(self):
        """启动监控服务"""
        if self.running:
            return
        
        self.running = True
        
        # 启动数据清理任务
        self.cleanup_task = asyncio.create_task(self._cleanup_loop())
        
        # 启动所有已配置的SLO评估任务
        for target_name in self.targets:
            await self._start_evaluation_task(target_name)
        
        logger.info("SLO监控服务已启动")
    
    async def stop(self):
        """停止监控服务"""
        if not self.running:
            return
        
        self.running = False
        
        # 停止所有评估任务
        for task in self.evaluation_tasks.values():
            task.cancel()
            try:
                await task
            except asyncio.CancelledError:
                pass
        
        self.evaluation_tasks.clear()
        
        # 停止数据清理任务
        if self.cleanup_task:
            self.cleanup_task.cancel()
            try:
                await self.cleanup_task
            except asyncio.CancelledError:
                pass
            self.cleanup_task = None
        
        logger.info("SLO监控服务已停止")
    
    def add_slo_target(self, target: SLOTarget):
        """添加SLO目标"""
        self.targets[target.name] = target
        
        # 如果服务正在运行，启动评估任务
        if self.running:
            asyncio.create_task(self._start_evaluation_task(target.name))
        
        logger.info("SLO目标已添加",
                   name=target.name,
                   type=target.slo_type.value,
                   target_value=target.target_value)
    
    def remove_slo_target(self, target_name: str):
        """移除SLO目标"""
        if target_name in self.targets:
            del self.targets[target_name]
        
        # 停止评估任务
        if target_name in self.evaluation_tasks:
            self.evaluation_tasks[target_name].cancel()
            del self.evaluation_tasks[target_name]
        
        logger.info("SLO目标已移除", name=target_name)
    
    async def record_metric(
        self,
        target_name: str,
        value: float,
        labels: Dict[str, str] = None,
        metadata: Dict[str, Any] = None
    ):
        """记录指标数据"""
        await self.data_collector.record_metric(target_name, value, labels, metadata)
    
    async def get_slo_evaluation(self, target_name: str) -> Optional[SLOEvaluation]:
        """获取SLO评估结果"""
        if target_name not in self.targets:
            return None
        
        return await self.evaluator.evaluate_slo(self.targets[target_name])
    
    async def get_all_evaluations(self) -> List[SLOEvaluation]:
        """获取所有SLO评估结果"""
        evaluations = []
        for target_name in self.targets:
            evaluation = await self.get_slo_evaluation(target_name)
            if evaluation:
                evaluations.append(evaluation)
        return evaluations
    
    def get_dashboard_data(self) -> Dict[str, Any]:
        """获取仪表板数据"""
        active_alerts = self.alert_manager.get_active_alerts()
        
        return {
            "slo_targets": {
                name: {
                    "type": target.slo_type.value,
                    "target_value": target.target_value,
                    "enabled": target.enabled,
                    "description": target.description,
                }
                for name, target in self.targets.items()
            },
            "active_alerts": [
                {
                    "id": alert.id,
                    "slo_name": alert.slo_name,
                    "severity": alert.severity.value,
                    "status": alert.status.value,
                    "message": alert.message,
                    "current_value": alert.current_value,
                    "target_value": alert.target_value,
                    "duration_seconds": alert.duration_seconds(),
                }
                for alert in active_alerts
            ],
            "summary": {
                "total_slos": len(self.targets),
                "enabled_slos": sum(1 for t in self.targets.values() if t.enabled),
                "active_alerts": len(active_alerts),
                "critical_alerts": len([a for a in active_alerts if a.severity == AlertSeverity.CRITICAL]),
            }
        }
    
    async def _start_evaluation_task(self, target_name: str):
        """启动SLO评估任务"""
        if target_name in self.evaluation_tasks:
            # 任务已存在，先取消
            self.evaluation_tasks[target_name].cancel()
        
        target = self.targets[target_name]
        if not target.enabled:
            return
        
        async def evaluation_loop():
            while self.running:
                try:
                    evaluation = await self.evaluator.evaluate_slo(target)
                    await self.alert_manager.process_evaluation(evaluation, target)
                    
                    await asyncio.sleep(target.evaluation_interval_seconds)
                    
                except asyncio.CancelledError:
                    break
                except Exception as e:
                    logger.error("SLO评估任务异常",
                               target_name=target_name,
                               error=str(e))
                    await asyncio.sleep(min(target.evaluation_interval_seconds, 60))
        
        self.evaluation_tasks[target_name] = asyncio.create_task(evaluation_loop())
        logger.debug("SLO评估任务已启动", target_name=target_name)
    
    async def _cleanup_loop(self):
        """数据清理循环"""
        while self.running:
            try:
                await asyncio.sleep(3600)  # 每小时清理一次
                await self.data_collector.cleanup_old_data(retention_seconds=86400 * 7)  # 保留7天
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error("数据清理任务异常", error=str(e))


# ==================== 便捷函数和预定义SLO ====================

def create_api_latency_slo(
    name: str = "api_latency",
    target_p95_ms: float = 100.0,
    warning_p95_ms: float = 80.0,
    critical_p95_ms: float = 50.0
) -> SLOTarget:
    """创建API延迟SLO"""
    return SLOTarget(
        name=name,
        slo_type=SLOType.LATENCY,
        target_value=target_p95_ms,
        threshold_warning=warning_p95_ms,
        threshold_critical=critical_p95_ms,
        measurement_window_seconds=300,  # 5分钟
        evaluation_interval_seconds=60,  # 1分钟评估
        aggregation_method="p95",
        description=f"API 95th percentile latency should be under {target_p95_ms}ms"
    )


def create_availability_slo(
    name: str = "service_availability",
    target_percentage: float = 99.9,
    warning_percentage: float = 99.5,
    critical_percentage: float = 99.0
) -> SLOTarget:
    """创建可用性SLO"""
    return SLOTarget(
        name=name,
        slo_type=SLOType.AVAILABILITY,
        target_value=target_percentage,
        threshold_warning=warning_percentage,
        threshold_critical=critical_percentage,
        measurement_window_seconds=3600,  # 1小时
        evaluation_interval_seconds=300,  # 5分钟评估
        aggregation_method="average",
        description=f"Service availability should be above {target_percentage}%"
    )


def create_error_rate_slo(
    name: str = "error_rate",
    target_percentage: float = 1.0,
    warning_percentage: float = 0.5,
    critical_percentage: float = 0.1
) -> SLOTarget:
    """创建错误率SLO"""
    return SLOTarget(
        name=name,
        slo_type=SLOType.ERROR_RATE,
        target_value=target_percentage,
        threshold_warning=warning_percentage,
        threshold_critical=critical_percentage,
        measurement_window_seconds=900,  # 15分钟
        evaluation_interval_seconds=300,  # 5分钟评估
        aggregation_method="average",
        description=f"Error rate should be below {target_percentage}%"
    )


# ==================== 全局监控服务 ====================

_global_slo_service: Optional[SLOMonitoringService] = None


async def get_slo_service() -> SLOMonitoringService:
    """获取全局SLO监控服务"""
    global _global_slo_service
    if _global_slo_service is None:
        _global_slo_service = SLOMonitoringService()
    return _global_slo_service


async def initialize_slo_monitoring():
    """初始化SLO监控服务"""
    global _global_slo_service
    _global_slo_service = SLOMonitoringService()
    
    # 添加默认SLO目标
    _global_slo_service.add_slo_target(create_api_latency_slo())
    _global_slo_service.add_slo_target(create_availability_slo())
    _global_slo_service.add_slo_target(create_error_rate_slo())
    
    await _global_slo_service.start()
    logger.info("SLO监控服务已初始化并启动")


async def shutdown_slo_monitoring():
    """关闭SLO监控服务"""
    global _global_slo_service
    if _global_slo_service:
        await _global_slo_service.stop()
        _global_slo_service = None