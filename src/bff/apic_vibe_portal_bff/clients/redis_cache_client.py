"""Redis-backed cache client for API Center response caching.

Implements the :class:`~apic_vibe_portal_bff.utils.cache.CacheBackend` protocol
using Azure Managed Redis via the ``redis-py`` library.

Authentication uses **Entra ID** (user-assigned managed identity) — no
access keys or connection-string secrets are required.  The BFF acquires a
short-lived token from ``DefaultAzureCredential``, passes it as the Redis
password, and refreshes it automatically before expiry.

Connection is established lazily on first use.  All operations catch Redis
exceptions and log a warning rather than propagating — a cache failure must
never bring down the BFF.  The caller will simply receive a cache miss and
fall through to the live API Center call.
"""

from __future__ import annotations

import logging
import pickle
import time
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    import redis as redis_lib
    from azure.core.credentials import TokenCredential

logger = logging.getLogger(__name__)

# Scope required to obtain a token for Azure Managed Redis
_REDIS_AUTH_SCOPE = "https://redis.azure.com/.default"

# Refresh the token this many seconds before it expires to avoid mid-request
# expiry (Azure tokens are typically valid for 1 hour)
_TOKEN_REFRESH_BUFFER_SECONDS = 300  # 5 minutes

# Key namespace prefix applied to every key stored in Redis, ensuring the BFF
# does not clash with other tenants sharing the same Redis instance.
_DEFAULT_PREFIX = "apic:bff:"


class RedisCacheBackend:
    """Redis-backed cache satisfying :class:`~apic_vibe_portal_bff.utils.cache.CacheBackend`.

    Connects to Azure Managed Redis using Entra ID token authentication.
    Values are serialized with ``pickle`` so that arbitrary Pydantic model
    instances and lists thereof can be stored without a custom serializer.

    Parameters
    ----------
    host:
        Azure Managed Redis hostname
        (e.g. ``my-redis.eastus.redis.azure.net``).
    port:
        Redis Enterprise database port — 10000 by default.
    credential:
        An ``azure-identity`` ``TokenCredential`` used to obtain Entra tokens.
        Defaults to ``DefaultAzureCredential()`` (lazily instantiated on first
        use so unit tests can inject mocks without importing ``azure-identity``).
    default_ttl_seconds:
        Default expiry applied when ``set`` is called without an explicit TTL.
    key_prefix:
        Namespace prefix prepended to every key stored in Redis.
    """

    def __init__(
        self,
        host: str,
        port: int = 10000,
        credential: TokenCredential | None = None,
        default_ttl_seconds: float = 300.0,
        key_prefix: str = _DEFAULT_PREFIX,
    ) -> None:
        self._host = host
        self._port = port
        self._credential = credential  # lazily default to DefaultAzureCredential
        self._default_ttl = default_ttl_seconds
        self._key_prefix = key_prefix
        self._client: redis_lib.Redis | None = None  # type: ignore[type-arg]
        self._token_expiry: float = 0.0  # unix timestamp after which we must refresh

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _get_credential(self) -> TokenCredential:
        """Return the credential, defaulting to ``DefaultAzureCredential``."""
        if self._credential is None:
            from azure.identity import DefaultAzureCredential

            self._credential = DefaultAzureCredential()
        return self._credential  # type: ignore[return-value]

    def _redis(self) -> redis_lib.Redis:  # type: ignore[type-arg]
        """Lazily create/refresh the Redis client when the token is near expiry."""
        now = time.time()
        if self._client is None or now >= self._token_expiry:
            import redis

            credential = self._get_credential()
            token = credential.get_token(_REDIS_AUTH_SCOPE)
            # Schedule refresh before the token expires
            self._token_expiry = token.expires_on - _TOKEN_REFRESH_BUFFER_SECONDS

            # Close the existing connection (if any) before creating a new one
            if self._client is not None:
                try:
                    self._client.close()
                except Exception:
                    pass

            self._client = redis.Redis(
                host=self._host,
                port=self._port,
                ssl=True,
                username="",          # Entra auth — username is unused
                password=token.token,
                decode_responses=False,
            )
        return self._client

    def _full_key(self, key: str) -> str:
        return f"{self._key_prefix}{key}"

    # ------------------------------------------------------------------
    # CacheBackend implementation
    # ------------------------------------------------------------------

    def get(self, key: str) -> object | None:
        """Return the deserialized cached value, or ``None`` on miss/error."""
        try:
            raw = self._redis().get(self._full_key(key))
            if raw is None:
                return None
            return pickle.loads(raw)  # noqa: S301  # data is only ever written by this BFF
        except Exception:
            logger.warning("Redis GET failed for key %r", key, exc_info=True)
            return None

    def set(self, key: str, value: object, ttl_seconds: float | None = None) -> None:
        """Serialize and store *value* in Redis with a TTL."""
        try:
            ttl = int(ttl_seconds if ttl_seconds is not None else self._default_ttl)
            self._redis().setex(self._full_key(key), ttl, pickle.dumps(value))
        except Exception:
            logger.warning("Redis SET failed for key %r", key, exc_info=True)

    def delete(self, key: str) -> None:
        """Remove *key* from Redis (no-op if not present)."""
        try:
            self._redis().delete(self._full_key(key))
        except Exception:
            logger.warning("Redis DELETE failed for key %r", key, exc_info=True)

    def clear(self) -> None:
        """Delete all keys under this backend's namespace prefix."""
        try:
            client = self._redis()
            pattern = f"{self._key_prefix}*"
            keys = client.keys(pattern)
            if keys:
                client.delete(*keys)
        except Exception:
            logger.warning("Redis CLEAR failed", exc_info=True)

    def invalidate_prefix(self, prefix: str) -> int:
        """Delete all keys whose logical name starts with *prefix*.

        Returns the number of keys removed.
        """
        try:
            client = self._redis()
            pattern = f"{self._key_prefix}{prefix}*"
            keys = client.keys(pattern)
            if not keys:
                return 0
            client.delete(*keys)
            return len(keys)
        except Exception:
            logger.warning("Redis INVALIDATE_PREFIX failed for prefix %r", prefix, exc_info=True)
            return 0

    def close(self) -> None:
        """Close the underlying Redis connection."""
        if self._client is not None:
            try:
                self._client.close()
            except Exception:
                logger.warning("Redis CLOSE failed", exc_info=True)
            finally:
                self._client = None
