"""Unit tests for MetadataCompletenessService."""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from apic_vibe_portal_bff.services.metadata_completeness_service import (
    MetadataCompletenessService,
    _grade_from_score,
)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_mock_api(
    api_id: str,
    title: str | None = None,
    description: str = "",
    contacts: list | None = None,
    versions: list | None = None,
    deployments: list | None = None,
    lifecycle_stage: str = "",
    custom_properties: dict | None = None,
    external_docs: list | None = None,
    license_val: str | None = None,
    terms_of_service: str | None = None,
    kind: str = "",
) -> dict:
    """Create a mock API dict matching the API Center shape."""
    api: dict = {
        "name": api_id,
        "title": title or api_id,
        "description": description,
        "contacts": contacts or [],
        "versions": versions or [],
        "deployments": deployments or [],
        "lifecycleStage": lifecycle_stage,
        "customProperties": custom_properties or {},
        "kind": kind,
    }
    if external_docs is not None:
        api["externalDocs"] = external_docs
    if license_val is not None:
        api["license"] = license_val
    if terms_of_service is not None:
        api["termsOfService"] = terms_of_service
    return api


def _make_fully_complete_api(api_id: str = "complete-api") -> dict:
    """Build an API dict with every field populated for maximum score."""
    return _make_mock_api(
        api_id,
        title="Complete API",
        description="A" * 120,  # >100 chars
        contacts=[{"email": "team@example.com"}],
        versions=[
            {
                "name": "v1.0.0",
                "lifecycleStage": "production",
                "definitions": [
                    {"name": "openapi.yaml", "specification": "OpenAPI", "content": "x"},
                    {"name": "schema.json", "specification": "JSON Schema", "content": "y"},
                ],
            },
            {
                "name": "v2.0.0",
                "lifecycleStage": "preview",
                "definitions": [],
            },
        ],
        deployments=[{"name": "prod-deployment", "title": "Production", "environmentId": "prod-env"}],
        lifecycle_stage="production",
        custom_properties={"category": "payments", "team": "platform"},
        external_docs=[{"url": "https://docs.example.com", "description": "Full API docs"}],
        license_val="MIT",
        terms_of_service="https://example.com/tos",
        kind="REST",
    )


def _make_service(
    apis: list[dict] | None = None,
) -> tuple[MetadataCompletenessService, MagicMock]:
    """Return a service wired to a mock ApiCenterClient."""
    mock_client = MagicMock()

    if apis is None:
        apis = []
    mock_client.list_apis.return_value = apis
    mock_client.list_api_versions.return_value = []
    mock_client.list_deployments.return_value = []
    mock_client.list_api_definitions.return_value = []

    service = MetadataCompletenessService(api_center_client=mock_client)
    return service, mock_client


# ---------------------------------------------------------------------------
# _grade_from_score
# ---------------------------------------------------------------------------


class TestGradeFromScore:
    def test_score_90_returns_a(self) -> None:
        assert _grade_from_score(90) == "A"

    def test_score_100_returns_a(self) -> None:
        assert _grade_from_score(100) == "A"

    def test_score_75_returns_b(self) -> None:
        assert _grade_from_score(75) == "B"

    def test_score_89_returns_b(self) -> None:
        assert _grade_from_score(89.9) == "B"

    def test_score_60_returns_c(self) -> None:
        assert _grade_from_score(60) == "C"

    def test_score_74_returns_c(self) -> None:
        assert _grade_from_score(74) == "C"

    def test_score_40_returns_d(self) -> None:
        assert _grade_from_score(40) == "D"

    def test_score_59_returns_d(self) -> None:
        assert _grade_from_score(59) == "D"

    def test_score_0_returns_f(self) -> None:
        assert _grade_from_score(0) == "F"

    def test_score_39_returns_f(self) -> None:
        assert _grade_from_score(39) == "F"


# ---------------------------------------------------------------------------
# Dimension scoring – basic_info
# ---------------------------------------------------------------------------


class TestScoreBasicInfo:
    def test_empty_api_scores_zero(self) -> None:
        api = _make_mock_api("x", description="")
        # title defaults to api_id ("x"), which still counts as present (+20).
        # Only description, contacts, termsOfService are empty → score is 20.
        service, _ = _make_service()
        assert service._score_basic_info(api) == 20.0

    def test_title_adds_20(self) -> None:
        api = _make_mock_api("x", title="My API", description="")
        service, _ = _make_service()
        assert service._score_basic_info(api) >= 20

    def test_short_description_adds_10(self) -> None:
        api = _make_mock_api("x", title="", description="Short")
        service, _ = _make_service()
        assert service._score_basic_info(api) >= 10

    def test_medium_description_adds_30(self) -> None:
        api = _make_mock_api("x", title="", description="A" * 50)
        service, _ = _make_service()
        assert service._score_basic_info(api) >= 30

    def test_long_description_adds_40(self) -> None:
        api = _make_mock_api("x", title="", description="A" * 100)
        service, _ = _make_service()
        assert service._score_basic_info(api) >= 40

    def test_contacts_with_email_add_30(self) -> None:
        api = _make_mock_api("x", title="", description="", contacts=[{"email": "a@b.com"}])
        service, _ = _make_service()
        assert service._score_basic_info(api) >= 30

    def test_terms_of_service_adds_10(self) -> None:
        api = _make_mock_api("x", title="", description="", terms_of_service="https://tos.example.com")
        service, _ = _make_service()
        assert service._score_basic_info(api) >= 10

    def test_fully_populated_basic_info(self) -> None:
        api = _make_mock_api(
            "x",
            title="API",
            description="A" * 100,
            contacts=[{"email": "a@b.com"}],
            terms_of_service="https://tos.example.com",
        )
        service, _ = _make_service()
        assert service._score_basic_info(api) == 100


# ---------------------------------------------------------------------------
# Dimension scoring – versioning
# ---------------------------------------------------------------------------


class TestScoreVersioning:
    def test_no_versions_scores_zero(self) -> None:
        api = _make_mock_api("x")
        service, _ = _make_service()
        assert service._score_versioning(api) == 0.0

    def test_one_version_adds_30(self) -> None:
        api = _make_mock_api("x", versions=[{"name": "v1", "lifecycleStage": ""}])
        service, _ = _make_service()
        assert service._score_versioning(api) >= 30

    def test_two_versions_add_bonus(self) -> None:
        api = _make_mock_api(
            "x",
            versions=[
                {"name": "v1", "lifecycleStage": ""},
                {"name": "v2", "lifecycleStage": ""},
            ],
        )
        service, _ = _make_service()
        assert service._score_versioning(api) >= 40

    def test_production_lifecycle_adds_20(self) -> None:
        api = _make_mock_api("x", versions=[{"name": "v1", "lifecycleStage": "production"}])
        service, _ = _make_service()
        assert service._score_versioning(api) >= 50

    def test_semver_adds_20(self) -> None:
        api = _make_mock_api("x", versions=[{"name": "v1.0.0", "lifecycleStage": ""}])
        service, _ = _make_service()
        assert service._score_versioning(api) >= 50

    def test_fully_populated_versioning(self) -> None:
        api = _make_mock_api(
            "x",
            versions=[
                {"name": "v1.0.0", "lifecycleStage": "production"},
                {"name": "v2.0.0", "lifecycleStage": "preview"},
            ],
        )
        service, _ = _make_service()
        assert service._score_versioning(api) == 100


# ---------------------------------------------------------------------------
# Dimension scoring – specification
# ---------------------------------------------------------------------------


class TestScoreSpecification:
    def test_no_definitions_scores_zero(self) -> None:
        api = _make_mock_api("x", versions=[{"name": "v1", "definitions": []}])
        service, _ = _make_service()
        assert service._score_specification(api) == 0.0

    def test_one_definition_adds_40(self) -> None:
        api = _make_mock_api("x", versions=[{"name": "v1", "definitions": [{"name": "openapi.yaml"}]}])
        service, _ = _make_service()
        assert service._score_specification(api) >= 40

    def test_definition_with_spec_and_content(self) -> None:
        api = _make_mock_api(
            "x",
            versions=[
                {
                    "name": "v1",
                    "definitions": [{"name": "openapi.yaml", "specification": "OpenAPI", "content": "x"}],
                }
            ],
        )
        service, _ = _make_service()
        assert service._score_specification(api) >= 80

    def test_two_definitions_scores_100(self) -> None:
        api = _make_mock_api(
            "x",
            versions=[
                {
                    "name": "v1",
                    "definitions": [
                        {"name": "openapi.yaml", "specification": "OpenAPI", "content": "x"},
                        {"name": "schema.json", "specification": "JSON Schema", "content": "y"},
                    ],
                }
            ],
        )
        service, _ = _make_service()
        assert service._score_specification(api) == 100


# ---------------------------------------------------------------------------
# Dimension scoring – documentation
# ---------------------------------------------------------------------------


class TestScoreDocumentation:
    def test_no_docs_scores_zero(self) -> None:
        api = _make_mock_api("x")
        service, _ = _make_service()
        assert service._score_documentation(api) == 0.0

    def test_external_docs_add_30(self) -> None:
        api = _make_mock_api("x", external_docs=[{"url": "https://docs.example.com"}])
        service, _ = _make_service()
        assert service._score_documentation(api) >= 30

    def test_external_docs_with_description_add_50(self) -> None:
        api = _make_mock_api(
            "x",
            external_docs=[{"url": "https://docs.example.com", "description": "Full docs"}],
        )
        service, _ = _make_service()
        assert service._score_documentation(api) >= 50

    def test_license_adds_25(self) -> None:
        api = _make_mock_api("x", license_val="MIT")
        service, _ = _make_service()
        assert service._score_documentation(api) >= 25

    def test_fully_populated_documentation(self) -> None:
        api = _make_mock_api(
            "x",
            external_docs=[{"url": "https://docs.example.com", "description": "Full docs"}],
            license_val="MIT",
            terms_of_service="https://tos.example.com",
        )
        service, _ = _make_service()
        assert service._score_documentation(api) == 100


# ---------------------------------------------------------------------------
# Dimension scoring – classification
# ---------------------------------------------------------------------------


class TestScoreClassification:
    def test_empty_classification_scores_zero(self) -> None:
        api = _make_mock_api("x")
        service, _ = _make_service()
        assert service._score_classification(api) == 0.0

    def test_one_custom_property_adds_30(self) -> None:
        api = _make_mock_api("x", custom_properties={"category": "payments"})
        service, _ = _make_service()
        assert service._score_classification(api) >= 30

    def test_two_custom_properties_add_50(self) -> None:
        api = _make_mock_api("x", custom_properties={"category": "payments", "team": "platform"})
        service, _ = _make_service()
        assert service._score_classification(api) >= 50

    def test_lifecycle_stage_adds_30(self) -> None:
        api = _make_mock_api("x", lifecycle_stage="production")
        service, _ = _make_service()
        assert service._score_classification(api) >= 30

    def test_design_lifecycle_does_not_score(self) -> None:
        api = _make_mock_api("x", lifecycle_stage="design")
        service, _ = _make_service()
        # "design" is excluded from lifecycle scoring
        assert service._score_classification(api) == 0.0

    def test_kind_adds_20(self) -> None:
        api = _make_mock_api("x", kind="REST")
        service, _ = _make_service()
        assert service._score_classification(api) >= 20

    def test_fully_populated_classification(self) -> None:
        api = _make_mock_api(
            "x",
            custom_properties={"a": "1", "b": "2"},
            lifecycle_stage="production",
            kind="REST",
        )
        service, _ = _make_service()
        assert service._score_classification(api) == 100


# ---------------------------------------------------------------------------
# Dimension scoring – security
# ---------------------------------------------------------------------------


class TestScoreSecurity:
    def test_no_deployments_scores_zero(self) -> None:
        api = _make_mock_api("x")
        service, _ = _make_service()
        assert service._score_security(api) == 0.0

    def test_deployment_adds_30(self) -> None:
        api = _make_mock_api("x", deployments=[{"name": "staging"}])
        service, _ = _make_service()
        assert service._score_security(api) >= 30

    def test_prod_deployment_adds_60(self) -> None:
        api = _make_mock_api("x", deployments=[{"name": "prod-deployment"}])
        service, _ = _make_service()
        assert service._score_security(api) >= 60

    def test_contacts_add_20(self) -> None:
        api = _make_mock_api("x", contacts=[{"email": "sec@example.com"}])
        service, _ = _make_service()
        assert service._score_security(api) >= 20

    def test_license_adds_20(self) -> None:
        api = _make_mock_api("x", license_val="Apache-2.0")
        service, _ = _make_service()
        assert service._score_security(api) >= 20

    def test_fully_populated_security(self) -> None:
        api = _make_mock_api(
            "x",
            deployments=[{"name": "prod-deployment"}],
            contacts=[{"email": "sec@example.com"}],
            license_val="MIT",
        )
        service, _ = _make_service()
        assert service._score_security(api) == 100


# ---------------------------------------------------------------------------
# get_score
# ---------------------------------------------------------------------------


class TestGetScore:
    def test_returns_score_for_single_api(self) -> None:
        api = _make_mock_api("api-1", title="Test API", description="OAuth")
        service, mock_client = _make_service()
        mock_client.get_api.return_value = api

        result = service.get_score("api-1")

        assert result["apiId"] == "api-1"
        assert result["apiName"] == "Test API"
        assert "overallScore" in result
        assert "grade" in result
        assert "dimensions" in result
        assert "lastChecked" in result

    def test_dimensions_contain_all_six_keys(self) -> None:
        api = _make_mock_api("api-1")
        service, mock_client = _make_service()
        mock_client.get_api.return_value = api

        result = service.get_score("api-1")

        dim_keys = {d["key"] for d in result["dimensions"]}
        assert dim_keys == {"basicInfo", "versioning", "specification", "documentation", "classification", "security"}

    def test_fully_complete_api_scores_high(self) -> None:
        api = _make_fully_complete_api("api-1")
        service, mock_client = _make_service()
        mock_client.get_api.return_value = api
        # _enrich_api overwrites versions/deployments from the client;
        # return the same rich data so scores stay high.
        mock_client.list_api_versions.return_value = api["versions"]
        mock_client.list_deployments.return_value = api["deployments"]
        mock_client.list_api_definitions.return_value = api["versions"][0].get("definitions", [])

        result = service.get_score("api-1")

        assert result["overallScore"] >= 80
        assert result["grade"] in ("A", "B")

    def test_raises_permission_error_when_not_accessible(self) -> None:
        service, _ = _make_service()

        with pytest.raises(PermissionError, match="Access denied"):
            service.get_score("api-1", accessible_api_ids=["api-2"])

    def test_raises_value_error_when_api_not_found(self) -> None:
        service, mock_client = _make_service()
        mock_client.get_api.side_effect = Exception("Not found")

        with pytest.raises(ValueError, match="API not found"):
            service.get_score("api-1")


# ---------------------------------------------------------------------------
# get_overview
# ---------------------------------------------------------------------------


class TestGetOverview:
    def test_returns_empty_overview_when_no_apis(self) -> None:
        service, _ = _make_service(apis=[])

        result = service.get_overview()

        assert result["averageScore"] == 0.0
        assert result["averageGrade"] == "F"
        assert result["totalApis"] == 0
        assert result["distribution"] == {"A": 0, "B": 0, "C": 0, "D": 0, "F": 0}
        assert result["dimensionAverages"] == []

    def test_returns_overview_for_multiple_apis(self) -> None:
        apis = [
            _make_mock_api("api-1", title="API One", description="A" * 100),
            _make_mock_api("api-2", title="API Two", description="Short"),
        ]
        service, _ = _make_service(apis=apis)

        result = service.get_overview()

        assert result["totalApis"] == 2
        assert result["averageScore"] > 0
        assert result["averageGrade"] in ("A", "B", "C", "D", "F")
        assert sum(result["distribution"].values()) == 2
        assert len(result["dimensionAverages"]) == 6

    def test_respects_accessible_api_ids(self) -> None:
        apis = [
            _make_mock_api("api-1"),
            _make_mock_api("api-2"),
            _make_mock_api("api-3"),
        ]
        service, _ = _make_service(apis=apis)

        result = service.get_overview(accessible_api_ids=["api-1", "api-3"])

        assert result["totalApis"] == 2

    def test_dimension_averages_have_correct_structure(self) -> None:
        apis = [_make_mock_api("api-1", description="Hello")]
        service, _ = _make_service(apis=apis)

        result = service.get_overview()

        for dim in result["dimensionAverages"]:
            assert "key" in dim
            assert "name" in dim
            assert "weight" in dim
            assert "averageScore" in dim


# ---------------------------------------------------------------------------
# get_leaderboard
# ---------------------------------------------------------------------------


class TestGetLeaderboard:
    def test_returns_empty_when_no_apis(self) -> None:
        service, _ = _make_service(apis=[])

        result = service.get_leaderboard()

        assert result == {"top": [], "bottom": []}

    def test_returns_top_and_bottom_apis(self) -> None:
        apis = [_make_mock_api(f"api-{i}", title=f"API {i}", description="A" * (i * 20)) for i in range(1, 8)]
        service, _ = _make_service(apis=apis)

        result = service.get_leaderboard()

        assert len(result["top"]) <= 5
        assert len(result["bottom"]) <= 5

    def test_top_is_sorted_descending(self) -> None:
        apis = [
            _make_mock_api("api-low", description=""),
            _make_mock_api("api-high", description="A" * 100, contacts=[{"email": "a@b.com"}]),
        ]
        service, _ = _make_service(apis=apis)

        result = service.get_leaderboard()

        top = result["top"]
        for i in range(len(top) - 1):
            assert top[i]["score"] >= top[i + 1]["score"]

    def test_leaderboard_entries_have_correct_fields(self) -> None:
        apis = [_make_mock_api("api-1", title="Test")]
        service, _ = _make_service(apis=apis)

        result = service.get_leaderboard()

        entry = result["top"][0]
        assert "apiId" in entry
        assert "apiName" in entry
        assert "score" in entry
        assert "grade" in entry

    def test_respects_accessible_api_ids(self) -> None:
        apis = [
            _make_mock_api("api-1"),
            _make_mock_api("api-2"),
        ]
        service, _ = _make_service(apis=apis)

        result = service.get_leaderboard(accessible_api_ids=["api-1"])

        all_ids = [e["apiId"] for e in result["top"] + result["bottom"]]
        assert "api-2" not in all_ids


# ---------------------------------------------------------------------------
# Edge cases
# ---------------------------------------------------------------------------


class TestEdgeCases:
    def test_api_with_none_contacts(self) -> None:
        api = _make_mock_api("x", contacts=None)
        service, _ = _make_service()
        # Should not raise
        assert service._score_basic_info(api) >= 0

    def test_api_with_none_versions(self) -> None:
        api = _make_mock_api("x", versions=None)
        service, _ = _make_service()
        assert service._score_versioning(api) == 0.0

    def test_api_with_none_deployments(self) -> None:
        api = _make_mock_api("x", deployments=None)
        service, _ = _make_service()
        assert service._score_security(api) >= 0

    def test_score_dimension_unknown_key(self) -> None:
        service, _ = _make_service()
        api = _make_mock_api("x")
        assert service._score_dimension("nonexistent", api) == 0.0

    def test_build_score_clamps_to_0_100(self) -> None:
        api = _make_mock_api("x")
        service, _ = _make_service()
        result = service._build_score(api)
        assert 0 <= result["overallScore"] <= 100
        for dim in result["dimensions"]:
            assert 0 <= dim["score"] <= 100
