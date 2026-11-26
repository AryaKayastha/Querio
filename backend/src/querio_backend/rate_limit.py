import math
import threading
import time
from collections import deque

from fastapi import Request


def client_ip_from_request(request: Request) -> str:
    """Return the caller IP, preferring the first hop of X-Forwarded-For (used by Cloud Run)."""
    forwarded_for = request.headers.get("x-forwarded-for", "")
    if forwarded_for:
        first_hop = forwarded_for.split(",", 1)[0].strip()
        if first_hop:
            return first_hop
    if request.client and request.client.host:
        return request.client.host
    return "unknown"


class SlidingWindowRateLimiter:
    """Thread-safe in-memory sliding-window rate limiter keyed by client IP."""

    def __init__(self, max_requests: int, window_seconds: float = 60.0) -> None:
        self.max_requests = max_requests
        self.window_seconds = window_seconds
        self._hits: dict[str, deque[float]] = {}
        self._lock = threading.Lock()

    def reset(self) -> None:
        """Clear all recorded request timestamps."""
        with self._lock:
            self._hits.clear()

    def check(self, key: str, now: float | None = None) -> int | None:
        """Record a request if under limit; otherwise return Retry-After seconds."""
        if self.max_requests <= 0:
            return None

        current = time.monotonic() if now is None else now
        cutoff = current - self.window_seconds

        with self._lock:
            if len(self._hits) > 1000:
                stale_keys = [
                    k for k, q in self._hits.items()
                    if not q or q[-1] <= cutoff
                ]
                for stale_key in stale_keys:
                    del self._hits[stale_key]

            timestamps = self._hits.setdefault(key, deque())
            while timestamps and timestamps[0] <= cutoff:
                timestamps.popleft()

            if len(timestamps) >= self.max_requests:
                retry_after = math.ceil(timestamps[0] + self.window_seconds - current)
                return max(1, retry_after)

            timestamps.append(current)
            return None
