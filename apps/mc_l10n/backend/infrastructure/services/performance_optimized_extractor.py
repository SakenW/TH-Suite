"""
性能优化的数据提取器
实现增量提取、并行处理、内存优化和缓存机制
支持大规模翻译数据的高效处理
"""

import asyncio
import hashlib
import structlog
import time
import uuid
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Any, Optional, Set, Tuple, Generator
import psutil
import gc

from .unified_data_extraction_service import UnifiedDataExtractionService
from .cas_keyset_cache_service import get_cas_keyset_cache_service
from .lang_upsert_event_handler import get_lang_upsert_event_handler
from .game_data_extractors import GameType, ExtractorRegistry, LanguageFile

logger = structlog.get_logger(__name__)


@dataclass
class ExtractionProgress:
    """提取进度信息"""
    session_id: str
    total_items: int
    processed_items: int
    current_item: str
    start_time: float
    estimated_completion: Optional[datetime] = None
    memory_usage_mb: float = 0
    throughput_items_per_sec: float = 0


@dataclass
class PerformanceMetrics:
    """性能指标"""
    total_duration_ms: int
    items_processed: int
    throughput_items_per_sec: float
    peak_memory_mb: float
    cache_hit_rate: float
    parallel_workers: int
    incremental_savings_percent: float


class PerformanceOptimizedExtractor:
    """性能优化的数据提取器"""
    
    def __init__(self, db_path: str = "data/mc_l10n.db"):
        self.db_path = db_path
        self.unified_service = UnifiedDataExtractionService(db_path)
        self.cache_service = get_cas_keyset_cache_service(db_path)
        self.event_handler = get_lang_upsert_event_handler(db_path)
        
        # 性能配置
        self.max_workers = min(8, (psutil.cpu_count() or 4))  # 最大并行工作线程
        self.memory_threshold_mb = 512  # 内存阈值
        self.batch_size = 50  # 批量处理大小
        self.cache_enabled = True
        
        # 运行时状态
        self._active_sessions: Dict[str, ExtractionProgress] = {}
        self._performance_history: List[PerformanceMetrics] = []
        
        logger.info(f"性能优化提取器已初始化: {self.max_workers} 工作线程")
    
    async def extract_with_optimization(
        self, 
        discovered_items: List[Dict[str, Any]],
        optimization_options: Dict[str, Any] = None
    ) -> Dict[str, Any]:
        """性能优化的数据提取"""
        session_id = f"perf_{uuid.uuid4().hex[:8]}"
        start_time = time.time()
        
        if not optimization_options:
            optimization_options = {}
        
        # 应用优化选项
        self._apply_optimization_options(optimization_options)
        
        logger.info(f"🚀 开始性能优化提取: {session_id} ({len(discovered_items)} 项目)")
        
        # 初始化进度跟踪
        progress = ExtractionProgress(
            session_id=session_id,
            total_items=len(discovered_items),
            processed_items=0,
            current_item="",
            start_time=start_time
        )
        self._active_sessions[session_id] = progress
        
        try:
            # 步骤1: 智能预处理和分组
            grouped_items = await self._intelligent_grouping(discovered_items)
            
            # 步骤2: 增量过滤
            if self.cache_enabled:
                filtered_items = await self._incremental_filtering(grouped_items)
                cache_savings = (len(discovered_items) - sum(len(items) for items in filtered_items.values())) / len(discovered_items)
            else:
                filtered_items = grouped_items
                cache_savings = 0
            
            # 步骤3: 并行提取
            extraction_results = await self._parallel_extraction(filtered_items, session_id)
            
            # 步骤4: 结果合并和优化
            final_result = await self._merge_and_optimize_results(extraction_results, session_id)
            
            # 计算性能指标
            duration_ms = int((time.time() - start_time) * 1000)
            metrics = self._calculate_performance_metrics(
                duration_ms, len(discovered_items), cache_savings, session_id
            )
            
            progress.processed_items = progress.total_items
            
            logger.info(
                f"✅ 性能优化提取完成: {session_id} "
                f"({metrics.items_processed} 项目, {duration_ms}ms, "
                f"{metrics.throughput_items_per_sec:.1f} 项目/秒)"
            )
            
            return {
                "success": True,
                "session_id": session_id,
                "results": final_result,
                "performance_metrics": metrics.__dict__,
                "cache_savings_percent": cache_savings * 100
            }
            
        except Exception as e:
            logger.error(f"性能优化提取失败 {session_id}: {e}")
            return {
                "success": False,
                "session_id": session_id,
                "error": str(e)
            }
        finally:
            # 清理会话
            if session_id in self._active_sessions:
                del self._active_sessions[session_id]
    
    async def extract_with_memory_optimization(
        self, 
        discovered_items: List[Dict[str, Any]],
        memory_limit_mb: int = 256
    ) -> Dict[str, Any]:
        """内存优化的数据提取"""
        session_id = f"mem_{uuid.uuid4().hex[:8]}"
        
        logger.info(f"🧠 开始内存优化提取: {session_id} (限制: {memory_limit_mb}MB)")
        
        # 分批处理以控制内存使用
        batch_size = max(1, min(self.batch_size, len(discovered_items) // 4))
        results = []
        
        for i in range(0, len(discovered_items), batch_size):
            batch = discovered_items[i:i + batch_size]
            
            # 检查内存使用
            current_memory = psutil.Process().memory_info().rss / 1024 / 1024
            if current_memory > memory_limit_mb:
                # 强制垃圾回收
                gc.collect()
                
                # 再次检查
                current_memory = psutil.Process().memory_info().rss / 1024 / 1024
                if current_memory > memory_limit_mb:
                    logger.warning(f"内存使用超限: {current_memory:.1f}MB > {memory_limit_mb}MB")
            
            # 处理批次
            batch_result = await self.unified_service.extract_from_scan_results(batch)
            if batch_result.get("success"):
                results.append(batch_result)
            
            # 进度更新
            progress_percent = ((i + len(batch)) / len(discovered_items)) * 100
            logger.info(f"内存优化提取进度: {progress_percent:.1f}% ({i + len(batch)}/{len(discovered_items)})")
        
        return {
            "success": True,
            "session_id": session_id,
            "batch_results": results,
            "total_batches": len(results)
        }
    
    async def _intelligent_grouping(
        self, 
        discovered_items: List[Dict[str, Any]]
    ) -> Dict[GameType, List[Dict[str, Any]]]:
        """智能分组：按游戏类型和处理复杂度分组"""
        grouped = {}
        
        for item in discovered_items:
            # 检测游戏类型
            game_type = ExtractorRegistry.detect_game_type([item])
            
            if game_type:
                if game_type not in grouped:
                    grouped[game_type] = []
                grouped[game_type].append(item)
        
        # 按复杂度排序（简单的先处理）
        for game_type, items in grouped.items():
            items.sort(key=lambda x: self._estimate_processing_complexity(x))
        
        return grouped
    
    async def _incremental_filtering(
        self, 
        grouped_items: Dict[GameType, List[Dict[str, Any]]]
    ) -> Dict[GameType, List[Dict[str, Any]]]:
        """增量过滤：移除未变更的项目"""
        filtered_items = {}
        
        for game_type, items in grouped_items.items():
            extractor = ExtractorRegistry.get_extractor(game_type)
            if not extractor:
                filtered_items[game_type] = items
                continue
            
            filtered_list = []
            
            for item in items:
                # 检查缓存
                has_changes = await self._check_item_changes(item, extractor)
                if has_changes:
                    filtered_list.append(item)
                else:
                    logger.debug(f"跳过未变更项目: {item.get('path', 'unknown')}")
            
            if filtered_list:
                filtered_items[game_type] = filtered_list
        
        return filtered_items
    
    async def _parallel_extraction(
        self, 
        grouped_items: Dict[GameType, List[Dict[str, Any]]],
        session_id: str
    ) -> Dict[GameType, Any]:
        """并行提取：多线程处理不同游戏类型"""
        results = {}
        
        # 创建提取任务
        tasks = []
        for game_type, items in grouped_items.items():
            if items:
                task = self._extract_game_type_async(game_type, items, session_id)
                tasks.append((game_type, task))
        
        # 并行执行
        if tasks:
            completed_tasks = await asyncio.gather(
                *[task for _, task in tasks], 
                return_exceptions=True
            )
            
            for i, result in enumerate(completed_tasks):
                game_type = tasks[i][0]
                if isinstance(result, Exception):
                    logger.error(f"游戏类型提取失败 {game_type}: {result}")
                    results[game_type] = {"success": False, "error": str(result)}
                else:
                    results[game_type] = result
        
        return results
    
    async def _extract_game_type_async(
        self, 
        game_type: GameType, 
        items: List[Dict[str, Any]],
        session_id: str
    ) -> Dict[str, Any]:
        """异步提取特定游戏类型的数据"""
        extractor = ExtractorRegistry.get_extractor(game_type)
        if not extractor:
            return {"success": False, "error": f"不支持的游戏类型: {game_type}"}
        
        try:
            # 更新进度
            if session_id in self._active_sessions:
                progress = self._active_sessions[session_id]
                progress.current_item = f"处理 {game_type.value} ({len(items)} 项目)"
            
            # 执行提取
            result = await extractor.extract_from_discovered_items(items)
            
            # 批量保存到数据库
            if result.success and result.language_files:
                save_result = await extractor._save_to_database(result.language_files)
                
                # 批量发送事件
                await self._batch_emit_events(result.language_files, session_id)
            
            return {
                "success": result.success,
                "game_type": game_type.value,
                "statistics": result.statistics,
                "language_files_count": len(result.language_files),
                "errors": result.errors
            }
            
        except Exception as e:
            logger.error(f"游戏类型提取异常 {game_type}: {e}")
            return {"success": False, "error": str(e)}
    
    async def _merge_and_optimize_results(
        self, 
        extraction_results: Dict[GameType, Any],
        session_id: str
    ) -> Dict[str, Any]:
        """合并和优化提取结果"""
        merged_statistics = {
            "total_language_files": 0,
            "total_translation_entries": 0,
            "supported_games": [],
            "game_results": {}
        }
        
        total_errors = []
        
        for game_type, result in extraction_results.items():
            if result.get("success"):
                stats = result.get("statistics", {})
                merged_statistics["total_language_files"] += result.get("language_files_count", 0)
                merged_statistics["total_translation_entries"] += stats.get("total_entries", 0)
                merged_statistics["supported_games"].append(game_type.value)
                merged_statistics["game_results"][game_type.value] = result
            else:
                total_errors.extend(result.get("errors", [result.get("error", "未知错误")]))
        
        return {
            "statistics": merged_statistics,
            "errors": total_errors,
            "success": len(total_errors) == 0
        }
    
    async def _batch_emit_events(
        self, 
        language_files: List[LanguageFile],
        session_id: str
    ):
        """批量发送LANG_UPSERT事件"""
        try:
            from .event_applier import ScanEvent, EventType
            
            events = []
            for lang_file in language_files:
                event = ScanEvent(
                    event_id=f"batch_{uuid.uuid4().hex[:8]}",
                    session_id=session_id,
                    event_type=EventType.LANG_UPSERT,
                    entity_ref=lang_file.carrier_uid,
                    stage="batch_extraction",
                    artifact_hash=lang_file.content_hash,
                    payload={
                        "language_file_uid": lang_file.uid,
                        "locale": lang_file.locale,
                        "carrier_type": lang_file.carrier_type,
                        "entry_count": len(lang_file.entries),
                        "keyset_hash": lang_file.keyset_hash,
                        "format": lang_file.format.value
                    },
                    timestamp=datetime.now().isoformat()
                )
                events.append(event)
            
            # 批量处理事件
            if events:
                await self.event_handler.handle_batch_lang_upsert_events(events)
                logger.debug(f"批量发送 {len(events)} 个LANG_UPSERT事件")
                
        except Exception as e:
            logger.warning(f"批量事件发送失败: {e}")
    
    async def _check_item_changes(
        self, 
        item: Dict[str, Any], 
        extractor
    ) -> bool:
        """检查项目是否有变更"""
        try:
            # 获取项目的键集预览
            preview_items = await extractor._extract_keyset_preview(item)
            
            if not preview_items:
                return True  # 无法获取预览，认为有变更
            
            # 批量检查缓存
            cache_requests = [
                (preview["carrier_uid"], preview["relative_path"], 
                 preview.get("locale", "unknown"))
                for preview in preview_items
            ]
            
            cached_fingerprints = await self.cache_service.get_bulk_keyset_cache(cache_requests)
            
            # 检查是否有变更
            for preview in preview_items:
                cache_key = f"{preview['carrier_uid']}:{preview['relative_path']}:{preview.get('locale', 'unknown')}"
                cached = cached_fingerprints.get(cache_key)
                
                if not cached or cached["keyset_hash"] != preview["keyset_hash"]:
                    return True  # 有变更
            
            return False  # 无变更
            
        except Exception as e:
            logger.warning(f"变更检查失败: {e}")
            return True  # 出错时认为有变更
    
    def _estimate_processing_complexity(self, item: Dict[str, Any]) -> int:
        """估算处理复杂度（用于排序）"""
        complexity = 0
        
        # 基于文件大小
        if "size" in item:
            complexity += item["size"] // 1024  # KB
        
        # 基于项目类型
        if item.get("type") == "mod":
            complexity += 100
        elif item.get("type") == "standalone_language_file":
            complexity += 10
        
        # 基于语言文件数量
        if "language_files" in item:
            complexity += len(item["language_files"]) * 5
        
        return complexity
    
    def _apply_optimization_options(self, options: Dict[str, Any]):
        """应用优化选项"""
        if "max_workers" in options:
            self.max_workers = min(options["max_workers"], psutil.cpu_count() or 4)
        
        if "memory_threshold_mb" in options:
            self.memory_threshold_mb = options["memory_threshold_mb"]
        
        if "batch_size" in options:
            self.batch_size = options["batch_size"]
        
        if "cache_enabled" in options:
            self.cache_enabled = options["cache_enabled"]
        
        logger.debug(f"应用优化选项: workers={self.max_workers}, memory={self.memory_threshold_mb}MB")
    
    def _calculate_performance_metrics(
        self, 
        duration_ms: int, 
        items_count: int, 
        cache_savings: float,
        session_id: str
    ) -> PerformanceMetrics:
        """计算性能指标"""
        throughput = (items_count / duration_ms) * 1000 if duration_ms > 0 else 0
        
        # 获取内存使用峰值
        current_memory = psutil.Process().memory_info().rss / 1024 / 1024
        
        metrics = PerformanceMetrics(
            total_duration_ms=duration_ms,
            items_processed=items_count,
            throughput_items_per_sec=throughput,
            peak_memory_mb=current_memory,
            cache_hit_rate=cache_savings,
            parallel_workers=self.max_workers,
            incremental_savings_percent=cache_savings * 100
        )
        
        # 保存到历史记录
        self._performance_history.append(metrics)
        if len(self._performance_history) > 100:  # 保留最近100次记录
            self._performance_history.pop(0)
        
        return metrics
    
    async def get_performance_report(self) -> Dict[str, Any]:
        """获取性能报告"""
        if not self._performance_history:
            return {"message": "暂无性能数据"}
        
        recent_metrics = self._performance_history[-10:]  # 最近10次
        
        avg_throughput = sum(m.throughput_items_per_sec for m in recent_metrics) / len(recent_metrics)
        avg_memory = sum(m.peak_memory_mb for m in recent_metrics) / len(recent_metrics)
        avg_cache_hit = sum(m.cache_hit_rate for m in recent_metrics) / len(recent_metrics)
        
        return {
            "recent_performance": {
                "average_throughput_items_per_sec": round(avg_throughput, 2),
                "average_memory_usage_mb": round(avg_memory, 2),
                "average_cache_hit_rate": round(avg_cache_hit * 100, 2),
                "parallel_workers": self.max_workers
            },
            "active_sessions": len(self._active_sessions),
            "total_extractions": len(self._performance_history),
            "cache_statistics": await self.cache_service.get_cache_statistics()
        }
    
    def get_active_sessions(self) -> Dict[str, Dict[str, Any]]:
        """获取活跃会话状态"""
        sessions = {}
        
        for session_id, progress in self._active_sessions.items():
            elapsed_time = time.time() - progress.start_time
            
            if progress.processed_items > 0:
                progress.throughput_items_per_sec = progress.processed_items / elapsed_time
                
                # 估算完成时间
                remaining_items = progress.total_items - progress.processed_items
                if progress.throughput_items_per_sec > 0:
                    eta_seconds = remaining_items / progress.throughput_items_per_sec
                    progress.estimated_completion = datetime.fromtimestamp(time.time() + eta_seconds)
            
            # 获取当前内存使用
            progress.memory_usage_mb = psutil.Process().memory_info().rss / 1024 / 1024
            
            sessions[session_id] = {
                "total_items": progress.total_items,
                "processed_items": progress.processed_items,
                "progress_percent": (progress.processed_items / progress.total_items) * 100,
                "current_item": progress.current_item,
                "elapsed_time_seconds": elapsed_time,
                "throughput_items_per_sec": progress.throughput_items_per_sec,
                "memory_usage_mb": progress.memory_usage_mb,
                "estimated_completion": progress.estimated_completion.isoformat() if progress.estimated_completion else None
            }
        
        return sessions


# 全局性能优化提取器实例
_performance_extractor: PerformanceOptimizedExtractor = None


def get_performance_optimized_extractor(db_path: str = "data/mc_l10n.db") -> PerformanceOptimizedExtractor:
    """获取性能优化提取器实例"""
    global _performance_extractor
    if _performance_extractor is None:
        _performance_extractor = PerformanceOptimizedExtractor(db_path)
    return _performance_extractor