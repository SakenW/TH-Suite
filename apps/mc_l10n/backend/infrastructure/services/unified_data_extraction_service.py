"""
统一数据提取服务
集成游戏专属数据提取器，提供统一的提取接口
支持与扫描系统、CAS缓存和事件系统的深度集成
"""

import asyncio
import hashlib
import structlog
import time
import uuid
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Any, Optional, Set

from .game_data_extractors import (
    ExtractorRegistry, GameType, 
    MinecraftDataExtractor, RimWorldDataExtractor, FactorioDataExtractor,
    ExtractionResult, LanguageFile
)

logger = structlog.get_logger(__name__)


class UnifiedDataExtractionService:
    """统一数据提取服务"""
    
    def __init__(self, db_path: str = "data/mc_l10n.db"):
        self.db_path = db_path
        self._initialize_extractors()
        self._active_extractions: Dict[str, Dict[str, Any]] = {}
        
        logger.info("统一数据提取服务已初始化")
    
    def _initialize_extractors(self):
        """初始化所有游戏数据提取器"""
        # 注册所有支持的游戏提取器
        ExtractorRegistry.register(GameType.MINECRAFT, MinecraftDataExtractor(self.db_path))
        ExtractorRegistry.register(GameType.RIMWORLD, RimWorldDataExtractor(self.db_path))
        ExtractorRegistry.register(GameType.FACTORIO, FactorioDataExtractor(self.db_path))
        
        logger.info(f"已注册 {len(ExtractorRegistry.get_all_extractors())} 个游戏数据提取器")
    
    async def extract_from_scan_results(
        self, 
        discovered_items: List[Dict[str, Any]],
        extraction_options: Dict[str, Any] = None
    ) -> Dict[str, Any]:
        """从扫描结果中提取翻译数据"""
        extraction_id = f"extract_{uuid.uuid4().hex[:8]}"
        start_time = time.time()
        
        if not extraction_options:
            extraction_options = {}
        
        logger.info(f"🚀 开始统一数据提取: {extraction_id}")
        
        # 初始化提取状态
        extraction_state = {
            "extraction_id": extraction_id,
            "status": "extracting",
            "progress": 0,
            "started_at": datetime.now().isoformat(),
            "current_game": "",
            "processed_games": 0,
            "total_games": 0,
            "results": {},
            "statistics": {
                "total_language_files": 0,
                "total_translation_entries": 0,
                "supported_games": [],
                "unsupported_items": 0
            }
        }
        
        self._active_extractions[extraction_id] = extraction_state
        
        try:
            # 按游戏类型分组扫描结果
            game_groups = await self._group_items_by_game(discovered_items)
            extraction_state["total_games"] = len(game_groups)
            
            # 并行处理各个游戏
            extraction_tasks = []
            for game_type, items in game_groups.items():
                if items:
                    task = self._extract_game_data(
                        game_type, items, extraction_id, extraction_options
                    )
                    extraction_tasks.append(task)
            
            # 等待所有提取任务完成
            if extraction_tasks:
                game_results = await asyncio.gather(*extraction_tasks, return_exceptions=True)
                
                # 合并结果
                for i, result in enumerate(game_results):
                    if isinstance(result, Exception):
                        logger.error(f"游戏数据提取失败: {result}")
                        continue
                    
                    game_type = list(game_groups.keys())[i]
                    extraction_state["results"][game_type.value] = result
                    
                    if result.get("success"):
                        stats = result.get("statistics", {})
                        extraction_state["statistics"]["total_language_files"] += stats.get("files_processed", 0)
                        extraction_state["statistics"]["total_translation_entries"] += stats.get("total_entries", 0)
                        extraction_state["statistics"]["supported_games"].append(game_type.value)
            
            # 处理不支持的项目
            unsupported_count = len(discovered_items) - sum(len(items) for items in game_groups.values())
            extraction_state["statistics"]["unsupported_items"] = unsupported_count
            
            # 完成提取
            extraction_state["status"] = "completed"
            extraction_state["progress"] = 100
            extraction_state["completed_at"] = datetime.now().isoformat()
            
            duration_ms = int((time.time() - start_time) * 1000)
            
            logger.info(
                f"✅ 统一数据提取完成: {extraction_id} "
                f"({extraction_state['statistics']['total_language_files']} 语言文件, "
                f"{extraction_state['statistics']['total_translation_entries']} 翻译条目, "
                f"{duration_ms}ms)"
            )
            
            return {
                "success": True,
                "extraction_id": extraction_id,
                "statistics": extraction_state["statistics"],
                "results": extraction_state["results"],
                "duration_ms": duration_ms
            }
            
        except Exception as e:
            logger.error(f"统一数据提取失败 {extraction_id}: {e}")
            extraction_state["status"] = "failed"
            extraction_state["error"] = str(e)
            
            return {
                "success": False,
                "extraction_id": extraction_id,
                "error": str(e)
            }
    
    async def extract_incremental(
        self, 
        discovered_items: List[Dict[str, Any]],
        last_extraction_cache: Dict[str, str] = None
    ) -> Dict[str, Any]:
        """增量数据提取"""
        if not last_extraction_cache:
            last_extraction_cache = await self._load_keyset_cache()
        
        extraction_id = f"incremental_{uuid.uuid4().hex[:8]}"
        logger.info(f"🔄 开始增量数据提取: {extraction_id}")
        
        # 按游戏类型分组
        game_groups = await self._group_items_by_game(discovered_items)
        
        extraction_results = {}
        total_processed = 0
        
        for game_type, items in game_groups.items():
            if not items:
                continue
                
            extractor = ExtractorRegistry.get_extractor(game_type)
            if not extractor:
                continue
            
            try:
                result = await extractor.extract_incremental(items, last_extraction_cache)
                extraction_results[game_type.value] = result
                total_processed += len(result.language_files)
                
                # 更新缓存
                for lang_file in result.language_files:
                    cache_key = f"{lang_file.carrier_uid}:{lang_file.relative_path}"
                    last_extraction_cache[cache_key] = lang_file.keyset_hash
                
            except Exception as e:
                logger.error(f"增量提取失败 {game_type.value}: {e}")
                extraction_results[game_type.value] = {
                    "success": False,
                    "error": str(e)
                }
        
        # 保存更新的缓存
        await self._save_keyset_cache(last_extraction_cache)
        
        return {
            "success": True,
            "extraction_id": extraction_id,
            "processed_files": total_processed,
            "results": extraction_results,
            "cache_updated": True
        }
    
    async def _extract_game_data(
        self, 
        game_type: GameType, 
        items: List[Dict[str, Any]],
        extraction_id: str,
        options: Dict[str, Any]
    ) -> Dict[str, Any]:
        """提取特定游戏的数据"""
        extractor = ExtractorRegistry.get_extractor(game_type)
        if not extractor:
            return {
                "success": False,
                "error": f"不支持的游戏类型: {game_type.value}"
            }
        
        try:
            # 更新提取状态
            extraction_state = self._active_extractions.get(extraction_id)
            if extraction_state:
                extraction_state["current_game"] = game_type.value
                extraction_state["progress"] = (extraction_state["processed_games"] / extraction_state["total_games"]) * 100
            
            # 执行提取
            result = await extractor.extract_from_discovered_items(items)
            
            if result.success:
                # 保存到数据库
                save_result = await extractor._save_to_database(result.language_files)
                
                # 发送事件
                session_id = f"{extraction_id}_{game_type.value}"
                for lang_file in result.language_files:
                    await extractor._emit_lang_upsert_event(lang_file, session_id)
                
                # 更新状态
                if extraction_state:
                    extraction_state["processed_games"] += 1
                
                return {
                    "success": True,
                    "game_type": game_type.value,
                    "language_files": len(result.language_files),
                    "statistics": result.statistics,
                    "database_save": save_result,
                    "duration_ms": result.duration_ms
                }
            else:
                return {
                    "success": False,
                    "game_type": game_type.value,
                    "errors": result.errors
                }
                
        except Exception as e:
            logger.error(f"游戏数据提取异常 {game_type.value}: {e}")
            return {
                "success": False,
                "game_type": game_type.value,
                "error": str(e)
            }
    
    async def _group_items_by_game(
        self, 
        discovered_items: List[Dict[str, Any]]
    ) -> Dict[GameType, List[Dict[str, Any]]]:
        """按游戏类型分组扫描项目"""
        game_groups = {
            GameType.MINECRAFT: [],
            GameType.RIMWORLD: [],
            GameType.FACTORIO: []
        }
        
        for item in discovered_items:
            # 检测游戏类型
            detected_game = ExtractorRegistry.detect_game_type([item])
            
            if detected_game and detected_game in game_groups:
                game_groups[detected_game].append(item)
            else:
                # 尝试基于文件扩展名或路径特征进行分组
                path = item.get("path", "")
                
                if any(pattern in path.lower() for pattern in [".jar", ".zip", "mods/", "assets/", "/lang/"]):
                    game_groups[GameType.MINECRAFT].append(item)
                elif any(pattern in path.lower() for pattern in ["definjected/", "languages/", "keyed/"]):
                    game_groups[GameType.RIMWORLD].append(item)
                elif any(pattern in path.lower() for pattern in ["/locale/", ".cfg"]):
                    game_groups[GameType.FACTORIO].append(item)
        
        # 移除空的分组
        return {k: v for k, v in game_groups.items() if v}
    
    async def get_extraction_status(self, extraction_id: str) -> Dict[str, Any]:
        """获取提取状态"""
        if extraction_id in self._active_extractions:
            return {
                "success": True,
                **self._active_extractions[extraction_id]
            }
        else:
            return {
                "success": False,
                "error": "提取记录不存在"
            }
    
    async def _load_keyset_cache(self) -> Dict[str, str]:
        """从CAS系统加载键集缓存"""
        try:
            # TODO: 集成CAS缓存系统
            # 这里可以从ops_cas_objects表中加载缓存数据
            return {}
        except Exception as e:
            logger.warning(f"键集缓存加载失败: {e}")
            return {}
    
    async def _save_keyset_cache(self, cache: Dict[str, str]):
        """保存键集缓存到CAS系统"""
        try:
            # TODO: 集成CAS缓存系统
            # 这里可以将缓存数据保存到ops_cas_objects表
            pass
        except Exception as e:
            logger.warning(f"键集缓存保存失败: {e}")
    
    async def extract_from_single_file(
        self, 
        file_path: str, 
        game_type: GameType = None,
        carrier_info: Dict[str, Any] = None
    ) -> Dict[str, Any]:
        """从单个文件提取翻译数据"""
        path = Path(file_path)
        
        if not path.exists():
            return {
                "success": False,
                "error": f"文件不存在: {file_path}"
            }
        
        # 自动检测游戏类型
        if not game_type:
            game_type = ExtractorRegistry.detect_game_type([{"path": file_path}])
        
        if not game_type:
            return {
                "success": False,
                "error": "无法识别游戏类型"
            }
        
        extractor = ExtractorRegistry.get_extractor(game_type)
        if not extractor:
            return {
                "success": False,
                "error": f"不支持的游戏类型: {game_type.value}"
            }
        
        try:
            if not carrier_info:
                carrier_info = {
                    "mod_id": path.stem,
                    "type": "manual"
                }
            
            language_files = await extractor.extract_from_file(path, carrier_info)
            
            if language_files:
                # 保存到数据库
                save_result = await extractor._save_to_database(language_files)
                
                return {
                    "success": True,
                    "game_type": game_type.value,
                    "language_files": len(language_files),
                    "total_entries": sum(len(lf.entries) for lf in language_files),
                    "database_save": save_result
                }
            else:
                return {
                    "success": False,
                    "error": "未发现翻译数据"
                }
                
        except Exception as e:
            logger.error(f"单文件提取失败 {file_path}: {e}")
            return {
                "success": False,
                "error": str(e)
            }
    
    def get_supported_games(self) -> List[str]:
        """获取支持的游戏列表"""
        return [game_type.value for game_type in ExtractorRegistry.get_all_extractors().keys()]
    
    async def get_extraction_statistics(self) -> Dict[str, Any]:
        """获取提取统计信息"""
        try:
            from infrastructure.repositories.repository_factory import get_repository_factory
            
            factory = get_repository_factory()
            lang_file_repo = factory.get_core_language_file_repo()
            entry_repo = factory.get_core_translation_entry_repo()
            
            return {
                "language_files": lang_file_repo.get_statistics(),
                "translation_entries": entry_repo.get_statistics(),
                "supported_games": self.get_supported_games()
            }
            
        except Exception as e:
            logger.error(f"获取提取统计失败: {e}")
            return {
                "error": str(e)
            }


# 全局服务实例
_unified_extraction_service: UnifiedDataExtractionService = None


def get_unified_extraction_service(db_path: str = "data/mc_l10n.db") -> UnifiedDataExtractionService:
    """获取统一数据提取服务实例"""
    global _unified_extraction_service
    if _unified_extraction_service is None:
        _unified_extraction_service = UnifiedDataExtractionService(db_path)
    return _unified_extraction_service