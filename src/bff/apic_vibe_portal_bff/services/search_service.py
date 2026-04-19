"""Search service — business logic for API search operations.

Orchestrates calls to :class:`AISearchClient`, transforms AI Search SDK
results into Pydantic response models, and implements search with
keyword + semantic ranking.
"""

from __future__ import annotations

import logging
import re
import time
from typing import Any

from apic_vibe_portal_bff.clients.ai_search_client import AISearchClient
from apic_vibe_portal_bff.models.search import (
    PaginationParams,
    SearchDocument,
    SearchFacet,
    SearchFacets,
    SearchFacetValue,
    SearchFilters,
    SearchRequest,
    SearchResponse,
    SearchResult,
    SearchSortField,
    SuggestResponse,
    SuggestResult,
)
from apic_vibe_portal_bff.utils.logger import sanitize_for_log

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

# Allowed filter value pattern — alphanumeric, hyphens, underscores, dots, spaces
_SAFE_FILTER_VALUE = re.compile(r"^[\w\s.\-]+$")

# Maps API-facing sort field names to AI Search index field names
_SORT_FIELD_MAP: dict[SearchSortField, str] = {
    "relevance": "",  # empty → use default relevance scoring
    "name": "apiName",
    "updatedAt": "updatedAt",
    "createdAt": "createdAt",
}


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _escape_odata_value(value: str) -> str:
    """Escape a value for safe use in an OData filter string literal.

    OData escapes single quotes by doubling them (``''``).  Values that
    contain characters outside the expected set are rejected to prevent
    injection-style filter manipulation.
    """
    if not _SAFE_FILTER_VALUE.match(value):
        raise ValueError(f"Invalid filter value: {value!r}")
    return value.replace("'", "''")


def _build_odata_filter(filters: SearchFilters | None, accessible_api_ids: list[str] | None = None) -> str | None:
    """Build an OData filter expression from :class:`SearchFilters`.

    Each field supports multi-value OR filters.  Multiple fields are combined
    with AND.  Values are validated and escaped to prevent OData injection.

    Parameters
    ----------
    filters:
        User-supplied search filters.
    accessible_api_ids:
        When ``None``, no security filter is applied (admin bypass).
        When a list, adds a ``search.in()`` clause restricting results to the
        named APIs.  An empty list produces a filter that matches nothing,
        effectively returning zero results.
    """
    if filters is None and accessible_api_ids is None:
        return None

    parts: list[str] = []

    if filters is not None:
        if filters.kind:
            kind_clauses = " or ".join(f"kind eq '{_escape_odata_value(v)}'" for v in filters.kind)
            parts.append(f"({kind_clauses})")

        if filters.lifecycle_stage:
            lc_clauses = " or ".join(f"lifecycleStage eq '{_escape_odata_value(v)}'" for v in filters.lifecycle_stage)
            parts.append(f"({lc_clauses})")

        if filters.tags:
            # Collection fields use any()
            tag_clauses = " or ".join(f"tags/any(t: t eq '{_escape_odata_value(v)}')" for v in filters.tags)
            parts.append(f"({tag_clauses})")

    # Security trimming: restrict to accessible API names.
    if accessible_api_ids is not None:
        if not accessible_api_ids:
            # No accessible APIs — return a filter that matches nothing.
            parts.append("apiName eq '__no_access__'")
        else:
            # Build a search.in() expression.  Values are API names (short
            # identifiers) which only contain alphanumerics, hyphens, and
            # underscores — safe to join without extra escaping.
            ids_csv = ",".join(accessible_api_ids)
            parts.append(f"search.in(apiName, '{ids_csv}', ',')")

    return " and ".join(parts) if parts else None


def _extract_highlights(result: dict[str, Any]) -> dict[str, list[str]]:
    """Extract hit highlights from an AI Search result dict."""
    raw = result.get("@search.highlights") or {}
    return {k: v for k, v in raw.items() if isinstance(v, list)}


def _extract_captions(result: dict[str, Any]) -> list[str]:
    """Extract semantic captions from an AI Search result dict."""
    raw_captions = result.get("@search.captions") or []
    texts: list[str] = []
    for caption in raw_captions:
        text = getattr(caption, "text", None) or (caption.get("text") if isinstance(caption, dict) else None)
        if text:
            texts.append(text)
    return texts


def _parse_facets(raw_facets: dict[str, list[Any]] | None) -> SearchFacets:
    """Transform raw AI Search facet data into :class:`SearchFacets`."""
    if not raw_facets:
        return SearchFacets(facets=[])

    facet_list: list[SearchFacet] = []
    for field_name, buckets in raw_facets.items():
        values: list[SearchFacetValue] = []
        for bucket in buckets:
            val = bucket.get("value") if isinstance(bucket, dict) else getattr(bucket, "value", None)
            cnt = bucket.get("count", 0) if isinstance(bucket, dict) else getattr(bucket, "count", 0)
            if val is not None:
                values.append(SearchFacetValue(value=str(val), count=cnt))
        facet_list.append(SearchFacet(field=field_name, values=values))

    return SearchFacets(facets=facet_list)


def _map_search_result(result: dict[str, Any]) -> SearchResult:
    """Map a raw AI Search result dict to a :class:`SearchResult`."""
    doc = SearchDocument.model_validate(result)
    return SearchResult(
        document=doc,
        score=result.get("@search.score", 0.0),
        reranker_score=result.get("@search.rerankerScore"),
        highlights=_extract_highlights(result),
        captions=_extract_captions(result),
    )


# ---------------------------------------------------------------------------
# Service
# ---------------------------------------------------------------------------


class SearchService:
    """High-level service for search operations.

    Parameters
    ----------
    client:
        :class:`AISearchClient` instance for querying Azure AI Search.
    """

    def __init__(self, client: AISearchClient) -> None:
        self._client = client

    def search(self, request: SearchRequest, accessible_api_ids: list[str] | None = None) -> SearchResponse:
        """Execute a search and return a structured response.

        Uses semantic ranking for natural-language understanding and
        hit highlights.  Sort parameters are honoured when provided.

        Parameters
        ----------
        request:
            The search request containing query text, optional filters,
            pagination, and sort preferences.
        accessible_api_ids:
            When ``None``, no security filter is applied (admin bypass).
            When a list, search results are restricted to the named APIs.
        """
        start = time.monotonic()

        pagination = request.pagination or PaginationParams()
        skip = (pagination.page - 1) * pagination.page_size

        filter_expr = _build_odata_filter(request.filters, accessible_api_ids)

        # Determine query type — always use semantic for best results
        query_type = "semantic"

        # Build order_by from sort params
        order_by: list[str] | None = None
        if request.sort_by and request.sort_by != "relevance":
            index_field = _SORT_FIELD_MAP.get(request.sort_by, "")
            if index_field:
                direction = request.sort_order or "desc"
                order_by = [f"{index_field} {direction}"]

        raw = self._client.search(
            search_text=request.query,
            filter_expression=filter_expr,
            order_by=order_by,
            skip=skip,
            top=pagination.page_size,
            include_total_count=True,
            semantic_query=request.query,
            query_type=query_type,
        )

        results = [_map_search_result(r) for r in raw.get("results", [])]
        total_count = raw.get("count") or 0
        facets = _parse_facets(raw.get("facets"))

        elapsed_ms = (time.monotonic() - start) * 1000

        return SearchResponse(
            items=results,
            totalCount=total_count,
            facets=facets,
            queryDuration=round(elapsed_ms, 2),
        )

    def suggest(self, prefix: str, accessible_api_ids: list[str] | None = None) -> SuggestResponse:
        """Return autocomplete suggestions for the given prefix.

        Parameters
        ----------
        prefix:
            The text prefix to generate suggestions from.
        accessible_api_ids:
            When ``None``, no security filter is applied (admin bypass).
            When a list, only APIs with names in the list are suggested.
        """
        safe_prefix = sanitize_for_log(prefix)
        logger.debug(
            "SearchService.suggest — prefix=%s",
            safe_prefix,
            extra={"prefix": safe_prefix},
        )

        # Build a filter string for the suggest call.
        suggest_filter: str | None = None
        if accessible_api_ids is not None:
            if not accessible_api_ids:
                return SuggestResponse(suggestions=[], query_prefix=prefix)
            ids_csv = ",".join(accessible_api_ids)
            suggest_filter = f"search.in(apiName, '{ids_csv}', ',')"

        raw_suggestions = self._client.suggest(search_text=prefix, top=5, filter_expression=suggest_filter)

        suggestions: list[SuggestResult] = []
        for item in raw_suggestions:
            api_id = item.get("apiName", "")
            title = item.get("title", "")
            description = item.get("description", "")
            kind = item.get("kind", "")
            suggestions.append(SuggestResult(apiId=api_id, title=title, description=description, kind=kind))

        return SuggestResponse(suggestions=suggestions, query_prefix=prefix)
