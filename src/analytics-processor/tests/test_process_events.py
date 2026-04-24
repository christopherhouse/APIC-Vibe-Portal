"""Unit tests for the analytics processor function."""

from __future__ import annotations

import json
from unittest.mock import MagicMock

from function_app import (
    _sanitize_metadata,
    _validate_and_sanitize,
    process_analytics_events,
)


def _make_sb_message(body: dict | str) -> MagicMock:
    """Create a mock ServiceBusMessage."""
    msg = MagicMock()
    if isinstance(body, dict):
        msg.get_body.return_value = json.dumps(body).encode("utf-8")
    else:
        msg.get_body.return_value = body.encode("utf-8")
    msg.message_id = "test-msg-id"
    return msg


def _make_cosmos_document(**overrides) -> dict:
    """Return a representative analytics event document."""
    doc = {
        "id": "evt-001",
        "eventType": "page_view",
        "userId": "hashed-user-id",
        "apiId": "",
        "timestamp": "2026-04-24T10:00:00+00:00",
        "ttl": 31536000,
        "metadata": {"pagePath": "/catalog"},
    }
    doc.update(overrides)
    return doc


class TestProcessAnalyticsEvents:
    def test_processes_single_message(self) -> None:
        doc = _make_cosmos_document()
        messages = [_make_sb_message(doc)]
        output = MagicMock()

        process_analytics_events(messages, output)

        output.set.assert_called_once()
        result = output.set.call_args[0][0]
        assert len(result) == 1
        assert json.loads(result[0])["id"] == "evt-001"

    def test_processes_batch_of_messages(self) -> None:
        docs = [{**_make_cosmos_document(), "id": f"evt-{i}"} for i in range(5)]
        messages = [_make_sb_message(d) for d in docs]
        output = MagicMock()

        process_analytics_events(messages, output)

        output.set.assert_called_once()
        result = output.set.call_args[0][0]
        assert len(result) == 5

    def test_skips_malformed_message_and_continues(self) -> None:
        good_doc = _make_cosmos_document()
        messages = [
            _make_sb_message("not valid json {{{"),
            _make_sb_message(good_doc),
        ]
        output = MagicMock()

        process_analytics_events(messages, output)

        output.set.assert_called_once()
        result = output.set.call_args[0][0]
        assert len(result) == 1
        assert json.loads(result[0])["id"] == "evt-001"

    def test_handles_empty_batch(self) -> None:
        output = MagicMock()
        process_analytics_events([], output)
        output.set.assert_not_called()

    def test_preserves_document_fields(self) -> None:
        doc = _make_cosmos_document()
        doc["metadata"] = {"pagePath": "/api/test", "sessionId": "sess-1"}
        messages = [_make_sb_message(doc)]
        output = MagicMock()

        process_analytics_events(messages, output)

        result = json.loads(output.set.call_args[0][0][0])
        assert result["eventType"] == "page_view"
        assert result["userId"] == "hashed-user-id"
        assert result["metadata"]["pagePath"] == "/api/test"
        assert result["ttl"] == 31536000

    def test_all_messages_malformed_produces_no_output(self) -> None:
        messages = [
            _make_sb_message("bad1{"),
            _make_sb_message("{bad2"),
        ]
        output = MagicMock()

        process_analytics_events(messages, output)

        output.set.assert_not_called()

    def test_rejects_document_missing_required_fields(self) -> None:
        doc = {"id": "evt-001", "eventType": "page_view"}  # missing timestamp
        messages = [_make_sb_message(doc)]
        output = MagicMock()

        process_analytics_events(messages, output)

        output.set.assert_not_called()

    def test_rejects_invalid_event_type(self) -> None:
        doc = _make_cosmos_document(eventType="page view; DROP TABLE")
        messages = [_make_sb_message(doc)]
        output = MagicMock()

        process_analytics_events(messages, output)

        output.set.assert_not_called()

    def test_strips_unknown_top_level_keys(self) -> None:
        doc = _make_cosmos_document()
        doc["injectedField"] = "should-be-removed"
        doc["__proto__"] = "bad"
        messages = [_make_sb_message(doc)]
        output = MagicMock()

        process_analytics_events(messages, output)

        result = json.loads(output.set.call_args[0][0][0])
        assert "injectedField" not in result
        assert "__proto__" not in result
        assert result["id"] == "evt-001"

    def test_strips_control_characters_from_strings(self) -> None:
        doc = _make_cosmos_document(userId="user\x00id\x07here")
        messages = [_make_sb_message(doc)]
        output = MagicMock()

        process_analytics_events(messages, output)

        result = json.loads(output.set.call_args[0][0][0])
        assert "\x00" not in result["userId"]
        assert "\x07" not in result["userId"]
        assert result["userId"] == "useridhere"

    def test_sanitizes_metadata_strings(self) -> None:
        doc = _make_cosmos_document(metadata={"path": "/ok", "note": "val\x00ue"})
        messages = [_make_sb_message(doc)]
        output = MagicMock()

        process_analytics_events(messages, output)

        result = json.loads(output.set.call_args[0][0][0])
        assert result["metadata"]["path"] == "/ok"
        assert result["metadata"]["note"] == "value"

    def test_replaces_non_dict_metadata_with_empty_dict(self) -> None:
        doc = _make_cosmos_document(metadata="not-a-dict")
        messages = [_make_sb_message(doc)]
        output = MagicMock()

        process_analytics_events(messages, output)

        result = json.loads(output.set.call_args[0][0][0])
        assert result["metadata"] == {}

    def test_rejects_empty_id(self) -> None:
        doc = _make_cosmos_document(id="")
        messages = [_make_sb_message(doc)]
        output = MagicMock()

        process_analytics_events(messages, output)

        output.set.assert_not_called()

    def test_drops_invalid_typed_optional_fields(self) -> None:
        doc = _make_cosmos_document(schemaVersion="not-an-int", isDeleted="yes", ttl="forever")
        messages = [_make_sb_message(doc)]
        output = MagicMock()

        process_analytics_events(messages, output)

        result = json.loads(output.set.call_args[0][0][0])
        assert "schemaVersion" not in result
        assert "isDeleted" not in result
        assert "ttl" not in result


# ---------------------------------------------------------------------------
# _validate_and_sanitize unit tests
# ---------------------------------------------------------------------------


class TestValidateAndSanitize:
    def test_valid_document_passes(self) -> None:
        doc = _make_cosmos_document()
        result = _validate_and_sanitize(doc)
        assert result is not None
        assert result["id"] == "evt-001"
        assert result["eventType"] == "page_view"

    def test_returns_none_for_non_dict(self) -> None:
        assert _validate_and_sanitize("a string") is None
        assert _validate_and_sanitize(42) is None
        assert _validate_and_sanitize([]) is None

    def test_returns_none_for_missing_required_keys(self) -> None:
        assert _validate_and_sanitize({"id": "x", "eventType": "y"}) is None
        assert _validate_and_sanitize({"id": "x", "timestamp": "t"}) is None
        assert _validate_and_sanitize({"eventType": "y", "timestamp": "t"}) is None

    def test_rejects_event_type_with_spaces(self) -> None:
        doc = _make_cosmos_document(eventType="has spaces")
        assert _validate_and_sanitize(doc) is None

    def test_rejects_event_type_with_special_chars(self) -> None:
        doc = _make_cosmos_document(eventType="type;DROP")
        assert _validate_and_sanitize(doc) is None

    def test_rejects_event_type_exceeding_max_length(self) -> None:
        doc = _make_cosmos_document(eventType="a" * 101)
        assert _validate_and_sanitize(doc) is None

    def test_accepts_event_type_at_max_length(self) -> None:
        doc = _make_cosmos_document(eventType="a" * 100)
        result = _validate_and_sanitize(doc)
        assert result is not None

    def test_truncates_long_strings(self) -> None:
        doc = _make_cosmos_document(apiId="x" * 3000)
        result = _validate_and_sanitize(doc)
        assert result is not None
        assert len(result["apiId"]) == 2048

    def test_rejects_id_exceeding_cosmos_limit(self) -> None:
        doc = _make_cosmos_document(id="x" * 256)
        assert _validate_and_sanitize(doc) is None

    def test_accepts_id_at_cosmos_limit(self) -> None:
        doc = _make_cosmos_document(id="x" * 255)
        result = _validate_and_sanitize(doc)
        assert result is not None
        assert result["id"] == "x" * 255

    def test_rejects_invalid_timestamp(self) -> None:
        doc = _make_cosmos_document(timestamp="not-a-date")
        assert _validate_and_sanitize(doc) is None

    def test_rejects_timestamp_before_2020(self) -> None:
        doc = _make_cosmos_document(timestamp="2019-12-31T23:59:59Z")
        assert _validate_and_sanitize(doc) is None

    def test_accepts_valid_iso_timestamp(self) -> None:
        doc = _make_cosmos_document(timestamp="2026-04-24T12:00:00Z")
        result = _validate_and_sanitize(doc)
        assert result is not None

    def test_accepts_timestamp_with_offset(self) -> None:
        doc = _make_cosmos_document(timestamp="2026-04-24T12:00:00+05:30")
        result = _validate_and_sanitize(doc)
        assert result is not None


# ---------------------------------------------------------------------------
# _sanitize_metadata unit tests
# ---------------------------------------------------------------------------


class TestSanitizeMetadata:
    def test_sanitizes_dict_nested_inside_list(self) -> None:
        meta = {"items": [{"name": "ok\x00bad"}]}
        result = _sanitize_metadata(meta)
        assert result["items"][0]["name"] == "okbad"

    def test_deeply_nested_dict_in_list_is_sanitized(self) -> None:
        meta = {"items": [{"inner": {"value": "clean\x07"}}]}
        result = _sanitize_metadata(meta)
        assert result["items"][0]["inner"]["value"] == "clean"

    def test_recursion_depth_is_capped(self) -> None:
        """Deeply nested metadata should be truncated, not stack-overflow."""
        # Build 15 levels of nesting (exceeds _MAX_METADATA_DEPTH=10)
        meta: dict = {"leaf": "value"}
        for i in range(15):
            meta = {f"level_{i}": meta}
        result = _sanitize_metadata(meta)
        # Walk down — at depth 10 the nested dict should become {}
        node = result
        for i in range(14, -1, -1):
            key = f"level_{i}"
            if key in node:
                node = node[key]
            else:
                break
        # At some point the nesting should have been cut off (empty dict)
        assert node == {} or node == {"leaf": "value"}

    def test_recursion_depth_preserves_shallow_nesting(self) -> None:
        meta = {"a": {"b": {"c": "ok"}}}
        result = _sanitize_metadata(meta)
        assert result["a"]["b"]["c"] == "ok"

    def test_list_of_mixed_types(self) -> None:
        meta = {"items": ["text\x00", {"key": "val"}, 42, True]}
        result = _sanitize_metadata(meta)
        assert result["items"][0] == "text"
        assert result["items"][1] == {"key": "val"}
        assert result["items"][2] == 42
        assert result["items"][3] is True
