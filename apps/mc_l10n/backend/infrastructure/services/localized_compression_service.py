"""
本地化压缩服务 - 语言特化的智能压缩系统
基于语言特征训练压缩字典，优化翻译数据传输效率
"""

import asyncio
import json
import logging
import pickle
import time
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple, Any, Set
from dataclasses import dataclass, asdict
from enum import Enum
from pathlib import Path
import blake3
import zstandard as zstd
import tempfile
import os

from infrastructure.repositories.repository_factory import get_repository_factory
from infrastructure.services.multi_layer_cache_service import (
    get_multi_layer_cache_service, CacheType
)

logger = logging.getLogger(__name__)


class CompressionStrategy(Enum):
    """压缩策略枚举"""
    FAST = "fast"                   # 快速压缩（速度优先）
    BALANCED = "balanced"           # 平衡模式（速度和压缩率平衡）
    HIGH = "high"                   # 高压缩率（压缩率优先）
    MAX = "max"                     # 最大压缩率（压缩率最高）
    ADAPTIVE = "adaptive"           # 自适应（根据数据特征选择）


class LanguageFamily(Enum):
    """语言族枚举"""
    CJK = "cjk"                     # 中日韩语族
    LATIN = "latin"                 # 拉丁语族
    CYRILLIC = "cyrillic"           # 西里尔语族
    ARABIC = "arabic"               # 阿拉伯语族
    DEVANAGARI = "devanagari"       # 天城文语族
    UNKNOWN = "unknown"             # 未知语族


@dataclass
class CompressionResult:
    """压缩结果"""
    compressed_data: bytes
    uncompressed_size: int
    compressed_size: int
    compression_ratio: float
    compression_time_ms: int
    strategy_used: CompressionStrategy
    dictionary_id: Optional[str] = None
    language_family: Optional[LanguageFamily] = None


@dataclass
class CompressionDictionary:
    """压缩字典"""
    dictionary_id: str
    locale_code: str
    language_family: LanguageFamily
    dictionary_data: bytes
    sample_size: int
    creation_time: datetime
    last_used: datetime
    usage_count: int
    effectiveness_score: float
    size_bytes: int


@dataclass
class CompressionStats:
    """压缩统计"""
    total_compressions: int
    total_bytes_processed: int
    total_bytes_saved: int
    average_compression_ratio: float
    average_compression_time_ms: float
    dictionary_usage: Dict[str, int]
    strategy_distribution: Dict[CompressionStrategy, int]


class LocalizedCompressionService:
    """本地化压缩服务"""
    
    def __init__(self):
        self.factory = get_repository_factory()
        self.cache_service = get_multi_layer_cache_service()
        
        # 压缩字典缓存
        self.dictionaries: Dict[str, CompressionDictionary] = {}
        
        # 语言检测模式和字典
        self.language_detection_patterns = {
            LanguageFamily.CJK: {
                "patterns": [r'[\u4e00-\u9fff]', r'[\u3040-\u309f]', r'[\u30a0-\u30ff]', r'[\uac00-\ud7af]'],
                "threshold": 0.3
            },
            LanguageFamily.LATIN: {
                "patterns": [r'[a-zA-Z]'],
                "threshold": 0.6
            },
            LanguageFamily.CYRILLIC: {
                "patterns": [r'[\u0400-\u04ff]'],
                "threshold": 0.4
            },
            LanguageFamily.ARABIC: {
                "patterns": [r'[\u0600-\u06ff]'],
                "threshold": 0.4
            },
            LanguageFamily.DEVANAGARI: {
                "patterns": [r'[\u0900-\u097f]'],
                "threshold": 0.4
            }
        }
        
        # 压缩策略配置
        self.strategy_configs = {
            CompressionStrategy.FAST: {
                "level": 1,
                "enable_long_distance": False,
                "enable_multithread": True,
                "window_log": 18  # 256KB
            },
            CompressionStrategy.BALANCED: {
                "level": 3,
                "enable_long_distance": True,
                "enable_multithread": True,
                "window_log": 20  # 1MB
            },
            CompressionStrategy.HIGH: {
                "level": 6,
                "enable_long_distance": True,
                "enable_multithread": False,
                "window_log": 22  # 4MB
            },
            CompressionStrategy.MAX: {
                "level": 9,
                "enable_long_distance": True,
                "enable_multithread": False,
                "window_log": 24  # 16MB
            }
        }
        
        # 统计信息
        self.stats = CompressionStats(
            total_compressions=0,
            total_bytes_processed=0,
            total_bytes_saved=0,
            average_compression_ratio=0.0,
            average_compression_time_ms=0.0,
            dictionary_usage={},
            strategy_distribution={strategy: 0 for strategy in CompressionStrategy}
        )
        
        # 自适应阈值
        self.adaptive_thresholds = {
            "small_data_threshold": 1024,      # 1KB以下数据使用FAST
            "large_data_threshold": 1024*1024, # 1MB以上数据使用HIGH
            "cjk_bonus": 0.1,                  # CJK语言压缩率加成
            "repetition_bonus": 0.15           # 重复内容压缩率加成
        }
        
    async def initialize(self):
        """初始化压缩服务"""
        try:
            # 加载已有的压缩字典
            await self._load_existing_dictionaries()
            
            # 清理过期字典
            await self._cleanup_expired_dictionaries()
            
            logger.info(f"本地化压缩服务初始化完成，已加载 {len(self.dictionaries)} 个字典")
            
        except Exception as e:
            logger.error(f"初始化本地化压缩服务失败: {e}")
            raise
            
    async def compress_translation_data(
        self,
        data: Dict[str, Any],
        locale_code: str,
        strategy: CompressionStrategy = CompressionStrategy.ADAPTIVE
    ) -> CompressionResult:
        """
        压缩翻译数据
        
        Args:
            data: 要压缩的翻译数据
            locale_code: 语言代码
            strategy: 压缩策略
        """
        start_time = time.time()
        
        try:
            # 序列化数据
            json_data = json.dumps(data, ensure_ascii=False, separators=(',', ':'))
            uncompressed_bytes = json_data.encode('utf-8')
            uncompressed_size = len(uncompressed_bytes)
            
            # 检测语言族
            language_family = await self._detect_language_family(json_data, locale_code)
            
            # 自适应策略选择
            if strategy == CompressionStrategy.ADAPTIVE:
                strategy = await self._choose_adaptive_strategy(
                    uncompressed_bytes, language_family, locale_code
                )
                
            # 获取或创建压缩字典
            dictionary = await self._get_or_create_dictionary(locale_code, language_family)
            
            # 执行压缩
            compressed_bytes = await self._compress_with_dictionary(
                uncompressed_bytes, dictionary, strategy
            )
            
            # 计算压缩结果
            compressed_size = len(compressed_bytes)
            compression_ratio = (uncompressed_size - compressed_size) / uncompressed_size
            compression_time_ms = int((time.time() - start_time) * 1000)
            
            # 更新统计
            await self._update_compression_stats(
                uncompressed_size, compressed_size, compression_time_ms, 
                strategy, dictionary.dictionary_id if dictionary else None
            )
            
            # 更新字典使用统计
            if dictionary:
                dictionary.usage_count += 1
                dictionary.last_used = datetime.now()
                await self._update_dictionary_effectiveness(dictionary, compression_ratio)
                
            logger.debug(f"压缩完成: {locale_code}, 原始: {uncompressed_size}, "
                        f"压缩: {compressed_size}, 压缩率: {compression_ratio:.2%}, "
                        f"耗时: {compression_time_ms}ms")
            
            return CompressionResult(
                compressed_data=compressed_bytes,
                uncompressed_size=uncompressed_size,
                compressed_size=compressed_size,
                compression_ratio=compression_ratio,
                compression_time_ms=compression_time_ms,
                strategy_used=strategy,
                dictionary_id=dictionary.dictionary_id if dictionary else None,
                language_family=language_family
            )
            
        except Exception as e:
            logger.error(f"压缩翻译数据失败: {locale_code}: {e}")
            raise
            
    async def decompress_translation_data(
        self,
        compressed_data: bytes,
        dictionary_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        解压缩翻译数据
        
        Args:
            compressed_data: 压缩数据
            dictionary_id: 字典ID（如果使用了字典压缩）
        """
        try:
            # 获取字典
            dictionary = None
            if dictionary_id:
                dictionary = await self._get_dictionary_by_id(dictionary_id)
                
            # 执行解压缩
            decompressed_bytes = await self._decompress_with_dictionary(
                compressed_data, dictionary
            )
            
            # 解析JSON数据
            json_data = decompressed_bytes.decode('utf-8')
            data = json.loads(json_data)
            
            return data
            
        except Exception as e:
            logger.error(f"解压缩翻译数据失败: {e}")
            raise
            
    async def train_compression_dictionary(
        self,
        locale_code: str,
        sample_data: List[Dict[str, Any]],
        force_retrain: bool = False
    ) -> Optional[CompressionDictionary]:
        """
        训练压缩字典
        
        Args:
            locale_code: 语言代码
            sample_data: 训练样本数据
            force_retrain: 强制重新训练
        """
        try:
            # 检查是否需要训练
            existing_dict = await self._get_dictionary_by_locale(locale_code)
            if existing_dict and not force_retrain:
                # 检查字典是否足够新
                days_old = (datetime.now() - existing_dict.creation_time).days
                if days_old < 30 and existing_dict.effectiveness_score > 0.7:
                    logger.debug(f"字典 {locale_code} 仍然有效，跳过训练")
                    return existing_dict
                    
            if len(sample_data) < 10:
                logger.warning(f"训练样本不足: {locale_code}, 样本数: {len(sample_data)}")
                return None
                
            # 准备训练数据
            training_samples = []
            for data in sample_data:
                json_str = json.dumps(data, ensure_ascii=False, separators=(',', ':'))
                training_samples.append(json_str.encode('utf-8'))
                
            # 检测语言族
            combined_text = "\n".join([json.dumps(data, ensure_ascii=False) for data in sample_data])
            language_family = await self._detect_language_family(combined_text, locale_code)
            
            # 训练字典
            dictionary_data = await self._train_zstd_dictionary(training_samples)
            
            if not dictionary_data:
                logger.warning(f"字典训练失败: {locale_code}")
                return None
                
            # 创建字典对象
            dictionary_id = f"{locale_code}_{language_family.value}_{int(time.time())}"
            dictionary = CompressionDictionary(
                dictionary_id=dictionary_id,
                locale_code=locale_code,
                language_family=language_family,
                dictionary_data=dictionary_data,
                sample_size=len(sample_data),
                creation_time=datetime.now(),
                last_used=datetime.now(),
                usage_count=0,
                effectiveness_score=0.0,
                size_bytes=len(dictionary_data)
            )
            
            # 测试字典效果
            effectiveness = await self._test_dictionary_effectiveness(dictionary, training_samples)
            dictionary.effectiveness_score = effectiveness
            
            # 保存字典
            await self._save_dictionary(dictionary)
            
            # 缓存字典
            self.dictionaries[dictionary_id] = dictionary
            
            logger.info(f"字典训练完成: {locale_code}, ID: {dictionary_id}, "
                       f"效果评分: {effectiveness:.2%}, 大小: {len(dictionary_data)} bytes")
            
            return dictionary
            
        except Exception as e:
            logger.error(f"训练压缩字典失败: {locale_code}: {e}")
            return None
            
    async def get_compression_statistics(self) -> Dict[str, Any]:
        """获取压缩统计信息"""
        try:
            # 从数据库加载最新统计
            await self._load_compression_stats()
            
            return {
                "service": "localized_compression",
                "total_compressions": self.stats.total_compressions,
                "total_bytes_processed": self.stats.total_bytes_processed,
                "total_bytes_saved": self.stats.total_bytes_saved,
                "average_compression_ratio": self.stats.average_compression_ratio,
                "average_compression_time_ms": self.stats.average_compression_time_ms,
                "dictionary_count": len(self.dictionaries),
                "dictionaries": {
                    dict_id: {
                        "locale_code": dictionary.locale_code,
                        "language_family": dictionary.language_family.value,
                        "usage_count": dictionary.usage_count,
                        "effectiveness_score": dictionary.effectiveness_score,
                        "size_bytes": dictionary.size_bytes,
                        "age_days": (datetime.now() - dictionary.creation_time).days
                    }
                    for dict_id, dictionary in self.dictionaries.items()
                },
                "strategy_distribution": {
                    strategy.value: count 
                    for strategy, count in self.stats.strategy_distribution.items()
                },
                "language_families": list(set(
                    dictionary.language_family.value 
                    for dictionary in self.dictionaries.values()
                ))
            }
            
        except Exception as e:
            logger.error(f"获取压缩统计失败: {e}")
            return {"error": str(e)}
            
    async def optimize_dictionaries(self) -> Dict[str, Any]:
        """优化压缩字典"""
        try:
            optimization_results = {
                "cleaned_dictionaries": 0,
                "retrained_dictionaries": 0,
                "new_dictionaries": 0,
                "total_size_saved": 0
            }
            
            # 清理低效字典
            low_effectiveness_threshold = 0.3
            for dict_id, dictionary in list(self.dictionaries.items()):
                if dictionary.effectiveness_score < low_effectiveness_threshold:
                    await self._remove_dictionary(dict_id)
                    optimization_results["cleaned_dictionaries"] += 1
                    optimization_results["total_size_saved"] += dictionary.size_bytes
                    
            # 识别需要重新训练的字典
            retrain_threshold_days = 60
            for dictionary in self.dictionaries.values():
                age_days = (datetime.now() - dictionary.creation_time).days
                if age_days > retrain_threshold_days and dictionary.usage_count > 100:
                    # 获取新的训练样本
                    sample_data = await self._get_recent_translation_samples(
                        dictionary.locale_code, limit=1000
                    )
                    
                    if len(sample_data) >= 50:
                        new_dict = await self.train_compression_dictionary(
                            dictionary.locale_code, sample_data, force_retrain=True
                        )
                        if new_dict and new_dict.effectiveness_score > dictionary.effectiveness_score:
                            await self._remove_dictionary(dictionary.dictionary_id)
                            optimization_results["retrained_dictionaries"] += 1
                            
            # 为没有字典的活跃语言创建字典
            active_locales = await self._get_active_locales_without_dictionaries()
            for locale_code in active_locales:
                sample_data = await self._get_recent_translation_samples(
                    locale_code, limit=500
                )
                
                if len(sample_data) >= 20:
                    new_dict = await self.train_compression_dictionary(
                        locale_code, sample_data
                    )
                    if new_dict:
                        optimization_results["new_dictionaries"] += 1
                        
            logger.info(f"字典优化完成: {optimization_results}")
            return optimization_results
            
        except Exception as e:
            logger.error(f"优化字典失败: {e}")
            return {"error": str(e)}
            
    # ============================================================================
    # 私有方法
    # ============================================================================
    
    async def _detect_language_family(self, text: str, locale_code: str) -> LanguageFamily:
        """检测语言族"""
        import re
        
        # 首先基于locale_code进行快速判断
        locale_family_mapping = {
            'zh': LanguageFamily.CJK,
            'ja': LanguageFamily.CJK,
            'ko': LanguageFamily.CJK,
            'ru': LanguageFamily.CYRILLIC,
            'bg': LanguageFamily.CYRILLIC,
            'sr': LanguageFamily.CYRILLIC,
            'ar': LanguageFamily.ARABIC,
            'fa': LanguageFamily.ARABIC,
            'hi': LanguageFamily.DEVANAGARI,
            'ne': LanguageFamily.DEVANAGARI
        }
        
        locale_prefix = locale_code.split('_')[0].lower()
        if locale_prefix in locale_family_mapping:
            return locale_family_mapping[locale_prefix]
            
        # 基于文本内容分析
        text_length = len(text)
        if text_length == 0:
            return LanguageFamily.UNKNOWN
            
        for family, config in self.language_detection_patterns.items():
            char_count = 0
            for pattern in config["patterns"]:
                matches = re.findall(pattern, text)
                char_count += len(''.join(matches))
                
            ratio = char_count / text_length
            if ratio >= config["threshold"]:
                return family
                
        return LanguageFamily.LATIN  # 默认为拉丁语族
        
    async def _choose_adaptive_strategy(
        self, 
        data: bytes, 
        language_family: LanguageFamily, 
        locale_code: str
    ) -> CompressionStrategy:
        """选择自适应压缩策略"""
        
        data_size = len(data)
        
        # 小数据使用快速压缩
        if data_size < self.adaptive_thresholds["small_data_threshold"]:
            return CompressionStrategy.FAST
            
        # 大数据使用高压缩率
        if data_size > self.adaptive_thresholds["large_data_threshold"]:
            return CompressionStrategy.HIGH
            
        # 分析数据特征
        repetition_ratio = await self._analyze_repetition_ratio(data)
        
        # CJK语言通常有更好的压缩效果
        if language_family == LanguageFamily.CJK:
            if repetition_ratio > 0.3:
                return CompressionStrategy.HIGH
            else:
                return CompressionStrategy.BALANCED
                
        # 重复内容较多时使用高压缩率
        if repetition_ratio > 0.4:
            return CompressionStrategy.HIGH
            
        # 默认平衡策略
        return CompressionStrategy.BALANCED
        
    async def _analyze_repetition_ratio(self, data: bytes) -> float:
        """分析数据重复率"""
        try:
            # 简化实现：计算4字节滑动窗口的重复率
            if len(data) < 8:
                return 0.0
                
            chunk_size = 4
            chunks = set()
            total_chunks = 0
            
            for i in range(len(data) - chunk_size + 1):
                chunk = data[i:i + chunk_size]
                chunks.add(chunk)
                total_chunks += 1
                
            if total_chunks == 0:
                return 0.0
                
            unique_ratio = len(chunks) / total_chunks
            repetition_ratio = 1.0 - unique_ratio
            
            return repetition_ratio
            
        except Exception:
            return 0.0
            
    async def _get_or_create_dictionary(
        self, 
        locale_code: str, 
        language_family: LanguageFamily
    ) -> Optional[CompressionDictionary]:
        """获取或创建压缩字典"""
        
        # 首先查找缓存
        for dictionary in self.dictionaries.values():
            if dictionary.locale_code == locale_code:
                return dictionary
                
        # 从数据库加载
        dictionary = await self._load_dictionary_from_db(locale_code)
        if dictionary:
            self.dictionaries[dictionary.dictionary_id] = dictionary
            return dictionary
            
        # 尝试创建新字典
        sample_data = await self._get_recent_translation_samples(locale_code, limit=200)
        if len(sample_data) >= 10:
            return await self.train_compression_dictionary(locale_code, sample_data)
            
        return None
        
    async def _compress_with_dictionary(
        self,
        data: bytes,
        dictionary: Optional[CompressionDictionary],
        strategy: CompressionStrategy
    ) -> bytes:
        """使用字典压缩数据"""
        
        config = self.strategy_configs[strategy]
        
        # 创建压缩器
        if dictionary:
            cctx = zstd.ZstdCompressor(
                level=config["level"],
                dict_data=dictionary.dictionary_data,
                write_content_size=True,
                write_dict_id=True
            )
        else:
            cctx = zstd.ZstdCompressor(
                level=config["level"],
                write_content_size=True
            )
            
        # 执行压缩
        compressed_data = cctx.compress(data)
        return compressed_data
        
    async def _decompress_with_dictionary(
        self,
        compressed_data: bytes,
        dictionary: Optional[CompressionDictionary]
    ) -> bytes:
        """使用字典解压缩数据"""
        
        # 创建解压缩器
        if dictionary:
            dctx = zstd.ZstdDecompressor(dict_data=dictionary.dictionary_data)
        else:
            dctx = zstd.ZstdDecompressor()
            
        # 执行解压缩
        decompressed_data = dctx.decompress(compressed_data)
        return decompressed_data
        
    async def _train_zstd_dictionary(self, samples: List[bytes]) -> Optional[bytes]:
        """训练ZSTD字典"""
        try:
            if not samples:
                return None
                
            # 合并所有样本
            combined_size = sum(len(sample) for sample in samples)
            if combined_size < 1024:  # 样本太小
                return None
                
            # 设置字典大小（不超过样本总大小的10%，最小8KB，最大64KB）
            dict_size = max(8192, min(65536, combined_size // 10))
            
            # 训练字典
            dictionary_data = zstd.train_dictionary(dict_size, samples)
            
            if len(dictionary_data) < 1024:  # 字典太小
                return None
                
            return dictionary_data
            
        except Exception as e:
            logger.error(f"训练ZSTD字典失败: {e}")
            return None
            
    async def _test_dictionary_effectiveness(
        self,
        dictionary: CompressionDictionary,
        test_samples: List[bytes]
    ) -> float:
        """测试字典效果"""
        try:
            if not test_samples:
                return 0.0
                
            total_original_size = 0
            total_compressed_size_with_dict = 0
            total_compressed_size_without_dict = 0
            
            cctx_with_dict = zstd.ZstdCompressor(
                level=3, dict_data=dictionary.dictionary_data
            )
            cctx_without_dict = zstd.ZstdCompressor(level=3)
            
            for sample in test_samples[:20]:  # 测试前20个样本
                original_size = len(sample)
                
                compressed_with_dict = cctx_with_dict.compress(sample)
                compressed_without_dict = cctx_without_dict.compress(sample)
                
                total_original_size += original_size
                total_compressed_size_with_dict += len(compressed_with_dict)
                total_compressed_size_without_dict += len(compressed_without_dict)
                
            if total_original_size == 0:
                return 0.0
                
            # 计算字典的效果提升
            ratio_with_dict = total_compressed_size_with_dict / total_original_size
            ratio_without_dict = total_compressed_size_without_dict / total_original_size
            
            improvement = (ratio_without_dict - ratio_with_dict) / ratio_without_dict
            return max(0.0, improvement)
            
        except Exception as e:
            logger.error(f"测试字典效果失败: {e}")
            return 0.0
            
    # 数据库操作方法的占位符实现
    async def _load_existing_dictionaries(self):
        """从数据库加载现有字典"""
        # TODO: 实现从数据库加载字典
        pass
        
    async def _cleanup_expired_dictionaries(self):
        """清理过期字典"""
        # TODO: 实现清理过期字典
        pass
        
    async def _save_dictionary(self, dictionary: CompressionDictionary):
        """保存字典到数据库"""
        # TODO: 实现保存字典到数据库
        pass
        
    async def _load_dictionary_from_db(self, locale_code: str) -> Optional[CompressionDictionary]:
        """从数据库加载字典"""
        # TODO: 实现从数据库加载字典
        return None
        
    async def _get_dictionary_by_id(self, dictionary_id: str) -> Optional[CompressionDictionary]:
        """根据ID获取字典"""
        return self.dictionaries.get(dictionary_id)
        
    async def _get_dictionary_by_locale(self, locale_code: str) -> Optional[CompressionDictionary]:
        """根据语言代码获取字典"""
        for dictionary in self.dictionaries.values():
            if dictionary.locale_code == locale_code:
                return dictionary
        return None
        
    async def _remove_dictionary(self, dictionary_id: str):
        """删除字典"""
        # TODO: 实现从数据库删除字典
        self.dictionaries.pop(dictionary_id, None)
        
    async def _get_recent_translation_samples(self, locale_code: str, limit: int = 200) -> List[Dict[str, Any]]:
        """获取最近的翻译样本"""
        # TODO: 实现从数据库获取翻译样本
        return []
        
    async def _get_active_locales_without_dictionaries(self) -> List[str]:
        """获取没有字典的活跃语言代码"""
        # TODO: 实现查询活跃语言
        return []
        
    async def _update_compression_stats(
        self, 
        uncompressed_size: int, 
        compressed_size: int, 
        compression_time_ms: int,
        strategy: CompressionStrategy,
        dictionary_id: Optional[str]
    ):
        """更新压缩统计"""
        self.stats.total_compressions += 1
        self.stats.total_bytes_processed += uncompressed_size
        self.stats.total_bytes_saved += (uncompressed_size - compressed_size)
        
        # 更新平均值
        total_ratio = self.stats.total_bytes_saved / self.stats.total_bytes_processed
        self.stats.average_compression_ratio = total_ratio
        
        # 更新平均时间
        total_time = self.stats.average_compression_time_ms * (self.stats.total_compressions - 1)
        self.stats.average_compression_time_ms = (total_time + compression_time_ms) / self.stats.total_compressions
        
        # 更新策略分布
        self.stats.strategy_distribution[strategy] += 1
        
        # 更新字典使用统计
        if dictionary_id:
            self.stats.dictionary_usage[dictionary_id] = self.stats.dictionary_usage.get(dictionary_id, 0) + 1
            
    async def _update_dictionary_effectiveness(self, dictionary: CompressionDictionary, compression_ratio: float):
        """更新字典效果评分"""
        # 使用指数移动平均更新效果评分
        alpha = 0.1  # 学习率
        dictionary.effectiveness_score = (
            alpha * compression_ratio + (1 - alpha) * dictionary.effectiveness_score
        )
        
    async def _load_compression_stats(self):
        """从数据库加载压缩统计"""
        # TODO: 实现从数据库加载统计信息
        pass


# 全局实例
_localized_compression_service: Optional[LocalizedCompressionService] = None


def get_localized_compression_service() -> LocalizedCompressionService:
    """获取全局本地化压缩服务实例"""
    global _localized_compression_service
    if _localized_compression_service is None:
        _localized_compression_service = LocalizedCompressionService()
        logger.info("本地化压缩服务已初始化")
    return _localized_compression_service