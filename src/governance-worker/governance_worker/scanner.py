"""Governance snapshot scanner service.

The :class:`GovernanceScannerService` fetches all APIs from Azure API
Center, evaluates them against the governance rules, and upserts the
results as governance snapshot documents in Cosmos DB.

One snapshot document is created per API per 3-hour window.  Documents
are keyed by ``{api_id}-{date}-{3h_slot}`` (e.g. ``my-api-2026-04-23-09``)
so that re-running within the same 3-hour window is idempotent.  Each
document carries a ``ttl`` of 172 800 seconds (48 hours) so Cosmos DB
automatically purges snapshots that are more than 48 hours old.
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

        Each document carries a ``ttl`` of 172 800 seconds (48 hours).  Cosmos
        DB automatically deletes documents once their TTL expires, keeping the
        container to a rolling 48-hour window of snapshots.

        Cosmos DB document IDs may not contain ``/``, ``\\``, ``?``, or ``#``.
        Any such characters in *api_id* are replaced with ``_`` before building
        the snapshot ID.
        """
        _SNAPSHOT_TTL_SECONDS = 48 * 3600  # 48 hours
        now = datetime.now(UTC)
        today = now.date().isoformat()
        three_hour_slot = (now.hour // 3) * 3
        safe_api_id = re.sub(r"[/\\?#]", "_", api_id)
        snapshot_id = f"{safe_api_id}-{today}-{three_hour_slot:02d}"
        timestamp = now.isoformat().replace("+00:00", "Z")

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
            "ttl": _SNAPSHOT_TTL_SECONDS,
        }
