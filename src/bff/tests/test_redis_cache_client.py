"""Unit tests for RedisCacheBackend.

All Redis interactions are exercised via a mocked ``redis.Redis`` client so
no real Redis server is required.  Tests verify serialization, TTL handling,
prefix-based invalidation, graceful degradation on errors, and lazy connection
setup.
"""

from __future__ import annotations

import pickle
from unittest.mock import MagicMock, patch

from apic_vibe_portal_bff.clients.redis_cache_client import RedisCacheBackend


def _make_backend(mock_redis_client: MagicMock | None = None) -> tuple[RedisCacheBackend, MagicMock]:
    """Return a backend with the Redis client pre-wired."""
    backend = RedisCacheBackend(url="redis://localhost:6379", default_ttl_seconds=60.0)
    if mock_redis_client is None:
        mock_redis_client = MagicMock()
    backend._client = mock_redis_client
    return backend, mock_redis_client


# ---------------------------------------------------------------------------
# get
# ---------------------------------------------------------------------------


class TestGet:
    def test_returns_deserialized_value_on_hit(self) -> None:
        backend, mock_client = _make_backend()
        value = {"key": "value", "number": 42}
        mock_client.get.return_value = pickle.dumps(value)

        result = backend.get("test-key")

        assert result == value
        mock_client.get.assert_called_once_with("apic:bff:test-key")

    def test_returns_none_on_miss(self) -> None:
        backend, mock_client = _make_backend()
        mock_client.get.return_value = None

        result = backend.get("missing")

        assert result is None

    def test_returns_none_on_redis_error(self) -> None:
        backend, mock_client = _make_backend()
        mock_client.get.side_effect = ConnectionError("Redis unavailable")

        result = backend.get("any-key")

        assert result is None  # graceful degradation

    def test_key_prefix_applied(self) -> None:
        backend = RedisCacheBackend(url="redis://localhost", key_prefix="custom:")
        backend._client = MagicMock()
        backend._client.get.return_value = pickle.dumps("hello")

        backend.get("foo")

        backend._client.get.assert_called_once_with("custom:foo")


# ---------------------------------------------------------------------------
# set
# ---------------------------------------------------------------------------


class TestSet:
    def test_stores_serialized_value_with_ttl(self) -> None:
        backend, mock_client = _make_backend()
        value = [1, 2, 3]

        backend.set("my-key", value, ttl_seconds=120.0)

        expected_bytes = pickle.dumps(value)
        mock_client.setex.assert_called_once_with("apic:bff:my-key", 120, expected_bytes)

    def test_uses_default_ttl_when_not_specified(self) -> None:
        backend, mock_client = _make_backend()

        backend.set("my-key", "hello")

        _, ttl, _ = mock_client.setex.call_args[0]
        assert ttl == 60  # default_ttl_seconds cast to int

    def test_ttl_cast_to_int(self) -> None:
        backend, mock_client = _make_backend()

        backend.set("key", "v", ttl_seconds=90.9)

        _, ttl, _ = mock_client.setex.call_args[0]
        assert isinstance(ttl, int)
        assert ttl == 90

    def test_silently_ignores_redis_error(self) -> None:
        backend, mock_client = _make_backend()
        mock_client.setex.side_effect = ConnectionError("Redis down")

        backend.set("key", "value")  # must not raise


# ---------------------------------------------------------------------------
# delete
# ---------------------------------------------------------------------------


class TestDelete:
    def test_deletes_full_key(self) -> None:
        backend, mock_client = _make_backend()

        backend.delete("some-key")

        mock_client.delete.assert_called_once_with("apic:bff:some-key")

    def test_silently_ignores_redis_error(self) -> None:
        backend, mock_client = _make_backend()
        mock_client.delete.side_effect = ConnectionError("Redis down")

        backend.delete("key")  # must not raise


# ---------------------------------------------------------------------------
# clear
# ---------------------------------------------------------------------------


class TestClear:
    def test_deletes_all_prefixed_keys(self) -> None:
        backend, mock_client = _make_backend()
        mock_client.keys.return_value = [b"apic:bff:a", b"apic:bff:b"]

        backend.clear()

        mock_client.keys.assert_called_once_with("apic:bff:*")
        mock_client.delete.assert_called_once_with(b"apic:bff:a", b"apic:bff:b")

    def test_no_delete_called_when_no_keys(self) -> None:
        backend, mock_client = _make_backend()
        mock_client.keys.return_value = []

        backend.clear()

        mock_client.delete.assert_not_called()

    def test_silently_ignores_redis_error(self) -> None:
        backend, mock_client = _make_backend()
        mock_client.keys.side_effect = ConnectionError("Redis down")

        backend.clear()  # must not raise


# ---------------------------------------------------------------------------
# invalidate_prefix
# ---------------------------------------------------------------------------


class TestInvalidatePrefix:
    def test_deletes_matching_keys_and_returns_count(self) -> None:
        backend, mock_client = _make_backend()
        mock_client.keys.return_value = [b"apic:bff:apis:1", b"apic:bff:apis:2"]

        removed = backend.invalidate_prefix("apis:")

        assert removed == 2
        mock_client.keys.assert_called_once_with("apic:bff:apis:*")
        mock_client.delete.assert_called_once_with(b"apic:bff:apis:1", b"apic:bff:apis:2")

    def test_returns_zero_when_no_matching_keys(self) -> None:
        backend, mock_client = _make_backend()
        mock_client.keys.return_value = []

        removed = backend.invalidate_prefix("nope:")

        assert removed == 0
        mock_client.delete.assert_not_called()

    def test_silently_ignores_redis_error_and_returns_zero(self) -> None:
        backend, mock_client = _make_backend()
        mock_client.keys.side_effect = ConnectionError("Redis down")

        removed = backend.invalidate_prefix("anything:")

        assert removed == 0


# ---------------------------------------------------------------------------
# close
# ---------------------------------------------------------------------------


class TestClose:
    def test_close_calls_client_close(self) -> None:
        backend, mock_client = _make_backend()

        backend.close()

        mock_client.close.assert_called_once()
        assert backend._client is None

    def test_close_is_idempotent(self) -> None:
        backend = RedisCacheBackend(url="redis://localhost")
        backend.close()  # no client created — must not raise
        backend.close()  # second call also safe


# ---------------------------------------------------------------------------
# Lazy connection
# ---------------------------------------------------------------------------


class TestLazyConnection:
    def test_client_created_on_first_get(self) -> None:
        with patch("redis.from_url") as mock_from_url:
            mock_redis = MagicMock()
            mock_from_url.return_value = mock_redis
            mock_redis.get.return_value = None

            backend = RedisCacheBackend(url="rediss://:pw@host:6380")
            assert backend._client is None  # not yet connected

            backend.get("key")

            mock_from_url.assert_called_once_with("rediss://:pw@host:6380", decode_responses=False)
            assert backend._client is mock_redis


# ---------------------------------------------------------------------------
# Protocol conformance
# ---------------------------------------------------------------------------


class TestProtocolConformance:
    def test_redis_backend_satisfies_cache_backend_protocol(self) -> None:
        from apic_vibe_portal_bff.utils.cache import CacheBackend

        backend = RedisCacheBackend(url="redis://localhost")
        assert isinstance(backend, CacheBackend)

    def test_in_memory_cache_satisfies_cache_backend_protocol(self) -> None:
        from apic_vibe_portal_bff.utils.cache import CacheBackend, InMemoryCache

        cache = InMemoryCache()
        assert isinstance(cache, CacheBackend)
