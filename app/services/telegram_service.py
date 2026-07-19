"""Telegram notification service for sending messages via Bot API."""

import logging
from typing import Optional

import httpx

from app.core.config import settings as app_settings

logger = logging.getLogger(__name__)


class TelegramNotConfiguredError(Exception):
    """Raised when Telegram bot token or chat ID is not configured."""


class TelegramService:
    """Service for sending notifications via Telegram Bot API."""

    BASE_API_URL = "https://api.telegram.org/bot{bot_token}/"

    def __init__(self, bot_token: str):
        if not bot_token:
            raise TelegramNotConfiguredError("Bot token is empty")
        self.api_url = self.BASE_API_URL.format(bot_token=bot_token)

    async def send_message(
        self,
        chat_id: str,
        text: str,
        parse_mode: str = "HTML",
    ) -> bool:
        """Send a text message to a Telegram chat.

        Args:
            chat_id: Target chat ID (numeric string).
            text: Message text, supports HTML formatting.
            parse_mode: 'HTML' or 'MarkdownV2'.

        Returns:
            True if message was sent successfully, False otherwise.
        """
        if not chat_id:
            logger.warning("Cannot send Telegram message: chat_id is empty")
            return False

        url = f"{self.api_url}sendMessage"
        payload = {
            "chat_id": chat_id,
            "text": text,
            "parse_mode": parse_mode,
        }

        try:
            async with httpx.AsyncClient(timeout=15) as client:
                response = await client.post(url, json=payload)
                result = response.json()

                if response.status_code == 200 and result.get("ok"):
                    logger.info(f"Telegram message sent to chat {chat_id}")
                    return True
                else:
                    logger.error(
                        f"Telegram API error (HTTP {response.status_code}): "
                        f"{result.get('description', 'unknown')}"
                    )
                    return False
        except httpx.TimeoutException:
            logger.error("Telegram API request timed out")
            return False
        except httpx.RequestError as e:
            logger.error(f"Telegram API request failed: {e}")
            return False

    async def send_notification(
        self, new_count: int, settings_obj, error_count: int = 0
    ) -> bool:
        """Send a notification about new processed stories.

        Message format (English):
        "📰 Hacker News'te {new_count} yeni konu özetlendi ve okunmaya hazır!"

        Falls back to API's chat_id if settings_obj.telegram_chat_id is not set.

        Args:
            new_count: Number of newly processed stories.
            settings_obj: Setting model instance (must have telegram_chat_id).
            error_count: Number of errors encountered during processing.

        Returns:
            True if sent successfully, False otherwise.
        """
        if not settings_obj.telegram_enabled:
            return False

        chat_id = settings_obj.telegram_chat_id
        if not chat_id:
            logger.warning("Telegram chat_id not configured")
            return False

        public_url = app_settings.PUBLIC_URL or "http://localhost:8000"
        text = (
            f"\U0001F4F0 Hacker News'te <b>{new_count} yeni konu</b> özetlendi "
            f"ve okunmaya haz\u0131r!\n\n"
            f"\U0001F517 <a href=\"{public_url}\">Hemen göz at</a>"
        )

        if error_count > 0:
            text += (
                f"\n\n\u26A0\uFE0F <b>{error_count} hata</b> olu\u015Ftu."
            )

        return await self.send_message(chat_id, text)

    async def send_empty_notification(self, settings_obj) -> bool:
        """Send a notification when there are no new stories.

        Message format:
        "🫡 Bugün Hacker News'te yeni bir konu yok. Bir sonraki taramada görüşmek üzere!"

        Args:
            settings_obj: Setting model instance (must have telegram_chat_id).

        Returns:
            True if sent successfully, False otherwise.
        """
        if not settings_obj.telegram_enabled:
            return False

        chat_id = settings_obj.telegram_chat_id
        if not chat_id:
            logger.warning("Telegram chat_id not configured")
            return False

        text = (
            "\U0001FAE1 Bug\xfcn Hacker News'te yeni bir konu yok. "
            "Bir sonraki taramada g\xf6r\xfc\u015fmek \xfczere!"
        )

        return await self.send_message(chat_id, text)