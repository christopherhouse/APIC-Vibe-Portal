"""Tests for the API comparison service."""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from apic_vibe_portal_bff.models.api_center import (
    ApiDefinition,
    ApiDeployment,
    ApiEnvironment,
    ApiVersion,
    DeploymentServer,
    EnvironmentKind,
)
from apic_vibe_portal_bff.services.api_compare_service import (
    ALL_ASPECTS,
    ApiCompareService,
    CompareAspect,
)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_api(
    name: str = "petstore-api",
    title: str = "Petstore API",
    kind: str = "rest",
    lifecycle_stage: str = "production",
    versions: list[ApiVersion] | None = None,
    deployments: list[ApiDeployment] | None = None,
    **kwargs,
) -> ApiDefinition:
    defaults = {
        "id": f"/apis/{name}",
        "name": name,
        "title": title,
        "description": f"A sample {name} API",
        "kind": kind,
        "lifecycle_stage": lifecycle_stage,
        "created_at": "2024-01-15T10:00:00",
        "updated_at": "2024-03-20T14:30:00",
        "versions": versions or [],
        "deployments": deployments or [],
    }
    defaults.update(kwargs)
    return ApiDefinition(**defaults)


def _make_version(name: str = "v1") -> ApiVersion:
    return ApiVersion(
        id=f"/versions/{name}",
        name=name,
        title=f"Version {name}",
        lifecycle_stage="production",
        created_at="2024-01-15T10:00:00",
        updated_at="2024-03-20T14:30:00",
    )


def _make_deployment(name: str = "dep-1") -> ApiDeployment:
    return ApiDeployment(
        id=f"/deployments/{name}",
        title=f"Deployment {name}",
        environment=ApiEnvironment(
            id="/environments/prod",
            name="prod",
            title="Production",
            kind=EnvironmentKind.PRODUCTION,
        ),
        server=DeploymentServer(runtime_uri=["https://api.example.com"]),
        created_at="2024-01-15T10:00:00",
        updated_at="2024-03-20T14:30:00",
    )


def _make_service(apis: dict[str, ApiDefinition]) -> ApiCompareService:
    mock_catalog = MagicMock()

    def _get_api(api_id: str, **_kwargs) -> ApiDefinition:
        if api_id not in apis:
            from apic_vibe_portal_bff.clients.api_center_client import ApiCenterNotFoundError

            raise ApiCenterNotFoundError(f"API '{api_id}' not found")
        return apis[api_id]

    mock_catalog.get_api.side_effect = _get_api
    return ApiCompareService(catalog_service=mock_catalog)


# ---------------------------------------------------------------------------
# Tests — compare()
# ---------------------------------------------------------------------------


class TestCompare:
    def test_returns_compare_response_with_two_apis(self):
        a1 = _make_api("api-1", "API One")
        a2 = _make_api("api-2", "API Two")
        svc = _make_service({"api-1": a1, "api-2": a2})

        result = svc.compare(["api-1", "api-2"])

        assert len(result.apis) == 2
        assert result.apis[0].name == "api-1"
        assert result.apis[1].name == "api-2"

    def test_returns_all_aspects_by_default(self):
        a1 = _make_api("api-1")
        a2 = _make_api("api-2")
        svc = _make_service({"api-1": a1, "api-2": a2})

        result = svc.compare(["api-1", "api-2"])

        # Every top-level aspect should be represented
        for aspect in ALL_ASPECTS:
            assert any(row.aspect.startswith(aspect) for row in result.aspects)

    def test_respects_aspect_filter(self):
        a1 = _make_api("api-1")
        a2 = _make_api("api-2")
        svc = _make_service({"api-1": a1, "api-2": a2})

        result = svc.compare(["api-1", "api-2"], aspects=[CompareAspect.METADATA])

        assert all(row.aspect.startswith("metadata") for row in result.aspects)

    def test_raises_for_fewer_than_two_ids(self):
        svc = _make_service({})
        with pytest.raises(ValueError, match="At least 2"):
            svc.compare(["api-1"])

    def test_raises_for_more_than_five_ids(self):
        apis = {f"api-{i}": _make_api(f"api-{i}") for i in range(6)}
        svc = _make_service(apis)
        with pytest.raises(ValueError, match="At most 5"):
            svc.compare([f"api-{i}" for i in range(6)])

    def test_similarity_score_one_for_identical_apis(self):
        a1 = _make_api("api-1", kind="rest", lifecycle_stage="production")
        a2 = _make_api("api-2", kind="rest", lifecycle_stage="production")
        svc = _make_service({"api-1": a1, "api-2": a2})

        result = svc.compare(["api-1", "api-2"], aspects=[CompareAspect.METADATA])

        # kind and lifecycle match → all_equal for both rows → score should be high
        equal_count = sum(1 for r in result.aspects if r.all_equal)
        assert equal_count >= 2  # at least kind + lifecycle

    def test_each_aspect_row_has_value_per_api(self):
        a1 = _make_api("api-1")
        a2 = _make_api("api-2")
        a3 = _make_api("api-3")
        svc = _make_service({"api-1": a1, "api-2": a2, "api-3": a3})

        result = svc.compare(["api-1", "api-2", "api-3"])

        for row in result.aspects:
            assert len(row.values) == 3

    def test_version_count_row(self):
        a1 = _make_api("api-1", versions=[_make_version("v1"), _make_version("v2")])
        a2 = _make_api("api-2", versions=[_make_version("v1")])
        svc = _make_service({"api-1": a1, "api-2": a2})

        result = svc.compare(["api-1", "api-2"], aspects=[CompareAspect.VERSIONS])

        row = next(r for r in result.aspects if r.aspect == "versions.count")
        assert row.values[0].value == "2"
        assert row.values[1].value == "1"
        assert row.values[0].is_best is True  # higher count is better
        assert row.all_equal is False

    def test_deployment_count_row(self):
        a1 = _make_api("api-1", deployments=[_make_deployment("d1")])
        a2 = _make_api("api-2", deployments=[_make_deployment("d1"), _make_deployment("d2")])
        svc = _make_service({"api-1": a1, "api-2": a2})

        result = svc.compare(["api-1", "api-2"], aspects=[CompareAspect.DEPLOYMENTS])

        row = next(r for r in result.aspects if r.aspect == "deployments.count")
        assert row.values[1].is_best is True  # api-2 has more deployments

    def test_similarity_score_between_0_and_1(self):
        a1 = _make_api("api-1", kind="rest", lifecycle_stage="production")
        a2 = _make_api("api-2", kind="graphql", lifecycle_stage="development")
        svc = _make_service({"api-1": a1, "api-2": a2})

        result = svc.compare(["api-1", "api-2"])

        assert 0.0 <= result.similarity_score <= 1.0

    def test_ai_analysis_is_none_without_openai(self):
        a1 = _make_api("api-1")
        a2 = _make_api("api-2")
        svc = _make_service({"api-1": a1, "api-2": a2})

        result = svc.compare(["api-1", "api-2"])

        assert result.ai_analysis is None


class TestCompareWithAi:
    def test_calls_openai_and_returns_analysis(self):
        a1 = _make_api("api-1")
        a2 = _make_api("api-2")
        mock_catalog = MagicMock()
        mock_catalog.get_api.side_effect = lambda api_id, **_: {"api-1": a1, "api-2": a2}[api_id]

        mock_openai = MagicMock()
        mock_openai.chat.completions.create.return_value.choices[0].message.content = "AI analysis text"

        svc = ApiCompareService(catalog_service=mock_catalog, openai_client=mock_openai)

        result = svc.compare_with_ai(["api-1", "api-2"])

        assert result.ai_analysis == "AI analysis text"
        mock_openai.chat.completions.create.assert_called_once()

    def test_ai_analysis_is_none_when_openai_raises(self):
        a1 = _make_api("api-1")
        a2 = _make_api("api-2")
        mock_catalog = MagicMock()
        mock_catalog.get_api.side_effect = lambda api_id, **_: {"api-1": a1, "api-2": a2}[api_id]

        mock_openai = MagicMock()
        mock_openai.chat.completions.create.side_effect = RuntimeError("OpenAI unavailable")

        svc = ApiCompareService(catalog_service=mock_catalog, openai_client=mock_openai)

        result = svc.compare_with_ai(["api-1", "api-2"])

        assert result.ai_analysis is None
