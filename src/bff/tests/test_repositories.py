"""Unit tests for the base repository and concrete repository classes.

All Cosmos DB calls are mocked — these tests verify the repository logic
(soft-delete, pagination, migration hooks, CRUD routing) without requiring
a live database.
"""

from __future__ import annotations

from unittest.mock import MagicMock

from apic_vibe_portal_bff.data.repositories.analytics_repository import AnalyticsRepository
from apic_vibe_portal_bff.data.repositories.base_repository import BaseRepository, PaginatedResult
from apic_vibe_portal_bff.data.repositories.chat_session_repository import ChatSessionRepository
from apic_vibe_portal_bff.data.repositories.governance_repository import GovernanceRepository

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_container_mock() -> MagicMock:
    """Return a mock ContainerProxy with sensible defaults."""
    mock = MagicMock()
    mock.id = "test-container"
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
        assert result["id"] == "1"

    def test_find_by_id_returns_document(self):
        container = _make_container_mock()
        container.read_item.return_value = {"id": "1", "userId": "u1", "schemaVersion": 1}
        repo = BaseRepository(container, "userId")

        result = repo.find_by_id("1", "u1")
        assert result is not None
        assert result["id"] == "1"
        container.read_item.assert_called_once_with(item="1", partition_key="u1")

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
        container.replace_item.assert_called_once_with(item="1", body=doc, partition_key="u1")
        assert result["title"] == "updated"

    def test_hard_delete_returns_true_on_success(self):
        container = _make_container_mock()
        repo = BaseRepository(container, "userId")

        assert repo.hard_delete("1", "u1") is True
        container.delete_item.assert_called_once_with(item="1", partition_key="u1")

    def test_hard_delete_returns_false_when_not_found(self):
        from azure.cosmos.exceptions import CosmosResourceNotFoundError

        container = _make_container_mock()
        container.delete_item.side_effect = CosmosResourceNotFoundError(message="gone")
        repo = BaseRepository(container, "userId")

        assert repo.hard_delete("missing", "u1") is False


class TestBaseRepositorySoftDelete:
    """Tests for soft-delete behaviour."""

    def test_soft_delete_marks_document(self):
        container = _make_container_mock()
        doc = {"id": "1", "userId": "u1", "schemaVersion": 1}
        container.read_item.return_value = doc
        container.replace_item.return_value = doc
        repo = BaseRepository(container, "userId")

        result = repo.soft_delete("1", "u1")
        assert result is not None
        # The doc passed to replace_item should have isDeleted=True
        call_args = container.replace_item.call_args
        body = call_args.kwargs.get("body") or call_args[1].get("body") or call_args[0][1]
        assert body["isDeleted"] is True
        assert body["deletedAt"] is not None

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


class TestBaseRepositoryRetention:
    """Tests for retention-related queries."""

    def test_find_expired_soft_deleted(self):
        container = _make_container_mock()
        expired = [{"id": "1", "userId": "u1", "isDeleted": True, "deletedAt": "2025-01-01T00:00:00Z"}]
        container.query_items.return_value = expired
        repo = BaseRepository(container, "userId")

        results = repo.find_expired_soft_deleted("2026-01-01T00:00:00Z")
        assert len(results) == 1
        query = container.query_items.call_args.kwargs.get("query") or container.query_items.call_args[1].get("query")
        assert "isDeleted = true" in query
        assert "deletedAt" in query


# ---------------------------------------------------------------------------
# Concrete repository tests
# ---------------------------------------------------------------------------


class TestChatSessionRepository:
    """Tests for :class:`ChatSessionRepository`."""

    def test_inherits_base(self):
        container = _make_container_mock()
        repo = ChatSessionRepository(container)
        assert isinstance(repo, BaseRepository)
        assert repo._pk_field == "userId"

    def test_find_sessions_for_user(self):
        container = _make_container_mock()
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
        container = _make_container_mock()
        repo = GovernanceRepository(container)
        assert isinstance(repo, BaseRepository)
        assert repo._pk_field == "apiId"

    def test_find_snapshots_for_api(self):
        container = _make_container_mock()
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
        container = _make_container_mock()
        repo = AnalyticsRepository(container)
        assert isinstance(repo, BaseRepository)
        assert repo._pk_field == "eventType"

    def test_find_events_by_type(self):
        container = _make_container_mock()
        container.query_items.return_value = _make_pager(
            [{"id": "e1", "eventType": "page_view", "schemaVersion": 1}],
        )
        repo = AnalyticsRepository(container)

        result = repo.find_events_by_type("page_view")
        assert len(result.items) == 1
        query = container.query_items.call_args.kwargs.get("query") or container.query_items.call_args[1].get("query")
        assert "timestamp DESC" in query
