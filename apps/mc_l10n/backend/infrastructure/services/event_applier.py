"""
事件应用器 (EventApplier)
单写入者模式，避免数据库锁争用，批量处理数据库更新
支持事务回滚和WAL模式写入
"""

import json
import sqlite3
import structlog
import time
import uuid
import threading
from pathlib import Path
from typing import Dict, List, Any, Optional, Tuple
from datetime import datetime, timedelta
from enum import Enum
from dataclasses import dataclass
from queue import Queue, Empty
import asyncio

logger = structlog.get_logger(__name__)


class EventType(Enum):
    """事件类型"""
    LIST_UPSERT = "LIST_UPSERT"      # 列表行上屏/更新
    FIELD_PATCH = "FIELD_PATCH"      # 版本/作者/loader/语言数
    LANG_UPSERT = "LANG_UPSERT"      # language_file与entries增量
    COUNT_PATCH = "COUNT_PATCH"      # 计数/统计
    TOMB_STONE = "TOMB_STONE"        # 删除/移动墓碑
    CONFLICT = "CONFLICT"            # 冲突标记
    PROGRESS = "PROGRESS"            # 会话/行内进度
    ERROR = "ERROR"                  # 错误徽章与重试


@dataclass
class ScanEvent:
    """扫描事件"""
    event_id: str
    session_id: str
    event_type: EventType
    entity_ref: str  # 实体引用 (如 mod_uid, file_path等)
    stage: str       # 处理阶段
    artifact_hash: Optional[str]  # 内容哈希，用于幂等
    payload: Dict[str, Any]       # 事件数据
    timestamp: str
    
    def __post_init__(self):
        if not self.event_id:
            self.event_id = f"evt_{uuid.uuid4().hex[:16]}"
        if not self.timestamp:
            self.timestamp = datetime.now().isoformat()
    
    @property
    def idempotent_key(self) -> str:
        """幂等键"""
        parts = [
            self.session_id,
            self.event_type.value,
            self.entity_ref,
            self.stage
        ]
        if self.artifact_hash:
            parts.append(self.artifact_hash)
        return "|".join(parts)
    
    def to_dict(self) -> Dict[str, Any]:
        """序列化为字典"""
        return {
            'event_id': self.event_id,
            'session_id': self.session_id,
            'event_type': self.event_type.value,
            'entity_ref': self.entity_ref,
            'stage': self.stage,
            'artifact_hash': self.artifact_hash,
            'payload': self.payload,
            'timestamp': self.timestamp,
            'idempotent_key': self.idempotent_key
        }


class EventApplier:
    """事件应用器 - 单写入者模式"""
    
    def __init__(self, db_path: str):
        self.db_path = Path(db_path)
        
        # 配置参数
        self.batch_size = 200           # 批处理大小
        self.flush_interval = 0.5       # 刷新间隔（秒）
        self.max_queue_size = 10000     # 最大队列大小
        
        # 内部状态
        self.event_queue = Queue(maxsize=self.max_queue_size)
        self.processed_keys = set()     # 已处理的幂等键
        self.is_running = False
        self.worker_thread: Optional[threading.Thread] = None
        
        # 统计信息
        self.stats = {
            'events_received': 0,
            'events_processed': 0,
            'events_skipped': 0,
            'batches_processed': 0,
            'errors': 0,
            'last_flush': None
        }
        
        # 确保数据库使用WAL模式
        self._ensure_wal_mode()
    
    def _ensure_wal_mode(self):
        """确保数据库使用WAL模式以提高并发性能"""
        try:
            conn = sqlite3.connect(str(self.db_path))
            conn.execute("PRAGMA journal_mode=WAL")
            conn.execute("PRAGMA synchronous=NORMAL")
            conn.execute("PRAGMA cache_size=10000")
            conn.execute("PRAGMA temp_store=memory")
            conn.close()
            logger.info("✅ 数据库WAL模式已启用")
        except Exception as e:
            logger.warning(f"⚠️ 设置WAL模式失败: {e}")
    
    def start(self):
        """启动事件处理器"""
        if self.is_running:
            return
        
        self.is_running = True
        self.worker_thread = threading.Thread(target=self._worker_loop, daemon=True)
        self.worker_thread.start()
        
        logger.info("🚀 EventApplier已启动", 
                   batch_size=self.batch_size, 
                   flush_interval=self.flush_interval)
    
    def stop(self):
        """停止事件处理器"""
        if not self.is_running:
            return
        
        self.is_running = False
        
        # 等待工作线程结束
        if self.worker_thread:
            self.worker_thread.join(timeout=5.0)
        
        # 处理剩余事件
        self._flush_remaining_events()
        
        logger.info("🛑 EventApplier已停止", stats=self.stats)
    
    def submit_event(self, event: ScanEvent) -> bool:
        """提交事件到队列"""
        if not self.is_running:
            logger.warning("⚠️ EventApplier未运行，丢弃事件", event_id=event.event_id)
            return False
        
        # 检查幂等性
        if event.idempotent_key in self.processed_keys:
            self.stats['events_skipped'] += 1
            logger.debug("⏭️ 跳过重复事件", 
                        event_id=event.event_id, 
                        idempotent_key=event.idempotent_key)
            return True
        
        try:
            self.event_queue.put(event, timeout=1.0)
            self.stats['events_received'] += 1
            return True
        except:
            logger.error("❌ 事件队列已满，丢弃事件", event_id=event.event_id)
            return False
    
    def _worker_loop(self):
        """工作线程主循环"""
        logger.info("🔄 EventApplier工作线程已启动")
        
        batch = []
        last_flush = time.time()
        
        while self.is_running:
            try:
                # 尝试获取事件，如果队列为空则等待一段时间
                try:
                    event = self.event_queue.get(timeout=0.1)
                    batch.append(event)
                except Empty:
                    event = None
                
                current_time = time.time()
                should_flush = (
                    len(batch) >= self.batch_size or 
                    (batch and current_time - last_flush >= self.flush_interval)
                )
                
                if should_flush:
                    self._process_batch(batch)
                    batch = []
                    last_flush = current_time
                    
            except Exception as e:
                logger.error(f"❌ 工作线程异常: {e}")
                self.stats['errors'] += 1
                time.sleep(0.1)
        
        # 处理剩余批次
        if batch:
            self._process_batch(batch)
        
        logger.info("🔄 EventApplier工作线程已停止")
    
    def _process_batch(self, batch: List[ScanEvent]):
        """批量处理事件"""
        if not batch:
            return
        
        start_time = time.time()
        
        try:
            conn = sqlite3.connect(str(self.db_path))
            conn.execute("BEGIN TRANSACTION")
            
            # 按事件类型分组处理
            events_by_type = {}
            for event in batch:
                if event.event_type not in events_by_type:
                    events_by_type[event.event_type] = []
                events_by_type[event.event_type].append(event)
            
            # 处理每种类型的事件
            for event_type, events in events_by_type.items():
                if event_type == EventType.LIST_UPSERT:
                    self._handle_list_upsert_batch(conn, events)
                elif event_type == EventType.FIELD_PATCH:
                    self._handle_field_patch_batch(conn, events)
                elif event_type == EventType.LANG_UPSERT:
                    self._handle_lang_upsert_batch(conn, events)
                elif event_type == EventType.COUNT_PATCH:
                    self._handle_count_patch_batch(conn, events)
                elif event_type == EventType.PROGRESS:
                    self._handle_progress_batch(conn, events)
                elif event_type == EventType.TOMB_STONE:
                    self._handle_tombstone_batch(conn, events)
                elif event_type == EventType.ERROR:
                    self._handle_error_batch(conn, events)
                else:
                    logger.warning(f"⚠️ 未知事件类型: {event_type}")
            
            # 记录事件到日志表
            self._log_events_batch(conn, batch)
            
            # 更新幂等键集合
            for event in batch:
                self.processed_keys.add(event.idempotent_key)
            
            conn.commit()
            
            # 更新统计
            self.stats['events_processed'] += len(batch)
            self.stats['batches_processed'] += 1
            self.stats['last_flush'] = datetime.now().isoformat()
            
            duration = time.time() - start_time
            logger.info(f"✅ 批处理完成", 
                       events=len(batch), 
                       duration_ms=int(duration * 1000),
                       events_by_type={k.value: len(v) for k, v in events_by_type.items()})
            
        except Exception as e:
            logger.error(f"❌ 批处理失败: {e}")
            self.stats['errors'] += 1
            try:
                conn.rollback()
            except:
                pass
        finally:
            try:
                conn.close()
            except:
                pass
    
    def _handle_list_upsert_batch(self, conn: sqlite3.Connection, events: List[ScanEvent]):
        """处理列表更新事件批次"""
        for event in events:
            payload = event.payload
            
            # 更新或插入MOD信息到core_mods表
            if 'mod_data' in payload:
                mod_data = payload['mod_data']
                conn.execute("""
                    INSERT OR REPLACE INTO core_mods 
                    (uid, pack_uid, name, loader, mc_version, version_string, file_path, created_at, updated_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    mod_data.get('uid', f"mod_{uuid.uuid4().hex[:16]}"),
                    mod_data.get('pack_uid'),
                    mod_data.get('name', 'Unknown Mod'),
                    mod_data.get('loader', 'unknown'),
                    mod_data.get('mc_version', 'unknown'),
                    mod_data.get('version', 'unknown'),
                    mod_data.get('file_path'),
                    datetime.now().isoformat(),
                    datetime.now().isoformat()
                ))
    
    def _handle_field_patch_batch(self, conn: sqlite3.Connection, events: List[ScanEvent]):
        """处理字段更新事件批次"""
        for event in events:
            payload = event.payload
            entity_ref = event.entity_ref
            
            # 更新MOD字段
            if payload.get('table') == 'core_mods':
                updates = []
                values = []
                
                for field, value in payload.get('fields', {}).items():
                    if field in ['name', 'loader', 'mc_version', 'version_string', 'author']:
                        updates.append(f"{field} = ?")
                        values.append(value)
                
                if updates:
                    updates.append("updated_at = ?")
                    values.append(datetime.now().isoformat())
                    values.append(entity_ref)  # WHERE条件
                    
                    sql = f"UPDATE core_mods SET {', '.join(updates)} WHERE uid = ?"
                    conn.execute(sql, values)
    
    def _handle_lang_upsert_batch(self, conn: sqlite3.Connection, events: List[ScanEvent]):
        """处理语言文件更新事件批次"""
        for event in events:
            payload = event.payload
            
            # 插入或更新语言文件记录
            if 'lang_file' in payload:
                lang_file = payload['lang_file']
                conn.execute("""
                    INSERT OR REPLACE INTO core_language_files
                    (uid, carrier_type, carrier_uid, locale, rel_path, format, size)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                """, (
                    lang_file.get('uid', f"lang_{uuid.uuid4().hex[:16]}"),
                    lang_file.get('carrier_type', 'mod'),
                    lang_file.get('carrier_uid'),
                    lang_file.get('locale', 'en_us'),
                    lang_file.get('rel_path'),
                    lang_file.get('format', 'json'),
                    lang_file.get('size', 0)
                ))
            
            # 批量插入翻译条目
            if 'translation_entries' in payload:
                entries = payload['translation_entries']
                # 获取语言文件UID，用于关联翻译条目
                lang_file_uid = payload.get('lang_file', {}).get('uid')
                if not lang_file_uid and 'lang_file' in payload:
                    lang_file_uid = f"lang_{uuid.uuid4().hex[:16]}"
                
                for entry in entries:
                    conn.execute("""
                        INSERT OR REPLACE INTO core_translation_entries
                        (uid, language_file_uid, key, src_text, dst_text, status)
                        VALUES (?, ?, ?, ?, ?, ?)
                    """, (
                        entry.get('uid', f"entry_{uuid.uuid4().hex[:16]}"),
                        entry.get('lang_file_uid') or lang_file_uid,
                        entry.get('key'),
                        entry.get('src_text', ''),
                        entry.get('dst_text', ''),
                        entry.get('status', 'new')
                    ))
    
    def _handle_count_patch_batch(self, conn: sqlite3.Connection, events: List[ScanEvent]):
        """处理计数更新事件批次"""
        for event in events:
            payload = event.payload
            
            # 更新统计数据到cache_stats表
            if 'stats' in payload:
                stats = payload['stats']
                for stat_key, stat_value in stats.items():
                    conn.execute("""
                        INSERT OR REPLACE INTO cache_stats
                        (stats_type, stats_key, stats_data, valid_until)
                        VALUES (?, ?, ?, ?)
                    """, ("scan_stats", stat_key, json.dumps(stat_value), 
                         (datetime.now() + timedelta(hours=24)).isoformat()))
    
    def _handle_progress_batch(self, conn: sqlite3.Connection, events: List[ScanEvent]):
        """处理进度更新事件批次"""
        for event in events:
            payload = event.payload
            
            # 更新扫描会话进度
            if 'progress' in payload:
                conn.execute("""
                    UPDATE cache_scan_sessions 
                    SET progress = ?, updated_at = ?
                    WHERE session_id = ?
                """, (
                    payload['progress'],
                    datetime.now().isoformat(),
                    event.session_id
                ))
    
    def _handle_tombstone_batch(self, conn: sqlite3.Connection, events: List[ScanEvent]):
        """处理墓碑事件批次"""
        for event in events:
            payload = event.payload
            
            # 墓碑事件主要用于记录和日志，不直接修改核心数据表
            # 这里可以记录到专门的墓碑表或者标记相关记录
            logger.info(f"🪦 墓碑事件", 
                       reason=payload.get('reason', 'unknown'),
                       entity_ref=event.entity_ref,
                       details=payload)
    
    def _handle_error_batch(self, conn: sqlite3.Connection, events: List[ScanEvent]):
        """处理错误事件批次"""
        for event in events:
            payload = event.payload
            
            # 记录错误到工作队列
            if 'error_message' in payload:
                conn.execute("""
                    UPDATE ops_work_queue 
                    SET state = 'err', last_error = ?, attempt = attempt + 1, updated_at = ?
                    WHERE dedupe_key = ?
                """, (
                    payload['error_message'],
                    datetime.now().isoformat(),
                    payload.get('task_dedupe_key')
                ))
    
    def _log_events_batch(self, conn: sqlite3.Connection, events: List[ScanEvent]):
        """批量记录事件到日志表"""
        for event in events:
            conn.execute("""
                INSERT INTO ops_event_log
                (event_id, session_id, event_type, entity_ref, stage, artifact_hash, payload_json, idempotency_key)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                event.event_id,
                event.session_id,
                event.event_type.value,
                event.entity_ref,
                event.stage,
                event.artifact_hash,
                json.dumps(event.payload, ensure_ascii=False),
event.idempotent_key
            ))
    
    def _flush_remaining_events(self):
        """刷新剩余事件"""
        remaining_events = []
        
        try:
            while True:
                event = self.event_queue.get_nowait()
                remaining_events.append(event)
        except Empty:
            pass
        
        if remaining_events:
            self._process_batch(remaining_events)
            logger.info(f"🔄 处理剩余事件: {len(remaining_events)}")
    
    def get_stats(self) -> Dict[str, Any]:
        """获取统计信息"""
        return {
            **self.stats,
            'queue_size': self.event_queue.qsize(),
            'processed_keys_count': len(self.processed_keys),
            'is_running': self.is_running
        }
    
    def clear_processed_keys(self, older_than_hours: int = 24):
        """清理过期的幂等键（防止内存泄漏）"""
        # 简化实现：定期清空所有键
        # 生产环境中应该根据时间戳进行清理
        if len(self.processed_keys) > 100000:  # 超过10万个键时清理
            self.processed_keys.clear()
            logger.info("🧹 清理了过期的幂等键")


# 便捷函数
def create_list_upsert_event(session_id: str, entity_ref: str, mod_data: Dict) -> ScanEvent:
    """创建列表更新事件"""
    return ScanEvent(
        event_id="",
        session_id=session_id,
        event_type=EventType.LIST_UPSERT,
        entity_ref=entity_ref,
        stage="enum",
        artifact_hash=None,
        payload={"mod_data": mod_data},
        timestamp=""
    )


def create_field_patch_event(session_id: str, entity_ref: str, 
                           table: str, fields: Dict) -> ScanEvent:
    """创建字段更新事件"""
    return ScanEvent(
        event_id="",
        session_id=session_id,
        event_type=EventType.FIELD_PATCH,
        entity_ref=entity_ref,
        stage="meta",
        artifact_hash=None,
        payload={"table": table, "fields": fields},
        timestamp=""
    )


def create_lang_upsert_event(session_id: str, entity_ref: str,
                           lang_file: Dict, entries: List[Dict]) -> ScanEvent:
    """创建语言文件更新事件"""
    return ScanEvent(
        event_id="",
        session_id=session_id,
        event_type=EventType.LANG_UPSERT,
        entity_ref=entity_ref,
        stage="lang",
        artifact_hash=None,
        payload={"lang_file": lang_file, "translation_entries": entries},
        timestamp=""
    )


def create_progress_event(session_id: str, progress: float) -> ScanEvent:
    """创建进度更新事件"""
    return ScanEvent(
        event_id="",
        session_id=session_id,
        event_type=EventType.PROGRESS,
        entity_ref=session_id,
        stage="progress",
        artifact_hash=None,
        payload={"progress": progress},
        timestamp=""
    )


def create_tombstone_event(session_id: str, entity_ref: str, tombstone_data: Dict) -> ScanEvent:
    """创建墓碑事件"""
    return ScanEvent(
        event_id="",
        session_id=session_id,
        event_type=EventType.TOMB_STONE,
        entity_ref=entity_ref,
        stage="verify",
        artifact_hash=None,
        payload=tombstone_data,
        timestamp=""
    )


def create_count_patch_event(session_id: str, entity_ref: str, stats_data: Dict) -> ScanEvent:
    """创建统计更新事件"""
    return ScanEvent(
        event_id="",
        session_id=session_id,
        event_type=EventType.COUNT_PATCH,
        entity_ref=entity_ref,
        stage="verify",
        artifact_hash=None,
        payload={"stats": stats_data},
        timestamp=""
    )