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

import importlib
import json
import logging
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

# Only allow deserialization of classes from this package to prevent arbitrary
# code execution if Redis contents were ever tampered with.
_SAFE_MODULE_PREFIX = "apic_vibe_portal_bff."

# Number of keys to delete per UNLINK batch (avoids O(N) blocking DEL calls)
_SCAN_BATCH_SIZE = 100


# ---------------------------------------------------------------------------
# Serialization helpers
# ---------------------------------------------------------------------------


def _serialize(value: object) -> bytes:
    """Serialize *value* to JSON bytes with an embedded type tag.

    Pydantic models and lists of Pydantic models are recorded with a
    fully-qualified type path so they can be safely reconstructed on load.
    All other JSON-serializable values are stored as-is under the ``__json__``
    sentinel.
    """
    from pydantic import BaseModel

    if isinstance(value, BaseModel):
        cls = type(value)
        return json.dumps(
            {
                "__type__": f"{cls.__module__}.{cls.__qualname__}",
                "__data__": value.model_dump(mode="json"),
            }
        ).encode()

    if isinstance(value, list) and value and isinstance(value[0], BaseModel):
        cls = type(value[0])
        return json.dumps(
            {
                "__type__": f"list[{cls.__module__}.{cls.__qualname__}]",
                "__data__": [v.model_dump(mode="json") for v in value],  # type: ignore[union-attr]
            }
        ).encode()

    # Plain JSON-serializable value (empty list, str, int, dict, …)
    return json.dumps({"__type__": "__json__", "__data__": value}).encode()


def _deserialize(raw: bytes) -> object:
    """Reconstruct a value from JSON bytes produced by :func:`_serialize`.

    Only Pydantic models whose module path starts with ``apic_vibe_portal_bff.``
    are allowed to be reconstructed, preventing deserialization of untrusted
    class paths even if Redis contents are modified by a third party.
    """
    wrapper = json.loads(raw)
    type_tag: str = wrapper["__type__"]
    data = wrapper["__data__"]

    if type_tag == "__json__":
        return data

    if type_tag.startswith("list["):
        inner = type_tag[5:-1]  # strip "list[…]"
        cls = _safe_import_model(inner)
        return [cls.model_validate(item) for item in data]

    cls = _safe_import_model(type_tag)
    return cls.model_validate(data)


def _safe_import_model(type_path: str):  # type: ignore[return]
    """Import a Pydantic BaseModel subclass from *type_path* if it is trusted.

    Raises ``ValueError`` when *type_path* is not within the application
    package, and ``TypeError`` if the resolved name is not a BaseModel subclass.
    """
    from pydantic import BaseModel

    if not type_path.startswith(_SAFE_MODULE_PREFIX):
        raise ValueError(f"Refusing to deserialize untrusted type path: {type_path!r}")
    module_path, _, class_name = type_path.rpartition(".")
    module = importlib.import_module(module_path)
    cls = getattr(module, class_name)
    if not (isinstance(cls, type) and issubclass(cls, BaseModel)):
        raise TypeError(f"{type_path!r} is not a Pydantic BaseModel subclass")
    return cls


class RedisCacheBackend:
    """Redis-backed cache satisfying :class:`~apic_vibe_portal_bff.utils.cache.CacheBackend`.

    Connects to Azure Managed Redis using Entra ID token authentication.
    Values are serialized to JSON with embedded type information so that
    Pydantic model instances and lists thereof can be stored and reconstructed
    without using ``pickle``.

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
        assert self._credential is not None
        return self._credential

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
            return _deserialize(raw)
        except Exception:
            logger.warning("Redis GET failed for key %r", key, exc_info=True)
            return None

    def set(self, key: str, value: object, ttl_seconds: float | None = None) -> None:
        """Serialize and store *value* in Redis with a TTL."""
        try:
            ttl = int(ttl_seconds if ttl_seconds is not None else self._default_ttl)
            self._redis().setex(self._full_key(key), ttl, _serialize(value))
        except Exception:
            logger.warning("Redis SET failed for key %r", key, exc_info=True)

    def delete(self, key: str) -> None:
        """Remove *key* from Redis (no-op if not present)."""
        try:
            self._redis().delete(self._full_key(key))
        except Exception:
            logger.warning("Redis DELETE failed for key %r", key, exc_info=True)

    def clear(self) -> None:
        """Delete all keys under this backend's namespace prefix.

        Uses ``SCAN`` + ``UNLINK`` in batches to avoid a single O(N) blocking
        ``KEYS`` call that could stall the Redis server.
        """
        try:
            client = self._redis()
            pattern = f"{self._key_prefix}*"
            batch: list[bytes] = []
            for key in client.scan_iter(pattern, count=_SCAN_BATCH_SIZE):
                batch.append(key)
                if len(batch) >= _SCAN_BATCH_SIZE:
                    client.unlink(*batch)
                    batch = []
            if batch:
                client.unlink(*batch)
        except Exception:
            logger.warning("Redis CLEAR failed", exc_info=True)

    def invalidate_prefix(self, prefix: str) -> int:
        """Delete all keys whose logical name starts with *prefix*.

        Uses ``SCAN`` + ``UNLINK`` in batches to avoid blocking the server.
        Returns the number of keys removed.
        """
        try:
            client = self._redis()
            pattern = f"{self._key_prefix}{prefix}*"
            count = 0
            batch: list[bytes] = []
            for key in client.scan_iter(pattern, count=_SCAN_BATCH_SIZE):
                batch.append(key)
                if len(batch) >= _SCAN_BATCH_SIZE:
                    client.unlink(*batch)
                    count += len(batch)
                    batch = []
            if batch:
                client.unlink(*batch)
                count += len(batch)
            return count
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
