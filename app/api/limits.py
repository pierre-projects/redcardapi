"""In-memory PDF cache and per-client rate limit.

Both are per process, which suits a single instance. For several instances,
put a CDN in front (PDF responses are cacheable) or use a shared limiter.
"""

import threading
import time
from collections import OrderedDict, deque
from collections.abc import Hashable

from ..exceptions import RateLimitedError

CachedPdf = tuple[bytes, str]  # (content, filename)


class PdfCache:
    """Least-recently-used cache of rendered PDFs."""

    def __init__(self, max_entries: int):
        self.max_entries = max_entries
        self._entries: OrderedDict[Hashable, CachedPdf] = OrderedDict()
        self._lock = threading.Lock()

    def get(self, key: Hashable) -> CachedPdf | None:
        with self._lock:
            hit = self._entries.get(key)
            if hit is not None:
                self._entries.move_to_end(key)
            return hit

    def put(self, key: Hashable, value: CachedPdf) -> None:
        if self.max_entries <= 0:
            return
        with self._lock:
            self._entries[key] = value
            self._entries.move_to_end(key)
            while len(self._entries) > self.max_entries:
                self._entries.popitem(last=False)


class RateLimiter:
    """Sliding one-minute window per client key."""

    WINDOW_SECONDS = 60.0

    def __init__(self, per_minute: int):
        self.per_minute = per_minute
        self._hits: dict[str, deque[float]] = {}
        self._lock = threading.Lock()

    def check(self, client: str) -> None:
        """Record a hit for client, or raise RateLimitedError if over the limit."""
        if self.per_minute <= 0:
            return
        now = time.monotonic()
        with self._lock:
            self._prune(now)
            hits = self._hits.setdefault(client, deque())
            if len(hits) >= self.per_minute:
                raise RateLimitedError(retry_after=max(1, int(self.WINDOW_SECONDS - (now - hits[0]))))
            hits.append(now)

    def _prune(self, now: float) -> None:
        """Drop expired hits, and clients with none left, so memory stays bounded."""
        for client in list(self._hits):
            hits = self._hits[client]
            while hits and now - hits[0] > self.WINDOW_SECONDS:
                hits.popleft()
            if not hits:
                del self._hits[client]
