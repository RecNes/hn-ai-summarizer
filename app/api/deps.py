"""Dependency injection helpers for device authentication."""

import logging
from typing import Any

from fastapi import Depends, HTTPException, WebSocket, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.models.device import Device
from app.services.device_service import get_device_by_id, verify_device_token

logger = logging.getLogger(__name__)


async def get_current_device_from_token(
    token: str,
    db: AsyncSession = Depends(get_db),
) -> Device:
    """Dependency: validates JWT auth token from REST requests, returns Device."""
    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Device auth token required. Use ?token=YOUR_TOKEN query parameter.",
        )

    payload = verify_device_token(token)
    if not payload:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired device auth token",
        )

    device_id = payload.get("device_id")
    if not device_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token payload",
        )

    device = await get_device_by_id(db, device_id)
    if not device:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Device not found. It may have been revoked.",
        )

    if not device.is_paired:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Device is not paired",
        )

    if device.auth_token != token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token mismatch. Device may have been re-paired.",
        )

    return device


async def get_ws_device(
    websocket: WebSocket,
    device_id: str,
) -> Device | None:
    """Validate WebSocket connection by device_id and token query param.

    Token is extracted from the WebSocket URL query string.
    Returns Device if valid, None otherwise.
    """
    from app.core.database import AsyncSessionLocal

    token = websocket.query_params.get("token", "")
    if not token:
        await websocket.close(code=4001, reason="Missing token")
        return None

    payload = verify_device_token(token)
    if not payload:
        await websocket.close(code=4001, reason="Invalid token")
        return None

    token_device_id = payload.get("device_id", "")
    if token_device_id != device_id:
        await websocket.close(code=4001, reason="Token does not match device_id")
        return None

    db: Any = None
    try:
        db = AsyncSessionLocal()
        device = await get_device_by_id(db, device_id)
        if not device or not device.is_paired:
            await websocket.close(code=4001, reason="Device not found or not paired")
            return None
        return device
    except Exception as e:
        logger.warning("WS auth error for %s: %s", device_id, e)
        await websocket.close(code=4001, reason="Auth error")
        return None
    finally:
        if db:
            await db.close()