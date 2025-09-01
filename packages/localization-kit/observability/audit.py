"""
审计日志器 - 记录系统操作和安全事件

提供完整的审计追踪，支持合规性要求
"""

import logging
import json
import uuid
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field, asdict
from datetime import datetime
from enum import Enum
from pathlib import Path

logger = logging.getLogger(__name__)


class AuditEventType(Enum):
    """审计事件类型"""
    # 认证与授权
    AUTH_LOGIN = "auth.login"
    AUTH_LOGOUT = "auth.logout"
    AUTH_FAILED = "auth.failed"
    PERMISSION_GRANTED = "permission.granted"
    PERMISSION_DENIED = "permission.denied"
    
    # 数据操作
    DATA_CREATE = "data.create"
    DATA_READ = "data.read"
    DATA_UPDATE = "data.update"
    DATA_DELETE = "data.delete"
    DATA_EXPORT = "data.export"
    DATA_IMPORT = "data.import"
    
    # 扫描操作
    SCAN_START = "scan.start"
    SCAN_COMPLETE = "scan.complete"
    SCAN_FAILED = "scan.failed"
    
    # 补丁操作
    PATCH_CREATE = "patch.create"
    PATCH_APPLY = "patch.apply"
    PATCH_ROLLBACK = "patch.rollback"
    PATCH_PUBLISH = "patch.publish"
    
    # 回写操作
    WRITEBACK_START = "writeback.start"
    WRITEBACK_SUCCESS = "writeback.success"
    WRITEBACK_FAILED = "writeback.failed"
    WRITEBACK_ROLLBACK = "writeback.rollback"
    
    # 质量检查
    QUALITY_CHECK = "quality.check"
    QUALITY_PASSED = "quality.passed"
    QUALITY_FAILED = "quality.failed"
    
    # 系统操作
    SYSTEM_START = "system.start"
    SYSTEM_STOP = "system.stop"
    SYSTEM_CONFIG_CHANGE = "system.config_change"
    SYSTEM_ERROR = "system.error"
    
    # 合规性
    COMPLIANCE_CHECK = "compliance.check"
    LICENSE_VIOLATION = "license.violation"
    SECURITY_ALERT = "security.alert"


class AuditLevel(Enum):
    """审计级别"""
    DEBUG = "debug"
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"


@dataclass
class AuditEvent:
    """审计事件"""
    event_id: str
    event_type: AuditEventType
    level: AuditLevel
    timestamp: datetime
    user_id: Optional[str]
    session_id: Optional[str]
    ip_address: Optional[str]
    action: str
    resource: Optional[str]
    result: str
    details: Dict[str, Any] = field(default_factory=dict)
    tags: List[str] = field(default_factory=list)
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        data = asdict(self)
        data['event_type'] = self.event_type.value
        data['level'] = self.level.value
        data['timestamp'] = self.timestamp.isoformat()
        return data
    
    def to_json(self) -> str:
        """转换为 JSON"""
        return json.dumps(self.to_dict(), ensure_ascii=False, indent=2)


class AuditLogger:
    """
    审计日志器
    
    功能：
    1. 记录所有关键操作
    2. 支持多种输出格式
    3. 提供查询和分析能力
    4. 满足合规性要求
    """
    
    def __init__(
        self,
        log_file: Optional[Path] = None,
        max_events: int = 10000,
        enable_console: bool = True
    ):
        """
        初始化审计日志器
        
        Args:
            log_file: 日志文件路径
            max_events: 内存中最大事件数
            enable_console: 是否输出到控制台
        """
        self.log_file = log_file
        self.max_events = max_events
        self.enable_console = enable_console
        
        # 事件存储
        self.events: List[AuditEvent] = []
        
        # 会话信息
        self.current_session_id: Optional[str] = None
        self.current_user_id: Optional[str] = None
        
        # 配置
        self.config = {
            'log_level': AuditLevel.INFO,
            'sensitive_fields': ['password', 'token', 'secret', 'key'],
            'retention_days': 90
        }
        
        # 初始化文件
        if self.log_file:
            self._init_log_file()
    
    def _init_log_file(self) -> None:
        """初始化日志文件"""
        if self.log_file and not self.log_file.exists():
            self.log_file.parent.mkdir(parents=True, exist_ok=True)
            self.log_file.touch()
            logger.info(f"创建审计日志文件: {self.log_file}")
    
    def set_session(self, session_id: str, user_id: Optional[str] = None) -> None:
        """
        设置会话信息
        
        Args:
            session_id: 会话 ID
            user_id: 用户 ID
        """
        self.current_session_id = session_id
        self.current_user_id = user_id
    
    def log(
        self,
        event_type: AuditEventType,
        action: str,
        level: AuditLevel = AuditLevel.INFO,
        resource: Optional[str] = None,
        result: str = "success",
        details: Optional[Dict[str, Any]] = None,
        tags: Optional[List[str]] = None
    ) -> AuditEvent:
        """
        记录审计事件
        
        Args:
            event_type: 事件类型
            action: 操作描述
            level: 级别
            resource: 资源标识
            result: 结果
            details: 详细信息
            tags: 标签
            
        Returns:
            审计事件
        """
        # 过滤敏感信息
        if details:
            details = self._filter_sensitive(details)
        
        # 创建事件
        event = AuditEvent(
            event_id=str(uuid.uuid4()),
            event_type=event_type,
            level=level,
            timestamp=datetime.now(),
            user_id=self.current_user_id,
            session_id=self.current_session_id,
            ip_address=self._get_ip_address(),
            action=action,
            resource=resource,
            result=result,
            details=details or {},
            tags=tags or []
        )
        
        # 存储事件
        self._store_event(event)
        
        # 输出事件
        self._output_event(event)
        
        return event
    
    def log_scan(
        self,
        action: str,
        path: str,
        result: str = "success",
        stats: Optional[Dict] = None
    ) -> AuditEvent:
        """记录扫描事件"""
        event_type = {
            "start": AuditEventType.SCAN_START,
            "complete": AuditEventType.SCAN_COMPLETE,
            "failed": AuditEventType.SCAN_FAILED
        }.get(result, AuditEventType.SCAN_START)
        
        return self.log(
            event_type=event_type,
            action=f"扫描操作: {action}",
            resource=path,
            result=result,
            details=stats or {},
            tags=["scan"]
        )
    
    def log_patch(
        self,
        action: str,
        patch_id: str,
        result: str = "success",
        affected_files: Optional[List[str]] = None
    ) -> AuditEvent:
        """记录补丁事件"""
        event_type = {
            "create": AuditEventType.PATCH_CREATE,
            "apply": AuditEventType.PATCH_APPLY,
            "rollback": AuditEventType.PATCH_ROLLBACK,
            "publish": AuditEventType.PATCH_PUBLISH
        }.get(action, AuditEventType.PATCH_APPLY)
        
        return self.log(
            event_type=event_type,
            action=f"补丁操作: {action}",
            resource=patch_id,
            result=result,
            details={"affected_files": affected_files} if affected_files else {},
            tags=["patch"]
        )
    
    def log_writeback(
        self,
        strategy: str,
        target: str,
        result: str = "success",
        stats: Optional[Dict] = None
    ) -> AuditEvent:
        """记录回写事件"""
        event_type = {
            "start": AuditEventType.WRITEBACK_START,
            "success": AuditEventType.WRITEBACK_SUCCESS,
            "failed": AuditEventType.WRITEBACK_FAILED,
            "rollback": AuditEventType.WRITEBACK_ROLLBACK
        }.get(result, AuditEventType.WRITEBACK_START)
        
        return self.log(
            event_type=event_type,
            action=f"回写策略: {strategy}",
            resource=target,
            result=result,
            details=stats or {},
            tags=["writeback", strategy]
        )
    
    def log_quality(
        self,
        check_type: str,
        target: str,
        passed: bool,
        issues: Optional[List[Dict]] = None
    ) -> AuditEvent:
        """记录质量检查事件"""
        event_type = AuditEventType.QUALITY_PASSED if passed else AuditEventType.QUALITY_FAILED
        
        return self.log(
            event_type=event_type,
            action=f"质量检查: {check_type}",
            resource=target,
            result="passed" if passed else "failed",
            details={"issues": issues} if issues else {},
            tags=["quality", check_type]
        )
    
    def log_security(
        self,
        alert_type: str,
        description: str,
        severity: str = "medium",
        details: Optional[Dict] = None
    ) -> AuditEvent:
        """记录安全事件"""
        level = {
            "low": AuditLevel.WARNING,
            "medium": AuditLevel.ERROR,
            "high": AuditLevel.CRITICAL,
            "critical": AuditLevel.CRITICAL
        }.get(severity, AuditLevel.WARNING)
        
        return self.log(
            event_type=AuditEventType.SECURITY_ALERT,
            action=f"安全警报: {alert_type}",
            level=level,
            result="alert",
            details={
                "description": description,
                "severity": severity,
                **(details or {})
            },
            tags=["security", severity]
        )
    
    def _filter_sensitive(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """过滤敏感信息"""
        filtered = {}
        for key, value in data.items():
            if any(field in key.lower() for field in self.config['sensitive_fields']):
                filtered[key] = "***REDACTED***"
            elif isinstance(value, dict):
                filtered[key] = self._filter_sensitive(value)
            else:
                filtered[key] = value
        return filtered
    
    def _get_ip_address(self) -> Optional[str]:
        """获取 IP 地址"""
        # 这里可以实现获取客户端 IP 的逻辑
        # 简化实现返回 None
        return None
    
    def _store_event(self, event: AuditEvent) -> None:
        """存储事件"""
        # 添加到内存
        self.events.append(event)
        
        # 限制内存中的事件数
        if len(self.events) > self.max_events:
            self.events = self.events[-self.max_events:]
        
        # 写入文件
        if self.log_file:
            try:
                with open(self.log_file, 'a', encoding='utf-8') as f:
                    f.write(event.to_json() + '\n')
            except Exception as e:
                logger.error(f"写入审计日志失败: {e}")
    
    def _output_event(self, event: AuditEvent) -> None:
        """输出事件"""
        if not self.enable_console:
            return
        
        # 根据级别输出
        message = (
            f"[AUDIT] {event.timestamp.strftime('%Y-%m-%d %H:%M:%S')} "
            f"{event.level.value.upper()} {event.event_type.value}: "
            f"{event.action} (result={event.result})"
        )
        
        if event.level == AuditLevel.DEBUG:
            logger.debug(message)
        elif event.level == AuditLevel.INFO:
            logger.info(message)
        elif event.level == AuditLevel.WARNING:
            logger.warning(message)
        elif event.level == AuditLevel.ERROR:
            logger.error(message)
        elif event.level == AuditLevel.CRITICAL:
            logger.critical(message)
    
    def query(
        self,
        event_type: Optional[AuditEventType] = None,
        level: Optional[AuditLevel] = None,
        user_id: Optional[str] = None,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
        tags: Optional[List[str]] = None,
        limit: int = 100
    ) -> List[AuditEvent]:
        """
        查询审计事件
        
        Args:
            event_type: 事件类型
            level: 级别
            user_id: 用户 ID
            start_time: 开始时间
            end_time: 结束时间
            tags: 标签
            limit: 限制数量
            
        Returns:
            匹配的事件列表
        """
        results = []
        
        for event in reversed(self.events):  # 从最新的开始
            # 检查条件
            if event_type and event.event_type != event_type:
                continue
            if level and event.level != level:
                continue
            if user_id and event.user_id != user_id:
                continue
            if start_time and event.timestamp < start_time:
                continue
            if end_time and event.timestamp > end_time:
                continue
            if tags and not all(tag in event.tags for tag in tags):
                continue
            
            results.append(event)
            
            if len(results) >= limit:
                break
        
        return results
    
    def get_statistics(self) -> Dict[str, Any]:
        """获取统计信息"""
        stats = {
            "total_events": len(self.events),
            "by_type": {},
            "by_level": {},
            "by_result": {},
            "recent_errors": [],
            "recent_security": []
        }
        
        # 统计事件类型
        for event in self.events:
            event_type = event.event_type.value
            stats["by_type"][event_type] = stats["by_type"].get(event_type, 0) + 1
            
            level = event.level.value
            stats["by_level"][level] = stats["by_level"].get(level, 0) + 1
            
            result = event.result
            stats["by_result"][result] = stats["by_result"].get(result, 0) + 1
        
        # 最近的错误
        error_events = self.query(level=AuditLevel.ERROR, limit=10)
        stats["recent_errors"] = [
            {
                "timestamp": e.timestamp.isoformat(),
                "type": e.event_type.value,
                "action": e.action,
                "resource": e.resource
            }
            for e in error_events
        ]
        
        # 最近的安全事件
        security_events = self.query(event_type=AuditEventType.SECURITY_ALERT, limit=10)
        stats["recent_security"] = [
            {
                "timestamp": e.timestamp.isoformat(),
                "action": e.action,
                "severity": e.details.get("severity", "unknown")
            }
            for e in security_events
        ]
        
        return stats
    
    def export(self, format: str = "json") -> str:
        """
        导出审计日志
        
        Args:
            format: 格式（json, csv）
            
        Returns:
            导出的内容
        """
        if format == "json":
            return json.dumps(
                [event.to_dict() for event in self.events],
                ensure_ascii=False,
                indent=2
            )
        elif format == "csv":
            import csv
            import io
            
            output = io.StringIO()
            writer = csv.DictWriter(
                output,
                fieldnames=[
                    'event_id', 'event_type', 'level', 'timestamp',
                    'user_id', 'action', 'resource', 'result'
                ]
            )
            writer.writeheader()
            
            for event in self.events:
                writer.writerow({
                    'event_id': event.event_id,
                    'event_type': event.event_type.value,
                    'level': event.level.value,
                    'timestamp': event.timestamp.isoformat(),
                    'user_id': event.user_id or '',
                    'action': event.action,
                    'resource': event.resource or '',
                    'result': event.result
                })
            
            return output.getvalue()
        else:
            raise ValueError(f"不支持的格式: {format}")
    
    def clear(self) -> None:
        """清理审计日志"""
        self.events.clear()


# 全局审计日志器实例
_global_audit = AuditLogger()


def get_audit_logger() -> AuditLogger:
    """获取全局审计日志器"""
    return _global_audit