"""Unit tests for data retention via Cosmos DB native TTL.

Verifies that the TTL constants are correctly defined and that the
``soft_delete`` method on ``BaseRepository`` sets the expected ``ttl``
field so Cosmos DB can auto-purge documents.
"""

from __future__ import annotations

from unittest.mock import MagicMock

from apic_vibe_portal_bff.data.repositories.base_repository import BaseRepository
from apic_vibe_portal_bff.data.retention import TTL_SECONDS


class TestTTLConstants:
    """Tests for :data:`TTL_SECONDS`."""

    def test_chat_sessions_90_days(self):
        assert TTL_SECONDS["chat-sessions"] == 90 * 86400

    def test_governance_snapshots_730_days(self):
        assert TTL_SECONDS["governance-snapshots"] == 730 * 86400

    def test_analytics_events_365_days(self):
        assert TTL_SECONDS["analytics-events"] == 365 * 86400


class TestSoftDeleteTTL:
    """Tests that soft_delete sets the correct TTL for each container."""

    def _make_repo(self, container_id: str) -> tuple[BaseRepository, MagicMock]:
        container = MagicMock()
        container.id = container_id
        doc = {"id": "1", "userId": "u1", "schemaVersion": 1}
        container.read_item.return_value = doc
        container.replace_item.return_value = doc
        repo = BaseRepository(container, "userId")
        return repo, container

    def test_chat_session_ttl(self):
        repo, container = self._make_repo("chat-sessions")
        repo.soft_delete("1", "u1")
        body = container.replace_item.call_args.kwargs.get("body") or container.replace_item.call_args[1].get("body")
        assert body["ttl"] == TTL_SECONDS["chat-sessions"]

    def test_governance_snapshot_ttl(self):
        repo, container = self._make_repo("governance-snapshots")
        repo.soft_delete("1", "u1")
        body = container.replace_item.call_args.kwargs.get("body") or container.replace_item.call_args[1].get("body")
        assert body["ttl"] == TTL_SECONDS["governance-snapshots"]

    def test_analytics_event_ttl(self):
        repo, container = self._make_repo("analytics-events")
        repo.soft_delete("1", "u1")
        body = container.replace_item.call_args.kwargs.get("body") or container.replace_item.call_args[1].get("body")
        assert body["ttl"] == TTL_SECONDS["analytics-events"]

    def test_custom_ttl_override(self):
        container = MagicMock()
        container.id = "custom"
        doc = {"id": "1", "userId": "u1", "schemaVersion": 1}
        container.read_item.return_value = doc
        container.replace_item.return_value = doc
        repo = BaseRepository(container, "userId", ttl_seconds=3600)
        repo.soft_delete("1", "u1")
        body = container.replace_item.call_args.kwargs.get("body") or container.replace_item.call_args[1].get("body")
        assert body["ttl"] == 3600

    def test_default_ttl_for_unknown_container(self):
        container = MagicMock()
        container.id = "unknown-container"
        repo = BaseRepository(container, "userId")
        assert repo._ttl == 365 * 86400  # 1 year fallback
