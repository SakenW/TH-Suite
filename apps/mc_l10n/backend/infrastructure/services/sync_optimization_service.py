"""
同步优化服务
集成现有CAS缓存系统，实现批量传输和压缩优化

主要特性:
- 基于BLAKE3的内容寻址缓存
- Zstd智能压缩传输
- 批量数据处理和传输
- 增量传输优化
- 性能监控和统计

作者: Claude Code
创建时间: 2025-09-20
"""

import asyncio
import hashlib
import json
import sqlite3
import structlog
import time
import zstandard as zstd
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Any, Optional, Set, Tuple, AsyncIterator
from dataclasses import dataclass, field
from concurrent.futures import ThreadPoolExecutor

# 导入现有服务
from infrastructure.services.cas_keyset_cache_service import (
    CasKeysetCacheService,
    get_cas_keyset_cache_service
)
from infrastructure.services.translation_sync_engine import (
    TranslationEntry,
    SyncDelta,
    ChangeType
)

logger = structlog.get_logger(__name__)


# ============================================================
# 压缩和传输优化数据类
# ============================================================

@dataclass
class CompressionStats:
    """压缩统计信息"""
    original_size: int = 0
    compressed_size: int = 0
    compression_ratio: float = 0.0
    compression_time: float = 0.0
    decompression_time: float = 0.0
    algorithm: str = "zstd"
    level: int = 3


@dataclass
class TransferBatch:
    """传输批次"""
    batch_id: str
    entries: List[TranslationEntry]
    size_bytes: int
    content_hash: str
    compression_stats: Optional[CompressionStats] = None
    
    # 传输状态
    prepared_at: Optional[datetime] = None
    transmitted_at: Optional[datetime] = None
    acknowledged_at: Optional[datetime] = None
    
    # 元数据
    metadata: Dict[str, Any] = field(default_factory=dict)
    retry_count: int = 0
    last_error: Optional[str] = None


@dataclass
class SyncOptimizationResult:
    """同步优化结果"""
    total_entries: int
    total_batches: int
    total_size_original: int
    total_size_compressed: int
    overall_compression_ratio: float
    preparation_time: float
    transmission_time: float
    
    # 性能统计
    cache_hits: int = 0
    cache_misses: int = 0
    cache_hit_ratio: float = 0.0
    
    # 批次统计
    batches: List[TransferBatch] = field(default_factory=list)
    failed_batches: List[str] = field(default_factory=list)


# ============================================================
# 智能压缩器
# ============================================================

class IntelligentCompressor:
    """智能压缩器，基于内容类型选择最优压缩策略"""
    
    def __init__(self):
        # 预训练的语言专用字典
        self.language_dicts = {}
        self._load_language_dictionaries()
        
        # 压缩器缓存
        self._compressor_cache = {}
        
    def _load_language_dictionaries(self):
        """加载语言专用压缩字典"""
        # 中文字典（高压缩率）
        self.language_dicts["zh_cn"] = self._create_chinese_dict()
        
        # 英文字典（标准压缩）
        self.language_dicts["en_us"] = self._create_english_dict()
        
        # 其他语言使用通用字典
        self.language_dicts["default"] = self._create_default_dict()
    
    def _create_chinese_dict(self) -> bytes:
        """创建中文专用压缩字典"""
        # 常见中文词汇和Minecraft术语
        chinese_samples = [
            "方块", "物品", "合成", "挖掘", "建造", "红石", "附魔", "药水",
            "村民", "怪物", "生物群系", "世界", "服务器", "模组", "材质包",
            "命令", "设置", "配置", "选项", "界面", "菜单", "按钮", "标签",
            "工具", "武器", "装备", "食物", "种子", "木头", "石头", "钻石"
        ]
        
        training_data = "\n".join(chinese_samples * 100).encode('utf-8')
        return zstd.train_dictionary(training_data, 1024)
    
    def _create_english_dict(self) -> bytes:
        """创建英文专用压缩字典"""
        english_samples = [
            "block", "item", "craft", "mine", "build", "redstone", "enchant", "potion",
            "villager", "monster", "biome", "world", "server", "mod", "resource pack",
            "command", "setting", "config", "option", "interface", "menu", "button", "tab",
            "tool", "weapon", "equipment", "food", "seed", "wood", "stone", "diamond"
        ]
        
        training_data = "\n".join(english_samples * 100).encode('utf-8')
        return zstd.train_dictionary(training_data, 1024)
    
    def _create_default_dict(self) -> bytes:
        """创建通用压缩字典"""
        # 混合各种语言的常见词汇
        mixed_samples = [
            "minecraft", "translation", "language", "locale", "content", "text",
            "source", "target", "key", "value", "metadata", "namespace", "context"
        ]
        
        training_data = "\n".join(mixed_samples * 100).encode('utf-8')
        return zstd.train_dictionary(training_data, 512)
    
    def compress_translations(
        self,
        entries: List[TranslationEntry],
        language_code: str = "en_us",
        compression_level: int = 3
    ) -> Tuple[bytes, CompressionStats]:
        """压缩翻译条目"""
        
        start_time = time.time()
        
        # 序列化数据
        data = self._serialize_entries(entries)
        original_data = json.dumps(data, ensure_ascii=False, separators=(',', ':')).encode('utf-8')
        original_size = len(original_data)
        
        # 选择压缩字典
        dict_data = self.language_dicts.get(language_code, self.language_dicts["default"])
        
        # 获取压缩器实例
        compressor_key = f"{language_code}_{compression_level}"
        if compressor_key not in self._compressor_cache:
            self._compressor_cache[compressor_key] = zstd.ZstdCompressor(
                level=compression_level,
                dict_data=zstd.ZstdCompressionDict(dict_data)
            )
        
        compressor = self._compressor_cache[compressor_key]
        
        # 执行压缩
        compressed_data = compressor.compress(original_data)
        compressed_size = len(compressed_data)
        
        compression_time = time.time() - start_time
        compression_ratio = compressed_size / original_size if original_size > 0 else 1.0
        
        stats = CompressionStats(
            original_size=original_size,
            compressed_size=compressed_size,
            compression_ratio=compression_ratio,
            compression_time=compression_time,
            algorithm="zstd",
            level=compression_level
        )
        
        logger.debug("翻译压缩完成",
                    entries_count=len(entries),
                    language=language_code,
                    original_size=original_size,
                    compressed_size=compressed_size,
                    ratio=f"{compression_ratio:.2%}")
        
        return compressed_data, stats
    
    def decompress_translations(
        self,
        compressed_data: bytes,
        language_code: str = "en_us"
    ) -> Tuple[List[TranslationEntry], CompressionStats]:
        """解压翻译条目"""
        
        start_time = time.time()
        
        # 选择解压字典
        dict_data = self.language_dicts.get(language_code, self.language_dicts["default"])
        
        # 创建解压器
        decompressor = zstd.ZstdDecompressor(
            dict_data=zstd.ZstdCompressionDict(dict_data)
        )
        
        # 执行解压
        decompressed_data = decompressor.decompress(compressed_data)
        
        # 反序列化
        data = json.loads(decompressed_data.decode('utf-8'))
        entries = self._deserialize_entries(data)
        
        decompression_time = time.time() - start_time
        
        stats = CompressionStats(
            original_size=len(decompressed_data),
            compressed_size=len(compressed_data),
            compression_ratio=len(compressed_data) / len(decompressed_data),
            decompression_time=decompression_time,
            algorithm="zstd"
        )
        
        return entries, stats
    
    def _serialize_entries(self, entries: List[TranslationEntry]) -> List[Dict[str, Any]]:
        """序列化翻译条目"""
        serialized = []
        
        for entry in entries:
            data = {
                "id": entry.entry_id,
                "key": entry.content_key,
                "src": entry.source_text,
                "tgt": entry.target_text,
                "lang": entry.language_code,
                "mod": entry.mod_id,
                "pack": entry.pack_id,
                "ns": entry.namespace,
                "ctx": entry.context,
                "hash": entry.content_hash,
                "ver": entry.version,
                "translated": entry.is_translated,
                "approved": entry.is_approved,
                "translator": entry.translator,
                "modified": entry.last_modified.isoformat() if entry.last_modified else None
            }
            
            # 移除空值以减少大小
            data = {k: v for k, v in data.items() if v is not None}
            serialized.append(data)
        
        return serialized
    
    def _deserialize_entries(self, data: List[Dict[str, Any]]) -> List[TranslationEntry]:
        """反序列化翻译条目"""
        entries = []
        
        for item in data:
            entry = TranslationEntry(
                entry_id=item["id"],
                content_key=item["key"],
                source_text=item["src"],
                target_text=item["tgt"],
                language_code=item["lang"],
                mod_id=item.get("mod"),
                pack_id=item.get("pack"),
                namespace=item.get("ns"),
                context=item.get("ctx"),
                content_hash=item.get("hash"),
                version=item.get("ver", 1),
                is_translated=item.get("translated", False),
                is_approved=item.get("approved", False),
                translator=item.get("translator"),
                last_modified=datetime.fromisoformat(item["modified"]) if item.get("modified") else None
            )
            entries.append(entry)
        
        return entries


# ============================================================
# 批量传输管理器
# ============================================================

class BatchTransferManager:
    """批量传输管理器"""
    
    def __init__(self, db_path: str, batch_size: int = 100, max_concurrency: int = 3):
        self.db_path = Path(db_path)
        self.batch_size = batch_size
        self.max_concurrency = max_concurrency
        
        # 组件
        self.compressor = IntelligentCompressor()
        self.cas_cache = get_cas_keyset_cache_service(str(self.db_path))
        
        # 执行器
        self.executor = ThreadPoolExecutor(max_workers=max_concurrency)
        
        # 统计
        self.stats = {
            "batches_created": 0,
            "batches_transmitted": 0,
            "batches_failed": 0,
            "total_bytes_original": 0,
            "total_bytes_compressed": 0,
            "total_compression_time": 0.0,
            "total_transmission_time": 0.0
        }
        
    async def prepare_transfer_batches(
        self,
        entries: List[TranslationEntry],
        direction: str = "upload"
    ) -> List[TransferBatch]:
        """准备传输批次"""
        
        logger.info("开始准备传输批次",
                   total_entries=len(entries),
                   batch_size=self.batch_size)
        
        batches = []
        
        # 按语言分组以优化压缩效果
        language_groups = self._group_by_language(entries)
        
        for language_code, lang_entries in language_groups.items():
            # 创建该语言的批次
            lang_batches = await self._create_language_batches(
                lang_entries, language_code, direction
            )
            batches.extend(lang_batches)
        
        logger.info("传输批次准备完成",
                   total_batches=len(batches),
                   by_language={lang: len(self._group_by_language(entries)[lang]) 
                               for lang in language_groups.keys()})
        
        return batches
    
    async def _create_language_batches(
        self,
        entries: List[TranslationEntry],
        language_code: str,
        direction: str
    ) -> List[TransferBatch]:
        """为特定语言创建批次"""
        
        batches = []
        
        # 分割为批次
        for i in range(0, len(entries), self.batch_size):
            batch_entries = entries[i:i + self.batch_size]
            
            # 创建批次ID
            batch_id = f"{language_code}_{direction}_{i//self.batch_size + 1}_{int(time.time())}"
            
            # 检查缓存
            cache_hit = await self._check_batch_cache(batch_entries, language_code)
            
            if cache_hit:
                logger.debug("批次缓存命中", batch_id=batch_id)
                # 使用缓存的压缩数据
                batch = TransferBatch(
                    batch_id=batch_id,
                    entries=batch_entries,
                    size_bytes=cache_hit["compressed_size"],
                    content_hash=cache_hit["content_hash"],
                    compression_stats=cache_hit["compression_stats"]
                )
            else:
                # 创建新批次
                batch = await self._create_new_batch(
                    batch_id, batch_entries, language_code
                )
            
            batch.prepared_at = datetime.now()
            batches.append(batch)
            
            self.stats["batches_created"] += 1
        
        return batches
    
    async def _create_new_batch(
        self,
        batch_id: str,
        entries: List[TranslationEntry],
        language_code: str
    ) -> TransferBatch:
        """创建新的传输批次"""
        
        # 压缩数据
        compressed_data, compression_stats = self.compressor.compress_translations(
            entries, language_code
        )
        
        # 计算内容哈希
        content_hash = hashlib.blake3(compressed_data).hexdigest()
        
        # 存储到CAS缓存
        await self.cas_cache.store_cas_object(
            "translation_batch",
            {
                "batch_id": batch_id,
                "language_code": language_code,
                "entries_count": len(entries),
                "compressed_data": compressed_data.hex(),  # 十六进制存储二进制数据
                "compression_stats": {
                    "original_size": compression_stats.original_size,
                    "compressed_size": compression_stats.compressed_size,
                    "compression_ratio": compression_stats.compression_ratio,
                    "algorithm": compression_stats.algorithm,
                    "level": compression_stats.level
                }
            },
            metadata={
                "content_hash": content_hash,
                "language": language_code,
                "batch_size": len(entries),
                "created_at": datetime.now().isoformat()
            }
        )
        
        # 更新统计
        self.stats["total_bytes_original"] += compression_stats.original_size
        self.stats["total_bytes_compressed"] += compression_stats.compressed_size
        self.stats["total_compression_time"] += compression_stats.compression_time
        
        return TransferBatch(
            batch_id=batch_id,
            entries=entries,
            size_bytes=compression_stats.compressed_size,
            content_hash=content_hash,
            compression_stats=compression_stats
        )
    
    async def _check_batch_cache(
        self,
        entries: List[TranslationEntry],
        language_code: str
    ) -> Optional[Dict[str, Any]]:
        """检查批次缓存"""
        
        # 计算条目指纹
        entries_hash = self._calculate_entries_hash(entries)
        
        # 查找CAS缓存
        cached_object = await self.cas_cache.get_cas_object(entries_hash)
        
        if cached_object and cached_object["object_type"] == "translation_batch":
            content = cached_object["content"]
            compression_stats = CompressionStats(**content["compression_stats"])
            
            return {
                "content_hash": cached_object["object_hash"],
                "compressed_size": compression_stats.compressed_size,
                "compression_stats": compression_stats,
                "cached_data": content
            }
        
        return None
    
    async def transmit_batches(
        self,
        batches: List[TransferBatch],
        target_endpoint: str,
        auth_headers: Optional[Dict[str, str]] = None
    ) -> SyncOptimizationResult:
        """传输批次数据"""
        
        start_time = time.time()
        
        logger.info("开始批量传输",
                   total_batches=len(batches),
                   target_endpoint=target_endpoint)
        
        # 并发传输
        transmission_tasks = []
        semaphore = asyncio.Semaphore(self.max_concurrency)
        
        for batch in batches:
            task = asyncio.create_task(
                self._transmit_single_batch(batch, target_endpoint, auth_headers, semaphore)
            )
            transmission_tasks.append(task)
        
        # 等待所有传输完成
        results = await asyncio.gather(*transmission_tasks, return_exceptions=True)
        
        # 统计结果
        successful_batches = []
        failed_batches = []
        
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                failed_batches.append(batches[i].batch_id)
                logger.error("批次传输失败",
                           batch_id=batches[i].batch_id,
                           error=str(result))
            else:
                successful_batches.append(batches[i])
                batches[i].transmitted_at = datetime.now()
        
        transmission_time = time.time() - start_time
        
        # 计算整体统计
        total_entries = sum(len(batch.entries) for batch in batches)
        total_original_size = sum(
            batch.compression_stats.original_size 
            for batch in batches 
            if batch.compression_stats
        )
        total_compressed_size = sum(batch.size_bytes for batch in batches)
        
        overall_compression_ratio = (
            total_compressed_size / total_original_size 
            if total_original_size > 0 else 1.0
        )
        
        result = SyncOptimizationResult(
            total_entries=total_entries,
            total_batches=len(batches),
            total_size_original=total_original_size,
            total_size_compressed=total_compressed_size,
            overall_compression_ratio=overall_compression_ratio,
            preparation_time=self.stats["total_compression_time"],
            transmission_time=transmission_time,
            batches=successful_batches,
            failed_batches=failed_batches
        )
        
        logger.info("批量传输完成",
                   successful=len(successful_batches),
                   failed=len(failed_batches),
                   compression_ratio=f"{overall_compression_ratio:.2%}",
                   transmission_time=f"{transmission_time:.2f}s")
        
        return result
    
    async def _transmit_single_batch(
        self,
        batch: TransferBatch,
        target_endpoint: str,
        auth_headers: Optional[Dict[str, str]],
        semaphore: asyncio.Semaphore
    ) -> bool:
        """传输单个批次"""
        
        async with semaphore:
            try:
                # 从CAS缓存获取压缩数据
                cached_object = await self.cas_cache.get_cas_object(batch.content_hash)
                
                if not cached_object:
                    raise Exception(f"批次缓存数据不存在: {batch.content_hash}")
                
                compressed_data = bytes.fromhex(cached_object["content"]["compressed_data"])
                
                # 这里应该实现实际的HTTP传输逻辑
                # 暂时模拟传输延迟
                await asyncio.sleep(0.1)
                
                logger.debug("批次传输成功",
                           batch_id=batch.batch_id,
                           size=len(compressed_data))
                
                self.stats["batches_transmitted"] += 1
                return True
                
            except Exception as e:
                self.stats["batches_failed"] += 1
                batch.last_error = str(e)
                batch.retry_count += 1
                raise
    
    def _group_by_language(self, entries: List[TranslationEntry]) -> Dict[str, List[TranslationEntry]]:
        """按语言分组条目"""
        groups = {}
        for entry in entries:
            lang = entry.language_code
            if lang not in groups:
                groups[lang] = []
            groups[lang].append(entry)
        return groups
    
    def _calculate_entries_hash(self, entries: List[TranslationEntry]) -> str:
        """计算条目集合的哈希"""
        # 创建稳定的哈希输入
        sorted_entries = sorted(entries, key=lambda e: (e.language_code, e.content_key))
        
        hash_input = ""
        for entry in sorted_entries:
            hash_input += f"{entry.content_key}:{entry.source_text}:{entry.target_text}:{entry.content_hash}\n"
        
        return hashlib.blake3(hash_input.encode('utf-8')).hexdigest()
    
    def get_transfer_statistics(self) -> Dict[str, Any]:
        """获取传输统计信息"""
        return {
            **self.stats,
            "compression_ratio": (
                self.stats["total_bytes_compressed"] / self.stats["total_bytes_original"]
                if self.stats["total_bytes_original"] > 0 else 1.0
            ),
            "success_rate": (
                self.stats["batches_transmitted"] / self.stats["batches_created"]
                if self.stats["batches_created"] > 0 else 0.0
            )
        }


# ============================================================
# 主要同步优化服务
# ============================================================

class SyncOptimizationService:
    """同步优化服务，集成CAS缓存和压缩传输"""
    
    def __init__(self, db_path: str = "data/mc_l10n.db"):
        self.db_path = Path(db_path)
        self.transfer_manager = BatchTransferManager(str(self.db_path))
        self.cas_cache = get_cas_keyset_cache_service(str(self.db_path))
        
        logger.info("同步优化服务初始化完成")
    
    async def optimize_sync_deltas(
        self,
        deltas: List[SyncDelta],
        direction: str = "bidirectional"
    ) -> SyncOptimizationResult:
        """优化同步差量传输"""
        
        # 提取需要传输的条目
        entries_to_transfer = []
        
        for delta in deltas:
            if delta.change_type in [ChangeType.ADDED, ChangeType.MODIFIED]:
                if delta.resolved_entry:
                    entries_to_transfer.append(delta.resolved_entry)
                else:
                    entries_to_transfer.append(delta.entry)
        
        if not entries_to_transfer:
            logger.info("没有需要传输的条目")
            return SyncOptimizationResult(
                total_entries=0,
                total_batches=0,
                total_size_original=0,
                total_size_compressed=0,
                overall_compression_ratio=1.0,
                preparation_time=0.0,
                transmission_time=0.0
            )
        
        # 准备传输批次
        batches = await self.transfer_manager.prepare_transfer_batches(
            entries_to_transfer, direction
        )
        
        # 模拟传输（实际应用中会调用真实的传输API）
        result = await self._simulate_transmission(batches)
        
        logger.info("同步优化完成",
                   entries=len(entries_to_transfer),
                   batches=len(batches),
                   compression_ratio=f"{result.overall_compression_ratio:.2%}")
        
        return result
    
    async def _simulate_transmission(self, batches: List[TransferBatch]) -> SyncOptimizationResult:
        """模拟传输过程"""
        
        # 计算统计信息
        total_entries = sum(len(batch.entries) for batch in batches)
        total_original_size = sum(
            batch.compression_stats.original_size 
            for batch in batches 
            if batch.compression_stats
        )
        total_compressed_size = sum(batch.size_bytes for batch in batches)
        
        overall_compression_ratio = (
            total_compressed_size / total_original_size 
            if total_original_size > 0 else 1.0
        )
        
        # 模拟传输时间
        await asyncio.sleep(0.1 * len(batches))
        
        return SyncOptimizationResult(
            total_entries=total_entries,
            total_batches=len(batches),
            total_size_original=total_original_size,
            total_size_compressed=total_compressed_size,
            overall_compression_ratio=overall_compression_ratio,
            preparation_time=self.transfer_manager.stats["total_compression_time"],
            transmission_time=0.1 * len(batches),
            batches=batches
        )
    
    async def get_optimization_statistics(self) -> Dict[str, Any]:
        """获取优化统计信息"""
        
        transfer_stats = self.transfer_manager.get_transfer_statistics()
        cache_stats = await self.cas_cache.get_cache_statistics()
        
        return {
            "transfer": transfer_stats,
            "cache": cache_stats,
            "optimization": {
                "average_compression_ratio": transfer_stats.get("compression_ratio", 1.0),
                "cache_efficiency": cache_stats.get("keyset_fingerprints", {}).get("total_count", 0),
                "total_data_saved": transfer_stats["total_bytes_original"] - transfer_stats["total_bytes_compressed"]
            }
        }


# ============================================================
# 服务工厂函数
# ============================================================

def create_sync_optimization_service(db_path: str = "data/mc_l10n.db") -> SyncOptimizationService:
    """创建同步优化服务实例"""
    return SyncOptimizationService(db_path)


# 全局实例
_optimization_service: Optional[SyncOptimizationService] = None


def get_sync_optimization_service(db_path: str = "data/mc_l10n.db") -> SyncOptimizationService:
    """获取同步优化服务单例"""
    global _optimization_service
    if _optimization_service is None:
        _optimization_service = SyncOptimizationService(db_path)
    return _optimization_service