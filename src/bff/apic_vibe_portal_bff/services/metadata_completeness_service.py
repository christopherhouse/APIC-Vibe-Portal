"""Metadata completeness scoring service.

Scores APIs across six dimensions (Basic Info, Versioning, Specification,
Documentation, Classification, Security) and produces weighted overall
scores, grades, and organisation-wide overviews.
"""

from __future__ import annotations

import logging
import re
from collections.abc import Callable
from datetime import UTC, datetime
from typing import Any

from apic_vibe_portal_bff.clients.api_center_client import ApiCenterClient

logger = logging.getLogger(__name__)

# ------------------------------------------------------------------
# Constants
# ------------------------------------------------------------------

_DIMENSION_WEIGHTS: dict[str, float] = {
    "basicInfo": 0.20,
    "versioning": 0.15,
    "specification": 0.25,
    "documentation": 0.15,
    "classification": 0.10,
    "security": 0.15,
}

_DIMENSION_LABELS: dict[str, str] = {
    "basicInfo": "Basic Info",
    "versioning": "Versioning",
    "specification": "Specification",
    "documentation": "Documentation",
    "classification": "Classification",
    "security": "Security",
}

_SEMVER_PATTERN = re.compile(r"^v?\d+\.\d+\.\d+")


def _grade_from_score(score: float) -> str:
    """Map a numeric score (0–100) to a letter grade."""
    if score >= 90:
        return "A"
    if score >= 75:
        return "B"
    if score >= 60:
        return "C"
    if score >= 40:
        return "D"
    return "F"


# ------------------------------------------------------------------
# Service
# ------------------------------------------------------------------


class MetadataCompletenessService:
    """Score API metadata completeness across six weighted dimensions.

    Parameters
    ----------
    api_center_client:
        Client for fetching API definitions from Azure API Center.
    """

    def __init__(self, api_center_client: ApiCenterClient) -> None:
        self._api_center = api_center_client

    # ------------------------------------------------------------------
    # Public operations
    # ------------------------------------------------------------------

    def get_score(self, api_id: str, accessible_api_ids: list[str] | None = None) -> dict[str, Any]:
        """Get completeness score for a single API.

        Parameters
        ----------
        api_id:
            API identifier (name).
        accessible_api_ids:
            Optional list of API IDs the user can access.

        Returns
        -------
        dict with keys: apiId, apiName, overallScore, grade, dimensions,
        lastChecked.

        Raises
        ------
        PermissionError:
            If the API is not in the accessible list.
        ValueError:
            If the API is not found.
        """
        if accessible_api_ids is not None and api_id not in accessible_api_ids:
            raise PermissionError(f"Access denied to API: {api_id}")

        try:
            api = self._api_center.get_api(api_id)
        except Exception as exc:
            raise ValueError(f"API not found: {api_id}") from exc

        api = self._enrich_api(api)
        return self._build_score(api)

    def get_overview(self, accessible_api_ids: list[str] | None = None) -> dict[str, Any]:
        """Get organization-wide completeness overview.

        Returns
        -------
        dict with keys: averageScore, averageGrade, totalApis, distribution
        (A/B/C/D/F counts), dimensionAverages.
        """
        all_apis = self._get_accessible_apis(accessible_api_ids)
        if not all_apis:
            return {
                "averageScore": 0.0,
                "averageGrade": "F",
                "totalApis": 0,
                "distribution": {"A": 0, "B": 0, "C": 0, "D": 0, "F": 0},
                "dimensionAverages": [],
            }

        scores: list[dict[str, Any]] = [self._build_score(api) for api in all_apis]

        overall_scores = [s["overallScore"] for s in scores]
        avg_score = sum(overall_scores) / len(overall_scores)

        distribution: dict[str, int] = {"A": 0, "B": 0, "C": 0, "D": 0, "F": 0}
        for s in scores:
            distribution[s["grade"]] += 1

        # Aggregate per-dimension averages
        dim_totals: dict[str, float] = dict.fromkeys(_DIMENSION_WEIGHTS, 0.0)
        for s in scores:
            for dim in s["dimensions"]:
                dim_totals[dim["key"]] += dim["score"]

        num_apis = len(scores)
        dimension_averages = [
            {
                "key": key,
                "name": _DIMENSION_LABELS[key],
                "weight": _DIMENSION_WEIGHTS[key],
                "averageScore": round(dim_totals[key] / num_apis, 1),
            }
            for key in _DIMENSION_WEIGHTS
        ]

        return {
            "averageScore": round(avg_score, 1),
            "averageGrade": _grade_from_score(avg_score),
            "totalApis": num_apis,
            "distribution": distribution,
            "dimensionAverages": dimension_averages,
        }

    def get_leaderboard(self, accessible_api_ids: list[str] | None = None) -> dict[str, Any]:
        """Get top 5 and bottom 5 APIs by completeness.

        Returns
        -------
        dict with keys: top (list of up to 5), bottom (list of up to 5),
        each item with apiId, apiName, score, grade.
        """
        all_apis = self._get_accessible_apis(accessible_api_ids)
        if not all_apis:
            return {"top": [], "bottom": []}

        entries = []
        for api in all_apis:
            score_data = self._build_score(api)
            entries.append(
                {
                    "apiId": score_data["apiId"],
                    "apiName": score_data["apiName"],
                    "score": score_data["overallScore"],
                    "grade": score_data["grade"],
                }
            )

        entries.sort(key=lambda x: x["score"], reverse=True)

        return {
            "top": entries[:5],
            "bottom": list(reversed(entries[-5:])) if len(entries) > 5 else entries,
        }

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _get_accessible_apis(self, accessible_api_ids: list[str] | None) -> list[dict[str, Any]]:
        """Fetch all accessible APIs and enrich with versions/deployments."""
        all_apis: list[dict[str, Any]] = self._api_center.list_apis()

        if accessible_api_ids is not None:
            all_apis = [api for api in all_apis if api.get("name") in accessible_api_ids]

        return [self._enrich_api(api) for api in all_apis]

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

        # Attempt to enrich versions with definitions
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

    def _build_score(self, api: dict[str, Any]) -> dict[str, Any]:
        """Build the full score response for a single API."""
        dimensions = []
        weighted_total = 0.0

        for key, weight in _DIMENSION_WEIGHTS.items():
            raw = self._score_dimension(key, api)
            score = min(max(raw, 0), 100)
            weighted_total += score * weight
            dimensions.append(
                {
                    "key": key,
                    "name": _DIMENSION_LABELS[key],
                    "weight": weight,
                    "score": round(score, 1),
                }
            )

        overall = round(weighted_total, 1)

        return {
            "apiId": api.get("name", ""),
            "apiName": api.get("title", api.get("name", "")),
            "overallScore": overall,
            "grade": _grade_from_score(overall),
            "dimensions": dimensions,
            "lastChecked": datetime.now(UTC).isoformat().replace("+00:00", "Z"),
        }

    # ------------------------------------------------------------------
    # Dimension scoring
    # ------------------------------------------------------------------

    def _score_dimension(self, key: str, api: dict[str, Any]) -> float:
        scorers: dict[str, Callable[[dict[str, Any]], float]] = {
            "basicInfo": self._score_basic_info,
            "versioning": self._score_versioning,
            "specification": self._score_specification,
            "documentation": self._score_documentation,
            "classification": self._score_classification,
            "security": self._score_security,
        }
        scorer = scorers.get(key)
        if scorer is None:
            logger.warning("Unknown dimension key: %s", key)
            return 0.0
        return scorer(api)

    @staticmethod
    def _score_basic_info(api: dict[str, Any]) -> float:
        score = 0.0
        title = api.get("title", "")
        if title and str(title).strip():
            score += 20

        description = api.get("description", "") or ""
        if description:
            score += 10
            if len(description) >= 50:
                score += 20
            if len(description) >= 100:
                score += 10

        contacts = api.get("contacts", []) or []
        if contacts:
            score += 20
            if any(c.get("email") for c in contacts if isinstance(c, dict)):
                score += 10

        if api.get("termsOfService"):
            score += 10

        return score

    @staticmethod
    def _score_versioning(api: dict[str, Any]) -> float:
        score = 0.0
        versions: list[dict[str, Any]] = api.get("versions", []) or []

        if versions:
            score += 30
            if len(versions) >= 2:
                score += 10

        has_production = any(str(v.get("lifecycleStage", "")).lower() == "production" for v in versions)
        if has_production:
            score += 20

        if versions and any(_SEMVER_PATTERN.match(str(v.get("name", ""))) for v in versions):
            score += 20

        has_non_deprecated = any(str(v.get("lifecycleStage", "")).lower() != "deprecated" for v in versions)
        if versions and has_non_deprecated:
            score += 20

        return score

    @staticmethod
    def _score_specification(api: dict[str, Any]) -> float:
        score = 0.0
        versions: list[dict[str, Any]] = api.get("versions", []) or []

        has_definition = False
        has_spec_type = False
        has_content = False
        definition_count = 0

        for version in versions:
            definitions: list[dict[str, Any]] = version.get("definitions", []) or []
            for defn in definitions:
                definition_count += 1
                has_definition = True
                if defn.get("specification") or defn.get("name"):
                    has_spec_type = True
                if defn.get("content") or defn.get("value"):
                    has_content = True

        if has_definition:
            score += 40
        if has_spec_type:
            score += 20
        if has_content:
            score += 20
        if definition_count >= 2:
            score += 20

        return score

    @staticmethod
    def _score_documentation(api: dict[str, Any]) -> float:
        score = 0.0
        external_docs = api.get("externalDocs", []) or api.get("externalDocumentation", []) or []

        if external_docs:
            score += 30
            if any(d.get("description") for d in external_docs if isinstance(d, dict)):
                score += 20

        if api.get("license"):
            score += 25

        if api.get("termsOfService"):
            score += 25

        return score

    @staticmethod
    def _score_classification(api: dict[str, Any]) -> float:
        score = 0.0
        custom_props = api.get("customProperties", {}) or {}

        if custom_props:
            score += 30
            if len(custom_props) >= 2:
                score += 20

        lifecycle = str(api.get("lifecycleStage", "") or "").lower()
        if lifecycle and lifecycle != "design":
            score += 30

        kind = api.get("kind", "")
        if kind and str(kind).strip():
            score += 20

        return score

    @staticmethod
    def _score_security(api: dict[str, Any]) -> float:
        score = 0.0
        deployments = api.get("deployments", []) or []

        if deployments:
            score += 30
            has_production = any(
                "prod" in str(d.get("name", "")).lower()
                or "prod" in str(d.get("title", "")).lower()
                or str(d.get("environmentId", "")).lower().find("prod") != -1
                for d in deployments
            )
            if has_production:
                score += 30

        contacts = api.get("contacts", []) or []
        if contacts:
            score += 20

        if api.get("license"):
            score += 20

        return score
