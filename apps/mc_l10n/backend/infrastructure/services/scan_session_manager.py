"""
扫描会话管理器 (ScanSessionManager)
Phase 4: 整合所有组件的统一扫描接口
负责协调ScanOrchestrator、WorkerManager、EventApplier等组件
"""

import asyncio
import structlog
import uuid
from pathlib import Path
from typing import Dict, List, Any, Optional, AsyncGenerator
from datetime import datetime
from enum import Enum

from .scan_orchestrator import ScanOrchestrator, ScanSession, ScanStage
from .worker_manager import WorkerManager, WorkerType
from .event_applier import EventApplier
from .workers.enum_worker import EnumWorker
from .workers.meta_worker import MetaWorker
from .workers.lang_worker import LangWorker
from .workers.verify_worker import VerifyWorker

logger = structlog.get_logger(__name__)


class ScanMode(Enum):
    """扫描模式"""
    FULL = "full"              # 完整扫描
    INCREMENTAL = "incremental" # 增量扫描
    METADATA_ONLY = "metadata_only"  # 仅元数据
    LANGUAGE_ONLY = "language_only"  # 仅语言文件


class ScanSessionManager:
    """扫描会话管理器 - 统一的扫描API接口"""
    
    def __init__(self, db_path: str):
        self.db_path = db_path
        
        # 初始化核心组件
        self.orchestrator = ScanOrchestrator(db_path)
        self.event_applier = EventApplier(db_path)
        self.worker_manager = WorkerManager(db_path, self.event_applier)
        
        # 注册所有Worker
        self._register_workers()
        
        # 会话管理
        self.active_sessions: Dict[str, ScanSession] = {}
        self.is_started = False
        
        logger.info("📋 扫描会话管理器已初始化", db_path=db_path)
    
    def _register_workers(self):
        """注册所有Worker"""
        self.worker_manager.register_worker(EnumWorker(self.db_path))
        self.worker_manager.register_worker(MetaWorker(self.db_path))
        self.worker_manager.register_worker(LangWorker(self.db_path))
        self.worker_manager.register_worker(VerifyWorker(self.db_path))
        
        logger.info("🔧 已注册所有Worker", 
                   workers=[wt.value for wt in self.worker_manager.workers.keys()])
    
    async def start(self):
        """启动会话管理器"""
        if self.is_started:
            return
        
        # 启动核心组件
        self.event_applier.start()  # EventApplier.start不是async的
        await self.worker_manager.start()  # WorkerManager.start是async的
        
        self.is_started = True
        logger.info("🚀 扫描会话管理器已启动")
    
    def stop(self):
        """停止会话管理器"""
        if not self.is_started:
            return
        
        # 停止所有活动会话
        for session_id in list(self.active_sessions.keys()):
            asyncio.create_task(self.cancel_scan(session_id))
        
        # 停止核心组件
        self.worker_manager.stop()
        self.event_applier.stop()
        
        self.is_started = False
        logger.info("🛑 扫描会话管理器已停止")
    
    async def start_scan(self, 
                        root_path: str,
                        mode: ScanMode = ScanMode.FULL,
                        target_languages: Optional[List[str]] = None,
                        incremental: bool = False,
                        **kwargs) -> str:
        """
        启动新的扫描会话
        
        Args:
            root_path: 扫描根目录
            mode: 扫描模式
            target_languages: 目标语言列表
            incremental: 是否增量扫描
            **kwargs: 其他扫描参数
            
        Returns:
            session_id: 会话ID
        """
        if not self.is_started:
            await self.start()
        
        # 生成会话ID
        session_id = f"scan_{uuid.uuid4().hex[:16]}"
        
        # 验证扫描路径
        scan_path = Path(root_path)
        if not scan_path.exists():
            raise ValueError(f"扫描路径不存在: {root_path}")
        
        # 设置目标语言
        if target_languages is None:
            target_languages = ['en_us', 'zh_cn']
        
        logger.info("🎯 启动新扫描会话",
                   session_id=session_id,
                   root_path=root_path,
                   mode=mode.value,
                   incremental=incremental,
                   target_languages=target_languages)
        
        try:
            # 创建扫描会话
            session = await self.orchestrator.start_scan_session(
                session_id=session_id,
                root_path=root_path,
                scan_type="async_full" if mode == ScanMode.FULL else "async_incremental",
                incremental=incremental,
                metadata={
                    'mode': mode.value,
                    'target_languages': target_languages,
                    **kwargs
                }
            )
            
            # 注册活动会话
            self.active_sessions[session_id] = session
            
            # 异步启动扫描流程
            asyncio.create_task(self._execute_scan_workflow(session, mode, target_languages))
            
            logger.info("✅ 扫描会话已启动", session_id=session_id)
            return session_id
            
        except Exception as e:
            logger.error("❌ 启动扫描会话失败", session_id=session_id, error=str(e))
            raise
    
    async def _execute_scan_workflow(self, 
                                   session: ScanSession,
                                   mode: ScanMode,
                                   target_languages: List[str]):
        """执行扫描工作流程"""
        session_id = session.session_id
        
        try:
            logger.info("🔄 开始执行扫描工作流程", session_id=session_id, mode=mode.value)
            
            # Phase 1: 快照阶段 - 使用ScanOrchestrator
            await self.orchestrator.process_snapshot_stage(session)
            
            # Phase 2: 差异检测阶段
            await self.orchestrator.process_diff_stage(session)
            
            # Phase 3: 任务分发阶段 - 根据扫描模式创建不同的任务
            await self._dispatch_tasks_by_mode(session, mode, target_languages)
            
            # Phase 4: 等待所有Worker任务完成
            await self._wait_for_workers_completion(session_id)
            
            # Phase 5: 验证和统计阶段
            if mode in [ScanMode.FULL, ScanMode.INCREMENTAL]:
                await self._dispatch_verify_tasks(session_id)
                await self._wait_for_workers_completion(session_id)
            
            # 完成扫描会话
            await self.orchestrator.complete_scan_session(session_id)
            
            # 从活动会话中移除
            self.active_sessions.pop(session_id, None)
            
            logger.info("🎉 扫描工作流程完成", session_id=session_id)
            
        except Exception as e:
            logger.error("❌ 扫描工作流程失败", session_id=session_id, error=str(e))
            
            # 标记会话失败
            await self.orchestrator.fail_scan_session(session_id, str(e))
            self.active_sessions.pop(session_id, None)
    
    async def _dispatch_tasks_by_mode(self,
                                    session: ScanSession,
                                    mode: ScanMode,
                                    target_languages: List[str]):
        """根据扫描模式分发任务"""
        session_id = session.session_id
        
        # 总是执行ENUM任务（目录枚举）
        await self.orchestrator.dispatch_enum_tasks(session)
        
        if mode == ScanMode.METADATA_ONLY:
            # 仅元数据模式：ENUM + META
            await self.orchestrator.dispatch_meta_tasks(session)
            
        elif mode == ScanMode.LANGUAGE_ONLY:
            # 仅语言文件模式：ENUM + LANG
            await self.orchestrator.dispatch_lang_tasks(session, target_languages)
            
        else:
            # 完整模式或增量模式：ENUM + META + LANG
            await self.orchestrator.dispatch_meta_tasks(session)
            await self.orchestrator.dispatch_lang_tasks(session, target_languages)
        
        logger.info("📤 任务分发完成", session_id=session_id, mode=mode.value)
    
    async def _dispatch_verify_tasks(self, session_id: str):
        """分发验证任务"""
        verify_task = {
            'session_id': session_id,
            'type': WorkerType.VERIFY.value,
            'priority': 20,  # NON_RAS优先级
            'payload_json': f'{{"session_id": "{session_id}", "verification_type": "full", "snapshot_id": "final"}}'
        }
        
        await self.orchestrator.submit_task(verify_task)
        logger.info("🔍 验证任务已分发", session_id=session_id)
    
    async def _wait_for_workers_completion(self, session_id: str, timeout: float = 300.0):
        """等待Worker任务完成"""
        start_time = asyncio.get_event_loop().time()
        
        while True:
            # 检查是否有未完成的任务
            pending_tasks = await self.orchestrator.get_pending_tasks(session_id)
            
            if not pending_tasks:
                break
            
            # 检查超时
            if asyncio.get_event_loop().time() - start_time > timeout:
                logger.warning("⏰ Worker任务等待超时", 
                              session_id=session_id, 
                              pending_tasks=len(pending_tasks))
                break
            
            # 等待一段时间后重新检查
            await asyncio.sleep(1.0)
        
        logger.info("✅ Worker任务完成", session_id=session_id)
    
    async def get_scan_status(self, session_id: str) -> Optional[Dict[str, Any]]:
        """获取扫描状态"""
        session = self.orchestrator.get_session(session_id)  # get_session不是async的
        if not session:
            return None
        
        # 获取任务统计
        tasks_stats = await self.orchestrator.get_tasks_stats(session_id)
        
        # 获取Worker统计
        worker_stats = self.worker_manager.get_stats()
        
        # 获取事件统计
        event_stats = self.event_applier.get_stats()
        
        # 安全地处理stage枚举，确保JSON序列化兼容性
        stage_value = session.stage
        if hasattr(stage_value, 'value'):
            stage_str = stage_value.value
        else:
            stage_str = str(stage_value)
        
        return {
            'session_id': session_id,
            'stage': stage_str,
            'progress': session.progress,
            'started_at': session.started_at,
            'updated_at': session.updated_at,
            'metadata': session.metadata,
            'tasks': tasks_stats,
            'workers': worker_stats,
            'events': event_stats
        }
    
    async def list_active_sessions(self) -> List[Dict[str, Any]]:
        """列出所有活动会话"""
        sessions = []
        for session_id in self.active_sessions.keys():
            status = await self.get_scan_status(session_id)
            if status:
                sessions.append(status)
        return sessions
    
    async def cancel_scan(self, session_id: str) -> bool:
        """取消扫描会话"""
        if session_id not in self.active_sessions:
            return False
        
        try:
            # 取消会话
            await self.orchestrator.cancel_scan_session(session_id)
            
            # 从活动会话中移除
            self.active_sessions.pop(session_id, None)
            
            logger.info("🚫 扫描会话已取消", session_id=session_id)
            return True
            
        except Exception as e:
            logger.error("❌ 取消扫描会话失败", session_id=session_id, error=str(e))
            return False
    
    async def get_scan_results(self, session_id: str) -> Optional[Dict[str, Any]]:
        """获取扫描结果"""
        session = self.orchestrator.get_session(session_id)  # get_session不是async的
        if not session or session.stage != ScanStage.COMPLETED:
            return None
        
        # 获取扫描统计结果
        stats = await self.orchestrator.get_scan_statistics(session_id)
        
        return {
            'session_id': session_id,
            'completed_at': session.updated_at,
            'statistics': stats,
            'metadata': session.metadata
        }
    
    async def stream_scan_progress(self, session_id: str) -> AsyncGenerator[Dict[str, Any], None]:
        """流式获取扫描进度"""
        last_progress = -1
        last_stage = None
        
        while True:
            status = await self.get_scan_status(session_id)
            if not status:
                break
            
            current_progress = status.get('progress', 0)
            current_stage = status.get('stage')
            
            # 只在进度或阶段改变时发送更新
            if current_progress != last_progress or current_stage != last_stage:
                yield {
                    'session_id': session_id,
                    'progress': current_progress,
                    'stage': current_stage,
                    'timestamp': datetime.now().isoformat(),
                    'tasks': status.get('tasks', {}),
                    'workers': status.get('workers', {}),
                    'events': status.get('events', {})
                }
                
                last_progress = current_progress
                last_stage = current_stage
            
            # 如果扫描完成，退出循环
            if current_stage in ['completed', 'failed', 'cancelled']:
                break
            
            await asyncio.sleep(0.5)
    
    def get_manager_stats(self) -> Dict[str, Any]:
        """获取管理器统计信息"""
        return {
            'is_started': self.is_started,
            'active_sessions_count': len(self.active_sessions),
            'active_sessions': list(self.active_sessions.keys()),
            'db_path': self.db_path,
            'orchestrator': self.orchestrator.get_stats(),
            'worker_manager': self.worker_manager.get_stats(),
            'event_applier': self.event_applier.get_stats()
        }