"""Unit tests for MetadataRecommendationsService."""

from __future__ import annotations

from unittest.mock import MagicMock

from apic_vibe_portal_bff.services.metadata_recommendations_service import (
    MetadataRecommendationsService,
)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_score_data(
    api_id: str = "test-api",
    api_name: str = "Test API",
    overall_score: float = 50.0,
    grade: str = "D",
    dimensions: list[dict] | None = None,
) -> dict:
    """Create a mock score data dict."""
    if dimensions is None:
        dimensions = [
            {"key": "basicInfo", "name": "Basic Info", "weight": 0.20, "score": 0.0},
            {"key": "versioning", "name": "Versioning", "weight": 0.15, "score": 0.0},
            {"key": "specification", "name": "Specification", "weight": 0.25, "score": 0.0},
            {"key": "documentation", "name": "Documentation", "weight": 0.15, "score": 0.0},
            {"key": "classification", "name": "Classification", "weight": 0.10, "score": 0.0},
            {"key": "security", "name": "Security", "weight": 0.15, "score": 0.0},
        ]
    return {
        "apiId": api_id,
        "apiName": api_name,
        "overallScore": overall_score,
        "grade": grade,
        "dimensions": dimensions,
        "lastChecked": "2024-06-01T00:00:00Z",
    }


def _make_api(
    api_id: str = "test-api",
    title: str = "Test API",
    description: str = "",
    contacts: list | None = None,
    terms_of_service: str = "",
    versions: list | None = None,
    deployments: list | None = None,
    external_docs: list | None = None,
    license_info: str = "",
    custom_properties: dict | None = None,
    lifecycle_stage: str = "",
    kind: str = "",
) -> dict:
    """Create a mock API dict."""
    api: dict = {
        "name": api_id,
        "title": title,
        "description": description,
        "contacts": contacts or [],
        "versions": versions or [],
        "deployments": deployments or [],
        "customProperties": custom_properties or {},
        "lifecycleStage": lifecycle_stage,
        "kind": kind,
    }
    if terms_of_service:
        api["termsOfService"] = terms_of_service
    if external_docs:
        api["externalDocs"] = external_docs
    if license_info:
        api["license"] = license_info
    return api


def _make_service(
    score_data: dict | None = None,
    api: dict | None = None,
) -> MetadataRecommendationsService:
    """Return a service wired to mock dependencies."""
    mock_scoring = MagicMock()
    mock_api_center = MagicMock()

    resolved_api = api or _make_api()
    mock_scoring.get_score.return_value = score_data or _make_score_data()
    mock_api_center.get_api.return_value = resolved_api

    # Wire version/deployment enrichment to reflect the API data
    versions = resolved_api.get("versions", [])
    mock_api_center.list_api_versions.return_value = versions
    mock_api_center.list_deployments.return_value = resolved_api.get("deployments", [])

    # Wire per-version definitions so _enrich_api preserves them
    def _list_definitions(api_id: str, version_name: str) -> list:
        for v in versions:
            if v.get("name") == version_name:
                return v.get("definitions", [])
        return []

    mock_api_center.list_api_definitions.side_effect = _list_definitions

    return MetadataRecommendationsService(
        metadata_completeness_service=mock_scoring,
        api_center_client=mock_api_center,
    )


# ---------------------------------------------------------------------------
# get_recommendations — general
# ---------------------------------------------------------------------------


class TestGetRecommendations:
    def test_returns_expected_top_level_keys(self) -> None:
        svc = _make_service()
        result = svc.get_recommendations("test-api")

        assert result["apiId"] == "test-api"
        assert result["apiName"] == "Test API"
        assert "overallScore" in result
        assert "grade" in result
        assert "recommendations" in result
        assert "generatedAt" in result

    def test_no_recommendations_for_perfect_scores(self) -> None:
        dimensions = [
            {"key": "basicInfo", "name": "Basic Info", "weight": 0.20, "score": 100.0},
            {"key": "versioning", "name": "Versioning", "weight": 0.15, "score": 100.0},
            {"key": "specification", "name": "Specification", "weight": 0.25, "score": 100.0},
            {"key": "documentation", "name": "Documentation", "weight": 0.15, "score": 100.0},
            {"key": "classification", "name": "Classification", "weight": 0.10, "score": 100.0},
            {"key": "security", "name": "Security", "weight": 0.15, "score": 100.0},
        ]
        score_data = _make_score_data(overall_score=100.0, grade="A", dimensions=dimensions)
        svc = _make_service(score_data=score_data)

        result = svc.get_recommendations("test-api")
        assert result["recommendations"] == []

    def test_recommendations_sorted_by_impact_descending(self) -> None:
        svc = _make_service()
        result = svc.get_recommendations("test-api")
        recs = result["recommendations"]

        impacts = [r["impact"] for r in recs]
        assert impacts == sorted(impacts, reverse=True)

    def test_recommendations_have_sequential_priorities(self) -> None:
        svc = _make_service()
        result = svc.get_recommendations("test-api")
        recs = result["recommendations"]

        priorities = [r["priority"] for r in recs]
        assert priorities == list(range(1, len(recs) + 1))

    def test_each_recommendation_has_required_fields(self) -> None:
        svc = _make_service()
        result = svc.get_recommendations("test-api")

        required = {"id", "dimension", "title", "description", "example", "impact", "effort", "priority"}
        for rec in result["recommendations"]:
            assert required.issubset(rec.keys()), f"Missing keys in {rec['id']}"

    def test_passes_accessible_api_ids_to_scoring(self) -> None:
        mock_scoring = MagicMock()
        mock_api_center = MagicMock()
        mock_scoring.get_score.return_value = _make_score_data(
            dimensions=[
                {"key": "basicInfo", "name": "Basic Info", "weight": 0.20, "score": 100.0},
                {"key": "versioning", "name": "Versioning", "weight": 0.15, "score": 100.0},
                {"key": "specification", "name": "Specification", "weight": 0.25, "score": 100.0},
                {"key": "documentation", "name": "Documentation", "weight": 0.15, "score": 100.0},
                {"key": "classification", "name": "Classification", "weight": 0.10, "score": 100.0},
                {"key": "security", "name": "Security", "weight": 0.15, "score": 100.0},
            ]
        )
        mock_api_center.get_api.return_value = _make_api()
        mock_api_center.list_api_versions.return_value = []
        mock_api_center.list_deployments.return_value = []

        svc = MetadataRecommendationsService(mock_scoring, mock_api_center)
        svc.get_recommendations("test-api", accessible_api_ids=["test-api"])

        mock_scoring.get_score.assert_called_once_with("test-api", ["test-api"])

    def test_handles_api_fetch_failure_gracefully(self) -> None:
        mock_scoring = MagicMock()
        mock_api_center = MagicMock()
        mock_scoring.get_score.return_value = _make_score_data()
        mock_api_center.get_api.side_effect = RuntimeError("boom")

        svc = MetadataRecommendationsService(mock_scoring, mock_api_center)
        result = svc.get_recommendations("test-api")

        assert "recommendations" in result
        assert result["apiId"] == "test-api"


# ---------------------------------------------------------------------------
# Basic Info recommendations
# ---------------------------------------------------------------------------


class TestBasicInfoRecommendations:
    def test_missing_description_generates_rec(self) -> None:
        svc = _make_service(api=_make_api(description=""))
        result = svc.get_recommendations("test-api")
        ids = [r["id"] for r in result["recommendations"]]
        assert "basic-info-description" in ids

    def test_short_description_generates_rec(self) -> None:
        svc = _make_service(api=_make_api(description="Too short"))
        result = svc.get_recommendations("test-api")
        ids = [r["id"] for r in result["recommendations"]]
        assert "basic-info-description" in ids

    def test_long_description_no_rec(self) -> None:
        long_desc = "A" * 100
        dims = [
            {"key": "basicInfo", "name": "Basic Info", "weight": 0.20, "score": 50.0},
        ]
        svc = _make_service(
            score_data=_make_score_data(dimensions=dims),
            api=_make_api(description=long_desc),
        )
        result = svc.get_recommendations("test-api")
        ids = [r["id"] for r in result["recommendations"]]
        assert "basic-info-description" not in ids

    def test_no_contacts_generates_rec(self) -> None:
        svc = _make_service(api=_make_api(contacts=[]))
        result = svc.get_recommendations("test-api")
        ids = [r["id"] for r in result["recommendations"]]
        assert "basic-info-contacts" in ids

    def test_contacts_without_email_generates_email_rec(self) -> None:
        contacts = [{"name": "Team Lead"}]
        svc = _make_service(api=_make_api(contacts=contacts))
        result = svc.get_recommendations("test-api")
        ids = [r["id"] for r in result["recommendations"]]
        assert "basic-info-email" in ids
        assert "basic-info-contacts" not in ids

    def test_contacts_with_email_no_email_rec(self) -> None:
        contacts = [{"name": "Team Lead", "email": "team@example.com"}]
        dims = [
            {"key": "basicInfo", "name": "Basic Info", "weight": 0.20, "score": 50.0},
        ]
        svc = _make_service(
            score_data=_make_score_data(dimensions=dims),
            api=_make_api(contacts=contacts),
        )
        result = svc.get_recommendations("test-api")
        ids = [r["id"] for r in result["recommendations"]]
        assert "basic-info-email" not in ids
        assert "basic-info-contacts" not in ids

    def test_no_tos_generates_rec(self) -> None:
        svc = _make_service(api=_make_api(terms_of_service=""))
        result = svc.get_recommendations("test-api")
        ids = [r["id"] for r in result["recommendations"]]
        assert "basic-info-tos" in ids

    def test_with_tos_no_rec(self) -> None:
        dims = [
            {"key": "basicInfo", "name": "Basic Info", "weight": 0.20, "score": 50.0},
        ]
        svc = _make_service(
            score_data=_make_score_data(dimensions=dims),
            api=_make_api(terms_of_service="https://example.com/tos"),
        )
        result = svc.get_recommendations("test-api")
        ids = [r["id"] for r in result["recommendations"]]
        assert "basic-info-tos" not in ids


# ---------------------------------------------------------------------------
# Versioning recommendations
# ---------------------------------------------------------------------------


class TestVersioningRecommendations:
    def test_no_versions_generates_create_rec(self) -> None:
        svc = _make_service(api=_make_api(versions=[]))
        result = svc.get_recommendations("test-api")
        ids = [r["id"] for r in result["recommendations"]]
        assert "versioning-create" in ids

    def test_versions_without_production_generates_rec(self) -> None:
        versions = [{"name": "v1.0.0", "lifecycleStage": "design"}]
        svc = _make_service(api=_make_api(versions=versions))
        result = svc.get_recommendations("test-api")
        ids = [r["id"] for r in result["recommendations"]]
        assert "versioning-production" in ids

    def test_versions_with_production_no_rec(self) -> None:
        versions = [{"name": "v1.0.0", "lifecycleStage": "production"}]
        dims = [
            {"key": "versioning", "name": "Versioning", "weight": 0.15, "score": 50.0},
        ]
        svc = _make_service(
            score_data=_make_score_data(dimensions=dims),
            api=_make_api(versions=versions),
        )
        result = svc.get_recommendations("test-api")
        ids = [r["id"] for r in result["recommendations"]]
        assert "versioning-production" not in ids

    def test_non_semver_generates_rec(self) -> None:
        versions = [{"name": "latest", "lifecycleStage": "production"}]
        svc = _make_service(api=_make_api(versions=versions))
        result = svc.get_recommendations("test-api")
        ids = [r["id"] for r in result["recommendations"]]
        assert "versioning-semver" in ids

    def test_semver_no_rec(self) -> None:
        versions = [{"name": "v1.0.0", "lifecycleStage": "production"}]
        dims = [
            {"key": "versioning", "name": "Versioning", "weight": 0.15, "score": 50.0},
        ]
        svc = _make_service(
            score_data=_make_score_data(dimensions=dims),
            api=_make_api(versions=versions),
        )
        result = svc.get_recommendations("test-api")
        ids = [r["id"] for r in result["recommendations"]]
        assert "versioning-semver" not in ids


# ---------------------------------------------------------------------------
# Specification recommendations
# ---------------------------------------------------------------------------


class TestSpecificationRecommendations:
    def test_no_definitions_generates_upload_rec(self) -> None:
        svc = _make_service(api=_make_api(versions=[{"name": "v1", "definitions": []}]))
        result = svc.get_recommendations("test-api")
        ids = [r["id"] for r in result["recommendations"]]
        assert "specification-upload" in ids

    def test_no_versions_generates_upload_rec(self) -> None:
        svc = _make_service(api=_make_api(versions=[]))
        result = svc.get_recommendations("test-api")
        ids = [r["id"] for r in result["recommendations"]]
        assert "specification-upload" in ids

    def test_definition_without_spec_type_generates_rec(self) -> None:
        versions = [{"name": "v1", "definitions": [{"content": "something"}]}]
        dims = [
            {"key": "specification", "name": "Specification", "weight": 0.25, "score": 50.0},
        ]
        svc = _make_service(
            score_data=_make_score_data(dimensions=dims),
            api=_make_api(versions=versions),
        )
        result = svc.get_recommendations("test-api")
        ids = [r["id"] for r in result["recommendations"]]
        assert "specification-type" in ids
        assert "specification-upload" not in ids

    def test_definition_with_spec_type_no_rec(self) -> None:
        versions = [{"name": "v1", "definitions": [{"specification": "openapi", "name": "main"}]}]
        dims = [
            {"key": "specification", "name": "Specification", "weight": 0.25, "score": 50.0},
        ]
        svc = _make_service(
            score_data=_make_score_data(dimensions=dims),
            api=_make_api(versions=versions),
        )
        result = svc.get_recommendations("test-api")
        ids = [r["id"] for r in result["recommendations"]]
        assert "specification-type" not in ids
        assert "specification-upload" not in ids


# ---------------------------------------------------------------------------
# Documentation recommendations
# ---------------------------------------------------------------------------


class TestDocumentationRecommendations:
    def test_no_external_docs_generates_rec(self) -> None:
        svc = _make_service(api=_make_api())
        result = svc.get_recommendations("test-api")
        ids = [r["id"] for r in result["recommendations"]]
        assert "documentation-external" in ids

    def test_with_external_docs_no_rec(self) -> None:
        dims = [
            {"key": "documentation", "name": "Documentation", "weight": 0.15, "score": 50.0},
        ]
        svc = _make_service(
            score_data=_make_score_data(dimensions=dims),
            api=_make_api(external_docs=[{"url": "https://docs.example.com"}]),
        )
        result = svc.get_recommendations("test-api")
        ids = [r["id"] for r in result["recommendations"]]
        assert "documentation-external" not in ids

    def test_no_license_generates_rec(self) -> None:
        svc = _make_service(api=_make_api())
        result = svc.get_recommendations("test-api")
        ids = [r["id"] for r in result["recommendations"]]
        assert "documentation-license" in ids

    def test_with_license_no_rec(self) -> None:
        dims = [
            {"key": "documentation", "name": "Documentation", "weight": 0.15, "score": 50.0},
        ]
        svc = _make_service(
            score_data=_make_score_data(dimensions=dims),
            api=_make_api(license_info="MIT"),
        )
        result = svc.get_recommendations("test-api")
        ids = [r["id"] for r in result["recommendations"]]
        assert "documentation-license" not in ids


# ---------------------------------------------------------------------------
# Classification recommendations
# ---------------------------------------------------------------------------


class TestClassificationRecommendations:
    def test_no_custom_props_generates_rec(self) -> None:
        svc = _make_service(api=_make_api())
        result = svc.get_recommendations("test-api")
        ids = [r["id"] for r in result["recommendations"]]
        assert "classification-custom-props" in ids

    def test_with_custom_props_no_rec(self) -> None:
        dims = [
            {"key": "classification", "name": "Classification", "weight": 0.10, "score": 50.0},
        ]
        svc = _make_service(
            score_data=_make_score_data(dimensions=dims),
            api=_make_api(custom_properties={"team": "platform"}),
        )
        result = svc.get_recommendations("test-api")
        ids = [r["id"] for r in result["recommendations"]]
        assert "classification-custom-props" not in ids

    def test_default_lifecycle_generates_rec(self) -> None:
        svc = _make_service(api=_make_api(lifecycle_stage="design"))
        result = svc.get_recommendations("test-api")
        ids = [r["id"] for r in result["recommendations"]]
        assert "classification-lifecycle" in ids

    def test_production_lifecycle_no_rec(self) -> None:
        dims = [
            {"key": "classification", "name": "Classification", "weight": 0.10, "score": 50.0},
        ]
        svc = _make_service(
            score_data=_make_score_data(dimensions=dims),
            api=_make_api(lifecycle_stage="production"),
        )
        result = svc.get_recommendations("test-api")
        ids = [r["id"] for r in result["recommendations"]]
        assert "classification-lifecycle" not in ids


# ---------------------------------------------------------------------------
# Security recommendations
# ---------------------------------------------------------------------------


class TestSecurityRecommendations:
    def test_no_deployments_generates_rec(self) -> None:
        svc = _make_service(api=_make_api())
        result = svc.get_recommendations("test-api")
        ids = [r["id"] for r in result["recommendations"]]
        assert "security-deployments" in ids

    def test_with_deployments_no_rec(self) -> None:
        dims = [
            {"key": "security", "name": "Security", "weight": 0.15, "score": 50.0},
        ]
        svc = _make_service(
            score_data=_make_score_data(dimensions=dims),
            api=_make_api(deployments=[{"name": "prod-deploy"}]),
        )
        result = svc.get_recommendations("test-api")
        ids = [r["id"] for r in result["recommendations"]]
        assert "security-deployments" not in ids

    def test_no_contacts_generates_ownership_rec(self) -> None:
        svc = _make_service(api=_make_api())
        result = svc.get_recommendations("test-api")
        ids = [r["id"] for r in result["recommendations"]]
        assert "security-ownership" in ids

    def test_with_contacts_no_ownership_rec(self) -> None:
        dims = [
            {"key": "security", "name": "Security", "weight": 0.15, "score": 50.0},
        ]
        svc = _make_service(
            score_data=_make_score_data(dimensions=dims),
            api=_make_api(contacts=[{"name": "Owner"}]),
        )
        result = svc.get_recommendations("test-api")
        ids = [r["id"] for r in result["recommendations"]]
        assert "security-ownership" not in ids
