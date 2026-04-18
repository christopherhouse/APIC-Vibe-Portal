"""Cache backends for API Center response caching.

Provides:
- :class:`CacheBackend` — structural protocol that all cache implementations must satisfy.
- :class:`CacheResult` — return type for :meth:`CacheBackend.get_with_staleness`.
- :class:`InMemoryCache` — simple in-process TTL cache (single-node/dev fallback).

The Redis-backed implementation lives in
``apic_vibe_portal_bff.clients.redis_cache_client``.
"""

from __future__ import annotations

import time
from dataclasses import dataclass
from typing import Protocol, runtime_checkable

# Fraction of the original TTL at which a cached value is considered
# "near-expiry" and should be refreshed in the background while the stale
# value is still returned to the caller.  0.2 means "when only 20 % of the
# original TTL remains".
STALE_REFRESH_THRESHOLD = 0.2


@dataclass(frozen=True, slots=True)
class CacheResult:
    """Value returned by :meth:`CacheBackend.get_with_staleness`.

    Attributes
    ----------
    value:
        The cached object, or ``None`` on a true miss.
    needs_refresh:
        ``True`` when the entry is still usable but close to expiry
        and should be asynchronously refreshed in the background.
    """

    value: object | None
    needs_refresh: bool


@runtime_checkable
class CacheBackend(Protocol):
    """Structural protocol for all cache backend implementations.

    Any object that provides ``get``, ``set``, ``delete``, ``clear``,
    ``invalidate_prefix``, and ``get_with_staleness`` with matching
    signatures satisfies this protocol without explicit inheritance.
    """

    def get(self, key: str) -> object | None:
        """Return the cached value for *key*, or ``None`` if missing/expired."""
        ...

    def get_with_staleness(self, key: str, original_ttl_seconds: float) -> CacheResult:
        """Return the cached value together with a staleness hint.

        If the remaining TTL is less than *STALE_REFRESH_THRESHOLD* of the
        original TTL the entry is flagged as ``needs_refresh``.  The caller
        should return the value immediately and schedule an asynchronous
        background refresh.

        Parameters
        ----------
        key:
            Cache key.
        original_ttl_seconds:
            The TTL that was used when the value was stored.  Required so
            that the "remaining fraction" can be computed.
        """
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
    """A single cached value with an expiry timestamp and original TTL."""

    __slots__ = ("value", "expires_at", "ttl_seconds")

    def __init__(self, value: V, ttl_seconds: float) -> None:
        self.value: V = value
        self.ttl_seconds: float = ttl_seconds
        self.expires_at: float = time.monotonic() + ttl_seconds

    @property
    def is_expired(self) -> bool:
        return time.monotonic() >= self.expires_at

    @property
    def remaining_fraction(self) -> float:
        """Fraction of the original TTL still remaining (0.0 – 1.0)."""
        if self.ttl_seconds <= 0:
            return 0.0
        remaining = self.expires_at - time.monotonic()
        return max(0.0, remaining / self.ttl_seconds)


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

    def get_with_staleness(self, key: str, original_ttl_seconds: float) -> CacheResult:
        """Return the value together with a near-expiry hint.

        When the remaining TTL is below ``STALE_REFRESH_THRESHOLD`` of
        *original_ttl_seconds*, :pyattr:`CacheResult.needs_refresh` is
        ``True``.  The caller should return the value immediately and kick
        off a background refresh.
        """
        entry = self._store.get(key)
        if entry is None:
            return CacheResult(value=None, needs_refresh=False)
        if entry.is_expired:
            del self._store[key]
            return CacheResult(value=None, needs_refresh=False)

        needs_refresh = entry.remaining_fraction < STALE_REFRESH_THRESHOLD
        return CacheResult(value=entry.value, needs_refresh=needs_refresh)

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
