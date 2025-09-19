"""
翻译数据提取器 - 专注于翻译数据的结构化提取与压缩传输
基于TH-Suite扫描架构的高性能翻译数据处理模块
"""

import asyncio
import json
import logging
from datetime import datetime
from typing import Dict, List, Optional, Tuple, Any, Set
from dataclasses import dataclass, asdict
from enum import Enum
import blake3
from pathlib import Path

from infrastructure.repositories.repository_factory import get_repository_factory
from infrastructure.services.multi_layer_cache_service import (
    get_multi_layer_cache_service, CacheType
)

logger = logging.getLogger(__name__)


class ExtractionType(Enum):
    """提取类型枚举"""
    FULL = "full"                    # 全量提取
    INCREMENTAL = "incremental"      # 增量提取（基于指纹）
    TARGETED = "targeted"            # 指定目标提取
    DIFFERENTIAL = "differential"    # 差异提取


class DataCategory(Enum):
    """数据类别枚举"""
    TRANSLATION_ENTRIES = "translation_entries"
    METADATA = "metadata"
    MOD_INFO = "mod_info"
    LANGUAGE_FILES = "language_files"
    PACK_CONFIGS = "pack_configs"


@dataclass
class TranslationDelta:
    """翻译数据增量信息"""
    operation: str  # CREATE, UPDATE, DELETE
    entity_type: str
    entity_id: str
    old_value: Optional[Any] = None
    new_value: Optional[Any] = None
    timestamp: datetime = None
    mod_id: Optional[str] = None
    locale_code: Optional[str] = None


@dataclass
class ExtractionResult:
    """提取结果"""
    extraction_id: str
    extraction_type: ExtractionType
    total_entries: int
    compressed_size: int
    uncompressed_size: int
    compression_ratio: float
    data_fingerprint: str
    key_set_fingerprint: str
    categories: Dict[DataCategory, int]
    deltas: List[TranslationDelta]
    metadata: Dict[str, Any]
    extraction_time: datetime
    data_payload: Optional[bytes] = None


@dataclass
class KeySetSignature:
    """键集签名 - 用于键集指纹优化"""
    mod_id: str
    locale_code: str
    key_count: int
    key_fingerprint: str
    value_fingerprint: str
    last_updated: datetime


class TranslationDataExtractor:
    """翻译数据提取器"""
    
    def __init__(self):
        self.factory = get_repository_factory()
        self.cache_service = get_multi_layer_cache_service()
        
        # 键集缓存：mod_id -> locale -> KeySetSignature
        self.key_set_cache: Dict[str, Dict[str, KeySetSignature]] = {}
        
        # 差异检测配置
        self.diff_config = {
            "chunk_size": 10000,           # 差异检测分块大小
            "batch_threshold": 5000,       # 批处理阈值
            "fingerprint_cache_ttl": 3600, # 指纹缓存TTL（秒）
            "enable_key_set_optimization": True,  # 启用键集优化
            "compression_level": 3,        # 压缩级别（1-9）
        }
        
    async def extract_translation_data(
        self, 
        extraction_type: ExtractionType,
        project_uid: Optional[str] = None,
        mod_ids: Optional[List[str]] = None,
        locale_codes: Optional[List[str]] = None,
        since_timestamp: Optional[datetime] = None
    ) -> ExtractionResult:
        """
        提取翻译数据
        
        Args:
            extraction_type: 提取类型
            project_uid: 项目UID过滤
            mod_ids: MOD ID列表过滤
            locale_codes: 语言代码列表过滤
            since_timestamp: 增量提取的起始时间戳
        """
        extraction_id = f"extract_{blake3.blake3(str(datetime.now()).encode()).hexdigest()[:16]}"
        logger.info(f"开始提取翻译数据: {extraction_id}, 类型: {extraction_type.value}")
        
        start_time = datetime.now()
        
        try:
            # 根据提取类型选择策略
            if extraction_type == ExtractionType.FULL:
                result = await self._extract_full_data(extraction_id, project_uid, mod_ids, locale_codes)
            elif extraction_type == ExtractionType.INCREMENTAL:
                result = await self._extract_incremental_data(extraction_id, since_timestamp, project_uid, mod_ids, locale_codes)
            elif extraction_type == ExtractionType.TARGETED:
                result = await self._extract_targeted_data(extraction_id, project_uid, mod_ids, locale_codes)
            elif extraction_type == ExtractionType.DIFFERENTIAL:
                result = await self._extract_differential_data(extraction_id, project_uid, mod_ids, locale_codes)
            else:
                raise ValueError(f"不支持的提取类型: {extraction_type}")
                
            # 更新统计信息
            result.extraction_time = datetime.now()
            duration = (result.extraction_time - start_time).total_seconds()
            
            logger.info(f"翻译数据提取完成: {extraction_id}, 耗时: {duration:.2f}秒, "
                       f"条目: {result.total_entries}, 压缩率: {result.compression_ratio:.2%}")
            
            return result
            
        except Exception as e:
            logger.error(f"翻译数据提取失败: {extraction_id}: {e}")
            raise
            
    async def _extract_full_data(
        self, 
        extraction_id: str,
        project_uid: Optional[str] = None,
        mod_ids: Optional[List[str]] = None,
        locale_codes: Optional[List[str]] = None
    ) -> ExtractionResult:
        """提取全量翻译数据"""
        
        # 构建查询条件
        query_conditions = []
        query_params = []
        
        if project_uid:
            query_conditions.append("p.project_uid = ?")
            query_params.append(project_uid)
            
        if mod_ids:
            placeholders = ",".join("?" * len(mod_ids))
            query_conditions.append(f"m.modid IN ({placeholders})")
            query_params.extend(mod_ids)
            
        if locale_codes:
            placeholders = ",".join("?" * len(locale_codes))
            query_conditions.append(f"lf.locale_code IN ({placeholders})")
            query_params.extend(locale_codes)
            
        where_clause = " AND ".join(query_conditions) if query_conditions else "1=1"
        
        # 提取翻译条目
        translation_entries = await self._query_translation_entries(where_clause, query_params)
        
        # 提取元数据
        metadata = await self._query_metadata(where_clause, query_params)
        
        # 构建数据包
        data_package = {
            "translation_entries": translation_entries,
            "metadata": metadata,
            "extraction_meta": {
                "type": "full",
                "timestamp": datetime.now().isoformat(),
                "conditions": {
                    "project_uid": project_uid,
                    "mod_ids": mod_ids,
                    "locale_codes": locale_codes
                }
            }
        }
        
        # 压缩数据
        compressed_data, compression_stats = await self._compress_data_package(data_package)
        
        # 计算指纹
        data_fingerprint = blake3.blake3(compressed_data).hexdigest()
        key_set_fingerprint = await self._calculate_key_set_fingerprint(translation_entries)
        
        # 统计分类
        categories = await self._categorize_data(translation_entries, metadata)
        
        return ExtractionResult(
            extraction_id=extraction_id,
            extraction_type=ExtractionType.FULL,
            total_entries=len(translation_entries),
            compressed_size=len(compressed_data),
            uncompressed_size=compression_stats["uncompressed_size"],
            compression_ratio=compression_stats["compression_ratio"],
            data_fingerprint=data_fingerprint,
            key_set_fingerprint=key_set_fingerprint,
            categories=categories,
            deltas=[],  # 全量提取无增量信息
            metadata=data_package["extraction_meta"],
            extraction_time=datetime.now(),
            data_payload=compressed_data
        )
        
    async def _extract_incremental_data(
        self,
        extraction_id: str,
        since_timestamp: Optional[datetime] = None,
        project_uid: Optional[str] = None,
        mod_ids: Optional[List[str]] = None,
        locale_codes: Optional[List[str]] = None
    ) -> ExtractionResult:
        """提取增量翻译数据"""
        
        if since_timestamp is None:
            # 从缓存获取最后同步时间戳
            cache_key = f"last_sync_timestamp:{project_uid or 'global'}"
            since_timestamp = await self.cache_service.get(cache_key, CacheType.METADATA)
            if since_timestamp is None:
                # 如果没有历史记录，回退到全量提取
                logger.warning("没有找到上次同步时间戳，回退到全量提取")
                return await self._extract_full_data(extraction_id, project_uid, mod_ids, locale_codes)
                
        # 查询增量变更
        deltas = await self._query_incremental_changes(since_timestamp, project_uid, mod_ids, locale_codes)
        
        if not deltas:
            # 没有变更，返回空结果
            return ExtractionResult(
                extraction_id=extraction_id,
                extraction_type=ExtractionType.INCREMENTAL,
                total_entries=0,
                compressed_size=0,
                uncompressed_size=0,
                compression_ratio=0.0,
                data_fingerprint="",
                key_set_fingerprint="",
                categories={},
                deltas=[],
                metadata={"message": "没有增量变更"},
                extraction_time=datetime.now()
            )
            
        # 构建增量数据包
        incremental_package = {
            "deltas": [asdict(delta) for delta in deltas],
            "extraction_meta": {
                "type": "incremental",
                "since_timestamp": since_timestamp.isoformat(),
                "timestamp": datetime.now().isoformat(),
                "conditions": {
                    "project_uid": project_uid,
                    "mod_ids": mod_ids,
                    "locale_codes": locale_codes
                }
            }
        }
        
        # 压缩增量数据
        compressed_data, compression_stats = await self._compress_data_package(incremental_package)
        
        # 计算指纹
        data_fingerprint = blake3.blake3(compressed_data).hexdigest()
        key_set_fingerprint = await self._calculate_delta_key_set_fingerprint(deltas)
        
        return ExtractionResult(
            extraction_id=extraction_id,
            extraction_type=ExtractionType.INCREMENTAL,
            total_entries=len(deltas),
            compressed_size=len(compressed_data),
            uncompressed_size=compression_stats["uncompressed_size"],
            compression_ratio=compression_stats["compression_ratio"],
            data_fingerprint=data_fingerprint,
            key_set_fingerprint=key_set_fingerprint,
            categories={DataCategory.TRANSLATION_ENTRIES: len(deltas)},
            deltas=deltas,
            metadata=incremental_package["extraction_meta"],
            extraction_time=datetime.now(),
            data_payload=compressed_data
        )
        
    async def _extract_targeted_data(
        self,
        extraction_id: str,
        project_uid: Optional[str] = None,
        mod_ids: Optional[List[str]] = None,
        locale_codes: Optional[List[str]] = None
    ) -> ExtractionResult:
        """提取指定目标的翻译数据"""
        
        if not mod_ids and not locale_codes:
            raise ValueError("targeted extraction requires mod_ids or locale_codes")
            
        # 使用缓存的键集指纹进行优化
        cached_signatures = await self._get_cached_key_set_signatures(mod_ids, locale_codes)
        
        # 只提取有变更的MOD和语言组合
        changed_combinations = await self._detect_changed_combinations(cached_signatures, mod_ids, locale_codes)
        
        if not changed_combinations:
            return ExtractionResult(
                extraction_id=extraction_id,
                extraction_type=ExtractionType.TARGETED,
                total_entries=0,
                compressed_size=0,
                uncompressed_size=0,
                compression_ratio=0.0,
                data_fingerprint="",
                key_set_fingerprint="",
                categories={},
                deltas=[],
                metadata={"message": "目标数据无变更"},
                extraction_time=datetime.now()
            )
            
        # 构建目标查询条件
        mod_locale_conditions = []
        for mod_id, locale_code in changed_combinations:
            mod_locale_conditions.append(f"(m.modid = '{mod_id}' AND lf.locale_code = '{locale_code}')")
            
        where_clause = f"({' OR '.join(mod_locale_conditions)})"
        if project_uid:
            where_clause = f"p.project_uid = '{project_uid}' AND ({where_clause})"
            
        # 提取目标数据
        translation_entries = await self._query_translation_entries(where_clause, [])
        metadata = await self._query_metadata(where_clause, [])
        
        # 构建数据包
        targeted_package = {
            "translation_entries": translation_entries,
            "metadata": metadata,
            "changed_combinations": changed_combinations,
            "extraction_meta": {
                "type": "targeted",
                "timestamp": datetime.now().isoformat(),
                "targets": {
                    "mod_ids": mod_ids,
                    "locale_codes": locale_codes,
                    "changed_count": len(changed_combinations)
                }
            }
        }
        
        # 压缩数据
        compressed_data, compression_stats = await self._compress_data_package(targeted_package)
        
        # 计算指纹
        data_fingerprint = blake3.blake3(compressed_data).hexdigest()
        key_set_fingerprint = await self._calculate_key_set_fingerprint(translation_entries)
        
        # 统计分类
        categories = await self._categorize_data(translation_entries, metadata)
        
        return ExtractionResult(
            extraction_id=extraction_id,
            extraction_type=ExtractionType.TARGETED,
            total_entries=len(translation_entries),
            compressed_size=len(compressed_data),
            uncompressed_size=compression_stats["uncompressed_size"],
            compression_ratio=compression_stats["compression_ratio"],
            data_fingerprint=data_fingerprint,
            key_set_fingerprint=key_set_fingerprint,
            categories=categories,
            deltas=[],
            metadata=targeted_package["extraction_meta"],
            extraction_time=datetime.now(),
            data_payload=compressed_data
        )
        
    async def _extract_differential_data(
        self,
        extraction_id: str,
        project_uid: Optional[str] = None,
        mod_ids: Optional[List[str]] = None,
        locale_codes: Optional[List[str]] = None
    ) -> ExtractionResult:
        """提取差异数据（与远程版本比较）"""
        
        # 获取本地版本指纹
        local_fingerprints = await self._calculate_current_fingerprints(project_uid, mod_ids, locale_codes)
        
        # 获取远程版本指纹（模拟）
        remote_fingerprints = await self._get_remote_fingerprints(project_uid, mod_ids, locale_codes)
        
        # 计算差异
        differences = await self._calculate_fingerprint_differences(local_fingerprints, remote_fingerprints)
        
        if not differences:
            return ExtractionResult(
                extraction_id=extraction_id,
                extraction_type=ExtractionType.DIFFERENTIAL,
                total_entries=0,
                compressed_size=0,
                uncompressed_size=0,
                compression_ratio=0.0,
                data_fingerprint="",
                key_set_fingerprint="",
                categories={},
                deltas=[],
                metadata={"message": "本地与远程版本一致"},
                extraction_time=datetime.now()
            )
            
        # 提取差异数据
        differential_entries = await self._extract_differential_entries(differences)
        
        # 构建差异数据包
        differential_package = {
            "differential_entries": differential_entries,
            "local_fingerprints": local_fingerprints,
            "remote_fingerprints": remote_fingerprints,
            "differences": differences,
            "extraction_meta": {
                "type": "differential",
                "timestamp": datetime.now().isoformat(),
                "comparison_base": "remote_version",
                "differences_count": len(differences)
            }
        }
        
        # 压缩差异数据
        compressed_data, compression_stats = await self._compress_data_package(differential_package)
        
        # 计算指纹
        data_fingerprint = blake3.blake3(compressed_data).hexdigest()
        key_set_fingerprint = await self._calculate_key_set_fingerprint(differential_entries)
        
        return ExtractionResult(
            extraction_id=extraction_id,
            extraction_type=ExtractionType.DIFFERENTIAL,
            total_entries=len(differential_entries),
            compressed_size=len(compressed_data),
            uncompressed_size=compression_stats["uncompressed_size"],
            compression_ratio=compression_stats["compression_ratio"],
            data_fingerprint=data_fingerprint,
            key_set_fingerprint=key_set_fingerprint,
            categories={DataCategory.TRANSLATION_ENTRIES: len(differential_entries)},
            deltas=[],
            metadata=differential_package["extraction_meta"],
            extraction_time=datetime.now(),
            data_payload=compressed_data
        )
        
    async def _query_translation_entries(self, where_clause: str, params: List) -> List[Dict]:
        """查询翻译条目"""
        
        query = f"""
            SELECT 
                te.entry_id,
                te.translation_key,
                te.original_value,
                te.translated_value,
                te.translation_status,
                te.last_updated,
                te.file_id,
                lf.locale_code,
                lf.mod_id,
                m.display_name as mod_name,
                p.project_uid
            FROM core_translation_entries te
            JOIN core_language_files lf ON te.file_id = lf.file_id
            JOIN core_mods m ON lf.mod_id = m.modid
            LEFT JOIN core_packs_mods pm ON m.modid = pm.mod_id
            LEFT JOIN core_packs p ON pm.pack_id = p.pack_id
            WHERE {where_clause}
            ORDER BY te.translation_key, lf.locale_code
        """
        
        async with self.factory.get_connection() as conn:
            cursor = await conn.execute(query, params)
            rows = await cursor.fetchall()
            
            return [
                {
                    "entry_id": row[0],
                    "translation_key": row[1],
                    "original_value": row[2],
                    "translated_value": row[3],
                    "translation_status": row[4],
                    "last_updated": row[5],
                    "file_id": row[6],
                    "locale_code": row[7],
                    "mod_id": row[8],
                    "mod_name": row[9],
                    "project_uid": row[10]
                }
                for row in rows
            ]
            
    async def _query_metadata(self, where_clause: str, params: List) -> Dict:
        """查询相关元数据"""
        
        metadata = {}
        
        async with self.factory.get_connection() as conn:
            # 查询MOD信息
            mod_query = f"""
                SELECT DISTINCT m.modid, m.display_name, m.version, m.mod_loader
                FROM core_mods m
                LEFT JOIN core_packs_mods pm ON m.modid = pm.mod_id
                LEFT JOIN core_packs p ON pm.pack_id = p.pack_id
                WHERE {where_clause}
            """
            cursor = await conn.execute(mod_query, params)
            mod_rows = await cursor.fetchall()
            
            metadata["mods"] = [
                {
                    "mod_id": row[0],
                    "display_name": row[1],
                    "version": row[2],
                    "mod_loader": row[3]
                }
                for row in mod_rows
            ]
            
            # 查询语言文件信息
            lang_file_query = f"""
                SELECT DISTINCT lf.file_id, lf.locale_code, lf.file_path, lf.file_size, lf.last_modified
                FROM core_language_files lf
                JOIN core_mods m ON lf.mod_id = m.modid
                LEFT JOIN core_packs_mods pm ON m.modid = pm.mod_id
                LEFT JOIN core_packs p ON pm.pack_id = p.pack_id
                WHERE {where_clause}
            """
            cursor = await conn.execute(lang_file_query, params)
            lang_file_rows = await cursor.fetchall()
            
            metadata["language_files"] = [
                {
                    "file_id": row[0],
                    "locale_code": row[1],
                    "file_path": row[2],
                    "file_size": row[3],
                    "last_modified": row[4]
                }
                for row in lang_file_rows
            ]
            
            # 查询包信息
            pack_query = f"""
                SELECT DISTINCT p.pack_id, p.project_uid, p.pack_name, p.pack_type, p.created_at
                FROM core_packs p
                LEFT JOIN core_packs_mods pm ON p.pack_id = pm.pack_id
                LEFT JOIN core_mods m ON pm.mod_id = m.modid
                WHERE {where_clause}
            """
            cursor = await conn.execute(pack_query, params)
            pack_rows = await cursor.fetchall()
            
            metadata["packs"] = [
                {
                    "pack_id": row[0],
                    "project_uid": row[1],
                    "pack_name": row[2],
                    "pack_type": row[3],
                    "created_at": row[4]
                }
                for row in pack_rows
            ]
            
        return metadata
        
    async def _compress_data_package(self, data_package: Dict) -> Tuple[bytes, Dict]:
        """压缩数据包"""
        
        # 序列化数据
        json_data = json.dumps(data_package, ensure_ascii=False, separators=(',', ':'))
        uncompressed_bytes = json_data.encode('utf-8')
        uncompressed_size = len(uncompressed_bytes)
        
        # 使用zstd压缩（调用现有压缩服务）
        try:
            from infrastructure.services.zstd_compression import get_zstd_compression_service
            compression_service = get_zstd_compression_service()
            
            compressed_bytes = await compression_service.compress_data(
                uncompressed_bytes,
                compression_level=self.diff_config["compression_level"]
            )
            
            compression_ratio = (uncompressed_size - len(compressed_bytes)) / uncompressed_size
            
            return compressed_bytes, {
                "uncompressed_size": uncompressed_size,
                "compressed_size": len(compressed_bytes),
                "compression_ratio": compression_ratio
            }
            
        except Exception as e:
            logger.warning(f"压缩失败，使用原始数据: {e}")
            return uncompressed_bytes, {
                "uncompressed_size": uncompressed_size,
                "compressed_size": uncompressed_size,
                "compression_ratio": 0.0
            }
            
    async def _calculate_key_set_fingerprint(self, translation_entries: List[Dict]) -> str:
        """计算键集指纹"""
        
        # 按MOD和语言分组
        grouped_keys = {}
        for entry in translation_entries:
            mod_id = entry["mod_id"]
            locale_code = entry["locale_code"]
            key = f"{mod_id}:{locale_code}"
            
            if key not in grouped_keys:
                grouped_keys[key] = set()
            grouped_keys[key].add(entry["translation_key"])
            
        # 计算每组的键集指纹
        fingerprints = []
        for group_key, keys in grouped_keys.items():
            sorted_keys = sorted(keys)
            keys_string = "|".join(sorted_keys)
            group_fingerprint = blake3.blake3(keys_string.encode()).hexdigest()
            fingerprints.append(f"{group_key}:{group_fingerprint}")
            
        # 计算总的键集指纹
        combined_fingerprint = "|".join(sorted(fingerprints))
        return blake3.blake3(combined_fingerprint.encode()).hexdigest()
        
    async def _categorize_data(self, translation_entries: List[Dict], metadata: Dict) -> Dict[DataCategory, int]:
        """数据分类统计"""
        
        return {
            DataCategory.TRANSLATION_ENTRIES: len(translation_entries),
            DataCategory.METADATA: 1,
            DataCategory.MOD_INFO: len(metadata.get("mods", [])),
            DataCategory.LANGUAGE_FILES: len(metadata.get("language_files", [])),
            DataCategory.PACK_CONFIGS: len(metadata.get("packs", []))
        }
        
    # 增量相关的私有方法
    async def _query_incremental_changes(
        self,
        since_timestamp: datetime,
        project_uid: Optional[str] = None,
        mod_ids: Optional[List[str]] = None,
        locale_codes: Optional[List[str]] = None
    ) -> List[TranslationDelta]:
        """查询增量变更"""
        
        # 这里应该查询变更日志表，但由于现有架构没有变更日志，
        # 我们使用last_updated字段模拟
        
        query_conditions = [f"te.last_updated > ?"]
        query_params = [since_timestamp.isoformat()]
        
        if project_uid:
            query_conditions.append("p.project_uid = ?")
            query_params.append(project_uid)
            
        if mod_ids:
            placeholders = ",".join("?" * len(mod_ids))
            query_conditions.append(f"m.modid IN ({placeholders})")
            query_params.extend(mod_ids)
            
        if locale_codes:
            placeholders = ",".join("?" * len(locale_codes))
            query_conditions.append(f"lf.locale_code IN ({placeholders})")
            query_params.extend(locale_codes)
            
        where_clause = " AND ".join(query_conditions)
        
        query = f"""
            SELECT 
                te.entry_id,
                te.translation_key,
                te.original_value,
                te.translated_value,
                te.last_updated,
                lf.locale_code,
                lf.mod_id
            FROM core_translation_entries te
            JOIN core_language_files lf ON te.file_id = lf.file_id
            JOIN core_mods m ON lf.mod_id = m.modid
            LEFT JOIN core_packs_mods pm ON m.modid = pm.mod_id
            LEFT JOIN core_packs p ON pm.pack_id = p.pack_id
            WHERE {where_clause}
            ORDER BY te.last_updated
        """
        
        deltas = []
        async with self.factory.get_connection() as conn:
            cursor = await conn.execute(query, query_params)
            rows = await cursor.fetchall()
            
            for row in rows:
                # 简化实现：所有变更都标记为UPDATE
                # 实际应该从变更日志表查询具体操作类型
                delta = TranslationDelta(
                    operation="UPDATE",
                    entity_type="translation_entry",
                    entity_id=row[0],
                    old_value=None,  # 需要从变更日志获取
                    new_value={
                        "translation_key": row[1],
                        "original_value": row[2],
                        "translated_value": row[3]
                    },
                    timestamp=datetime.fromisoformat(row[4]),
                    mod_id=row[6],
                    locale_code=row[5]
                )
                deltas.append(delta)
                
        return deltas
        
    async def _calculate_delta_key_set_fingerprint(self, deltas: List[TranslationDelta]) -> str:
        """计算增量变更的键集指纹"""
        
        affected_keys = set()
        for delta in deltas:
            if delta.new_value and "translation_key" in delta.new_value:
                affected_keys.add(delta.new_value["translation_key"])
                
        sorted_keys = sorted(affected_keys)
        keys_string = "|".join(sorted_keys)
        return blake3.blake3(keys_string.encode()).hexdigest()
        
    # 其他私有方法的占位符实现
    async def _get_cached_key_set_signatures(self, mod_ids: Optional[List[str]], locale_codes: Optional[List[str]]) -> Dict:
        """获取缓存的键集签名"""
        # TODO: 实现键集签名缓存逻辑
        return {}
        
    async def _detect_changed_combinations(self, cached_signatures: Dict, mod_ids: Optional[List[str]], locale_codes: Optional[List[str]]) -> List[Tuple[str, str]]:
        """检测变更的MOD-语言组合"""
        # TODO: 实现变更检测逻辑
        if mod_ids and locale_codes:
            return [(mod_id, locale_code) for mod_id in mod_ids for locale_code in locale_codes]
        return []
        
    async def _calculate_current_fingerprints(self, project_uid: Optional[str], mod_ids: Optional[List[str]], locale_codes: Optional[List[str]]) -> Dict:
        """计算当前版本指纹"""
        # TODO: 实现当前版本指纹计算
        return {}
        
    async def _get_remote_fingerprints(self, project_uid: Optional[str], mod_ids: Optional[List[str]], locale_codes: Optional[List[str]]) -> Dict:
        """获取远程版本指纹"""
        # TODO: 实现远程版本指纹获取
        return {}
        
    async def _calculate_fingerprint_differences(self, local_fingerprints: Dict, remote_fingerprints: Dict) -> List:
        """计算指纹差异"""
        # TODO: 实现指纹差异计算
        return []
        
    async def _extract_differential_entries(self, differences: List) -> List[Dict]:
        """提取差异条目"""
        # TODO: 实现差异条目提取
        return []


# 全局实例
_translation_data_extractor: Optional[TranslationDataExtractor] = None


def get_translation_data_extractor() -> TranslationDataExtractor:
    """获取全局翻译数据提取器实例"""
    global _translation_data_extractor
    if _translation_data_extractor is None:
        _translation_data_extractor = TranslationDataExtractor()
        logger.info("翻译数据提取器已初始化")
    return _translation_data_extractor