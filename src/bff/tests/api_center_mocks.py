"""Mock Azure API Center SDK responses for unit tests.

All factories return plain Python objects (``SimpleNamespace``) that mimic
the attribute access pattern of the real ``azure-mgmt-apicenter`` models
without requiring the SDK to be imported.
"""

from __future__ import annotations

import datetime
from types import SimpleNamespace


def _ns(**kwargs: object) -> SimpleNamespace:
    """Shorthand for creating a ``SimpleNamespace``."""
    return SimpleNamespace(**kwargs)


def _system_data(
    created: str = "2024-01-15T10:00:00",
    updated: str = "2024-03-20T14:30:00",
) -> SimpleNamespace:
    return _ns(
        created_at=datetime.datetime.fromisoformat(created),
        last_modified_at=datetime.datetime.fromisoformat(updated),
    )


# ---------------------------------------------------------------------------
# Environment mock factories
# ---------------------------------------------------------------------------


def make_environment(
    *,
    name: str = "prod-env",
    title: str = "Production Environment",
    description: str | None = "Main production environment",
    kind: str = "production",
) -> SimpleNamespace:
    return _ns(
        name=name,
        title=title,
        description=description,
        kind=kind,
        system_data=_system_data(),
    )


MOCK_ENVIRONMENTS = [
    make_environment(name="dev-env", title="Development Environment", kind="development"),
    make_environment(name="staging-env", title="Staging Environment", kind="staging"),
    make_environment(name="prod-env", title="Production Environment", kind="production"),
]


# ---------------------------------------------------------------------------
# Deployment mock factories
# ---------------------------------------------------------------------------


def make_deployment(
    *,
    name: str = "dep-v1",
    title: str = "v1 Production Deployment",
    description: str | None = "Main deployment",
    environment_id: str = (
        "/subscriptions/sub/resourceGroups/rg/providers/Microsoft.ApiCenter/services/svc/environments/prod-env"
    ),
    runtime_uri: list[str] | None = None,
) -> SimpleNamespace:
    actual_uri = runtime_uri if runtime_uri is not None else ["https://api.example.com/v1"]
    return _ns(
        name=name,
        title=title,
        description=description,
        environment_id=environment_id,
        server=_ns(runtime_uri=actual_uri),
        system_data=_system_data(),
    )


MOCK_DEPLOYMENTS: list[SimpleNamespace] = [
    make_deployment(name="dep-v1", title="v1 Deployment"),
    make_deployment(
        name="dep-v2",
        title="v2 Deployment",
        runtime_uri=["https://api.example.com/v2"],
    ),
]


# ---------------------------------------------------------------------------
# API version mock factories
# ---------------------------------------------------------------------------


def make_api_version(
    *,
    name: str = "v1",
    title: str = "Version 1",
    lifecycle_stage: str = "production",
) -> SimpleNamespace:
    return _ns(
        name=name,
        title=title,
        lifecycle_stage=lifecycle_stage,
        system_data=_system_data(),
    )


MOCK_VERSIONS: list[SimpleNamespace] = [
    make_api_version(name="v1", title="Version 1.0", lifecycle_stage="production"),
    make_api_version(name="v2", title="Version 2.0", lifecycle_stage="preview"),
]


# ---------------------------------------------------------------------------
# API definition (spec document) mock factories
# ---------------------------------------------------------------------------


def make_api_spec_definition(
    *,
    name: str = "openapi",
    title: str = "OpenAPI Definition",
    spec_name: str = "openapi",
    spec_version: str = "3.0.1",
) -> SimpleNamespace:
    return _ns(
        name=name,
        title=title,
        specification=_ns(name=spec_name, version=spec_version),
        system_data=_system_data(),
    )


MOCK_API_DEFINITIONS: list[SimpleNamespace] = [
    make_api_spec_definition(name="openapi", title="OpenAPI Definition"),
]

MOCK_SPEC_CONTENT = '{"openapi": "3.0.1", "info": {"title": "Petstore API", "version": "1.0"}}'


# ---------------------------------------------------------------------------
# API mock factories
# ---------------------------------------------------------------------------


def make_api(
    *,
    name: str = "petstore-api",
    title: str = "Petstore API",
    description: str = "A sample pet store API",
    kind: str = "rest",
    lifecycle_stage: str = "production",
    contacts: list[object] | None = None,
    external_docs: list[object] | None = None,
    custom_properties: dict[str, object] | None = None,
    license_url: str | None = None,
    tos_url: str | None = None,
) -> SimpleNamespace:
    return _ns(
        name=name,
        title=title,
        description=description,
        kind=kind,
        lifecycle_stage=lifecycle_stage,
        contacts=contacts or [_ns(name="API Team", email="api-team@example.com", url=None)],
        external_docs=external_docs or [_ns(title="Docs", url="https://docs.example.com", description=None)],
        custom_properties=custom_properties or {"owner": "platform-team"},
        license=_ns(url=license_url) if license_url else _ns(url=None),
        terms_of_service=_ns(url=tos_url) if tos_url else _ns(url=None),
        system_data=_system_data(),
    )


MOCK_APIS: list[SimpleNamespace] = [
    make_api(name="petstore-api", title="Petstore API", kind="rest"),
    make_api(name="graphql-api", title="GraphQL API", kind="graphql", lifecycle_stage="development"),
    make_api(name="grpc-service", title="gRPC Service", kind="grpc", lifecycle_stage="testing"),
]
