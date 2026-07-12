import asyncio
import time
from collections import deque
from Chunking.core.settings import ChunkingSettings


class RateLimiter:
    def __init__(self, token_budget_per_minute: int | None = None, safety_factor: float | None = None):
        settings = ChunkingSettings()
        self.available_budget = int((token_budget_per_minute or settings.token_budget_per_minute) * (safety_factor or settings.rate_limit_safety_factor))
        self._events = deque()
        self._lock = asyncio.Lock()

    async def acquire_tokens(self, estimated_tokens: int):
        estimated = max(1, int(estimated_tokens or 1))
        while True:
            async with self._lock:
                now = time.monotonic()
                self._drop_expired(now)
                used = sum(tokens for _timestamp, tokens in self._events)
                if used + estimated <= self.available_budget:
                    self._events.append((now, estimated))
                    return
                wait_for = 60 - (now - self._events[0][0]) if self._events else 1
            await asyncio.sleep(max(0.1, wait_for))

    def _drop_expired(self, now: float):
        while self._events and now - self._events[0][0] >= 60:
            self._events.popleft()
