"""Global rate-limit state for AI provider calls.

OpenRouter (ve diğer provider'lar) 429 RateLimitError döndüğünde,
X-RateLimit-Reset timestamp'ini parse edip bu state'e yazar.
Tüm AIService instance'ları istek öncesi bu state'i kontrol eder.
"""

import asyncio
import time
from dataclasses import dataclass, field
from typing import Optional


@dataclass
class RateLimitState:
    """Provider-agnostic rate-limit state, shared across all AIService instances.

    When a 429 is received, ``until`` is set to the absolute timestamp (seconds)
    from X-RateLimit-Reset or from a parsed error body.  All callers wait until
    that timestamp passes before making the next request.
    """

    until: float = 0.0        # monotonic timestamp until which we must wait
    _event: asyncio.Event = field(default_factory=asyncio.Event)

    def __post_init__(self):
        self._event.set()  # initially unlocked

    @property
    def is_limited(self) -> bool:
        """True if a rate limit is currently active."""
        return time.monotonic() < self.until

    @property
    def remaining_seconds(self) -> float:
        """Seconds until the rate-lift window expires (0 if not limited)."""
        if self.is_limited:
            return self.until - time.monotonic()
        return 0.0

    def set_limited(self, seconds_from_now: float):
        """Activate rate-limit for the given duration.

        Args:
            seconds_from_now: How many seconds to wait before allowing
                              the next request.
        """
        new_until = time.monotonic() + seconds_from_now
        # Only extend – never shrink – the deadline
        if new_until > self.until:
            self.until = new_until
        self._event.clear()
        # Schedule the wake-up
        asyncio.get_event_loop().call_later(seconds_from_now, self._release)

    def _release(self):
        """Re-open the gate."""
        self.until = 0.0
        self._event.set()

    async def wait_if_limited(self):
        """Block the current coroutine until the rate-lift window passes."""
        if self.is_limited:
            wait = self.remaining_seconds
            print(f"[RateLimit] Holding off for {wait:.1f}s (reset in {wait:.0f}s)...")
            await asyncio.sleep(wait)

    # ── helpers ────────────────────────────────────────────────

    @staticmethod
    def parse_reset_seconds(error_body: dict, default: float = 60.0) -> float:
        """Try to extract the reset-window duration from a 429 error payload.

        Strategy (in order):
          1. ``X-RateLimit-Reset`` in metadata headers (OpenRouter – ms timestamp).
          2. ``Retry-After`` header value.
          3. ``rate_limit.reset`` in metadata (ms timestamp).
          4. Fall back to ``default`` seconds.

        Returns seconds-from-now to wait.
        """
        now_ms = time.time() * 1000
        metadata: dict = error_body.get("metadata", {}) or {}

        # 1 – metadata.headers.X-RateLimit-Reset (ms epoch)
        try:
            headers = metadata.get("headers", {}) or {}
            reset_str = headers.get("X-RateLimit-Reset", "") or ""
            if reset_str:
                reset_ms = int(reset_str)
                if reset_ms > now_ms:
                    return (reset_ms - now_ms) / 1000.0
        except (ValueError, TypeError):
            pass

        # 2 – metadata.rate_limit.reset (ms epoch)
        try:
            rl = metadata.get("rate_limit", {}) or {}
            reset_ms = int(rl.get("reset", 0))
            if reset_ms > now_ms:
                return (reset_ms - now_ms) / 1000.0
        except (ValueError, TypeError):
            pass

        # 3 – free-models-per-min / requests-per-min hint
        msg = (error_body.get("message", "") or "").lower()
        if "per-min" in msg or "per_min" in msg:
            return 60.0

        return default


# Singleton – tüm AIService instance'ları bunu paylaşır
GLOBAL_RATE_LIMIT = RateLimitState()