"""
API Key Manager with round-robin rotation and automatic fallback on rate-limit errors.

Supports multiple Google Gemini API keys to work around the 60 req/min free-tier limit.
"""
import asyncio
import time
from typing import List, Optional
from loguru import logger


class ApiKeyManager:
    """
    Round-robin key rotation with per-key cooldown on 429 / quota errors.

    Usage:
        manager = ApiKeyManager(keys)
        key = manager.next_key()
        # on rate-limit error:
        manager.mark_exhausted(key)
    """

    # How long (seconds) to put a key on cooldown after a 429 error
    COOLDOWN_SECONDS = 65

    def __init__(self, keys: List[str]) -> None:
        if not keys:
            raise ValueError("At least one API key must be provided")

        self._keys = list(keys)
        self._index = 0
        self._lock = asyncio.Lock()
        # Maps key → timestamp when it may be used again (0 = available now)
        self._cooldown_until: dict[str, float] = {k: 0.0 for k in self._keys}

        logger.info(f"ApiKeyManager initialised with {len(self._keys)} key(s)")

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def next_key(self) -> str:
        """Return the next available API key (synchronous, thread-safe)."""
        now = time.monotonic()
        n = len(self._keys)

        for _ in range(n):
            candidate = self._keys[self._index % n]
            self._index = (self._index + 1) % n

            if self._cooldown_until[candidate] <= now:
                return candidate

        # All keys are on cooldown — return the one that recovers soonest
        soonest = min(self._keys, key=lambda k: self._cooldown_until[k])
        wait = max(0.0, self._cooldown_until[soonest] - now)
        if wait > 0:
            logger.warning(
                f"All {n} API key(s) exhausted. Waiting {wait:.1f}s for key rotation..."
            )
            time.sleep(wait)
        return soonest

    async def next_key_async(self) -> str:
        """Async-safe version of next_key()."""
        async with self._lock:
            now = time.monotonic()
            n = len(self._keys)

            for _ in range(n):
                candidate = self._keys[self._index % n]
                self._index = (self._index + 1) % n

                if self._cooldown_until[candidate] <= now:
                    return candidate

            soonest = min(self._keys, key=lambda k: self._cooldown_until[k])
            wait = max(0.0, self._cooldown_until[soonest] - now)
            if wait > 0:
                logger.warning(
                    f"All {n} API key(s) exhausted. Sleeping {wait:.1f}s..."
                )
            return soonest

    def mark_exhausted(self, key: str, cooldown: Optional[float] = None) -> None:
        """
        Mark a key as rate-limited. It will not be selected again until
        the cooldown period expires.
        """
        seconds = cooldown if cooldown is not None else self.COOLDOWN_SECONDS
        self._cooldown_until[key] = time.monotonic() + seconds
        available = self._available_count()
        logger.warning(
            f"API key ...{key[-6:]} marked exhausted for {seconds}s. "
            f"{available}/{len(self._keys)} key(s) still available."
        )

    def is_rate_limit_error(self, exc: Exception) -> bool:
        """Heuristic: detect quota / rate-limit errors from Gemini SDK."""
        msg = str(exc).lower()
        indicators = [
            "429",
            "quota",
            "rate limit",
            "rate_limit",
            "resource exhausted",
            "resourceexhausted",
            "too many requests",
        ]
        return any(i in msg for i in indicators)

    def key_count(self) -> int:
        return len(self._keys)

    def available_count(self) -> int:
        return self._available_count()

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _available_count(self) -> int:
        now = time.monotonic()
        return sum(1 for k in self._keys if self._cooldown_until[k] <= now)
