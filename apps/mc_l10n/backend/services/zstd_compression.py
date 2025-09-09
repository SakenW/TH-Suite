#!/usr/bin/env python
"""
Zstd压缩中间件
基于locale字典的自适应压缩服务，优化翻译文本的压缩效率
"""

import zstandard as zstd
import io
import json
from typing import Dict, List, Optional, Any, Union, Tuple
from pathlib import Path
from dataclasses import dataclass, asdict
from enum import Enum
import structlog

logger = structlog.get_logger(__name__)


class CompressionLevel(Enum):
    """压缩级别"""
    FAST = 1       # 快速压缩，低CPU使用
    BALANCED = 3   # 平衡模式
    HIGH = 6       # 高压缩比
    MAXIMUM = 22   # 最大压缩比


@dataclass
class CompressionStats:
    """压缩统计信息"""
    original_size: int
    compressed_size: int
    compression_level: int
    locale: Optional[str] = None
    dictionary_used: bool = False
    compression_ratio: float = 0.0
    
    def __post_init__(self):
        if self.original_size > 0:
            self.compression_ratio = self.compressed_size / self.original_size
        else:
            self.compression_ratio = 0.0


@dataclass
class LocaleDictionary:
    """Locale字典"""
    locale: str
    dictionary_data: bytes  # 用于持久化的原始字节数据
    dictionary_obj: 'zstd.ZstdCompressionDict'  # 用于压缩的字典对象
    size: int
    samples_count: int
    created_at: str
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "locale": self.locale,
            "size": self.size,
            "samples_count": self.samples_count,
            "created_at": self.created_at
        }


class ZstdCompressionService:
    """Zstd压缩服务"""
    
    def __init__(self, 
                 default_level: CompressionLevel = CompressionLevel.BALANCED,
                 enable_dictionaries: bool = True,
                 max_dictionary_size: int = 100 * 1024,  # 100KB
                 cache_size: int = 50):
        self.default_level = default_level
        self.enable_dictionaries = enable_dictionaries
        self.max_dictionary_size = max_dictionary_size
        
        # 字典缓存
        self.locale_dictionaries: Dict[str, LocaleDictionary] = {}
        self.cache_size = cache_size
        
        # 训练样本缓存
        self.training_samples: Dict[str, List[bytes]] = {}
        self.max_samples_per_locale = 1000
        
        # 统计信息
        self.compression_stats: List[CompressionStats] = []
        
        logger.info("Zstd压缩服务初始化",
                   default_level=default_level.value,
                   enable_dictionaries=enable_dictionaries,
                   max_dict_size_kb=max_dictionary_size//1024)
    
    def add_training_sample(self, locale: str, content: Union[str, bytes, Dict]) -> None:
        """添加训练样本用于字典生成"""
        if not self.enable_dictionaries:
            return
        
        # 转换为bytes
        if isinstance(content, str):
            sample_bytes = content.encode('utf-8')
        elif isinstance(content, dict):
            sample_bytes = json.dumps(content, ensure_ascii=False).encode('utf-8')
        else:
            sample_bytes = content
        
        if locale not in self.training_samples:
            self.training_samples[locale] = []
        
        samples = self.training_samples[locale]
        if len(samples) < self.max_samples_per_locale:
            samples.append(sample_bytes)
            logger.debug("添加训练样本", 
                        locale=locale, 
                        sample_size=len(sample_bytes),
                        total_samples=len(samples))
    
    def train_dictionary(self, locale: str, force_retrain: bool = False) -> bool:
        """为指定locale训练压缩字典"""
        if not self.enable_dictionaries:
            return False
        
        if locale in self.locale_dictionaries and not force_retrain:
            logger.debug("字典已存在", locale=locale)
            return True
        
        if locale not in self.training_samples or not self.training_samples[locale]:
            logger.warning("没有训练样本", locale=locale)
            return False
        
        samples = self.training_samples[locale]
        if len(samples) < 10:  # 至少需要10个样本
            logger.info("训练样本不足", locale=locale, samples_count=len(samples))
            return False
        
        # 检查样本总大小 - zstd需要足够的训练数据
        total_sample_size = sum(len(sample) for sample in samples)
        min_training_size = 8192  # 至少需要8KB样本数据
        if total_sample_size < min_training_size:
            logger.info("训练样本数据量不足", locale=locale, 
                       samples_count=len(samples), 
                       total_size=total_sample_size,
                       required_size=min_training_size)
            return False
        
        try:
            # 训练字典
            dict_obj = zstd.train_dictionary(self.max_dictionary_size, samples)
            
            # 提取字典的原始字节数据用于持久化
            dict_data = dict_obj.as_bytes()
            
            # 保存字典（同时保存对象和字节数据）
            from datetime import datetime
            locale_dict = LocaleDictionary(
                locale=locale,
                dictionary_data=dict_data,
                dictionary_obj=dict_obj,
                size=len(dict_data),
                samples_count=len(samples),
                created_at=datetime.now().isoformat()
            )
            
            self.locale_dictionaries[locale] = locale_dict
            
            logger.info("字典训练完成",
                       locale=locale,
                       dict_size_kb=len(dict_data)//1024,
                       samples_used=len(samples))
            
            return True
            
        except Exception as e:
            logger.error("字典训练失败", locale=locale, error=str(e))
            return False
    
    def compress(self, 
                 data: Union[str, bytes, Dict], 
                 locale: Optional[str] = None,
                 level: Optional[CompressionLevel] = None) -> Tuple[bytes, CompressionStats]:
        """压缩数据"""
        # 转换为bytes
        if isinstance(data, str):
            data_bytes = data.encode('utf-8')
        elif isinstance(data, dict):
            data_bytes = json.dumps(data, ensure_ascii=False).encode('utf-8')
        else:
            data_bytes = data
        
        original_size = len(data_bytes)
        compression_level = (level or self.default_level).value
        
        # 选择字典
        compression_dict_obj = None
        dictionary_used = False
        
        if self.enable_dictionaries and locale and locale in self.locale_dictionaries:
            compression_dict_obj = self.locale_dictionaries[locale].dictionary_obj
            dictionary_used = True
        
        try:
            # 创建压缩器
            if compression_dict_obj:
                compressor = zstd.ZstdCompressor(level=compression_level, dict_data=compression_dict_obj)
            else:
                compressor = zstd.ZstdCompressor(level=compression_level)
            
            # 执行压缩
            compressed_data = compressor.compress(data_bytes)
            
            # 统计信息
            stats = CompressionStats(
                original_size=original_size,
                compressed_size=len(compressed_data),
                compression_level=compression_level,
                locale=locale,
                dictionary_used=dictionary_used
            )
            
            self.compression_stats.append(stats)
            
            logger.debug("数据压缩完成",
                        original_size=original_size,
                        compressed_size=len(compressed_data),
                        ratio=f"{stats.compression_ratio:.3f}",
                        locale=locale,
                        dict_used=dictionary_used)
            
            return compressed_data, stats
            
        except Exception as e:
            logger.error("压缩失败", 
                        original_size=original_size,
                        locale=locale,
                        error=str(e))
            raise
    
    def decompress(self, 
                   compressed_data: bytes, 
                   locale: Optional[str] = None) -> bytes:
        """解压缩数据"""
        # 选择字典
        compression_dict_obj = None
        if self.enable_dictionaries and locale and locale in self.locale_dictionaries:
            compression_dict_obj = self.locale_dictionaries[locale].dictionary_obj
        
        try:
            # 创建解压器
            if compression_dict_obj:
                decompressor = zstd.ZstdDecompressor(dict_data=compression_dict_obj)
            else:
                decompressor = zstd.ZstdDecompressor()
            
            # 执行解压
            decompressed_data = decompressor.decompress(compressed_data)
            
            logger.debug("数据解压完成",
                        compressed_size=len(compressed_data),
                        decompressed_size=len(decompressed_data),
                        locale=locale)
            
            return decompressed_data
            
        except Exception as e:
            logger.error("解压失败", 
                        compressed_size=len(compressed_data),
                        locale=locale,
                        error=str(e))
            raise
    
    def compress_json(self, data: Dict, locale: Optional[str] = None) -> Tuple[bytes, CompressionStats]:
        """压缩JSON数据"""
        return self.compress(data, locale)
    
    def decompress_json(self, compressed_data: bytes, locale: Optional[str] = None) -> Dict:
        """解压JSON数据"""
        decompressed_bytes = self.decompress(compressed_data, locale)
        return json.loads(decompressed_bytes.decode('utf-8'))
    
    def get_compression_stats(self, locale: Optional[str] = None) -> Dict[str, Any]:
        """获取压缩统计信息"""
        if locale:
            stats = [s for s in self.compression_stats if s.locale == locale]
        else:
            stats = self.compression_stats
        
        if not stats:
            return {"total_operations": 0}
        
        total_original = sum(s.original_size for s in stats)
        total_compressed = sum(s.compressed_size for s in stats)
        avg_ratio = sum(s.compression_ratio for s in stats) / len(stats)
        dict_usage = sum(1 for s in stats if s.dictionary_used) / len(stats)
        
        return {
            "total_operations": len(stats),
            "total_original_bytes": total_original,
            "total_compressed_bytes": total_compressed,
            "overall_ratio": total_compressed / total_original if total_original > 0 else 0,
            "average_ratio": avg_ratio,
            "space_saved_bytes": total_original - total_compressed,
            "space_saved_percent": ((total_original - total_compressed) / total_original * 100) if total_original > 0 else 0,
            "dictionary_usage_percent": dict_usage * 100,
            "locale": locale
        }
    
    def list_dictionaries(self) -> List[Dict[str, Any]]:
        """列出所有字典信息"""
        return [d.to_dict() for d in self.locale_dictionaries.values()]
    
    def save_dictionaries(self, directory: Path) -> None:
        """保存字典到文件"""
        if not self.enable_dictionaries:
            return
        
        directory = Path(directory)
        directory.mkdir(parents=True, exist_ok=True)
        
        for locale, locale_dict in self.locale_dictionaries.items():
            dict_file = directory / f"{locale}.zstd.dict"
            with open(dict_file, 'wb') as f:
                f.write(locale_dict.dictionary_data)
            
            # 保存元数据
            meta_file = directory / f"{locale}.zstd.meta.json"
            with open(meta_file, 'w', encoding='utf-8') as f:
                json.dump(locale_dict.to_dict(), f, ensure_ascii=False, indent=2)
        
        logger.info("字典保存完成", 
                   directory=str(directory),
                   dictionaries_count=len(self.locale_dictionaries))
    
    def load_dictionaries(self, directory: Path) -> None:
        """从文件加载字典"""
        if not self.enable_dictionaries:
            return
        
        directory = Path(directory)
        if not directory.exists():
            logger.warning("字典目录不存在", directory=str(directory))
            return
        
        loaded_count = 0
        for dict_file in directory.glob("*.zstd.dict"):
            locale = dict_file.stem.replace('.zstd', '')
            meta_file = directory / f"{locale}.zstd.meta.json"
            
            try:
                # 加载字典数据
                with open(dict_file, 'rb') as f:
                    dict_data = f.read()
                
                # 加载元数据
                meta_data = {}
                if meta_file.exists():
                    with open(meta_file, 'r', encoding='utf-8') as f:
                        meta_data = json.load(f)
                
                # 从字节数据重新创建压缩字典对象
                dict_obj = zstd.ZstdCompressionDict(dict_data)
                
                # 创建字典对象
                locale_dict = LocaleDictionary(
                    locale=locale,
                    dictionary_data=dict_data,
                    dictionary_obj=dict_obj,
                    size=len(dict_data),
                    samples_count=meta_data.get("samples_count", 0),
                    created_at=meta_data.get("created_at", "unknown")
                )
                
                self.locale_dictionaries[locale] = locale_dict
                loaded_count += 1
                
                logger.debug("字典加载成功", 
                           locale=locale,
                           dict_size_kb=len(dict_data)//1024)
                
            except Exception as e:
                logger.error("字典加载失败", 
                           locale=locale,
                           file=str(dict_file),
                           error=str(e))
        
        logger.info("字典加载完成",
                   directory=str(directory),
                   loaded_count=loaded_count)


# 全局压缩服务实例
_compression_service: Optional[ZstdCompressionService] = None


def get_compression_service() -> ZstdCompressionService:
    """获取压缩服务实例 (单例)"""
    global _compression_service
    if _compression_service is None:
        _compression_service = ZstdCompressionService()
        logger.info("Zstd压缩服务单例初始化完成")
    return _compression_service


def compress_translation_data(data: Dict, locale: str) -> Tuple[bytes, CompressionStats]:
    """压缩翻译数据的便捷函数"""
    service = get_compression_service()
    return service.compress_json(data, locale)


def decompress_translation_data(compressed_data: bytes, locale: str) -> Dict:
    """解压翻译数据的便捷函数"""
    service = get_compression_service()
    return service.decompress_json(compressed_data, locale)