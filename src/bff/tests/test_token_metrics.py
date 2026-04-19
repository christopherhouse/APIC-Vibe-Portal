"""Tests for token metrics helpers (token_metrics.py).

Verifies tiktoken-based estimation, actual usage recording, cost calculation,
and drift logging.
"""

from __future__ import annotations

import logging
from unittest.mock import MagicMock, patch


class TestEstimateTokens:
    """Unit tests for ``estimate_tokens``."""

    def test_returns_positive_integer_for_nonempty_text(self) -> None:
        from apic_vibe_portal_bff.telemetry.token_metrics import estimate_tokens

        result = estimate_tokens("Hello, world!", model="gpt-4o")
        assert isinstance(result, int)
        assert result > 0

    def test_falls_back_gracefully_when_tiktoken_raises(self) -> None:
        from apic_vibe_portal_bff.telemetry.token_metrics import estimate_tokens

        with patch("tiktoken.encoding_for_model", side_effect=Exception("boom")):
            with patch("tiktoken.get_encoding", side_effect=Exception("boom")):
                result = estimate_tokens("Hello world", model="gpt-4o")
        # fallback: len("Hello world") // 4 = 2
        assert result >= 1

    def test_returns_at_least_one_for_very_short_text(self) -> None:
        from apic_vibe_portal_bff.telemetry.token_metrics import estimate_tokens

        assert estimate_tokens("a") >= 1

    def test_longer_text_produces_more_tokens(self) -> None:
        from apic_vibe_portal_bff.telemetry.token_metrics import estimate_tokens

        short = estimate_tokens("Hi", model="gpt-4o")
        long = estimate_tokens("Hi " * 100, model="gpt-4o")
        assert long > short

    def test_unknown_model_uses_cl100k_base(self) -> None:
        from apic_vibe_portal_bff.telemetry.token_metrics import estimate_tokens

        result = estimate_tokens("test text", model="unknown-model-xyz")
        assert result > 0


class TestRecordEstimatedTokens:
    """Unit tests for ``record_estimated_tokens``."""

    def setup_method(self) -> None:
        import apic_vibe_portal_bff.telemetry.metrics as m

        m._meter = None
        m._instruments.clear()

    def test_records_to_estimated_histogram(self) -> None:
        import apic_vibe_portal_bff.telemetry.metrics as m

        mock_meter = MagicMock()
        mock_hist = MagicMock()
        mock_meter.create_histogram.return_value = mock_hist
        m._meter = mock_meter

        from apic_vibe_portal_bff.telemetry.token_metrics import record_estimated_tokens

        record_estimated_tokens(100, model="gpt-4o", component="system_prompt")
        mock_hist.record.assert_called_once_with(100, {"model": "gpt-4o", "component": "system_prompt"})

    def test_default_component_is_total(self) -> None:
        import apic_vibe_portal_bff.telemetry.metrics as m

        mock_meter = MagicMock()
        mock_hist = MagicMock()
        mock_meter.create_histogram.return_value = mock_hist
        m._meter = mock_meter

        from apic_vibe_portal_bff.telemetry.token_metrics import record_estimated_tokens

        record_estimated_tokens(50, model="gpt-4o-mini")
        mock_hist.record.assert_called_once_with(50, {"model": "gpt-4o-mini", "component": "total"})


class TestRecordActualTokenUsage:
    """Unit tests for ``record_actual_token_usage``."""

    def setup_method(self) -> None:
        import apic_vibe_portal_bff.telemetry.metrics as m

        m._meter = None
        m._instruments.clear()

    def _make_usage(self, prompt: int = 100, completion: int = 50, total: int | None = None) -> MagicMock:
        usage = MagicMock()
        usage.prompt_tokens = prompt
        usage.completion_tokens = completion
        usage.total_tokens = total if total is not None else (prompt + completion)
        return usage

    def _setup_mock_meter(self) -> tuple[MagicMock, dict[str, MagicMock]]:
        import apic_vibe_portal_bff.telemetry.metrics as m

        mock_meter = MagicMock()
        hists: dict[str, MagicMock] = {}

        def _create_hist(*args: object, **kwargs: object) -> MagicMock:
            name = args[0] if args else kwargs.get("name", "")
            h = MagicMock()
            hists[str(name)] = h
            return h

        mock_meter.create_histogram.side_effect = _create_hist
        mock_meter.create_counter.return_value = MagicMock()
        m._meter = mock_meter
        return mock_meter, hists

    def test_emits_prompt_completion_total_histograms(self) -> None:
        _, hists = self._setup_mock_meter()
        usage = self._make_usage(prompt=100, completion=50, total=150)

        from apic_vibe_portal_bff.telemetry.token_metrics import record_actual_token_usage

        record_actual_token_usage(usage, model="gpt-4o")

        assert "apic.llm.tokens.prompt" in hists
        assert "apic.llm.tokens.completion" in hists
        assert "apic.llm.tokens.total" in hists
        hists["apic.llm.tokens.prompt"].record.assert_called_once_with(100, {"model": "gpt-4o"})
        hists["apic.llm.tokens.completion"].record.assert_called_once_with(50, {"model": "gpt-4o"})
        hists["apic.llm.tokens.total"].record.assert_called_once_with(150, {"model": "gpt-4o"})

    def test_emits_cost_histogram(self) -> None:
        _, hists = self._setup_mock_meter()
        usage = self._make_usage(prompt=1000, completion=500, total=1500)

        from apic_vibe_portal_bff.telemetry.token_metrics import record_actual_token_usage

        record_actual_token_usage(usage, model="gpt-4o")

        assert "apic.llm.cost.estimated" in hists
        cost_call = hists["apic.llm.cost.estimated"].record.call_args
        cost_value = cost_call[0][0]
        assert cost_value > 0

    def test_cost_calculation_gpt4o_mini(self) -> None:
        _, hists = self._setup_mock_meter()
        usage = self._make_usage(prompt=1000, completion=1000, total=2000)

        from apic_vibe_portal_bff.telemetry.token_metrics import record_actual_token_usage

        record_actual_token_usage(usage, model="gpt-4o-mini")

        cost_call = hists["apic.llm.cost.estimated"].record.call_args
        cost_value = cost_call[0][0]
        expected = (1000 * 0.00015 + 1000 * 0.0006) / 1000.0
        assert abs(cost_value - expected) < 1e-9

    def test_drift_warning_logged_when_over_10_percent(self, caplog: object) -> None:
        self._setup_mock_meter()
        usage = self._make_usage(prompt=100, completion=50, total=150)

        from apic_vibe_portal_bff.telemetry.token_metrics import record_actual_token_usage

        with caplog.at_level(logging.WARNING, logger="apic_vibe_portal_bff.telemetry.token_metrics"):  # type: ignore[attr-defined]
            record_actual_token_usage(usage, model="gpt-4o", estimated_total=200)

        assert any("drift" in r.message.lower() or "drift" in r.getMessage().lower() for r in caplog.records)  # type: ignore[attr-defined]

    def test_no_drift_warning_when_within_10_percent(self, caplog: object) -> None:
        self._setup_mock_meter()
        usage = self._make_usage(prompt=100, completion=50, total=150)

        from apic_vibe_portal_bff.telemetry.token_metrics import record_actual_token_usage

        with caplog.at_level(logging.WARNING, logger="apic_vibe_portal_bff.telemetry.token_metrics"):  # type: ignore[attr-defined]
            record_actual_token_usage(usage, model="gpt-4o", estimated_total=155)

        assert not any("drift" in r.getMessage().lower() for r in caplog.records)  # type: ignore[attr-defined]

    def test_no_drift_check_when_estimated_not_provided(self, caplog: object) -> None:
        self._setup_mock_meter()
        usage = self._make_usage()

        from apic_vibe_portal_bff.telemetry.token_metrics import record_actual_token_usage

        with caplog.at_level(logging.WARNING, logger="apic_vibe_portal_bff.telemetry.token_metrics"):  # type: ignore[attr-defined]
            record_actual_token_usage(usage, model="gpt-4o")

        assert not any("drift" in r.getMessage().lower() for r in caplog.records)  # type: ignore[attr-defined]

    def test_handles_none_usage_fields_gracefully(self) -> None:
        self._setup_mock_meter()
        usage = MagicMock()
        usage.prompt_tokens = None
        usage.completion_tokens = None
        usage.total_tokens = None

        from apic_vibe_portal_bff.telemetry.token_metrics import record_actual_token_usage

        record_actual_token_usage(usage, model="gpt-4o")
