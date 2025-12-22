"""
同步协议数据模型
定义Bloom握手、分片传输等相关数据结构
"""

from typing import List, Optional, Dict, Any, Union
from pydantic import BaseModel, Field
from enum import Enum


class SyncProtocolVersion(str, Enum):
    """同步协议版本"""
    V1 = "v1"


class BloomHandshakeRequest(BaseModel):
    """Bloom握手请求"""
    protocol_version: SyncProtocolVersion = Field(default=SyncProtocolVersion.V1, description="协议版本")
    client_id: str = Field(..., description="客户端标识符")
    session_id: str = Field(..., description="会话标识符")
    
    # Bloom过滤器参数
    bloom_bits: int = Field(default=8388608, description="Bloom过滤器位数 (默认1MB)")
    bloom_hashes: int = Field(default=7, description="哈希函数数量")
    
    # 客户端CID集合的Bloom过滤器
    bloom_filter: str = Field(..., description="客户端CID的Bloom过滤器 (Base64编码)")
    
    # 可选：客户端能力声明
    capabilities: Dict[str, Any] = Field(default_factory=dict, description="客户端能力")
    
    # 同步范围限制
    sync_scope: Optional[Dict[str, Any]] = Field(default=None, description="同步范围限制")


class BloomHandshakeResponse(BaseModel):
    """Bloom握手响应"""
    session_id: str = Field(..., description="会话标识符")
    server_protocol_version: SyncProtocolVersion = Field(..., description="服务端协议版本")
    
    # 服务端缺失的CID列表
    missing_cids: List[str] = Field(..., description="服务端缺失的CID列表")
    
    # 服务端状态信息
    server_info: Dict[str, Any] = Field(default_factory=dict, description="服务端信息")
    
    # 传输配置
    chunk_size_bytes: int = Field(default=2097152, description="分片大小 (默认2MB)")
    max_concurrent_chunks: int = Field(default=4, description="最大并发分片数")
    
    # 会话过期时间
    session_expires_at: str = Field(..., description="会话过期时间 (ISO格式)")


class ChunkUploadRequest(BaseModel):
    """分片上传请求"""
    session_id: str = Field(..., description="会话标识符")
    cid: str = Field(..., description="内容标识符 (BLAKE3哈希)")
    
    # 分片信息
    chunk_index: int = Field(..., description="分片索引 (从0开始)")
    total_chunks: int = Field(..., description="总分片数")
    
    # 数据
    data: str = Field(..., description="Entry-Delta数据 (Base64编码)")
    data_size: int = Field(..., description="原始数据大小")
    
    # 校验
    chunk_hash: str = Field(..., description="分片BLAKE3哈希")
    
    # 幂等性
    idempotency_key: Optional[str] = Field(default=None, description="幂等性键")


class ChunkUploadResponse(BaseModel):
    """分片上传响应"""
    session_id: str = Field(..., description="会话标识符")
    cid: str = Field(..., description="内容标识符")
    chunk_index: int = Field(..., description="分片索引")
    
    # 状态
    status: str = Field(..., description="上传状态: received, completed, error")
    
    # 进度信息
    bytes_received: int = Field(..., description="已接收字节数")
    total_bytes: int = Field(..., description="总字节数")
    
    # 下一步动作
    next_chunk_index: Optional[int] = Field(default=None, description="下一个期望的分片索引")


class SyncCommitRequest(BaseModel):
    """同步提交请求"""
    session_id: str = Field(..., description="会话标识符")
    
    # 完成的CID列表
    completed_cids: List[str] = Field(..., description="已完成上传的CID列表")
    
    # 合并选项
    merge_strategy: str = Field(default="3way", description="合并策略: 3way, overwrite, skip")
    
    # 冲突处理选项
    conflict_resolution: str = Field(default="mark_for_review", description="冲突处理: mark_for_review, take_remote, take_local")


class SyncCommitResponse(BaseModel):
    """同步提交响应"""
    session_id: str = Field(..., description="会话标识符")
    
    # 处理结果
    total_entries_processed: int = Field(..., description="处理的条目总数")
    entries_merged: int = Field(..., description="成功合并的条目数")
    entries_conflicts: int = Field(..., description="产生冲突的条目数")
    entries_errors: int = Field(..., description="处理错误的条目数")
    
    # 冲突详情
    conflict_entries: List[Dict[str, Any]] = Field(default_factory=list, description="冲突条目详情")
    
    # 会话完成时间
    completed_at: str = Field(..., description="完成时间 (ISO格式)")


class EntryDelta(BaseModel):
    """Entry-Delta数据结构"""
    # 条目标识
    entry_uid: str = Field(..., description="条目UID")
    uida_keys_b64: str = Field(..., description="UIDA标识符 (Base64)")
    uida_hash: str = Field(..., description="UIDA Hash")
    
    # 变更信息
    operation: str = Field(..., description="操作类型: create, update, delete")
    
    # 内容数据
    key: str = Field(..., description="翻译键")
    src_text: str = Field(..., description="源文本")
    dst_text: str = Field(..., description="目标文本")
    status: str = Field(..., description="状态")
    
    # 元数据
    language_file_uid: str = Field(..., description="语言文件UID")
    updated_at: str = Field(..., description="更新时间")
    
    # 质量标记
    qa_flags: Dict[str, Any] = Field(default_factory=dict, description="QA标记")


class SyncSession(BaseModel):
    """同步会话信息"""
    session_id: str = Field(..., description="会话标识符")
    client_id: str = Field(..., description="客户端标识符")
    
    # 会话状态
    status: str = Field(..., description="会话状态: active, completed, expired, error")
    
    # 时间戳
    created_at: str = Field(..., description="创建时间")
    expires_at: str = Field(..., description="过期时间")
    completed_at: Optional[str] = Field(default=None, description="完成时间")
    
    # 进度信息
    total_cids: int = Field(default=0, description="总CID数量")
    completed_cids: int = Field(default=0, description="已完成CID数量")
    
    # 配置
    chunk_size_bytes: int = Field(..., description="分片大小")
    
    # 元数据
    metadata: Dict[str, Any] = Field(default_factory=dict, description="会话元数据")


class SyncStatistics(BaseModel):
    """同步统计信息"""
    # 会话统计
    active_sessions: int = Field(..., description="活动会话数")
    total_sessions_today: int = Field(..., description="今日总会话数")
    
    # 传输统计
    bytes_transferred_today: int = Field(..., description="今日传输字节数")
    chunks_uploaded_today: int = Field(..., description="今日上传分片数")
    
    # 性能指标
    avg_session_duration_seconds: float = Field(..., description="平均会话时长(秒)")
    avg_chunk_upload_speed_mbps: float = Field(..., description="平均分片上传速度(Mbps)")
    
    # Bloom过滤器统计
    bloom_false_positive_rate: float = Field(..., description="Bloom过滤器假阳性率")
    bloom_efficiency: float = Field(..., description="Bloom过滤器效率")


class SyncCapability(BaseModel):
    """同步能力声明"""
    # 协议支持
    supported_versions: List[SyncProtocolVersion] = Field(..., description="支持的协议版本")
    
    # 传输能力
    max_chunk_size_bytes: int = Field(..., description="最大分片大小")
    max_concurrent_chunks: int = Field(..., description="最大并发分片数")
    
    # 压缩支持
    compression_algorithms: List[str] = Field(default_factory=list, description="支持的压缩算法")
    
    # 数据格式
    supported_formats: List[str] = Field(default=["json", "protobuf"], description="支持的数据格式")
    
    # 其他能力
    supports_resume: bool = Field(default=True, description="是否支持断点续传")
    supports_delta_compression: bool = Field(default=False, description="是否支持增量压缩")