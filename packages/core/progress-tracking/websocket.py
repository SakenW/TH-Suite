"""
WebSocket进度推送模块

实现实时进度推送和WebSocket处理
"""

import asyncio
import json
import logging
from typing import Dict, Set, Optional, Any, List
import websockets
from websockets.server import WebSocketServerProtocol
import weakref

from .core import ProgressListener, ProgressEvent, ProgressManager
from .config import ProgressConfig


class WebSocketProgressNotifier(ProgressListener):
    """WebSocket进度通知器"""
    
    def __init__(self, config: ProgressConfig):
        self.config = config
        self.logger = logging.getLogger(__name__)
        self.connections: Set[WebSocketServerProtocol] = set()
        self.client_subscriptions: Dict[WebSocketServerProtocol, Set[str]] = {}
        self.server: Optional[websockets.WebSocketServer] = None
        self._last_notification_time: Dict[str, float] = {}
        
    async def start_server(self) -> None:
        """启动WebSocket服务器"""
        if not self.config.websocket_enabled:
            return
        
        try:
            self.server = await websockets.serve(
                self.handle_connection,
                "localhost",
                self.config.websocket_port,
                ping_interval=20,
                ping_timeout=10,
                close_timeout=5
            )
            
            self.logger.info(
                f"WebSocket进度服务器启动在端口 {self.config.websocket_port}, "
                f"路径 {self.config.websocket_path}"
            )
            
        except Exception as e:
            self.logger.error(f"启动WebSocket服务器失败: {e}")
            raise
    
    async def stop_server(self) -> None:
        """停止WebSocket服务器"""
        if self.server:
            self.server.close()
            await self.server.wait_closed()
            self.server = None
            
            # 关闭所有连接
            if self.connections:
                await asyncio.gather(
                    *[conn.close() for conn in self.connections],
                    return_exceptions=True
                )
            
            self.connections.clear()
            self.client_subscriptions.clear()
            self.logger.info("WebSocket进度服务器已停止")
    
    async def handle_connection(
        self, 
        websocket: WebSocketServerProtocol, 
        path: str
    ) -> None:
        """处理WebSocket连接"""
        if path != self.config.websocket_path:
            await websocket.close(code=1008, reason="Invalid path")
            return
        
        self.connections.add(websocket)
        self.client_subscriptions[websocket] = set()
        
        try:
            self.logger.info(f"新的WebSocket连接: {websocket.remote_address}")
            
            async for message in websocket:
                await self.handle_message(websocket, message)
                
        except websockets.exceptions.ConnectionClosed:
            self.logger.info(f"WebSocket连接已断开: {websocket.remote_address}")
        except Exception as e:
            self.logger.error(f"WebSocket连接错误: {e}")
        finally:
            self.connections.discard(websocket)
            self.client_subscriptions.pop(websocket, None)
    
    async def handle_message(
        self, 
        websocket: WebSocketServerProtocol, 
        message: str
    ) -> None:
        """处理客户端消息"""
        try:
            data = json.loads(message)
            message_type = data.get('type')
            
            if message_type == 'subscribe':
                await self.handle_subscribe(websocket, data)
            elif message_type == 'unsubscribe':
                await self.handle_unsubscribe(websocket, data)
            elif message_type == 'get_status':
                await self.handle_get_status(websocket, data)
            elif message_type == 'ping':
                await self.send_message(websocket, {'type': 'pong'})
            else:
                await self.send_error(websocket, f"未知消息类型: {message_type}")
                
        except json.JSONDecodeError:
            await self.send_error(websocket, "无效的JSON格式")
        except Exception as e:
            self.logger.error(f"处理消息失败: {e}")
            await self.send_error(websocket, str(e))
    
    async def handle_subscribe(
        self, 
        websocket: WebSocketServerProtocol, 
        data: Dict[str, Any]
    ) -> None:
        """处理订阅请求"""
        task_ids = data.get('task_ids', [])
        
        if isinstance(task_ids, str):
            task_ids = [task_ids]
        
        if not task_ids:
            # 订阅所有任务
            self.client_subscriptions[websocket].add('*')
        else:
            # 订阅特定任务
            for task_id in task_ids:
                self.client_subscriptions[websocket].add(task_id)
        
        await self.send_message(websocket, {
            'type': 'subscribe_response',
            'success': True,
            'subscriptions': list(self.client_subscriptions[websocket])
        })
        
        self.logger.debug(f"客户端订阅任务: {task_ids}")
    
    async def handle_unsubscribe(
        self, 
        websocket: WebSocketServerProtocol, 
        data: Dict[str, Any]
    ) -> None:
        """处理取消订阅请求"""
        task_ids = data.get('task_ids', [])
        
        if isinstance(task_ids, str):
            task_ids = [task_ids]
        
        if not task_ids:
            # 取消订阅所有任务
            self.client_subscriptions[websocket].clear()
        else:
            # 取消订阅特定任务
            for task_id in task_ids:
                self.client_subscriptions[websocket].discard(task_id)
        
        await self.send_message(websocket, {
            'type': 'unsubscribe_response',
            'success': True,
            'subscriptions': list(self.client_subscriptions[websocket])
        })
        
        self.logger.debug(f"客户端取消订阅任务: {task_ids}")
    
    async def handle_get_status(
        self, 
        websocket: WebSocketServerProtocol, 
        data: Dict[str, Any]
    ) -> None:
        """处理状态查询请求"""
        response = {
            'type': 'status_response',
            'connected_clients': len(self.connections),
            'server_info': {
                'port': self.config.websocket_port,
                'path': self.config.websocket_path,
                'notifications_enabled': self.config.enable_notifications
            }
        }
        
        await self.send_message(websocket, response)
    
    async def send_message(
        self, 
        websocket: WebSocketServerProtocol, 
        message: Dict[str, Any]
    ) -> None:
        """发送消息到客户端"""
        try:
            await websocket.send(json.dumps(message))
        except websockets.exceptions.ConnectionClosed:
            self.connections.discard(websocket)
        except Exception as e:
            self.logger.error(f"发送消息失败: {e}")
    
    async def send_error(
        self, 
        websocket: WebSocketServerProtocol, 
        error_message: str
    ) -> None:
        """发送错误消息"""
        await self.send_message(websocket, {
            'type': 'error',
            'message': error_message
        })
    
    async def on_progress_event(self, event: ProgressEvent) -> None:
        """处理进度事件"""
        if not self.config.enable_notifications or not self.connections:
            return
        
        # 节流处理
        current_time = asyncio.get_event_loop().time()
        throttle_key = f"{event.task_id}:{event.event_type.value}"
        
        if throttle_key in self._last_notification_time:
            if (current_time - self._last_notification_time[throttle_key]) < self.config.notification_throttle:
                return
        
        self._last_notification_time[throttle_key] = current_time
        
        # 构建通知消息
        message = {
            'type': 'progress_event',
            'event': event.to_dict()
        }
        
        # 发送给订阅的客户端
        for websocket in self.connections.copy():
            subscriptions = self.client_subscriptions.get(websocket, set())
            
            if '*' in subscriptions or event.task_id in subscriptions:
                await self.send_message(websocket, message)
    
    async def broadcast_progress_update(
        self, 
        task_id: str, 
        progress_data: Dict[str, Any]
    ) -> None:
        """广播进度更新"""
        if not self.connections:
            return
        
        message = {
            'type': 'progress_update',
            'task_id': task_id,
            'progress': progress_data
        }
        
        # 发送给订阅的客户端
        for websocket in self.connections.copy():
            subscriptions = self.client_subscriptions.get(websocket, set())
            
            if '*' in subscriptions or task_id in subscriptions:
                await self.send_message(websocket, message)
    
    async def broadcast_task_list(self, tasks: List[Dict[str, Any]]) -> None:
        """广播任务列表"""
        if not self.connections:
            return
        
        message = {
            'type': 'task_list',
            'tasks': tasks
        }
        
        # 发送给所有客户端
        for websocket in self.connections.copy():
            await self.send_message(websocket, message)
    
    def get_connection_count(self) -> int:
        """获取连接数"""
        return len(self.connections)
    
    def get_subscription_info(self) -> Dict[str, Any]:
        """获取订阅信息"""
        subscription_counts = {}
        total_subscriptions = 0
        
        for subscriptions in self.client_subscriptions.values():
            total_subscriptions += len(subscriptions)
            for task_id in subscriptions:
                subscription_counts[task_id] = subscription_counts.get(task_id, 0) + 1
        
        return {
            'total_connections': len(self.connections),
            'total_subscriptions': total_subscriptions,
            'subscription_counts': subscription_counts
        }


class ProgressWebSocketHandler:
    """进度WebSocket处理器"""
    
    def __init__(self, progress_manager: ProgressManager, config: ProgressConfig):
        self.progress_manager = progress_manager
        self.config = config
        self.notifier = WebSocketProgressNotifier(config)
        self.logger = logging.getLogger(__name__)
        
        # 将通知器添加为进度监听器
        self.progress_manager.add_listener(self.notifier)
    
    async def start(self) -> None:
        """启动WebSocket处理器"""
        await self.notifier.start_server()
        self.logger.info("进度WebSocket处理器已启动")
    
    async def stop(self) -> None:
        """停止WebSocket处理器"""
        self.progress_manager.remove_listener(self.notifier)
        await self.notifier.stop_server()
        self.logger.info("进度WebSocket处理器已停止")
    
    async def broadcast_all_tasks(self) -> None:
        """广播所有任务状态"""
        tasks = self.progress_manager.tracker.list_tasks()
        task_data = [task.to_dict() for task in tasks]
        await self.notifier.broadcast_task_list(task_data)
    
    async def notify_task_update(self, task_id: str) -> None:
        """通知任务更新"""
        progress = self.progress_manager.tracker.get_task_progress(task_id)
        if progress:
            await self.notifier.broadcast_progress_update(
                task_id, 
                progress.to_dict()
            )
    
    def get_stats(self) -> Dict[str, Any]:
        """获取统计信息"""
        return {
            'websocket_enabled': self.config.websocket_enabled,
            'server_running': self.notifier.server is not None,
            'connection_info': self.notifier.get_subscription_info(),
            'active_tasks': len(self.progress_manager.tracker.list_tasks()),
            'config': {
                'port': self.config.websocket_port,
                'path': self.config.websocket_path,
                'notification_throttle': self.config.notification_throttle
            }
        }


# WebSocket客户端示例
class ProgressWebSocketClient:
    """进度WebSocket客户端"""
    
    def __init__(self, url: str):
        self.url = url
        self.websocket: Optional[WebSocketServerProtocol] = None
        self.subscriptions: Set[str] = set()
        self.message_handlers: Dict[str, callable] = {}
        self.logger = logging.getLogger(f"{__name__}.Client")
    
    async def connect(self) -> None:
        """连接到WebSocket服务器"""
        try:
            self.websocket = await websockets.connect(self.url)
            self.logger.info(f"已连接到进度服务器: {self.url}")
            
            # 启动消息监听
            asyncio.create_task(self._message_listener())
            
        except Exception as e:
            self.logger.error(f"连接进度服务器失败: {e}")
            raise
    
    async def disconnect(self) -> None:
        """断开连接"""
        if self.websocket:
            await self.websocket.close()
            self.websocket = None
            self.logger.info("已断开进度服务器连接")
    
    async def subscribe(self, task_ids: List[str] = None) -> None:
        """订阅任务进度"""
        if not self.websocket:
            raise RuntimeError("未连接到服务器")
        
        message = {
            'type': 'subscribe',
            'task_ids': task_ids or []
        }
        
        await self.websocket.send(json.dumps(message))
        
        if task_ids:
            self.subscriptions.update(task_ids)
        else:
            self.subscriptions.add('*')
    
    async def unsubscribe(self, task_ids: List[str] = None) -> None:
        """取消订阅"""
        if not self.websocket:
            raise RuntimeError("未连接到服务器")
        
        message = {
            'type': 'unsubscribe',
            'task_ids': task_ids or []
        }
        
        await self.websocket.send(json.dumps(message))
        
        if task_ids:
            for task_id in task_ids:
                self.subscriptions.discard(task_id)
        else:
            self.subscriptions.clear()
    
    async def get_status(self) -> None:
        """获取服务器状态"""
        if not self.websocket:
            raise RuntimeError("未连接到服务器")
        
        message = {'type': 'get_status'}
        await self.websocket.send(json.dumps(message))
    
    def on_message(self, message_type: str, handler: callable) -> None:
        """注册消息处理器"""
        self.message_handlers[message_type] = handler
    
    async def _message_listener(self) -> None:
        """消息监听器"""
        try:
            async for message in self.websocket:
                try:
                    data = json.loads(message)
                    message_type = data.get('type')
                    
                    handler = self.message_handlers.get(message_type)
                    if handler:
                        if asyncio.iscoroutinefunction(handler):
                            await handler(data)
                        else:
                            handler(data)
                    else:
                        self.logger.debug(f"未处理的消息类型: {message_type}")
                        
                except json.JSONDecodeError:
                    self.logger.error("收到无效的JSON消息")
                except Exception as e:
                    self.logger.error(f"处理消息失败: {e}")
                    
        except websockets.exceptions.ConnectionClosed:
            self.logger.info("服务器连接已断开")
        except Exception as e:
            self.logger.error(f"消息监听错误: {e}")