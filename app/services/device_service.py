"""Device pairing, token management, and sync business logic."""

import hashlib
import logging
import secrets
from datetime import UTC, datetime, timedelta

import jwt
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from app.core.config import settings
from app.models.device import Device

logger = logging.getLogger(__name__)


def generate_pairing_code() -> str:
    """Generate a 6-digit random pairing code."""
    return str(secrets.randbelow(900000) + 100000)


def _hash_pairing_code(code: str) -> str:
    """SHA256 hash a pairing code for secure storage."""
    return hashlib.sha256(code.encode()).hexdigest()


def generate_device_token(device_id: str, secret_key: str | None = None) -> str:
    """Generate a JWT token for device authentication (24 hour TTL)."""
    key = secret_key or settings.SECRET_KEY
    payload = {
        "device_id": device_id,
        "iat": datetime.now(UTC),
        "exp": datetime.now(UTC) + timedelta(hours=24),
    }
    return jwt.encode(payload, key, algorithm="HS256")


def verify_device_token(token: str, secret_key: str | None = None) -> dict | None:
    """Verify a JWT device token. Returns payload dict or None if invalid."""
    key = secret_key or settings.SECRET_KEY
    try:
        payload = jwt.decode(token, key, algorithms=["HS256"])
        return payload
    except jwt.ExpiredSignatureError:
        logger.warning("Device token expired")
        return None
    except jwt.InvalidTokenError as e:
        logger.warning("Invalid device token: %s", e)
        return None


async def create_device(
    db: AsyncSession, device_name: str, device_id: str, device_type: str = "android"
) -> Device:
    """Create a new device record with a pairing code."""
    pairing_code = generate_pairing_code()

    device = Device(
        device_name=device_name,
        device_id=device_id,
        device_type=device_type,
        pairing_code=_hash_pairing_code(pairing_code),
        is_paired=False,
    )
    db.add(device)
    await db.commit()
    await db.refresh(device)

    # Store the plaintext pairing code temporarily on the object for response
    device._plaintext_pairing_code = pairing_code  # type: ignore
    return device


async def confirm_pairing(
    db: AsyncSession, device_id: str, pairing_code: str
) -> dict | None:
    """Confirm pairing code and generate auth token. Returns dict with auth_token or None."""
    result = await db.execute(select(Device).where(Device.device_id == device_id))
    device = result.scalar_one_or_none()

    if not device:
        logger.warning("Pairing confirm: device %s not found", device_id)
        return None

    if device.is_paired:
        # Device already paired — check if the code is valid and re-issue token
        hashed = _hash_pairing_code(pairing_code)
        if device.pairing_code == hashed:
            token = generate_device_token(device_id)
            device.auth_token = token
            await db.commit()
            return {
                "device_id": device_id,
                "auth_token": token,
                "device_name": device.device_name,
                "message": "Re-paired successfully",
            }
        logger.warning("Pairing confirm: wrong code for already-paired device %s", device_id)
        return None

    hashed = _hash_pairing_code(pairing_code)
    if device.pairing_code != hashed:
        logger.warning("Pairing confirm: wrong code for device %s", device_id)
        return None

    # Pairing successful — generate token
    token = generate_device_token(device_id)
    device.auth_token = token
    device.is_paired = True
    await db.commit()

    return {
        "device_id": device_id,
        "auth_token": token,
        "device_name": device.device_name,
        "message": "Device paired successfully",
    }


async def get_paired_devices(db: AsyncSession) -> list[Device]:
    """Get all paired devices for the web UI device management panel."""
    result = await db.execute(
        select(Device).where(Device.is_paired.is_(True)).order_by(Device.created_at.desc())
    )
    return list(result.scalars().all())


async def get_device_by_id(db: AsyncSession, device_id: str) -> Device | None:
    """Find a device by its unique device_id."""
    result = await db.execute(select(Device).where(Device.device_id == device_id))
    return result.scalar_one_or_none()


async def get_device_by_token(db: AsyncSession, token: str) -> Device | None:
    """Find a device by auth token. Verifies JWT first."""
    payload = verify_device_token(token)
    if not payload:
        return None
    return await get_device_by_id(db, payload["device_id"])


async def revoke_device(db: AsyncSession, device_id: str) -> dict:
    """Revoke a device connection from web app — invalidate token, reset pairing.

    The active WS connection will be closed by the caller (ws_manager).
    """
    device = await get_device_by_id(db, device_id)
    if not device:
        return {"device_id": device_id, "revoked": False, "message": "Device not found"}

    device.auth_token = None
    device.is_paired = False
    device.is_connected = False
    await db.commit()

    logger.info("Device %s (%s) revoked from web app", device.device_name, device_id)
    return {
        "device_id": device_id,
        "revoked": True,
        "message": f"Device '{device.device_name}' connection revoked",
    }


async def reset_device(db: AsyncSession, device_id: str) -> dict:
    """Factory reset from Android client — clear all pairing data, allow re-pairing."""
    device = await get_device_by_id(db, device_id)
    if not device:
        # Device not found — already clean, return success
        return {
            "device_id": device_id,
            "revoked": True,
            "message": "Device reset complete (not found on server, may already be cleaned)",
        }

    device.auth_token = None
    device.is_paired = False
    device.is_connected = False
    device.pairing_code = None
    await db.commit()

    logger.info("Device %s (%s) factory reset complete", device.device_name, device_id)
    return {
        "device_id": device_id,
        "revoked": True,
        "message": f"Device '{device.device_name}' reset complete",
    }


async def update_device_sync_time(db: AsyncSession, device_id: str) -> None:
    """Update last_sync_at timestamp for a device."""
    device = await get_device_by_id(db, device_id)
    if device:
        device.last_sync_at = datetime.now(UTC)
        await db.commit()


async def update_device_connection(
    db: AsyncSession, device_id: str, is_connected: bool
) -> None:
    """Update is_connected status for a device."""
    device = await get_device_by_id(db, device_id)
    if device:
        device.is_connected = is_connected
        await db.commit()


async def apply_read_status(db: AsyncSession, read_story_ids: list[int]) -> int:
    """Apply read status from Android client to stories. Returns count of updated stories."""
    if not read_story_ids:
        return 0

    from app.models.story import Story
    from sqlalchemy import update

    stmt = (
        update(Story)
        .where(Story.id.in_(read_story_ids))
        .values(is_read=True)
    )
    result = await db.execute(stmt)
    await db.commit()
    return result.rowcount  # type: ignore