"""Unit tests for the analytics service."""

from __future__ import annotations

import re
from unittest.mock import MagicMock, patch

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


# ---------------------------------------------------------------------------
# AnalyticsService Cosmos DB persistence
# ---------------------------------------------------------------------------


def _make_mock_repo() -> MagicMock:
    """Return a mock AnalyticsRepository."""
    return MagicMock()


class TestAnalyticsServiceCosmosPersistence:
    def test_does_not_call_repository_when_none(self) -> None:
        service = AnalyticsService()  # no repository
        result = service.record_events([_make_envelope("page_view")])
        assert result == 1  # should not raise

    def test_persists_event_to_repository(self) -> None:
        repo = _make_mock_repo()
        service = AnalyticsService(repository=repo)
        service.record_events([_make_envelope("page_view")])
        assert repo.create.call_count == 1

    def test_persists_all_events_in_batch(self) -> None:
        repo = _make_mock_repo()
        service = AnalyticsService(repository=repo)
        service.record_events([_make_envelope("page_view"), _make_envelope("api_view")])
        assert repo.create.call_count == 2

    def test_persisted_document_has_correct_event_type(self) -> None:
        repo = _make_mock_repo()
        service = AnalyticsService(repository=repo)
        service.record_events([_make_envelope("api_view")])
        doc = repo.create.call_args[0][0]
        assert doc["eventType"] == "api_view"

    def test_persisted_document_has_api_id_field(self) -> None:
        repo = _make_mock_repo()
        service = AnalyticsService(repository=repo)
        service.record_events([_make_envelope("api_view", apiId="payments-api")])
        doc = repo.create.call_args[0][0]
        assert doc["apiId"] == "payments-api"

    def test_persisted_document_has_hashed_user_id(self) -> None:
        repo = _make_mock_repo()
        service = AnalyticsService(repository=repo)
        user = _make_user("oid-xyz")
        service.record_events([_make_envelope("page_view")], user=user)
        doc = repo.create.call_args[0][0]
        assert doc["userId"] != ""
        assert "oid-xyz" not in doc["userId"]  # raw OID must never be stored

    def test_persisted_document_has_empty_user_id_when_no_user(self) -> None:
        repo = _make_mock_repo()
        service = AnalyticsService(repository=repo)
        service.record_events([_make_envelope("page_view")], user=None)
        doc = repo.create.call_args[0][0]
        assert doc["userId"] == ""

    def test_persisted_document_has_unique_ids(self) -> None:
        repo = _make_mock_repo()
        service = AnalyticsService(repository=repo)
        service.record_events([_make_envelope("page_view"), _make_envelope("page_view")])
        ids = [call[0][0]["id"] for call in repo.create.call_args_list]
        assert ids[0] != ids[1]

    def test_persisted_document_has_timestamp(self) -> None:
        repo = _make_mock_repo()
        service = AnalyticsService(repository=repo)
        service.record_events([_make_envelope("page_view")])
        doc = repo.create.call_args[0][0]
        assert "timestamp" in doc
        assert doc["timestamp"].endswith("Z")

    def test_repository_failure_does_not_prevent_logging(self) -> None:
        repo = _make_mock_repo()
        repo.create.side_effect = RuntimeError("Cosmos unavailable")
        service = AnalyticsService(repository=repo)
        # Enrichment succeeds, persistence failure is logged but doesn't affect
        # the accepted count — events are "accepted" at enrichment time.
        result = service.record_events([_make_envelope("page_view")])
        assert result == 1


# ---------------------------------------------------------------------------
# AnalyticsService — Service Bus path
# ---------------------------------------------------------------------------


def _make_mock_sb_sender() -> MagicMock:
    """Return a mock ServiceBusSender with a mock batch."""
    sender = MagicMock()
    batch = MagicMock()
    batch.__len__ = MagicMock(return_value=1)
    sender.create_message_batch.return_value = batch
    return sender


class TestAnalyticsServiceServiceBus:
    def test_sends_events_to_service_bus_when_configured(self) -> None:
        sb_sender = _make_mock_sb_sender()
        service = AnalyticsService(service_bus_sender=sb_sender)
        result = service.record_events([_make_envelope("page_view")])
        assert result == 1
        sb_sender.send_messages.assert_called_once()

    def test_sends_batch_to_service_bus(self) -> None:
        sb_sender = _make_mock_sb_sender()
        service = AnalyticsService(service_bus_sender=sb_sender)
        service.record_events([_make_envelope("page_view"), _make_envelope("api_view")])
        sb_sender.send_messages.assert_called_once()

    def test_message_has_event_type_application_property(self) -> None:
        sb_sender = _make_mock_sb_sender()
        service = AnalyticsService(service_bus_sender=sb_sender)
        service.record_events([_make_envelope("api_view")])
        # The batch.add_message call receives a ServiceBusMessage
        batch = sb_sender.create_message_batch.return_value
        msg = batch.add_message.call_args[0][0]
        assert msg.application_properties["eventType"] == "api_view"

    def test_falls_back_to_cosmos_on_sb_failure(self) -> None:
        sb_sender = _make_mock_sb_sender()
        sb_sender.create_message_batch.side_effect = RuntimeError("SB down")
        repo = _make_mock_repo()
        service = AnalyticsService(repository=repo, service_bus_sender=sb_sender)
        result = service.record_events([_make_envelope("page_view")])
        assert result == 1
        # Should have fallen back to Cosmos
        assert repo.create.call_count == 1

    def test_sb_preferred_over_cosmos_when_both_configured(self) -> None:
        sb_sender = _make_mock_sb_sender()
        repo = _make_mock_repo()
        service = AnalyticsService(repository=repo, service_bus_sender=sb_sender)
        service.record_events([_make_envelope("page_view")])
        # SB should be used, NOT Cosmos
        sb_sender.send_messages.assert_called_once()
        repo.create.assert_not_called()

    def test_no_sb_no_repo_still_logs(self) -> None:
        service = AnalyticsService()
        result = service.record_events([_make_envelope("page_view")])
        assert result == 1

    def test_falls_back_to_cosmos_when_single_message_exceeds_sb_max_size(self) -> None:
        """When a message is too large for even an empty SB batch, the retry
        add_message also raises ValueError. This should propagate to
        _persist_events and trigger the Cosmos fallback."""
        sb_sender = _make_mock_sb_sender()
        batch = sb_sender.create_message_batch.return_value
        # First add_message fails (message oversized), retry also fails
        batch.add_message.side_effect = ValueError("Message too large")
        repo = _make_mock_repo()
        service = AnalyticsService(repository=repo, service_bus_sender=sb_sender)
        result = service.record_events([_make_envelope("page_view")])
        assert result == 1
        # Should have fallen back to Cosmos
        assert repo.create.call_count == 1
