"""Unit tests for the API Center data mapper."""

from __future__ import annotations

from types import SimpleNamespace

from apic_vibe_portal_bff.clients.api_center_mapper import (
    map_api_definition,
    map_api_specification,
    map_api_version,
    map_deployment,
    map_environment,
)
from apic_vibe_portal_bff.models.api_center import (
    ApiKind,
    ApiLifecycle,
    EnvironmentKind,
)
from tests.api_center_mocks import (
    MOCK_API_DEFINITIONS,
    MOCK_APIS,
    MOCK_DEPLOYMENTS,
    MOCK_ENVIRONMENTS,
    MOCK_VERSIONS,
    make_api,
    make_api_spec_definition,
    make_api_version,
    make_deployment,
    make_environment,
)


def _ns(**kwargs: object) -> SimpleNamespace:
    return SimpleNamespace(**kwargs)


# ---------------------------------------------------------------------------
# map_environment
# ---------------------------------------------------------------------------


class TestMapEnvironment:
    def test_maps_basic_fields(self) -> None:
        raw = make_environment(name="prod-env", title="Production", kind="production")
        env = map_environment(raw)
        assert env.id == "prod-env"
        assert env.name == "prod-env"
        assert env.title == "Production"
        assert env.kind == EnvironmentKind.PRODUCTION

    def test_maps_all_env_kinds(self) -> None:
        for kind_str, expected in [
            ("development", EnvironmentKind.DEVELOPMENT),
            ("staging", EnvironmentKind.STAGING),
            ("testing", EnvironmentKind.TESTING),
            ("production", EnvironmentKind.PRODUCTION),
        ]:
            env = map_environment(make_environment(kind=kind_str))
            assert env.kind == expected

    def test_unknown_kind_defaults_to_development(self) -> None:
        raw = make_environment(kind="unknown-kind")
        env = map_environment(raw)
        assert env.kind == EnvironmentKind.DEVELOPMENT

    def test_none_kind_defaults_to_development(self) -> None:
        raw = make_environment(kind=None)  # type: ignore[arg-type]
        env = map_environment(raw)
        assert env.kind == EnvironmentKind.DEVELOPMENT

    def test_description_can_be_none(self) -> None:
        raw = make_environment(description=None)
        env = map_environment(raw)
        assert env.description is None

    def test_maps_all_mock_environments(self) -> None:
        for raw in MOCK_ENVIRONMENTS:
            env = map_environment(raw)
            assert env.id
            assert env.name


# ---------------------------------------------------------------------------
# map_deployment
# ---------------------------------------------------------------------------


class TestMapDeployment:
    def test_maps_basic_fields(self) -> None:
        raw = make_deployment(name="dep-v1", title="v1 Deployment", runtime_uri=["https://api.example.com/v1"])
        dep = map_deployment(raw)
        assert dep.id == "dep-v1"
        assert dep.title == "v1 Deployment"
        assert dep.server.runtime_uri == ["https://api.example.com/v1"]

    def test_environment_id_string_parsed(self) -> None:
        raw = make_deployment(
            environment_id=(
                "/subscriptions/sub/resourceGroups/rg/providers/Microsoft.ApiCenter/services/svc/environments/prod-env"
            )
        )
        dep = map_deployment(raw)
        assert dep.environment.id == "prod-env"

    def test_environment_object_mapped(self) -> None:
        env_obj = make_environment(name="staging-env", kind="staging")
        raw = _ns(
            name="dep-1",
            title="Dep 1",
            description=None,
            environment=env_obj,
            environment_id=None,
            server=_ns(runtime_uri=[]),
            system_data=None,
        )
        dep = map_deployment(raw)
        assert dep.environment.kind == EnvironmentKind.STAGING

    def test_missing_runtime_uri_defaults_to_empty_list(self) -> None:
        raw = make_deployment(runtime_uri=[])
        dep = map_deployment(raw)
        assert dep.server.runtime_uri == []

    def test_description_can_be_none(self) -> None:
        raw = make_deployment(description=None)
        dep = map_deployment(raw)
        assert dep.description is None

    def test_maps_all_mock_deployments(self) -> None:
        for raw in MOCK_DEPLOYMENTS:
            dep = map_deployment(raw)
            assert dep.id


# ---------------------------------------------------------------------------
# map_api_version
# ---------------------------------------------------------------------------


class TestMapApiVersion:
    def test_maps_basic_fields(self) -> None:
        raw = make_api_version(name="v1", title="Version 1", lifecycle_stage="production")
        ver = map_api_version(raw)
        assert ver.id == "v1"
        assert ver.name == "v1"
        assert ver.title == "Version 1"
        assert ver.lifecycle_stage == ApiLifecycle.PRODUCTION

    def test_maps_all_lifecycle_stages(self) -> None:
        for stage_str, expected in [
            ("design", ApiLifecycle.DESIGN),
            ("development", ApiLifecycle.DEVELOPMENT),
            ("testing", ApiLifecycle.TESTING),
            ("preview", ApiLifecycle.PREVIEW),
            ("production", ApiLifecycle.PRODUCTION),
            ("deprecated", ApiLifecycle.DEPRECATED),
            ("retired", ApiLifecycle.RETIRED),
        ]:
            raw = make_api_version(lifecycle_stage=stage_str)
            ver = map_api_version(raw)
            assert ver.lifecycle_stage == expected

    def test_unknown_lifecycle_defaults_to_development(self) -> None:
        raw = make_api_version(lifecycle_stage="unknown")
        ver = map_api_version(raw)
        assert ver.lifecycle_stage == ApiLifecycle.DEVELOPMENT

    def test_system_data_provides_timestamps(self) -> None:
        raw = make_api_version(name="v1", lifecycle_stage="production")
        ver = map_api_version(raw)
        assert ver.created_at  # non-empty

    def test_maps_all_mock_versions(self) -> None:
        for raw in MOCK_VERSIONS:
            ver = map_api_version(raw)
            assert ver.id


# ---------------------------------------------------------------------------
# map_api_specification
# ---------------------------------------------------------------------------


class TestMapApiSpecification:
    def test_maps_basic_fields(self) -> None:
        raw = make_api_spec_definition(
            name="openapi", title="OpenAPI Definition", spec_name="openapi", spec_version="3.0.1"
        )
        spec = map_api_specification(raw)
        assert spec.id == "openapi"
        assert spec.name == "openapi"
        assert spec.title == "OpenAPI Definition"
        assert spec.specification_type == "openapi"
        assert spec.specification_version == "3.0.1"
        assert spec.content is None

    def test_content_is_embedded_when_provided(self) -> None:
        raw = make_api_spec_definition()
        content = '{"openapi": "3.0.1"}'
        spec = map_api_specification(raw, content=content)
        assert spec.content == content

    def test_maps_all_mock_definitions(self) -> None:
        for raw in MOCK_API_DEFINITIONS:
            spec = map_api_specification(raw)
            assert spec.id


# ---------------------------------------------------------------------------
# map_api_definition
# ---------------------------------------------------------------------------


class TestMapApiDefinition:
    def test_maps_basic_fields(self) -> None:
        raw = make_api(name="petstore-api", title="Petstore API", kind="rest", lifecycle_stage="production")
        defn = map_api_definition(raw)
        assert defn.id == "petstore-api"
        assert defn.name == "petstore-api"
        assert defn.title == "Petstore API"
        assert defn.kind == ApiKind.REST
        assert defn.lifecycle_stage == ApiLifecycle.PRODUCTION

    def test_maps_all_api_kinds(self) -> None:
        for kind_str, expected in [
            ("rest", ApiKind.REST),
            ("graphql", ApiKind.GRAPHQL),
            ("grpc", ApiKind.GRPC),
            ("soap", ApiKind.SOAP),
            ("websocket", ApiKind.WEBSOCKET),
            ("webhook", ApiKind.WEBHOOK),
        ]:
            raw = make_api(kind=kind_str)
            defn = map_api_definition(raw)
            assert defn.kind == expected

    def test_unknown_kind_defaults_to_rest(self) -> None:
        raw = make_api(kind="unknown")
        defn = map_api_definition(raw)
        assert defn.kind == ApiKind.REST

    def test_contacts_mapped(self) -> None:
        raw = make_api(contacts=[_ns(name="Team", email="team@example.com", url="https://example.com")])
        defn = map_api_definition(raw)
        assert len(defn.contacts) == 1
        assert defn.contacts[0].name == "Team"
        assert defn.contacts[0].email == "team@example.com"

    def test_external_docs_mapped(self) -> None:
        raw = make_api(external_docs=[_ns(title="Guide", url="https://guide.example.com", description="A guide")])
        defn = map_api_definition(raw)
        assert len(defn.external_docs) == 1
        assert defn.external_docs[0].title == "Guide"

    def test_custom_properties_mapped(self) -> None:
        raw = make_api(custom_properties={"team": "platform", "tier": "internal"})
        defn = map_api_definition(raw)
        assert defn.custom_properties["team"] == "platform"

    def test_versions_and_deployments_embedded(self) -> None:
        from apic_vibe_portal_bff.clients.api_center_mapper import map_api_version, map_deployment

        raw = make_api()
        versions = [map_api_version(v) for v in MOCK_VERSIONS]
        deployments = [map_deployment(d) for d in MOCK_DEPLOYMENTS]
        defn = map_api_definition(raw, versions=versions, deployments=deployments)
        assert len(defn.versions) == len(MOCK_VERSIONS)
        assert len(defn.deployments) == len(MOCK_DEPLOYMENTS)

    def test_empty_versions_and_deployments_by_default(self) -> None:
        raw = make_api()
        defn = map_api_definition(raw)
        assert defn.versions == []
        assert defn.deployments == []

    def test_license_url_extracted(self) -> None:
        raw = make_api(license_url="https://opensource.org/licenses/MIT")
        defn = map_api_definition(raw)
        assert defn.license == "https://opensource.org/licenses/MIT"

    def test_tos_url_extracted(self) -> None:
        raw = make_api(tos_url="https://example.com/tos")
        defn = map_api_definition(raw)
        assert defn.terms_of_service == "https://example.com/tos"

    def test_null_license_and_tos_become_none(self) -> None:
        raw = make_api()
        defn = map_api_definition(raw)
        assert defn.license is None
        assert defn.terms_of_service is None

    def test_maps_all_mock_apis(self) -> None:
        for raw in MOCK_APIS:
            defn = map_api_definition(raw)
            assert defn.id

    def test_missing_description_defaults_to_empty_string(self) -> None:
        raw = make_api(description=None)
        defn = map_api_definition(raw)
        assert defn.description == ""

    def test_timestamps_from_system_data(self) -> None:
        raw = make_api()
        defn = map_api_definition(raw)
        assert defn.created_at  # non-empty
        assert defn.updated_at  # non-empty
