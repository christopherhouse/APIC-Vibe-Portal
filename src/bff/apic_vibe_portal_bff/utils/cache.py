"""Cache backends for API Center response caching.

Provides:
- :class:`CacheBackend` — structural protocol that all cache implementations must satisfy.
- :class:`InMemoryCache` — simple in-process TTL cache (single-node/dev fallback).

The Redis-backed implementation lives in
``apic_vibe_portal_bff.clients.redis_cache_client``.
"""

from __future__ import annotations

import time
from typing import Protocol, runtime_checkable


@runtime_checkable
class CacheBackend(Protocol):
    """Structural protocol for all cache backend implementations.

    Any object that provides ``get``, ``set``, ``delete``, ``clear``, and
    ``invalidate_prefix`` with matching signatures satisfies this protocol
    without explicit inheritance.
    """

    def get(self, key: str) -> object | None:
        """Return the cached value for *key*, or ``None`` if missing/expired."""
        ...

    def set(self, key: str, value: object, ttl_seconds: float | None = None) -> None:
        """Cache *value* under *key* with an optional TTL override."""
        ...

    def delete(self, key: str) -> None:
        """Remove *key* from the cache (no-op if not present)."""
        ...

    def clear(self) -> None:
        """Evict all entries."""
        ...

    def invalidate_prefix(self, prefix: str) -> int:
        """Remove all keys that start with *prefix*.

        Returns the number of keys removed.
        """
        ...


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
    """Thread-unsafe in-process TTL cache.

    Satisfies :class:`CacheBackend`.  Used as a local-development fallback
    when Redis is not configured via ``REDIS_HOST``/``REDIS_PORT``.  For
    production (multi-replica Container Apps deployments) the Redis backend
    should be used instead.
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
