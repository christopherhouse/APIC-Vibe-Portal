"""Unit tests for the lazy migration utility."""

from __future__ import annotations

import pytest

from apic_vibe_portal_bff.data.migrations.lazy_migration import apply_migrations


def _migrate_v1_to_v2(doc: dict) -> dict:
    """Test migration: adds ``model`` and ``tokensUsed`` fields."""
    doc = dict(doc)
    doc["model"] = "gpt-4"
    doc["tokensUsed"] = 0
    doc["schemaVersion"] = 2
    return doc


def _migrate_v2_to_v3(doc: dict) -> dict:
    """Test migration: adds ``tags`` field."""
    doc = dict(doc)
    doc["tags"] = []
    doc["schemaVersion"] = 3
    return doc


MIGRATIONS = {
    1: _migrate_v1_to_v2,
    2: _migrate_v2_to_v3,
}


class TestApplyMigrations:
    """Tests for :func:`apply_migrations`."""

    def test_no_op_when_already_at_target(self):
        doc = {"schemaVersion": 2, "id": "abc"}
        result = apply_migrations(doc, target_version=2, migrations=MIGRATIONS)
        assert result is doc  # same object, no copy

    def test_no_op_when_above_target(self):
        doc = {"schemaVersion": 3, "id": "abc"}
        result = apply_migrations(doc, target_version=2, migrations=MIGRATIONS)
        assert result is doc

    def test_single_step_migration(self):
        doc = {"schemaVersion": 1, "id": "abc"}
        result = apply_migrations(doc, target_version=2, migrations=MIGRATIONS)
        assert result["schemaVersion"] == 2
        assert result["model"] == "gpt-4"
        assert result["tokensUsed"] == 0

    def test_multi_step_migration(self):
        doc = {"schemaVersion": 1, "id": "abc"}
        result = apply_migrations(doc, target_version=3, migrations=MIGRATIONS)
        assert result["schemaVersion"] == 3
        assert result["model"] == "gpt-4"
        assert result["tags"] == []

    def test_defaults_to_version_1_when_missing(self):
        doc = {"id": "abc"}  # no schemaVersion field
        result = apply_migrations(doc, target_version=2, migrations=MIGRATIONS)
        assert result["schemaVersion"] == 2

    def test_raises_on_missing_migration(self):
        doc = {"schemaVersion": 1, "id": "abc"}
        with pytest.raises(ValueError, match="No migration registered"):
            apply_migrations(doc, target_version=3, migrations={1: _migrate_v1_to_v2})
            # migration from 2→3 is missing

    def test_does_not_mutate_original(self):
        doc = {"schemaVersion": 1, "id": "abc"}
        _ = apply_migrations(doc, target_version=2, migrations=MIGRATIONS)
        assert doc["schemaVersion"] == 1
        assert "model" not in doc
