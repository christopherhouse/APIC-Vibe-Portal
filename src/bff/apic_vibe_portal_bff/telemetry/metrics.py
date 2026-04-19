"""Custom OpenTelemetry metrics for APIC Vibe Portal BFF.

All metric instruments are created lazily and cached as module-level singletons.
The meters are created with the ``opentelemetry.metrics`` API so they work
whether the Azure Monitor distro is configured or not (in tests the SDK ships
a no-op implementation).
"""

from __future__ import annotations

from opentelemetry import metrics

_METER_NAME = "apic.vibe.portal.bff"
_meter: metrics.Meter | None = None


def get_meter() -> metrics.Meter:
    """Return the application-level OTel meter (created once)."""
    global _meter  # noqa: PLW0603
    if _meter is None:
        _meter = metrics.get_meter(_METER_NAME)
    return _meter


# ---------------------------------------------------------------------------
# Request / feature counters and histograms
# ---------------------------------------------------------------------------


def get_api_center_requests_histogram() -> metrics.Histogram:
    """Histogram for Azure API Center call latency (ms)."""
    return get_meter().create_histogram(
        name="apic.api_center.requests",
        description="Azure API Center call latency",
        unit="ms",
    )


def get_search_queries_histogram() -> metrics.Histogram:
    """Histogram for search request latency and result volume (ms)."""
    return get_meter().create_histogram(
        name="apic.search.queries",
        description="Search request latency and result volume",
        unit="ms",
    )


def get_chat_messages_counter() -> metrics.Counter:
    """Counter for chat message count."""
    return get_meter().create_counter(
        name="apic.chat.messages",
        description="Chat message count",
        unit="{message}",
    )


def get_chat_latency_histogram() -> metrics.Histogram:
    """Histogram for end-to-end chat response time (ms)."""
    return get_meter().create_histogram(
        name="apic.chat.latency",
        description="End-to-end chat response time",
        unit="ms",
    )


def get_cache_lookups_counter() -> metrics.Counter:
    """Counter for cache hit/miss ratio."""
    return get_meter().create_counter(
        name="apic.cache.lookups",
        description="Cache hit/miss count",
        unit="{lookup}",
    )


def get_auth_failures_counter() -> metrics.Counter:
    """Counter for authentication failures."""
    return get_meter().create_counter(
        name="apic.auth.failures",
        description="Authentication failure count",
        unit="{failure}",
    )


def get_agent_invocations_counter() -> metrics.Counter:
    """Counter for agent invocations."""
    return get_meter().create_counter(
        name="apic.agent.invocations",
        description="Agent invocation count",
        unit="{invocation}",
    )


# ---------------------------------------------------------------------------
# Token usage histograms
# ---------------------------------------------------------------------------


def get_tokens_estimated_histogram() -> metrics.Histogram:
    """Histogram for pre-call token estimates (tiktoken)."""
    return get_meter().create_histogram(
        name="apic.llm.tokens.estimated",
        description="Pre-call token estimate via tiktoken",
        unit="{token}",
    )


def get_tokens_prompt_histogram() -> metrics.Histogram:
    """Histogram for actual prompt tokens from OpenAI response."""
    return get_meter().create_histogram(
        name="apic.llm.tokens.prompt",
        description="Actual prompt tokens from OpenAI response",
        unit="{token}",
    )


def get_tokens_completion_histogram() -> metrics.Histogram:
    """Histogram for actual completion tokens from OpenAI response."""
    return get_meter().create_histogram(
        name="apic.llm.tokens.completion",
        description="Actual completion tokens from OpenAI response",
        unit="{token}",
    )


def get_tokens_total_histogram() -> metrics.Histogram:
    """Histogram for actual total tokens from OpenAI response."""
    return get_meter().create_histogram(
        name="apic.llm.tokens.total",
        description="Actual total tokens (prompt + completion)",
        unit="{token}",
    )


def get_cost_estimated_histogram() -> metrics.Histogram:
    """Histogram for estimated LLM cost per request."""
    return get_meter().create_histogram(
        name="apic.llm.cost.estimated",
        description="Estimated cost based on token pricing",
        unit="USD",
    )
