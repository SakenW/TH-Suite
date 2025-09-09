"""
报告生成器 - 生成各类报告

根据白皮书要求，生成 apply_report.json 等报告
"""

import json
import logging
from dataclasses import asdict, dataclass, field
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any

from .audit import AuditLogger
from .metrics import MetricsCollector
from .tracer import Tracer

logger = logging.getLogger(__name__)


class ReportType(Enum):
    """报告类型"""

    APPLY_REPORT = "apply_report"  # 应用报告
    SCAN_REPORT = "scan_report"  # 扫描报告
    QUALITY_REPORT = "quality_report"  # 质量报告
    AUDIT_REPORT = "audit_report"  # 审计报告
    PERFORMANCE_REPORT = "performance_report"  # 性能报告


@dataclass
class ApplyReportItem:
    """应用报告项"""

    patch_item_id: str
    target_file: str
    strategy: str
    status: str  # success, failed, skipped
    applied_entries: int
    conflict_entries: int
    error_message: str | None = None
    rollback_info: dict | None = None
    duration_ms: float = 0.0


@dataclass
class ApplyReport:
    """
    应用报告

    根据白皮书要求，记录补丁应用的详细信息
    """

    report_id: str
    patch_set_id: str
    apply_time: datetime
    total_items: int
    success_items: int
    failed_items: int
    skipped_items: int
    total_entries: int
    applied_entries: int
    conflict_entries: int
    items: list[ApplyReportItem] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        """转换为字典"""
        data = asdict(self)
        data["apply_time"] = self.apply_time.isoformat()
        return data

    def to_json(self) -> str:
        """转换为 JSON"""
        return json.dumps(self.to_dict(), ensure_ascii=False, indent=2)


class ReportGenerator:
    """
    报告生成器

    功能：
    1. 生成应用报告（apply_report.json）
    2. 生成扫描报告
    3. 生成质量报告
    4. 生成审计报告
    5. 生成性能报告
    """

    def __init__(
        self,
        output_dir: Path | None = None,
        tracer: Tracer | None = None,
        metrics: MetricsCollector | None = None,
        audit: AuditLogger | None = None,
    ):
        """
        初始化报告生成器

        Args:
            output_dir: 输出目录
            tracer: 追踪器
            metrics: 指标收集器
            audit: 审计日志器
        """
        self.output_dir = output_dir or Path("./reports")
        self.tracer = tracer
        self.metrics = metrics
        self.audit = audit

        # 确保输出目录存在
        self.output_dir.mkdir(parents=True, exist_ok=True)

    def generate_apply_report(
        self, patch_set_id: str, apply_results: list[dict[str, Any]]
    ) -> ApplyReport:
        """
        生成应用报告

        Args:
            patch_set_id: 补丁集 ID
            apply_results: 应用结果列表

        Returns:
            应用报告
        """
        report_id = f"apply_{datetime.now().strftime('%Y%m%d_%H%M%S')}"

        # 统计
        total_items = len(apply_results)
        success_items = sum(1 for r in apply_results if r["status"] == "success")
        failed_items = sum(1 for r in apply_results if r["status"] == "failed")
        skipped_items = sum(1 for r in apply_results if r["status"] == "skipped")

        total_entries = 0
        applied_entries = 0
        conflict_entries = 0

        # 生成报告项
        items = []
        for result in apply_results:
            item = ApplyReportItem(
                patch_item_id=result.get("patch_item_id", ""),
                target_file=result.get("target_file", ""),
                strategy=result.get("strategy", ""),
                status=result.get("status", "unknown"),
                applied_entries=result.get("applied_entries", 0),
                conflict_entries=result.get("conflict_entries", 0),
                error_message=result.get("error_message"),
                rollback_info=result.get("rollback_info"),
                duration_ms=result.get("duration_ms", 0.0),
            )
            items.append(item)

            # 累计统计
            total_entries += item.applied_entries + item.conflict_entries
            applied_entries += item.applied_entries
            conflict_entries += item.conflict_entries

        # 创建报告
        report = ApplyReport(
            report_id=report_id,
            patch_set_id=patch_set_id,
            apply_time=datetime.now(),
            total_items=total_items,
            success_items=success_items,
            failed_items=failed_items,
            skipped_items=skipped_items,
            total_entries=total_entries,
            applied_entries=applied_entries,
            conflict_entries=conflict_entries,
            items=items,
            metadata={
                "success_rate": success_items / total_items if total_items > 0 else 0,
                "conflict_rate": conflict_entries / total_entries
                if total_entries > 0
                else 0,
                "average_duration_ms": sum(i.duration_ms for i in items) / len(items)
                if items
                else 0,
            },
        )

        # 保存报告
        self._save_report(report, ReportType.APPLY_REPORT)

        logger.info(
            f"生成应用报告: {report_id} "
            f"(成功: {success_items}, 失败: {failed_items}, 跳过: {skipped_items})"
        )

        return report

    def generate_scan_report(
        self, scan_id: str, scan_results: dict[str, Any]
    ) -> dict[str, Any]:
        """
        生成扫描报告

        Args:
            scan_id: 扫描 ID
            scan_results: 扫描结果

        Returns:
            扫描报告
        """
        report = {
            "report_id": f"scan_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
            "scan_id": scan_id,
            "scan_time": datetime.now().isoformat(),
            "statistics": {
                "total_files": scan_results.get("total_files", 0),
                "scanned_files": scan_results.get("scanned_files", 0),
                "language_files": scan_results.get("language_files", 0),
                "total_entries": scan_results.get("total_entries", 0),
                "unique_entries": scan_results.get("unique_entries", 0),
                "dedup_ratio": scan_results.get("dedup_ratio", 0.0),
            },
            "artifacts": scan_results.get("artifacts", []),
            "containers": scan_results.get("containers", []),
            "blobs": scan_results.get("blobs", []),
            "errors": scan_results.get("errors", []),
            "warnings": scan_results.get("warnings", []),
        }

        # 添加追踪信息
        if self.tracer:
            trace = self.tracer.get_current_trace()
            if trace:
                report["trace_info"] = {
                    "trace_id": trace.trace_id,
                    "duration_ms": trace.duration_ms,
                    "span_count": trace.span_count,
                }

        # 添加性能指标
        if self.metrics:
            report["performance"] = {
                "p95_duration": self.metrics.get_p95_latency("scan_duration"),
                "throughput": self.metrics.metrics.get(
                    "scan_file_count", {}
                ).get_rate(),
            }

        # 保存报告
        self._save_report(report, ReportType.SCAN_REPORT)

        logger.info(f"生成扫描报告: {report['report_id']}")

        return report

    def generate_quality_report(
        self, check_results: dict[str, list[dict]]
    ) -> dict[str, Any]:
        """
        生成质量报告

        Args:
            check_results: 质量检查结果

        Returns:
            质量报告
        """
        report = {
            "report_id": f"quality_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
            "check_time": datetime.now().isoformat(),
            "summary": {
                "total_entries": len(check_results),
                "passed_entries": 0,
                "failed_entries": 0,
                "warning_entries": 0,
            },
            "by_validator": {},
            "failed_items": [],
            "warning_items": [],
        }

        # 分析结果
        for key, results in check_results.items():
            entry_passed = True
            has_warning = False

            for result in results:
                validator_name = result.get("validator", "unknown")

                # 统计验证器
                if validator_name not in report["by_validator"]:
                    report["by_validator"][validator_name] = {
                        "total": 0,
                        "passed": 0,
                        "failed": 0,
                        "warnings": 0,
                    }

                report["by_validator"][validator_name]["total"] += 1

                if result.get("passed"):
                    report["by_validator"][validator_name]["passed"] += 1
                else:
                    level = result.get("level", "error")
                    if level == "error":
                        report["by_validator"][validator_name]["failed"] += 1
                        entry_passed = False
                        report["failed_items"].append(
                            {
                                "key": key,
                                "validator": validator_name,
                                "message": result.get("message", ""),
                            }
                        )
                    elif level == "warning":
                        report["by_validator"][validator_name]["warnings"] += 1
                        has_warning = True
                        report["warning_items"].append(
                            {
                                "key": key,
                                "validator": validator_name,
                                "message": result.get("message", ""),
                            }
                        )

            # 更新统计
            if entry_passed and not has_warning:
                report["summary"]["passed_entries"] += 1
            elif not entry_passed:
                report["summary"]["failed_entries"] += 1
            elif has_warning:
                report["summary"]["warning_entries"] += 1

        # 限制失败和警告项数量
        report["failed_items"] = report["failed_items"][:100]
        report["warning_items"] = report["warning_items"][:100]

        # 计算通过率
        total = report["summary"]["total_entries"]
        if total > 0:
            report["summary"]["pass_rate"] = report["summary"]["passed_entries"] / total
            report["summary"]["failure_rate"] = (
                report["summary"]["failed_entries"] / total
            )

        # 保存报告
        self._save_report(report, ReportType.QUALITY_REPORT)

        logger.info(f"生成质量报告: {report['report_id']}")

        return report

    def generate_audit_report(
        self, start_time: datetime | None = None, end_time: datetime | None = None
    ) -> dict[str, Any]:
        """
        生成审计报告

        Args:
            start_time: 开始时间
            end_time: 结束时间

        Returns:
            审计报告
        """
        if not self.audit:
            logger.warning("审计日志器未配置")
            return {}

        report = {
            "report_id": f"audit_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
            "report_time": datetime.now().isoformat(),
            "period": {
                "start": start_time.isoformat() if start_time else None,
                "end": end_time.isoformat() if end_time else None,
            },
            "statistics": self.audit.get_statistics(),
            "critical_events": [],
            "security_events": [],
            "failed_operations": [],
        }

        # 查询关键事件
        from .audit import AuditEventType, AuditLevel

        critical_events = self.audit.query(
            level=AuditLevel.CRITICAL,
            start_time=start_time,
            end_time=end_time,
            limit=50,
        )
        report["critical_events"] = [
            {
                "timestamp": e.timestamp.isoformat(),
                "type": e.event_type.value,
                "action": e.action,
                "resource": e.resource,
                "user": e.user_id,
            }
            for e in critical_events
        ]

        # 查询安全事件
        security_events = self.audit.query(
            event_type=AuditEventType.SECURITY_ALERT,
            start_time=start_time,
            end_time=end_time,
            limit=50,
        )
        report["security_events"] = [
            {
                "timestamp": e.timestamp.isoformat(),
                "action": e.action,
                "severity": e.details.get("severity", "unknown"),
                "description": e.details.get("description", ""),
            }
            for e in security_events
        ]

        # 查询失败操作
        failed_ops = [
            e
            for e in self.audit.query(
                start_time=start_time, end_time=end_time, limit=1000
            )
            if e.result == "failed"
        ][:50]
        report["failed_operations"] = [
            {
                "timestamp": e.timestamp.isoformat(),
                "type": e.event_type.value,
                "action": e.action,
                "resource": e.resource,
                "error": e.details.get("error", ""),
            }
            for e in failed_ops
        ]

        # 保存报告
        self._save_report(report, ReportType.AUDIT_REPORT)

        logger.info(f"生成审计报告: {report['report_id']}")

        return report

    def generate_performance_report(self) -> dict[str, Any]:
        """
        生成性能报告

        Returns:
            性能报告
        """
        if not self.metrics:
            logger.warning("指标收集器未配置")
            return {}

        report = {
            "report_id": f"performance_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
            "report_time": datetime.now().isoformat(),
            "key_metrics": self.metrics.get_summary()["key_metrics"],
            "latencies": {},
            "throughput": {},
            "resource_usage": {},
            "recommendations": [],
        }

        # 时延分析
        latency_metrics = [
            "scan_duration",
            "patch_apply_duration",
            "api_request_duration",
        ]
        for metric_name in latency_metrics:
            if metric_name in self.metrics.metrics:
                metric = self.metrics.metrics[metric_name]
                report["latencies"][metric_name] = {
                    "p50": metric.get_percentile(50),
                    "p95": metric.get_percentile(95),
                    "p99": metric.get_percentile(99),
                    "max": max([v.value for v in metric.values])
                    if metric.values
                    else None,
                }

        # 吞吐量分析
        rate_metrics = ["api_request_rate"]
        for metric_name in rate_metrics:
            if metric_name in self.metrics.metrics:
                metric = self.metrics.metrics[metric_name]
                report["throughput"][metric_name] = {
                    "current": metric.get_rate(),
                    "unit": metric.unit,
                }

        # 资源使用
        if "memory_usage" in self.metrics.metrics:
            memory_metric = self.metrics.metrics["memory_usage"]
            report["resource_usage"]["memory"] = {
                "current": memory_metric.get_current(),
                "max": max([v.value for v in memory_metric.values])
                if memory_metric.values
                else None,
                "unit": memory_metric.unit,
            }

        # 生成建议
        if report["key_metrics"]:
            # 去重率建议
            dedup_ratio = report["key_metrics"].get("dedup_ratio", 0)
            if dedup_ratio < 20:
                report["recommendations"].append(
                    {
                        "type": "optimization",
                        "message": "去重率较低，建议检查内容识别算法",
                    }
                )

            # P95 时延建议
            p95_scan = report["key_metrics"].get("p95_scan", 0)
            if p95_scan and p95_scan > 5000:
                report["recommendations"].append(
                    {
                        "type": "performance",
                        "message": "扫描 P95 时延超过 5 秒，建议优化扫描性能",
                    }
                )

            # 冲突率建议
            conflict_rate = report["key_metrics"].get("conflict_rate", 0)
            if conflict_rate > 10:
                report["recommendations"].append(
                    {
                        "type": "quality",
                        "message": "补丁冲突率较高，建议改进翻译质量控制",
                    }
                )

        # 保存报告
        self._save_report(report, ReportType.PERFORMANCE_REPORT)

        logger.info(f"生成性能报告: {report['report_id']}")

        return report

    def _save_report(self, report: Any, report_type: ReportType) -> Path:
        """
        保存报告

        Args:
            report: 报告内容
            report_type: 报告类型

        Returns:
            报告文件路径
        """
        # 生成文件名
        if hasattr(report, "report_id"):
            filename = f"{report.report_id}.json"
        elif isinstance(report, dict) and "report_id" in report:
            filename = f"{report['report_id']}.json"
        else:
            filename = (
                f"{report_type.value}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
            )

        # 创建类型目录
        type_dir = self.output_dir / report_type.value
        type_dir.mkdir(exist_ok=True)

        # 保存文件
        file_path = type_dir / filename

        try:
            # 转换为 JSON
            if hasattr(report, "to_json"):
                content = report.to_json()
            else:
                content = json.dumps(report, ensure_ascii=False, indent=2)

            # 写入文件
            with open(file_path, "w", encoding="utf-8") as f:
                f.write(content)

            logger.info(f"报告已保存: {file_path}")
            return file_path

        except Exception as e:
            logger.error(f"保存报告失败: {e}")
            raise

    def list_reports(
        self, report_type: ReportType | None = None, limit: int = 100
    ) -> list[dict[str, Any]]:
        """
        列出报告

        Args:
            report_type: 报告类型（None 表示所有）
            limit: 限制数量

        Returns:
            报告列表
        """
        reports = []

        # 确定搜索目录
        if report_type:
            search_dirs = [self.output_dir / report_type.value]
        else:
            search_dirs = [self.output_dir / rt.value for rt in ReportType]

        # 搜索报告文件
        for dir_path in search_dirs:
            if not dir_path.exists():
                continue

            for file_path in sorted(dir_path.glob("*.json"), reverse=True)[:limit]:
                try:
                    # 读取报告元信息
                    with open(file_path, encoding="utf-8") as f:
                        data = json.load(f)

                    reports.append(
                        {
                            "file": str(file_path),
                            "type": dir_path.name,
                            "report_id": data.get("report_id", file_path.stem),
                            "time": data.get("report_time")
                            or data.get("apply_time")
                            or data.get("scan_time"),
                            "size": file_path.stat().st_size,
                        }
                    )
                except Exception as e:
                    logger.error(f"读取报告失败 {file_path}: {e}")

        return reports[:limit]


# 全局报告生成器实例
_global_reporter: ReportGenerator | None = None


def get_reporter() -> ReportGenerator:
    """获取全局报告生成器"""
    global _global_reporter
    if not _global_reporter:
        from .audit import get_audit_logger
        from .metrics import get_metrics_collector
        from .tracer import get_tracer

        _global_reporter = ReportGenerator(
            tracer=get_tracer(),
            metrics=get_metrics_collector(),
            audit=get_audit_logger(),
        )
    return _global_reporter
