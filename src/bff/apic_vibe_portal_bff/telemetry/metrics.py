"""Custom OpenTelemetry metrics for APIC Vibe Portal BFF.

All metric instruments are created lazily on first use and then cached as
module-level singletons so that repeated calls never create duplicate
instruments (or trigger OTel SDK conflict warnings on hot paths).

The meters are created with the ``opentelemetry.metrics`` API so they work
whether the Azure Monitor distro is configured or not (in tests the SDK ships
a no-op implementation).
"""

from __future__ import annotations

from opentelemetry import metrics

_METER_NAME = "apic.vibe.portal.bff"
_meter: metrics.Meter | None = None

# Instrument cache — keyed by metric name.  Cleared in tests via ``_instruments.clear()``.
_instruments: dict[str, metrics.Histogram | metrics.Counter] = {}


def get_meter() -> metrics.Meter:
    """Return the application-level OTel meter (created once)."""
    global _meter  # noqa: PLW0603
    if _meter is None:
        _meter = metrics.get_meter(_METER_NAME)
    return _meter


def _histogram(name: str, description: str, unit: str) -> metrics.Histogram:
    """Return a cached :class:`metrics.Histogram`, creating it on first call."""
    if name not in _instruments:
        _instruments[name] = get_meter().create_histogram(name=name, description=description, unit=unit)
    return _instruments[name]  # type: ignore[return-value]


def _counter(name: str, description: str, unit: str) -> metrics.Counter:
    """Return a cached :class:`metrics.Counter`, creating it on first call."""
    if name not in _instruments:
        _instruments[name] = get_meter().create_counter(name=name, description=description, unit=unit)
    return _instruments[name]  # type: ignore[return-value]


# ---------------------------------------------------------------------------
# Request / feature counters and histograms
# ---------------------------------------------------------------------------


def get_api_center_requests_histogram() -> metrics.Histogram:
    """Histogram for Azure API Center call latency (ms)."""
    return _histogram("apic.api_center.requests", "Azure API Center call latency", "ms")


def get_search_queries_histogram() -> metrics.Histogram:
    """Histogram for search request latency and result volume (ms)."""
    return _histogram("apic.search.queries", "Search request latency and result volume", "ms")


def get_chat_messages_counter() -> metrics.Counter:
    """Counter for chat message count."""
    return _counter("apic.chat.messages", "Chat message count", "{message}")


def get_chat_latency_histogram() -> metrics.Histogram:
    """Histogram for end-to-end chat response time (ms)."""
    return _histogram("apic.chat.latency", "End-to-end chat response time", "ms")


def get_cache_lookups_counter() -> metrics.Counter:
    """Counter for cache hit/miss ratio."""
    return _counter("apic.cache.lookups", "Cache hit/miss count", "{lookup}")


def get_auth_failures_counter() -> metrics.Counter:
    """Counter for authentication failures."""
    return _counter("apic.auth.failures", "Authentication failure count", "{failure}")


def get_agent_invocations_counter() -> metrics.Counter:
    """Counter for agent invocations."""
    return _counter("apic.agent.invocations", "Agent invocation count", "{invocation}")


# ---------------------------------------------------------------------------
# Token usage histograms
# ---------------------------------------------------------------------------


def get_tokens_estimated_histogram() -> metrics.Histogram:
    """Histogram for pre-call token estimates (tiktoken)."""
    return _histogram("apic.llm.tokens.estimated", "Pre-call token estimate via tiktoken", "{token}")


def get_tokens_prompt_histogram() -> metrics.Histogram:
    """Histogram for actual prompt tokens from OpenAI response."""
    return _histogram("apic.llm.tokens.prompt", "Actual prompt tokens from OpenAI response", "{token}")


def get_tokens_completion_histogram() -> metrics.Histogram:
    """Histogram for actual completion tokens from OpenAI response."""
    return _histogram("apic.llm.tokens.completion", "Actual completion tokens from OpenAI response", "{token}")


def get_tokens_total_histogram() -> metrics.Histogram:
    """Histogram for actual total tokens from OpenAI response."""
    return _histogram("apic.llm.tokens.total", "Actual total tokens (prompt + completion)", "{token}")


def get_cost_estimated_histogram() -> metrics.Histogram:
    """Histogram for estimated LLM cost per request."""
    return _histogram("apic.llm.cost.estimated", "Estimated cost based on token pricing", "USD")


# ---------------------------------------------------------------------------
# Cosmos DB RU metrics
# ---------------------------------------------------------------------------


def get_cosmos_ru_histogram() -> metrics.Histogram:
    """Histogram for Cosmos DB query Request Unit (RU) cost.

    Attributes:
        ``container``: Cosmos DB container name.
        ``operation``: Operation type (``read``, ``create``, ``replace``,
            ``delete``, ``query``).
    """
    return _histogram("apic.cosmos.ru_cost", "Cosmos DB operation Request Unit (RU) cost", "{RU}")
