"""
进度监控配置模块

定义进度监控系统的各种配置选项
"""

from dataclasses import dataclass
from typing import Dict, Any, Optional


@dataclass
class ProgressConfig:
    """进度监控配置"""
    
    # 事件配置
    max_event_history: int = 1000  # 最大事件历史记录数
    milestone_interval: float = 10.0  # 里程碑间隔（百分比）
    
    # 清理配置
    auto_cleanup_interval: float = 300.0  # 自动清理间隔（秒）
    completed_task_retention: float = 3600.0  # 已完成任务保留时间（秒）
    
    # 性能配置
    metrics_update_interval: float = 5.0  # 指标更新间隔（秒）
    speed_calculation_window: int = 10  # 速度计算窗口（秒）
    
    # WebSocket配置
    websocket_enabled: bool = True
    websocket_port: int = 8001
    websocket_path: str = "/ws/progress"
    
    # 存储配置
    persistence_enabled: bool = False
    storage_backend: str = "memory"  # memory, database, file
    storage_config: Dict[str, Any] = None
    
    # 日志配置
    log_level: str = "INFO"
    log_progress_events: bool = True
    log_milestone_events: bool = True
    
    # 通知配置
    enable_notifications: bool = True
    notification_throttle: float = 1.0  # 通知节流间隔（秒）
    
    # 高级配置
    max_concurrent_tasks: int = 100
    enable_task_hierarchy: bool = True
    enable_speed_optimization: bool = True
    
    def __post_init__(self):
        if self.storage_config is None:
            self.storage_config = {}
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            'max_event_history': self.max_event_history,
            'milestone_interval': self.milestone_interval,
            'auto_cleanup_interval': self.auto_cleanup_interval,
            'completed_task_retention': self.completed_task_retention,
            'metrics_update_interval': self.metrics_update_interval,
            'speed_calculation_window': self.speed_calculation_window,
            'websocket_enabled': self.websocket_enabled,
            'websocket_port': self.websocket_port,
            'websocket_path': self.websocket_path,
            'persistence_enabled': self.persistence_enabled,
            'storage_backend': self.storage_backend,
            'storage_config': self.storage_config,
            'log_level': self.log_level,
            'log_progress_events': self.log_progress_events,
            'log_milestone_events': self.log_milestone_events,
            'enable_notifications': self.enable_notifications,
            'notification_throttle': self.notification_throttle,
            'max_concurrent_tasks': self.max_concurrent_tasks,
            'enable_task_hierarchy': self.enable_task_hierarchy,
            'enable_speed_optimization': self.enable_speed_optimization
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'ProgressConfig':
        """从字典创建配置"""
        return cls(**data)


# 预定义配置模板
class ProgressConfigTemplates:
    """进度配置模板"""
    
    @staticmethod
    def lightweight() -> ProgressConfig:
        """轻量级配置"""
        return ProgressConfig(
            max_event_history=100,
            auto_cleanup_interval=600.0,
            completed_task_retention=1800.0,
            metrics_update_interval=10.0,
            websocket_enabled=False,
            persistence_enabled=False,
            log_progress_events=False,
            enable_notifications=False
        )
    
    @staticmethod
    def development() -> ProgressConfig:
        """开发环境配置"""
        return ProgressConfig(
            max_event_history=500,
            milestone_interval=5.0,
            auto_cleanup_interval=300.0,
            completed_task_retention=1800.0,
            metrics_update_interval=2.0,
            websocket_enabled=True,
            websocket_port=8001,
            persistence_enabled=False,
            log_level="DEBUG",
            log_progress_events=True,
            log_milestone_events=True,
            enable_notifications=True,
            notification_throttle=0.5
        )
    
    @staticmethod
    def production() -> ProgressConfig:
        """生产环境配置"""
        return ProgressConfig(
            max_event_history=2000,
            milestone_interval=10.0,
            auto_cleanup_interval=600.0,
            completed_task_retention=7200.0,
            metrics_update_interval=5.0,
            websocket_enabled=True,
            websocket_port=8001,
            persistence_enabled=True,
            storage_backend="database",
            log_level="INFO",
            log_progress_events=False,
            log_milestone_events=True,
            enable_notifications=True,
            notification_throttle=1.0,
            max_concurrent_tasks=200
        )
    
    @staticmethod
    def high_performance() -> ProgressConfig:
        """高性能配置"""
        return ProgressConfig(
            max_event_history=5000,
            milestone_interval=20.0,
            auto_cleanup_interval=1200.0,
            completed_task_retention=3600.0,
            metrics_update_interval=1.0,
            websocket_enabled=True,
            persistence_enabled=True,
            storage_backend="memory",
            log_level="WARNING",
            log_progress_events=False,
            log_milestone_events=False,
            enable_notifications=True,
            notification_throttle=2.0,
            max_concurrent_tasks=500,
            enable_speed_optimization=True
        )
    
    @staticmethod
    def minimal() -> ProgressConfig:
        """最小化配置"""
        return ProgressConfig(
            max_event_history=50,
            milestone_interval=25.0,
            auto_cleanup_interval=0,  # 禁用自动清理
            metrics_update_interval=0,  # 禁用指标更新
            websocket_enabled=False,
            persistence_enabled=False,
            log_progress_events=False,
            log_milestone_events=False,
            enable_notifications=False,
            max_concurrent_tasks=10
        )