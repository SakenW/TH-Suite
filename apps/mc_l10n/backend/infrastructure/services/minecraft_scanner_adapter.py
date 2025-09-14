"""
Minecraft扫描器适配器
连接Universal Scanner引擎与Minecraft特定扫描器
"""

import sys
from pathlib import Path
import asyncio
import logging
import uuid
from typing import Any, Dict, List

# 添加包路径到Python路径
project_root = Path(__file__).parents[5]  # 向上5层到TH-Suite
packages_path = project_root / "packages"
sys.path.insert(0, str(packages_path))

try:
    from universal_scanner.core.scanner_engine import UniversalScannerEngine
    from universal_scanner.core.scanner_interface import (
        ScanRequest, 
        GameSpecificHandler, 
        ContentItem, 
        ContentType,
        ScanProgress
    )
    from adapters.minecraft.scanner import MinecraftProjectScanner
except ImportError as e:
    logger.error(f"无法导入Universal Scanner模块: {e}")
    # 临时回退到模拟实现
    UniversalScannerEngine = None
    GameSpecificHandler = None
    ContentItem = None
    ContentType = None
    ScanProgress = None
    MinecraftProjectScanner = None

logger = logging.getLogger(__name__)


if GameSpecificHandler is None:
    # 模拟GameSpecificHandler基类
    class GameSpecificHandler:
        @property
        def game_type(self) -> str:
            return "unknown"
        
        async def detect_project_info(self, path: Path) -> Dict[str, Any]:
            return {"detected": False}
        
        async def extract_content_items(self, file_path: Path) -> List[Any]:
            return []
        
        async def analyze_file_metadata(self, file_path: Path) -> Dict[str, Any]:
            return {}

class MinecraftGameHandler(GameSpecificHandler):
    """Minecraft游戏处理器，实现Universal Scanner的GameSpecificHandler接口"""
    
    def __init__(self):
        self.minecraft_scanner = MinecraftProjectScanner()
        
    @property
    def game_type(self) -> str:
        """游戏类型标识"""
        return "minecraft"
    
    async def detect_project_info(self, path: Path) -> Dict[str, Any]:
        """检测项目信息"""
        try:
            # 使用Minecraft扫描器检测项目类型
            project_type = await self.minecraft_scanner._detect_project_type(path)
            logger.info(f"检测到Minecraft项目类型: {project_type.value}")
            
            return {
                "detected": True,
                "project_type": project_type.value,
                "game_type": "minecraft",
                "path": str(path),
                "name": path.name
            }
        except Exception as e:
            logger.debug(f"Minecraft项目检测失败 {path}: {e}")
            return {"detected": False}
    
    async def extract_content_items(self, file_path: Path) -> List[ContentItem]:
        """从文件提取内容项"""
        content_items = []
        
        try:
            if file_path.suffix.lower() in ['.jar', '.zip']:
                # 处理MOD文件
                content_items.append(ContentItem(
                    content_hash=str(hash(str(file_path))),
                    content_type=ContentType.MOD,
                    name=file_path.stem,
                    metadata={
                        "file_path": str(file_path),
                        "file_size": file_path.stat().st_size,
                        "file_type": "jar" if file_path.suffix.lower() == '.jar' else "zip"
                    }
                ))
                
                # 模拟从JAR中提取的语言文件
                # 在真实实现中，这里应该调用JAR解析器
                content_items.append(ContentItem(
                    content_hash=str(hash(f"{file_path}_lang")),
                    content_type=ContentType.LANGUAGE_FILE,
                    name=f"{file_path.stem}_lang",
                    metadata={
                        "parent_mod": file_path.stem,
                        "language_code": "en_us",
                        "entries_count": 100
                    },
                    relationships={"parent_mod": content_items[0].content_hash if content_items else ""}
                ))
                
        except Exception as e:
            logger.error(f"提取内容项失败 {file_path}: {e}")
            
        return content_items
    
    async def analyze_file_metadata(self, file_path: Path) -> Dict[str, Any]:
        """分析文件元数据"""
        try:
            stat = file_path.stat()
            return {
                "size": stat.st_size,
                "modified": stat.st_mtime,
                "extension": file_path.suffix,
                "name": file_path.name,
                "is_mod": file_path.suffix.lower() in ['.jar', '.zip']
            }
        except Exception as e:
            logger.error(f"分析文件元数据失败 {file_path}: {e}")
            return {}


class MinecraftUniversalScannerService:
    """基于Universal Scanner引擎的Minecraft扫描服务"""
    
    def __init__(self, db_path: str = "data/universal_scanner.db"):
        self.scanner_engine = UniversalScannerEngine(db_path)
        self.minecraft_handler = MinecraftGameHandler()
        
        # 注册Minecraft游戏处理器
        self.scanner_engine.register_game_handler(self.minecraft_handler)
        
        logger.info("Minecraft Universal Scanner Service 已初始化")
    
    async def start_scan(
        self,
        target_path: str,
        incremental: bool = True,
        scan_options: Dict[str, Any] = None
    ) -> Dict[str, Any]:
        """启动扫描"""
        try:
            # 创建扫描请求
            scan_request = await self.scanner_engine.create_scan_request(
                target_path=target_path,
                game_type="minecraft",
                incremental=incremental,
                **(scan_options or {})
            )
            
            logger.info(f"🚀 启动Universal Scanner扫描: {target_path}")
            logger.info(f"📋 扫描ID: {scan_request.scan_id}")
            
            # 执行扫描（异步生成器，取第一个结果）
            scan_results = []
            async for result in self.scanner_engine.scan(scan_request):
                scan_results.append(result)
                break  # 取第一个结果
            
            if scan_results:
                result = scan_results[0]
                return {
                    "success": True,
                    "scan_id": result.scan_id,
                    "status": result.status.value,
                    "discovered_items_count": len(result.discovered_items),
                    "statistics": result.statistics,
                    "metadata": result.metadata,
                    "duration_seconds": result.duration_seconds
                }
            else:
                return {
                    "success": False,
                    "error": "扫描未返回结果",
                    "scan_id": scan_request.scan_id
                }
                
        except Exception as e:
            logger.error(f"扫描失败: {e}")
            return {
                "success": False,
                "error": str(e),
                "scan_id": str(uuid.uuid4())
            }
    
    async def get_scan_status(self, scan_id: str) -> Dict[str, Any]:
        """获取扫描状态"""
        try:
            progress = await self.scanner_engine.get_scan_progress(scan_id)
            if progress:
                return {
                    "success": True,
                    "scan_id": scan_id,
                    "status": progress.status.value,
                    "progress": progress.progress_percent,
                    "current_item": progress.current_item,
                    "processed_count": progress.processed_count,
                    "total_count": progress.total_count,
                    "duration_seconds": progress.duration_seconds,
                    "error_message": progress.error_message
                }
            else:
                return {
                    "success": False,
                    "error": "扫描记录不存在",
                    "scan_id": scan_id
                }
        except Exception as e:
            logger.error(f"获取扫描状态失败: {e}")
            return {
                "success": False,
                "error": str(e),
                "scan_id": scan_id
            }
    
    async def cancel_scan(self, scan_id: str) -> bool:
        """取消扫描"""
        try:
            return await self.scanner_engine.cancel_scan(scan_id)
        except Exception as e:
            logger.error(f"取消扫描失败: {e}")
            return False
    
    async def get_content_items(self, content_type: str, limit: int = 100) -> List[Dict[str, Any]]:
        """获取内容项（通过数据库引擎）"""
        try:
            # 这里应该通过数据库引擎获取内容项
            # 暂时返回空列表，后续实现
            return []
        except Exception as e:
            logger.error(f"获取内容项失败: {e}")
            return []


# 全局实例
_minecraft_scanner_service: MinecraftUniversalScannerService = None


def get_minecraft_scanner_service(db_path: str = "data/universal_scanner.db") -> MinecraftUniversalScannerService:
    """获取Minecraft扫描服务实例"""
    global _minecraft_scanner_service
    if _minecraft_scanner_service is None:
        _minecraft_scanner_service = MinecraftUniversalScannerService(db_path)
    return _minecraft_scanner_service