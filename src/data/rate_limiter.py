"""Sliding-window rate limiter for Tushare API calls."""

from __future__ import annotations

import threading
import time
from collections import deque


class RateLimiter:
    """Thread-safe sliding window rate limiter.

    Blocks the caller until a call slot is available within the window.
    """

    def __init__(self, max_calls: int = 200, window_seconds: int = 60) -> None:
        self._max_calls = max_calls
        self._window = window_seconds
        self._timestamps: deque[float] = deque()
        self._lock = threading.Lock()

    def acquire(self) -> None:
        """Block until a call slot is available."""
        while True:
            with self._lock:
                now = time.time()
                # Evict timestamps outside the sliding window
                while self._timestamps and self._timestamps[0] <= now - self._window:
                    self._timestamps.popleft()

                if len(self._timestamps) < self._max_calls:
                    self._timestamps.append(now)
                    return

                # Must wait until the oldest slot expires
                wait_until = self._timestamps[0] + self._window

            sleep_time = wait_until - time.time()
            if sleep_time > 0:
                time.sleep(sleep_time + 0.05)
