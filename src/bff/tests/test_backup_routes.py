"""Unit tests for the backup admin router."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from apic_vibe_portal_bff.middleware.auth import AuthenticatedUser
from apic_vibe_portal_bff.middleware.rbac import get_current_user
from apic_vibe_portal_bff.routers import backup as backup_router
from apic_vibe_portal_bff.services.backup_service import (
    BackupNotConfiguredError,
    BackupNotFoundError,
)


def _user(roles: list[str]) -> AuthenticatedUser:
    return AuthenticatedUser(oid="u1", name="Tester", email="t@example.com", roles=roles)


_SAMPLE = {
    "backupId": "apic-backup-2026-04-28T12-00-00Z",
    "sourceServiceName": "apic-test",
    "timestamp": "2026-04-28T12:00:00Z",
    "blobName": "apic-backup-2026-04-28T12-00-00Z.zip",
    "sizeBytes": 4096,
    "sizeFormatted": "4.0 KB",
    "counts": {
        "apis": 2,
        "versions": 2,
        "definitions": 2,
        "deployments": 2,
        "environments": 1,
    },
    "retentionTiers": ["hourly", "daily"],
    "status": "completed",
    "durationMs": 1234,
}


class _StubBackupService:
    def __init__(
        self,
        *,
        items: list[dict[str, Any]] | None = None,
        missing: bool = False,
        pages: list[tuple[list[dict[str, Any]], str | None, bool]] | None = None,
    ) -> None:
        self._items = items if items is not None else [_SAMPLE]
        self._missing = missing
        self.not_configured = False
        # Optional explicit pagination scenarios keyed by continuation token
        self._pages = pages
        self.list_calls: list[tuple[int, str | None]] = []

    def list_backups(
        self, *, limit: int = 50, continuation_token: str | None = None
    ) -> tuple[list[dict[str, Any]], str | None, bool]:
        self.list_calls.append((limit, continuation_token))
        if self._pages is not None:
            idx = 0 if continuation_token is None else int(continuation_token)
            return self._pages[idx]
        return self._items[:limit], None, False

    def get_backup(self, backup_id: str) -> dict[str, Any]:
        if self._missing:
            raise BackupNotFoundError(backup_id)
        return self._items[0]

    def generate_download_url(self, backup_id: str) -> tuple[str, datetime]:
        if self.not_configured:
            raise BackupNotConfiguredError("not configured")
        if self._missing:
            raise BackupNotFoundError(backup_id)
        return ("https://fake.blob/backup.zip?sas=token", datetime(2026, 4, 28, 13, 0, tzinfo=UTC))


@pytest.fixture
def app() -> FastAPI:
    test_app = FastAPI()
    test_app.include_router(backup_router.router)
    return test_app


def _wire_admin(app: FastAPI, service: _StubBackupService) -> None:
    app.dependency_overrides[backup_router.get_backup_service] = lambda: service
    app.dependency_overrides[get_current_user] = lambda: _user(["Portal.Admin"])


def _wire_non_admin(app: FastAPI, service: _StubBackupService) -> None:
    app.dependency_overrides[backup_router.get_backup_service] = lambda: service
    app.dependency_overrides[get_current_user] = lambda: _user(["Portal.User"])


# ---------------------------------------------------------------------------
# GET /api/admin/backups
# ---------------------------------------------------------------------------


class TestListBackups:
    def test_returns_items_for_admin(self, app: FastAPI) -> None:
        _wire_admin(app, _StubBackupService())
        client = TestClient(app)

        resp = client.get("/api/admin/backups")
        assert resp.status_code == 200
        body = resp.json()
        assert body["data"][0]["backupId"] == _SAMPLE["backupId"]
        assert body["data"][0]["sizeFormatted"] == "4.0 KB"
        assert body["data"][0]["counts"]["apis"] == 2
        assert body["pagination"] == {"continuationToken": None, "hasMore": False}

    def test_forbidden_for_non_admin(self, app: FastAPI) -> None:
        _wire_non_admin(app, _StubBackupService())
        client = TestClient(app)

        resp = client.get("/api/admin/backups")
        assert resp.status_code == 403

    def test_supports_continuation_token_paging(self, app: FastAPI) -> None:
        page_one = ([_SAMPLE], "1", True)
        page_two = ([{**_SAMPLE, "backupId": "second"}], None, False)
        svc = _StubBackupService(pages=[page_one, page_two])
        _wire_admin(app, svc)
        client = TestClient(app)

        first = client.get("/api/admin/backups?limit=1").json()
        assert first["pagination"] == {"continuationToken": "1", "hasMore": True}
        assert first["data"][0]["backupId"] == _SAMPLE["backupId"]

        second = client.get("/api/admin/backups?limit=1&continuationToken=1").json()
        assert second["pagination"] == {"continuationToken": None, "hasMore": False}
        assert second["data"][0]["backupId"] == "second"

        assert svc.list_calls == [(1, None), (1, "1")]

    def test_includes_failed_backups(self, app: FastAPI) -> None:
        failed = {**_SAMPLE, "backupId": "failed-1", "status": "failed", "error": "boom"}
        _wire_admin(app, _StubBackupService(items=[failed]))
        client = TestClient(app)
        body = client.get("/api/admin/backups").json()
        assert body["data"][0]["status"] == "failed"
        assert body["data"][0]["error"] == "boom"


# ---------------------------------------------------------------------------
# GET /api/admin/backups/{id}
# ---------------------------------------------------------------------------


class TestGetBackup:
    def test_returns_backup(self, app: FastAPI) -> None:
        _wire_admin(app, _StubBackupService())
        client = TestClient(app)

        resp = client.get(f"/api/admin/backups/{_SAMPLE['backupId']}")
        assert resp.status_code == 200
        assert resp.json()["backupId"] == _SAMPLE["backupId"]

    def test_not_found(self, app: FastAPI) -> None:
        _wire_admin(app, _StubBackupService(missing=True))
        client = TestClient(app)

        resp = client.get("/api/admin/backups/missing")
        assert resp.status_code == 404
        assert resp.json()["detail"]["code"] == "BACKUP_NOT_FOUND"


# ---------------------------------------------------------------------------
# GET /api/admin/backups/{id}/download
# ---------------------------------------------------------------------------


class TestDownloadBackup:
    def test_returns_sas_url(self, app: FastAPI) -> None:
        _wire_admin(app, _StubBackupService())
        client = TestClient(app)

        resp = client.get(f"/api/admin/backups/{_SAMPLE['backupId']}/download")
        assert resp.status_code == 200
        body = resp.json()
        assert body["downloadUrl"].startswith("https://")
        assert "sas=token" in body["downloadUrl"]
        assert body["expiresAt"].startswith("2026-04-28T13:00")

    def test_503_when_not_configured(self, app: FastAPI) -> None:
        svc = _StubBackupService()
        svc.not_configured = True
        _wire_admin(app, svc)
        client = TestClient(app)

        resp = client.get(f"/api/admin/backups/{_SAMPLE['backupId']}/download")
        assert resp.status_code == 503
        assert resp.json()["detail"]["code"] == "BACKUP_NOT_CONFIGURED"

    def test_not_found(self, app: FastAPI) -> None:
        _wire_admin(app, _StubBackupService(missing=True))
        client = TestClient(app)

        resp = client.get("/api/admin/backups/missing/download")
        assert resp.status_code == 404
