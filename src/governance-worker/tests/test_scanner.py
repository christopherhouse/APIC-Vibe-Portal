"""Tests for governance_worker.scanner — GovernanceScannerService."""

from __future__ import annotations

from datetime import UTC, datetime
from unittest.mock import MagicMock

import pytest

from governance_worker.rules import ComplianceChecker, GovernanceRule, RuleSeverity
from governance_worker.scanner import (
    _DAILY_TTL,
    _GRANULAR_TTL,
    _MONTHLY_TTL,
    _WEEKLY_TTL,
    RETENTION_TIER_DAILY,
    RETENTION_TIER_GRANULAR,
    RETENTION_TIER_MONTHLY,
    RETENTION_TIER_WEEKLY,
    GovernanceScannerService,
    compute_retention_tier,
)

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


def _make_api(name: str = "test-api", **kwargs) -> dict:
    base = {
        "name": name,
        "title": f"Title for {name}",
        "description": "A test api using oauth authentication.",
        "contacts": [{"name": "team"}],
        "lifecycleStage": "design",
        "versions": [{"name": "v1.0.0", "specifications": [{"name": "openapi"}]}],
        "deployments": [{"name": "prod"}],
        "externalDocs": [{"url": "https://docs.example.com"}],
        "customProperties": {"tags": ["x"]},
    }
    base.update(kwargs)
    return base


def _make_scanner(
    apis: list[dict] | None = None,
    list_versions_return: list | None = None,
    list_deployments_return: list | None = None,
    rules: list | None = None,
    cosmos_upsert_raises: Exception | None = None,
) -> tuple[GovernanceScannerService, MagicMock, MagicMock]:
    """Return (scanner, mock_apic, mock_cosmos_container)."""
    mock_apic = MagicMock()
    mock_apic.list_apis.return_value = apis or [_make_api()]
    mock_apic.list_api_versions.return_value = list_versions_return or [{"name": "v1"}]
    mock_apic.list_api_deployments.return_value = list_deployments_return or []

    mock_container = MagicMock()
    if cosmos_upsert_raises is not None:
        mock_container.upsert_item.side_effect = cosmos_upsert_raises

    mock_cosmos = MagicMock()
    mock_cosmos.get_database_client.return_value.get_container_client.return_value = mock_container

    checker = ComplianceChecker(rules=rules) if rules is not None else ComplianceChecker()

    scanner = GovernanceScannerService(
        apic_client=mock_apic,
        cosmos_client=mock_cosmos,
        database_name="test-db",
        container_name="governance-snapshots",
        workspace_name="default",
        agent_id="test-worker",
        checker=checker,
    )
    return scanner, mock_apic, mock_container


# ---------------------------------------------------------------------------
# GovernanceScannerService.scan_all
# ---------------------------------------------------------------------------


class TestScanAll:
    def test_returns_count_of_processed_apis(self):
        apis = [_make_api("api-1"), _make_api("api-2"), _make_api("api-3")]
        scanner, _, _ = _make_scanner(apis=apis)
        count = scanner.scan_all()
        assert count == 3

    def test_upserts_one_document_per_api(self):
        apis = [_make_api("api-1"), _make_api("api-2")]
        scanner, _, container = _make_scanner(apis=apis)
        scanner.scan_all()
        assert container.upsert_item.call_count == 2

    def test_snapshot_document_has_required_fields(self):
        scanner, _, container = _make_scanner(apis=[_make_api("my-api")])
        scanner.scan_all()
        doc = container.upsert_item.call_args[0][0]
        assert doc["apiId"] == "my-api"
        assert "findings" in doc
        assert "complianceScore" in doc
        assert "timestamp" in doc
        assert "schemaVersion" in doc
        assert doc["agentId"] == "test-worker"
        assert doc["isDeleted"] is False
        assert "retentionTier" in doc
        assert doc["ttl"] > 0

    def test_snapshot_id_includes_api_id_date_and_3h_slot(self):
        scanner, _, container = _make_scanner(apis=[_make_api("my-api")])
        scanner.scan_all()
        doc = container.upsert_item.call_args[0][0]
        from datetime import UTC, datetime

        now = datetime.now(UTC)
        expected_slot = (now.hour // 3) * 3
        assert doc["id"].startswith("my-api-")
        assert now.date().isoformat() in doc["id"]
        assert doc["id"].endswith(f"-{expected_slot:02d}")

    def test_snapshot_id_sanitizes_invalid_cosmos_chars(self):
        """API IDs with /, \\, ?, # must be sanitized in the document ID."""
        api = _make_api("workspace/api-with/slashes")
        scanner, _, container = _make_scanner(apis=[api])
        scanner.scan_all()
        doc = container.upsert_item.call_args[0][0]
        assert "/" not in doc["id"]
        assert doc["id"].startswith("workspace_api-with_slashes-")

    def test_apis_without_name_are_skipped(self):
        apis = [{"title": "No Name"}]
        scanner, _, container = _make_scanner(apis=apis)
        count = scanner.scan_all()
        assert count == 0
        container.upsert_item.assert_not_called()

    def test_cosmos_error_skips_api_and_continues(self):
        from azure.cosmos.exceptions import CosmosHttpResponseError

        apis = [_make_api("api-1"), _make_api("api-2")]
        scanner, _, container = _make_scanner(
            apis=apis,
            cosmos_upsert_raises=CosmosHttpResponseError(message="Cosmos error", status_code=503),
        )
        count = scanner.scan_all()
        # Both upserts failed but scan_all returned 0 (no successes)
        assert count == 0

    def test_apic_list_error_propagates(self):
        scanner, mock_apic, _ = _make_scanner()
        mock_apic.list_apis.side_effect = RuntimeError("Network error")
        with pytest.raises(RuntimeError, match="Network error"):
            scanner.scan_all()

    def test_enrichment_failure_still_produces_snapshot(self):
        """If fetching versions/deployments fails, a snapshot is still created."""
        scanner, mock_apic, container = _make_scanner(apis=[_make_api("api-x")])
        mock_apic.list_api_versions.side_effect = RuntimeError("version fetch failed")
        mock_apic.list_api_deployments.side_effect = RuntimeError("deploy fetch failed")
        # Should not raise — error is logged and empty lists used
        count = scanner.scan_all()
        assert count == 1
        doc = container.upsert_item.call_args[0][0]
        assert doc["apiId"] == "api-x"

    def test_findings_contain_all_rule_results(self):
        always_pass = GovernanceRule("x.pass", "Pass", "", RuleSeverity.WARNING, "", lambda api: True)
        always_fail = GovernanceRule("x.fail", "Fail", "", RuleSeverity.CRITICAL, "fix it", lambda api: False)
        scanner, _, container = _make_scanner(
            apis=[_make_api("my-api")],
            rules=[always_pass, always_fail],
        )
        scanner.scan_all()
        doc = container.upsert_item.call_args[0][0]
        assert len(doc["findings"]) == 2
        rule_ids = {f["ruleId"] for f in doc["findings"]}
        assert rule_ids == {"x.pass", "x.fail"}

    def test_compliance_score_in_snapshot(self):
        always_pass = GovernanceRule("x.pass", "Pass", "", RuleSeverity.CRITICAL, "", lambda api: True)
        scanner, _, container = _make_scanner(
            apis=[_make_api("my-api")],
            rules=[always_pass],
        )
        scanner.scan_all()
        doc = container.upsert_item.call_args[0][0]
        assert doc["complianceScore"] == 100.0

    def test_multiple_apis_processed_independently(self):
        apis = [_make_api(f"api-{i}") for i in range(5)]
        scanner, _, container = _make_scanner(apis=apis)
        count = scanner.scan_all()
        assert count == 5
        upserted_api_ids = {call[0][0]["apiId"] for call in container.upsert_item.call_args_list}
        assert upserted_api_ids == {f"api-{i}" for i in range(5)}


# ---------------------------------------------------------------------------
# GovernanceScannerService._fetch_all_apis (enrichment)
# ---------------------------------------------------------------------------


class TestFetchAllApis:
    def test_versions_and_deployments_merged_into_api(self):
        api = {"name": "api-1", "title": "API 1"}
        scanner, mock_apic, _ = _make_scanner(
            apis=[api],
            list_versions_return=[{"name": "v2"}],
            list_deployments_return=[{"name": "prod-deploy"}],
        )
        enriched = scanner._fetch_all_apis()
        assert len(enriched) == 1
        assert enriched[0]["versions"] == [{"name": "v2"}]
        assert enriched[0]["deployments"] == [{"name": "prod-deploy"}]

    def test_enrichment_does_not_modify_original_list_apis_result(self):
        api = {"name": "api-1", "title": "API 1"}
        scanner, mock_apic, _ = _make_scanner(apis=[api])
        scanner._fetch_all_apis()
        # Original dict should be unchanged (we copy before enriching)
        assert "versions" not in api


# ---------------------------------------------------------------------------
# compute_retention_tier — tiered retention policy
# ---------------------------------------------------------------------------


class TestComputeRetentionTier:
    """Verify the four retention tiers are assigned correctly."""

    def _dt(self, *, day: int, month: int = 4, year: int = 2026, hour: int = 0, weekday_mon: bool = False) -> datetime:
        """Helper: build a UTC datetime at the given calendar position."""
        # Find a date matching month/day and (optionally) a Monday.
        from datetime import date, timedelta

        d = date(year, month, day)
        if weekday_mon:
            # Advance to the next Monday if needed.
            while d.weekday() != 0:
                d += timedelta(days=1)
        return datetime(d.year, d.month, d.day, hour, 0, 0, tzinfo=UTC)

    # -- Granular tier (non-midnight slot) -----------------------------------

    def test_granular_tier_at_03h(self):
        tier, ttl = compute_retention_tier(self._dt(day=7, hour=3))
        assert tier == RETENTION_TIER_GRANULAR
        assert ttl == _GRANULAR_TTL

    def test_granular_tier_at_06h(self):
        tier, ttl = compute_retention_tier(self._dt(day=7, hour=6))
        assert tier == RETENTION_TIER_GRANULAR
        assert ttl == _GRANULAR_TTL

    def test_granular_tier_at_21h(self):
        tier, ttl = compute_retention_tier(self._dt(day=7, hour=21))
        assert tier == RETENTION_TIER_GRANULAR
        assert ttl == _GRANULAR_TTL

    def test_granular_ttl_is_48_hours(self):
        tier, ttl = compute_retention_tier(self._dt(day=7, hour=9))
        assert ttl == 48 * 3600

    # -- Daily tier (midnight, not Mon, not 1st) ------------------------------

    def test_daily_tier_at_midnight_on_regular_day(self):
        # April 7 2026 is a Tuesday — regular day.
        tier, ttl = compute_retention_tier(self._dt(day=7, hour=0))
        assert tier == RETENTION_TIER_DAILY
        assert ttl == _DAILY_TTL

    def test_daily_ttl_is_7_days(self):
        tier, ttl = compute_retention_tier(self._dt(day=7, hour=0))
        assert ttl == 7 * 24 * 3600

    # -- Weekly tier (Monday midnight, not 1st) --------------------------------

    def test_weekly_tier_on_monday_midnight(self):
        # April 6 2026 is a Monday and not the 1st.
        dt = datetime(2026, 4, 6, 0, 0, 0, tzinfo=UTC)
        assert dt.weekday() == 0  # sanity-check
        tier, ttl = compute_retention_tier(dt)
        assert tier == RETENTION_TIER_WEEKLY
        assert ttl == _WEEKLY_TTL

    def test_weekly_ttl_is_4_weeks(self):
        dt = datetime(2026, 4, 6, 0, 0, 0, tzinfo=UTC)
        _, ttl = compute_retention_tier(dt)
        assert ttl == 4 * 7 * 24 * 3600

    def test_monday_non_midnight_is_granular(self):
        dt = datetime(2026, 4, 6, 3, 0, 0, tzinfo=UTC)
        tier, _ = compute_retention_tier(dt)
        assert tier == RETENTION_TIER_GRANULAR

    # -- Monthly tier (1st of month, midnight) ---------------------------------

    def test_monthly_tier_on_1st_midnight(self):
        dt = datetime(2026, 4, 1, 0, 0, 0, tzinfo=UTC)
        tier, ttl = compute_retention_tier(dt)
        assert tier == RETENTION_TIER_MONTHLY
        assert ttl == _MONTHLY_TTL

    def test_monthly_ttl_is_90_days(self):
        dt = datetime(2026, 4, 1, 0, 0, 0, tzinfo=UTC)
        _, ttl = compute_retention_tier(dt)
        assert ttl == 90 * 24 * 3600

    def test_monthly_takes_priority_over_weekly_when_1st_is_monday(self):
        # Find a 1st-of-month that is also a Monday.
        # June 1 2026 is a Monday.
        dt = datetime(2026, 6, 1, 0, 0, 0, tzinfo=UTC)
        assert dt.weekday() == 0  # sanity-check: is Monday
        assert dt.day == 1  # sanity-check: is 1st
        tier, ttl = compute_retention_tier(dt)
        assert tier == RETENTION_TIER_MONTHLY
        assert ttl == _MONTHLY_TTL

    def test_1st_non_midnight_is_granular(self):
        dt = datetime(2026, 4, 1, 6, 0, 0, tzinfo=UTC)
        tier, _ = compute_retention_tier(dt)
        assert tier == RETENTION_TIER_GRANULAR

    # -- Snapshot document carries retentionTier field -------------------------

    def test_snapshot_document_includes_retention_tier_field(self):
        """The persisted document must include retentionTier."""
        scanner, _, container = _make_scanner(apis=[_make_api("my-api")])
        scanner.scan_all()
        doc = container.upsert_item.call_args[0][0]
        assert "retentionTier" in doc
        assert doc["retentionTier"] in (
            RETENTION_TIER_GRANULAR,
            RETENTION_TIER_DAILY,
            RETENTION_TIER_WEEKLY,
            RETENTION_TIER_MONTHLY,
        )

    def test_snapshot_document_ttl_matches_tier(self):
        """The document TTL must match the TTL for the reported retentionTier."""
        tier_to_ttl = {
            RETENTION_TIER_GRANULAR: _GRANULAR_TTL,
            RETENTION_TIER_DAILY: _DAILY_TTL,
            RETENTION_TIER_WEEKLY: _WEEKLY_TTL,
            RETENTION_TIER_MONTHLY: _MONTHLY_TTL,
        }
        scanner, _, container = _make_scanner(apis=[_make_api("my-api")])
        scanner.scan_all()
        doc = container.upsert_item.call_args[0][0]
        expected_ttl = tier_to_ttl[doc["retentionTier"]]
        assert doc["ttl"] == expected_ttl
