"""Azure SDK client wrappers."""

from apic_client.exceptions import (
    ApiCenterAuthError,
    ApiCenterClientError,
    ApiCenterNotFoundError,
    ApiCenterUnavailableError,
)

from apic_vibe_portal_bff.clients.ai_search_client import (
    AISearchClient,
    AISearchClientError,
    AISearchNotFoundError,
    AISearchUnavailableError,
)
from apic_vibe_portal_bff.clients.api_center_client import ApiCenterClient
from apic_vibe_portal_bff.clients.openai_client import (
    OpenAIClient,
    OpenAIClientError,
    OpenAIRateLimitError,
    OpenAIUnavailableError,
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
    "OpenAIClient",
    "OpenAIClientError",
    "OpenAIRateLimitError",
    "OpenAIUnavailableError",
    "RedisCacheBackend",
]
