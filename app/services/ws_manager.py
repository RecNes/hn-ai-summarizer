"""WebSocket connection manager for device communication.

Manages active WebSocket connections from Android/iOS devices,
handles broadcasting, stale connection cleanup, and per-device messaging.
"""

import asyncio
import json
import logging
from datetime import UTC, datetime

from fastapi import WebSocket

from app.core.database import AsyncSessionLocal
from app.services.device_service import update_device_connection

logger = logging.getLogger(__name__)


class ConnectionManager:
    """Singleton WebSocket connection manager.

    Tracks active device connections and provides broadcast/send capabilities.
    """

    def __init__(self):
        self.active_connections: dict[str, WebSocket] = {}
        self.last_ping: dict[str, datetime] = {}
        self._cleanup_task: asyncio.Task | None = None

    async def connect(self, websocket: WebSocket, device_id: str) -> None:
        """Register a new WebSocket connection for a device."""
        await websocket.accept()
        self.active_connections[device_id] = websocket
        self.last_ping[device_id] = datetime.now(UTC)

        # Update DB connection status
        db = None
        try:
            db = AsyncSessionLocal()
            await update_device_connection(db, device_id, is_connected=True)
        except Exception as e:
            logger.warning("Failed to update DB connection status for %s: %s", device_id, e)
        finally:
            if db:
                await db.close()

        logger.info(
            "Device %s connected (total: %d)", device_id, len(self.active_connections)
        )

        # Start cleanup task if not running
        if self._cleanup_task is None or self._cleanup_task.done():
            self._cleanup_task = asyncio.create_task(self._cleanup_loop())

    async def disconnect(self, device_id: str) -> None:
        """Remove a device's WebSocket connection."""
        if device_id in self.active_connections:
            try:
                ws = self.active_connections[device_id]
                await ws.close()
            except Exception:
                pass
            del self.active_connections[device_id]

        if device_id in self.last_ping:
            del self.last_ping[device_id]

        # Update DB connection status
        db = None
        try:
            db = AsyncSessionLocal()
            await update_device_connection(db, device_id, is_connected=False)
        except Exception as e:
            logger.warning("Failed to update DB disconnect status for %s: %s", device_id, e)
        finally:
            if db:
                await db.close()

        logger.info(
            "Device %s disconnected (total: %d)", device_id, len(self.active_connections)
        )

    async def send_to_device(self, device_id: str, message: dict) -> bool:
        """Send a JSON message to a specific device. Returns True if sent."""
        ws = self.active_connections.get(device_id)
        if ws is None:
            return False
        try:
            await ws.send_text(json.dumps(message))
            return True
        except Exception as e:
            logger.warning("Failed to send message to device %s: %s", device_id, e)
            await self.disconnect(device_id)
            return False

    async def broadcast(self, message: dict) -> int:
        """Broadcast a JSON message to all connected devices. Returns sent count."""
        sent = 0
        for device_id in list(self.active_connections.keys()):
            if await self.send_to_device(device_id, message):
                sent += 1
        return sent

    async def broadcast_new_content(self, story_count: int) -> int:
        """Broadcast new content notification to all connected devices."""
        message = {
            "type": "new_content",
            "story_count": story_count,
            "timestamp": datetime.now(UTC).isoformat(),
        }
        sent = await self.broadcast(message)
        logger.info(
            "Broadcasted new_content (%d stories) to %d devices",
            story_count,
            sent,
        )
        return sent

    def get_connected_device_ids(self) -> set[str]:
        """Get the set of currently connected device IDs."""
        return set(self.active_connections.keys())

    async def _cleanup_loop(self) -> None:
        """Periodically clean up stale connections (60 second TTL with keepalive pings)."""
        while True:
            await asyncio.sleep(30)
            await self.cleanup_stale_connections(ttl=60)

    async def cleanup_stale_connections(self, ttl: int = 60) -> int:
        """Remove connections that haven't sent a ping in TTL seconds. Returns removed count."""
        now = datetime.now(UTC)
        stale = []
        for device_id, last in self.last_ping.items():
            if (now - last).total_seconds() > ttl:
                stale.append(device_id)

        for device_id in stale:
            logger.info("Cleaning up stale connection: %s (last ping: %s)", device_id, self.last_ping.get(device_id))
            await self.disconnect(device_id)

        return len(stale)

    async def update_ping(self, device_id: str) -> None:
        """Update the last ping timestamp for a device (called on keepalive messages)."""
        self.last_ping[device_id] = datetime.now(UTC)


# Global singleton instance
ws_manager = ConnectionManager()