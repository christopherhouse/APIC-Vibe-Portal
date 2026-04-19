"""Pydantic models for API access policy documents in Cosmos DB.

Documents are stored in the ``api-access-policies`` container, partitioned
by ``/apiName``.

Each document represents the access control rules for one API in the catalog.
An API with no policy document is treated as public (accessible to all
authenticated users).  Once a policy is created with ``allowedGroups`` set,
only users who are members of those Entra ID groups can see the API.

Admin users (``Portal.Admin`` role) always bypass security trimming.
"""

from __future__ import annotations

from datetime import UTC, datetime

from pydantic import BaseModel, Field

CURRENT_SCHEMA_VERSION: int = 1


class ApiAccessPolicyDocument(BaseModel):
    """Cosmos DB document schema for an API access policy.

    Attributes
    ----------
    id:
        Same as ``api_name`` — the short API Center API name.  Used as the
        document ID for point-reads.
    api_name:
        Short name of the API in API Center (partition key and document ID).
        Example: ``"petstore-api"``.
    api_id:
        Full Azure resource ID of the API (for informational purposes).
    allowed_groups:
        List of Entra ID group object IDs (OIDs) whose members may access
        this API.  An empty list with ``is_public=False`` means nobody can
        access the API (effectively hidden from all non-admin users).
    is_public:
        When ``True``, all authenticated users can access this API regardless
        of group membership.  Overrides ``allowed_groups``.
    schema_version:
        Schema version for lazy migration support.
    created_at:
        ISO-8601 timestamp of policy creation.
    updated_at:
        ISO-8601 timestamp of last policy update.
    is_deleted:
        Soft-delete flag.
    deleted_at:
        ISO-8601 soft-delete timestamp.
    """

    id: str = Field(..., description="Document ID — same as apiName")
    api_name: str = Field(..., alias="apiName", description="API Center API name (partition key)")
    api_id: str = Field(default="", alias="apiId", description="Full Azure resource ID of the API")
    allowed_groups: list[str] = Field(
        default_factory=list,
        alias="allowedGroups",
        description="Entra ID group OIDs whose members may access this API",
    )
    is_public: bool = Field(
        default=False,
        alias="isPublic",
        description="When True, all authenticated users can access regardless of group membership",
    )
    schema_version: int = Field(default=CURRENT_SCHEMA_VERSION, alias="schemaVersion")
    created_at: str = Field(default="", alias="createdAt", description="ISO-8601 creation timestamp")
    updated_at: str = Field(default="", alias="updatedAt", description="ISO-8601 last-update timestamp")
    is_deleted: bool = Field(default=False, alias="isDeleted")
    deleted_at: str | None = Field(default=None, alias="deletedAt")

    model_config = {"populate_by_name": True}

    def to_cosmos_dict(self) -> dict:
        """Serialise to a dict using camelCase alias keys for Cosmos DB storage."""
        return self.model_dump(by_alias=True, exclude_none=False)

    @classmethod
    def new(
        cls,
        *,
        api_name: str,
        api_id: str = "",
        allowed_groups: list[str] | None = None,
        is_public: bool = False,
    ) -> ApiAccessPolicyDocument:
        """Factory that creates a new policy document with timestamps set to now."""
        now = datetime.now(UTC).isoformat().replace("+00:00", "Z")
        return cls(
            id=api_name,
            apiName=api_name,
            apiId=api_id,
            allowedGroups=allowed_groups or [],
            isPublic=is_public,
            schemaVersion=CURRENT_SCHEMA_VERSION,
            createdAt=now,
            updatedAt=now,
            isDeleted=False,
            deletedAt=None,
        )
