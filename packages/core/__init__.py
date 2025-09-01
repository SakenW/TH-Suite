"""
TH-Suite Core Platform

提供所有工具共享的核心基础设施，包括：
- Framework Layer: IoC容器、配置管理、事件系统、缓存、日志、任务调度
- Data Layer: 数据访问、仓储模式、工作单元模式
- Application Layer: 应用服务、CQRS模式、异常处理
- Infrastructure Layer: 存储、HTTP通信、序列化、加密等
"""

from packages.core.framework.container import IoCContainer
from packages.core.errors import (
    ProjectAlreadyExistsError,
    ProjectError,
    ScanError,
    UnsupportedProjectTypeError,
    ModParsingError,
    ProcessingError,
    ValidationError,
    ConfigurationError,
    THToolsError
)
from packages.core.models import (
    JobStatus,
    JobInfo,
    Segment,
    FileInfo,
    TranslationProject,
    ValidationResult,
    ExportRequest,
    ExportResult
)

__version__ = "2.0.0"
__all__ = [
    "IoCContainer",
    # Error types
    "ProjectAlreadyExistsError",
    "ProjectError", 
    "ScanError",
    "UnsupportedProjectTypeError",
    "ModParsingError",
    "ProcessingError",
    "ValidationError",
    "ConfigurationError",
    "THToolsError",
    # Model types
    "JobStatus",
    "JobInfo", 
    "Segment",
    "FileInfo",
    "TranslationProject",
    "ValidationResult",
    "ExportRequest",
    "ExportResult"
]
