import json
from typing import Any

from fastapi import APIRouter, Depends, WebSocket, WebSocketDisconnect

from packages.core.logging import get_logger

from ..dependencies import get_websocket_manager
from .manager import MessageType, NotificationLevel, websocket_manager

logger = get_logger(__name__)

router = APIRouter()


@router.websocket("/ws/{client_id}")
async def websocket_endpoint(
    websocket: WebSocket, client_id: str, manager=Depends(get_websocket_manager)
):
    """WebSocket 连接端点"""
    try:
        # 连接客户端
        await manager.connect(client_id, websocket)

        logger.info(f"WebSocket connection established for client: {client_id}")

        try:
            while True:
                # 接收客户端消息
                data = await websocket.receive_text()
                await handle_client_message(client_id, data, manager)

        except WebSocketDisconnect:
            logger.info(f"WebSocket client {client_id} disconnected")
        except Exception as e:
            logger.error(f"Error in WebSocket connection for {client_id}: {e}")
            await manager.send_to_client(
                client_id, MessageType.SYSTEM_ERROR, {"error": str(e)}
            )
        finally:
            await manager.disconnect(client_id)

    except Exception as e:
        logger.error(f"Failed to establish WebSocket connection for {client_id}: {e}")
        try:
            await websocket.close(code=1011, reason=str(e))
        except Exception:
            pass


async def handle_client_message(client_id: str, message: str, manager):
    """处理客户端消息"""
    try:
        # 解析消息
        data = json.loads(message)
        message_type = data.get("type")
        payload = data.get("data", {})

        logger.debug(f"Received message from {client_id}: {message_type}")

        # 处理不同类型的消息
        if message_type == "ping":
            await handle_ping(client_id, payload, manager)
        elif message_type == "subscribe":
            await handle_subscribe(client_id, payload, manager)
        elif message_type == "unsubscribe":
            await handle_unsubscribe(client_id, payload, manager)
        elif message_type == "get_status":
            await handle_get_status(client_id, payload, manager)
        elif message_type == "set_metadata":
            await handle_set_metadata(client_id, payload, manager)
        else:
            logger.warning(f"Unknown message type from {client_id}: {message_type}")
            await manager.send_to_client(
                client_id,
                MessageType.SYSTEM_ERROR,
                {"error": f"Unknown message type: {message_type}"},
            )

    except json.JSONDecodeError as e:
        logger.error(f"Invalid JSON from client {client_id}: {e}")
        await manager.send_to_client(
            client_id, MessageType.SYSTEM_ERROR, {"error": "Invalid JSON format"}
        )
    except Exception as e:
        logger.error(f"Error handling message from {client_id}: {e}")
        await manager.send_to_client(
            client_id, MessageType.SYSTEM_ERROR, {"error": str(e)}
        )


async def handle_ping(client_id: str, payload: dict[str, Any], manager):
    """处理心跳消息"""
    await manager.send_to_client(
        client_id,
        MessageType.SYSTEM_STATUS,
        {
            "type": "pong",
            "timestamp": payload.get("timestamp"),
            "server_time": manager.clients[client_id].last_ping.isoformat(),
        },
    )


async def handle_subscribe(client_id: str, payload: dict[str, Any], manager):
    """处理订阅消息"""
    topics = payload.get("topics", [])
    if not isinstance(topics, list):
        topics = [topics]

    for topic in topics:
        manager.subscribe_client(client_id, topic)

    await manager.send_to_client(
        client_id,
        MessageType.SYSTEM_STATUS,
        {
            "type": "subscribed",
            "topics": topics,
            "all_subscriptions": list(manager.clients[client_id].subscriptions),
        },
    )


async def handle_unsubscribe(client_id: str, payload: dict[str, Any], manager):
    """处理取消订阅消息"""
    topics = payload.get("topics", [])
    if not isinstance(topics, list):
        topics = [topics]

    for topic in topics:
        manager.unsubscribe_client(client_id, topic)

    await manager.send_to_client(
        client_id,
        MessageType.SYSTEM_STATUS,
        {
            "type": "unsubscribed",
            "topics": topics,
            "all_subscriptions": list(manager.clients[client_id].subscriptions),
        },
    )


async def handle_get_status(client_id: str, payload: dict[str, Any], manager):
    """处理获取状态消息"""
    client_info = manager.get_client_info(client_id)

    await manager.send_to_client(
        client_id,
        MessageType.SYSTEM_STATUS,
        {
            "type": "status",
            "client_info": client_info,
            "connected_clients": manager.get_client_count(),
            "server_status": "running",
        },
    )


async def handle_set_metadata(client_id: str, payload: dict[str, Any], manager):
    """处理设置元数据消息"""
    metadata = payload.get("metadata", {})
    manager.set_client_metadata(client_id, metadata)

    await manager.send_to_client(
        client_id,
        MessageType.SYSTEM_STATUS,
        {"type": "metadata_updated", "metadata": manager.clients[client_id].metadata},
    )


# WebSocket 工具函数
async def notify_clients(
    message_type: MessageType, data: Any = None, client_ids: list = None
):
    """通知客户端"""
    if client_ids:
        for client_id in client_ids:
            await websocket_manager.send_to_client(client_id, message_type, data)
    else:
        await websocket_manager.broadcast(message_type, data)


async def send_notification(
    title: str,
    message: str,
    level: NotificationLevel = NotificationLevel.INFO,
    client_id: str = None,
    action_url: str = None,
):
    """发送通知"""
    await websocket_manager.send_notification(
        title=title,
        message=message,
        level=level,
        client_id=client_id,
        action_url=action_url,
    )


async def send_task_update(
    task_id: str,
    status: str,
    progress: float = None,
    message: str = None,
    client_id: str = None,
):
    """发送任务更新"""
    await websocket_manager.send_task_update(
        task_id=task_id,
        status=status,
        progress=progress,
        message=message,
        client_id=client_id,
    )


async def send_log_message(
    level: str, message: str, module: str = None, client_id: str = None
):
    """发送日志消息"""
    await websocket_manager.send_log_message(
        level=level, message=message, module=module, client_id=client_id
    )


# 导出路由和工具函数
__all__ = [
    "router",
    "websocket_manager",
    "notify_clients",
    "send_notification",
    "send_task_update",
    "send_log_message",
    "MessageType",
    "NotificationLevel",
]
