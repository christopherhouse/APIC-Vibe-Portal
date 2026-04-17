"""Azure SDK client wrappers."""

from apic_vibe_portal_bff.clients.ai_search_client import (
    AISearchClient,
    AISearchClientError,
    AISearchNotFoundError,
    AISearchUnavailableError,
)
from apic_vibe_portal_bff.clients.api_center_client import (
    ApiCenterAuthError,
    ApiCenterClient,
    ApiCenterClientError,
    ApiCenterNotFoundError,
    ApiCenterUnavailableError,
)
from apic_vibe_portal_bff.clients.redis_cache_client import RedisCacheBackend

__all__ = [
    "AISearchClient",
    "AISearchClientError",
    "AISearchNotFoundError",
    "AISearchUnavailableError",
    "ApiCenterAuthError",
    "ApiCenterClient",
    "ApiCenterClientError",
    "ApiCenterNotFoundError",
    "ApiCenterUnavailableError",
    "RedisCacheBackend",
]
