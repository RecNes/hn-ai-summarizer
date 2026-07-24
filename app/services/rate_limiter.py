"""Global rate-limit state for AI provider calls.

Adaptive inter-request delay:

- After each successful request, the delay is reduced by ALPHA (10%).
  Minimum floor: MIN_DELAY seconds.
- When a 429 is received, the delay at which we were running successfully
  is pinned as ``_safe_delay``. Once the reset window expires, the delay
  is set to ``_safe_delay`` and stays there (no further reduction).

This lets the system find the optimal request rate for the current
provider/model without hammering the API.
"""

import asyncio
import time
from dataclasses import dataclass, field

# ── Tunable constants ──────────────────────────
ALPHA = 0.10          # fractional reduction per successful call
MIN_DELAY = 1.5       # minimum inter-request delay (seconds)
INITIAL_DELAY = 16.0  # starting delay after a 429


@dataclass
class RateLimitState:
    """Provider-agnostic rate-limit state, shared across all AIService instances.

    When a 429 is received, ``until`` is set to the absolute timestamp (seconds)
    from X-RateLimit-Reset or from a parsed error body.  All callers wait until
    that timestamp passes before making the next request.

    Additionally, an adaptive ``_inter_request_delay`` is maintained so that
    even outside a rate-limit window, calls are spaced by a dynamically-
    discovered safe interval.
    """

    # ── Rate-limit window ──────────────────────
    until: float = 0.0        # monotonic timestamp until which we must wait
    _event: asyncio.Event = field(default_factory=asyncio.Event)

    # ── Adaptive inter-request delay ───────────
    _inter_request_delay: float = INITIAL_DELAY
    _safe_delay: float | None = None   # pinned after a 429
    _pinned: bool = False              # True once a 429 has been seen

    def __post_init__(self):
        self._event.set()

    # ── Rate-limit window API ──────────────────

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
        if new_until > self.until:
            self.until = new_until
        self._event.clear()

        # Pin the current delay as the safe level – this is the speed we
        # were running at before hitting the limit.
        current = self._inter_request_delay if not self._pinned else (self._safe_delay or MIN_DELAY)
        if self._safe_delay is None or current < self._safe_delay:
            self._safe_delay = current
        self._pinned = True

        print(
            f"[RateLimit] 429 received – pinned safe delay at "
            f"{self._safe_delay:.2f}s. Current delay: {self._inter_request_delay:.2f}s. "
            f"Waiting {seconds_from_now:.0f}s."
        )

        asyncio.get_event_loop().call_later(seconds_from_now, self._release)

    def _release(self):
        """Re-open the gate and lock the safe delay."""
        self.until = 0.0
        self._event.set()

        # ── After 429 → pin to the safe delay ──
        if self._pinned and self._safe_delay is not None:
            self._inter_request_delay = self._safe_delay
            print(
                f"[RateLimit] Window expired – pinned inter-request delay "
                f"at {self._inter_request_delay:.2f}s (safe level)."
            )

    async def wait_if_limited(self):
        """Block the current coroutine until the rate-lift window passes."""
        if self.is_limited:
            wait = self.remaining_seconds
            print(f"[RateLimit] Holding off for {wait:.1f}s (reset in {wait:.0f}s)...")
            await asyncio.sleep(wait)

    # ── Adaptive delay API ─────────────────────

    @property
    def inter_request_delay(self) -> float:
        """Current adaptive delay applied between every call."""
        return self._inter_request_delay

    def on_success(self):
        """Called after every successful API call.

        Reduces the inter-request delay by ALPHA (10%), but never below
        MIN_DELAY.  If we have been pinned after a 429, do NOT reduce
        further – we stay at the safe level.
        """
        if self._pinned:
            return  # stay at the safe delay, don't try to speed up

        new = self._inter_request_delay * (1.0 - ALPHA)
        self._inter_request_delay = max(new, MIN_DELAY)

    # ── Helper ─────────────────────────────────

    @staticmethod
    def parse_reset_seconds(error_body: dict, default: float = 60.0) -> float:
        """Try to extract the reset-window duration from a 429 error payload.

        Strategy (in order):
          1. ``X-RateLimit-Reset`` in metadata headers (OpenRouter – ms timestamp).
          2. ``Retry-After`` header value.
          3. ``rate_limit.reset`` in metadata (ms timestamp).
          4. Fall back to ``default`` seconds.
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