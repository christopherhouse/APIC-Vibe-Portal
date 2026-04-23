"""Governance snapshot scanner service.

The :class:`GovernanceScannerService` fetches all APIs from Azure API
Center, evaluates them against the governance rules, and upserts the
results as governance snapshot documents in Cosmos DB.

Snapshot IDs
------------
One document is created per API per 3-hour window, keyed by
``{api_id}-{date}-{3h_slot}`` (e.g. ``my-api-2026-04-23-09``).
Re-running within the same 3-hour window overwrites the document with the
freshest catalog state (upsert), keeping exactly one snapshot per slot.

Tiered Retention
----------------
Document TTLs follow a graduated retention policy so that Cosmos DB
automatically purges documents at the right time:

+----------------+----------------------------------+----------------+
| Tier           | When                             | TTL            |
+================+==================================+================+
| ``granular``   | Any non-midnight 3-hour slot     | 48 hours       |
+----------------+----------------------------------+----------------+
| ``daily``      | Midnight (00:00) — other days    | 7 days         |
+----------------+----------------------------------+----------------+
| ``weekly``     | Monday midnight (00:00)          | 4 weeks        |
+----------------+----------------------------------+----------------+
| ``monthly``    | 1st of month, midnight (00:00)   | ~90 days       |
+----------------+----------------------------------+----------------+

Each snapshot document includes a ``retentionTier`` field so consumers
can filter or display snapshots by tier (e.g. show only daily rollups for
a 30-day trend chart).
"""

from __future__ import annotations

import re
from datetime import UTC, datetime
from typing import Any

import structlog
from apic_client import ApiCenterDataPlaneClient
from azure.cosmos import CosmosClient
from azure.cosmos.exceptions import CosmosHttpResponseError

from governance_worker.rules import ComplianceChecker, ComplianceResult

logger = structlog.get_logger()

# ---------------------------------------------------------------------------
# Retention tiers
# ---------------------------------------------------------------------------

#: Tier name constants — stored in each snapshot document as ``retentionTier``.
RETENTION_TIER_GRANULAR = "granular"  # every 3-hour slot, kept 48 h
RETENTION_TIER_DAILY = "daily"  # midnight slot, kept 7 days
RETENTION_TIER_WEEKLY = "weekly"  # Monday midnight, kept 4 weeks
RETENTION_TIER_MONTHLY = "monthly"  # 1st-of-month midnight, kept ~90 days

# TTL values in seconds for each retention tier.
_GRANULAR_TTL: int = 48 * 3600  # 48 hours
_DAILY_TTL: int = 7 * 24 * 3600  # 7 days
_WEEKLY_TTL: int = 4 * 7 * 24 * 3600  # 4 weeks (28 days)
_MONTHLY_TTL: int = 90 * 24 * 3600  # ~3 months (90 days)


def compute_retention_tier(now: datetime) -> tuple[str, int]:
    """Return ``(tier_name, ttl_seconds)`` for a snapshot taken at *now*.

    The hierarchy is: monthly → weekly → daily → granular.

    Parameters
    ----------
    now:
        The UTC timestamp of the snapshot (typically ``datetime.now(UTC)``).

    Returns
    -------
    tuple[str, int]
        A ``(tier_name, ttl_seconds)`` pair where *tier_name* is one of the
        ``RETENTION_TIER_*`` constants and *ttl_seconds* is the Cosmos DB TTL
        to apply to the document.
    """
    slot = (now.hour // 3) * 3
    if slot != 0:
        # Non-midnight 3-hour slot — granular snapshot only.
        return (RETENTION_TIER_GRANULAR, _GRANULAR_TTL)

    # Midnight (slot 00) — classify by calendar position, highest tier wins.
    if now.day == 1:
        return (RETENTION_TIER_MONTHLY, _MONTHLY_TTL)
    if now.weekday() == 0:  # Monday
        return (RETENTION_TIER_WEEKLY, _WEEKLY_TTL)
    return (RETENTION_TIER_DAILY, _DAILY_TTL)


class GovernanceScannerService:
    """Orchestrates a full governance scan across all APIs in API Center.

    Parameters
    ----------
    apic_client:
        Authenticated API Center data-plane client.
    cosmos_client:
        Authenticated Cosmos DB client.
    database_name:
        Cosmos DB database name.
    container_name:
        Cosmos DB container name for governance snapshots.
    workspace_name:
        API Center workspace name (default: ``"default"``).
    agent_id:
        Identifier recorded on every snapshot document.
    checker:
        Optional :class:`ComplianceChecker` instance.  Defaults to one
        using the full :data:`~rules.DEFAULT_RULES` set.
    """

    def __init__(
        self,
        *,
        apic_client: ApiCenterDataPlaneClient,
        cosmos_client: CosmosClient,
        database_name: str,
        container_name: str,
        workspace_name: str = "default",
        agent_id: str = "governance-worker",
        checker: ComplianceChecker | None = None,
    ) -> None:
        self._apic = apic_client
        self._cosmos = cosmos_client
        self._database_name = database_name
        self._container_name = container_name
        self._workspace_name = workspace_name
        self._agent_id = agent_id
        self._checker = checker or ComplianceChecker()

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def scan_all(self) -> int:
        """Fetch all APIs, evaluate governance rules, and persist snapshots.

        Returns
        -------
        int
            Number of APIs successfully scanned and persisted.
        """
        container = self._cosmos.get_database_client(self._database_name).get_container_client(self._container_name)

        apis = self._fetch_all_apis()
        logger.info("governance_worker.scan_start", api_count=len(apis))

        success_count = 0
        for api in apis:
            api_id = api.get("name", "")
            if not api_id:
                logger.warning("governance_worker.api_missing_name", api=api)
                continue

            try:
                result = self._checker.check_api(api)
                doc = self._build_snapshot_document(api_id, result)
                container.upsert_item(doc)
                logger.info(
                    "governance_worker.snapshot_upserted",
                    api_id=api_id,
                    score=result.score,
                    category=str(result.category),
                    failing_rule_count=len(result.failing_rules),
                )
                success_count += 1
            except CosmosHttpResponseError as exc:
                logger.error(
                    "governance_worker.cosmos_error",
                    api_id=api_id,
                    status_code=exc.status_code,
                    error=str(exc),
                )
            except Exception as exc:  # noqa: BLE001
                logger.error("governance_worker.scan_error", api_id=api_id, error=str(exc))

        logger.info("governance_worker.scan_complete", scanned=success_count, total=len(apis))
        return success_count

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _fetch_all_apis(self) -> list[dict[str, Any]]:
        """Return all APIs from API Center, enriched with versions and deployments."""
        try:
            raw_apis = self._apic.list_apis()
        except Exception as exc:  # noqa: BLE001
            logger.error("governance_worker.list_apis_failed", error=str(exc))
            raise

        enriched: list[dict[str, Any]] = []
        for api in raw_apis:
            api_name = api.get("name", "")
            if not api_name:
                continue
            enriched_api = dict(api)
            try:
                versions = self._apic.list_api_versions(api_name)
                enriched_api["versions"] = versions
                deployments = self._apic.list_api_deployments(api_name)
                enriched_api["deployments"] = deployments
            except Exception as exc:  # noqa: BLE001
                logger.warning(
                    "governance_worker.enrich_failed",
                    api_id=api_name,
                    error=str(exc),
                )
                enriched_api.setdefault("versions", [])
                enriched_api.setdefault("deployments", [])
            enriched.append(enriched_api)

        return enriched

    def _build_snapshot_document(self, api_id: str, result: ComplianceResult) -> dict[str, Any]:
        """Construct a Cosmos DB governance snapshot document.

        The document ``id`` is ``{sanitized_api_id}-{date}-{3h_slot:02d}`` (e.g.
        ``my-api-2026-04-23-09``) so that re-running within the same 3-hour
        window is idempotent while each 3-hour window produces a distinct
        document.  The 3-hour slot is the UTC hour rounded down to the nearest
        multiple of 3 (values: 00, 03, 06, 09, 12, 15, 18, 21).

        Document TTLs follow the tiered retention policy defined by
        :func:`compute_retention_tier`:

        - **granular** (any non-midnight slot) — 48 hours
        - **daily** (midnight, non-Mon, non-1st) — 7 days
        - **weekly** (Monday midnight) — 4 weeks
        - **monthly** (1st of month, midnight) — 90 days

        Cosmos DB document IDs may not contain ``/``, ``\\``, ``?``, or ``#``.
        Any such characters in *api_id* are replaced with ``_`` before building
        the snapshot ID.
        """
        now = datetime.now(UTC)
        today = now.date().isoformat()
        three_hour_slot = (now.hour // 3) * 3
        safe_api_id = re.sub(r"[/\\?#]", "_", api_id)
        snapshot_id = f"{safe_api_id}-{today}-{three_hour_slot:02d}"
        timestamp = now.isoformat().replace("+00:00", "Z")

        tier, ttl = compute_retention_tier(now)

        findings = [
            {
                "ruleId": r.rule_id,
                "ruleName": r.rule_name,
                "severity": str(r.severity),
                "passed": r.passed,
                "message": r.message,
            }
            for r in result.rule_results
        ]

        return {
            "id": snapshot_id,
            "apiId": api_id,
            "timestamp": timestamp,
            "findings": findings,
            "complianceScore": result.score,
            "agentId": self._agent_id,
            "schemaVersion": 1,
            "isDeleted": False,
            "deletedAt": None,
            "retentionTier": tier,
            "ttl": ttl,
        }
