"""WebSocket management for real-time communication in TransHub Tools."""

import json
from datetime import datetime
from typing import Any

from fastapi import WebSocket, WebSocketDisconnect
from pydantic import BaseModel

from packages.core.framework.logging import get_logger
from packages.core.models import JobStatus


class WebSocketMessage(BaseModel):
    """WebSocket message structure."""

    type: str
    data: dict[str, Any]
    timestamp: datetime = None

    def __init__(self, **data):
        if "timestamp" not in data:
            data["timestamp"] = datetime.utcnow()
        super().__init__(**data)

    def to_json(self) -> str:
        """Convert message to JSON string."""
        return self.model_dump_json()


class ProgressMessage(WebSocketMessage):
    """Progress update message."""

    def __init__(
        self, job_id: str, status: JobStatus, progress: float, message: str, **kwargs
    ):
        super().__init__(
            type="progress",
            data={
                "job_id": job_id,
                "status": status.value,
                "progress": progress,
                "message": message,
                **kwargs,
            },
        )


class LogMessage(WebSocketMessage):
    """Log message."""

    def __init__(self, level: str, message: str, **kwargs):
        super().__init__(
            type="log", data={"level": level, "message": message, **kwargs}
        )


class ErrorMessage(WebSocketMessage):
    """Error message."""

    def __init__(self, error_type: str, message: str, **kwargs):
        super().__init__(
            type="error", data={"error_type": error_type, "message": message, **kwargs}
        )


class WebSocketConnection:
    """Represents a WebSocket connection with metadata."""

    def __init__(self, websocket: WebSocket, connection_id: str):
        self.websocket = websocket
        self.connection_id = connection_id
        self.connected_at = datetime.utcnow()
        self.subscriptions: set[str] = set()
        self.metadata: dict[str, Any] = {}

    async def send_message(self, message: WebSocketMessage):
        """Send a message to this connection."""
        try:
            await self.websocket.send_text(message.to_json())
        except Exception as e:
            # Connection might be closed
            raise WebSocketDisconnect() from e

    def subscribe(self, topic: str):
        """Subscribe to a topic."""
        self.subscriptions.add(topic)

    def unsubscribe(self, topic: str):
        """Unsubscribe from a topic."""
        self.subscriptions.discard(topic)

    def is_subscribed(self, topic: str) -> bool:
        """Check if subscribed to a topic."""
        return topic in self.subscriptions


class WebSocketManager:
    """Manages WebSocket connections and message broadcasting."""

    def __init__(self):
        self.connections: dict[str, WebSocketConnection] = {}
        self.logger = get_logger("thtools.websocket")
        self._connection_counter = 0

    async def connect(self, websocket: WebSocket) -> str:
        """Accept a new WebSocket connection.

        Returns:
            Connection ID
        """
        await websocket.accept()

        # Generate connection ID
        self._connection_counter += 1
        connection_id = (
            f"conn_{self._connection_counter}_{int(datetime.utcnow().timestamp())}"
        )

        # Create connection object
        connection = WebSocketConnection(websocket, connection_id)
        self.connections[connection_id] = connection

        self.logger.info(
            "WebSocket connection established",
            connection_id=connection_id,
            total_connections=len(self.connections),
        )

        try:
            # Send welcome message
            welcome_msg = WebSocketMessage(
                type="welcome",
                data={
                    "connection_id": connection_id,
                    "server_time": datetime.utcnow().isoformat(),
                },
            )
            await connection.send_message(welcome_msg)

            # Listen for messages
            await self._handle_connection(connection)

        except WebSocketDisconnect:
            pass
        except Exception as e:
            self.logger.error(
                "Error in WebSocket connection",
                connection_id=connection_id,
                error=str(e),
                exc_info=True,
            )
        finally:
            await self.disconnect(connection_id)

        return connection_id

    async def disconnect(self, connection_id: str):
        """Disconnect a WebSocket connection."""
        if connection_id in self.connections:
            connection = self.connections[connection_id]

            try:
                await connection.websocket.close()
            except Exception:
                pass  # Connection might already be closed

            del self.connections[connection_id]

            self.logger.info(
                "WebSocket connection closed",
                connection_id=connection_id,
                total_connections=len(self.connections),
                duration=(datetime.utcnow() - connection.connected_at).total_seconds(),
            )

    async def disconnect_all(self):
        """Disconnect all WebSocket connections."""
        connection_ids = list(self.connections.keys())
        for connection_id in connection_ids:
            await self.disconnect(connection_id)

    async def send_to_connection(self, connection_id: str, message: WebSocketMessage):
        """Send a message to a specific connection."""
        if connection_id in self.connections:
            try:
                await self.connections[connection_id].send_message(message)
            except WebSocketDisconnect:
                await self.disconnect(connection_id)
            except Exception as e:
                self.logger.error(
                    "Failed to send message to connection",
                    connection_id=connection_id,
                    error=str(e),
                )

    async def broadcast(self, message: WebSocketMessage, topic: str | None = None):
        """Broadcast a message to all connections or subscribers of a topic."""
        disconnected = []
        sent_count = 0

        for connection_id, connection in self.connections.items():
            # Check if connection is subscribed to topic (if specified)
            if topic and not connection.is_subscribed(topic):
                continue

            try:
                await connection.send_message(message)
                sent_count += 1
            except WebSocketDisconnect:
                disconnected.append(connection_id)
            except Exception as e:
                self.logger.error(
                    "Failed to broadcast message to connection",
                    connection_id=connection_id,
                    error=str(e),
                )

        # Clean up disconnected connections
        for connection_id in disconnected:
            await self.disconnect(connection_id)

        self.logger.debug(
            "Message broadcasted",
            message_type=message.type,
            topic=topic,
            sent_to=sent_count,
            total_connections=len(self.connections),
        )

    async def _handle_connection(self, connection: WebSocketConnection):
        """Handle incoming messages from a WebSocket connection."""
        while True:
            try:
                # Receive message
                data = await connection.websocket.receive_text()
                message_data = json.loads(data)

                # Handle different message types
                message_type = message_data.get("type")

                if message_type == "subscribe":
                    topic = message_data.get("topic")
                    if topic:
                        connection.subscribe(topic)
                        self.logger.debug(
                            "Connection subscribed to topic",
                            connection_id=connection.connection_id,
                            topic=topic,
                        )

                elif message_type == "unsubscribe":
                    topic = message_data.get("topic")
                    if topic:
                        connection.unsubscribe(topic)
                        self.logger.debug(
                            "Connection unsubscribed from topic",
                            connection_id=connection.connection_id,
                            topic=topic,
                        )

                elif message_type == "ping":
                    # Respond with pong
                    pong_msg = WebSocketMessage(
                        type="pong", data={"timestamp": datetime.utcnow().isoformat()}
                    )
                    await connection.send_message(pong_msg)

                else:
                    self.logger.warning(
                        "Unknown message type received",
                        connection_id=connection.connection_id,
                        message_type=message_type,
                    )

            except WebSocketDisconnect:
                break
            except json.JSONDecodeError:
                self.logger.warning(
                    "Invalid JSON received from WebSocket",
                    connection_id=connection.connection_id,
                )
            except Exception as e:
                self.logger.error(
                    "Error handling WebSocket message",
                    connection_id=connection.connection_id,
                    error=str(e),
                    exc_info=True,
                )

    def get_connection_count(self) -> int:
        """Get the number of active connections."""
        return len(self.connections)

    def get_connection_info(self) -> list[dict[str, Any]]:
        """Get information about all connections."""
        return [
            {
                "connection_id": conn.connection_id,
                "connected_at": conn.connected_at.isoformat(),
                "subscriptions": list(conn.subscriptions),
                "metadata": conn.metadata,
            }
            for conn in self.connections.values()
        ]


# Global WebSocket manager instance
_ws_manager: WebSocketManager | None = None


def get_websocket_manager() -> WebSocketManager:
    """Get the global WebSocket manager instance."""
    global _ws_manager
    if _ws_manager is None:
        _ws_manager = WebSocketManager()
    return _ws_manager


async def broadcast_message(message: WebSocketMessage, topic: str | None = None):
    """Broadcast a message using the global WebSocket manager."""
    manager = get_websocket_manager()
    await manager.broadcast(message, topic)


async def send_progress_update(
    job_id: str, status: JobStatus, progress: float, message: str, **kwargs
):
    """Send a progress update message."""
    progress_msg = ProgressMessage(job_id, status, progress, message, **kwargs)
    await broadcast_message(progress_msg, topic=f"job_{job_id}")


async def send_log_message(level: str, message: str, **kwargs):
    """Send a log message."""
    log_msg = LogMessage(level, message, **kwargs)
    await broadcast_message(log_msg, topic="logs")


async def send_error_message(error_type: str, message: str, **kwargs):
    """Send an error message."""
    error_msg = ErrorMessage(error_type, message, **kwargs)
    await broadcast_message(error_msg, topic="errors")
