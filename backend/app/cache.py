import time
import threading
from typing import Optional, Any

class ReportCache:
    def __init__(self, ttl_seconds: int = 60):
        self.ttl_seconds = ttl_seconds
        self._cache: Optional[Any] = None
        self._cached_at: float = 0
        self._lock = threading.Lock()

    def get(self) -> Optional[Any]:
        with self._lock:
            if self._cache is not None and (time.time() - self._cached_at) < self.ttl_seconds:
                return self._cache
            return None

    def set(self, data: Any):
        with self._lock:
            self._cache = data
            self._cached_at = time.time()

    def invalidate(self):
        with self._lock:
            self._cache = None
            self._cached_at = 0

summary_cache = ReportCache(ttl_seconds=60)