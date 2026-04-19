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
        """Reset the module-level meter cache before each test."""
        import apic_vibe_portal_bff.telemetry.metrics as m

        m._meter = None

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
