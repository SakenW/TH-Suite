"""
检查点管理器 (CheckpointManager)
实现任务中断后从检查点续扫，支持指数退避重试机制
"""

import json
import sqlite3
import structlog
import time
import uuid
from pathlib import Path
from typing import Dict, List, Any, Optional, Tuple
from datetime import datetime, timedelta
from dataclasses import dataclass
from enum import Enum

logger = structlog.get_logger(__name__)


class CheckpointType(Enum):
    """检查点类型"""
    SNAPSHOT = "snapshot"      # 快照构建检查点
    DIFF = "diff"             # 差异计算检查点
    ENUM = "enum"             # 枚举任务检查点
    META = "meta"             # 元数据解析检查点
    LANG = "lang"             # 语言文件处理检查点
    VERIFY = "verify"         # 验证任务检查点


@dataclass
class Checkpoint:
    """检查点数据"""
    checkpoint_id: str
    session_id: str
    task_type: str
    entity_ref: str           # 实体引用（文件路径、MOD ID等）
    stage: str               # 当前阶段
    artifact_ref: str        # 工件引用（快照ID、文件哈希等）
    artifact_hash: Optional[str]  # 工件哈希
    last_step: str          # 最后完成的步骤
    offset: Optional[int]    # 处理偏移量（如文件索引、行号等）
    context_data: Dict[str, Any]  # 上下文数据
    created_at: str
    updated_at: str
    
    def to_dict(self) -> Dict[str, Any]:
        """序列化为字典"""
        return {
            'checkpoint_id': self.checkpoint_id,
            'session_id': self.session_id,
            'task_type': self.task_type,
            'entity_ref': self.entity_ref,
            'stage': self.stage,
            'artifact_ref': self.artifact_ref,
            'artifact_hash': self.artifact_hash,
            'last_step': self.last_step,
            'offset': self.offset,
            'context_data': self.context_data,
            'created_at': self.created_at,
            'updated_at': self.updated_at
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Checkpoint':
        """从字典反序列化"""
        return cls(
            checkpoint_id=data['checkpoint_id'],
            session_id=data['session_id'],
            task_type=data['task_type'],
            entity_ref=data['entity_ref'],
            stage=data['stage'],
            artifact_ref=data['artifact_ref'],
            artifact_hash=data.get('artifact_hash'),
            last_step=data['last_step'],
            offset=data.get('offset'),
            context_data=data.get('context_data', {}),
            created_at=data['created_at'],
            updated_at=data['updated_at']
        )


class RetryStrategy:
    """重试策略"""
    
    def __init__(self, max_attempts: int = 5, base_delay: float = 1.0, max_delay: float = 300.0):
        self.max_attempts = max_attempts
        self.base_delay = base_delay
        self.max_delay = max_delay
    
    def calculate_delay(self, attempt: int) -> float:
        """计算指数退避延迟"""
        if attempt <= 0:
            return 0.0
        
        # 指数退避：base_delay * (2 ^ (attempt - 1))
        delay = self.base_delay * (2 ** (attempt - 1))
        return min(delay, self.max_delay)
    
    def should_retry(self, attempt: int) -> bool:
        """判断是否应该重试"""
        return attempt < self.max_attempts


class CheckpointManager:
    """检查点管理器"""
    
    def __init__(self, db_path: str):
        self.db_path = Path(db_path)
        self.retry_strategy = RetryStrategy()
        
        # 清理配置
        self.cleanup_interval_hours = 24  # 清理间隔
        self.max_checkpoint_age_days = 7  # 检查点最大保留天数
    
    def save_checkpoint(self, checkpoint: Checkpoint) -> bool:
        """保存检查点"""
        try:
            conn = sqlite3.connect(str(self.db_path))
            
            # 检查点数据序列化
            context_json = json.dumps(checkpoint.context_data, ensure_ascii=False)
            
            conn.execute("""
                INSERT OR REPLACE INTO cache_checkpoint
                (checkpoint_id, session_id, task_type, entity_ref, stage, 
                 artifact_ref, artifact_hash, last_step, offset, context_json, 
                 created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                checkpoint.checkpoint_id,
                checkpoint.session_id,
                checkpoint.task_type,
                checkpoint.entity_ref,
                checkpoint.stage,
                checkpoint.artifact_ref,
                checkpoint.artifact_hash,
                checkpoint.last_step,
                checkpoint.offset,
                context_json,
                checkpoint.created_at,
                checkpoint.updated_at
            ))
            
            conn.commit()
            conn.close()
            
            logger.debug("✅ 检查点已保存", 
                        checkpoint_id=checkpoint.checkpoint_id,
                        task_type=checkpoint.task_type,
                        stage=checkpoint.stage)
            return True
            
        except Exception as e:
            logger.error(f"❌ 保存检查点失败: {e}", 
                        checkpoint_id=checkpoint.checkpoint_id)
            return False
    
    def load_checkpoint(self, session_id: str, task_type: str, 
                       entity_ref: str) -> Optional[Checkpoint]:
        """加载检查点"""
        try:
            conn = sqlite3.connect(str(self.db_path))
            conn.row_factory = sqlite3.Row
            
            cursor = conn.execute("""
                SELECT * FROM cache_checkpoint
                WHERE session_id = ? AND task_type = ? AND entity_ref = ?
                ORDER BY updated_at DESC
                LIMIT 1
            """, (session_id, task_type, entity_ref))
            
            row = cursor.fetchone()
            conn.close()
            
            if not row:
                return None
            
            # 反序列化检查点
            checkpoint_data = dict(row)
            checkpoint_data['context_data'] = json.loads(checkpoint_data['context_json'])
            del checkpoint_data['context_json']
            
            checkpoint = Checkpoint.from_dict(checkpoint_data)
            
            logger.debug("✅ 检查点已加载", 
                        checkpoint_id=checkpoint.checkpoint_id,
                        task_type=checkpoint.task_type)
            return checkpoint
            
        except Exception as e:
            logger.error(f"❌ 加载检查点失败: {e}", 
                        session_id=session_id, task_type=task_type)
            return None
    
    def create_checkpoint(self, session_id: str, task_type: str, entity_ref: str,
                         stage: str, artifact_ref: str, last_step: str,
                         artifact_hash: Optional[str] = None,
                         offset: Optional[int] = None,
                         context_data: Optional[Dict] = None) -> Checkpoint:
        """创建新检查点"""
        
        checkpoint = Checkpoint(
            checkpoint_id=f"cp_{uuid.uuid4().hex[:16]}",
            session_id=session_id,
            task_type=task_type,
            entity_ref=entity_ref,
            stage=stage,
            artifact_ref=artifact_ref,
            artifact_hash=artifact_hash,
            last_step=last_step,
            offset=offset,
            context_data=context_data or {},
            created_at=datetime.now().isoformat(),
            updated_at=datetime.now().isoformat()
        )
        
        return checkpoint
    
    def update_checkpoint(self, checkpoint: Checkpoint, last_step: str,
                         offset: Optional[int] = None,
                         context_updates: Optional[Dict] = None) -> Checkpoint:
        """更新检查点"""
        checkpoint.last_step = last_step
        checkpoint.updated_at = datetime.now().isoformat()
        
        if offset is not None:
            checkpoint.offset = offset
        
        if context_updates:
            checkpoint.context_data.update(context_updates)
        
        return checkpoint
    
    def mark_task_completed(self, session_id: str, task_type: str, entity_ref: str):
        """标记任务完成（删除对应检查点）"""
        try:
            conn = sqlite3.connect(str(self.db_path))
            
            conn.execute("""
                DELETE FROM cache_checkpoint
                WHERE session_id = ? AND task_type = ? AND entity_ref = ?
            """, (session_id, task_type, entity_ref))
            
            conn.commit()
            conn.close()
            
            logger.debug("🎯 任务完成，检查点已删除", 
                        session_id=session_id, task_type=task_type)
            
        except Exception as e:
            logger.error(f"❌ 删除检查点失败: {e}")
    
    def get_session_checkpoints(self, session_id: str) -> List[Checkpoint]:
        """获取会话的所有检查点"""
        try:
            conn = sqlite3.connect(str(self.db_path))
            conn.row_factory = sqlite3.Row
            
            cursor = conn.execute("""
                SELECT * FROM cache_checkpoint
                WHERE session_id = ?
                ORDER BY updated_at DESC
            """, (session_id,))
            
            checkpoints = []
            for row in cursor.fetchall():
                checkpoint_data = dict(row)
                checkpoint_data['context_data'] = json.loads(checkpoint_data['context_json'])
                del checkpoint_data['context_json']
                
                checkpoint = Checkpoint.from_dict(checkpoint_data)
                checkpoints.append(checkpoint)
            
            conn.close()
            return checkpoints
            
        except Exception as e:
            logger.error(f"❌ 获取会话检查点失败: {e}")
            return []
    
    def cleanup_old_checkpoints(self):
        """清理过期检查点"""
        try:
            cutoff_time = (datetime.now() - timedelta(days=self.max_checkpoint_age_days)).isoformat()
            
            conn = sqlite3.connect(str(self.db_path))
            
            cursor = conn.execute("""
                SELECT COUNT(*) FROM cache_checkpoint
                WHERE created_at < ?
            """, (cutoff_time,))
            
            count_to_delete = cursor.fetchone()[0]
            
            if count_to_delete > 0:
                conn.execute("""
                    DELETE FROM cache_checkpoint
                    WHERE created_at < ?
                """, (cutoff_time,))
                
                conn.commit()
                logger.info(f"🧹 清理了 {count_to_delete} 个过期检查点")
            
            conn.close()
            
        except Exception as e:
            logger.error(f"❌ 清理检查点失败: {e}")
    
    def get_retry_info(self, task_id: int) -> Tuple[int, float]:
        """获取任务重试信息"""
        try:
            conn = sqlite3.connect(str(self.db_path))
            conn.row_factory = sqlite3.Row
            
            cursor = conn.execute("""
                SELECT attempt, updated_at FROM ops_work_queue
                WHERE id = ?
            """, (task_id,))
            
            row = cursor.fetchone()
            conn.close()
            
            if not row:
                return 0, 0.0
            
            attempt = row['attempt']
            last_attempt_time = datetime.fromisoformat(row['updated_at'])
            
            # 计算下次重试时间
            delay = self.retry_strategy.calculate_delay(attempt)
            next_retry_time = last_attempt_time + timedelta(seconds=delay)
            time_until_retry = (next_retry_time - datetime.now()).total_seconds()
            
            return attempt, max(0, time_until_retry)
            
        except Exception as e:
            logger.error(f"❌ 获取重试信息失败: {e}")
            return 0, 0.0
    
    def should_retry_task(self, task_id: int) -> bool:
        """判断任务是否应该重试"""
        attempt, time_until_retry = self.get_retry_info(task_id)
        
        # 检查重试次数限制
        if not self.retry_strategy.should_retry(attempt):
            return False
        
        # 检查是否到重试时间
        return time_until_retry <= 0
    
    def increment_task_attempt(self, task_id: int, error_message: str):
        """增加任务重试次数"""
        try:
            conn = sqlite3.connect(str(self.db_path))
            
            conn.execute("""
                UPDATE ops_work_queue 
                SET attempt = attempt + 1, 
                    last_error = ?,
                    state = CASE 
                        WHEN attempt + 1 >= ? THEN 'dead'
                        ELSE 'err'
                    END,
                    updated_at = ?
                WHERE id = ?
            """, (
                error_message,
                self.retry_strategy.max_attempts,
                datetime.now().isoformat(),
                task_id
            ))
            
            conn.commit()
            conn.close()
            
        except Exception as e:
            logger.error(f"❌ 更新任务重试次数失败: {e}")


class IdempotencyManager:
    """幂等性管理器"""
    
    def __init__(self, db_path: str):
        self.db_path = Path(db_path)
        self.cache_size = 50000  # 内存缓存大小
        self.memory_cache = set()
    
    def generate_idempotent_key(self, session_id: str, event_type: str, 
                               entity_ref: str, stage: str, 
                               artifact_hash: Optional[str] = None) -> str:
        """生成幂等键"""
        parts = [session_id, event_type, entity_ref, stage]
        if artifact_hash:
            parts.append(artifact_hash)
        return "|".join(parts)
    
    def is_processed(self, idempotent_key: str) -> bool:
        """检查是否已处理"""
        # 先检查内存缓存
        if idempotent_key in self.memory_cache:
            return True
        
        # 检查数据库
        try:
            conn = sqlite3.connect(str(self.db_path))
            
            cursor = conn.execute("""
                SELECT 1 FROM ops_idempotency
                WHERE idempotent_key = ?
                LIMIT 1
            """, (idempotent_key,))
            
            exists = cursor.fetchone() is not None
            conn.close()
            
            if exists:
                # 添加到内存缓存
                self._add_to_cache(idempotent_key)
            
            return exists
            
        except Exception as e:
            logger.error(f"❌ 检查幂等性失败: {e}")
            return False
    
    def mark_processed(self, idempotent_key: str, event_data: Dict[str, Any]):
        """标记为已处理"""
        try:
            conn = sqlite3.connect(str(self.db_path))
            
            conn.execute("""
                INSERT OR IGNORE INTO ops_idempotency
                (idempotent_key, event_data, created_at)
                VALUES (?, ?, ?)
            """, (
                idempotent_key,
                json.dumps(event_data, ensure_ascii=False),
                datetime.now().isoformat()
            ))
            
            conn.commit()
            conn.close()
            
            # 添加到内存缓存
            self._add_to_cache(idempotent_key)
            
        except Exception as e:
            logger.error(f"❌ 标记幂等性失败: {e}")
    
    def _add_to_cache(self, idempotent_key: str):
        """添加到内存缓存"""
        if len(self.memory_cache) >= self.cache_size:
            # 简单的LRU：清空一半缓存
            self.memory_cache.clear()
        
        self.memory_cache.add(idempotent_key)
    
    def cleanup_old_records(self, days_to_keep: int = 7):
        """清理过期幂等记录"""
        try:
            cutoff_time = (datetime.now() - timedelta(days=days_to_keep)).isoformat()
            
            conn = sqlite3.connect(str(self.db_path))
            
            cursor = conn.execute("""
                SELECT COUNT(*) FROM ops_idempotency
                WHERE created_at < ?
            """, (cutoff_time,))
            
            count_to_delete = cursor.fetchone()[0]
            
            if count_to_delete > 0:
                conn.execute("""
                    DELETE FROM ops_idempotency
                    WHERE created_at < ?
                """, (cutoff_time,))
                
                conn.commit()
                logger.info(f"🧹 清理了 {count_to_delete} 个过期幂等记录")
            
            conn.close()
            
        except Exception as e:
            logger.error(f"❌ 清理幂等记录失败: {e}")


# 便捷函数
def create_enum_checkpoint(session_id: str, root_path: str, 
                          processed_files: int = 0) -> Checkpoint:
    """创建枚举任务检查点"""
    return Checkpoint(
        checkpoint_id=f"cp_{uuid.uuid4().hex[:16]}",
        session_id=session_id,
        task_type="scan_enum",
        entity_ref=root_path,
        stage="enum",
        artifact_ref=root_path,
        artifact_hash=None,
        last_step="file_listing",
        offset=processed_files,
        context_data={"processed_files": processed_files},
        created_at=datetime.now().isoformat(),
        updated_at=datetime.now().isoformat()
    )


def create_meta_checkpoint(session_id: str, jar_file: str, 
                          last_parsed_entry: str = "") -> Checkpoint:
    """创建元数据解析检查点"""
    return Checkpoint(
        checkpoint_id=f"cp_{uuid.uuid4().hex[:16]}",
        session_id=session_id,
        task_type="scan_meta",
        entity_ref=jar_file,
        stage="meta",
        artifact_ref=jar_file,
        artifact_hash=None,
        last_step="manifest_parsing",
        offset=None,
        context_data={"last_parsed_entry": last_parsed_entry},
        created_at=datetime.now().isoformat(),
        updated_at=datetime.now().isoformat()
    )


def create_lang_checkpoint(session_id: str, lang_file: str, 
                          last_key: str = "", processed_keys: int = 0) -> Checkpoint:
    """创建语言文件处理检查点"""
    return Checkpoint(
        checkpoint_id=f"cp_{uuid.uuid4().hex[:16]}",
        session_id=session_id,
        task_type="scan_lang",
        entity_ref=lang_file,
        stage="lang",
        artifact_ref=lang_file,
        artifact_hash=None,
        last_step="key_processing",
        offset=processed_keys,
        context_data={"last_key": last_key, "processed_keys": processed_keys},
        created_at=datetime.now().isoformat(),
        updated_at=datetime.now().isoformat()
    )