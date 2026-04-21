"""Unit tests for the analytics service."""

from __future__ import annotations

import re
from unittest.mock import patch

from apic_vibe_portal_bff.middleware.auth import AuthenticatedUser
from apic_vibe_portal_bff.services.analytics_service import (
    AnalyticsService,
    hash_user_id,
    sanitize_event_metadata,
)

# ---------------------------------------------------------------------------
# hash_user_id
# ---------------------------------------------------------------------------


class TestHashUserId:
    def test_returns_64_char_hex_string(self) -> None:
        result = hash_user_id("user-abc-123")
        assert isinstance(result, str)
        assert len(result) == 64
        assert re.fullmatch(r"[0-9a-f]{64}", result) is not None

    def test_same_input_produces_same_hash(self) -> None:
        assert hash_user_id("abc") == hash_user_id("abc")

    def test_different_inputs_produce_different_hashes(self) -> None:
        assert hash_user_id("user-1") != hash_user_id("user-2")

    def test_salt_changes_hash(self) -> None:
        without_salt = hash_user_id("user-1", salt="")
        with_salt = hash_user_id("user-1", salt="mysecret")
        assert without_salt != with_salt

    def test_empty_string_returns_hash(self) -> None:
        result = hash_user_id("")
        assert len(result) == 64


# ---------------------------------------------------------------------------
# sanitize_event_metadata
# ---------------------------------------------------------------------------


class TestSanitizeEventMetadata:
    def test_redacts_email_values(self) -> None:
        result = sanitize_event_metadata({"query": "hello user@example.com world"})
        assert result["query"] == "<redacted>"

    def test_redacts_phone_numbers(self) -> None:
        result = sanitize_event_metadata({"note": "call me at 555-867-5309"})
        assert result["note"] == "<redacted>"

    def test_leaves_safe_strings_unchanged(self) -> None:
        result = sanitize_event_metadata({"apiId": "payments-api", "source": "search"})
        assert result == {"apiId": "payments-api", "source": "search"}

    def test_leaves_non_string_values_unchanged(self) -> None:
        result = sanitize_event_metadata({"count": 42, "active": True, "ratio": 0.5})
        assert result == {"count": 42, "active": True, "ratio": 0.5}

    def test_empty_dict_returns_empty_dict(self) -> None:
        assert sanitize_event_metadata({}) == {}

    def test_redacts_pii_in_nested_dict(self) -> None:
        result = sanitize_event_metadata({"meta": {"contact": "evil@hacker.io", "count": 5}})
        assert result["meta"]["contact"] == "<redacted>"
        assert result["meta"]["count"] == 5

    def test_redacts_pii_in_nested_list(self) -> None:
        result = sanitize_event_metadata({"notes": ["clean value", "bad@email.com", "also clean"]})
        assert result["notes"][0] == "clean value"
        assert result["notes"][1] == "<redacted>"
        assert result["notes"][2] == "also clean"

    def test_deep_nesting_is_sanitized(self) -> None:
        data = {"level1": {"level2": {"pii": "reach@me.com"}}}
        result = sanitize_event_metadata(data)
        assert result["level1"]["level2"]["pii"] == "<redacted>"


# ---------------------------------------------------------------------------
# AnalyticsService.record_events
# ---------------------------------------------------------------------------


def _make_user(oid: str = "test-oid") -> AuthenticatedUser:
    return AuthenticatedUser(oid=oid, name="Test User", email="test@example.com", roles=[])


def _make_envelope(event_type: str = "page_view", **extra) -> dict:
    return {
        "event": {"type": event_type, **extra},
        "clientTimestamp": "2026-04-21T12:00:00Z",
        "pagePath": "/catalog",
        "sessionId": "sess-abc",
    }


class TestAnalyticsServiceRecordEvents:
    def test_returns_count_of_recorded_events(self) -> None:
        service = AnalyticsService()
        envelopes = [_make_envelope("page_view"), _make_envelope("api_view", apiId="my-api", source="search")]
        result = service.record_events(envelopes)
        assert result == 2

    def test_returns_zero_for_empty_list(self) -> None:
        service = AnalyticsService()
        assert service.record_events([]) == 0

    def test_logs_each_event(self) -> None:
        service = AnalyticsService()
        with patch("apic_vibe_portal_bff.services.analytics_service.logger") as mock_logger:
            service.record_events([_make_envelope("page_view")])
            assert mock_logger.info.called
            call_args = mock_logger.info.call_args
            assert call_args[0][0] == "analytics.event"

    def test_includes_user_id_hash_when_user_provided(self) -> None:
        service = AnalyticsService()
        user = _make_user("oid-xyz")
        with patch("apic_vibe_portal_bff.services.analytics_service.logger") as mock_logger:
            service.record_events([_make_envelope("page_view")], user=user)
            call_kwargs = mock_logger.info.call_args[1]
            extra = call_kwargs.get("extra", {})
            assert "user_id_hash" in extra
            # The raw OID must never appear in the log
            assert "oid-xyz" not in str(extra.get("user_id_hash", ""))

    def test_does_not_include_user_id_when_no_user(self) -> None:
        service = AnalyticsService()
        with patch("apic_vibe_portal_bff.services.analytics_service.logger") as mock_logger:
            service.record_events([_make_envelope("page_view")], user=None)
            call_kwargs = mock_logger.info.call_args[1]
            extra = call_kwargs.get("extra", {})
            assert "user_id_hash" not in extra

    def test_skips_malformed_envelope_and_continues(self) -> None:
        service = AnalyticsService()
        bad_envelope = None  # type: ignore[assignment]
        good_envelope = _make_envelope("page_view")
        # Should not raise; malformed item is skipped, good item is recorded.
        result = service.record_events([bad_envelope, good_envelope])
        assert result == 1

    def test_sanitizes_pii_in_event_payload(self) -> None:
        service = AnalyticsService()
        envelope = _make_envelope(
            "search_query",
            queryHash="abc",
            queryLength=10,
            resultCount=5,
            displayTerm="user@example.com",
        )
        with patch("apic_vibe_portal_bff.services.analytics_service.logger") as mock_logger:
            service.record_events([envelope])
            call_kwargs = mock_logger.info.call_args[1]
            extra = call_kwargs.get("extra", {})
            # The raw email must be redacted
            assert extra.get("displayTerm") == "<redacted>"

    def test_records_session_id_when_present(self) -> None:
        service = AnalyticsService()
        with patch("apic_vibe_portal_bff.services.analytics_service.logger") as mock_logger:
            service.record_events([_make_envelope("page_view")])
            call_kwargs = mock_logger.info.call_args[1]
            extra = call_kwargs.get("extra", {})
            assert extra.get("session_id") == "sess-abc"

    def test_handles_missing_event_key_gracefully(self) -> None:
        service = AnalyticsService()
        envelope_no_event = {"clientTimestamp": "2026-04-21T12:00:00Z", "pagePath": "/"}
        result = service.record_events([envelope_no_event])
        assert result == 1
