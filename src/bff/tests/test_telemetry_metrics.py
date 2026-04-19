"""Tests for custom OTel metrics (mocked meter).

Verifies that each metric factory function records to the expected
instrument name, unit, and attribute set.
"""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_mock_meter() -> MagicMock:
    """Return a MagicMock that mimics ``opentelemetry.metrics.Meter``."""
    meter = MagicMock()
    # create_histogram / create_counter return a MagicMock instrument
    meter.create_histogram.return_value = MagicMock()
    meter.create_counter.return_value = MagicMock()
    return meter


# ---------------------------------------------------------------------------
# Tests — metrics.py instrument factories
# ---------------------------------------------------------------------------


class TestMetricsInstrumentFactories:
    """Verify each factory creates the correct instrument and records values."""

    def setup_method(self) -> None:
        """Reset the module-level meter and instrument caches before each test."""
        import apic_vibe_portal_bff.telemetry.metrics as m

        m._meter = None
        m._instruments.clear()

    def test_get_meter_returns_otel_meter(self) -> None:
        from apic_vibe_portal_bff.telemetry.metrics import get_meter

        meter = get_meter()
        # Should be an OTel Meter (no-op implementation in tests)
        assert meter is not None

    def test_get_meter_is_cached(self) -> None:
        from apic_vibe_portal_bff.telemetry.metrics import get_meter

        m1 = get_meter()
        m2 = get_meter()
        assert m1 is m2

    @pytest.mark.parametrize(
        "factory_name, expected_name, expected_unit, instrument_type",
        [
            ("get_api_center_requests_histogram", "apic.api_center.requests", "ms", "histogram"),
            ("get_search_queries_histogram", "apic.search.queries", "ms", "histogram"),
            ("get_chat_messages_counter", "apic.chat.messages", "{message}", "counter"),
            ("get_chat_latency_histogram", "apic.chat.latency", "ms", "histogram"),
            ("get_cache_lookups_counter", "apic.cache.lookups", "{lookup}", "counter"),
            ("get_auth_failures_counter", "apic.auth.failures", "{failure}", "counter"),
            ("get_agent_invocations_counter", "apic.agent.invocations", "{invocation}", "counter"),
            ("get_tokens_estimated_histogram", "apic.llm.tokens.estimated", "{token}", "histogram"),
            ("get_tokens_prompt_histogram", "apic.llm.tokens.prompt", "{token}", "histogram"),
            ("get_tokens_completion_histogram", "apic.llm.tokens.completion", "{token}", "histogram"),
            ("get_tokens_total_histogram", "apic.llm.tokens.total", "{token}", "histogram"),
            ("get_cost_estimated_histogram", "apic.llm.cost.estimated", "USD", "histogram"),
            ("get_cosmos_ru_histogram", "apic.cosmos.ru_cost", "{RU}", "histogram"),
        ],
    )
    def test_instrument_factory_uses_correct_name_and_unit(
        self, factory_name: str, expected_name: str, expected_unit: str, instrument_type: str
    ) -> None:
        import apic_vibe_portal_bff.telemetry.metrics as m

        mock_meter = _make_mock_meter()
        m._meter = mock_meter

        import importlib

        mod = importlib.import_module("apic_vibe_portal_bff.telemetry.metrics")
        factory = getattr(mod, factory_name)
        factory()

        create_fn = getattr(mock_meter, f"create_{instrument_type}")
        create_fn.assert_called_once()
        call_kwargs = create_fn.call_args
        # name may be positional or keyword
        args, kwargs = call_kwargs
        all_kwargs = {**kwargs}
        if args:
            all_kwargs["name"] = args[0]
        assert all_kwargs.get("name") == expected_name
        assert all_kwargs.get("unit") == expected_unit

    def test_search_histogram_records_with_attributes(self) -> None:
        import apic_vibe_portal_bff.telemetry.metrics as m

        mock_meter = _make_mock_meter()
        m._meter = mock_meter
        mock_histogram = MagicMock()
        mock_meter.create_histogram.return_value = mock_histogram

        from apic_vibe_portal_bff.telemetry.metrics import get_search_queries_histogram

        hist = get_search_queries_histogram()
        attrs = {"query_type": "semantic", "result_count": 10, "status_code": 200}
        hist.record(42, attrs)
        mock_histogram.record.assert_called_once_with(42, attrs)

    def test_cache_lookups_counter_records_hit(self) -> None:
        import apic_vibe_portal_bff.telemetry.metrics as m

        mock_meter = _make_mock_meter()
        m._meter = mock_meter
        mock_counter = MagicMock()
        mock_meter.create_counter.return_value = mock_counter

        from apic_vibe_portal_bff.telemetry.metrics import get_cache_lookups_counter

        counter = get_cache_lookups_counter()
        counter.add(1, {"hit": True})
        mock_counter.add.assert_called_once_with(1, {"hit": True})

    def test_auth_failures_counter_records_reason(self) -> None:
        import apic_vibe_portal_bff.telemetry.metrics as m

        mock_meter = _make_mock_meter()
        m._meter = mock_meter
        mock_counter = MagicMock()
        mock_meter.create_counter.return_value = mock_counter

        from apic_vibe_portal_bff.telemetry.metrics import get_auth_failures_counter

        counter = get_auth_failures_counter()
        counter.add(1, {"reason": "expired_token"})
        mock_counter.add.assert_called_once_with(1, {"reason": "expired_token"})

    def test_agent_invocations_counter_records_type_and_status(self) -> None:
        import apic_vibe_portal_bff.telemetry.metrics as m

        mock_meter = _make_mock_meter()
        m._meter = mock_meter
        mock_counter = MagicMock()
        mock_meter.create_counter.return_value = mock_counter

        from apic_vibe_portal_bff.telemetry.metrics import get_agent_invocations_counter

        counter = get_agent_invocations_counter()
        counter.add(1, {"agent_type": "search", "status": "success"})
        mock_counter.add.assert_called_once_with(1, {"agent_type": "search", "status": "success"})

    def test_instrument_is_cached_and_not_recreated_on_second_call(self) -> None:
        """Second call to the same factory must return the cached instrument."""
        import apic_vibe_portal_bff.telemetry.metrics as m

        mock_meter = _make_mock_meter()
        m._meter = mock_meter

        from apic_vibe_portal_bff.telemetry.metrics import get_search_queries_histogram

        inst1 = get_search_queries_histogram()
        inst2 = get_search_queries_histogram()

        # The underlying meter should only be called once — caching prevents duplication
        mock_meter.create_histogram.assert_called_once()
        assert inst1 is inst2


# ---------------------------------------------------------------------------
# Tests — OTelEnrichmentMiddleware
# ---------------------------------------------------------------------------


class TestOTelEnrichmentMiddleware:
    """Verify route template, trace-id header, and ctx.is_valid guard."""

    @pytest.mark.asyncio
    async def test_http_route_uses_route_template(self) -> None:
        """http.route should be the matched route template, not the concrete path."""
        from fastapi import FastAPI
        from httpx import ASGITransport, AsyncClient
        from opentelemetry.sdk.trace import TracerProvider
        from opentelemetry.sdk.trace.export import SimpleSpanProcessor
        from opentelemetry.sdk.trace.export.in_memory_span_exporter import InMemorySpanExporter

        from apic_vibe_portal_bff.telemetry.middleware import OTelEnrichmentMiddleware

        exporter = InMemorySpanExporter()
        provider = TracerProvider()
        provider.add_span_processor(SimpleSpanProcessor(exporter))

        app = FastAPI()
        app.add_middleware(OTelEnrichmentMiddleware)

        @app.get("/items/{item_id}")
        async def get_item(item_id: str):
            return {"item_id": item_id}

        # Manually start a span so the middleware can record into it
        tracer = provider.get_tracer("test")
        with tracer.start_as_current_span("test-span"):
            async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
                response = await client.get("/items/abc123")

        assert response.status_code == 200

        spans = exporter.get_finished_spans()
        # Find the test span and verify http.route is the template, not the concrete path
        test_span = next(s for s in spans if s.name == "test-span")
        route_attr = test_span.attributes.get("http.route", "")
        # Should be the template (/items/{item_id}), NOT /items/abc123
        assert route_attr == "/items/{item_id}", f"Expected template, got: {route_attr!r}"

    @pytest.mark.asyncio
    async def test_x_trace_id_header_not_set_for_invalid_context(self) -> None:
        """X-Trace-ID must not appear when the span context is invalid (non-recording span)."""
        from fastapi import FastAPI
        from httpx import ASGITransport, AsyncClient

        from apic_vibe_portal_bff.telemetry.middleware import OTelEnrichmentMiddleware

        app = FastAPI()
        app.add_middleware(OTelEnrichmentMiddleware)

        @app.get("/ping")
        async def ping():
            return {"ok": True}

        # No active span — the current span is non-recording (invalid context)
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            response = await client.get("/ping")

        assert response.status_code == 200
        # Without a valid span context, no X-Trace-ID header should be added
        assert "x-trace-id" not in response.headers
