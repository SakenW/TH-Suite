"""
通用扫描器引擎

职责：
- 协调各种游戏特定扫描器
- 管理扫描流程和状态
- 提供统一的扫描器入口
- 处理缓存、WebSocket等通用功能

设计原则：
- 组合模式：组合不同的游戏处理器
- 策略模式：根据游戏类型选择处理策略
- 观察者模式：支持进度监听
"""

import asyncio
import logging
from pathlib import Path
from typing import Dict, List, Optional, Set, Callable, AsyncIterator
from datetime import datetime
import uuid

from .scanner_interface import (
    ScannerInterface, GameSpecificHandler, ScanRequest, ScanResult, 
    ScanProgress, ScanStatus, ContentItem, ContentType, ProgressCallback
)
from .database_engine import UniversalUpsertEngine

logger = logging.getLogger(__name__)

class UniversalScannerEngine(ScannerInterface):
    """通用扫描器引擎 - 单一入口"""
    
    def __init__(self, db_path: str = "universal_scanner.db"):
        self.db_engine = UniversalUpsertEngine(db_path)
        self._game_handlers: Dict[str, GameSpecificHandler] = {}
        self._active_scans: Dict[str, ScanProgress] = {}
        self._progress_callbacks: Dict[str, List[ProgressCallback]] = {}
        
        logger.info("🚀 Universal Scanner Engine initialized")
    
    def register_game_handler(self, handler: GameSpecificHandler) -> None:
        """注册游戏特定处理器"""
        self._game_handlers[handler.game_type] = handler
        logger.info(f"✅ Registered game handler: {handler.game_type}")
    
    def get_supported_game_types(self) -> Set[str]:
        """获取支持的游戏类型"""
        return set(self._game_handlers.keys())
    
    @property
    def scanner_name(self) -> str:
        return "Universal Scanner Engine"
    
    @property
    def supported_game_types(self) -> Set[str]:
        return self.get_supported_game_types()
    
    async def can_handle(self, request: ScanRequest) -> bool:
        """检查是否能处理此扫描请求"""
        # 检查路径是否存在
        if not request.target_path.exists():
            return False
        
        # 检查是否有对应的游戏处理器
        if request.game_type in self._game_handlers:
            return True
        
        # 尝试自动检测游戏类型
        detected_type = await self._detect_game_type(request.target_path)
        if detected_type and detected_type in self._game_handlers:
            request.game_type = detected_type
            return True
        
        return False
    
    async def _detect_game_type(self, path: Path) -> Optional[str]:
        """自动检测游戏类型"""
        # 让每个注册的处理器尝试识别
        for game_type, handler in self._game_handlers.items():
            try:
                project_info = await handler.detect_project_info(path)
                if project_info and project_info.get('detected', False):
                    logger.info(f"🎯 Auto-detected game type: {game_type}")
                    return game_type
            except Exception as e:
                logger.debug(f"Handler {game_type} failed to detect: {e}")
                continue
        
        return None
    
    async def scan(
        self, 
        request: ScanRequest,
        progress_callback: Optional[ProgressCallback] = None
    ) -> AsyncIterator[ScanResult]:
        """执行扫描"""
        
        # 验证请求
        if not await self.can_handle(request):
            yield ScanResult(
                scan_id=request.scan_id,
                status=ScanStatus.FAILED,
                errors=[f"Cannot handle scan request for {request.game_type}"]
            )
            return
        
        # 获取游戏处理器
        handler = self._game_handlers[request.game_type]
        
        # 初始化扫描进度
        progress = ScanProgress(request.scan_id)
        progress.status = ScanStatus.SCANNING
        self._active_scans[request.scan_id] = progress
        
        # 注册进度回调
        if progress_callback:
            self._register_progress_callback(request.scan_id, progress_callback)
        
        try:
            # 开始扫描会话
            await self.db_engine.start_scan_session(
                scan_id=request.scan_id,
                target_path=request.target_path,
                game_type=request.game_type,
                scan_mode="incremental" if request.incremental else "full",
                metadata=request.metadata
            )
            
            # 调用进度回调
            await self._notify_progress(progress)
            
            # 检测项目信息
            logger.info(f"🔍 Detecting project info for: {request.target_path}")
            project_info = await handler.detect_project_info(request.target_path)
            progress.metadata.update(project_info or {})
            progress.progress_percent = 10.0
            await self._notify_progress(progress)
            
            # 发现文件
            logger.info(f"📁 Discovering files in: {request.target_path}")
            discovered_files = await self._discover_files(request.target_path, request.scan_options)
            progress.total_count = len(discovered_files)
            progress.progress_percent = 20.0
            await self._notify_progress(progress)
            
            # 处理文件
            logger.info(f"⚙️ Processing {len(discovered_files)} files")
            all_content_items = []
            
            for i, file_path in enumerate(discovered_files):
                # 检查是否被取消
                if progress.status == ScanStatus.CANCELLED:
                    break
                
                progress.current_item = file_path.name
                progress.processed_count = i + 1
                progress.progress_percent = 20.0 + (i / len(discovered_files)) * 70.0
                await self._notify_progress(progress)
                
                try:
                    # 使用游戏处理器提取内容
                    content_items = await handler.extract_content_items(file_path)
                    
                    # UPSERT到数据库
                    for item in content_items:
                        await self.db_engine.upsert_content_item(item)
                        await self.db_engine.record_scan_discovery(
                            request.scan_id, item.content_hash, item.content_type
                        )
                    
                    all_content_items.extend(content_items)
                    
                except Exception as e:
                    error_msg = f"Failed to process {file_path}: {str(e)}"
                    logger.error(error_msg)
                    progress.metadata.setdefault('errors', []).append(error_msg)
                
                # 定期更新数据库进度
                if i % 10 == 0:
                    await self.db_engine.update_scan_progress(progress)
                
                # 让出控制权
                if i % 5 == 0:
                    await asyncio.sleep(0.01)
            
            # 完成扫描
            progress.status = ScanStatus.COMPLETED if progress.status != ScanStatus.CANCELLED else ScanStatus.CANCELLED
            progress.progress_percent = 100.0
            progress.end_time = datetime.now()
            await self.db_engine.update_scan_progress(progress)
            await self._notify_progress(progress)
            
            # 获取统计信息
            statistics = await self.db_engine.get_scan_statistics(request.scan_id)
            
            # 创建最终结果
            result = ScanResult(
                scan_id=request.scan_id,
                status=progress.status,
                discovered_items=all_content_items,
                statistics=statistics,
                errors=progress.metadata.get('errors', []),
                warnings=progress.metadata.get('warnings', []),
                metadata=progress.metadata,
                duration_seconds=progress.duration_seconds
            )
            
            logger.info(f"✅ Scan completed: {request.scan_id} - {len(all_content_items)} items discovered")
            yield result
            
        except Exception as e:
            error_msg = f"Scan failed: {str(e)}"
            logger.error(error_msg)
            
            progress.status = ScanStatus.FAILED
            progress.error_message = error_msg
            progress.end_time = datetime.now()
            await self.db_engine.update_scan_progress(progress)
            await self._notify_progress(progress)
            
            yield ScanResult(
                scan_id=request.scan_id,
                status=ScanStatus.FAILED,
                errors=[error_msg],
                duration_seconds=progress.duration_seconds
            )
        
        finally:
            # 清理资源
            self._cleanup_scan(request.scan_id)
    
    async def _discover_files(self, target_path: Path, scan_options: Dict) -> List[Path]:
        """发现需要处理的文件"""
        discovered_files = []
        
        # 配置文件扩展名过滤
        extensions = scan_options.get('file_extensions', ['.jar', '.zip'])
        max_depth = scan_options.get('max_depth', 10)
        
        def should_include_file(file_path: Path, depth: int) -> bool:
            # 深度检查
            if depth > max_depth:
                return False
            
            # 扩展名检查
            if extensions and file_path.suffix.lower() not in extensions:
                return False
            
            # 大小检查
            max_size = scan_options.get('max_file_size_mb')
            if max_size:
                try:
                    size_mb = file_path.stat().st_size / (1024 * 1024)
                    if size_mb > max_size:
                        return False
                except:
                    return False
            
            return True
        
        def scan_directory(path: Path, depth: int = 0):
            try:
                for item in path.iterdir():
                    if item.is_file() and should_include_file(item, depth):
                        discovered_files.append(item)
                    elif item.is_dir() and depth < max_depth:
                        scan_directory(item, depth + 1)
            except PermissionError:
                logger.warning(f"Permission denied: {path}")
        
        if target_path.is_file():
            if should_include_file(target_path, 0):
                discovered_files.append(target_path)
        else:
            scan_directory(target_path)
        
        logger.info(f"📋 Discovered {len(discovered_files)} files to process")
        return discovered_files
    
    def _register_progress_callback(self, scan_id: str, callback: ProgressCallback) -> None:
        """注册进度回调"""
        if scan_id not in self._progress_callbacks:
            self._progress_callbacks[scan_id] = []
        self._progress_callbacks[scan_id].append(callback)
    
    async def _notify_progress(self, progress: ScanProgress) -> None:
        """通知进度回调"""
        callbacks = self._progress_callbacks.get(progress.scan_id, [])
        for callback in callbacks:
            try:
                if asyncio.iscoroutinefunction(callback):
                    await callback(progress)
                else:
                    callback(progress)
            except Exception as e:
                logger.error(f"Progress callback error: {e}")
    
    def _cleanup_scan(self, scan_id: str) -> None:
        """清理扫描资源"""
        self._active_scans.pop(scan_id, None)
        self._progress_callbacks.pop(scan_id, None)
    
    async def get_scan_progress(self, scan_id: str) -> Optional[ScanProgress]:
        """获取扫描进度"""
        # 优先返回内存中的进度
        if scan_id in self._active_scans:
            return self._active_scans[scan_id]
        
        # 从数据库获取
        return await self.db_engine.get_scan_progress(scan_id)
    
    async def cancel_scan(self, scan_id: str) -> bool:
        """取消扫描"""
        if scan_id in self._active_scans:
            progress = self._active_scans[scan_id]
            progress.status = ScanStatus.CANCELLED
            progress.end_time = datetime.now()
            await self.db_engine.update_scan_progress(progress)
            await self._notify_progress(progress)
            logger.info(f"❌ Scan cancelled: {scan_id}")
            return True
        return False
    
    async def create_scan_request(
        self, 
        target_path: str | Path,
        game_type: str = "auto",
        incremental: bool = True,
        **options
    ) -> ScanRequest:
        """创建扫描请求的便捷方法"""
        if isinstance(target_path, str):
            target_path = Path(target_path)
        
        scan_id = str(uuid.uuid4())
        
        return ScanRequest(
            scan_id=scan_id,
            target_path=target_path,
            incremental=incremental,
            game_type=game_type,
            scan_options=options
        )
    
    async def get_scan_history(
        self,
        game_type: Optional[str] = None,
        limit: int = 50
    ) -> List[Dict]:
        """获取扫描历史"""
        # 这里可以实现从数据库获取扫描历史的逻辑
        # 暂时返回空列表
        return []
    
    async def cleanup_old_data(self, days: int = 30) -> Dict[str, int]:
        """清理旧数据"""
        sessions_deleted = await self.db_engine.cleanup_old_sessions(days)
        
        return {
            "sessions_deleted": sessions_deleted,
            "cleanup_date": datetime.now().isoformat()
        }