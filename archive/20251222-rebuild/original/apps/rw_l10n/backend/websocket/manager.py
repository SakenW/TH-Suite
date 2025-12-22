import asyncio
import json
from datetime import datetime
from enum import Enum
from typing import Any

from fastapi import WebSocket

from packages.core.logging import get_logger

logger = get_logger(__name__)


class MessageType(str, Enum):
    """WebSocket 消息类型"""

    # 系统消息
    SYSTEM_STATUS = "system_status"
    SYSTEM_ERROR = "system_error"

    # 任务消息
    TASK_STARTED = "task_started"
    TASK_PROGRESS = "task_progress"
    TASK_COMPLETED = "task_completed"
    TASK_FAILED = "task_failed"

    # 模组消息
    MOD_INSTALLED = "mod_installed"
    MOD_UNINSTALLED = "mod_uninstalled"
    MOD_UPDATED = "mod_updated"
    MOD_ENABLED = "mod_enabled"
    MOD_DISABLED = "mod_disabled"

    # Workshop 消息
    WORKSHOP_SUBSCRIBED = "workshop_subscribed"
    WORKSHOP_UNSUBSCRIBED = "workshop_unsubscribed"
    WORKSHOP_UPDATED = "workshop_updated"
    WORKSHOP_SYNC_STARTED = "workshop_sync_started"
    WORKSHOP_SYNC_COMPLETED = "workshop_sync_completed"

    # 存档消息
    SAVE_BACKED_UP = "save_backed_up"
    SAVE_RESTORED = "save_restored"
    SAVE_ANALYZED = "save_analyzed"
    SAVE_UPLOADED = "save_uploaded"
    SAVE_DELETED = "save_deleted"

    # 配置消息
    CONFIG_UPDATED = "config_updated"
    CONFIG_RESET = "config_reset"
    CONFIG_IMPORTED = "config_imported"
    CONFIG_EXPORTED = "config_exported"

    # 通知消息
    NOTIFICATION = "notification"
    LOG_MESSAGE = "log_message"


class NotificationLevel(str, Enum):
    """通知级别"""

    INFO = "info"
    SUCCESS = "success"
    WARNING = "warning"
    ERROR = "error"


class WebSocketMessage:
    """WebSocket 消息模型"""

    def __init__(
        self,
        message_type: MessageType,
        data: Any = None,
        timestamp: datetime | None = None,
        client_id: str | None = None,
    ):
        self.type = message_type
        self.data = data or {}
        self.timestamp = timestamp or datetime.now()
        self.client_id = client_id

    def to_dict(self) -> dict[str, Any]:
        """转换为字典"""
        return {
            "type": self.type,
            "data": self.data,
            "timestamp": self.timestamp.isoformat(),
            "client_id": self.client_id,
        }

    def to_json(self) -> str:
        """转换为 JSON 字符串"""
        return json.dumps(self.to_dict(), ensure_ascii=False)


class WebSocketClient:
    """WebSocket 客户端信息"""

    def __init__(self, client_id: str, websocket: WebSocket):
        self.client_id = client_id
        self.websocket = websocket
        self.connected_at = datetime.now()
        self.last_ping = datetime.now()
        self.subscriptions: set[str] = set()
        self.metadata: dict[str, Any] = {}

    async def send_message(self, message: WebSocketMessage):
        """发送消息"""
        try:
            await self.websocket.send_text(message.to_json())
        except Exception as e:
            logger.error(f"Failed to send message to client {self.client_id}: {e}")
            raise

    async def ping(self):
        """发送心跳"""
        try:
            await self.websocket.ping()
            self.last_ping = datetime.now()
        except Exception as e:
            logger.error(f"Failed to ping client {self.client_id}: {e}")
            raise


class WebSocketManager:
    """WebSocket 连接管理器"""

    def __init__(self):
        self.clients: dict[str, WebSocketClient] = {}
        self.message_history: list[WebSocketMessage] = []
        self.max_history_size = 1000
        self._heartbeat_task: asyncio.Task | None = None
        self._cleanup_task: asyncio.Task | None = None

        # 启动后台任务
        self._start_background_tasks()

    def _start_background_tasks(self):
        """启动后台任务"""
        if self._heartbeat_task is None or self._heartbeat_task.done():
            self._heartbeat_task = asyncio.create_task(self._heartbeat_loop())

        if self._cleanup_task is None or self._cleanup_task.done():
            self._cleanup_task = asyncio.create_task(self._cleanup_loop())

    async def connect(self, client_id: str, websocket: WebSocket) -> WebSocketClient:
        """连接客户端"""
        try:
            await websocket.accept()

            # 如果客户端已存在，先断开旧连接
            if client_id in self.clients:
                await self.disconnect(client_id)

            # 创建新客户端
            client = WebSocketClient(client_id, websocket)
            self.clients[client_id] = client

            logger.info(f"WebSocket client connected: {client_id}")

            # 发送连接成功消息
            await self.send_to_client(
                client_id,
                MessageType.SYSTEM_STATUS,
                {"status": "connected", "client_id": client_id},
            )

            # 发送最近的消息历史
            await self._send_message_history(client)

            return client

        except Exception as e:
            logger.error(f"Failed to connect WebSocket client {client_id}: {e}")
            raise

    async def disconnect(self, client_id: str):
        """断开客户端连接"""
        try:
            if client_id in self.clients:
                client = self.clients[client_id]
                try:
                    await client.websocket.close()
                except Exception:
                    pass  # 忽略关闭错误

                del self.clients[client_id]
                logger.info(f"WebSocket client disconnected: {client_id}")

        except Exception as e:
            logger.error(f"Failed to disconnect WebSocket client {client_id}: {e}")

    async def send_to_client(
        self, client_id: str, message_type: MessageType, data: Any = None
    ):
        """发送消息给特定客户端"""
        try:
            if client_id not in self.clients:
                logger.warning(f"Client {client_id} not found")
                return

            client = self.clients[client_id]
            message = WebSocketMessage(message_type, data, client_id=client_id)

            await client.send_message(message)
            self._add_to_history(message)

        except Exception as e:
            logger.error(f"Failed to send message to client {client_id}: {e}")
            # 如果发送失败，可能是连接已断开
            await self.disconnect(client_id)

    async def broadcast(
        self,
        message_type: MessageType,
        data: Any = None,
        exclude_clients: list[str] | None = None,
    ):
        """广播消息给所有客户端"""
        try:
            exclude_clients = exclude_clients or []
            message = WebSocketMessage(message_type, data)

            # 发送给所有连接的客户端
            disconnected_clients = []
            for client_id, client in self.clients.items():
                if client_id not in exclude_clients:
                    try:
                        await client.send_message(message)
                    except Exception as e:
                        logger.error(
                            f"Failed to send broadcast to client {client_id}: {e}"
                        )
                        disconnected_clients.append(client_id)

            # 清理断开的客户端
            for client_id in disconnected_clients:
                await self.disconnect(client_id)

            self._add_to_history(message)

        except Exception as e:
            logger.error(f"Failed to broadcast message: {e}")

    async def send_notification(
        self,
        title: str,
        message: str,
        level: NotificationLevel = NotificationLevel.INFO,
        client_id: str | None = None,
        action_url: str | None = None,
    ):
        """发送通知"""
        try:
            notification_data = {
                "title": title,
                "message": message,
                "level": level,
                "action_url": action_url,
                "timestamp": datetime.now().isoformat(),
            }

            if client_id:
                await self.send_to_client(
                    client_id, MessageType.NOTIFICATION, notification_data
                )
            else:
                await self.broadcast(MessageType.NOTIFICATION, notification_data)

        except Exception as e:
            logger.error(f"Failed to send notification: {e}")

    async def send_task_update(
        self,
        task_id: str,
        status: str,
        progress: float | None = None,
        message: str | None = None,
        client_id: str | None = None,
    ):
        """发送任务更新"""
        try:
            task_data = {
                "task_id": task_id,
                "status": status,
                "progress": progress,
                "message": message,
                "timestamp": datetime.now().isoformat(),
            }

            # 根据状态选择消息类型
            if status == "running":
                message_type = MessageType.TASK_PROGRESS
            elif status == "completed":
                message_type = MessageType.TASK_COMPLETED
            elif status == "failed":
                message_type = MessageType.TASK_FAILED
            else:
                message_type = MessageType.TASK_STARTED

            if client_id:
                await self.send_to_client(client_id, message_type, task_data)
            else:
                await self.broadcast(message_type, task_data)

        except Exception as e:
            logger.error(f"Failed to send task update: {e}")

    async def send_log_message(
        self,
        level: str,
        message: str,
        module: str | None = None,
        client_id: str | None = None,
    ):
        """发送日志消息"""
        try:
            log_data = {
                "level": level,
                "message": message,
                "module": module,
                "timestamp": datetime.now().isoformat(),
            }

            if client_id:
                await self.send_to_client(client_id, MessageType.LOG_MESSAGE, log_data)
            else:
                await self.broadcast(MessageType.LOG_MESSAGE, log_data)

        except Exception as e:
            logger.error(f"Failed to send log message: {e}")

    def get_connected_clients(self) -> list[str]:
        """获取已连接的客户端列表"""
        return list(self.clients.keys())

    def get_client_count(self) -> int:
        """获取连接的客户端数量"""
        return len(self.clients)

    def get_client_info(self, client_id: str) -> dict[str, Any] | None:
        """获取客户端信息"""
        if client_id not in self.clients:
            return None

        client = self.clients[client_id]
        return {
            "client_id": client.client_id,
            "connected_at": client.connected_at.isoformat(),
            "last_ping": client.last_ping.isoformat(),
            "subscriptions": list(client.subscriptions),
            "metadata": client.metadata,
        }

    def subscribe_client(self, client_id: str, topic: str):
        """客户端订阅主题"""
        if client_id in self.clients:
            self.clients[client_id].subscriptions.add(topic)

    def unsubscribe_client(self, client_id: str, topic: str):
        """客户端取消订阅主题"""
        if client_id in self.clients:
            self.clients[client_id].subscriptions.discard(topic)

    def set_client_metadata(self, client_id: str, metadata: dict[str, Any]):
        """设置客户端元数据"""
        if client_id in self.clients:
            self.clients[client_id].metadata.update(metadata)

    def _add_to_history(self, message: WebSocketMessage):
        """添加消息到历史记录"""
        self.message_history.append(message)

        # 限制历史记录大小
        if len(self.message_history) > self.max_history_size:
            self.message_history = self.message_history[-self.max_history_size :]

    async def _send_message_history(self, client: WebSocketClient):
        """发送消息历史给新连接的客户端"""
        try:
            # 发送最近的 50 条消息
            recent_messages = self.message_history[-50:]
            for message in recent_messages:
                await client.send_message(message)

        except Exception as e:
            logger.error(
                f"Failed to send message history to client {client.client_id}: {e}"
            )

    async def _heartbeat_loop(self):
        """心跳循环"""
        while True:
            try:
                await asyncio.sleep(30)  # 每 30 秒发送一次心跳

                disconnected_clients = []
                for client_id, client in self.clients.items():
                    try:
                        await client.ping()
                    except Exception:
                        disconnected_clients.append(client_id)

                # 清理断开的客户端
                for client_id in disconnected_clients:
                    await self.disconnect(client_id)

            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in heartbeat loop: {e}")

    async def _cleanup_loop(self):
        """清理循环"""
        while True:
            try:
                await asyncio.sleep(300)  # 每 5 分钟清理一次

                # 清理超时的客户端
                current_time = datetime.now()
                timeout_clients = []

                for client_id, client in self.clients.items():
                    # 如果客户端超过 10 分钟没有心跳，认为已断开
                    if (current_time - client.last_ping).total_seconds() > 600:
                        timeout_clients.append(client_id)

                for client_id in timeout_clients:
                    logger.info(f"Cleaning up timeout client: {client_id}")
                    await self.disconnect(client_id)

                # 清理旧的消息历史
                if len(self.message_history) > self.max_history_size:
                    self.message_history = self.message_history[
                        -self.max_history_size :
                    ]

            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in cleanup loop: {e}")

    async def shutdown(self):
        """关闭管理器"""
        try:
            # 取消后台任务
            if self._heartbeat_task:
                self._heartbeat_task.cancel()
            if self._cleanup_task:
                self._cleanup_task.cancel()

            # 断开所有客户端
            for client_id in list(self.clients.keys()):
                await self.disconnect(client_id)

            logger.info("WebSocket manager shutdown completed")

        except Exception as e:
            logger.error(f"Error during WebSocket manager shutdown: {e}")


# 全局 WebSocket 管理器实例
websocket_manager = WebSocketManager()
