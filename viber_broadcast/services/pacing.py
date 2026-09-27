"""Pacing service — jittered delay plus a sliding-window burst cap."""

from __future__ import annotations

import asyncio
import random
import time
from collections import deque


class PacingService:
    """Two-layer throttle.

    Layer 1: per-send jittered delay in [min_delay_s, max_delay_s].
    Layer 2: sliding window — no more than `burst_cap` sends per `burst_window_s`.
    """

    def __init__(
        self,
        min_delay_s: float,
        max_delay_s: float,
        burst_window_s: float,
        burst_cap: int,
    ) -> None:
        if min_delay_s < 0 or max_delay_s < min_delay_s:
            raise ValueError("invalid delay bounds")
        self._min = min_delay_s
        self._max = max_delay_s
        self._window = burst_window_s
        self._cap = burst_cap
        self._lock = asyncio.Lock()
        self._recent: deque[float] = deque()
        self._last_send: float = 0.0

    async def acquire(self, account_id: str) -> None:
        async with self._lock:
            now = time.monotonic()
            # Layer 1: inter-send jitter.
            since_last = now - self._last_send
            target_gap = random.uniform(self._min, self._max)
            if since_last < target_gap:
                await asyncio.sleep(target_gap - since_last)

            # Layer 2: sliding window.
            while True:
                now = time.monotonic()
                while self._recent and now - self._recent[0] > self._window:
                    self._recent.popleft()
                if len(self._recent) < self._cap:
                    break
                wait = self._window - (now - self._recent[0]) + 0.05
                await asyncio.sleep(max(wait, 0.05))
            self._recent.append(time.monotonic())
            self._last_send = time.monotonic()