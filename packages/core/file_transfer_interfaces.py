"""
通用文件传输接口定义

定义GameAdapter接口和标准化的服务接口
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from typing import (
    Dict, List, Optional, Union, Any, 
    AsyncIterator, Protocol, runtime_checkable
)

from .file_transfer import TransferTask, TransferResult
from .progress_tracking import TaskProgress, ProgressManager
from .compression import CompressionResult
from .security import SecurityContext


class GameType(Enum):
    """游戏类型"""
    MINECRAFT = "minecraft"
    RUSTED_WARFARE = "rusted_warfare"
    CUSTOM = "custom"


class ResourceType(Enum):
    """资源类型"""
    MOD = "mod"
    RESOURCE_PACK = "resource_pack"
    TEXTURE_PACK = "texture_pack"
    LANGUAGE_PACK = "language_pack"
    DATA_PACK = "data_pack"
    MAP = "map"
    SAVE = "save"
    CONFIG = "config"


@dataclass
class GameResource:
    """游戏资源"""
    resource_id: str
    name: str
    resource_type: ResourceType
    game_type: GameType
    file_path: Path
    size: int
    version: Optional[str] = None
    description: Optional[str] = None
    metadata: Dict[str, Any] = None
    
    def __post_init__(self):
        if self.metadata is None:
            self.metadata = {}


@dataclass
class ProcessingOptions:
    """处理选项"""
    enable_compression: bool = True
    compression_algorithm: str = "zstd"
    verify_integrity: bool = True
    create_backup: bool = True
    parallel_processing: bool = True
    max_workers: int = 4
    custom_options: Dict[str, Any] = None
    
    def __post_init__(self):
        if self.custom_options is None:
            self.custom_options = {}


@dataclass
class ProcessingResult:
    """处理结果"""
    success: bool
    resource: GameResource
    output_path: Optional[Path] = None
    transfer_result: Optional[TransferResult] = None
    compression_result: Optional[CompressionResult] = None
    error_message: Optional[str] = None
    processing_time: float = 0.0
    metadata: Dict[str, Any] = None
    
    def __post_init__(self):
        if self.metadata is None:
            self.metadata = {}


@runtime_checkable
class GameAdapter(Protocol):
    """游戏适配器协议"""
    
    @property
    def game_type(self) -> GameType:
        """获取游戏类型"""
        ...
    
    @property
    def supported_resource_types(self) -> List[ResourceType]:
        """获取支持的资源类型"""
        ...
    
    async def scan_resources(
        self, 
        directory: Path,
        resource_types: Optional[List[ResourceType]] = None
    ) -> List[GameResource]:
        """扫描游戏资源"""
        ...
    
    async def validate_resource(
        self, 
        resource: GameResource
    ) -> bool:
        """验证游戏资源"""
        ...
    
    async def process_resource(
        self, 
        resource: GameResource,
        options: ProcessingOptions,
        progress_manager: Optional[ProgressManager] = None
    ) -> ProcessingResult:
        """处理游戏资源"""
        ...
    
    async def extract_metadata(
        self, 
        resource: GameResource
    ) -> Dict[str, Any]:
        """提取资源元数据"""
        ...


class BaseGameAdapter(GameAdapter):
    """游戏适配器基类"""
    
    def __init__(self, game_type: GameType):
        self._game_type = game_type
        self._supported_types: List[ResourceType] = []
    
    @property
    def game_type(self) -> GameType:
        return self._game_type
    
    @property
    def supported_resource_types(self) -> List[ResourceType]:
        return self._supported_types.copy()
    
    def add_supported_type(self, resource_type: ResourceType) -> None:
        """添加支持的资源类型"""
        if resource_type not in self._supported_types:
            self._supported_types.append(resource_type)
    
    async def scan_resources(
        self, 
        directory: Path,
        resource_types: Optional[List[ResourceType]] = None
    ) -> List[GameResource]:
        """默认资源扫描实现"""
        if not directory.exists() or not directory.is_dir():
            return []
        
        resources = []
        target_types = resource_types or self.supported_resource_types
        
        for file_path in directory.rglob('*'):
            if file_path.is_file():
                resource_type = await self._detect_resource_type(file_path)
                if resource_type and resource_type in target_types:
                    resource = GameResource(
                        resource_id=str(file_path.relative_to(directory)),
                        name=file_path.name,
                        resource_type=resource_type,
                        game_type=self.game_type,
                        file_path=file_path,
                        size=file_path.stat().st_size
                    )
                    resources.append(resource)
        
        return resources
    
    async def validate_resource(self, resource: GameResource) -> bool:
        """默认资源验证实现"""
        return (
            resource.file_path.exists() and
            resource.resource_type in self.supported_resource_types and
            resource.game_type == self.game_type
        )
    
    async def extract_metadata(self, resource: GameResource) -> Dict[str, Any]:
        """默认元数据提取实现"""
        metadata = {
            'file_size': resource.size,
            'file_extension': resource.file_path.suffix,
            'created_time': resource.file_path.stat().st_ctime,
            'modified_time': resource.file_path.stat().st_mtime
        }
        
        # 子类可以重写此方法添加特定的元数据提取逻辑
        return metadata
    
    @abstractmethod
    async def _detect_resource_type(self, file_path: Path) -> Optional[ResourceType]:
        """检测资源类型（由子类实现）"""
        pass
    
    @abstractmethod
    async def process_resource(
        self, 
        resource: GameResource,
        options: ProcessingOptions,
        progress_manager: Optional[ProgressManager] = None
    ) -> ProcessingResult:
        """处理资源（由子类实现）"""
        pass


@runtime_checkable
class FileTransferService(Protocol):
    """文件传输服务协议"""
    
    async def upload_file(
        self, 
        file_path: Path,
        target_url: str,
        security_context: Optional[SecurityContext] = None,
        progress_callback: Optional[callable] = None
    ) -> TransferResult:
        """上传文件"""
        ...
    
    async def download_file(
        self, 
        source_url: str,
        target_path: Path,
        security_context: Optional[SecurityContext] = None,
        progress_callback: Optional[callable] = None
    ) -> TransferResult:
        """下载文件"""
        ...
    
    async def sync_directory(
        self, 
        local_path: Path,
        remote_url: str,
        security_context: Optional[SecurityContext] = None
    ) -> List[TransferResult]:
        """同步目录"""
        ...


@runtime_checkable
class CompressionService(Protocol):
    """压缩服务协议"""
    
    async def compress_file(
        self, 
        input_path: Path,
        output_path: Path,
        algorithm: Optional[str] = None
    ) -> CompressionResult:
        """压缩文件"""
        ...
    
    async def decompress_file(
        self, 
        input_path: Path,
        output_path: Path
    ) -> bool:
        """解压文件"""
        ...
    
    async def compress_directory(
        self, 
        directory_path: Path,
        output_path: Path,
        algorithm: Optional[str] = None
    ) -> CompressionResult:
        """压缩目录"""
        ...


@runtime_checkable
class SecurityService(Protocol):
    """安全服务协议"""
    
    async def verify_file_integrity(
        self, 
        file_path: Path,
        expected_hash: Optional[str] = None
    ) -> bool:
        """验证文件完整性"""
        ...
    
    async def create_security_context(
        self, 
        user_id: str,
        permissions: List[str]
    ) -> SecurityContext:
        """创建安全上下文"""
        ...
    
    async def check_permission(
        self, 
        context: SecurityContext,
        resource_id: str,
        action: str
    ) -> bool:
        """检查权限"""
        ...


@runtime_checkable
class ProgressService(Protocol):
    """进度服务协议"""
    
    async def create_task(
        self, 
        task_id: str,
        title: str,
        total_value: float
    ) -> TaskProgress:
        """创建进度任务"""
        ...
    
    async def update_progress(
        self, 
        task_id: str,
        current_value: float,
        message: Optional[str] = None
    ) -> None:
        """更新进度"""
        ...
    
    async def complete_task(
        self, 
        task_id: str
    ) -> None:
        """完成任务"""
        ...


class UniversalFileProcessor:
    """通用文件处理器"""
    
    def __init__(
        self,
        file_transfer_service: FileTransferService,
        compression_service: CompressionService,
        security_service: SecurityService,
        progress_service: ProgressService
    ):
        self.file_transfer = file_transfer_service
        self.compression = compression_service
        self.security = security_service
        self.progress = progress_service
        self.adapters: Dict[GameType, GameAdapter] = {}
    
    def register_adapter(self, adapter: GameAdapter) -> None:
        """注册游戏适配器"""
        self.adapters[adapter.game_type] = adapter
    
    def get_adapter(self, game_type: GameType) -> Optional[GameAdapter]:
        """获取游戏适配器"""
        return self.adapters.get(game_type)
    
    async def process_game_resources(
        self, 
        game_type: GameType,
        directory: Path,
        options: ProcessingOptions,
        security_context: Optional[SecurityContext] = None
    ) -> List[ProcessingResult]:
        """处理游戏资源"""
        adapter = self.get_adapter(game_type)
        if not adapter:
            raise ValueError(f"不支持的游戏类型: {game_type}")
        
        # 扫描资源
        resources = await adapter.scan_resources(directory)
        
        # 创建进度任务
        task_id = f"process_{game_type.value}_{directory.name}"
        await self.progress.create_task(
            task_id, 
            f"处理{game_type.value}资源", 
            len(resources)
        )
        
        results = []
        for i, resource in enumerate(resources):
            try:
                # 验证资源
                if not await adapter.validate_resource(resource):
                    continue
                
                # 处理资源
                result = await adapter.process_resource(
                    resource, options, self.progress
                )
                results.append(result)
                
                # 更新进度
                await self.progress.update_progress(
                    task_id, i + 1, f"已处理: {resource.name}"
                )
                
            except Exception as e:
                # 记录错误但继续处理其他资源
                error_result = ProcessingResult(
                    success=False,
                    resource=resource,
                    error_message=str(e)
                )
                results.append(error_result)
        
        await self.progress.complete_task(task_id)
        return results
    
    async def batch_transfer_files(
        self, 
        file_paths: List[Path],
        target_url: str,
        security_context: Optional[SecurityContext] = None
    ) -> List[TransferResult]:
        """批量传输文件"""
        task_id = "batch_transfer"
        await self.progress.create_task(
            task_id, "批量文件传输", len(file_paths)
        )
        
        results = []
        for i, file_path in enumerate(file_paths):
            try:
                result = await self.file_transfer.upload_file(
                    file_path, target_url, security_context
                )
                results.append(result)
                
                await self.progress.update_progress(
                    task_id, i + 1, f"已传输: {file_path.name}"
                )
                
            except Exception as e:
                # 创建失败结果
                error_result = TransferResult(
                    task_id=f"transfer_{file_path.name}",
                    success=False,
                    transferred_size=0,
                    total_time=__import__('datetime').timedelta(0),
                    average_speed=0,
                    error=str(e)
                )
                results.append(error_result)
        
        await self.progress.complete_task(task_id)
        return results