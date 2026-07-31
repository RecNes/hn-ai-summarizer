"""API routes for device pairing, authentication, sync, and WebSocket management."""

import io
import json
import logging
import qrcode
from datetime import UTC, datetime as dt
from fastapi import APIRouter, Depends, HTTPException, Query, WebSocket, WebSocketDisconnect, status
from redis.asyncio import Redis
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_device_from_token, get_ws_device
from app.core.config import settings as app_settings
from app.core.database import get_db
from app.models.device import Device
from app.models.preference import UserPreference
from app.models.story import Story
from app.schemas.device import (
    DevicePairingConfirm,
    DevicePairingRequest,
    DevicePairingResponse,
    DeviceRegisterResponse,
    DeviceResetRequest,
    DeviceRevokeResponse,
    SyncStatusRequest,
)
from app.schemas.story import StoryResponse
from app.services.device_service import (
    apply_read_status,
    confirm_pairing,
    create_device,
    get_paired_devices,
    get_device_by_id,
    reset_device,
    revoke_device,
    update_device_sync_time,
)
from app.services.ws_manager import ws_manager
from app.shared.languages import get_languages

logger = logging.getLogger(__name__)

router = APIRouter()


# ── Token Verify ──────────────────────────────────────────


@router.get("/verify")
async def verify_device_token_endpoint(
    token: str = Query(..., description="Device JWT auth token"),
    db: AsyncSession = Depends(get_db),
):
    """Verify that a stored device token is still valid.
    
    Returns 200 if token is valid and device is still paired.
    Returns 401 if token is invalid, expired, or device was revoked.
    """
    device = await get_current_device_from_token(token, db)
    return {
        "device_id": device.device_id,
        "device_name": device.device_name,
        "valid": True,
    }


# ── Device Registration & Pairing ──────────────────────────


@router.post("/register", response_model=DeviceRegisterResponse)
async def register_device(
    req: DevicePairingRequest,
    db: AsyncSession = Depends(get_db),
):
    """Register a new device for pairing. Returns a 6-digit pairing code."""
    # Check if device already exists
    existing = await get_device_by_id(db, req.device_id)
    if existing:
        # Re-register: generate new pairing code
        from app.services.device_service import _hash_pairing_code, generate_pairing_code

        new_code = generate_pairing_code()
        existing.pairing_code = _hash_pairing_code(new_code)
        existing.is_paired = False
        existing.auth_token = None
        await db.commit()
        return DeviceRegisterResponse(
            device_id=req.device_id,
            pairing_code=new_code,
            message="Device re-registered. Use the new pairing code.",
        )

    # New device
    device = await create_device(db, req.device_name, req.device_id, req.device_type)
    plaintext_code = getattr(device, "_plaintext_pairing_code", "000000")
    return DeviceRegisterResponse(
        device_id=req.device_id,
        pairing_code=plaintext_code,
        message="Device registered. Enter the pairing code shown on the web app.",
    )


@router.post("/confirm", response_model=DevicePairingResponse)
async def confirm_device_pairing(
    req: DevicePairingConfirm,
    db: AsyncSession = Depends(get_db),
):
    """Confirm pairing with the 6-digit code. Returns JWT auth token."""
    result = await confirm_pairing(db, req.device_id, req.pairing_code)
    if not result:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid pairing code. Please check and try again.",
        )
    return DevicePairingResponse(**result)


# ── Device List (Web UI) ──────────────────────────────────


@router.get("/list")
async def list_devices(db: AsyncSession = Depends(get_db)):
    """List all paired devices (for web UI device management panel)."""
    devices = await get_paired_devices(db)
    return [
        {
            "id": d.id,
            "device_name": d.device_name or "Bilinmeyen Cihaz",
            "device_id": d.device_id or "",
            "device_type": d.device_type or "android",
            "is_paired": d.is_paired,
            "is_connected": d.is_connected,
            "last_sync_at": d.last_sync_at.isoformat() if d.last_sync_at else None,
            "paired_at": d.created_at.isoformat() if d.created_at else None,
        }
        for d in devices
    ]


# ── Device Revoke & Reset ─────────────────────────────────


@router.delete("/{device_id}/revoke", response_model=DeviceRevokeResponse)
async def revoke_device_connection(
    device_id: str,
    db: AsyncSession = Depends(get_db),
):
    """Revoke a device connection from web app — invalidate token, close WS."""
    # Send revoked message via WebSocket before revoking
    await ws_manager.send_to_device(
        device_id,
        {"type": "revoked", "message": "Bağlantınız yönetici tarafından sonlandırıldı"},
    )

    # Revoke in DB
    result = await revoke_device(db, device_id)

    # Close WS connection
    await ws_manager.disconnect(device_id)

    return DeviceRevokeResponse(**result)


@router.post("/{device_id}/reset", response_model=DeviceRevokeResponse)
async def reset_device_data(
    device_id: str,
    db: AsyncSession = Depends(get_db),
):
    """Factory reset from Android client — clear all pairing data on server."""
    result = await reset_device(db, device_id)
    await ws_manager.disconnect(device_id)
    return DeviceRevokeResponse(**result)


# ── Sync Endpoints ────────────────────────────────────────


@router.get("/sync")
async def sync_data(
    token: str = Query(..., description="Device JWT auth token"),
    last_synced_story_id: int = Query(0, description="Last synced story ID from device"),
    db: AsyncSession = Depends(get_db),
):
    """Get new stories since last sync, plus preferences and settings.

    Requires device auth token as query parameter.
    """
    device = await get_current_device_from_token(token, db)

    # Get new stories since last_synced_story_id
    from sqlalchemy.future import select

    result = await db.execute(
        select(Story)
        .where(Story.is_blocked.is_(False), Story.id > last_synced_story_id)
        .order_by(Story.id.asc())
    )
    new_stories = result.scalars().all()

    # Get user preferences
    pref_result = await db.execute(select(UserPreference).limit(1))
    prefs = pref_result.scalar_one_or_none()

    # Update sync time
    await update_device_sync_time(db, device.device_id)

    return {
        "new_stories": [
            {
                "id": s.id,
                "hacker_news_id": s.hacker_news_id,
                "title": s.title,
                "title_tr": s.title_tr,
                "url": s.url,
                "score": s.score,
                "author": s.author,
                "content_tr": s.content_tr,
                "comments_summary": s.comments_summary,
                "image_url": s.image_url,
                "is_translated": s.is_translated,
                "is_read": s.is_read,
                "is_highlighted": s.is_highlighted,
                "is_dimmed": s.is_dimmed,
                "created_at": s.created_at.isoformat() if s.created_at else None,
                "hn_created_at": s.hn_created_at.isoformat() if s.hn_created_at else None,
            }
            for s in new_stories
        ],
        "deleted_story_ids": [],
        "preferences": {
            "ui_language": prefs.ui_language if prefs else "en",
            "translation_language": prefs.translation_language if prefs else "en",
            "available_languages": get_languages() if prefs else [],
        },
        "settings": {
            "ui_language": prefs.ui_language if prefs else "en",
            "translation_language": prefs.translation_language if prefs else "en",
            "dark_mode": "system",
        },
        "sync_timestamp": device.last_sync_at.isoformat() if device.last_sync_at else None,
    }


@router.post("/sync/read-status")
async def sync_read_status(
    req: SyncStatusRequest,
    token: str = Query(..., description="Device JWT auth token"),
    db: AsyncSession = Depends(get_db),
):
    """Receive read status updates from device."""
    device = await get_current_device_from_token(token, db)

    updated = await apply_read_status(db, req.read_story_ids)

    await update_device_sync_time(db, device.device_id)

    return {"updated_stories": updated, "message": f"Updated {updated} stories as read"}


# ── Pairing Session (Web UI) ─────────────────────────────


@router.post("/pairing-session")
async def create_pairing_session():
    """Generate a 6-digit pairing code stored in Redis with 5-minute TTL.
    
    No device record is created — this is purely for the web UI to show
    a QR code + pairing code without polluting the devices table.
    """
    from app.services.device_service import generate_pairing_code

    redis_url = app_settings.REDIS_CONNECTION_URL or "redis://localhost:6379/0"
    r = Redis.from_url(redis_url, decode_responses=True)

    try:
        code = generate_pairing_code()
        server_url = str(app_settings.PUBLIC_URL or "http://localhost:8000").rstrip("/")

        session_data = json.dumps({
            "server_url": server_url,
            "pairing_code": code,
            "created_at": str(dt.now(UTC)),
        })
        await r.setex(f"hn_reader:pairing:{code}", 300, session_data)

        return {
            "pairing_code": code,
            "server_url": server_url,
        }
    finally:
        await r.aclose()


# ── QR Code ───────────────────────────────────────────────


@router.get("/qr-code")
async def get_pairing_qr_code(
    server_url: str = Query("", description="Server URL for pairing (auto-detected if empty)"),
    pairing_code: str = Query("", description="Optional pairing code to embed in QR"),
):
    """Generate a QR code for device pairing.

    Returns a base64-encoded PNG image of the QR code.
    The QR code contains JSON with server_url and optional pairing_code.
    """
    import base64

    # Use provided URL or fall back to PUBLIC_URL or build from localhost
    if not server_url:
        server_url = app_settings.PUBLIC_URL or "http://localhost:8000"

    # QR code data: JSON with server info
    qr_dict = {
        "server_url": str(server_url).rstrip("/"),
        "register_endpoint": "/api/devices/register",
        "version": "1.0",
    }
    if pairing_code:
        qr_dict["pairing_code"] = pairing_code
    qr_data = json.dumps(qr_dict)

    # Generate QR code
    qr = qrcode.QRCode(version=1, box_size=10, border=2)
    qr.add_data(qr_data)
    qr.make(fit=True)

    img = qr.make_image(fill_color="black", back_color="white")

    # Convert to base64 PNG
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    buf.seek(0)
    img_base64 = base64.b64encode(buf.getvalue()).decode()

    return {
        "qr_code_base64": f"data:image/png;base64,{img_base64}",
        "server_url": str(server_url).rstrip("/"),
    }


# ── WebSocket Endpoint ────────────────────────────────────


@router.websocket("/ws/{device_id}")
async def websocket_endpoint(
    websocket: WebSocket,
    device_id: str,
):
    """WebSocket endpoint for device real-time communication.

    Device connects with JWT token as query parameter: /ws/{device_id}?token=YOUR_TOKEN
    """
    # Authenticate
    device = await get_ws_device(websocket, device_id)
    if device is None:
        return  # get_ws_device already closed the connection with reason

    await ws_manager.connect(websocket, device_id)

    try:
        while True:
            data = await websocket.receive_text()
            try:
                msg = json.loads(data)
            except json.JSONDecodeError:
                # If not JSON, treat as keepalive ping
                await ws_manager.update_ping(device_id)
                continue

            msg_type = msg.get("type", "")

            if msg_type == "ping":
                await ws_manager.update_ping(device_id)
                await ws_manager.send_to_device(device_id, {"type": "pong"})

            elif msg_type == "read_status":
                # Handle read status via WS
                read_ids = msg.get("read_story_ids", [])
                if read_ids:
                    db = None
                    try:
                        from app.core.database import AsyncSessionLocal

                        db = AsyncSessionLocal()
                        await apply_read_status(db, read_ids)
                        await update_device_sync_time(db, device_id)
                    except Exception as e:
                        logger.warning("WS read_status error: %s", e)
                    finally:
                        if db:
                            await db.close()
                await ws_manager.send_to_device(
                    device_id,
                    {"type": "read_status_ack", "updated": len(read_ids)},
                )

            elif msg_type == "sync_request":
                # Device requests full sync
                await ws_manager.send_to_device(
                    device_id,
                    {
                        "type": "sync_trigger",
                        "message": "Sync recommended",
                        "timestamp": msg.get("timestamp", ""),
                    },
                )

    except WebSocketDisconnect:
        logger.info("WebSocket disconnected: device %s", device_id)
    except Exception as e:
        logger.error("WebSocket error for device %s: %s", device_id, e)
    finally:
        await ws_manager.disconnect(device_id)


# ── Disconnect (soft — keeps pairing info) ────────────────


@router.post("/{device_id}/disconnect")
async def disconnect_device(
    device_id: str,
    db: AsyncSession = Depends(get_db),
):
    """Soft disconnect — close WS but keep pairing info for reconnection."""
    device = await get_device_by_id(db, device_id)
    if device:
        device.is_connected = False
        await db.commit()

    await ws_manager.disconnect(device_id)

    return {"device_id": device_id, "message": "Device disconnected"}


@router.delete("/{device_id}")
async def delete_device(
    device_id: str,
    db: AsyncSession = Depends(get_db),
):
    """Delete a device record entirely (unpair and remove)."""
    device = await get_device_by_id(db, device_id)
    if not device:
        raise HTTPException(status_code=404, detail="Device not found")

    await ws_manager.disconnect(device_id)
    await db.delete(device)
    await db.commit()

    return {"device_id": device_id, "message": "Device deleted"}