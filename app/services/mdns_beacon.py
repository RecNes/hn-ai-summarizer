"""mDNS beacon: Zeroconf ile ağda 'ben buradayım' yayını yapar.

Android client'ın hn-reader sunucusunu otomatik bulmasını sağlar.
Servis tipi: _hnreader._tcp
"""

import asyncio
import logging
import socket

from app.core.config import settings as app_settings

logger = logging.getLogger(__name__)

SERVICE_TYPE = "_hnreader._tcp.local."
SERVICE_NAME = "HN Reader"


async def start_mdns_beacon():
    """Start mDNS beacon advertisement for device discovery."""

    try:
        from zeroconf import IPVersion, ServiceInfo
        from zeroconf.asyncio import AsyncZeroconf
    except ImportError:
        logger.warning("zeroconf not installed — mDNS beacon disabled")
        return

    # Determine server port and IP
    port = 8000
    server_url = str(app_settings.PUBLIC_URL or "http://localhost:8000")
    if ":" in server_url.replace("://", "").split("/")[0]:
        try:
            port = int(server_url.rsplit(":", 1)[1].split("/")[0])
        except (ValueError, IndexError):
            port = 8000

    # Get local IP address
    local_ip = _get_local_ip()

    # Build TXT record with server info
    props = {
        "server_url": server_url,
        "version": app_settings.PROJECT_VERSION or "0.0.0",
        "path": "/api/devices/register",
    }

    info = ServiceInfo(
        SERVICE_TYPE,
        f"{SERVICE_NAME}.{SERVICE_TYPE}",
        addresses=[socket.inet_aton(local_ip)],
        port=port,
        properties=props,
    )

    aiozc = AsyncZeroconf(ip_version=IPVersion.V4Only)

    try:
        await aiozc.async_register_service(info, allow_name_change=True)
        logger.info(
            "[mDNS] Beacon started — %s:%d (%s)", local_ip, port, SERVICE_TYPE
        )

        # Keep running forever
        while True:
            await asyncio.sleep(3600)

    except asyncio.CancelledError:
        logger.info("[mDNS] Beacon stopped")
    except Exception as e:
        logger.warning("[mDNS] Beacon error: %s", e)
    finally:
        await aiozc.async_close()


def _get_local_ip() -> str:
    """Get the local network IP address."""
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except Exception:
        return "127.0.0.1"