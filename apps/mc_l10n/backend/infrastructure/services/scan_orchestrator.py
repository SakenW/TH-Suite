"""
扫描编排器 (ScanOrchestrator)
协调快照→差异→任务派发流程，管理扫描会话生命周期
实现1-2秒首屏响应的核心逻辑
"""

import json
import sqlite3
import structlog
import uuid
import asyncio
from pathlib import Path
from typing import Optional, Dict, List, Any, Tuple
from datetime import datetime
from enum import Enum

from .snapshot_builder import SnapshotBuilder
from .diff_engine import DiffEngine

logger = structlog.get_logger(__name__)


class ScanPriority(Enum):
    """扫描任务优先级"""
    VISIBLE = 100    # 可见优先 - 用户当前查看的内容
    DELTA = 70       # Δ变更 - 增量扫描中检测到的变化文件
    RAS = 50         # RAS补完 - Recent Active Set 中的活跃文件
    NON_RAS = 20     # 非RAS补完 - 其他文件的补完扫描


class ScanStage(Enum):
    """扫描阶段"""
    INITIALIZING = "initializing"    # 初始化
    SNAPSHOT = "snapshot"            # 快照构建
    DIFF = "diff"                   # 差异计算
    DISPATCH = "dispatch"           # 任务派发
    PROCESSING = "processing"       # 处理中
    COMPLETED = "completed"         # 已完成
    FAILED = "failed"              # 失败
    CANCELLED = "cancelled"         # 已取消


class ScanSession:
    """扫描会话"""
    
    def __init__(self, session_id: str, root_path: str, 
                 pack_uid: Optional[str] = None,
                 pack_version_uid: Optional[str] = None,
                 resume_from: Optional[str] = None,
                 incremental: bool = False):
        self.session_id = session_id
        self.root_path = root_path
        self.pack_uid = pack_uid
        self.pack_version_uid = pack_version_uid
        self.resume_from = resume_from
        self.incremental = incremental
        
        # 状态信息
        self.stage = ScanStage.INITIALIZING
        self.current_snapshot_id: Optional[str] = None
        self.base_snapshot_id: Optional[str] = None
        self.delta_id: Optional[str] = None
        self.progress = 0.0
        self.error_message: Optional[str] = None
        
        # 统计信息
        self.total_files = 0
        self.processed_files = 0
        self.created_at = datetime.now().isoformat()
        self.started_at = self.created_at  # 添加started_at属性
        self.updated_at = self.created_at
        
        # 任务分发统计
        self.tasks_created = {
            'scan_enum': 0,
            'scan_meta': 0, 
            'scan_lang': 0,
            'scan_verify': 0
        }
        
        # 元数据存储
        self.metadata: Dict[str, Any] = {}
    
    def update_progress(self, processed: int, total: int, stage: ScanStage):
        """更新进度"""
        self.processed_files = processed
        self.total_files = total
        self.progress = processed / total if total > 0 else 0.0
        self.stage = stage
        self.updated_at = datetime.now().isoformat()
    
    def to_dict(self) -> Dict[str, Any]:
        """序列化为字典"""
        return {
            'session_id': self.session_id,
            'root_path': self.root_path,
            'pack_uid': self.pack_uid,
            'pack_version_uid': self.pack_version_uid,
            'incremental': self.incremental,
            'stage': self.stage.value,
            'current_snapshot_id': self.current_snapshot_id,
            'base_snapshot_id': self.base_snapshot_id,
            'delta_id': self.delta_id,
            'progress': self.progress,
            'error_message': self.error_message,
            'total_files': self.total_files,
            'processed_files': self.processed_files,
            'tasks_created': self.tasks_created,
            'metadata': self.metadata,
            'created_at': self.created_at,
            'updated_at': self.updated_at
        }


class ScanOrchestrator:
    """扫描编排器"""
    
    def __init__(self, db_path: str):
        self.db_path = Path(db_path)
        self.snapshot_builder = SnapshotBuilder(db_path)
        self.diff_engine = DiffEngine(db_path)
        self.active_sessions: Dict[str, ScanSession] = {}
        
        # 配置参数
        self.max_concurrent_sessions = 3
        self.visible_priority_limit = 10  # 可见优先任务数量限制
        self.batch_size = 50  # 批量处理大小
    
    async def start_scan(self, root_path: str, 
                        pack_uid: Optional[str] = None,
                        pack_version_uid: Optional[str] = None,
                        resume_session_id: Optional[str] = None) -> str:
        """启动异步扫描，立即返回session_id"""
        
        # 检查并发限制
        if len(self.active_sessions) >= self.max_concurrent_sessions:
            raise ValueError(f"达到最大并发扫描限制: {self.max_concurrent_sessions}")
        
        # 创建或恢复会话
        if resume_session_id and resume_session_id in self.active_sessions:
            session = self.active_sessions[resume_session_id]
            logger.info(f"🔄 恢复扫描会话", session_id=resume_session_id)
        else:
            session_id = resume_session_id or f"scan_{uuid.uuid4().hex[:16]}"
            session = ScanSession(
                session_id=session_id,
                root_path=root_path,
                pack_uid=pack_uid,
                pack_version_uid=pack_version_uid,
                resume_from=resume_session_id
            )
            self.active_sessions[session_id] = session
            logger.info(f"🚀 启动新扫描会话", session_id=session_id, root_path=root_path)
        
        # 保存会话到数据库
        self._save_session(session)
        
        # 异步执行扫描流程
        asyncio.create_task(self._execute_scan_workflow(session))
        
        return session.session_id
    
    async def _execute_scan_workflow(self, session: ScanSession):
        """执行扫描工作流程"""
        try:
            logger.info(f"📋 开始执行扫描工作流程", session_id=session.session_id)
            
            # 阶段1: 构建快照（≤2秒）
            await self._stage_build_snapshot(session)
            
            # 阶段2: 计算差异（如果有基准快照）
            if session.base_snapshot_id:
                await self._stage_calculate_diff(session)
            
            # 阶段3: 派发任务
            await self._stage_dispatch_tasks(session)
            
            # 阶段4: 标记为处理中
            session.stage = ScanStage.PROCESSING
            self._save_session(session)
            
            logger.info(f"✅ 扫描工作流程执行完成", session_id=session.session_id)
            
        except Exception as e:
            logger.error(f"❌ 扫描工作流程失败", session_id=session.session_id, error=str(e))
            session.stage = ScanStage.FAILED
            session.error_message = str(e)
            self._save_session(session)
    
    async def _stage_build_snapshot(self, session: ScanSession):
        """阶段1: 构建快照"""
        session.stage = ScanStage.SNAPSHOT
        self._save_session(session)
        
        logger.info(f"📸 开始构建快照", session_id=session.session_id)
        
        # 查找最近的快照作为基准
        base_snapshot_id = self._find_latest_snapshot(session.root_path)
        session.base_snapshot_id = base_snapshot_id
        
        # 构建当前快照
        snapshot_id, file_count = self.snapshot_builder.build_snapshot(
            root_path=session.root_path,
            session_id=session.session_id,
            pack_uid=session.pack_uid,
            pack_version_uid=session.pack_version_uid,
            resume_snapshot_id=session.current_snapshot_id
        )
        
        session.current_snapshot_id = snapshot_id
        session.total_files = file_count
        session.update_progress(file_count, file_count, ScanStage.SNAPSHOT)
        self._save_session(session)
        
        logger.info(f"✅ 快照构建完成", session_id=session.session_id, 
                   snapshot_id=snapshot_id, file_count=file_count)
    
    async def _stage_calculate_diff(self, session: ScanSession):
        """阶段2: 计算差异"""
        if not session.base_snapshot_id or not session.current_snapshot_id:
            logger.info(f"⏭️ 跳过差异计算阶段", session_id=session.session_id, 
                       reason="缺少基准快照或当前快照")
            return
        
        session.stage = ScanStage.DIFF
        self._save_session(session)
        
        logger.info(f"🔍 开始计算差异", session_id=session.session_id)
        
        try:
            delta_id, changes = self.diff_engine.compare_snapshots(
                current_snapshot_id=session.current_snapshot_id,
                base_snapshot_id=session.base_snapshot_id,
                session_id=session.session_id
            )
        except ValueError as e:
            logger.warning(f"⚠️ 差异计算失败，继续执行", session_id=session.session_id, 
                          error=str(e))
            # 清除无效的基准快照ID，继续执行
            session.base_snapshot_id = None
            return
        
        session.delta_id = delta_id
        self._save_session(session)
        
        # 统计变化
        total_changes = sum(len(change_list) for change_list in changes.values())
        logger.info(f"✅ 差异计算完成", session_id=session.session_id,
                   delta_id=delta_id, total_changes=total_changes)
    
    async def _stage_dispatch_tasks(self, session: ScanSession):
        """阶段3: 派发任务"""
        session.stage = ScanStage.DISPATCH
        self._save_session(session)
        
        logger.info(f"📋 开始派发扫描任务", session_id=session.session_id)
        
        # 获取快照数据
        snapshot_data = self.snapshot_builder.get_snapshot(session.current_snapshot_id)
        if not snapshot_data:
            raise ValueError(f"无法获取快照数据: {session.current_snapshot_id}")
        
        files = snapshot_data['files']
        
        # 如果有差异数据，优先处理变化的文件
        priority_files = set()
        if session.delta_id:
            delta_data = self.diff_engine.get_delta(session.current_snapshot_id)
            if delta_data:
                for change_list in delta_data['changes'].values():
                    for change in change_list:
                        priority_files.add(change.path)
        
        # 1. 创建枚举任务（高优先级，立即展示列表）
        await self._create_enum_tasks(session, files, priority_files)
        
        # 2. 创建元数据解析任务
        await self._create_meta_tasks(session, files, priority_files)
        
        # 3. 创建语言文件处理任务
        await self._create_lang_tasks(session, files, priority_files)
        
        # 4. 创建验证任务
        await self._create_verify_tasks(session)
        
        self._save_session(session)
        
        total_tasks = sum(session.tasks_created.values())
        logger.info(f"✅ 任务派发完成", session_id=session.session_id, 
                   total_tasks=total_tasks, task_breakdown=session.tasks_created)
    
    async def _create_enum_tasks(self, session: ScanSession, files: Dict, priority_files: set):
        """创建枚举任务"""
        # 枚举任务：快速展示文件列表
        task_payload = {
            "session_id": session.session_id,
            "snapshot_id": session.current_snapshot_id,
            "root_path": session.root_path,
            "pack_uid": session.pack_uid,
            "checkpoint": {"stage": "enum", "offset": 0}
        }
        
        # 高优先级任务（变化文件优先）
        priority = ScanPriority.DELTA.value if priority_files else ScanPriority.VISIBLE.value
        
        task_id = self._create_work_task(
            task_type="scan_enum",
            payload=task_payload,
            priority=priority,
            dedupe_key=f"enum_{session.session_id}"
        )
        
        session.tasks_created['scan_enum'] += 1
        logger.info(f"📝 创建枚举任务", session_id=session.session_id, task_id=task_id)
    
    async def _create_meta_tasks(self, session: ScanSession, files: Dict, priority_files: set):
        """创建元数据解析任务"""
        jar_files = [path for path, snapshot in files.items() 
                    if snapshot.is_jar and path.endswith('.jar')]
        
        # 按优先级分批
        priority_jars = [f for f in jar_files if f in priority_files]
        other_jars = [f for f in jar_files if f not in priority_files]
        
        # 高优先级MOD文件
        for jar_file in priority_jars[:self.visible_priority_limit]:
            task_payload = {
                "session_id": session.session_id,
                "snapshot_id": session.current_snapshot_id,
                "file_path": jar_file,
                "file_type": "jar",
                "target_info": ["modid", "version", "loader", "mc_version"],
                "checkpoint": {"stage": "meta", "last_step": "start"}
            }
            
            task_id = self._create_work_task(
                task_type="scan_meta",
                payload=task_payload,
                priority=ScanPriority.DELTA.value,
                dedupe_key=f"meta_{session.session_id}_{jar_file}"
            )
            session.tasks_created['scan_meta'] += 1
        
        # 其他MOD文件（批量处理）
        for i in range(0, len(other_jars), self.batch_size):
            batch = other_jars[i:i+self.batch_size]
            task_payload = {
                "session_id": session.session_id,
                "snapshot_id": session.current_snapshot_id,
                "file_batch": batch,
                "batch_index": i // self.batch_size,
                "checkpoint": {"stage": "meta_batch", "last_step": "start"}
            }
            
            task_id = self._create_work_task(
                task_type="scan_meta",
                payload=task_payload,
                priority=ScanPriority.RAS.value,
                dedupe_key=f"meta_batch_{session.session_id}_{i}"
            )
            session.tasks_created['scan_meta'] += 1
    
    async def _create_lang_tasks(self, session: ScanSession, files: Dict, priority_files: set):
        """创建语言文件处理任务"""
        lang_files = [path for path, snapshot in files.items() 
                     if any(lang_ext in path for lang_ext in ['/lang/', '.json', '.properties'])]
        
        # 按优先级分批
        priority_langs = [f for f in lang_files if f in priority_files]
        other_langs = [f for f in lang_files if f not in priority_files]
        
        # 高优先级语言文件
        for lang_file in priority_langs:
            task_payload = {
                "session_id": session.session_id,
                "snapshot_id": session.current_snapshot_id,
                "root_path": session.root_path,
                "file_path": lang_file,
                "format": self._detect_lang_format(lang_file),
                "encoding": "utf-8",
                "target_languages": ["zh_cn", "en_us"],
                "checkpoint": {"stage": "lang", "last_key": None}
            }
            
            task_id = self._create_work_task(
                task_type="scan_lang",
                payload=task_payload,
                priority=ScanPriority.DELTA.value,
                dedupe_key=f"lang_{session.session_id}_{lang_file}"
            )
            session.tasks_created['scan_lang'] += 1
        
        # 其他语言文件（单独处理每个文件）
        for lang_file in other_langs:
            task_payload = {
                "session_id": session.session_id,
                "snapshot_id": session.current_snapshot_id,
                "root_path": session.root_path,
                "file_path": lang_file,
                "format": self._detect_lang_format(lang_file),
                "encoding": "utf-8",
                "target_languages": ["zh_cn", "en_us"],
                "checkpoint": {"stage": "lang", "last_key": None}
            }
            
            task_id = self._create_work_task(
                task_type="scan_lang",
                payload=task_payload,
                priority=ScanPriority.NON_RAS.value,
                dedupe_key=f"lang_{session.session_id}_{lang_file.replace('/', '_')}"
            )
            session.tasks_created['scan_lang'] += 1
    
    async def _create_verify_tasks(self, session: ScanSession):
        """创建验证任务"""
        task_payload = {
            "session_id": session.session_id,
            "snapshot_id": session.current_snapshot_id,
            "verify_scope": "all",
            "checkpoint": {"stage": "verify", "last_verified": None}
        }
        
        task_id = self._create_work_task(
            task_type="scan_verify",
            payload=task_payload,
            priority=ScanPriority.NON_RAS.value,
            dedupe_key=f"verify_{session.session_id}"
        )
        
        session.tasks_created['scan_verify'] += 1
        logger.info(f"🔍 创建验证任务", session_id=session.session_id, task_id=task_id)
    
    def _create_work_task(self, task_type: str, payload: Dict, 
                         priority: int, dedupe_key: str) -> int:
        """创建工作队列任务"""
        conn = sqlite3.connect(str(self.db_path))
        try:
            cursor = conn.execute("""
                INSERT INTO ops_work_queue (type, payload_json, priority, dedupe_key)
                VALUES (?, ?, ?, ?)
            """, (task_type, json.dumps(payload), priority, dedupe_key))
            
            conn.commit()
            return cursor.lastrowid
            
        finally:
            conn.close()
    
    def _detect_lang_format(self, file_path: str) -> str:
        """检测语言文件格式"""
        if file_path.endswith('.json'):
            return 'json'
        elif file_path.endswith('.properties'):
            return 'properties'
        elif file_path.endswith('.lang'):
            return 'lang'
        else:
            return 'unknown'
    
    def _find_latest_snapshot(self, root_path: str) -> Optional[str]:
        """查找最新的快照作为基准"""
        conn = sqlite3.connect(str(self.db_path))
        try:
            cursor = conn.execute("""
                SELECT snapshot_id FROM cache_scan_snapshots
                WHERE root_path = ?
                ORDER BY created_at DESC
                LIMIT 1
            """, (root_path,))
            
            row = cursor.fetchone()
            return row[0] if row else None
            
        finally:
            conn.close()
    
    def _save_session(self, session: ScanSession):
        """保存会话到数据库"""
        conn = sqlite3.connect(str(self.db_path))
        try:
            # 构建进度和配置JSON
            progress_json = json.dumps({
                "progress": session.progress,
                "processed_files": session.processed_files,
                "total_files": session.total_files,
                "stage": session.stage.value
            }, ensure_ascii=False)
            
            config_json = json.dumps({
                "pack_uid": session.pack_uid,
                "incremental": session.incremental,
                "priority_limit": getattr(session, 'priority_limit', 5),
                "batch_size": getattr(session, 'batch_size', 10)
            }, ensure_ascii=False)
            
            checkpoint_json = json.dumps({
                "tasks_created": session.tasks_created,
                "stage_timestamps": getattr(session, 'stage_timestamps', {}),
                "last_checkpoint": session.updated_at
            }, ensure_ascii=False)
            
            # 映射ScanStage到database state
            state_mapping = {
                ScanStage.INITIALIZING: 'discovering',
                ScanStage.SNAPSHOT: 'analyzing', 
                ScanStage.DIFF: 'analyzing',
                ScanStage.DISPATCH: 'processing',
                ScanStage.PROCESSING: 'processing',
                ScanStage.COMPLETED: 'completed',
                ScanStage.FAILED: 'failed',
                ScanStage.CANCELLED: 'cancelled'
            }
            
            conn.execute("""
                INSERT OR REPLACE INTO cache_scan_sessions
                (session_id, scan_type, root_path, snapshot_id, state,
                 progress_json, stats_json, started_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                session.session_id,
                'incremental' if session.incremental else 'full',
                session.root_path,
                session.current_snapshot_id,
                state_mapping.get(session.stage, 'discovering'),
                progress_json,
                config_json,  # 将config_json作为stats_json存储
                session.created_at
            ))
            
            conn.commit()
            
        finally:
            conn.close()
    
    def get_session(self, session_id: str) -> Optional[ScanSession]:
        """获取扫描会话"""
        if session_id in self.active_sessions:
            return self.active_sessions[session_id]
        
        # 从数据库加载
        conn = sqlite3.connect(str(self.db_path))
        try:
            cursor = conn.execute("""
                SELECT scan_type, root_path, snapshot_id, state, progress_json, 
                       config_json, checkpoint_json, started_at, updated_at
                FROM cache_scan_sessions
                WHERE session_id = ?
            """, (session_id,))
            
            row = cursor.fetchone()
            if not row:
                return None
            
            scan_type, root_path, snapshot_id, state, progress_json, config_json, checkpoint_json, started_at, updated_at = row
            
            # 解析JSON数据
            progress_data = json.loads(progress_json) if progress_json else {}
            config_data = json.loads(config_json) if config_json else {}
            checkpoint_data = json.loads(checkpoint_json) if checkpoint_json else {}
            
            # 创建会话对象
            session = ScanSession(
                session_id=session_id,
                root_path=root_path,
                pack_uid=config_data.get('pack_uid'),
                pack_version_uid=None  # TODO: 从config_data或其他地方获取
            )
            
            # 恢复状态
            # 映射database state到ScanStage
            state_mapping = {
                'discovering': ScanStage.INITIALIZING,
                'analyzing': ScanStage.SNAPSHOT, 
                'extracting': ScanStage.PROCESSING,
                'processing': ScanStage.PROCESSING,
                'finalizing': ScanStage.PROCESSING,
                'completed': ScanStage.COMPLETED,
                'cancelled': ScanStage.CANCELLED,
                'failed': ScanStage.FAILED,
                'interrupted': ScanStage.FAILED
            }
            
            session.stage = state_mapping.get(state, ScanStage.INITIALIZING)
            session.progress = progress_data.get('progress', 0.0)
            session.current_snapshot_id = snapshot_id
            session.base_snapshot_id = None  # TODO: 需要从其他地方获取
            session.delta_id = None  # TODO: 需要从其他地方获取 
            session.error_message = None  # TODO: 从error_info字段获取
            session.total_files = progress_data.get('total_files', 0)
            session.processed_files = progress_data.get('processed_files', 0)
            session.tasks_created = checkpoint_data.get('tasks_created', {})
            session.incremental = (scan_type == 'incremental')
            session.created_at = started_at
            session.updated_at = updated_at
            
            return session
            
        finally:
            conn.close()
    
    async def cancel_scan(self, session_id: str) -> bool:
        """取消扫描"""
        session = self.get_session(session_id)
        if not session:
            return False
        
        session.stage = ScanStage.CANCELLED
        self._save_session(session)
        
        if session_id in self.active_sessions:
            del self.active_sessions[session_id]
        
        logger.info(f"🚫 扫描已取消", session_id=session_id)
        return True
    
    def list_sessions(self, limit: int = 20) -> List[Dict]:
        """列出扫描会话"""
        conn = sqlite3.connect(str(self.db_path))
        conn.row_factory = sqlite3.Row
        
        try:
            cursor = conn.execute("""
                SELECT session_id, stage, progress, created_at, updated_at
                FROM cache_scan_sessions
                ORDER BY created_at DESC
                LIMIT ?
            """, (limit,))
            
            return [dict(row) for row in cursor.fetchall()]
            
        finally:
            conn.close()
    
    # ===== ScanSessionManager期望的方法 =====
    
    async def start_scan_session(self, session_id: str, root_path: str, 
                                scan_type: str = "async_full",
                                incremental: bool = False,
                                metadata: Optional[Dict[str, Any]] = None) -> ScanSession:
        """启动扫描会话 - ScanSessionManager接口"""
        # 创建会话
        session = ScanSession(
            session_id=session_id,
            root_path=root_path,
            incremental=incremental
        )
        
        # 存储元数据
        if metadata:
            session.metadata = metadata
        
        # 保存并注册
        self.active_sessions[session_id] = session
        self._save_session(session)
        
        logger.info("🚀 扫描会话已启动", session_id=session_id, scan_type=scan_type)
        return session
    
    async def process_snapshot_stage(self, session: ScanSession):
        """处理快照阶段 - ScanSessionManager接口"""
        await self._stage_build_snapshot(session)
    
    async def process_diff_stage(self, session: ScanSession):
        """处理差异计算阶段 - ScanSessionManager接口"""
        if session.base_snapshot_id and session.current_snapshot_id:
            await self._stage_calculate_diff(session)
    
    async def dispatch_enum_tasks(self, session: ScanSession):
        """分发枚举任务 - ScanSessionManager接口"""
        snapshot_data = self.snapshot_builder.get_snapshot(session.current_snapshot_id)
        if snapshot_data:
            files = snapshot_data['files']
            await self._create_enum_tasks(session, files, set())
    
    async def dispatch_meta_tasks(self, session: ScanSession):
        """分发元数据任务 - ScanSessionManager接口"""
        snapshot_data = self.snapshot_builder.get_snapshot(session.current_snapshot_id)
        if snapshot_data:
            files = snapshot_data['files']
            await self._create_meta_tasks(session, files, set())
    
    async def dispatch_lang_tasks(self, session: ScanSession, target_languages: List[str]):
        """分发语言任务 - ScanSessionManager接口"""
        snapshot_data = self.snapshot_builder.get_snapshot(session.current_snapshot_id)
        if snapshot_data:
            files = snapshot_data['files']
            await self._create_lang_tasks(session, files, set())
    
    async def complete_scan_session(self, session_id: str):
        """完成扫描会话 - ScanSessionManager接口"""
        session = self.get_session(session_id)
        if session:
            session.stage = ScanStage.COMPLETED
            session.progress = 1.0
            self._save_session(session)
            
            # 从活动会话中移除
            self.active_sessions.pop(session_id, None)
            
            logger.info("🎉 扫描会话已完成", session_id=session_id)
    
    async def fail_scan_session(self, session_id: str, error_message: str):
        """标记扫描会话失败 - ScanSessionManager接口"""
        session = self.get_session(session_id)
        if session:
            session.stage = ScanStage.FAILED
            session.error_message = error_message
            self._save_session(session)
            
            # 从活动会话中移除
            self.active_sessions.pop(session_id, None)
            
            logger.error("❌ 扫描会话失败", session_id=session_id, error=error_message)
    
    async def cancel_scan_session(self, session_id: str):
        """取消扫描会话 - ScanSessionManager接口"""
        await self.cancel_scan(session_id)
    
    async def get_pending_tasks(self, session_id: str) -> List[Dict[str, Any]]:
        """获取待处理任务 - ScanSessionManager接口"""
        conn = sqlite3.connect(str(self.db_path))
        try:
            cursor = conn.execute("""
                SELECT id, type, payload_json, priority, state, created_at
                FROM ops_work_queue
                WHERE JSON_EXTRACT(payload_json, '$.session_id') = ? 
                AND state IN ('pending', 'processing')
                ORDER BY priority DESC, created_at ASC
            """, (session_id,))
            
            tasks = []
            for row in cursor.fetchall():
                task_id, task_type, payload_json, priority, state, created_at = row
                tasks.append({
                    'task_id': task_id,
                    'type': task_type,
                    'payload': json.loads(payload_json) if payload_json else {},
                    'priority': priority,
                    'status': state,
                    'created_at': created_at
                })
            
            return tasks
            
        finally:
            conn.close()
    
    async def get_tasks_stats(self, session_id: str) -> Dict[str, Any]:
        """获取任务统计 - ScanSessionManager接口"""
        conn = sqlite3.connect(str(self.db_path))
        try:
            cursor = conn.execute("""
                SELECT type, state, COUNT(*) as count
                FROM ops_work_queue
                WHERE JSON_EXTRACT(payload_json, '$.session_id') = ?
                GROUP BY type, state
            """, (session_id,))
            
            stats = {}
            for row in cursor.fetchall():
                task_type, state, count = row
                if task_type not in stats:
                    stats[task_type] = {}
                stats[task_type][state] = count
            
            # 计算总计
            total_stats = {'pending': 0, 'processing': 0, 'completed': 0, 'failed': 0}
            for task_type, type_stats in stats.items():
                for status, count in type_stats.items():
                    if status in total_stats:
                        total_stats[status] += count
            
            return {
                'by_type': stats,
                'totals': total_stats
            }
            
        finally:
            conn.close()
    
    async def get_scan_statistics(self, session_id: str) -> Dict[str, Any]:
        """获取扫描统计结果 - ScanSessionManager接口"""
        session = self.get_session(session_id)
        if not session:
            return {}
        
        # 基础统计
        stats = {
            'session_id': session_id,
            'stage': session.stage.value,
            'progress': session.progress,
            'total_files': session.total_files,
            'processed_files': session.processed_files,
            'tasks_created': session.tasks_created,
            'duration': None  # TODO: 计算持续时间
        }
        
        # 任务统计
        task_stats = await self.get_tasks_stats(session_id)
        stats['task_statistics'] = task_stats
        
        return stats
    
    async def submit_task(self, task: Dict[str, Any]):
        """提交任务到工作队列 - ScanSessionManager接口"""
        task_id = self._create_work_task(
            task_type=task['type'],
            payload=json.loads(task['payload_json']),
            priority=task['priority'],
            dedupe_key=f"{task['type']}_{task['session_id']}"
        )
        
        logger.debug("📤 任务已提交", task_id=task_id, task_type=task['type'])
        return task_id
    
    def get_stats(self) -> Dict[str, Any]:
        """获取编排器统计信息 - ScanSessionManager接口"""
        return {
            'active_sessions_count': len(self.active_sessions),
            'active_sessions': list(self.active_sessions.keys()),
            'max_concurrent_sessions': self.max_concurrent_sessions,
            'visible_priority_limit': self.visible_priority_limit,
            'batch_size': self.batch_size
        }