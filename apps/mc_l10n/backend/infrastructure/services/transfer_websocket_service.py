"""
文件传输WebSocket服务 - 实时进度推送和状态同步
支持多客户端连接、事件广播、自动重连
"""

import asyncio
import json
import logging
from datetime import datetime
from typing import Dict, List, Set, Optional, Callable, Any
from dataclasses import dataclass, asdict
from enum import Enum
import weakref
import uuid

from fastapi import WebSocket, WebSocketDisconnect
from websockets.exceptions import ConnectionClosed

logger = logging.getLogger(__name__)


class WebSocketEventType(Enum):
    """WebSocket事件类型"""
    # 连接管理
    CONNECTION_ESTABLISHED = "connection_established"
    CONNECTION_CLOSED = "connection_closed"
    SUBSCRIPTION_CONFIRMED = "subscription_confirmed"
    SUBSCRIPTION_CANCELLED = "subscription_cancelled"
    
    # 传输进度事件
    TRANSFER_PROGRESS = "transfer_progress"
    TRANSFER_STATUS_CHANGED = "transfer_status_changed"
    TRANSFER_COMPLETED = "transfer_completed"
    TRANSFER_FAILED = "transfer_failed"
    TRANSFER_CANCELLED = "transfer_cancelled"
    
    # 分块事件
    CHUNK_STARTED = "chunk_started"
    CHUNK_COMPLETED = "chunk_completed"
    CHUNK_FAILED = "chunk_failed"
    CHUNK_RETRIED = "chunk_retried"
    
    # 错误和警告
    ERROR_OCCURRED = "error_occurred"
    WARNING_ISSUED = "warning_issued"
    
    # 系统事件
    HEARTBEAT = "heartbeat"
    SYSTEM_STATUS = "system_status"


@dataclass
class WebSocketEvent:
    """WebSocket事件"""
    event_type: WebSocketEventType
    session_id: Optional[str] = None
    timestamp: str = None
    data: Dict = None
    client_id: Optional[str] = None
    
    def __post_init__(self):
        if self.timestamp is None:
            self.timestamp = datetime.now().isoformat()
        if self.data is None:
            self.data = {}


@dataclass
class ClientConnection:
    """客户端连接信息"""
    client_id: str
    websocket: WebSocket
    connected_at: datetime
    last_heartbeat: datetime
    subscriptions: Set[str]  # 订阅的session_id集合
    metadata: Dict = None
    
    def __post_init__(self):
        if self.metadata is None:
            self.metadata = {}


class TransferWebSocketService:
    """文件传输WebSocket服务"""
    
    def __init__(self):
        # 客户端连接管理
        self.active_connections: Dict[str, ClientConnection] = {}
        self.session_subscribers: Dict[str, Set[str]] = {}  # session_id -> set of client_ids
        
        # 事件队列和处理
        self.event_queue: asyncio.Queue = asyncio.Queue()
        self.event_handlers: Dict[WebSocketEventType, List[Callable]] = {}
        
        # 广播和批处理
        self.pending_broadcasts: Dict[str, List[WebSocketEvent]] = {}
        self.broadcast_interval: float = 0.1  # 100ms批处理间隔
        
        # 监控和统计
        self.connection_stats: Dict = {
            'total_connections': 0,
            'active_connections': 0,
            'total_messages_sent': 0,
            'total_messages_received': 0,
            'total_events_processed': 0
        }
        
        # 后台任务
        self._background_tasks: Set[asyncio.Task] = set()
        
        # 启动后台服务
        self._start_background_services()
        
    async def connect_client(self, websocket: WebSocket, client_metadata: Optional[Dict] = None) -> str:
        """连接新客户端"""
        
        await websocket.accept()
        
        # 生成客户端ID
        client_id = f"client_{uuid.uuid4().hex[:8]}"
        
        # 创建连接对象
        connection = ClientConnection(
            client_id=client_id,
            websocket=websocket,
            connected_at=datetime.now(),
            last_heartbeat=datetime.now(),
            subscriptions=set(),
            metadata=client_metadata or {}
        )
        
        # 注册连接
        self.active_connections[client_id] = connection
        self.connection_stats['total_connections'] += 1
        self.connection_stats['active_connections'] += 1
        
        # 发送连接确认事件
        await self._send_to_client(client_id, WebSocketEvent(
            event_type=WebSocketEventType.CONNECTION_ESTABLISHED,
            client_id=client_id,
            data={
                "client_id": client_id,
                "server_time": datetime.now().isoformat(),
                "supported_events": [e.value for e in WebSocketEventType]
            }
        ))
        
        logger.info(f"客户端连接成功: {client_id}")
        return client_id
        
    async def disconnect_client(self, client_id: str):
        """断开客户端连接"""
        
        connection = self.active_connections.get(client_id)
        if not connection:
            return
            
        # 清理订阅
        for session_id in connection.subscriptions:
            if session_id in self.session_subscribers:
                self.session_subscribers[session_id].discard(client_id)
                if not self.session_subscribers[session_id]:
                    del self.session_subscribers[session_id]
                    
        # 移除连接
        del self.active_connections[client_id]
        self.connection_stats['active_connections'] -= 1
        
        logger.info(f"客户端连接已断开: {client_id}")
        
    async def subscribe_to_session(self, client_id: str, session_id: str):
        """订阅传输会话事件"""
        
        connection = self.active_connections.get(client_id)
        if not connection:
            return False
            
        # 添加订阅
        connection.subscriptions.add(session_id)
        
        if session_id not in self.session_subscribers:
            self.session_subscribers[session_id] = set()
        self.session_subscribers[session_id].add(client_id)
        
        # 发送订阅确认
        await self._send_to_client(client_id, WebSocketEvent(
            event_type=WebSocketEventType.SUBSCRIPTION_CONFIRMED,
            session_id=session_id,
            client_id=client_id,
            data={"session_id": session_id}
        ))
        
        logger.debug(f"客户端订阅会话: {client_id} -> {session_id}")
        return True
        
    async def unsubscribe_from_session(self, client_id: str, session_id: str):
        """取消订阅传输会话事件"""
        
        connection = self.active_connections.get(client_id)
        if not connection:
            return False
            
        # 移除订阅
        connection.subscriptions.discard(session_id)
        
        if session_id in self.session_subscribers:
            self.session_subscribers[session_id].discard(client_id)
            if not self.session_subscribers[session_id]:
                del self.session_subscribers[session_id]
                
        # 发送取消确认
        await self._send_to_client(client_id, WebSocketEvent(
            event_type=WebSocketEventType.SUBSCRIPTION_CANCELLED,
            session_id=session_id,
            client_id=client_id,
            data={"session_id": session_id}
        ))
        
        logger.debug(f"客户端取消订阅: {client_id} -> {session_id}")
        return True
        
    async def broadcast_transfer_progress(self, session_id: str, progress_data: Dict):
        """广播传输进度更新"""
        
        event = WebSocketEvent(
            event_type=WebSocketEventType.TRANSFER_PROGRESS,
            session_id=session_id,
            data=progress_data
        )
        
        await self._broadcast_to_session_subscribers(session_id, event)
        
    async def broadcast_transfer_status_change(self, session_id: str, old_status: str, new_status: str, extra_data: Optional[Dict] = None):
        """广播传输状态变更"""
        
        data = {
            "old_status": old_status,
            "new_status": new_status
        }
        if extra_data:
            data.update(extra_data)
            
        event = WebSocketEvent(
            event_type=WebSocketEventType.TRANSFER_STATUS_CHANGED,
            session_id=session_id,
            data=data
        )
        
        await self._broadcast_to_session_subscribers(session_id, event)
        
    async def broadcast_chunk_event(self, session_id: str, event_type: WebSocketEventType, chunk_index: int, extra_data: Optional[Dict] = None):
        """广播分块事件"""
        
        data = {"chunk_index": chunk_index}
        if extra_data:
            data.update(extra_data)
            
        event = WebSocketEvent(
            event_type=event_type,
            session_id=session_id,
            data=data
        )
        
        await self._broadcast_to_session_subscribers(session_id, event)
        
    async def broadcast_error(self, session_id: str, error_message: str, error_details: Optional[Dict] = None):
        """广播错误事件"""
        
        data = {
            "error_message": error_message,
            "severity": "error"
        }
        if error_details:
            data.update(error_details)
            
        event = WebSocketEvent(
            event_type=WebSocketEventType.ERROR_OCCURRED,
            session_id=session_id,
            data=data
        )
        
        await self._broadcast_to_session_subscribers(session_id, event)
        
    async def handle_client_message(self, client_id: str, message: str):
        """处理客户端消息"""
        
        try:
            data = json.loads(message)
            message_type = data.get("type")
            
            if message_type == "subscribe":
                session_id = data.get("session_id")
                if session_id:
                    await self.subscribe_to_session(client_id, session_id)
                    
            elif message_type == "unsubscribe":
                session_id = data.get("session_id")
                if session_id:
                    await self.unsubscribe_from_session(client_id, session_id)
                    
            elif message_type == "heartbeat":
                await self._handle_heartbeat(client_id)
                
            elif message_type == "get_status":
                session_id = data.get("session_id")
                if session_id:
                    await self._send_session_status(client_id, session_id)
                    
            else:
                logger.warning(f"未知消息类型: {message_type} from {client_id}")
                
            self.connection_stats['total_messages_received'] += 1
            
        except json.JSONDecodeError:
            logger.error(f"客户端消息JSON解析失败: {client_id}")
        except Exception as e:
            logger.error(f"处理客户端消息失败: {client_id}: {e}")
            
    def add_event_handler(self, event_type: WebSocketEventType, handler: Callable):
        """添加事件处理器"""
        
        if event_type not in self.event_handlers:
            self.event_handlers[event_type] = []
        self.event_handlers[event_type].append(handler)
        
    def get_connection_stats(self) -> Dict:
        """获取连接统计信息"""
        
        return {
            **self.connection_stats,
            'current_active_connections': len(self.active_connections),
            'total_subscriptions': sum(len(conn.subscriptions) for conn in self.active_connections.values()),
            'active_session_subscribers': len(self.session_subscribers)
        }
        
    # ============================================================================
    # 私有方法
    # ============================================================================
    
    async def _send_to_client(self, client_id: str, event: WebSocketEvent):
        """发送事件到指定客户端"""
        
        connection = self.active_connections.get(client_id)
        if not connection:
            return False
            
        try:
            message = {
                "event_type": event.event_type.value,
                "session_id": event.session_id,
                "timestamp": event.timestamp,
                "data": event.data,
                "client_id": event.client_id
            }
            
            await connection.websocket.send_text(json.dumps(message))
            self.connection_stats['total_messages_sent'] += 1
            return True
            
        except (WebSocketDisconnect, ConnectionClosed):
            logger.warning(f"客户端连接已断开，移除连接: {client_id}")
            await self.disconnect_client(client_id)
            return False
        except Exception as e:
            logger.error(f"发送消息到客户端失败: {client_id}: {e}")
            return False
            
    async def _broadcast_to_session_subscribers(self, session_id: str, event: WebSocketEvent):
        """广播事件到会话订阅者"""
        
        subscribers = self.session_subscribers.get(session_id, set())
        if not subscribers:
            return
            
        # 批量发送
        send_tasks = [
            self._send_to_client(client_id, event) 
            for client_id in subscribers
        ]
        
        if send_tasks:
            results = await asyncio.gather(*send_tasks, return_exceptions=True)
            success_count = sum(1 for result in results if result is True)
            logger.debug(f"事件广播: {session_id}, 发送给 {success_count}/{len(send_tasks)} 个客户端")
            
    async def _handle_heartbeat(self, client_id: str):
        """处理心跳"""
        
        connection = self.active_connections.get(client_id)
        if connection:
            connection.last_heartbeat = datetime.now()
            
            # 发送心跳响应
            await self._send_to_client(client_id, WebSocketEvent(
                event_type=WebSocketEventType.HEARTBEAT,
                client_id=client_id,
                data={"server_time": datetime.now().isoformat()}
            ))
            
    async def _send_session_status(self, client_id: str, session_id: str):
        """发送会话状态"""
        
        # 这里应该从FileTransferService获取实际状态
        # 简化实现，发送模拟状态
        status_data = {
            "session_id": session_id,
            "status": "active",
            "progress_percentage": 45.5,
            "current_chunk": 123,
            "total_chunks": 256
        }
        
        await self._send_to_client(client_id, WebSocketEvent(
            event_type=WebSocketEventType.SYSTEM_STATUS,
            session_id=session_id,
            client_id=client_id,
            data=status_data
        ))
        
    def _start_background_services(self):
        """启动后台服务"""
        
        # 启动心跳检查任务
        heartbeat_task = asyncio.create_task(self._heartbeat_checker())
        self._background_tasks.add(heartbeat_task)
        heartbeat_task.add_done_callback(self._background_tasks.discard)
        
        # 启动事件处理任务
        event_task = asyncio.create_task(self._event_processor())
        self._background_tasks.add(event_task)
        event_task.add_done_callback(self._background_tasks.discard)
        
        logger.info("WebSocket后台服务已启动")
        
    async def _heartbeat_checker(self):
        """心跳检查器"""
        
        while True:
            try:
                current_time = datetime.now()
                timeout_threshold = current_time.timestamp() - 60  # 60秒超时
                
                disconnected_clients = []
                
                for client_id, connection in self.active_connections.items():
                    if connection.last_heartbeat.timestamp() < timeout_threshold:
                        disconnected_clients.append(client_id)
                        
                # 清理超时连接
                for client_id in disconnected_clients:
                    logger.warning(f"客户端心跳超时，断开连接: {client_id}")
                    await self.disconnect_client(client_id)
                    
                # 发送系统心跳
                if self.active_connections:
                    system_heartbeat = WebSocketEvent(
                        event_type=WebSocketEventType.HEARTBEAT,
                        data={
                            "server_time": current_time.isoformat(),
                            "active_connections": len(self.active_connections)
                        }
                    )
                    
                    # 广播到所有连接
                    for client_id in list(self.active_connections.keys()):
                        await self._send_to_client(client_id, system_heartbeat)
                        
                await asyncio.sleep(30)  # 30秒检查一次
                
            except Exception as e:
                logger.error(f"心跳检查器错误: {e}")
                await asyncio.sleep(30)
                
    async def _event_processor(self):
        """事件处理器"""
        
        while True:
            try:
                # 从队列获取事件
                event = await self.event_queue.get()
                
                # 调用事件处理器
                handlers = self.event_handlers.get(event.event_type, [])
                for handler in handlers:
                    try:
                        if asyncio.iscoroutinefunction(handler):
                            await handler(event)
                        else:
                            handler(event)
                    except Exception as e:
                        logger.error(f"事件处理器执行失败: {handler}: {e}")
                        
                self.connection_stats['total_events_processed'] += 1
                
            except Exception as e:
                logger.error(f"事件处理器错误: {e}")
                await asyncio.sleep(1)
                
    async def cleanup(self):
        """清理资源"""
        
        # 取消后台任务
        for task in self._background_tasks:
            task.cancel()
            
        # 断开所有连接
        for client_id in list(self.active_connections.keys()):
            await self.disconnect_client(client_id)
            
        logger.info("WebSocket服务已清理")


# 全局WebSocket服务实例
_websocket_service: Optional[TransferWebSocketService] = None


def get_transfer_websocket_service() -> TransferWebSocketService:
    """获取全局传输WebSocket服务实例"""
    global _websocket_service
    
    if _websocket_service is None:
        _websocket_service = TransferWebSocketService()
        logger.info("传输WebSocket服务已初始化")
        
    return _websocket_service