"""Unit tests for RedisCacheBackend.

All Redis interactions are exercised via a mocked ``redis.Redis`` client and a
mocked Azure credential so no real Redis server or Azure connectivity is
required.  Tests verify serialization, TTL handling, prefix-based invalidation,
graceful degradation on errors, lazy connection setup, and token refresh logic.
"""

from __future__ import annotations

import pickle
import time
from unittest.mock import MagicMock, patch

from apic_vibe_portal_bff.clients.redis_cache_client import RedisCacheBackend

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_credential(expires_in: float = 7200.0) -> MagicMock:
    """Return a mock Azure TokenCredential whose token expires at now + expires_in."""
    token = MagicMock()
    token.token = "fake-entra-token"
    token.expires_on = time.time() + expires_in
    cred = MagicMock()
    cred.get_token.return_value = token
    return cred


def _make_backend(
    mock_redis_client: MagicMock | None = None,
    expires_in: float = 7200.0,
) -> tuple[RedisCacheBackend, MagicMock]:
    """Return a backend with the Redis client and token pre-wired."""
    credential = _make_credential(expires_in=expires_in)
    backend = RedisCacheBackend(
        host="test-redis.redis.azure.net",
        port=10000,
        credential=credential,
        default_ttl_seconds=60.0,
    )
    if mock_redis_client is None:
        mock_redis_client = MagicMock()
    # Pre-wire a valid token expiry so _redis() doesn't try to fetch a new one
    backend._token_expiry = time.time() + expires_in
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
        credential = _make_credential()
        backend = RedisCacheBackend(
            host="test-redis.redis.azure.net",
            credential=credential,
            key_prefix="custom:",
        )
        backend._token_expiry = time.time() + 7200
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
        credential = _make_credential()
        backend = RedisCacheBackend(host="localhost", credential=credential)
        backend.close()  # no client created — must not raise
        backend.close()  # second call also safe


# ---------------------------------------------------------------------------
# Lazy connection and token acquisition
# ---------------------------------------------------------------------------


class TestLazyConnection:
    def test_client_created_on_first_get(self) -> None:
        credential = _make_credential()
        with patch("redis.Redis") as mock_redis_cls:
            mock_redis = MagicMock()
            mock_redis_cls.return_value = mock_redis
            mock_redis.get.return_value = None

            backend = RedisCacheBackend(
                host="test-redis.redis.azure.net",
                port=10000,
                credential=credential,
            )
            assert backend._client is None  # not yet connected

            backend.get("key")

            mock_redis_cls.assert_called_once_with(
                host="test-redis.redis.azure.net",
                port=10000,
                ssl=True,
                username="",
                password="fake-entra-token",
                decode_responses=False,
            )
            assert backend._client is mock_redis

    def test_default_credential_created_lazily(self) -> None:
        """DefaultAzureCredential is not imported until _redis() is called."""
        with patch("redis.Redis") as mock_redis_cls:
            mock_redis_cls.return_value = MagicMock()
            mock_token = MagicMock()
            mock_token.token = "lazy-token"
            mock_token.expires_on = time.time() + 3600
            mock_cred = MagicMock()
            mock_cred.get_token.return_value = mock_token

            with patch("azure.identity.DefaultAzureCredential") as mock_dac:
                mock_dac.return_value = mock_cred
                backend = RedisCacheBackend(host="h")
                assert backend._credential is None  # not created yet

                backend.get("any")  # triggers lazy init

                mock_dac.assert_called_once()
                mock_cred.get_token.assert_called_once_with(
                    "https://redis.azure.com/.default"
                )


# ---------------------------------------------------------------------------
# Token refresh
# ---------------------------------------------------------------------------


class TestTokenRefresh:
    def test_client_recreated_when_token_expired(self) -> None:
        credential = _make_credential(expires_in=7200)
        with patch("redis.Redis") as mock_redis_cls:
            first_client = MagicMock()
            second_client = MagicMock()
            mock_redis_cls.side_effect = [first_client, second_client]
            first_client.get.return_value = None
            second_client.get.return_value = None

            backend = RedisCacheBackend(
                host="h", port=10000, credential=credential
            )
            backend.get("a")  # creates first client
            assert backend._client is first_client

            # Simulate token expiry by setting expiry to the past
            backend._token_expiry = time.time() - 1

            backend.get("b")  # should create second client

            assert backend._client is second_client
            assert mock_redis_cls.call_count == 2
            first_client.close.assert_called_once()  # old client was closed

    def test_token_expiry_set_with_buffer(self) -> None:
        credential = _make_credential(expires_in=3600)
        with patch("redis.Redis") as mock_redis_cls:
            mock_redis_cls.return_value = MagicMock()
            mock_redis_cls.return_value.get.return_value = None

            backend = RedisCacheBackend(host="h", credential=credential)
            backend.get("k")

            # Token expires_on was (now + 3600); expiry should be set to (now + 3600 - 300)
            # Allow ±5 s tolerance for test timing
            expected = credential.get_token.return_value.expires_on - 300
            assert abs(backend._token_expiry - expected) < 5


# ---------------------------------------------------------------------------
# Protocol conformance
# ---------------------------------------------------------------------------


class TestProtocolConformance:
    def test_redis_backend_satisfies_cache_backend_protocol(self) -> None:
        from apic_vibe_portal_bff.utils.cache import CacheBackend

        backend = RedisCacheBackend(host="localhost", credential=_make_credential())
        assert isinstance(backend, CacheBackend)

    def test_in_memory_cache_satisfies_cache_backend_protocol(self) -> None:
        from apic_vibe_portal_bff.utils.cache import CacheBackend, InMemoryCache

        cache = InMemoryCache()
        assert isinstance(cache, CacheBackend)
