"""Telegram notification service for sending messages via Bot API.

Supports i18n: messages are read from locale JSON files (app/static/locales/{lang}/common.json)
based on the user's UI language preference. Falls back to English if language is not found.
"""

import json
import logging
import os
from pathlib import Path
from typing import Optional

import httpx

from app.core.config import settings as app_settings

logger = logging.getLogger(__name__)

# Locale dosyalarının konumu: çalışma dizini (WORKDIR) altındaki app/static/locales
# Docker'da WORKDIR=/app → /app/static/locales
# Yerelde proje kökü → C:/.../hn-reader/static/locales
# İkinci seçenek olarak LOCALE_DIR env var veya __file__ tabanlı fallback
_cwd = Path(os.getcwd())
# Docker'da WORKDIR=/app → /app/static/locales
# Yerelde proje kökü → C:/.../hn-reader/app/static/locales veya C:/.../hn-reader/static/locales
for _candidate in [
    _cwd / "static" / "locales",                      # Docker: /app/static/locales
    _cwd / "app" / "static" / "locales",              # Yerel: proje/app/static/locales
    Path(__file__).resolve().parent.parent / "static" / "locales",  # site-packages
]:
    if _candidate.exists():
        _LOCALE_DIR = _candidate
        break
else:
    _LOCALE_DIR = _cwd / "static" / "locales"  # fallback


def _get_locale_message(key: str, language_code: str, **kwargs) -> str:
    """Locale JSON'dan mesajı okur, yoksa İngilizce fallback.

    Args:
        key: Mesaj anahtarı (örn. "new_stories")
        language_code: Dil kodu (örn. "tr", "en", "de")
        **kwargs: format() için parametreler

    Returns:
        Formatlanmış mesaj metni
    """
    # Önce istenen dilde dene
    locale_path = _LOCALE_DIR / language_code / "common.json"
    try:
        with open(locale_path, "r", encoding="utf-8") as f:
            data = json.load(f)
        notification = data.get("telegram", {}).get("notification", {})
        template = notification.get(key)
        print(f"[Locale] _get_locale_message(lang={language_code}, key={key}): template={'FOUND' if template else 'MISSING'}, notification keys={list(notification.keys())}")
        if template:
            return template.format(**kwargs)
    except (FileNotFoundError, json.JSONDecodeError) as e:
        logger.warning(f"Locale file not found/readable for '{language_code}': {e}")

    # Fallback: İngilizce
    fallback_path = _LOCALE_DIR / "en" / "common.json"
    try:
        with open(fallback_path, "r", encoding="utf-8") as f:
            data = json.load(f)
        template = data.get("telegram", {}).get("notification", {}).get(key, "")
        return template.format(**kwargs)
    except (FileNotFoundError, json.JSONDecodeError) as e:
        logger.warning(f"Fallback locale (en) also failed: {e}")
        # Hardcoded fallback (son çare)
        fallbacks = {
            "new_stories": "📰 <b>{count} new stories</b> summarized on Hacker News and ready to read!",
            "check_link": "🔗 <a href=\"{url}\">Check them out</a>",
            "no_stories": "🫡 No new stories on Hacker News today. See you at the next scan!",
            "errors": "⚠️ <b>{count} errors</b> occurred.",
        }
        return fallbacks.get(key, "").format(**kwargs)


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
        self, new_count: int, settings_obj, error_count: int = 0,
        language_code: str = "en",
    ) -> bool:
        """Send a notification about new processed stories.

        Message is read from locale JSON files based on language_code.
        Falls back to English if the language or key is not found.

        Args:
            new_count: Number of newly processed stories.
            settings_obj: Setting model instance (must have telegram_chat_id).
            error_count: Number of errors encountered during processing.
            language_code: User's UI language code (e.g. "tr", "en", "de").

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

        text = _get_locale_message("new_stories", language_code, count=new_count)
        text += "\n\n"
        text += _get_locale_message("check_link", language_code, url=public_url)

        if error_count > 0:
            text += "\n\n"
            text += _get_locale_message("errors", language_code, count=error_count)

        return await self.send_message(chat_id, text)

    async def send_empty_notification(
        self, settings_obj, language_code: str = "en"
    ) -> bool:
        """Send a notification when there are no new stories.

        Message is read from locale JSON files based on language_code.

        Args:
            settings_obj: Setting model instance (must have telegram_chat_id).
            language_code: User's UI language code (e.g. "tr", "en", "de").

        Returns:
            True if sent successfully, False otherwise.
        """
        if not settings_obj.telegram_enabled:
            return False

        chat_id = settings_obj.telegram_chat_id
        if not chat_id:
            logger.warning("Telegram chat_id not configured")
            return False

        text = _get_locale_message("no_stories", language_code)

        return await self.send_message(chat_id, text)