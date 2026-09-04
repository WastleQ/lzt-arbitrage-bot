import asyncio
import time
from contextlib import asynccontextmanager


class AsyncRateLimiter:
    """Token bucket rate limiter для исходящих запросов."""

    def __init__(self, rate: float, burst: int) -> None:
        self._rate = max(rate, 0.01)
        self._capacity = max(burst, 1)
        self._tokens = float(self._capacity)
        self._last_refill = time.monotonic()
        self._lock = asyncio.Lock()

    async def acquire(self, tokens: float = 1.0) -> None:
        async with self._lock:
            while True:
                now = time.monotonic()
                elapsed = now - self._last_refill
                self._last_refill = now
                self._tokens = min(self._capacity, self._tokens + elapsed * self._rate)
                if self._tokens >= tokens:
                    self._tokens -= tokens
                    return
                deficit = tokens - self._tokens
                wait = deficit / self._rate
                await asyncio.sleep(wait)

    @asynccontextmanager
    async def throttle(self):
        await self.acquire()
        yield
