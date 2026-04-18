"""Unit tests for the data retention cleanup job."""

from __future__ import annotations

from datetime import datetime, timedelta
from unittest.mock import MagicMock

from apic_vibe_portal_bff.data.repositories.base_repository import BaseRepository
from apic_vibe_portal_bff.jobs.data_retention_job import RETENTION_DAYS, run_cleanup


def _make_repo(expired_docs: list[dict] | None = None) -> BaseRepository:
    """Return a mock repository with ``find_expired_soft_deleted`` and ``hard_delete``."""
    repo = MagicMock(spec=BaseRepository)
    repo._pk_field = "userId"
    repo.find_expired_soft_deleted.return_value = expired_docs or []
    repo.hard_delete.return_value = True
    return repo


class TestRunCleanup:
    """Tests for :func:`run_cleanup`."""

    def test_no_expired_docs(self):
        repos = {"chat-sessions": _make_repo([])}
        result = run_cleanup(repos)
        assert result == {"chat-sessions": 0}

    def test_purges_expired_docs(self):
        expired = [
            {"id": "1", "userId": "u1", "isDeleted": True, "deletedAt": "2025-01-01T00:00:00Z"},
            {"id": "2", "userId": "u2", "isDeleted": True, "deletedAt": "2025-02-01T00:00:00Z"},
        ]
        repos = {"chat-sessions": _make_repo(expired)}
        result = run_cleanup(repos)
        assert result == {"chat-sessions": 2}
        assert repos["chat-sessions"].hard_delete.call_count == 2

    def test_uses_correct_retention_days(self):
        repos = {
            "chat-sessions": _make_repo(),
            "governance-snapshots": _make_repo(),
            "analytics-events": _make_repo(),
        }
        now = datetime(2026, 4, 18, 12, 0, 0)
        run_cleanup(repos, now=now)

        # Verify each repo was called with the correct cutoff date
        for container_name, repo in repos.items():
            call_args = repo.find_expired_soft_deleted.call_args
            cutoff = call_args[0][0]  # positional arg
            days = RETENTION_DAYS[container_name]
            expected_cutoff = (now - timedelta(days=days)).isoformat() + "Z"
            assert cutoff == expected_cutoff, f"Wrong cutoff for {container_name}"

    def test_retention_override(self):
        repos = {"chat-sessions": _make_repo()}
        now = datetime(2026, 4, 18, 12, 0, 0)
        run_cleanup(repos, retention_overrides={"chat-sessions": 30}, now=now)

        call_args = repos["chat-sessions"].find_expired_soft_deleted.call_args
        cutoff = call_args[0][0]
        expected = (now - timedelta(days=30)).isoformat() + "Z"
        assert cutoff == expected

    def test_handles_hard_delete_failure(self):
        expired = [{"id": "1", "userId": "u1"}]
        repo = _make_repo(expired)
        repo.hard_delete.return_value = False  # simulate failure
        repos = {"chat-sessions": repo}

        result = run_cleanup(repos)
        assert result == {"chat-sessions": 0}

    def test_multiple_containers(self):
        repos = {
            "chat-sessions": _make_repo([{"id": "1", "userId": "u1"}]),
            "governance-snapshots": _make_repo([{"id": "2", "userId": "u2"}, {"id": "3", "userId": "u3"}]),
            "analytics-events": _make_repo([]),
        }
        result = run_cleanup(repos)
        assert result == {
            "chat-sessions": 1,
            "governance-snapshots": 2,
            "analytics-events": 0,
        }
