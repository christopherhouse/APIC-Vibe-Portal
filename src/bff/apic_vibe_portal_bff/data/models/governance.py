"""Pydantic models for governance snapshot documents in Cosmos DB.

Documents are stored in the ``governance-snapshots`` container, partitioned
by ``/apiId``.
"""

from __future__ import annotations

from datetime import UTC, datetime

from pydantic import BaseModel, Field

# ---------------------------------------------------------------------------
# Nested models
# ---------------------------------------------------------------------------


class GovernanceFinding(BaseModel):
    """A single finding within a governance snapshot."""

    rule_id: str = Field(..., alias="ruleId", description="Governance rule identifier")
    rule_name: str = Field(..., alias="ruleName", description="Human-readable rule name")
    severity: str = Field(..., description="Finding severity: critical | high | medium | low | info")
    passed: bool = Field(..., description="Whether the API passed this rule")
    message: str = Field(default="", description="Detailed finding message")

    model_config = {"populate_by_name": True}


# ---------------------------------------------------------------------------
# Governance snapshot document
# ---------------------------------------------------------------------------

CURRENT_SCHEMA_VERSION: int = 1


class GovernanceSnapshotDocument(BaseModel):
    """Cosmos DB document schema for a governance snapshot."""

    id: str = Field(..., description="Unique snapshot identifier (UUID)")
    api_id: str = Field(..., alias="apiId", description="API identifier (partition key)")
    timestamp: str = Field(..., description="ISO-8601 snapshot timestamp")
    findings: list[GovernanceFinding] = Field(default_factory=list, description="Rule evaluation results")
    compliance_score: float = Field(default=0.0, alias="complianceScore", description="Overall compliance score 0-100")
    agent_id: str = Field(default="", alias="agentId", description="ID of the agent that produced this snapshot")
    schema_version: int = Field(default=CURRENT_SCHEMA_VERSION, alias="schemaVersion")
    is_deleted: bool = Field(default=False, alias="isDeleted", description="Soft-delete flag")
    deleted_at: str | None = Field(default=None, alias="deletedAt", description="ISO-8601 soft-delete timestamp")

    model_config = {"populate_by_name": True}

    def to_cosmos_dict(self) -> dict:
        """Serialise to a dict using camelCase alias keys for Cosmos DB storage."""
        return self.model_dump(by_alias=True, exclude_none=False)

    @classmethod
    def new(
        cls,
        *,
        snapshot_id: str,
        api_id: str,
        findings: list[GovernanceFinding] | None = None,
        compliance_score: float = 0.0,
        agent_id: str = "",
    ) -> GovernanceSnapshotDocument:
        """Factory helper that creates a new snapshot with timestamp set to *now*."""
        now = datetime.now(UTC).isoformat().replace("+00:00", "Z")
        return cls(
            id=snapshot_id,
            apiId=api_id,
            timestamp=now,
            findings=findings or [],
            complianceScore=compliance_score,
            agentId=agent_id,
            schemaVersion=CURRENT_SCHEMA_VERSION,
            isDeleted=False,
            deletedAt=None,
        )
