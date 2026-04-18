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


def make_upload_result(succeeded: bool = True) -> SimpleNamespace:
    return _ns(succeeded=succeeded)


def _make_service() -> tuple[IndexerService, MagicMock, MagicMock, MagicMock, MagicMock]:
    """Return an IndexerService wired to mock data-plane client."""
    apic_client = MagicMock()
    search_index_client = MagicMock()
    search_client = MagicMock()
    embedding_service = MagicMock()

    # Default embedding response
    embedding_service.generate_embedding.return_value = [0.1] * 1536

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
        assert uploaded[0]["specContent"] == '{"openapi": "3.0.0"}'

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
