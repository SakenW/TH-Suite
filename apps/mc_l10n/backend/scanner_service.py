"""
MC 扫描服务 - 单一入口

职责：
- 整合通用扫描引擎和MC专属处理器
- 提供REST API接口给前端
- 处理实时进度WebSocket通信
- 维持与现有前端的向后兼容性

设计原则：
- 单一入口：统一的扫描服务接口
- 适配器模式：适配现有的API结构
- 依赖注入：注入通用扫描器和MC处理器
"""

import asyncio
import logging
from pathlib import Path
from typing import Dict, Any, Optional, List
from datetime import datetime

import sys
import os

# Add packages to path
current_dir = os.path.dirname(__file__)
packages_dir = os.path.abspath(os.path.join(current_dir, "..", "..", "..", "packages"))
universal_scanner_dir = os.path.join(packages_dir, "universal-scanner")
game_parsers_dir = os.path.join(packages_dir, "game-parsers")

sys.path.insert(0, universal_scanner_dir)
sys.path.insert(0, game_parsers_dir)

from core.scanner_engine import UniversalScannerEngine
from core.scanner_interface import ScanRequest, ScanProgress, ScanStatus, ContentType
from minecraft.mc_game_handler import MinecraftGameHandler

logger = logging.getLogger(__name__)


class McScannerService:
    """MC 扫描服务 - 统一入口"""
    
    def __init__(self, db_path: str = "mc_localization.db"):
        # 初始化通用扫描引擎
        self.universal_scanner = UniversalScannerEngine(db_path)
        
        # 创建并注册MC游戏处理器
        self.mc_handler = MinecraftGameHandler()
        self.universal_scanner.register_game_handler(self.mc_handler)
        
        # 扫描状态缓存
        self._scan_cache: Dict[str, Dict[str, Any]] = {}
        
        logger.info("🚀 MC Scanner Service initialized")
    
    async def start_scan(
        self, 
        target_path: str,
        incremental: bool = True,
        options: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """启动扫描并返回扫描ID"""
        
        # 创建扫描请求
        scan_request = await self.universal_scanner.create_scan_request(
            target_path=target_path,
            game_type="minecraft",
            incremental=incremental,
            **(options or {})
        )
        
        logger.info(f"🔍 Starting scan: {scan_request.scan_id} for path: {target_path}")
        
        # 在后台执行扫描
        asyncio.create_task(self._execute_scan(scan_request))
        
        # 返回扫描信息
        return {
            "scan_id": scan_request.scan_id,
            "target_path": str(scan_request.target_path),
            "game_type": scan_request.game_type,
            "status": "pending",
            "started_at": datetime.now().isoformat()
        }
    
    async def _execute_scan(self, request: ScanRequest) -> None:
        """执行扫描并处理结果"""
        try:
            logger.info(f"🔍 Starting scan execution for {request.scan_id}")
            
            # 初始化扫描状态
            self._scan_cache[request.scan_id] = {
                "scan_id": request.scan_id,
                "status": "scanning",
                "progress_percent": 0.0,
                "current_item": "初始化扫描...",
                "processed_count": 0,
                "total_count": 0,
                "statistics": {},
                "metadata": {"scan_mode": "增量" if request.incremental else "全量"}
            }
            
            # 定义进度回调
            async def progress_callback(progress: ScanProgress):
                logger.info(f"📊 Progress update: {progress.scan_id} - {progress.progress_percent:.1f}%")
                await self._cache_scan_progress(progress)
            
            # 执行扫描
            scan_completed = False
            async for result in self.universal_scanner.scan(request, progress_callback):
                scan_completed = True
                # 缓存最终结果
                self._scan_cache[request.scan_id] = {
                    "scan_id": result.scan_id,
                    "status": result.status.value,
                    "progress_percent": 100.0,
                    "current_item": "扫描完成",
                    "processed_count": len(result.discovered_items),
                    "total_count": len(result.discovered_items),
                    "discovered_items": len(result.discovered_items),
                    "statistics": result.statistics,
                    "errors": result.errors,
                    "warnings": result.warnings,
                    "duration_seconds": result.duration_seconds,
                    "metadata": result.metadata
                }
                
                logger.info(f"✅ Scan completed: {request.scan_id}, discovered {len(result.discovered_items)} items")
            
            if not scan_completed:
                logger.warning(f"⚠️ Scan {request.scan_id} did not complete normally")
                
        except Exception as e:
            error_msg = f"Scan execution failed: {str(e)}"
            logger.error(f"❌ {error_msg}", exc_info=True)
            
            # 缓存错误状态
            self._scan_cache[request.scan_id] = {
                "scan_id": request.scan_id,
                "status": "failed",
                "progress_percent": 0.0,
                "error_message": error_msg
            }
    
    async def _cache_scan_progress(self, progress: ScanProgress) -> None:
        """缓存扫描进度"""
        # 确保metadata中包含统计信息
        metadata = progress.metadata or {}
        
        # 尝试从progress中提取统计信息
        statistics = metadata.get("statistics", {})
        if not statistics and hasattr(progress, "statistics"):
            statistics = progress.statistics
        
        cache_data = {
            "scan_id": progress.scan_id,
            "status": progress.status.value,
            "progress_percent": progress.progress_percent,
            "current_item": progress.current_item,
            "processed_count": progress.processed_count,
            "total_count": progress.total_count,
            "duration_seconds": progress.duration_seconds,
            "metadata": metadata,
            "statistics": statistics  # 单独存储统计信息
        }
        
        self._scan_cache[progress.scan_id] = cache_data
        
        # 记录进度日志用于调试 - 使用 INFO 级别确保输出
        logger.info(f"📊 Progress cached for {progress.scan_id}: "
                   f"status={progress.status.value}, "
                   f"percent={progress.progress_percent:.1f}%, "
                   f"processed={progress.processed_count}/{progress.total_count}, "
                   f"current_item={progress.current_item}")
        
        # 打印缓存内容用于调试
        logger.info(f"📦 Cache content: {cache_data}")
    
    async def get_scan_status(self, scan_id: str) -> Optional[Dict[str, Any]]:
        """获取扫描状态（兼容现有前端API）"""
        
        logger.info(f"🔍 Getting scan status for: {scan_id}")
        logger.info(f"📦 Current cache keys: {list(self._scan_cache.keys())}")
        
        # 优先从缓存获取
        if scan_id in self._scan_cache:
            cached_status = self._scan_cache[scan_id]
            logger.info(f"✅ Found in cache: {cached_status}")
            
            # 转换为前端期望的扁平格式
            progress_percent = cached_status.get("progress_percent", 0.0)
            processed_count = cached_status.get("processed_count", 0)
            total_count = cached_status.get("total_count", 0)
            
            return {
                "scan_id": scan_id,
                "status": cached_status.get("status", "unknown"),
                "progress": progress_percent,  # 扁平的进度百分比
                "total": total_count,  # 扁平的总数
                "current": processed_count,  # 扁平的当前数
                "processed_files": processed_count,
                "total_files": total_count,
                "current_file": cached_status.get("current_item", ""),
                # 从statistics中提取统计信息
                "total_mods": cached_status.get("statistics", {}).get("total_mods", 0),
                "total_language_files": cached_status.get("statistics", {}).get("total_language_files", 0),
                "total_keys": cached_status.get("statistics", {}).get("total_keys", 0),
                "scan_mode": cached_status.get("metadata", {}).get("scan_mode", "全量"),
                # 保留嵌套的progress对象以支持新格式
                "progress_detail": {
                    "percent": progress_percent,
                    "current_item": cached_status.get("current_item", ""),
                    "processed": processed_count,
                    "total": total_count
                },
                "statistics": cached_status.get("statistics", {}),
                "errors": cached_status.get("errors", []),
                "warnings": cached_status.get("warnings", []),
                "duration_seconds": cached_status.get("duration_seconds", 0.0),
                "metadata": cached_status.get("metadata", {})
            }
        
        # 从通用扫描器获取
        progress = await self.universal_scanner.get_scan_progress(scan_id)
        if progress:
            return {
                "scan_id": scan_id,
                "status": progress.status.value,
                "progress": progress.progress_percent,  # 扁平的进度百分比
                "total": progress.total_count,  # 扁平的总数
                "current": progress.processed_count,  # 扁平的当前数
                "processed_files": progress.processed_count,
                "total_files": progress.total_count,
                "current_file": progress.current_item,
                # 统计信息需要从metadata中提取
                "total_mods": progress.metadata.get("total_mods", 0) if progress.metadata else 0,
                "total_language_files": progress.metadata.get("total_language_files", 0) if progress.metadata else 0,
                "total_keys": progress.metadata.get("total_keys", 0) if progress.metadata else 0,
                "scan_mode": progress.metadata.get("scan_mode", "全量") if progress.metadata else "全量",
                # 保留嵌套的progress对象以支持新格式
                "progress_detail": {
                    "percent": progress.progress_percent,
                    "current_item": progress.current_item,
                    "processed": progress.processed_count,
                    "total": progress.total_count
                },
                "duration_seconds": progress.duration_seconds,
                "metadata": progress.metadata
            }
        
        return None
    
    async def cancel_scan(self, scan_id: str) -> bool:
        """取消扫描"""
        success = await self.universal_scanner.cancel_scan(scan_id)
        
        if success:
            # 更新缓存状态
            if scan_id in self._scan_cache:
                self._scan_cache[scan_id]["status"] = "cancelled"
            
            logger.info(f"❌ Scan cancelled: {scan_id}")
        
        return success
    
    async def get_scan_history(self, limit: int = 50) -> List[Dict[str, Any]]:
        """获取扫描历史"""
        return await self.universal_scanner.get_scan_history(
            game_type="minecraft",
            limit=limit
        )
    
    async def get_modpack_info(self, target_path: str) -> Optional[Dict[str, Any]]:
        """获取组合包信息（不执行完整扫描）"""
        try:
            path_obj = Path(target_path)
            project_info = await self.mc_handler.detect_project_info(path_obj)
            
            return {
                "path": str(path_obj),
                "detected": project_info.get("detected", False),
                "project_info": project_info
            }
            
        except Exception as e:
            logger.error(f"Failed to detect modpack info: {e}")
            return None
    
    async def get_content_items(
        self, 
        content_type: Optional[str] = None,
        limit: Optional[int] = None
    ) -> List[Dict[str, Any]]:
        """获取内容项列表"""
        
        # 转换内容类型
        ct = None
        if content_type:
            try:
                ct = ContentType(content_type)
            except ValueError:
                logger.warning(f"Invalid content type: {content_type}")
        
        items = await self.universal_scanner.db_engine.get_content_items(
            content_type=ct,
            game_type="minecraft",
            limit=limit
        )
        
        # 转换为字典格式
        result = []
        for item in items:
            result.append({
                "content_hash": item.content_hash,
                "content_type": item.content_type.value,
                "name": item.name,
                "metadata": item.metadata,
                "relationships": item.relationships
            })
        
        return result
    
    async def cleanup_old_data(self, days: int = 30) -> Dict[str, Any]:
        """清理旧数据"""
        return await self.universal_scanner.cleanup_old_data(days)
    
    async def get_statistics(self) -> Dict[str, Any]:
        """获取统计信息"""
        
        # 获取内容统计
        mods = await self.get_content_items(content_type="mod")
        language_files = await self.get_content_items(content_type="language_file") 
        translation_entries = await self.get_content_items(content_type="translation_entry")
        
        return {
            "total_mods": len(mods),
            "total_language_files": len(language_files),
            "total_translation_entries": len(translation_entries),
            "supported_game_types": list(self.universal_scanner.get_supported_game_types()),
            "scanner_version": "1.0.0"
        }


# 全局服务实例
_mc_scanner_service: Optional[McScannerService] = None


def get_mc_scanner_service() -> McScannerService:
    """获取MC扫描服务单例"""
    global _mc_scanner_service
    
    if _mc_scanner_service is None:
        _mc_scanner_service = McScannerService()
    
    return _mc_scanner_service


async def init_mc_scanner_service(db_path: str = "mc_localization.db") -> McScannerService:
    """初始化MC扫描服务"""
    global _mc_scanner_service
    
    if _mc_scanner_service is None:
        _mc_scanner_service = McScannerService(db_path)
    
    return _mc_scanner_service