"""Data mapping utilities for Azure API Center data-plane responses.

Converts data-plane JSON dicts (or legacy SDK model instances) into BFF
Pydantic models.  All mappers are pure functions that handle ``None`` /
missing fields gracefully.

The data-plane API returns flat JSON objects (``name``, ``title``,
``lifecycleStage``, ``lastUpdated``, ``externalDocumentation``, etc.)
rather than the ARM envelope pattern (``properties`` sub-object).
"""

from __future__ import annotations

import datetime
import logging
from typing import Any

from apic_vibe_portal_bff.models.api_center import (
    ApiDefinition,
    ApiDeployment,
    ApiEnvironment,
    ApiKind,
    ApiLifecycle,
    ApiSpecification,
    ApiVersion,
    Contact,
    DeploymentServer,
    EnvironmentKind,
    ExternalDoc,
)

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_API_KIND_MAP: dict[str, ApiKind] = {
    "rest": ApiKind.REST,
    "graphql": ApiKind.GRAPHQL,
    "grpc": ApiKind.GRPC,
    "soap": ApiKind.SOAP,
    "websocket": ApiKind.WEBSOCKET,
    "webhook": ApiKind.WEBHOOK,
}

_LIFECYCLE_MAP: dict[str, ApiLifecycle] = {
    "design": ApiLifecycle.DESIGN,
    "development": ApiLifecycle.DEVELOPMENT,
    "testing": ApiLifecycle.TESTING,
    "preview": ApiLifecycle.PREVIEW,
    "production": ApiLifecycle.PRODUCTION,
    "deprecated": ApiLifecycle.DEPRECATED,
    "retired": ApiLifecycle.RETIRED,
}

_ENV_KIND_MAP: dict[str, EnvironmentKind] = {
    "development": EnvironmentKind.DEVELOPMENT,
    "staging": EnvironmentKind.STAGING,
    "testing": EnvironmentKind.TESTING,
    "production": EnvironmentKind.PRODUCTION,
}


def _get_attr(obj: Any, attr: str, default: Any = None) -> Any:
    """Retrieve *attr* from an object or dict, returning *default* on miss."""
    if isinstance(obj, dict):
        return obj.get(attr, default)
    return getattr(obj, attr, default)


def _iso_or_empty(dt: Any) -> str:
    """Convert a ``datetime`` (or string) to an ISO 8601 string.

    Returns an empty string if the value is ``None``.
    """
    if dt is None:
        return ""
    if isinstance(dt, datetime.datetime):
        return dt.isoformat()
    return str(dt)


def _map_api_kind(value: Any) -> ApiKind:
    if value is None:
        return ApiKind.REST
    normalized = str(value).lower()
    return _API_KIND_MAP.get(normalized, ApiKind.REST)


def _map_lifecycle(value: Any) -> ApiLifecycle:
    if value is None:
        return ApiLifecycle.DEVELOPMENT
    normalized = str(value).lower()
    return _LIFECYCLE_MAP.get(normalized, ApiLifecycle.DEVELOPMENT)


def _map_env_kind(value: Any) -> EnvironmentKind:
    if value is None:
        return EnvironmentKind.DEVELOPMENT
    normalized = str(value).lower()
    return _ENV_KIND_MAP.get(normalized, EnvironmentKind.DEVELOPMENT)


# ---------------------------------------------------------------------------
# Public mappers
# ---------------------------------------------------------------------------


def map_environment(raw: Any) -> ApiEnvironment:
    """Map an API Center environment data-plane dict → :class:`ApiEnvironment`."""
    return ApiEnvironment(
        id=str(_get_attr(raw, "name") or _get_attr(raw, "id") or ""),
        name=str(_get_attr(raw, "name") or ""),
        title=str(_get_attr(raw, "title") or _get_attr(raw, "name") or ""),
        description=_get_attr(raw, "description"),
        kind=_map_env_kind(_get_attr(raw, "kind")),
    )


def map_deployment(raw: Any) -> ApiDeployment:
    """Map an API Center deployment data-plane dict → :class:`ApiDeployment`."""
    # Data plane uses ``environmentId`` (camelCase resource path)
    raw_env = _get_attr(raw, "environmentId") or _get_attr(raw, "environment_id") or _get_attr(raw, "environment") or {}
    if isinstance(raw_env, str):
        # environmentId is a resource path string — extract the last segment
        env_id = raw_env.split("/")[-1] if raw_env else ""
        environment = ApiEnvironment(
            id=env_id,
            name=env_id,
            title=env_id,
            kind=EnvironmentKind.DEVELOPMENT,
        )
    else:
        environment = map_environment(raw_env)

    raw_server = _get_attr(raw, "server") or {}
    # Data plane: ``runtimeUri`` (camelCase); SDK: ``runtime_uri``
    runtime_uri_raw = _get_attr(raw_server, "runtimeUri") or _get_attr(raw_server, "runtime_uri") or []
    runtime_uri = list(runtime_uri_raw) if runtime_uri_raw else []

    # Data plane: ``lastUpdated`` at top level; SDK: ``system_data``
    system_data = _get_attr(raw, "system_data") or {}
    created_at = _iso_or_empty(
        _get_attr(raw, "created_at")
        or _get_attr(raw, "createdAt")
        or _get_attr(system_data, "created_at")
        or _get_attr(system_data, "createdAt")
    )
    updated_at = _iso_or_empty(
        _get_attr(raw, "updated_at")
        or _get_attr(raw, "lastUpdated")
        or _get_attr(system_data, "last_modified_at")
        or _get_attr(system_data, "lastModifiedAt")
    )

    return ApiDeployment(
        id=str(_get_attr(raw, "name") or _get_attr(raw, "id") or ""),
        title=str(_get_attr(raw, "title") or _get_attr(raw, "name") or ""),
        description=_get_attr(raw, "description"),
        environment=environment,
        server=DeploymentServer(runtime_uri=runtime_uri),
        created_at=created_at,
        updated_at=updated_at,
    )


def map_api_version(raw: Any) -> ApiVersion:
    """Map an API Center API version data-plane dict → :class:`ApiVersion`."""
    system_data = _get_attr(raw, "system_data") or {}
    created_at = _iso_or_empty(
        _get_attr(raw, "created_at")
        or _get_attr(raw, "createdAt")
        or _get_attr(system_data, "created_at")
        or _get_attr(system_data, "createdAt")
    )
    updated_at = _iso_or_empty(
        _get_attr(raw, "updated_at")
        or _get_attr(raw, "lastUpdated")
        or _get_attr(system_data, "last_modified_at")
        or _get_attr(system_data, "lastModifiedAt")
    )

    return ApiVersion(
        id=str(_get_attr(raw, "name") or _get_attr(raw, "id") or ""),
        name=str(_get_attr(raw, "name") or ""),
        title=str(_get_attr(raw, "title") or _get_attr(raw, "name") or ""),
        lifecycle_stage=_map_lifecycle(_get_attr(raw, "lifecycleStage") or _get_attr(raw, "lifecycle_stage")),
        created_at=created_at,
        updated_at=updated_at,
    )


def map_api_specification(raw: Any, content: str | None = None) -> ApiSpecification:
    """Map an API Center definition data-plane dict → :class:`ApiSpecification`."""
    spec_info = _get_attr(raw, "specification") or {}
    return ApiSpecification(
        id=str(_get_attr(raw, "name") or _get_attr(raw, "id") or ""),
        name=str(_get_attr(raw, "name") or ""),
        title=str(_get_attr(raw, "title") or _get_attr(raw, "name") or ""),
        specification_type=_get_attr(spec_info, "name"),
        specification_version=_get_attr(spec_info, "version"),
        content=content,
    )


def map_api_definition(
    raw: Any,
    versions: list[ApiVersion] | None = None,
    deployments: list[ApiDeployment] | None = None,
) -> ApiDefinition:
    """Map an API Center API data-plane dict → :class:`ApiDefinition`.

    *versions* and *deployments* are pre-fetched lists that are embedded into
    the definition.  Pass empty lists (the default) to omit them.
    """
    system_data = _get_attr(raw, "system_data") or {}
    created_at = _iso_or_empty(
        _get_attr(raw, "created_at")
        or _get_attr(raw, "createdAt")
        or _get_attr(system_data, "created_at")
        or _get_attr(system_data, "createdAt")
    )
    updated_at = _iso_or_empty(
        _get_attr(raw, "updated_at")
        or _get_attr(raw, "lastUpdated")
        or _get_attr(system_data, "last_modified_at")
        or _get_attr(system_data, "lastModifiedAt")
    )

    # contacts
    raw_contacts = _get_attr(raw, "contacts") or []
    contacts: list[Contact] = []
    for c in raw_contacts:
        try:
            contacts.append(
                Contact(
                    name=str(_get_attr(c, "name") or ""),
                    email=_get_attr(c, "email"),
                    url=_get_attr(c, "url"),
                )
            )
        except Exception:
            logger.debug("Failed to map contact entry", exc_info=True)

    # externalDocumentation (data plane camelCase) / external_docs (SDK)
    raw_ext_docs = (
        _get_attr(raw, "externalDocumentation")
        or _get_attr(raw, "external_docs")
        or _get_attr(raw, "externalDocs")
        or []
    )
    external_docs: list[ExternalDoc] = []
    for d in raw_ext_docs:
        try:
            external_docs.append(
                ExternalDoc(
                    title=str(_get_attr(d, "title") or ""),
                    url=str(_get_attr(d, "url") or ""),
                    description=_get_attr(d, "description"),
                )
            )
        except Exception:
            logger.debug("Failed to map external doc entry", exc_info=True)

    # customProperties (data plane camelCase) / custom_properties (SDK)
    raw_custom = _get_attr(raw, "customProperties") or _get_attr(raw, "custom_properties") or {}
    custom_properties: dict[str, object] = dict(raw_custom) if isinstance(raw_custom, dict) else {}

    # license / termsOfService
    license_info = _get_attr(raw, "license") or {}
    license_url = _get_attr(license_info, "url") if license_info else None

    tos_info = _get_attr(raw, "termsOfService") or _get_attr(raw, "terms_of_service") or {}
    tos_url = _get_attr(tos_info, "url") if tos_info else None

    return ApiDefinition(
        id=str(_get_attr(raw, "name") or _get_attr(raw, "id") or ""),
        name=str(_get_attr(raw, "name") or ""),
        title=str(_get_attr(raw, "title") or _get_attr(raw, "name") or ""),
        description=str(_get_attr(raw, "description") or ""),
        kind=_map_api_kind(_get_attr(raw, "kind")),
        lifecycle_stage=_map_lifecycle(_get_attr(raw, "lifecycleStage") or _get_attr(raw, "lifecycle_stage")),
        terms_of_service=tos_url,
        license=license_url,
        external_docs=external_docs,
        contacts=contacts,
        custom_properties=custom_properties,
        versions=versions or [],
        deployments=deployments or [],
        created_at=created_at,
        updated_at=updated_at,
    )
