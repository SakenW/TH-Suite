"""
同步协议性能监控服务
提供Bloom过滤器效率、压缩比、同步吞吐量等指标监控
"""

import time
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any
from collections import defaultdict, deque
import statistics
import structlog

logger = structlog.get_logger(__name__)


@dataclass
class BloomFilterStats:
    """Bloom过滤器统计"""
    total_handshakes: int = 0
    total_elements_checked: int = 0
    false_positives: int = 0
    true_negatives: int = 0
    false_positive_rate: float = 0.0
    average_filter_size_kb: float = 0.0
    
    def update_false_positive_rate(self):
        """更新假阳性率"""
        total_checks = self.false_positives + self.true_negatives
        if total_checks > 0:
            self.false_positive_rate = self.false_positives / total_checks


@dataclass
class CompressionStats:
    """压缩统计"""
    total_operations: int = 0
    total_input_bytes: int = 0
    total_output_bytes: int = 0
    average_compression_ratio: float = 0.0
    zstd_operations: int = 0
    gzip_operations: int = 0
    compression_time_ms: List[float] = field(default_factory=list)
    
    def update_average_ratio(self):
        """更新平均压缩比"""
        if self.total_input_bytes > 0:
            self.average_compression_ratio = self.total_output_bytes / self.total_input_bytes
    
    def get_average_compression_time(self) -> float:
        """获取平均压缩时间"""
        if not self.compression_time_ms:
            return 0.0
        return statistics.mean(self.compression_time_ms[-100:])  # 最近100次的平均值


@dataclass
class SyncSessionStats:
    """同步会话统计"""
    session_id: str
    client_id: str
    started_at: float
    completed_at: Optional[float] = None
    status: str = "active"
    
    # 数据量统计
    total_chunks: int = 0
    uploaded_chunks: int = 0
    total_bytes: int = 0
    processed_entries: int = 0
    conflicts: int = 0
    
    # 性能指标
    handshake_time_ms: float = 0.0
    upload_time_ms: float = 0.0
    merge_time_ms: float = 0.0
    commit_time_ms: float = 0.0
    
    def get_duration_seconds(self) -> float:
        """获取会话持续时间"""
        end_time = self.completed_at or time.time()
        return end_time - self.started_at
    
    def get_throughput_mbps(self) -> float:
        """获取上传吞吐量（MB/s）"""
        duration = self.get_duration_seconds()
        if duration > 0:
            return (self.total_bytes / 1024 / 1024) / duration
        return 0.0
    
    def get_progress_percent(self) -> float:
        """获取进度百分比"""
        if self.total_chunks > 0:
            return (self.uploaded_chunks / self.total_chunks) * 100
        return 0.0


class SyncMetricsCollector:
    """同步协议性能指标收集器"""
    
    def __init__(self):
        # 基础统计
        self.bloom_stats = BloomFilterStats()
        self.compression_stats = CompressionStats()
        
        # 会话管理
        self.active_sessions: Dict[str, SyncSessionStats] = {}
        self.completed_sessions: deque = deque(maxlen=1000)  # 保留最近1000个完成的会话
        
        # 性能时间序列（最近24小时，每分钟一个点）
        self.throughput_history: deque = deque(maxlen=1440)
        self.compression_ratio_history: deque = deque(maxlen=1440)
        self.bloom_efficiency_history: deque = deque(maxlen=1440)
        
        # 错误统计
        self.error_counts: Dict[str, int] = defaultdict(int)
        
        logger.info("同步协议性能监控初始化完成")
    
    # ==================== Bloom过滤器监控 ====================
    
    def record_bloom_handshake(
        self,
        elements_checked: int,
        filter_size_bytes: int,
        missing_count: int,
        total_count: int
    ):
        """记录Bloom握手性能"""
        self.bloom_stats.total_handshakes += 1
        self.bloom_stats.total_elements_checked += elements_checked
        
        # 更新平均过滤器大小
        current_total = self.bloom_stats.average_filter_size_kb * (self.bloom_stats.total_handshakes - 1)
        self.bloom_stats.average_filter_size_kb = (current_total + filter_size_bytes / 1024) / self.bloom_stats.total_handshakes
        
        # 计算Bloom过滤器效率（理论上所有missing都应该被检测到）
        expected_negatives = total_count - missing_count
        if expected_negatives > 0:
            # 这里简化处理，实际需要更复杂的假阳性检测逻辑
            efficiency = missing_count / total_count if total_count > 0 else 0
            
            # 记录到历史
            self._record_bloom_efficiency(efficiency)
        
        logger.debug("Bloom握手性能记录",
                    elements_checked=elements_checked,
                    filter_size_kb=round(filter_size_bytes / 1024, 2),
                    missing_count=missing_count)
    
    def record_bloom_false_positive(self):
        """记录Bloom过滤器假阳性"""
        self.bloom_stats.false_positives += 1
        self.bloom_stats.update_false_positive_rate()
    
    def record_bloom_true_negative(self):
        """记录Bloom过滤器真阴性"""
        self.bloom_stats.true_negatives += 1
        self.bloom_stats.update_false_positive_rate()
    
    # ==================== 压缩监控 ====================
    
    def record_compression(
        self,
        algorithm: str,
        input_bytes: int,
        output_bytes: int,
        compression_time_ms: float
    ):
        """记录压缩操作性能"""
        stats = self.compression_stats
        
        stats.total_operations += 1
        stats.total_input_bytes += input_bytes
        stats.total_output_bytes += output_bytes
        stats.compression_time_ms.append(compression_time_ms)
        
        if algorithm == "zstd":
            stats.zstd_operations += 1
        elif algorithm == "gzip":
            stats.gzip_operations += 1
        
        stats.update_average_ratio()
        
        # 记录到历史
        compression_ratio = output_bytes / input_bytes if input_bytes > 0 else 1.0
        self._record_compression_ratio(compression_ratio)
        
        logger.debug("压缩性能记录",
                    algorithm=algorithm,
                    input_kb=round(input_bytes / 1024, 2),
                    output_kb=round(output_bytes / 1024, 2),
                    ratio=round(compression_ratio, 3),
                    time_ms=compression_time_ms)
    
    # ==================== 同步会话监控 ====================
    
    def start_sync_session(self, session_id: str, client_id: str) -> SyncSessionStats:
        """开始同步会话监控"""
        session = SyncSessionStats(
            session_id=session_id,
            client_id=client_id,
            started_at=time.time()
        )
        
        self.active_sessions[session_id] = session
        
        logger.info("同步会话开始监控", 
                   session_id=session_id, 
                   client_id=client_id)
        
        return session
    
    def record_handshake_time(self, session_id: str, time_ms: float):
        """记录握手时间"""
        if session_id in self.active_sessions:
            self.active_sessions[session_id].handshake_time_ms = time_ms
    
    def record_chunk_upload(
        self,
        session_id: str,
        chunk_size_bytes: int,
        upload_time_ms: float
    ):
        """记录分片上传"""
        if session_id in self.active_sessions:
            session = self.active_sessions[session_id]
            session.uploaded_chunks += 1
            session.total_bytes += chunk_size_bytes
            session.upload_time_ms += upload_time_ms
    
    def record_merge_operation(self, session_id: str, time_ms: float, conflicts: int):
        """记录合并操作"""
        if session_id in self.active_sessions:
            session = self.active_sessions[session_id]
            session.merge_time_ms += time_ms
            session.conflicts += conflicts
    
    def complete_sync_session(self, session_id: str, status: str = "completed"):
        """完成同步会话"""
        if session_id not in self.active_sessions:
            return
        
        session = self.active_sessions[session_id]
        session.completed_at = time.time()
        session.status = status
        
        # 记录吞吐量
        throughput = session.get_throughput_mbps()
        self._record_throughput(throughput)
        
        # 移动到已完成会话
        self.completed_sessions.append(session)
        del self.active_sessions[session_id]
        
        logger.info("同步会话完成",
                   session_id=session_id,
                   status=status,
                   duration_seconds=round(session.get_duration_seconds(), 2),
                   throughput_mbps=round(throughput, 2),
                   conflicts=session.conflicts)
    
    def record_sync_error(self, error_type: str, session_id: Optional[str] = None):
        """记录同步错误"""
        self.error_counts[error_type] += 1
        
        if session_id and session_id in self.active_sessions:
            self.complete_sync_session(session_id, "failed")
        
        logger.warning("同步错误记录", error_type=error_type, session_id=session_id)
    
    # ==================== 历史数据记录 ====================
    
    def _record_throughput(self, throughput_mbps: float):
        """记录吞吐量历史"""
        self.throughput_history.append({
            "timestamp": time.time(),
            "throughput_mbps": throughput_mbps
        })
    
    def _record_compression_ratio(self, ratio: float):
        """记录压缩比历史"""
        self.compression_ratio_history.append({
            "timestamp": time.time(),
            "compression_ratio": ratio
        })
    
    def _record_bloom_efficiency(self, efficiency: float):
        """记录Bloom过滤器效率历史"""
        self.bloom_efficiency_history.append({
            "timestamp": time.time(),
            "efficiency": efficiency
        })
    
    # ==================== 统计报告 ====================
    
    def get_comprehensive_stats(self) -> Dict[str, Any]:
        """获取综合统计报告"""
        current_time = time.time()
        
        # 活跃会话统计
        active_sessions_stats = []
        for session in self.active_sessions.values():
            active_sessions_stats.append({
                "session_id": session.session_id,
                "client_id": session.client_id,
                "duration_seconds": round(session.get_duration_seconds(), 2),
                "progress_percent": round(session.get_progress_percent(), 1),
                "throughput_mbps": round(session.get_throughput_mbps(), 2),
                "conflicts": session.conflicts,
            })
        
        # 最近完成会话的平均性能
        recent_sessions = list(self.completed_sessions)[-10:]  # 最近10个
        avg_throughput = 0.0
        avg_duration = 0.0
        total_conflicts = 0
        
        if recent_sessions:
            throughputs = [s.get_throughput_mbps() for s in recent_sessions]
            durations = [s.get_duration_seconds() for s in recent_sessions]
            avg_throughput = statistics.mean(throughputs)
            avg_duration = statistics.mean(durations)
            total_conflicts = sum(s.conflicts for s in recent_sessions)
        
        return {
            "bloom_filter": {
                "total_handshakes": self.bloom_stats.total_handshakes,
                "false_positive_rate": round(self.bloom_stats.false_positive_rate, 4),
                "average_filter_size_kb": round(self.bloom_stats.average_filter_size_kb, 2),
                "total_elements_checked": self.bloom_stats.total_elements_checked,
            },
            "compression": {
                "total_operations": self.compression_stats.total_operations,
                "average_compression_ratio": round(self.compression_stats.average_compression_ratio, 3),
                "average_compression_time_ms": round(self.compression_stats.get_average_compression_time(), 2),
                "zstd_operations": self.compression_stats.zstd_operations,
                "gzip_operations": self.compression_stats.gzip_operations,
                "total_input_mb": round(self.compression_stats.total_input_bytes / 1024 / 1024, 2),
                "total_output_mb": round(self.compression_stats.total_output_bytes / 1024 / 1024, 2),
            },
            "sync_sessions": {
                "active_sessions": len(self.active_sessions),
                "completed_sessions": len(self.completed_sessions),
                "average_throughput_mbps": round(avg_throughput, 2),
                "average_duration_seconds": round(avg_duration, 2),
                "total_recent_conflicts": total_conflicts,
                "active_sessions_detail": active_sessions_stats,
            },
            "performance_history": {
                "throughput_samples": len(self.throughput_history),
                "compression_samples": len(self.compression_ratio_history),
                "bloom_samples": len(self.bloom_efficiency_history),
            },
            "errors": dict(self.error_counts),
            "report_time": current_time,
        }
    
    def get_performance_trends(self, hours: int = 1) -> Dict[str, Any]:
        """获取性能趋势（最近N小时）"""
        cutoff_time = time.time() - (hours * 3600)
        
        # 过滤最近的数据
        recent_throughput = [
            item for item in self.throughput_history
            if item["timestamp"] > cutoff_time
        ]
        
        recent_compression = [
            item for item in self.compression_ratio_history
            if item["timestamp"] > cutoff_time
        ]
        
        recent_bloom = [
            item for item in self.bloom_efficiency_history
            if item["timestamp"] > cutoff_time
        ]
        
        # 计算趋势
        throughput_trend = 0.0
        compression_trend = 0.0
        bloom_trend = 0.0
        
        if len(recent_throughput) > 1:
            throughput_values = [item["throughput_mbps"] for item in recent_throughput]
            if len(throughput_values) > 1:
                throughput_trend = throughput_values[-1] - throughput_values[0]
        
        if len(recent_compression) > 1:
            compression_values = [item["compression_ratio"] for item in recent_compression]
            if len(compression_values) > 1:
                compression_trend = compression_values[-1] - compression_values[0]
        
        if len(recent_bloom) > 1:
            bloom_values = [item["efficiency"] for item in recent_bloom]
            if len(bloom_values) > 1:
                bloom_trend = bloom_values[-1] - bloom_values[0]
        
        return {
            "period_hours": hours,
            "throughput": {
                "samples": len(recent_throughput),
                "trend": round(throughput_trend, 3),
                "current": recent_throughput[-1]["throughput_mbps"] if recent_throughput else 0,
                "average": round(statistics.mean([item["throughput_mbps"] for item in recent_throughput]), 2) if recent_throughput else 0,
            },
            "compression": {
                "samples": len(recent_compression),
                "trend": round(compression_trend, 4),
                "current": recent_compression[-1]["compression_ratio"] if recent_compression else 0,
                "average": round(statistics.mean([item["compression_ratio"] for item in recent_compression]), 3) if recent_compression else 0,
            },
            "bloom_efficiency": {
                "samples": len(recent_bloom),
                "trend": round(bloom_trend, 4),
                "current": recent_bloom[-1]["efficiency"] if recent_bloom else 0,
                "average": round(statistics.mean([item["efficiency"] for item in recent_bloom]), 3) if recent_bloom else 0,
            },
        }


# ==================== 全局监控实例 ====================

_global_sync_metrics: Optional[SyncMetricsCollector] = None


def get_sync_metrics() -> SyncMetricsCollector:
    """获取全局同步监控实例"""
    global _global_sync_metrics
    if _global_sync_metrics is None:
        _global_sync_metrics = SyncMetricsCollector()
    return _global_sync_metrics


def reset_sync_metrics():
    """重置同步监控数据"""
    global _global_sync_metrics
    _global_sync_metrics = SyncMetricsCollector()


# ==================== 便捷装饰器 ====================

def monitor_sync_operation(operation_name: str):
    """同步操作监控装饰器"""
    def decorator(func):
        async def wrapper(*args, **kwargs):
            start_time = time.time()
            metrics = get_sync_metrics()
            
            try:
                result = await func(*args, **kwargs)
                
                # 记录成功的操作
                duration_ms = (time.time() - start_time) * 1000
                logger.debug(f"{operation_name}完成", duration_ms=round(duration_ms, 2))
                
                return result
                
            except Exception as e:
                # 记录错误
                metrics.record_sync_error(f"{operation_name}_error")
                logger.error(f"{operation_name}失败", error=str(e))
                raise
        
        return wrapper
    return decorator