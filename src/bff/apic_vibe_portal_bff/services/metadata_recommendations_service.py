"""Metadata recommendations service.

Analyzes metadata gaps and generates prioritized improvement
recommendations for API owners.
"""

from __future__ import annotations

import logging
import re
from typing import Any

from apic_vibe_portal_bff.clients.api_center_client import ApiCenterClient
from apic_vibe_portal_bff.services.metadata_completeness_service import (
    MetadataCompletenessService,
)

logger = logging.getLogger(__name__)

_SEMVER_PATTERN = re.compile(r"^v?\d+\.\d+\.\d+")

_IMPACT_VALUES: dict[str, int] = {"high": 3, "medium": 2, "low": 1}


class MetadataRecommendationsService:
    """Generate metadata improvement recommendations based on scoring gaps.

    Parameters
    ----------
    metadata_completeness_service:
        Service for computing completeness scores.
    api_center_client:
        Client for fetching API definitions from Azure API Center.
    """

    def __init__(
        self,
        metadata_completeness_service: MetadataCompletenessService,
        api_center_client: ApiCenterClient,
    ) -> None:
        self._scoring = metadata_completeness_service
        self._api_center = api_center_client

    # ------------------------------------------------------------------
    # Public operations
    # ------------------------------------------------------------------

    def get_recommendations(
        self,
        api_id: str,
        accessible_api_ids: list[str] | None = None,
    ) -> dict[str, Any]:
        """Get recommendations for improving API metadata.

        Parameters
        ----------
        api_id:
            API identifier (name).
        accessible_api_ids:
            Optional list of API IDs the user can access.

        Returns
        -------
        dict with keys: apiId, apiName, overallScore, grade,
        recommendations (list), generatedAt.
        """
        score_data = self._scoring.get_score(api_id, accessible_api_ids)

        try:
            api = self._api_center.get_api(api_id)
            api = self._enrich_api(api)
        except Exception:
            logger.warning(
                "Failed to fetch API data for recommendations: %s",
                api_id,
                exc_info=True,
            )
            api = {}

        recommendations = self._generate_recommendations(score_data, api)

        return {
            "apiId": score_data["apiId"],
            "apiName": score_data["apiName"],
            "overallScore": score_data["overallScore"],
            "grade": score_data["grade"],
            "recommendations": recommendations,
            "generatedAt": score_data["lastChecked"],
        }

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _enrich_api(self, api: dict[str, Any]) -> dict[str, Any]:
        """Enrich an API dict with versions and deployments."""
        api_id = api.get("name", "")
        if not api_id:
            return api

        try:
            api["versions"] = self._api_center.list_api_versions(api_id)
        except Exception:
            logger.warning("Failed to fetch versions for API: %s", api_id)
            api["versions"] = []

        try:
            api["deployments"] = self._api_center.list_deployments(api_id)
        except Exception:
            logger.warning("Failed to fetch deployments for API: %s", api_id)
            api["deployments"] = []

        for version in api.get("versions", []):
            version_name = version.get("name", "")
            if not version_name:
                continue
            try:
                version["definitions"] = self._api_center.list_api_definitions(api_id, version_name)
            except Exception:
                logger.debug("Could not fetch definitions for %s/%s", api_id, version_name)
                version["definitions"] = []

        return api

    def _generate_recommendations(
        self,
        score_data: dict[str, Any],
        api: dict[str, Any],
    ) -> list[dict[str, Any]]:
        """Generate recommendations based on score gaps."""
        recommendations: list[dict[str, Any]] = []

        for dim in score_data.get("dimensions", []):
            dim_key = dim["key"]
            dim_score = dim["score"]

            if dim_score >= 100:
                continue

            dim_recs = self._get_dimension_recommendations(dim_key, dim_score, api)
            recommendations.extend(dim_recs)

        # Sort by impact score descending
        recommendations.sort(key=lambda r: r["impact"], reverse=True)

        # Assign priority numbers
        for i, rec in enumerate(recommendations):
            rec["priority"] = i + 1

        return recommendations

    def _get_dimension_recommendations(
        self,
        dimension: str,
        score: float,
        api: dict[str, Any],
    ) -> list[dict[str, Any]]:
        """Get specific recommendations for a dimension."""
        generators: dict[str, Any] = {
            "basicInfo": self._recs_basic_info,
            "versioning": self._recs_versioning,
            "specification": self._recs_specification,
            "documentation": self._recs_documentation,
            "classification": self._recs_classification,
            "security": self._recs_security,
        }
        generator = generators.get(dimension)
        if generator is None:
            logger.warning("Unknown dimension key: %s", dimension)
            return []
        return generator(api)

    # ------------------------------------------------------------------
    # Dimension-specific recommendation generators
    # ------------------------------------------------------------------

    @staticmethod
    def _recs_basic_info(api: dict[str, Any]) -> list[dict[str, Any]]:
        recs: list[dict[str, Any]] = []
        description = api.get("description", "") or ""

        if len(description) < 50:
            recs.append(
                {
                    "id": "basic-info-description",
                    "dimension": "basicInfo",
                    "title": "Add a detailed API description",
                    "description": (
                        "A thorough description helps developers quickly understand "
                        "what your API does, its primary use cases, and key capabilities. "
                        "Aim for at least 100 characters."
                    ),
                    "example": (
                        "The Petstore API provides a complete set of endpoints for "
                        "managing pet inventory, customer orders, and user accounts. "
                        "It supports CRUD operations with JSON payloads and OAuth 2.0 "
                        "authentication."
                    ),
                    "impact": _IMPACT_VALUES["high"],
                    "effort": "low",
                }
            )

        contacts = api.get("contacts", []) or []
        if not contacts:
            recs.append(
                {
                    "id": "basic-info-contacts",
                    "dimension": "basicInfo",
                    "title": "Add contact information",
                    "description": (
                        "Contact information lets consumers reach the API team for "
                        "support, bug reports, and integration questions."
                    ),
                    "example": (
                        "Contact: API Platform Team, api-platform@example.com, https://teams.example.com/api-support"
                    ),
                    "impact": _IMPACT_VALUES["medium"],
                    "effort": "low",
                }
            )
        elif not any(c.get("email") for c in contacts if isinstance(c, dict)):
            recs.append(
                {
                    "id": "basic-info-email",
                    "dimension": "basicInfo",
                    "title": "Add email to contact",
                    "description": (
                        "Including an email address in your contact information "
                        "provides a direct channel for API consumers to report "
                        "issues or ask questions."
                    ),
                    "example": "api-team@example.com",
                    "impact": _IMPACT_VALUES["low"],
                    "effort": "low",
                }
            )

        if not api.get("termsOfService"):
            recs.append(
                {
                    "id": "basic-info-tos",
                    "dimension": "basicInfo",
                    "title": "Add terms of service",
                    "description": (
                        "Terms of service define usage policies, rate limits, and legal obligations for API consumers."
                    ),
                    "example": "https://example.com/api/terms-of-service",
                    "impact": _IMPACT_VALUES["low"],
                    "effort": "medium",
                }
            )

        return recs

    @staticmethod
    def _recs_versioning(api: dict[str, Any]) -> list[dict[str, Any]]:
        recs: list[dict[str, Any]] = []
        versions: list[dict[str, Any]] = api.get("versions", []) or []

        if not versions:
            recs.append(
                {
                    "id": "versioning-create",
                    "dimension": "versioning",
                    "title": "Create an API version",
                    "description": (
                        "Versioning enables you to evolve your API without "
                        "breaking existing consumers. At least one version "
                        "should be defined."
                    ),
                    "example": "v1.0.0 (lifecycle: production)",
                    "impact": _IMPACT_VALUES["high"],
                    "effort": "medium",
                }
            )
            return recs

        has_production = any(str(v.get("lifecycleStage", "")).lower() == "production" for v in versions)
        if not has_production:
            recs.append(
                {
                    "id": "versioning-production",
                    "dimension": "versioning",
                    "title": "Promote a version to production",
                    "description": (
                        "Marking a version as production signals to consumers "
                        "which version is stable and recommended for use."
                    ),
                    "example": "Set lifecycle stage of v1.0.0 to 'production'",
                    "impact": _IMPACT_VALUES["medium"],
                    "effort": "low",
                }
            )

        has_semver = any(_SEMVER_PATTERN.match(str(v.get("name", ""))) for v in versions)
        if not has_semver:
            recs.append(
                {
                    "id": "versioning-semver",
                    "dimension": "versioning",
                    "title": "Use semantic versioning",
                    "description": (
                        "Semantic versioning (e.g. v1.2.3) communicates the "
                        "nature of changes — major breaking changes, minor "
                        "features, and patch fixes — at a glance."
                    ),
                    "example": "v1.0.0, v1.1.0, v2.0.0",
                    "impact": _IMPACT_VALUES["low"],
                    "effort": "low",
                }
            )

        return recs

    @staticmethod
    def _recs_specification(api: dict[str, Any]) -> list[dict[str, Any]]:
        recs: list[dict[str, Any]] = []
        versions: list[dict[str, Any]] = api.get("versions", []) or []

        has_definition = False
        has_spec_type = False
        for version in versions:
            definitions: list[dict[str, Any]] = version.get("definitions", []) or []
            for defn in definitions:
                has_definition = True
                if defn.get("specification") or defn.get("name"):
                    has_spec_type = True

        if not has_definition:
            recs.append(
                {
                    "id": "specification-upload",
                    "dimension": "specification",
                    "title": "Upload an API specification",
                    "description": (
                        "An API specification (OpenAPI, AsyncAPI, gRPC, etc.) "
                        "is the single most important piece of metadata. It "
                        "enables auto-generated docs, SDKs, and testing."
                    ),
                    "example": "Upload an OpenAPI 3.1 YAML or JSON specification file",
                    "impact": _IMPACT_VALUES["high"],
                    "effort": "high",
                }
            )
        elif not has_spec_type:
            recs.append(
                {
                    "id": "specification-type",
                    "dimension": "specification",
                    "title": "Set specification type",
                    "description": (
                        "Setting the specification type (e.g. OpenAPI, gRPC) "
                        "helps tooling render documentation and generate "
                        "client SDKs correctly."
                    ),
                    "example": "specification: openapi, version: 3.1.0",
                    "impact": _IMPACT_VALUES["medium"],
                    "effort": "low",
                }
            )

        return recs

    @staticmethod
    def _recs_documentation(api: dict[str, Any]) -> list[dict[str, Any]]:
        recs: list[dict[str, Any]] = []
        external_docs = api.get("externalDocs", []) or api.get("externalDocumentation", []) or []

        if not external_docs:
            recs.append(
                {
                    "id": "documentation-external",
                    "dimension": "documentation",
                    "title": "Add external documentation links",
                    "description": (
                        "External documentation links (guides, tutorials, "
                        "quickstarts) help developers get started faster "
                        "and understand advanced use cases."
                    ),
                    "example": ("https://docs.example.com/petstore/getting-started — Getting Started Guide"),
                    "impact": _IMPACT_VALUES["high"],
                    "effort": "medium",
                }
            )

        if not api.get("license"):
            recs.append(
                {
                    "id": "documentation-license",
                    "dimension": "documentation",
                    "title": "Add license information",
                    "description": (
                        "License information clarifies how the API can be used, "
                        "whether it is open-source or proprietary, and any "
                        "restrictions on redistribution."
                    ),
                    "example": "MIT License — https://opensource.org/licenses/MIT",
                    "impact": _IMPACT_VALUES["medium"],
                    "effort": "low",
                }
            )

        return recs

    @staticmethod
    def _recs_classification(api: dict[str, Any]) -> list[dict[str, Any]]:
        recs: list[dict[str, Any]] = []
        custom_props = api.get("customProperties", {}) or {}

        if not custom_props:
            recs.append(
                {
                    "id": "classification-custom-props",
                    "dimension": "classification",
                    "title": "Add custom properties/tags",
                    "description": (
                        "Custom properties and tags improve API discoverability "
                        "by enabling filtering and categorization in the portal."
                    ),
                    "example": (
                        'department: "payments", data-classification: "internal", team: "platform-engineering"'
                    ),
                    "impact": _IMPACT_VALUES["medium"],
                    "effort": "low",
                }
            )

        lifecycle = str(api.get("lifecycleStage", "") or "").lower()
        if not lifecycle or lifecycle == "design":
            recs.append(
                {
                    "id": "classification-lifecycle",
                    "dimension": "classification",
                    "title": "Set lifecycle stage",
                    "description": (
                        "An accurate lifecycle stage (development, testing, "
                        "production, deprecated) helps consumers choose the "
                        "right API version."
                    ),
                    "example": "lifecycleStage: production",
                    "impact": _IMPACT_VALUES["medium"],
                    "effort": "low",
                }
            )

        return recs

    @staticmethod
    def _recs_security(api: dict[str, Any]) -> list[dict[str, Any]]:
        recs: list[dict[str, Any]] = []
        deployments = api.get("deployments", []) or []

        if not deployments:
            recs.append(
                {
                    "id": "security-deployments",
                    "dimension": "security",
                    "title": "Configure API deployments",
                    "description": (
                        "Deployment information documents where and how the "
                        "API is hosted, which is essential for security "
                        "reviews and environment management."
                    ),
                    "example": ("deployment: prod-eastus, server: https://api.example.com, environment: production"),
                    "impact": _IMPACT_VALUES["high"],
                    "effort": "high",
                }
            )

        contacts = api.get("contacts", []) or []
        if not contacts:
            recs.append(
                {
                    "id": "security-ownership",
                    "dimension": "security",
                    "title": "Define API ownership",
                    "description": (
                        "Clear ownership ensures there is an accountable team "
                        "for security incidents, vulnerability patches, and "
                        "access-control decisions."
                    ),
                    "example": ("Contact: Security Team Lead, security-team@example.com"),
                    "impact": _IMPACT_VALUES["medium"],
                    "effort": "low",
                }
            )

        return recs
