"""Global rate limiter for AI service calls."""

import asyncio
import logging
from datetime import datetime, timezone

logger = logging.getLogger(__name__)


class GlobalRateLimit:
    """Global rate limiter for AI service calls.

    Detects 429 responses, imposes a cooldown window, and gradually shrinks
    the inter-request delay on successful calls.  All AIService instances
    share this single instance so that every provider call observes the
    same back-off state.
    """

    MIN_DELAY: float = 0.05    # 50 ms — fast path once proven stable
    MAX_DELAY: float = 10.0    # 10 s  — deep back-off
    SAFE_DELAY: float = 2.0    # delay when recovering from a 429
    DECAY: float = 0.9         # multiply delay by this on each success

    def __init__(self):
        self._inter_request_delay: float = self.MIN_DELAY
        self._limited_until: float = 0.0  # monotonic clock timestamp
        self._remaining_seconds: float = 0.0

    # ── public API ──────────────────────────────────────────────────

    @property
    def inter_request_delay(self) -> float:
        return self._inter_request_delay

    @property
    def remaining_seconds(self) -> float:
        remaining = self._limited_until - asyncio.get_event_loop().time()
        return max(0.0, remaining)

    def parse_reset_seconds(self, err_body: dict) -> float:
        """Try to extract the retry-after / reset timestamp from an error body.

        Checks multiple common fields in order of preference.
        """
        now = asyncio.get_event_loop().time()

        # Retry-After header (seconds)
        retry_after = err_body.get("Retry-After") or err_body.get("retry-after")
        if retry_after is not None:
            try:
                return float(retry_after)
            except (ValueError, TypeError):
                pass

        # OpenAI-style: error.code == "rate_limit_exceeded" with a message
        # e.g. "Rate limit exceeded for … (Please retry after X seconds.)"
        msg = err_body.get("message", "") or err_body.get("error", {}).get("message", "")
        import re
        match = re.search(r"retry\s+after\s+(\d+)", msg, re.IGNORECASE)
        if match:
            return float(match.group(1))

        # Anthropic-style: headers contain retry-after-ms as int
        headers = err_body.get("headers", {})
        retry_after_ms = headers.get("retry-after-ms") or headers.get("x-ratelimit-reset-requests")
        if retry_after_ms is not None:
            try:
                return float(retry_after_ms) / 1000.0
            except (ValueError, TypeError):
                pass

        # Fallback: reset based on the rate limit window (e.g. 60s)
        return 60.0

    def set_limited(self, wait_seconds: float) -> None:
        """Enter rate-limit cooldown mode.

        Args:
            wait_seconds: Number of seconds to wait before retrying.
        """
        now = asyncio.get_event_loop().time()
        self._limited_until = now + wait_seconds
        self._remaining_seconds = wait_seconds
        self._inter_request_delay = self.SAFE_DELAY
        logger.warning(
            "[RateLimit] 429 received – pinned safe delay at %.1fs for %.0fs",
            self.SAFE_DELAY, wait_seconds,
        )

    def on_success(self) -> None:
        """Called after a successful API call – gradually shrink delay."""
        if self._inter_request_delay > self.MIN_DELAY:
            self._inter_request_delay = max(
                self.MIN_DELAY, self._inter_request_delay * self.DECAY,
            )
            logger.info(
                "[RateLimit] Window expired – pinned inter-request delay "
                "decayed to %.3fs",
                self._inter_request_delay,
            )

    async def wait_if_limited(self) -> None:
        """If we are in a rate-limit cooldown, wait until the window expires."""
        wait = self.remaining_seconds
        if wait > 0:
            logger.info(
                "[RateLimit] Holding off for %.1fs (reset in %.0fs)...",
                wait, wait,
            )
            await asyncio.sleep(wait)


GLOBAL_RATE_LIMIT = GlobalRateLimit()