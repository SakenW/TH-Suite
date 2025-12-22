"""
Protobuf序列化服务
提供高效的数据序列化和反序列化功能
"""

import sys
import os
from typing import Any, Dict, List, Optional, Union, Type, TypeVar
from datetime import datetime
import json
import time
import gzip
import zlib
from pathlib import Path

# 添加生成的protobuf模块到路径
sys.path.append(os.path.join(os.path.dirname(__file__), '../generated'))

import structlog
from google.protobuf.message import Message
from google.protobuf.json_format import MessageToJson, Parse
from google.protobuf.timestamp_pb2 import Timestamp

try:
    import translation_pb2 as pb
    import translation_pb2_grpc as pb_grpc
except ImportError as e:
    logger = structlog.get_logger(__name__)
    logger.error("无法导入生成的protobuf模块，请先运行编译命令", error=str(e))
    raise

from services.content_addressing import ContentAddressingSystem, HashAlgorithm, compute_cid

logger = structlog.get_logger(__name__)

# 类型变量
ProtoMessage = TypeVar('ProtoMessage', bound=Message)


class ProtobufSerializer:
    """Protobuf序列化器"""
    
    def __init__(
        self,
        enable_compression: bool = True,
        compression_algorithm: str = "zstd",
        enable_content_addressing: bool = True,
        enable_validation: bool = True
    ):
        self.enable_compression = enable_compression
        self.compression_algorithm = compression_algorithm
        self.enable_content_addressing = enable_content_addressing
        self.enable_validation = enable_validation
        
        # 内容寻址系统
        if enable_content_addressing:
            self.content_addressing = ContentAddressingSystem(
                algorithm=HashAlgorithm.BLAKE3,
                enable_caching=True,
                max_cache_entries=10000
            )
        
        # 性能统计
        self.stats = {
            "serializations": 0,
            "deserializations": 0,
            "compression_saves_bytes": 0,
            "content_addressing_hits": 0,
            "validation_errors": 0,
            "average_serialization_time_ms": 0.0,
            "average_deserialization_time_ms": 0.0,
        }
        
        logger.info("Protobuf序列化器初始化", 
                   compression=enable_compression,
                   compression_algorithm=compression_algorithm,
                   content_addressing=enable_content_addressing)
    
    def serialize(self, message: Message, compress: bool = None) -> bytes:
        """序列化Protobuf消息"""
        start_time = time.time()
        
        if compress is None:
            compress = self.enable_compression
        
        try:
            # 验证消息
            if self.enable_validation:
                self._validate_message(message)
            
            # 序列化
            data = message.SerializeToString()
            
            # 压缩
            if compress:
                data = self._compress_data(data)
                self.stats["compression_saves_bytes"] += len(message.SerializeToString()) - len(data)
            
            # 内容寻址
            if self.enable_content_addressing:
                cid = self.content_addressing.compute_cid(data)
                # 这里可以存储CID映射关系
                logger.debug("序列化内容CID", cid=str(cid)[:16], size=len(data))
            
            # 更新统计
            self.stats["serializations"] += 1
            serialization_time = (time.time() - start_time) * 1000
            self.stats["average_serialization_time_ms"] = (
                self.stats["average_serialization_time_ms"] * (self.stats["serializations"] - 1) + serialization_time
            ) / self.stats["serializations"]
            
            logger.debug("Protobuf序列化完成", 
                        message_type=type(message).__name__,
                        size_bytes=len(data),
                        compressed=compress,
                        time_ms=round(serialization_time, 2))
            
            return data
            
        except Exception as e:
            logger.error("Protobuf序列化失败", 
                        message_type=type(message).__name__,
                        error=str(e))
            raise
    
    def deserialize(self, data: bytes, message_class: Type[ProtoMessage], decompress: bool = None) -> ProtoMessage:
        """反序列化Protobuf消息"""
        start_time = time.time()
        
        if decompress is None:
            decompress = self.enable_compression
        
        try:
            # 解压缩
            if decompress:
                data = self._decompress_data(data)
            
            # 反序列化
            message = message_class()
            message.ParseFromString(data)
            
            # 验证消息
            if self.enable_validation:
                self._validate_message(message)
            
            # 更新统计
            self.stats["deserializations"] += 1
            deserialization_time = (time.time() - start_time) * 1000
            self.stats["average_deserialization_time_ms"] = (
                self.stats["average_deserialization_time_ms"] * (self.stats["deserializations"] - 1) + deserialization_time
            ) / self.stats["deserializations"]
            
            logger.debug("Protobuf反序列化完成",
                        message_type=message_class.__name__,
                        size_bytes=len(data),
                        decompressed=decompress,
                        time_ms=round(deserialization_time, 2))
            
            return message
            
        except Exception as e:
            logger.error("Protobuf反序列化失败",
                        message_type=message_class.__name__,
                        data_size=len(data),
                        error=str(e))
            raise
    
    def serialize_to_json(self, message: Message) -> str:
        """序列化为JSON格式（用于调试）"""
        try:
            return MessageToJson(message, preserving_proto_field_name=True, indent=2)
        except Exception as e:
            logger.error("JSON序列化失败", error=str(e))
            raise
    
    def deserialize_from_json(self, json_str: str, message_class: Type[ProtoMessage]) -> ProtoMessage:
        """从JSON格式反序列化"""
        try:
            message = message_class()
            return Parse(json_str, message)
        except Exception as e:
            logger.error("JSON反序列化失败", error=str(e))
            raise
    
    def _compress_data(self, data: bytes) -> bytes:
        """压缩数据"""
        if self.compression_algorithm == "zstd":
            try:
                import zstandard as zstd
                compressor = zstd.ZstdCompressor(level=3)
                return compressor.compress(data)
            except ImportError:
                logger.warning("zstd未安装，回退到gzip压缩")
                self.compression_algorithm = "gzip"
        
        if self.compression_algorithm == "gzip":
            return gzip.compress(data)
        elif self.compression_algorithm == "zlib":
            return zlib.compress(data)
        else:
            return data
    
    def _decompress_data(self, data: bytes) -> bytes:
        """解压缩数据"""
        if self.compression_algorithm == "zstd":
            try:
                import zstandard as zstd
                decompressor = zstd.ZstdDecompressor()
                return decompressor.decompress(data)
            except ImportError:
                self.compression_algorithm = "gzip"
        
        if self.compression_algorithm == "gzip":
            return gzip.decompress(data)
        elif self.compression_algorithm == "zlib":
            return zlib.decompress(data)
        else:
            return data
    
    def _validate_message(self, message: Message):
        """验证Protobuf消息"""
        try:
            # 检查必填字段
            if not message.IsInitialized():
                raise ValueError("消息包含未初始化的必填字段")
            
            # 这里可以添加更多自定义验证逻辑
            
        except Exception as e:
            self.stats["validation_errors"] += 1
            raise
    
    def get_stats(self) -> Dict[str, Any]:
        """获取性能统计"""
        compression_ratio = 1.0
        if self.stats["serializations"] > 0:
            original_size = self.stats["serializations"] * 100  # 估算
            compressed_size = original_size - self.stats["compression_saves_bytes"]
            compression_ratio = compressed_size / original_size if original_size > 0 else 1.0
        
        return {
            **self.stats,
            "compression_ratio": compression_ratio,
            "content_addressing_enabled": self.enable_content_addressing,
            "validation_enabled": self.enable_validation,
            "compression_algorithm": self.compression_algorithm,
        }


class TranslationProtobufConverter:
    """翻译数据与Protobuf消息的转换器"""
    
    def __init__(self, serializer: ProtobufSerializer):
        self.serializer = serializer
        
    def translation_entry_to_proto(self, entry: Dict[str, Any]) -> pb.TranslationEntry:
        """将翻译条目转换为Protobuf消息"""
        proto_entry = pb.TranslationEntry()
        
        # 基本字段
        proto_entry.uid = entry.get("uid", "")
        proto_entry.key = entry.get("key", "")
        proto_entry.locale = entry.get("locale", "")
        proto_entry.src_text = entry.get("src_text", "")
        proto_entry.dst_text = entry.get("dst_text", "")
        proto_entry.status = entry.get("status", "")
        
        # 时间戳
        if "created_at" in entry:
            proto_entry.created_at = self._parse_timestamp(entry["created_at"])
        if "updated_at" in entry:
            proto_entry.updated_at = self._parse_timestamp(entry["updated_at"])
        
        # 关联信息
        proto_entry.language_file_uid = entry.get("language_file_uid", "")
        proto_entry.pack_uid = entry.get("pack_uid", "")
        
        # 元数据
        if "metadata" in entry and entry["metadata"]:
            for key, value in entry["metadata"].items():
                proto_entry.metadata[key] = str(value)
        
        # 可选字段
        if "notes" in entry:
            proto_entry.notes = entry["notes"]
        if "translator" in entry:
            proto_entry.translator = entry["translator"]
        if "version" in entry:
            proto_entry.version = int(entry["version"])
        
        return proto_entry
    
    def proto_to_translation_entry(self, proto_entry: pb.TranslationEntry) -> Dict[str, Any]:
        """将Protobuf消息转换为翻译条目字典"""
        entry = {
            "uid": proto_entry.uid,
            "key": proto_entry.key,
            "locale": proto_entry.locale,
            "src_text": proto_entry.src_text,
            "dst_text": proto_entry.dst_text,
            "status": proto_entry.status,
            "created_at": self._timestamp_to_string(proto_entry.created_at),
            "updated_at": self._timestamp_to_string(proto_entry.updated_at),
            "language_file_uid": proto_entry.language_file_uid,
            "pack_uid": proto_entry.pack_uid,
        }
        
        # 元数据
        if proto_entry.metadata:
            entry["metadata"] = dict(proto_entry.metadata)
        
        # 可选字段
        if proto_entry.HasField("notes"):
            entry["notes"] = proto_entry.notes
        if proto_entry.HasField("translator"):
            entry["translator"] = proto_entry.translator
        if proto_entry.HasField("version"):
            entry["version"] = proto_entry.version
        
        return entry
    
    def translation_batch_to_proto(self, entries: List[Dict[str, Any]], batch_info: Dict[str, Any] = None) -> pb.TranslationBatch:
        """将翻译条目列表转换为批次Protobuf消息"""
        batch = pb.TranslationBatch()
        
        # 转换条目
        for entry in entries:
            proto_entry = self.translation_entry_to_proto(entry)
            batch.entries.append(proto_entry)
        
        # 批次信息
        if batch_info:
            batch.batch_id = batch_info.get("batch_id", "")
            batch.timestamp = self._parse_timestamp(batch_info.get("timestamp", time.time()))
            batch.source = batch_info.get("source", "")
            batch.total_entries = len(entries)
            
            # 批次元数据
            if "metadata" in batch_info:
                for key, value in batch_info["metadata"].items():
                    batch.metadata[key] = str(value)
        else:
            batch.batch_id = f"batch_{int(time.time())}"
            batch.timestamp = int(time.time())
            batch.total_entries = len(entries)
        
        return batch
    
    def create_sync_request(
        self, 
        session_id: str, 
        client_id: str, 
        locale: str,
        pack_uids: List[str] = None,
        since_timestamp: int = None,
        compression: str = "zstd"
    ) -> pb.SyncRequest:
        """创建同步请求"""
        request = pb.SyncRequest()
        
        request.session_id = session_id
        request.client_id = client_id
        request.locale = locale
        request.compression = compression
        
        if pack_uids:
            request.pack_uids.extend(pack_uids)
        
        if since_timestamp:
            request.since_timestamp = since_timestamp
        
        # 这里可以添加Bloom过滤器生成逻辑
        
        return request
    
    def create_sync_response(
        self,
        session_id: str,
        status: pb.SyncStatus,
        added_entries: List[Dict[str, Any]] = None,
        updated_entries: List[Dict[str, Any]] = None,
        deleted_uids: List[str] = None
    ) -> pb.SyncResponse:
        """创建同步响应"""
        response = pb.SyncResponse()
        
        response.session_id = session_id
        response.status = status
        response.server_timestamp = int(time.time())
        
        # 添加条目
        if added_entries:
            for entry in added_entries:
                proto_entry = self.translation_entry_to_proto(entry)
                response.added_entries.append(proto_entry)
        
        # 更新条目
        if updated_entries:
            for entry in updated_entries:
                proto_entry = self.translation_entry_to_proto(entry)
                response.updated_entries.append(proto_entry)
        
        # 删除的UID
        if deleted_uids:
            response.deleted_entry_uids.extend(deleted_uids)
        
        # 统计总变更数
        response.total_changes = len(added_entries or []) + len(updated_entries or []) + len(deleted_uids or [])
        
        return response
    
    def _parse_timestamp(self, timestamp: Union[str, int, float]) -> int:
        """解析时间戳"""
        if isinstance(timestamp, str):
            try:
                # 尝试ISO格式
                dt = datetime.fromisoformat(timestamp.replace('Z', '+00:00'))
                return int(dt.timestamp())
            except:
                # 回退到字符串格式的Unix时间戳
                return int(float(timestamp))
        elif isinstance(timestamp, (int, float)):
            return int(timestamp)
        else:
            return int(time.time())
    
    def _timestamp_to_string(self, timestamp: int) -> str:
        """时间戳转换为字符串"""
        if timestamp > 0:
            return datetime.fromtimestamp(timestamp).isoformat()
        return ""


class ProtobufBatchProcessor:
    """Protobuf批处理器"""
    
    def __init__(
        self,
        serializer: ProtobufSerializer,
        converter: TranslationProtobufConverter,
        batch_size: int = 1000,
        max_batch_size_bytes: int = 1024 * 1024  # 1MB
    ):
        self.serializer = serializer
        self.converter = converter
        self.batch_size = batch_size
        self.max_batch_size_bytes = max_batch_size_bytes
        
        logger.info("Protobuf批处理器初始化",
                   batch_size=batch_size,
                   max_batch_size_mb=max_batch_size_bytes / 1024 / 1024)
    
    def process_translation_entries_batch(
        self,
        entries: List[Dict[str, Any]],
        batch_info: Dict[str, Any] = None
    ) -> List[bytes]:
        """批处理翻译条目"""
        batches = []
        current_batch = []
        current_size = 0
        
        for entry in entries:
            # 估算条目大小（粗略估算）
            entry_size = len(str(entry).encode('utf-8'))
            
            # 检查是否需要开始新批次
            if (len(current_batch) >= self.batch_size or 
                current_size + entry_size > self.max_batch_size_bytes):
                
                if current_batch:
                    # 处理当前批次
                    batch_proto = self.converter.translation_batch_to_proto(current_batch, batch_info)
                    batch_bytes = self.serializer.serialize(batch_proto)
                    batches.append(batch_bytes)
                    
                    # 重置
                    current_batch = []
                    current_size = 0
            
            current_batch.append(entry)
            current_size += entry_size
        
        # 处理最后一个批次
        if current_batch:
            batch_proto = self.converter.translation_batch_to_proto(current_batch, batch_info)
            batch_bytes = self.serializer.serialize(batch_proto)
            batches.append(batch_bytes)
        
        logger.info("批处理完成",
                   total_entries=len(entries),
                   batch_count=len(batches),
                   avg_batch_size=len(entries) // max(len(batches), 1))
        
        return batches
    
    def merge_batches(self, batch_bytes_list: List[bytes]) -> pb.TranslationBatch:
        """合并多个批次"""
        merged_batch = pb.TranslationBatch()
        merged_batch.batch_id = f"merged_{int(time.time())}"
        merged_batch.timestamp = int(time.time())
        
        total_entries = 0
        
        for batch_bytes in batch_bytes_list:
            batch = self.serializer.deserialize(batch_bytes, pb.TranslationBatch)
            merged_batch.entries.extend(batch.entries)
            total_entries += len(batch.entries)
        
        merged_batch.total_entries = total_entries
        
        logger.info("批次合并完成",
                   source_batches=len(batch_bytes_list),
                   total_entries=total_entries)
        
        return merged_batch


# ==================== 全局服务实例 ====================

_global_protobuf_service: Optional[ProtobufSerializer] = None
_global_converter: Optional[TranslationProtobufConverter] = None
_global_batch_processor: Optional[ProtobufBatchProcessor] = None


def get_protobuf_service() -> ProtobufSerializer:
    """获取全局Protobuf序列化器"""
    global _global_protobuf_service
    if _global_protobuf_service is None:
        _global_protobuf_service = ProtobufSerializer()
    return _global_protobuf_service


def get_protobuf_converter() -> TranslationProtobufConverter:
    """获取全局Protobuf转换器"""
    global _global_converter
    if _global_converter is None:
        _global_converter = TranslationProtobufConverter(get_protobuf_service())
    return _global_converter


def get_batch_processor() -> ProtobufBatchProcessor:
    """获取全局批处理器"""
    global _global_batch_processor
    if _global_batch_processor is None:
        _global_batch_processor = ProtobufBatchProcessor(
            get_protobuf_service(),
            get_protobuf_converter()
        )
    return _global_batch_processor


def initialize_protobuf_service(
    enable_compression: bool = True,
    compression_algorithm: str = "zstd",
    enable_content_addressing: bool = True,
    batch_size: int = 1000
):
    """初始化全局Protobuf服务"""
    global _global_protobuf_service, _global_converter, _global_batch_processor
    
    _global_protobuf_service = ProtobufSerializer(
        enable_compression=enable_compression,
        compression_algorithm=compression_algorithm,
        enable_content_addressing=enable_content_addressing
    )
    
    _global_converter = TranslationProtobufConverter(_global_protobuf_service)
    _global_batch_processor = ProtobufBatchProcessor(
        _global_protobuf_service,
        _global_converter,
        batch_size=batch_size
    )