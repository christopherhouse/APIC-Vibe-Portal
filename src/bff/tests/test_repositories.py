"""Unit tests for the base repository and concrete repository classes.

All Cosmos DB calls are mocked — these tests verify the repository logic
(soft-delete with TTL, pagination, migration hooks, CRUD routing) without
requiring a live database.
"""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from apic_vibe_portal_bff.data.repositories.analytics_repository import AnalyticsRepository
from apic_vibe_portal_bff.data.repositories.base_repository import TTL_SECONDS, BaseRepository, PaginatedResult
from apic_vibe_portal_bff.data.repositories.chat_session_repository import ChatSessionRepository
from apic_vibe_portal_bff.data.repositories.governance_repository import GovernanceRepository

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_container_mock(container_id: str = "test-container") -> MagicMock:
    """Return a mock ContainerProxy with sensible defaults."""
    mock = MagicMock()
    mock.id = container_id
    return mock


def _make_pager(items: list[dict], continuation_token: str | None = None):
    """Build a mock pager that returns one page of items."""
    page_iter = MagicMock()
    page_iter.__next__ = MagicMock(return_value=items)
    page_iter.continuation_token = continuation_token

    pager = MagicMock()
    pager.by_page = MagicMock(return_value=page_iter)
    return pager


# ---------------------------------------------------------------------------
# BaseRepository tests
# ---------------------------------------------------------------------------


class TestBaseRepositoryCRUD:
    """Tests for :class:`BaseRepository` CRUD operations."""

    def test_create_delegates_to_container(self):
        container = _make_container_mock()
        container.create_item.return_value = {"id": "1", "userId": "u1"}
        repo = BaseRepository(container, "userId")

        result = repo.create({"id": "1", "userId": "u1"})
        container.create_item.assert_called_once()
        call_kwargs = container.create_item.call_args.kwargs
        assert call_kwargs["body"] == {"id": "1", "userId": "u1"}
        assert call_kwargs["partition_key"] == "u1"
        assert callable(call_kwargs.get("response_hook"))
        assert result["id"] == "1"

    def test_create_raises_on_missing_partition_key(self):
        container = _make_container_mock()
        repo = BaseRepository(container, "userId")

        with pytest.raises(ValueError, match="missing required partition key"):
            repo.create({"id": "1"})

    def test_create_raises_on_empty_partition_key(self):
        container = _make_container_mock()
        repo = BaseRepository(container, "userId")

        with pytest.raises(ValueError, match="missing required partition key"):
            repo.create({"id": "1", "userId": ""})

    def test_find_by_id_returns_document(self):
        container = _make_container_mock()
        container.read_item.return_value = {"id": "1", "userId": "u1", "schemaVersion": 1}
        repo = BaseRepository(container, "userId")

        result = repo.find_by_id("1", "u1")
        assert result is not None
        assert result["id"] == "1"
        container.read_item.assert_called_once()
        call_kwargs = container.read_item.call_args.kwargs
        assert call_kwargs["item"] == "1"
        assert call_kwargs["partition_key"] == "u1"
        assert callable(call_kwargs.get("response_hook"))

    def test_find_by_id_returns_none_for_missing(self):
        from azure.cosmos.exceptions import CosmosResourceNotFoundError

        container = _make_container_mock()
        container.read_item.side_effect = CosmosResourceNotFoundError(message="not found")
        repo = BaseRepository(container, "userId")

        assert repo.find_by_id("missing", "u1") is None

    def test_find_by_id_returns_none_for_soft_deleted(self):
        container = _make_container_mock()
        container.read_item.return_value = {"id": "1", "userId": "u1", "isDeleted": True}
        repo = BaseRepository(container, "userId")

        assert repo.find_by_id("1", "u1") is None

    def test_update_calls_replace_item(self):
        container = _make_container_mock()
        container.replace_item.return_value = {"id": "1", "userId": "u1", "title": "updated"}
        repo = BaseRepository(container, "userId")

        doc = {"id": "1", "userId": "u1", "title": "updated"}
        result = repo.update(doc)
        container.replace_item.assert_called_once()
        call_kwargs = container.replace_item.call_args.kwargs
        assert call_kwargs["item"] == "1"
        assert call_kwargs["body"] == doc
        assert call_kwargs["partition_key"] == "u1"
        assert callable(call_kwargs.get("response_hook"))
        assert result["title"] == "updated"

    def test_update_raises_on_missing_partition_key(self):
        container = _make_container_mock()
        repo = BaseRepository(container, "userId")

        with pytest.raises(ValueError, match="missing required partition key"):
            repo.update({"id": "1"})

    def test_update_raises_on_empty_partition_key(self):
        container = _make_container_mock()
        repo = BaseRepository(container, "userId")

        with pytest.raises(ValueError, match="missing required partition key"):
            repo.update({"id": "1", "userId": ""})

    def test_hard_delete_returns_true_on_success(self):
        container = _make_container_mock()
        repo = BaseRepository(container, "userId")

        assert repo.hard_delete("1", "u1") is True
        container.delete_item.assert_called_once()
        call_kwargs = container.delete_item.call_args.kwargs
        assert call_kwargs["item"] == "1"
        assert call_kwargs["partition_key"] == "u1"
        assert callable(call_kwargs.get("response_hook"))

    def test_hard_delete_returns_false_when_not_found(self):
        from azure.cosmos.exceptions import CosmosResourceNotFoundError

        container = _make_container_mock()
        container.delete_item.side_effect = CosmosResourceNotFoundError(message="gone")
        repo = BaseRepository(container, "userId")

        assert repo.hard_delete("missing", "u1") is False


class TestBaseRepositorySoftDelete:
    """Tests for soft-delete behaviour with TTL."""

    def test_soft_delete_marks_document_and_sets_ttl(self):
        container = _make_container_mock("chat-sessions")
        doc = {"id": "1", "userId": "u1", "schemaVersion": 1}
        container.read_item.return_value = doc
        container.replace_item.return_value = doc
        repo = BaseRepository(container, "userId")

        result = repo.soft_delete("1", "u1")
        assert result is not None
        # The doc passed to replace_item should have isDeleted=True and ttl set
        call_args = container.replace_item.call_args
        body = call_args.kwargs.get("body") or call_args[1].get("body") or call_args[0][1]
        assert body["isDeleted"] is True
        assert body["deletedAt"] is not None
        assert body["ttl"] == TTL_SECONDS["chat-sessions"]

    def test_soft_delete_uses_custom_ttl(self):
        container = _make_container_mock("custom")
        doc = {"id": "1", "userId": "u1", "schemaVersion": 1}
        container.read_item.return_value = doc
        container.replace_item.return_value = doc
        repo = BaseRepository(container, "userId", ttl_seconds=3600)

        repo.soft_delete("1", "u1")
        call_args = container.replace_item.call_args
        body = call_args.kwargs.get("body") or call_args[1].get("body") or call_args[0][1]
        assert body["ttl"] == 3600

    def test_soft_delete_returns_none_when_not_found(self):
        from azure.cosmos.exceptions import CosmosResourceNotFoundError

        container = _make_container_mock()
        container.read_item.side_effect = CosmosResourceNotFoundError(message="gone")
        repo = BaseRepository(container, "userId")

        assert repo.soft_delete("missing", "u1") is None


class TestBaseRepositoryPagination:
    """Tests for paginated queries."""

    def test_find_by_partition_key_returns_paginated_result(self):
        container = _make_container_mock()
        items = [{"id": "1", "userId": "u1"}, {"id": "2", "userId": "u1"}]
        container.query_items.return_value = _make_pager(items, continuation_token="tok123")
        repo = BaseRepository(container, "userId")

        result = repo.find_by_partition_key("u1", max_items=10)
        assert isinstance(result, PaginatedResult)
        assert len(result.items) == 2
        assert result.continuation_token == "tok123"

    def test_find_by_partition_key_with_order_by(self):
        container = _make_container_mock()
        container.query_items.return_value = _make_pager([])
        repo = BaseRepository(container, "userId")

        repo.find_by_partition_key("u1", order_by="c.createdAt DESC")
        query = container.query_items.call_args.kwargs.get("query") or container.query_items.call_args[1].get("query")
        assert "ORDER BY c.createdAt DESC" in query

    def test_find_by_partition_key_excludes_deleted(self):
        container = _make_container_mock()
        container.query_items.return_value = _make_pager([])
        repo = BaseRepository(container, "userId")

        repo.find_by_partition_key("u1")
        query = container.query_items.call_args.kwargs.get("query") or container.query_items.call_args[1].get("query")
        assert "isDeleted" in query

    def test_find_by_partition_key_empty_result(self):
        container = _make_container_mock()
        page_iter = MagicMock()
        page_iter.__next__ = MagicMock(side_effect=StopIteration)
        page_iter.continuation_token = None
        pager = MagicMock()
        pager.by_page = MagicMock(return_value=page_iter)
        container.query_items.return_value = pager
        repo = BaseRepository(container, "userId")

        result = repo.find_by_partition_key("u1")
        assert result.items == []


# ---------------------------------------------------------------------------
# Concrete repository tests
# ---------------------------------------------------------------------------


class TestChatSessionRepository:
    """Tests for :class:`ChatSessionRepository`."""

    def test_inherits_base(self):
        container = _make_container_mock("chat-sessions")
        repo = ChatSessionRepository(container)
        assert isinstance(repo, BaseRepository)
        assert repo._pk_field == "userId"

    def test_find_sessions_for_user(self):
        container = _make_container_mock("chat-sessions")
        container.query_items.return_value = _make_pager(
            [{"id": "s1", "userId": "u1", "schemaVersion": 1}],
        )
        repo = ChatSessionRepository(container)

        result = repo.find_sessions_for_user("u1")
        assert len(result.items) == 1
        query = container.query_items.call_args.kwargs.get("query") or container.query_items.call_args[1].get("query")
        assert "createdAt DESC" in query


class TestGovernanceRepository:
    """Tests for :class:`GovernanceRepository`."""

    def test_inherits_base(self):
        container = _make_container_mock("governance-snapshots")
        repo = GovernanceRepository(container)
        assert isinstance(repo, BaseRepository)
        assert repo._pk_field == "apiId"

    def test_find_snapshots_for_api(self):
        container = _make_container_mock("governance-snapshots")
        container.query_items.return_value = _make_pager(
            [{"id": "g1", "apiId": "api-1", "schemaVersion": 1}],
        )
        repo = GovernanceRepository(container)

        result = repo.find_snapshots_for_api("api-1")
        assert len(result.items) == 1
        query = container.query_items.call_args.kwargs.get("query") or container.query_items.call_args[1].get("query")
        assert "timestamp DESC" in query


class TestAnalyticsRepository:
    """Tests for :class:`AnalyticsRepository`."""

    def test_inherits_base(self):
        container = _make_container_mock("analytics-events")
        repo = AnalyticsRepository(container)
        assert isinstance(repo, BaseRepository)
        assert repo._pk_field == "eventType"

    def test_find_events_by_type(self):
        container = _make_container_mock("analytics-events")
        container.query_items.return_value = _make_pager(
            [{"id": "e1", "eventType": "page_view", "schemaVersion": 1}],
        )
        repo = AnalyticsRepository(container)

        result = repo.find_events_by_type("page_view")
        assert len(result.items) == 1
        query = container.query_items.call_args.kwargs.get("query") or container.query_items.call_args[1].get("query")
        assert "timestamp DESC" in query


# ---------------------------------------------------------------------------
# RU metric emission tests
# ---------------------------------------------------------------------------


class TestCosmosRuMetrics:
    """Verify that RU cost is emitted for each Cosmos operation via response_hook."""

    def setup_method(self) -> None:
        import apic_vibe_portal_bff.telemetry.metrics as m

        m._meter = None
        m._instruments.clear()

    def _make_mock_meter_with_histogram(self) -> tuple[MagicMock, MagicMock]:
        import apic_vibe_portal_bff.telemetry.metrics as m

        mock_meter = MagicMock()
        mock_histogram = MagicMock()
        mock_meter.create_histogram.return_value = mock_histogram
        mock_meter.create_counter.return_value = MagicMock()
        m._meter = mock_meter
        return mock_meter, mock_histogram

    def _invoke_hook(self, container_mock: MagicMock, method_name: str, ru_charge: float) -> None:
        """Call the response_hook that was passed to the given container method."""
        call_kwargs = getattr(container_mock, method_name).call_args.kwargs
        hook = call_kwargs["response_hook"]
        hook({"x-ms-request-charge": str(ru_charge)}, {})

    def test_create_emits_ru_metric(self) -> None:
        _, mock_histogram = self._make_mock_meter_with_histogram()
        container = _make_container_mock("chat-sessions")
        container.create_item.return_value = {"id": "1", "userId": "u1"}
        repo = BaseRepository(container, "userId")

        repo.create({"id": "1", "userId": "u1"})
        self._invoke_hook(container, "create_item", 5.72)

        mock_histogram.record.assert_called_once_with(5.72, {"container": "chat-sessions", "operation": "create"})

    def test_read_emits_ru_metric(self) -> None:
        _, mock_histogram = self._make_mock_meter_with_histogram()
        container = _make_container_mock("chat-sessions")
        container.read_item.return_value = {"id": "1", "userId": "u1"}
        repo = BaseRepository(container, "userId")

        repo.find_by_id("1", "u1")
        self._invoke_hook(container, "read_item", 1.0)

        mock_histogram.record.assert_called_once_with(1.0, {"container": "chat-sessions", "operation": "read"})

    def test_replace_emits_ru_metric(self) -> None:
        _, mock_histogram = self._make_mock_meter_with_histogram()
        container = _make_container_mock("chat-sessions")
        container.replace_item.return_value = {"id": "1", "userId": "u1"}
        repo = BaseRepository(container, "userId")

        repo.update({"id": "1", "userId": "u1"})
        self._invoke_hook(container, "replace_item", 10.5)

        mock_histogram.record.assert_called_once_with(10.5, {"container": "chat-sessions", "operation": "replace"})

    def test_delete_emits_ru_metric(self) -> None:
        _, mock_histogram = self._make_mock_meter_with_histogram()
        container = _make_container_mock("chat-sessions")
        repo = BaseRepository(container, "userId")

        repo.hard_delete("1", "u1")
        self._invoke_hook(container, "delete_item", 6.25)

        mock_histogram.record.assert_called_once_with(6.25, {"container": "chat-sessions", "operation": "delete"})

    def test_query_emits_ru_metric(self) -> None:
        _, mock_histogram = self._make_mock_meter_with_histogram()
        container = _make_container_mock("chat-sessions")
        container.query_items.return_value = _make_pager([{"id": "1", "userId": "u1"}])
        repo = BaseRepository(container, "userId")

        repo.find_by_partition_key("u1")
        self._invoke_hook(container, "query_items", 3.14)

        mock_histogram.record.assert_called_once_with(3.14, {"container": "chat-sessions", "operation": "query"})

    def test_ru_hook_tolerates_missing_header(self) -> None:
        """Response hook should not raise when the RU header is absent."""
        _, mock_histogram = self._make_mock_meter_with_histogram()
        container = _make_container_mock("chat-sessions")
        container.create_item.return_value = {"id": "1", "userId": "u1"}
        repo = BaseRepository(container, "userId")

        repo.create({"id": "1", "userId": "u1"})
        hook = container.create_item.call_args.kwargs["response_hook"]
        # Missing header — should be a no-op, not an exception
        hook({}, {})
        mock_histogram.record.assert_not_called()

    def test_ru_hook_tolerates_non_numeric_header(self) -> None:
        """Response hook should not raise when the RU header is not a valid float."""
        _, mock_histogram = self._make_mock_meter_with_histogram()
        container = _make_container_mock("chat-sessions")
        container.create_item.return_value = {"id": "1", "userId": "u1"}
        repo = BaseRepository(container, "userId")

        repo.create({"id": "1", "userId": "u1"})
        hook = container.create_item.call_args.kwargs["response_hook"]
        hook({"x-ms-request-charge": "not-a-number"}, {})
        mock_histogram.record.assert_not_called()
