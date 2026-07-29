"""Pydantic schemas for device pairing and synchronization."""

from datetime import datetime

from pydantic import BaseModel


class DevicePairingRequest(BaseModel):
    """Request schema for device registration (pairing initiation)."""
    device_name: str
    device_id: str


class DevicePairingConfirm(BaseModel):
    """Request schema for pairing code confirmation."""
    device_id: str
    pairing_code: str


class DeviceAuthRequest(BaseModel):
    """Request schema for device authentication."""
    device_id: str
    auth_token: str


class DeviceDisconnectRequest(BaseModel):
    """Request schema for device disconnection."""
    device_id: str


class DeviceResetRequest(BaseModel):
    """Android client factory reset request — clears all local data, allows re-pairing."""
    device_id: str


class DeviceRevokeResponse(BaseModel):
    """Response schema when a device connection is revoked from web app."""
    device_id: str
    revoked: bool
    message: str


class SyncStatusRequest(BaseModel):
    """Request schema for syncing read status from device."""
    device_id: str
    last_synced_story_id: int | None = None
    read_story_ids: list[int] = []


class DeviceSettingsResponse(BaseModel):
    """Settings sent to the device during sync."""
    ui_language: str
    translation_language: str
    dark_mode: str  # "light", "dark", "system"


class DeviceInfoResponse(BaseModel):
    """Response schema for a single device (used in device list)."""
    id: int
    device_name: str
    device_id: str
    is_paired: bool
    is_connected: bool
    last_sync_at: datetime | None = None
    created_at: datetime

    class Config:
        from_attributes = True


class DeviceRegisterResponse(BaseModel):
    """Response schema after device registration."""
    device_id: str
    pairing_code: str  # Only returned on registration, never stored as plaintext
    message: str


class DevicePairingResponse(BaseModel):
    """Response schema after successful pairing."""
    device_id: str
    auth_token: str
    device_name: str
    message: str