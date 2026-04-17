"""Pydantic models for Azure API Center entities.

These models mirror the shared TypeScript interfaces in ``src/shared/src/models/``
and serve as the BFF's internal representation of API Center data.
"""

from __future__ import annotations

from enum import StrEnum

from pydantic import BaseModel, ConfigDict, Field
from pydantic.alias_generators import to_camel

# ---------------------------------------------------------------------------
# Enums (mirror src/shared/src/enums/)
# ---------------------------------------------------------------------------


class ApiKind(StrEnum):
    """The kind (protocol/style) of an API."""

    REST = "rest"
    GRAPHQL = "graphql"
    GRPC = "grpc"
    SOAP = "soap"
    WEBSOCKET = "websocket"
    WEBHOOK = "webhook"


class ApiLifecycle(StrEnum):
    """API lifecycle stages as defined by Azure API Center."""

    DESIGN = "design"
    DEVELOPMENT = "development"
    TESTING = "testing"
    PREVIEW = "preview"
    PRODUCTION = "production"
    DEPRECATED = "deprecated"
    RETIRED = "retired"


class EnvironmentKind(StrEnum):
    """The kind of deployment environment."""

    DEVELOPMENT = "development"
    STAGING = "staging"
    TESTING = "testing"
    PRODUCTION = "production"


# ---------------------------------------------------------------------------
# Core models (mirror src/shared/src/models/)
# ---------------------------------------------------------------------------


class CamelModel(BaseModel):
    """Base model that serializes field names as camelCase in JSON.

    Python code continues to use snake_case attribute names.
    """

    model_config = ConfigDict(
        alias_generator=to_camel,
        populate_by_name=True,
    )


class ExternalDoc(CamelModel):
    """External documentation link for an API."""

    title: str
    url: str
    description: str | None = None


class Contact(CamelModel):
    """Contact information for an API."""

    name: str
    email: str | None = None
    url: str | None = None


class ApiEnvironment(CamelModel):
    """An environment where APIs can be deployed."""

    id: str
    name: str
    title: str
    description: str | None = None
    kind: EnvironmentKind = EnvironmentKind.DEVELOPMENT


class DeploymentServer(CamelModel):
    """Server information for a deployed API."""

    runtime_uri: list[str] = Field(default_factory=list)


class ApiDeployment(CamelModel):
    """Deployment information for an API version in a specific environment."""

    id: str
    title: str
    description: str | None = None
    environment: ApiEnvironment
    server: DeploymentServer
    created_at: str
    updated_at: str


class ApiVersion(CamelModel):
    """A specific version of an API."""

    id: str
    name: str
    title: str
    lifecycle_stage: ApiLifecycle = ApiLifecycle.DEVELOPMENT
    created_at: str
    updated_at: str


class ApiSpecification(CamelModel):
    """An API specification document (OpenAPI, AsyncAPI, etc.)."""

    id: str
    name: str
    title: str
    specification_type: str | None = None
    specification_version: str | None = None
    # The raw spec content (JSON/YAML) as a string; None if not yet exported
    content: str | None = None


class ApiDefinition(CamelModel):
    """Core API definition model, mirroring Azure API Center's API entity."""

    id: str
    name: str
    title: str
    description: str = ""
    kind: ApiKind = ApiKind.REST
    lifecycle_stage: ApiLifecycle = ApiLifecycle.DEVELOPMENT
    terms_of_service: str | None = None
    license: str | None = None
    external_docs: list[ExternalDoc] = Field(default_factory=list)
    contacts: list[Contact] = Field(default_factory=list)
    custom_properties: dict[str, object] = Field(default_factory=dict)
    versions: list[ApiVersion] = Field(default_factory=list)
    deployments: list[ApiDeployment] = Field(default_factory=list)
    created_at: str
    updated_at: str


# ---------------------------------------------------------------------------
# Pagination (mirror src/shared/src/models/pagination.ts)
# ---------------------------------------------------------------------------


class PaginationMeta(BaseModel):
    """Pagination metadata returned in responses."""

    page: int
    page_size: int
    total_count: int
    total_pages: int


class PaginatedResponse(BaseModel):
    """Generic paginated response wrapper."""

    items: list[ApiDefinition]
    pagination: PaginationMeta
