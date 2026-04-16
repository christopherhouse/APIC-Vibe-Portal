"""Unit tests for RedisCacheBackend.

All Redis interactions are exercised via a mocked ``redis.Redis`` client and a
mocked Azure credential so no real Redis server or Azure connectivity is
required.  Tests verify serialization, TTL handling, prefix-based invalidation,
graceful degradation on errors, lazy connection setup, and credential provider
wiring.
"""

from __future__ import annotations

from unittest.mock import MagicMock, patch

from apic_vibe_portal_bff.clients.redis_cache_client import RedisCacheBackend, _serialize

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_backend(
    mock_redis_client: MagicMock | None = None,
) -> tuple[RedisCacheBackend, MagicMock]:
    """Return a backend with the Redis client pre-wired."""
    backend = RedisCacheBackend(
        host="test-redis.redis.azure.net",
        port=10000,
        default_ttl_seconds=60.0,
    )
    if mock_redis_client is None:
        mock_redis_client = MagicMock()
    # Pre-wire the client so _redis() doesn't try to create one
    backend._client = mock_redis_client
    return backend, mock_redis_client


# ---------------------------------------------------------------------------
# get
# ---------------------------------------------------------------------------


class TestGet:
    def test_returns_deserialized_value_on_hit(self) -> None:
        backend, mock_client = _make_backend()
        value = {"key": "value", "number": 42}
        mock_client.get.return_value = _serialize(value)

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
        backend = RedisCacheBackend(
            host="test-redis.redis.azure.net",
            key_prefix="custom:",
        )
        backend._client = MagicMock()
        backend._client.get.return_value = _serialize("hello")

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

        expected_bytes = _serialize(value)
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
    def test_deletes_all_prefixed_keys_via_scan(self) -> None:
        backend, mock_client = _make_backend()
        mock_client.scan_iter.return_value = iter([b"apic:bff:a", b"apic:bff:b"])

        backend.clear()

        mock_client.scan_iter.assert_called_once_with("apic:bff:*", count=100)
        mock_client.unlink.assert_called_once_with(b"apic:bff:a", b"apic:bff:b")

    def test_no_unlink_called_when_no_keys(self) -> None:
        backend, mock_client = _make_backend()
        mock_client.scan_iter.return_value = iter([])

        backend.clear()

        mock_client.unlink.assert_not_called()

    def test_silently_ignores_redis_error(self) -> None:
        backend, mock_client = _make_backend()
        mock_client.scan_iter.side_effect = ConnectionError("Redis down")

        backend.clear()  # must not raise


# ---------------------------------------------------------------------------
# invalidate_prefix
# ---------------------------------------------------------------------------


class TestInvalidatePrefix:
    def test_deletes_matching_keys_and_returns_count(self) -> None:
        backend, mock_client = _make_backend()
        mock_client.scan_iter.return_value = iter([b"apic:bff:apis:1", b"apic:bff:apis:2"])

        removed = backend.invalidate_prefix("apis:")

        assert removed == 2
        mock_client.scan_iter.assert_called_once_with("apic:bff:apis:*", count=100)
        mock_client.unlink.assert_called_once_with(b"apic:bff:apis:1", b"apic:bff:apis:2")

    def test_returns_zero_when_no_matching_keys(self) -> None:
        backend, mock_client = _make_backend()
        mock_client.scan_iter.return_value = iter([])

        removed = backend.invalidate_prefix("nope:")

        assert removed == 0
        mock_client.unlink.assert_not_called()

    def test_silently_ignores_redis_error_and_returns_zero(self) -> None:
        backend, mock_client = _make_backend()
        mock_client.scan_iter.side_effect = ConnectionError("Redis down")

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
        backend = RedisCacheBackend(host="localhost")
        backend.close()  # no client created — must not raise
        backend.close()  # second call also safe


# ---------------------------------------------------------------------------
# Lazy connection and token acquisition
# ---------------------------------------------------------------------------


class TestLazyConnection:
    def test_client_created_on_first_get(self) -> None:
        with (
            patch("redis.Redis") as mock_redis_cls,
            patch("redis_entraid.cred_provider.create_from_default_azure_credential") as mock_create,
        ):
            mock_redis = MagicMock()
            mock_redis_cls.return_value = mock_redis
            mock_redis.get.return_value = None

            mock_provider = MagicMock()
            mock_create.return_value = mock_provider

            backend = RedisCacheBackend(
                host="test-redis.redis.azure.net",
                port=10000,
            )
            assert backend._client is None  # not yet connected

            backend.get("key")

            mock_create.assert_called_once_with(
                scopes=("https://redis.azure.com/.default",),
            )
            mock_redis_cls.assert_called_once_with(
                host="test-redis.redis.azure.net",
                port=10000,
                ssl=True,
                credential_provider=mock_provider,
                decode_responses=False,
            )
            assert backend._client is mock_redis

    def test_credential_provider_created_lazily(self) -> None:
        """credential_provider is not created until _redis() is called."""
        with (
            patch("redis.Redis") as mock_redis_cls,
            patch("redis_entraid.cred_provider.create_from_default_azure_credential") as mock_create,
        ):
            mock_redis_cls.return_value = MagicMock()
            mock_create.return_value = MagicMock()

            backend = RedisCacheBackend(host="h")
            assert backend._client is None  # not created yet

            backend.get("any")  # triggers lazy init

            mock_create.assert_called_once_with(
                scopes=("https://redis.azure.com/.default",),
            )


# ---------------------------------------------------------------------------
# Client reuse (credential provider handles token refresh internally)
# ---------------------------------------------------------------------------


class TestClientReuse:
    def test_client_created_once_and_reused(self) -> None:
        """The credential_provider handles token refresh, so the client is created once."""
        with (
            patch("redis.Redis") as mock_redis_cls,
            patch("redis_entraid.cred_provider.create_from_default_azure_credential"),
        ):
            mock_redis = MagicMock()
            mock_redis_cls.return_value = mock_redis
            mock_redis.get.return_value = None

            backend = RedisCacheBackend(host="h", port=10000)
            backend.get("a")
            backend.get("b")

            # Redis client only created once — credential_provider refreshes tokens
            mock_redis_cls.assert_called_once()
            assert backend._client is mock_redis


# ---------------------------------------------------------------------------
# Protocol conformance
# ---------------------------------------------------------------------------


class TestProtocolConformance:
    def test_redis_backend_satisfies_cache_backend_protocol(self) -> None:
        from apic_vibe_portal_bff.utils.cache import CacheBackend

        backend = RedisCacheBackend(host="localhost")
        assert isinstance(backend, CacheBackend)

    def test_in_memory_cache_satisfies_cache_backend_protocol(self) -> None:
        from apic_vibe_portal_bff.utils.cache import CacheBackend, InMemoryCache

        cache = InMemoryCache()
        assert isinstance(cache, CacheBackend)
