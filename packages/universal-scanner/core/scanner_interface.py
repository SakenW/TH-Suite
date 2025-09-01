"""
通用扫描器接口定义

职责：
- 定义标准的扫描器接口和数据模型
- 提供游戏无关的基础类型定义
- 确保不同游戏扫描器的一致性

设计原则：
- 接口分离：定义而不实现
- 类型安全：完整的类型注解
- 扩展性：支持自定义元数据和配置
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Callable, AsyncIterator
from enum import Enum

class ScanStatus(Enum):
    """扫描状态枚举"""
    PENDING = "pending"
    SCANNING = "scanning"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"

class ContentType(Enum):
    """内容类型枚举"""
    FILE = "file"
    MOD = "mod"
    LANGUAGE_FILE = "language_file"
    TRANSLATION_ENTRY = "translation_entry"
    PROJECT = "project"

@dataclass
class ScanRequest:
    """通用扫描请求"""
    scan_id: str
    target_path: Path
    incremental: bool = True
    game_type: str = "unknown"  # 游戏类型标识
    scan_options: Dict[str, Any] = field(default_factory=dict)
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def __post_init__(self):
        """确保路径为Path对象"""
        if isinstance(self.target_path, str):
            self.target_path = Path(self.target_path)

@dataclass 
class ContentItem:
    """通用内容项"""
    content_hash: str
    content_type: ContentType
    name: str
    metadata: Dict[str, Any] = field(default_factory=dict)
    relationships: Dict[str, str] = field(default_factory=dict)  # 与其他内容的关系
    
class ScanProgress:
    """扫描进度信息"""
    def __init__(self, scan_id: str):
        self.scan_id = scan_id
        self.status = ScanStatus.PENDING
        self.progress_percent = 0.0
        self.current_item = ""
        self.processed_count = 0
        self.total_count = 0
        self.start_time = datetime.now()
        self.end_time: Optional[datetime] = None
        self.error_message: Optional[str] = None
        self.metadata: Dict[str, Any] = {}
    
    @property
    def is_complete(self) -> bool:
        return self.status in [ScanStatus.COMPLETED, ScanStatus.FAILED, ScanStatus.CANCELLED]
    
    @property
    def duration_seconds(self) -> float:
        end = self.end_time or datetime.now()
        return (end - self.start_time).total_seconds()

@dataclass
class ScanResult:
    """通用扫描结果"""
    scan_id: str
    status: ScanStatus
    discovered_items: List[ContentItem] = field(default_factory=list)
    statistics: Dict[str, int] = field(default_factory=dict)
    errors: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)
    duration_seconds: float = 0.0
    
    @property
    def success(self) -> bool:
        return self.status == ScanStatus.COMPLETED
    
    def get_items_by_type(self, content_type: ContentType) -> List[ContentItem]:
        """根据类型获取内容项"""
        return [item for item in self.discovered_items if item.content_type == content_type]

class ScannerInterface(ABC):
    """通用扫描器接口"""
    
    @abstractmethod
    async def can_handle(self, request: ScanRequest) -> bool:
        """检查是否能处理此扫描请求"""
        pass
    
    @abstractmethod
    async def scan(
        self, 
        request: ScanRequest,
        progress_callback: Optional[Callable[[ScanProgress], None]] = None
    ) -> AsyncIterator[ScanResult]:
        """执行扫描并产出结果"""
        pass
    
    @abstractmethod
    async def get_scan_progress(self, scan_id: str) -> Optional[ScanProgress]:
        """获取扫描进度"""
        pass
    
    @abstractmethod
    async def cancel_scan(self, scan_id: str) -> bool:
        """取消扫描"""
        pass
    
    @property
    @abstractmethod
    def scanner_name(self) -> str:
        """扫描器名称"""
        pass
    
    @property 
    @abstractmethod
    def supported_game_types(self) -> Set[str]:
        """支持的游戏类型"""
        pass

class GameSpecificHandler(ABC):
    """游戏特定处理器接口"""
    
    @abstractmethod
    async def detect_project_info(self, path: Path) -> Dict[str, Any]:
        """检测项目信息（如组合包信息）"""
        pass
    
    @abstractmethod
    async def extract_content_items(self, file_path: Path) -> List[ContentItem]:
        """从文件提取内容项"""
        pass
    
    @abstractmethod
    async def analyze_file_metadata(self, file_path: Path) -> Dict[str, Any]:
        """分析文件元数据"""
        pass
    
    @property
    @abstractmethod
    def game_type(self) -> str:
        """游戏类型标识"""
        pass

# 进度回调类型别名
ProgressCallback = Callable[[ScanProgress], None]
AsyncProgressCallback = Callable[[ScanProgress], None]