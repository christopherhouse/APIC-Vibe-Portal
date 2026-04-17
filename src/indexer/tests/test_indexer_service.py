"""Unit tests for IndexerService — mocked Azure SDK calls."""

from __future__ import annotations

import datetime
from types import SimpleNamespace
from unittest.mock import MagicMock

from indexer.indexer_service import IndexerService, IndexStats

# ---------------------------------------------------------------------------
# Helpers / factories
# ---------------------------------------------------------------------------


def _ns(**kwargs: object) -> SimpleNamespace:
    return SimpleNamespace(**kwargs)


def _make_system_data(
    created: str = "2024-01-15T10:00:00",
    updated: str = "2024-03-20T14:30:00",
) -> SimpleNamespace:
    return _ns(
        created_at=datetime.datetime.fromisoformat(created),
        last_modified_at=datetime.datetime.fromisoformat(updated),
    )


def make_api(
    name: str = "petstore-api",
    title: str = "Petstore API",
    description: str = "A sample pet store API",
    kind: str = "rest",
    lifecycle_stage: str = "production",
    custom_properties: dict[str, object] | None = None,
    contacts: list[object] | None = None,
) -> SimpleNamespace:
    """Build a mock that mirrors the real ``azure.mgmt.apicenter.models.Api``
    ARM resource: ``name`` and ``system_data`` on the top-level object,
    everything else nested under ``properties``.
    """
    return _ns(
        name=name,
        system_data=_make_system_data(),
        properties=_ns(
            title=title,
            description=description,
            kind=kind,
            lifecycle_stage=lifecycle_stage,
            custom_properties=custom_properties or {"owner": "platform-team"},
            contacts=contacts or [_ns(name="API Team", email="api-team@example.com")],
        ),
    )


def make_upload_result(succeeded: bool = True) -> SimpleNamespace:
    return _ns(succeeded=succeeded)


def _make_service() -> tuple[IndexerService, MagicMock, MagicMock, MagicMock, MagicMock]:
    """Return an IndexerService wired to mock Azure SDK clients."""
    apic_client = MagicMock()
    search_index_client = MagicMock()
    search_client = MagicMock()
    embedding_service = MagicMock()

    # Default embedding response
    embedding_service.generate_embedding.return_value = [0.1] * 1536

    # Default workspace listing — return a single "default" workspace
    apic_client.workspaces.list.return_value = iter([_ns(name="default")])

    service = IndexerService(
        apic_client=apic_client,
        search_index_client=search_index_client,
        search_client=search_client,
        embedding_service=embedding_service,
        resource_group="rg-test",
        service_name="apic-test",
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

        service.ensure_index(mock_schema)

        search_index_client.create_or_update_index.assert_called_once_with(mock_schema)


# ---------------------------------------------------------------------------
# full_reindex
# ---------------------------------------------------------------------------


class TestFullReindex:
    def test_returns_count_of_successfully_indexed_documents(self) -> None:
        service, apic_client, _, search_client, _ = _make_service()

        apis = [make_api(name="api-1"), make_api(name="api-2")]
        apic_client.apis.list.return_value = iter(apis)
        apic_client.api_versions.list.return_value = iter([])
        search_client.upload_documents.return_value = [
            make_upload_result(True),
            make_upload_result(True),
        ]

        count = service.full_reindex()

        assert count == 2
        search_client.upload_documents.assert_called_once()

    def test_returns_zero_when_no_apis(self) -> None:
        service, apic_client, _, search_client, _ = _make_service()
        apic_client.apis.list.return_value = iter([])

        count = service.full_reindex()

        assert count == 0
        search_client.upload_documents.assert_not_called()

    def test_document_contains_required_fields(self) -> None:
        service, apic_client, _, search_client, _ = _make_service()

        api = make_api(name="my-api", title="My API", description="My description")
        apic_client.apis.list.return_value = iter([api])
        apic_client.api_versions.list.return_value = iter([])
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
        apic_client.apis.list.return_value = iter(apis)
        apic_client.api_versions.list.return_value = iter([])
        search_client.upload_documents.return_value = [make_upload_result(True)] * 3

        service.full_reindex()

        assert embedding_service.generate_embedding.call_count == 3

    def test_version_names_included_in_document(self) -> None:
        service, apic_client, _, search_client, _ = _make_service()

        api = make_api(name="my-api")
        apic_client.apis.list.return_value = iter([api])
        apic_client.api_versions.list.return_value = iter(
            [
                _ns(name="v1"),
                _ns(name="v2"),
            ]
        )
        # No definitions for simplicity
        apic_client.api_definitions.list.return_value = iter([])
        search_client.upload_documents.return_value = [make_upload_result(True)]

        service.full_reindex()

        uploaded = search_client.upload_documents.call_args.kwargs["documents"]
        doc = uploaded[0]
        assert "v1" in doc["versions"]
        assert "v2" in doc["versions"]

    def test_partial_failures_counted_correctly(self) -> None:
        service, apic_client, _, search_client, _ = _make_service()

        apis = [make_api(name="api-1"), make_api(name="api-2")]
        apic_client.apis.list.return_value = iter(apis)
        apic_client.api_versions.list.return_value = iter([])
        search_client.upload_documents.return_value = [
            make_upload_result(True),
            make_upload_result(False),
        ]

        count = service.full_reindex()

        assert count == 1

    def test_versions_fallback_to_empty_and_logs_warning_on_error(self) -> None:
        """Version list errors degrade gracefully and emit a warning."""
        from unittest.mock import patch

        service, apic_client, _, search_client, _ = _make_service()

        api = make_api(name="bad-api")
        apic_client.apis.list.return_value = iter([api])
        apic_client.api_versions.list.side_effect = RuntimeError("network error")
        search_client.upload_documents.return_value = [make_upload_result(True)]

        with patch("indexer.indexer_service.logger") as mock_logger:
            service.full_reindex()
            # The warning is now called with structlog keyword args
            assert mock_logger.warning.call_count >= 1
            call_args_str = str(mock_logger.warning.call_args_list)
            assert "bad-api" in call_args_str

        # Document is still uploaded even when version fetch fails
        search_client.upload_documents.assert_called_once()

    def test_verify_workspace_called_before_listing_apis(self) -> None:
        """Workspace verification runs before the API listing."""
        service, apic_client, _, search_client, _ = _make_service()

        apic_client.apis.list.return_value = iter([make_api()])
        apic_client.api_versions.list.return_value = iter([])
        search_client.upload_documents.return_value = [make_upload_result(True)]

        service.full_reindex()

        apic_client.workspaces.list.assert_called_once_with(
            resource_group_name="rg-test",
            service_name="apic-test",
        )


# ---------------------------------------------------------------------------
# _verify_workspace
# ---------------------------------------------------------------------------


class TestVerifyWorkspace:
    def test_logs_error_when_workspace_not_found(self) -> None:
        """When the configured workspace doesn't exist, an error is logged."""
        from unittest.mock import patch

        service, apic_client, _, _, _ = _make_service()
        apic_client.workspaces.list.return_value = iter([_ns(name="other-ws")])

        with patch("indexer.indexer_service.logger") as mock_logger:
            service._verify_workspace()
            mock_logger.error.assert_called_once()
            call_args_str = str(mock_logger.error.call_args)
            assert "does not exist" in call_args_str

    def test_logs_info_when_workspace_found(self) -> None:
        """When the configured workspace exists, only info is logged."""
        from unittest.mock import patch

        service, apic_client, _, _, _ = _make_service()
        apic_client.workspaces.list.return_value = iter([_ns(name="default")])

        with patch("indexer.indexer_service.logger") as mock_logger:
            service._verify_workspace()
            mock_logger.error.assert_not_called()
            mock_logger.info.assert_called_once()

    def test_workspace_list_failure_is_non_fatal(self) -> None:
        """If workspace listing itself fails, the error is logged as a
        warning and does not propagate."""
        from unittest.mock import patch

        service, apic_client, _, _, _ = _make_service()
        apic_client.workspaces.list.side_effect = RuntimeError("authz denied")

        with patch("indexer.indexer_service.logger") as mock_logger:
            service._verify_workspace()  # must not raise
            mock_logger.warning.assert_called_once()


# ---------------------------------------------------------------------------
# _props helper
# ---------------------------------------------------------------------------


class TestProps:
    def test_returns_properties_sub_object_when_present(self) -> None:
        """For real SDK objects with a ``properties`` sub-object, return it."""
        inner = _ns(title="My API", kind="rest")
        api = _ns(name="my-api", properties=inner)

        result = IndexerService._props(api)

        assert result is inner
        assert result.title == "My API"

    def test_returns_api_itself_when_no_properties(self) -> None:
        """For legacy SimpleNamespace mocks without ``properties``, fallback
        to the object itself so old-style attribute access still works."""
        api = _ns(name="my-api", title="My API", kind="rest")

        result = IndexerService._props(api)

        assert result is api

    def test_returns_api_itself_when_properties_is_none(self) -> None:
        """If ``properties`` exists but is ``None``, fallback to the api."""
        api = _ns(name="my-api", title="My API", properties=None)

        result = IndexerService._props(api)

        assert result is api


# ---------------------------------------------------------------------------
# incremental_index
# ---------------------------------------------------------------------------


class TestIncrementalIndex:
    def test_returns_true_on_success(self) -> None:
        service, apic_client, _, search_client, _ = _make_service()

        api = make_api(name="petstore-api")
        apic_client.apis.get.return_value = api
        apic_client.api_versions.list.return_value = iter([])
        search_client.upload_documents.return_value = [make_upload_result(True)]

        result = service.incremental_index("petstore-api")

        assert result is True
        apic_client.apis.get.assert_called_once_with(
            resource_group_name="rg-test",
            service_name="apic-test",
            workspace_name="default",
            api_name="petstore-api",
        )

    def test_returns_false_on_upload_failure(self) -> None:
        service, apic_client, _, search_client, _ = _make_service()

        api = make_api(name="petstore-api")
        apic_client.apis.get.return_value = api
        apic_client.api_versions.list.return_value = iter([])
        search_client.upload_documents.return_value = [make_upload_result(False)]

        result = service.incremental_index("petstore-api")

        assert result is False

    def test_uploads_single_document(self) -> None:
        service, apic_client, _, search_client, _ = _make_service()

        api = make_api(name="petstore-api")
        apic_client.apis.get.return_value = api
        apic_client.api_versions.list.return_value = iter([])
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
    def test_formats_name_and_email(self) -> None:
        contact = _ns(name="Alice", email="alice@example.com")
        result = IndexerService._contact_to_str(contact)
        assert result == "Alice <alice@example.com>"

    def test_email_only(self) -> None:
        contact = _ns(name="", email="alice@example.com")
        result = IndexerService._contact_to_str(contact)
        assert result == "alice@example.com"

    def test_name_only(self) -> None:
        contact = _ns(name="Bob", email=None)
        result = IndexerService._contact_to_str(contact)
        assert result == "Bob"

    def test_empty_contact(self) -> None:
        contact = _ns(name="", email=None)
        result = IndexerService._contact_to_str(contact)
        assert result == ""


# ---------------------------------------------------------------------------
# datetime timezone normalisation
# ---------------------------------------------------------------------------


class TestDatetimeTimezone:
    def test_naive_datetime_is_normalised_to_utc(self) -> None:
        """Naive datetimes (no tzinfo) are assigned UTC before indexing."""
        service, apic_client, _, search_client, _ = _make_service()

        naive_created = datetime.datetime(2024, 1, 15, 10, 0, 0)  # no tzinfo
        naive_updated = datetime.datetime(2024, 3, 20, 14, 30, 0)
        assert naive_created.tzinfo is None

        api = make_api(name="tz-api")
        api.system_data = _ns(created_at=naive_created, last_modified_at=naive_updated)
        apic_client.apis.list.return_value = iter([api])
        apic_client.api_versions.list.return_value = iter([])
        search_client.upload_documents.return_value = [make_upload_result(True)]

        service.full_reindex()

        uploaded = search_client.upload_documents.call_args.kwargs["documents"]
        doc = uploaded[0]
        assert doc["createdAt"].tzinfo is not None
        assert doc["updatedAt"].tzinfo is not None

    def test_aware_datetime_is_preserved(self) -> None:
        """Timezone-aware datetimes are passed through unchanged."""
        service, apic_client, _, search_client, _ = _make_service()

        aware_created = datetime.datetime(2024, 1, 15, 10, 0, 0, tzinfo=datetime.UTC)
        aware_updated = datetime.datetime(2024, 3, 20, 14, 30, 0, tzinfo=datetime.UTC)

        api = make_api(name="aware-api")
        api.system_data = _ns(created_at=aware_created, last_modified_at=aware_updated)
        apic_client.apis.list.return_value = iter([api])
        apic_client.api_versions.list.return_value = iter([])
        search_client.upload_documents.return_value = [make_upload_result(True)]

        service.full_reindex()

        uploaded = search_client.upload_documents.call_args.kwargs["documents"]
        doc = uploaded[0]
        assert doc["createdAt"] == aware_created
        assert doc["updatedAt"] == aware_updated


# ---------------------------------------------------------------------------
# _fetch_spec_content — warning logging
# ---------------------------------------------------------------------------


class TestFetchSpecContent:
    def test_logs_warning_on_spec_fetch_failure(self) -> None:
        """Spec export errors are logged as warnings (not silently swallowed)."""
        from unittest.mock import patch

        service, apic_client, _, search_client, _ = _make_service()

        api = make_api(name="spec-fail-api")
        apic_client.apis.list.return_value = iter([api])
        apic_client.api_versions.list.return_value = iter([_ns(name="v1")])
        apic_client.api_definitions.list.return_value = iter([_ns(name="openapi")])
        apic_client.api_definitions.export_specification.side_effect = RuntimeError("export failed")
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
