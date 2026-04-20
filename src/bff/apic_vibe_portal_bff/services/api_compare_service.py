"""API comparison service — business logic for multi-API comparisons.

Generates structured side-by-side comparisons of multiple APIs across
configurable aspects (metadata, versions, endpoints, governance, deployments,
specifications).  Optionally produces an AI-powered narrative analysis via
the OpenAI client.
"""

from __future__ import annotations

import logging
from enum import StrEnum
from typing import TYPE_CHECKING, Any

from pydantic import BaseModel, ConfigDict, Field
from pydantic.alias_generators import to_camel

if TYPE_CHECKING:
    from apic_vibe_portal_bff.services.api_catalog_service import ApiCatalogService

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Enums & public models
# ---------------------------------------------------------------------------


class CompareAspect(StrEnum):
    """Aspects that can be compared between APIs."""

    METADATA = "metadata"
    VERSIONS = "versions"
    ENDPOINTS = "endpoints"
    GOVERNANCE = "governance"
    DEPLOYMENTS = "deployments"
    SPECIFICATIONS = "specifications"


ALL_ASPECTS: list[CompareAspect] = list(CompareAspect)


class CamelModel(BaseModel):
    """Base model that serialises to camelCase JSON."""

    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True)


class CompareApiSummary(CamelModel):
    """Summary information for one API in a comparison."""

    id: str
    name: str
    title: str
    description: str
    kind: str
    lifecycle_stage: str


class AspectValue(CamelModel):
    """A single value cell in the comparison table."""

    value: str | None = None
    display: str | None = None
    """Human-readable representation (e.g. ``"3 versions"`` for an integer 3)."""
    is_best: bool = False
    """True when this value is the 'best' in its row (for highlighting)."""


class AspectComparison(CamelModel):
    """Comparison data for one aspect row across all compared APIs."""

    aspect: str
    label: str
    values: list[AspectValue]
    """One entry per API, in the same order as :attr:`CompareResponse.apis`."""
    all_equal: bool = False


class CompareResponse(CamelModel):
    """Full comparison response returned by the compare endpoints."""

    apis: list[CompareApiSummary]
    aspects: list[AspectComparison]
    similarity_score: float = Field(default=0.0, ge=0.0, le=1.0)
    """Fraction of aspects that are identical across all APIs (0–1)."""
    ai_analysis: str | None = None
    """Only populated by the /api/compare/ai-analysis endpoint."""


# ---------------------------------------------------------------------------
# Service
# ---------------------------------------------------------------------------

_AI_PROMPT_TEMPLATE = """\
You are an API consultant reviewing the following APIs for a developer portal.

Compare these APIs side by side and provide a concise analysis covering:
1. Use-case fit — which API is best suited for different scenarios
2. Key differences — the most important technical distinctions
3. Trade-offs — strengths and weaknesses of each
4. Recommendation — a clear recommendation with rationale

APIs under comparison:
{api_summaries}

Aspect comparison data:
{aspect_data}

Write 3-5 clear paragraphs in plain English. Do not use tables. Be specific and actionable.
"""


class ApiCompareService:
    """Generates structured multi-API comparisons.

    Parameters
    ----------
    catalog_service:
        Used to fetch full API definitions for each requested ID.
    openai_client:
        Optional OpenAI client used for AI-powered narrative analysis.
        When ``None``, the ``ai_analysis`` field is always ``None``.
    """

    def __init__(
        self,
        catalog_service: ApiCatalogService,
        openai_client: Any | None = None,
    ) -> None:
        self._catalog = catalog_service
        self._openai = openai_client

    # ------------------------------------------------------------------
    # Public
    # ------------------------------------------------------------------

    def compare(
        self,
        api_ids: list[str],
        aspects: list[CompareAspect] | None = None,
    ) -> CompareResponse:
        """Return a structured comparison for *api_ids*.

        Parameters
        ----------
        api_ids:
            2–5 API names / IDs to compare.
        aspects:
            Subset of aspects to include.  ``None`` → all aspects.
        """
        if len(api_ids) < 2:  # noqa: PLR2004
            raise ValueError("At least 2 API IDs are required for comparison")
        if len(api_ids) > 5:  # noqa: PLR2004
            raise ValueError("At most 5 API IDs can be compared at once")

        target_aspects = aspects if aspects is not None else ALL_ASPECTS

        # Fetch API definitions (no security trimming — caller enforces access)
        definitions = []
        for api_id in api_ids:
            api = self._catalog.get_api(api_id)
            definitions.append(api)

        summaries = [
            CompareApiSummary(
                id=d.id,
                name=d.name,
                title=d.title,
                description=d.description,
                kind=d.kind,
                lifecycle_stage=d.lifecycle_stage,
            )
            for d in definitions
        ]

        aspect_rows = self._build_aspects(definitions, target_aspects)
        equal_count = sum(1 for a in aspect_rows if a.all_equal)
        similarity = equal_count / len(aspect_rows) if aspect_rows else 0.0

        return CompareResponse(
            apis=summaries,
            aspects=aspect_rows,
            similarity_score=round(similarity, 3),
        )

    def compare_with_ai(
        self,
        api_ids: list[str],
        aspects: list[CompareAspect] | None = None,
    ) -> CompareResponse:
        """Return a comparison that also includes AI-generated narrative analysis."""
        result = self.compare(api_ids, aspects)
        result.ai_analysis = self._generate_ai_analysis(result)
        return result

    # ------------------------------------------------------------------
    # Aspect builders
    # ------------------------------------------------------------------

    def _build_aspects(
        self,
        definitions: list[Any],
        aspects: list[CompareAspect],
    ) -> list[AspectComparison]:
        rows: list[AspectComparison] = []
        for aspect in aspects:
            match aspect:
                case CompareAspect.METADATA:
                    rows.extend(self._metadata_rows(definitions))
                case CompareAspect.VERSIONS:
                    rows.extend(self._version_rows(definitions))
                case CompareAspect.ENDPOINTS:
                    rows.extend(self._endpoint_rows(definitions))
                case CompareAspect.GOVERNANCE:
                    rows.extend(self._governance_rows(definitions))
                case CompareAspect.DEPLOYMENTS:
                    rows.extend(self._deployment_rows(definitions))
                case CompareAspect.SPECIFICATIONS:
                    rows.extend(self._specification_rows(definitions))
        return rows

    # -- Metadata --

    def _metadata_rows(self, defs: list[Any]) -> list[AspectComparison]:
        rows = []

        rows.append(self._row("metadata.kind", "API Kind", [d.kind for d in defs]))
        rows.append(self._row("metadata.lifecycle", "Lifecycle", [d.lifecycle_stage for d in defs]))
        rows.append(
            self._row(
                "metadata.license",
                "License",
                [d.license or "" for d in defs],
            )
        )
        rows.append(
            self._row(
                "metadata.contacts",
                "Contacts",
                [str(len(d.contacts)) for d in defs],
                display_fn=lambda v: f"{v} contact{'s' if v != '1' else ''}",
            )
        )
        return rows

    # -- Versions --

    def _version_rows(self, defs: list[Any]) -> list[AspectComparison]:
        count_values = [str(len(d.versions)) for d in defs]
        return [
            self._row(
                "versions.count",
                "Version Count",
                count_values,
                display_fn=lambda v: f"{v} version{'s' if v != '1' else ''}",
                higher_is_better=True,
            )
        ]

    # -- Endpoints --

    def _endpoint_rows(self, defs: list[Any]) -> list[AspectComparison]:
        # Count operations from custom_properties if available, otherwise use a placeholder
        def _op_count(d: Any) -> str:
            props = d.custom_properties or {}
            count = props.get("operationCount") or props.get("operation_count")
            return str(count) if count is not None else "N/A"

        return [
            self._row(
                "endpoints.operations",
                "Operation Count",
                [_op_count(d) for d in defs],
            )
        ]

    # -- Governance --

    def _governance_rows(self, defs: list[Any]) -> list[AspectComparison]:
        def _score(d: Any) -> str:
            props = d.custom_properties or {}
            score = props.get("governanceScore") or props.get("governance_score")
            return str(score) if score is not None else "N/A"

        return [
            self._row(
                "governance.score",
                "Governance Score",
                [_score(d) for d in defs],
            )
        ]

    # -- Deployments --

    def _deployment_rows(self, defs: list[Any]) -> list[AspectComparison]:
        count_values = [str(len(d.deployments)) for d in defs]
        return [
            self._row(
                "deployments.count",
                "Deployment Count",
                count_values,
                display_fn=lambda v: f"{v} deployment{'s' if v != '1' else ''}",
                higher_is_better=True,
            )
        ]

    # -- Specifications --

    def _specification_rows(self, defs: list[Any]) -> list[AspectComparison]:
        def _spec_type(d: Any) -> str:
            props = d.custom_properties or {}
            return str(props.get("specType") or props.get("spec_type") or "N/A")

        return [
            self._row(
                "specifications.type",
                "Spec Format",
                [_spec_type(d) for d in defs],
            )
        ]

    # ------------------------------------------------------------------
    # Row-building helper
    # ------------------------------------------------------------------

    @staticmethod
    def _row(
        aspect: str,
        label: str,
        raw_values: list[str],
        *,
        display_fn: Any | None = None,
        higher_is_better: bool = False,
    ) -> AspectComparison:
        """Create an :class:`AspectComparison` row from raw string values."""
        all_equal = len(set(raw_values)) == 1

        # Determine "best" value for numeric rows
        best_idx: int | None = None
        if higher_is_better and not all_equal:
            try:
                nums = [int(v) for v in raw_values]
                best_idx = nums.index(max(nums))
            except (ValueError, TypeError):
                pass

        values = []
        for idx, raw in enumerate(raw_values):
            display = display_fn(raw) if display_fn else raw
            values.append(
                AspectValue(
                    value=raw,
                    display=display,
                    is_best=(idx == best_idx),
                )
            )

        return AspectComparison(
            aspect=aspect,
            label=label,
            values=values,
            all_equal=all_equal,
        )

    # ------------------------------------------------------------------
    # AI analysis
    # ------------------------------------------------------------------

    def _generate_ai_analysis(self, result: CompareResponse) -> str | None:
        if self._openai is None:
            return None

        api_summaries = "\n".join(
            f"- {s.title} (kind={s.kind}, lifecycle={s.lifecycle_stage}): {(s.description or '')[:200]}"
            for s in result.apis
        )
        aspect_lines = []
        for row in result.aspects:
            cells = " | ".join(f"{result.apis[i].title}: {v.display or v.value}" for i, v in enumerate(row.values))
            aspect_lines.append(f"- {row.label}: {cells}")
        aspect_data = "\n".join(aspect_lines)

        prompt = _AI_PROMPT_TEMPLATE.format(
            api_summaries=api_summaries,
            aspect_data=aspect_data,
        )

        try:
            response = self._openai.chat.completions.create(
                model="gpt-4o-mini",
                messages=[{"role": "user", "content": prompt}],
                max_tokens=800,
                temperature=0.3,
            )
            return response.choices[0].message.content
        except Exception:  # noqa: BLE001
            logger.warning("AI analysis generation failed", exc_info=True)
            return None
