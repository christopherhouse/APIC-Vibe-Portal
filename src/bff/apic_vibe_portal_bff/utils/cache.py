"""Simple in-memory TTL cache for Azure API Center responses.

The cache stores arbitrary values keyed by string keys and expires entries
after a configurable TTL.  It is intentionally simple (no LRU eviction,
single-process only) — sufficient for BFF caching of relatively small API
Center datasets.
"""

from __future__ import annotations

import time


class CacheEntry[V]:
    """A single cached value with an expiry timestamp."""

    __slots__ = ("value", "expires_at")

    def __init__(self, value: V, ttl_seconds: float) -> None:
        self.value: V = value
        self.expires_at: float = time.monotonic() + ttl_seconds

    @property
    def is_expired(self) -> bool:
        return time.monotonic() >= self.expires_at


class InMemoryCache[V]:
    """Thread-unsafe in-memory TTL cache.

    Suitable for single-threaded async FastAPI workloads where the GIL
    provides sufficient protection.  For multi-process deployments (gunicorn
    workers) a distributed cache (e.g., Redis) should replace this.
    """

    def __init__(self, default_ttl_seconds: float = 300.0) -> None:
        self._default_ttl = default_ttl_seconds
        self._store: dict[str, CacheEntry[V]] = {}

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def get(self, key: str) -> V | None:
        """Return the cached value for *key*, or ``None`` if missing/expired."""
        entry = self._store.get(key)
        if entry is None:
            return None
        if entry.is_expired:
            del self._store[key]
            return None
        return entry.value

    def set(self, key: str, value: V, ttl_seconds: float | None = None) -> None:
        """Cache *value* under *key* with an optional TTL override."""
        ttl = ttl_seconds if ttl_seconds is not None else self._default_ttl
        self._store[key] = CacheEntry(value, ttl)

    def delete(self, key: str) -> None:
        """Remove *key* from the cache (no-op if not present)."""
        self._store.pop(key, None)

    def clear(self) -> None:
        """Evict all entries."""
        self._store.clear()

    def invalidate_prefix(self, prefix: str) -> int:
        """Remove all keys that start with *prefix*.

        Returns the number of keys removed.
        """
        to_delete = [k for k in self._store if k.startswith(prefix)]
        for k in to_delete:
            del self._store[k]
        return len(to_delete)

    def __len__(self) -> int:
        # Evict expired entries first so len() reflects live entries.
        expired = [k for k, v in self._store.items() if v.is_expired]
        for k in expired:
            del self._store[k]
        return len(self._store)
