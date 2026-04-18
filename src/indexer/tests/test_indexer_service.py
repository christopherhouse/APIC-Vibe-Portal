"""Unit tests for IndexerService — mocked data-plane client calls."""

from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import MagicMock, patch

from apic_client.exceptions import ApiCenterNotFoundError

from indexer.indexer_service import IndexerService, IndexStats

# ---------------------------------------------------------------------------
# Helpers / factories
# ---------------------------------------------------------------------------


def _ns(**kwargs: object) -> SimpleNamespace:
    return SimpleNamespace(**kwargs)


def make_api(
    name: str = "petstore-api",
    title: str = "Petstore API",
    description: str = "A sample pet store API",
    kind: str = "rest",
    lifecycle_stage: str = "production",
    custom_properties: dict[str, object] | None = None,
    contacts: list[dict[str, str]] | None = None,
    last_updated: str | None = "2024-03-20T14:30:00Z",
) -> dict[str, object]:
    """Build a mock data-plane API dict."""
    return {
        "name": name,
        "title": title,
        "description": description,
        "kind": kind,
        "lifecycleStage": lifecycle_stage,
        "customProperties": custom_properties or {"owner": "platform-team"},
        "contacts": contacts or [{"name": "API Team", "email": "api-team@example.com"}],
        "lastUpdated": last_updated,
    }


def make_upload_result(
    succeeded: bool = True,
    key: str | None = None,
    status_code: int | None = None,
    error_message: str | None = None,
) -> SimpleNamespace:
    return _ns(
        succeeded=succeeded,
        key=key,
        status_code=status_code,
        error_message=error_message,
    )


def _make_service() -> tuple[IndexerService, MagicMock, MagicMock, MagicMock, MagicMock]:
    """Return an IndexerService wired to mock data-plane client."""
    apic_client = MagicMock()
    search_index_client = MagicMock()
    search_client = MagicMock()
    embedding_service = MagicMock()

    # Default embedding response
    embedding_service.generate_embedding.return_value = [0.1] * 1536

    # Default: no existing chunk documents to clean up.
    search_client.search.return_value = iter([])

    service = IndexerService(
        apic_client=apic_client,
        search_index_client=search_index_client,
        search_client=search_client,
        embedding_service=embedding_service,
        index_name="apic-apis",
    )
    return service, apic_client, search_index_client, search_client, embedding_service


# ---------------------------------------------------------------------------
# ensure_index
# ---------------------------------------------------------------------------


class TestEnsureIndex:
    def test_calls_create_or_update_index(self) -> None:
        service, _, search_index_client, _, _ = _make_service()
        mock_schema = MagicMock()
        mock_schema.suggesters = []

        service.ensure_index(mock_schema)

        search_index_client.create_or_update_index.assert_called_once_with(mock_schema)

    def test_no_rebuild_when_suggesters_present(self) -> None:
        """When the live index already has the expected suggesters, no rebuild."""
        service, _, search_index_client, _, _ = _make_service()

        suggester = _ns(name="sg", source_fields=["apiName", "title"])
        mock_schema = MagicMock()
        mock_schema.suggesters = [suggester]

        # Live index has the suggester
        live_index = MagicMock()
        live_index.suggesters = [_ns(name="sg")]
        search_index_client.get_index.return_value = live_index

        service.ensure_index(mock_schema)

        search_index_client.delete_index.assert_not_called()
        search_index_client.create_or_update_index.assert_called_once_with(mock_schema)

    def test_rebuilds_index_when_suggesters_missing(self) -> None:
        """When the live index is missing suggesters, delete and recreate."""
        service, _, search_index_client, _, _ = _make_service()

        suggester = _ns(name="sg", source_fields=["apiName", "title"])
        mock_schema = MagicMock()
        mock_schema.suggesters = [suggester]

        # Live index has NO suggesters
        live_index = MagicMock()
        live_index.suggesters = []
        search_index_client.get_index.return_value = live_index

        service.ensure_index(mock_schema)

        search_index_client.delete_index.assert_called_once_with("apic-apis")
        # create_or_update_index called twice: initial + rebuild
        assert search_index_client.create_or_update_index.call_count == 2

    def test_rebuilds_when_suggesters_none_on_live_index(self) -> None:
        """Handles the case where the live index returns suggesters=None."""
        service, _, search_index_client, _, _ = _make_service()

        suggester = _ns(name="sg", source_fields=["apiName"])
        mock_schema = MagicMock()
        mock_schema.suggesters = [suggester]

        live_index = MagicMock()
        live_index.suggesters = None
        search_index_client.get_index.return_value = live_index

        service.ensure_index(mock_schema)

        search_index_client.delete_index.assert_called_once_with("apic-apis")
        assert search_index_client.create_or_update_index.call_count == 2

    def test_skips_reconciliation_when_schema_has_no_suggesters(self) -> None:
        """No get_index call when schema has no suggesters."""
        service, _, search_index_client, _, _ = _make_service()

        mock_schema = MagicMock()
        mock_schema.suggesters = []

        service.ensure_index(mock_schema)

        search_index_client.get_index.assert_not_called()
        search_index_client.delete_index.assert_not_called()


# ---------------------------------------------------------------------------
# full_reindex
# ---------------------------------------------------------------------------


class TestFullReindex:
    def test_returns_count_of_successfully_indexed_documents(self) -> None:
        service, apic_client, _, search_client, _ = _make_service()

        apis = [make_api(name="api-1"), make_api(name="api-2")]
        apic_client.list_apis.return_value = apis
        apic_client.list_api_versions.return_value = []
        search_client.upload_documents.return_value = [
            make_upload_result(True),
            make_upload_result(True),
        ]

        count = service.full_reindex()

        assert count == 2
        search_client.upload_documents.assert_called_once()

    def test_returns_zero_when_no_apis(self) -> None:
        service, apic_client, _, search_client, _ = _make_service()
        apic_client.list_apis.return_value = []

        count = service.full_reindex()

        assert count == 0
        search_client.upload_documents.assert_not_called()

    def test_document_contains_required_fields(self) -> None:
        service, apic_client, _, search_client, _ = _make_service()

        api = make_api(name="my-api", title="My API", description="My description")
        apic_client.list_apis.return_value = [api]
        apic_client.list_api_versions.return_value = []
        search_client.upload_documents.return_value = [make_upload_result(True)]

        service.full_reindex()

        uploaded = search_client.upload_documents.call_args.kwargs["documents"]
        doc = uploaded[0]
        assert doc["id"] == "my-api"
        assert doc["apiName"] == "my-api"
        assert doc["title"] == "My API"
        assert doc["description"] == "My description"
        assert doc["parentApiId"] == ""
        assert doc["chunkIndex"] == 0
        assert "contentVector" in doc
        assert len(doc["contentVector"]) == 1536

    def test_embeddings_generated_per_api(self) -> None:
        service, apic_client, _, search_client, embedding_service = _make_service()

        apis = [make_api(name="api-1"), make_api(name="api-2"), make_api(name="api-3")]
        apic_client.list_apis.return_value = apis
        apic_client.list_api_versions.return_value = []
        search_client.upload_documents.return_value = [make_upload_result(True)] * 3

        service.full_reindex()

        assert embedding_service.generate_embedding.call_count == 3

    def test_version_names_included_in_document(self) -> None:
        service, apic_client, _, search_client, _ = _make_service()

        api = make_api(name="my-api")
        apic_client.list_apis.return_value = [api]
        apic_client.list_api_versions.return_value = [
            {"name": "v1"},
            {"name": "v2"},
        ]
        # No definitions for simplicity
        apic_client.list_api_definitions.return_value = []
        search_client.upload_documents.return_value = [make_upload_result(True)]

        service.full_reindex()

        uploaded = search_client.upload_documents.call_args.kwargs["documents"]
        doc = uploaded[0]
        assert "v1" in doc["versions"]
        assert "v2" in doc["versions"]

    def test_partial_failures_counted_correctly(self) -> None:
        service, apic_client, _, search_client, _ = _make_service()

        apis = [make_api(name="api-1"), make_api(name="api-2")]
        apic_client.list_apis.return_value = apis
        apic_client.list_api_versions.return_value = []
        search_client.upload_documents.return_value = [
            make_upload_result(True),
            make_upload_result(False),
        ]

        count = service.full_reindex()

        assert count == 1

    def test_versions_fallback_to_empty_and_logs_warning_on_error(self) -> None:
        """Version list errors degrade gracefully and emit a warning."""
        service, apic_client, _, search_client, _ = _make_service()

        api = make_api(name="bad-api")
        apic_client.list_apis.return_value = [api]
        apic_client.list_api_versions.side_effect = RuntimeError("network error")
        search_client.upload_documents.return_value = [make_upload_result(True)]

        with patch("indexer.indexer_service.logger") as mock_logger:
            service.full_reindex()
            assert mock_logger.warning.call_count >= 1
            call_args_str = str(mock_logger.warning.call_args_list)
            assert "bad-api" in call_args_str

        # Document is still uploaded even when version fetch fails
        search_client.upload_documents.assert_called_once()

    def test_logs_per_document_failure_details(self) -> None:
        """When documents fail to upload, the warning includes per-doc details."""
        service, apic_client, _, search_client, _ = _make_service()

        apis = [make_api(name="ok-api"), make_api(name="bad-api")]
        apic_client.list_apis.return_value = apis
        apic_client.list_api_versions.return_value = []
        search_client.upload_documents.return_value = [
            make_upload_result(True, key="ok-api"),
            make_upload_result(
                False,
                key="bad-api",
                status_code=400,
                error_message="Invalid field 'foo'",
            ),
        ]

        with patch("indexer.indexer_service.logger") as mock_logger:
            count = service.full_reindex()

            assert count == 1
            assert mock_logger.warning.call_count >= 1
            # Find the warning call that contains failed_documents
            found = False
            for call in mock_logger.warning.call_args_list:
                kwargs = call.kwargs if call.kwargs else {}
                if "failed_documents" in kwargs:
                    details = kwargs["failed_documents"]
                    assert len(details) == 1
                    assert details[0]["key"] == "bad-api"
                    assert details[0]["status_code"] == 400
                    assert details[0]["error_message"] == "Invalid field 'foo'"
                    found = True
                    break
            assert found, "Expected a warning with failed_documents details"


# ---------------------------------------------------------------------------
# incremental_index
# ---------------------------------------------------------------------------


class TestIncrementalIndex:
    def test_returns_true_on_success(self) -> None:
        service, apic_client, _, search_client, _ = _make_service()

        api = make_api(name="petstore-api")
        apic_client.get_api.return_value = api
        apic_client.list_api_versions.return_value = []
        search_client.upload_documents.return_value = [make_upload_result(True)]

        result = service.incremental_index("petstore-api")

        assert result is True
        apic_client.get_api.assert_called_once_with("petstore-api")

    def test_returns_false_on_upload_failure(self) -> None:
        service, apic_client, _, search_client, _ = _make_service()

        api = make_api(name="petstore-api")
        apic_client.get_api.return_value = api
        apic_client.list_api_versions.return_value = []
        search_client.upload_documents.return_value = [make_upload_result(False)]

        result = service.incremental_index("petstore-api")

        assert result is False

    def test_logs_details_on_upload_failure(self) -> None:
        """When a single document fails, the warning includes failure details."""
        service, apic_client, _, search_client, _ = _make_service()

        api = make_api(name="bad-api")
        apic_client.get_api.return_value = api
        apic_client.list_api_versions.return_value = []
        search_client.upload_documents.return_value = [
            make_upload_result(
                False,
                key="bad-api",
                status_code=400,
                error_message="Document is malformed",
            ),
        ]

        with patch("indexer.indexer_service.logger") as mock_logger:
            result = service.incremental_index("bad-api")

            assert result is False
            assert mock_logger.warning.call_count >= 1
            # Find the warning call with the failure details
            found = False
            for call in mock_logger.warning.call_args_list:
                kwargs = call.kwargs if call.kwargs else {}
                if "failed_documents" in kwargs:
                    details = kwargs["failed_documents"]
                    assert len(details) == 1
                    assert details[0]["key"] == "bad-api"
                    assert details[0]["status_code"] == 400
                    assert details[0]["error_message"] == "Document is malformed"
                    found = True
                    break
            assert found, "Expected a warning with failed_documents details"

    def test_uploads_single_document(self) -> None:
        service, apic_client, _, search_client, _ = _make_service()

        api = make_api(name="petstore-api")
        apic_client.get_api.return_value = api
        apic_client.list_api_versions.return_value = []
        search_client.upload_documents.return_value = [make_upload_result(True)]

        service.incremental_index("petstore-api")

        uploaded = search_client.upload_documents.call_args.kwargs["documents"]
        assert len(uploaded) == 1
        assert uploaded[0]["id"] == "petstore-api"


# ---------------------------------------------------------------------------
# delete_from_index
# ---------------------------------------------------------------------------


class TestDeleteFromIndex:
    def test_returns_true_on_success(self) -> None:
        service, _, _, search_client, _ = _make_service()
        search_client.delete_documents.return_value = [make_upload_result(True)]

        result = service.delete_from_index("petstore-api")

        assert result is True
        search_client.delete_documents.assert_called_once_with(documents=[{"id": "petstore-api"}])

    def test_returns_false_on_failure(self) -> None:
        service, _, _, search_client, _ = _make_service()
        search_client.delete_documents.return_value = [make_upload_result(False)]

        result = service.delete_from_index("missing-api")

        assert result is False

    def test_handles_empty_result_list(self) -> None:
        service, _, _, search_client, _ = _make_service()
        search_client.delete_documents.return_value = []

        result = service.delete_from_index("any-api")

        assert result is False


# ---------------------------------------------------------------------------
# get_index_stats
# ---------------------------------------------------------------------------


class TestGetIndexStats:
    def test_returns_stats_with_document_count(self) -> None:
        service, _, search_index_client, _, _ = _make_service()
        search_index_client.get_index_statistics.return_value = _ns(document_count=42)

        stats = service.get_index_stats()

        assert isinstance(stats, IndexStats)
        assert stats.document_count == 42
        assert stats.index_name == "apic-apis"
        search_index_client.get_index_statistics.assert_called_once_with("apic-apis")


# ---------------------------------------------------------------------------
# _contact_to_str
# ---------------------------------------------------------------------------


class TestContactToStr:
    def test_formats_name_and_email_dict(self) -> None:
        contact = {"name": "Alice", "email": "alice@example.com"}
        result = IndexerService._contact_to_str(contact)
        assert result == "Alice <alice@example.com>"

    def test_email_only_dict(self) -> None:
        contact = {"name": "", "email": "alice@example.com"}
        result = IndexerService._contact_to_str(contact)
        assert result == "alice@example.com"

    def test_name_only_dict(self) -> None:
        contact = {"name": "Bob", "email": ""}
        result = IndexerService._contact_to_str(contact)
        assert result == "Bob"

    def test_empty_contact_dict(self) -> None:
        contact = {"name": "", "email": ""}
        result = IndexerService._contact_to_str(contact)
        assert result == ""

    def test_formats_name_and_email_object(self) -> None:
        contact = _ns(name="Alice", email="alice@example.com")
        result = IndexerService._contact_to_str(contact)
        assert result == "Alice <alice@example.com>"


# ---------------------------------------------------------------------------
# datetime timezone normalisation
# ---------------------------------------------------------------------------


class TestDatetimeTimezone:
    def test_last_updated_parsed_and_normalised(self) -> None:
        """lastUpdated ISO string is parsed into a timezone-aware datetime."""
        service, apic_client, _, search_client, _ = _make_service()

        api = make_api(name="tz-api", last_updated="2024-03-20T14:30:00Z")
        apic_client.list_apis.return_value = [api]
        apic_client.list_api_versions.return_value = []
        search_client.upload_documents.return_value = [make_upload_result(True)]

        service.full_reindex()

        uploaded = search_client.upload_documents.call_args.kwargs["documents"]
        doc = uploaded[0]
        assert "updatedAt" in doc
        assert doc["updatedAt"].tzinfo is not None

    def test_naive_last_updated_is_normalised_to_utc(self) -> None:
        """Naive datetime strings are normalized to UTC."""
        service, apic_client, _, search_client, _ = _make_service()

        api = make_api(name="naive-api", last_updated="2024-03-20T14:30:00")
        apic_client.list_apis.return_value = [api]
        apic_client.list_api_versions.return_value = []
        search_client.upload_documents.return_value = [make_upload_result(True)]

        service.full_reindex()

        uploaded = search_client.upload_documents.call_args.kwargs["documents"]
        doc = uploaded[0]
        assert "updatedAt" in doc
        assert doc["updatedAt"].tzinfo is not None

    def test_no_last_updated_omits_field(self) -> None:
        """When lastUpdated is None, updatedAt is not included."""
        service, apic_client, _, search_client, _ = _make_service()

        api = make_api(name="no-date-api", last_updated=None)
        apic_client.list_apis.return_value = [api]
        apic_client.list_api_versions.return_value = []
        search_client.upload_documents.return_value = [make_upload_result(True)]

        service.full_reindex()

        uploaded = search_client.upload_documents.call_args.kwargs["documents"]
        doc = uploaded[0]
        assert "updatedAt" not in doc


# ---------------------------------------------------------------------------
# _fetch_spec_content
# ---------------------------------------------------------------------------


class TestFetchSpecContent:
    def test_spec_content_fetched_via_data_plane(self) -> None:
        """Spec export uses the data-plane export_api_specification method."""
        import json

        service, apic_client, _, search_client, _ = _make_service()

        api = make_api(name="spec-api")
        apic_client.list_apis.return_value = [api]
        apic_client.list_api_versions.return_value = [{"name": "v1"}]
        apic_client.list_api_definitions.return_value = [{"name": "openapi"}]
        apic_client.export_api_specification.return_value = '{"openapi": "3.0.0"}'
        search_client.upload_documents.return_value = [make_upload_result(True)]

        service.full_reindex()

        apic_client.export_api_specification.assert_called_once_with("spec-api", "v1", "openapi")
        uploaded = search_client.upload_documents.call_args.kwargs["documents"]
        # Spec content is sanitized (pretty-printed JSON) but semantically identical.
        assert json.loads(uploaded[0]["specContent"]) == {"openapi": "3.0.0"}

    def test_logs_warning_on_spec_fetch_failure(self) -> None:
        """Spec export errors are logged as warnings (not silently swallowed)."""
        service, apic_client, _, search_client, _ = _make_service()

        api = make_api(name="spec-fail-api")
        apic_client.list_apis.return_value = [api]
        apic_client.list_api_versions.return_value = [{"name": "v1"}]
        apic_client.list_api_definitions.return_value = [{"name": "openapi"}]
        apic_client.export_api_specification.side_effect = RuntimeError("export failed")
        search_client.upload_documents.return_value = [make_upload_result(True)]

        with patch("indexer.indexer_service.logger") as mock_logger:
            service.full_reindex()
            assert mock_logger.warning.call_count >= 1
            call_args_str = str(mock_logger.warning.call_args_list)
            assert "spec-fail-api" in call_args_str

        # Document is still indexed even without spec content
        search_client.upload_documents.assert_called_once()
        uploaded = search_client.upload_documents.call_args.kwargs["documents"]
        assert uploaded[0]["specContent"] == ""

    def test_logs_warning_on_definition_list_failure(self) -> None:
        """When listing definitions fails, warning is logged and doc still indexed."""
        service, apic_client, _, search_client, _ = _make_service()

        api = make_api(name="def-fail-api")
        apic_client.list_apis.return_value = [api]
        apic_client.list_api_versions.return_value = [{"name": "v1"}]
        apic_client.list_api_definitions.side_effect = RuntimeError("definitions failed")
        search_client.upload_documents.return_value = [make_upload_result(True)]

        with patch("indexer.indexer_service.logger") as mock_logger:
            service.full_reindex()
            assert mock_logger.warning.call_count >= 1
            call_args_str = str(mock_logger.warning.call_args_list)
            assert "def-fail-api" in call_args_str

        search_client.upload_documents.assert_called_once()
        uploaded = search_client.upload_documents.call_args.kwargs["documents"]
        assert uploaded[0]["specContent"] == ""

    def test_not_found_error_logs_info_not_warning(self) -> None:
        """An ApiCenterNotFoundError (404) is logged at info, not warning, since
        some API types (e.g. GraphQL) simply don't have downloadable specs.
        """
        service, apic_client, _, search_client, _ = _make_service()

        api = make_api(name="graphql-api")
        apic_client.list_apis.return_value = [api]
        apic_client.list_api_versions.return_value = [{"name": "v1"}]
        apic_client.list_api_definitions.return_value = [{"name": "graphql-def"}]
        apic_client.export_api_specification.side_effect = ApiCenterNotFoundError("Spec not found")
        search_client.upload_documents.return_value = [make_upload_result(True)]

        with patch("indexer.indexer_service.logger") as mock_logger:
            count = service.full_reindex()
            # Should log at info (expected), NOT at warning
            info_str = str(mock_logger.info.call_args_list)
            assert "graphql-api" in info_str
            assert "Spec not available" in info_str
            # No warning should mention spec failure for this API
            warning_str = str(mock_logger.warning.call_args_list)
            assert "graphql-api" not in warning_str

        assert count == 1
        search_client.upload_documents.assert_called_once()
        uploaded = search_client.upload_documents.call_args.kwargs["documents"]
        assert uploaded[0]["specContent"] == ""

    def test_non_404_error_still_logs_warning(self) -> None:
        """Non-404 errors should still be logged as warnings."""
        service, apic_client, _, search_client, _ = _make_service()

        api = make_api(name="server-error-api")
        apic_client.list_apis.return_value = [api]
        apic_client.list_api_versions.return_value = [{"name": "v1"}]
        apic_client.list_api_definitions.return_value = [{"name": "def1"}]
        apic_client.export_api_specification.side_effect = RuntimeError("Internal Server Error")
        search_client.upload_documents.return_value = [make_upload_result(True)]

        with patch("indexer.indexer_service.logger") as mock_logger:
            service.full_reindex()
            warning_str = str(mock_logger.warning.call_args_list)
            assert "server-error-api" in warning_str


# ---------------------------------------------------------------------------
# _sanitize_spec_content
# ---------------------------------------------------------------------------


class TestSanitizeSpecContent:
    def test_empty_string_returned_unchanged(self) -> None:
        result = IndexerService._sanitize_spec_content("")
        assert result == ""

    def test_none_like_empty_returns_as_is(self) -> None:
        """Falsy values are returned immediately."""
        result = IndexerService._sanitize_spec_content("")
        assert result == ""

    def test_json_is_pretty_printed(self) -> None:
        compact = '{"openapi":"3.0.0","info":{"title":"Test"}}'
        result = IndexerService._sanitize_spec_content(compact)
        # Pretty-printed JSON has newlines and indentation
        assert "\n" in result
        assert "  " in result
        # Content is preserved
        assert '"openapi"' in result
        assert '"3.0.0"' in result

    def test_yaml_content_passes_through(self) -> None:
        yaml_spec = "openapi: 3.0.0\ninfo:\n  title: Test\n"
        result = IndexerService._sanitize_spec_content(yaml_spec)
        # YAML is not JSON so pretty-print is skipped; content unchanged
        assert result == yaml_spec

    def test_short_content_returned_unchanged_semantically(self) -> None:
        """Short JSON is pretty-printed but contains the same data."""
        import json

        original = '{"a":"b"}'
        result = IndexerService._sanitize_spec_content(original)
        assert json.loads(result) == json.loads(original)

    def test_long_token_is_truncated(self) -> None:
        """A single token exceeding 32 000 bytes is truncated."""
        long_token = "x" * 40_000
        result = IndexerService._sanitize_spec_content(long_token)
        # Every whitespace-delimited token must be <= _MAX_TERM_BYTES
        from indexer.indexer_service import _MAX_TERM_BYTES

        for token in result.split():
            assert len(token.encode("utf-8")) <= _MAX_TERM_BYTES

    def test_mixed_content_with_long_token(self) -> None:
        """Normal words around a long token — only the long one is truncated."""
        long_token = "A" * 40_000
        text = f"short {long_token} words"
        result = IndexerService._sanitize_spec_content(text)
        parts = result.split()
        assert parts[0] == "short"
        assert parts[-1] == "words"
        from indexer.indexer_service import _MAX_TERM_BYTES

        assert len(parts[1].encode("utf-8")) <= _MAX_TERM_BYTES

    def test_multibyte_utf8_token_truncated_correctly(self) -> None:
        """Tokens with multi-byte UTF-8 characters are truncated by byte count."""
        # Each emoji is 4 bytes in UTF-8
        long_token = "\U0001f600" * 10_000  # 40 000 bytes
        result = IndexerService._sanitize_spec_content(long_token)
        from indexer.indexer_service import _MAX_TERM_BYTES

        for token in result.split():
            assert len(token.encode("utf-8")) <= _MAX_TERM_BYTES

    def test_json_with_base64_blob_truncated(self) -> None:
        """Simulates an OpenAPI spec with an embedded base64 example."""
        import json

        from indexer.indexer_service import _MAX_TERM_BYTES

        spec = {
            "openapi": "3.0.0",
            "info": {"title": "Test"},
            "paths": {
                "/upload": {
                    "post": {
                        "requestBody": {
                            "content": {
                                "application/octet-stream": {
                                    "example": "x" * 40_000,
                                }
                            }
                        }
                    }
                }
            },
        }
        compact = json.dumps(spec)
        result = IndexerService._sanitize_spec_content(compact)
        for token in result.split():
            assert len(token.encode("utf-8")) <= _MAX_TERM_BYTES

    def test_sanitize_called_during_build_documents(self) -> None:
        """_build_documents applies sanitization to specContent."""
        service, apic_client, _, search_client, _ = _make_service()

        long_spec = '{"data":"' + "x" * 40_000 + '"}'
        api = make_api(name="big-spec-api")
        apic_client.list_apis.return_value = [api]
        apic_client.list_api_versions.return_value = [{"name": "v1"}]
        apic_client.list_api_definitions.return_value = [{"name": "openapi"}]
        apic_client.export_api_specification.return_value = long_spec
        # Need enough upload results for all docs produced
        search_client.upload_documents.return_value = [make_upload_result(True)] * 10

        service.full_reindex()

        from indexer.indexer_service import _MAX_TERM_BYTES

        uploaded = search_client.upload_documents.call_args.kwargs["documents"]
        for doc in uploaded:
            for token in doc["specContent"].split():
                assert len(token.encode("utf-8")) <= _MAX_TERM_BYTES


# ---------------------------------------------------------------------------
# _split_into_chunks
# ---------------------------------------------------------------------------


class TestSplitIntoChunks:
    def test_empty_string_returns_single_element(self) -> None:
        result = IndexerService._split_into_chunks("")
        assert result == [""]

    def test_short_string_returns_single_element(self) -> None:
        result = IndexerService._split_into_chunks("hello world")
        assert result == ["hello world"]

    def test_exact_chunk_size_returns_single_element(self) -> None:
        from indexer.indexer_service import _CHUNK_SIZE_CHARS

        text = "x" * _CHUNK_SIZE_CHARS
        result = IndexerService._split_into_chunks(text)
        assert len(result) == 1
        assert result[0] == text

    def test_large_text_is_split_into_chunks(self) -> None:
        from indexer.indexer_service import _CHUNK_SIZE_CHARS

        text = "a" * (_CHUNK_SIZE_CHARS * 3 + 100)
        result = IndexerService._split_into_chunks(text)
        assert len(result) == 4
        assert all(len(c) <= _CHUNK_SIZE_CHARS for c in result)
        assert "".join(result) == text


# ---------------------------------------------------------------------------
# Document chunking (large spec → multiple documents)
# ---------------------------------------------------------------------------


class TestDocumentChunking:
    def test_small_spec_produces_single_document(self) -> None:
        """A spec under the chunk size produces only one document."""
        service, apic_client, _, search_client, _ = _make_service()

        api = make_api(name="small-api")
        apic_client.list_apis.return_value = [api]
        apic_client.list_api_versions.return_value = [{"name": "v1"}]
        apic_client.list_api_definitions.return_value = [{"name": "openapi"}]
        apic_client.export_api_specification.return_value = '{"openapi": "3.0.0"}'
        search_client.upload_documents.return_value = [make_upload_result(True)]

        service.full_reindex()

        uploaded = search_client.upload_documents.call_args.kwargs["documents"]
        assert len(uploaded) == 1
        assert uploaded[0]["id"] == "small-api"
        assert uploaded[0]["parentApiId"] == ""
        assert uploaded[0]["chunkIndex"] == 0

    def test_large_spec_produces_multiple_documents(self) -> None:
        """A spec exceeding the chunk size produces parent + child documents."""
        from indexer.indexer_service import _CHUNK_SIZE_CHARS

        service, apic_client, _, search_client, _ = _make_service()

        # Build a well-tokenized spec larger than one chunk.
        # Use space-separated tokens to avoid token-truncation shrinking the text.
        spec = " ".join(f"token{i}" for i in range(_CHUNK_SIZE_CHARS // 4))

        api = make_api(name="big-api")
        apic_client.list_apis.return_value = [api]
        apic_client.list_api_versions.return_value = [{"name": "v1"}]
        apic_client.list_api_definitions.return_value = [{"name": "openapi"}]
        apic_client.export_api_specification.return_value = spec
        search_client.upload_documents.return_value = [make_upload_result(True)] * 10

        service.full_reindex()

        uploaded = search_client.upload_documents.call_args.kwargs["documents"]
        assert len(uploaded) > 1

        # Parent document (chunkIndex 0) carries the API name as ID.
        parent = uploaded[0]
        assert parent["id"] == "big-api"
        assert parent["parentApiId"] == ""
        assert parent["chunkIndex"] == 0

        # Child documents have chunk IDs and reference the parent.
        for i, child in enumerate(uploaded[1:], start=1):
            assert child["id"] == f"big-api__chunk_{i}"
            assert child["parentApiId"] == "big-api"
            assert child["chunkIndex"] == i

    def test_chunk_documents_share_metadata(self) -> None:
        """All chunk documents carry the same API metadata."""
        from indexer.indexer_service import _CHUNK_SIZE_CHARS

        service, apic_client, _, search_client, _ = _make_service()

        spec = " ".join(f"word{i}" for i in range(_CHUNK_SIZE_CHARS // 3))

        api = make_api(name="meta-api", title="Meta API", description="Desc")
        apic_client.list_apis.return_value = [api]
        apic_client.list_api_versions.return_value = []
        search_client.upload_documents.return_value = [make_upload_result(True)] * 5

        # Monkeypatch spec fetch to return the large spec
        apic_client.list_api_versions.return_value = [{"name": "v1"}]
        apic_client.list_api_definitions.return_value = [{"name": "def"}]
        apic_client.export_api_specification.return_value = spec

        service.full_reindex()

        uploaded = search_client.upload_documents.call_args.kwargs["documents"]
        assert len(uploaded) > 1
        for doc in uploaded:
            assert doc["apiName"] == "meta-api"
            assert doc["title"] == "Meta API"
            assert doc["description"] == "Desc"

    def test_each_chunk_gets_own_embedding(self) -> None:
        """Each chunk document triggers its own embedding call."""
        from indexer.indexer_service import _CHUNK_SIZE_CHARS

        service, apic_client, _, search_client, embedding_service = _make_service()

        spec = " ".join(f"tok{i}" for i in range(_CHUNK_SIZE_CHARS // 2))  # large, well-tokenized

        api = make_api(name="emb-api")
        apic_client.list_apis.return_value = [api]
        apic_client.list_api_versions.return_value = [{"name": "v1"}]
        apic_client.list_api_definitions.return_value = [{"name": "def"}]
        apic_client.export_api_specification.return_value = spec
        search_client.upload_documents.return_value = [make_upload_result(True)] * 5

        service.full_reindex()

        uploaded = search_client.upload_documents.call_args.kwargs["documents"]
        # Each document should have triggered an embedding call.
        assert embedding_service.generate_embedding.call_count == len(uploaded)

    def test_incremental_index_cleans_up_old_chunks(self) -> None:
        """incremental_index calls _cleanup_api_chunks before uploading."""
        service, apic_client, _, search_client, _ = _make_service()

        # Simulate an existing chunk document in the index.
        search_client.search.return_value = iter([{"id": "my-api__chunk_1"}])

        api = make_api(name="my-api")
        apic_client.get_api.return_value = api
        apic_client.list_api_versions.return_value = []
        search_client.upload_documents.return_value = [make_upload_result(True)]

        service.incremental_index("my-api")

        # The old chunk should have been deleted.
        search_client.delete_documents.assert_called()
        delete_calls = search_client.delete_documents.call_args_list
        # At least one delete call should contain the old chunk ID.
        deleted_ids = []
        for call in delete_calls:
            docs = call.kwargs.get("documents") or (call.args[0] if call.args else [])
            deleted_ids.extend(d["id"] for d in docs if isinstance(d, dict))
        assert "my-api__chunk_1" in deleted_ids

    def test_delete_from_index_cleans_up_chunks(self) -> None:
        """delete_from_index removes the parent and any chunk documents."""
        service, _, _, search_client, _ = _make_service()

        # Simulate existing chunks.
        search_client.search.return_value = iter(
            [
                {"id": "my-api__chunk_1"},
                {"id": "my-api__chunk_2"},
            ]
        )
        search_client.delete_documents.return_value = [make_upload_result(True)]

        result = service.delete_from_index("my-api")

        assert result is True
        # Should have at least two delete calls: one for chunks, one for parent.
        assert search_client.delete_documents.call_count >= 2

    def test_2mb_spec_is_fully_indexed(self) -> None:
        """A 2 MB spec (APIM max size) is indexed across many chunk documents."""
        from indexer.indexer_service import _CHUNK_SIZE_CHARS, _MAX_TERM_BYTES

        service, apic_client, _, search_client, _ = _make_service()

        # Simulate a ~2 MB spec with well-tokenized content (many short words).
        spec = " ".join(f"path{i}" for i in range(250_000))  # ~2 MB of text

        api = make_api(name="huge-api")
        apic_client.list_apis.return_value = [api]
        apic_client.list_api_versions.return_value = [{"name": "v1"}]
        apic_client.list_api_definitions.return_value = [{"name": "openapi"}]
        apic_client.export_api_specification.return_value = spec

        # Return one success result per uploaded document (dynamic).
        def _dynamic_upload(documents: list) -> list:
            return [make_upload_result(True) for _ in documents]

        search_client.upload_documents.side_effect = lambda documents: _dynamic_upload(documents)

        count = service.full_reindex()

        uploaded = search_client.upload_documents.call_args.kwargs["documents"]
        assert count == len(uploaded)
        # Every document must have specContent within chunk limits.
        for doc in uploaded:
            assert len(doc["specContent"]) <= _CHUNK_SIZE_CHARS
            # Every token must be within Lucene term limit.
            for token in doc["specContent"].split():
                assert len(token.encode("utf-8")) <= _MAX_TERM_BYTES
        # Should have produced many chunks for a 2 MB spec.
        assert len(uploaded) > 1
