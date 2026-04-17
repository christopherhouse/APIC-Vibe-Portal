"""Search service — business logic for API search operations.

Orchestrates calls to :class:`AISearchClient`, transforms AI Search SDK
results into Pydantic response models, and implements hybrid search
(keyword + semantic + vector with RRF).
"""

from __future__ import annotations

import logging
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
    SuggestResponse,
    SuggestResult,
)

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _build_odata_filter(filters: SearchFilters | None) -> str | None:
    """Build an OData filter expression from :class:`SearchFilters`.

    Each field supports multi-value OR filters.  Multiple fields are combined
    with AND.
    """
    if filters is None:
        return None

    parts: list[str] = []

    if filters.kind:
        kind_clauses = " or ".join(f"kind eq '{v}'" for v in filters.kind)
        parts.append(f"({kind_clauses})")

    if filters.lifecycle_stage:
        lc_clauses = " or ".join(f"lifecycleStage eq '{v}'" for v in filters.lifecycle_stage)
        parts.append(f"({lc_clauses})")

    if filters.tags:
        # Collection fields use any()
        tag_clauses = " or ".join(f"tags/any(t: t eq '{v}')" for v in filters.tags)
        parts.append(f"({tag_clauses})")

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
        reranker_score=result.get("@search.reranker_score"),
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

    def search(self, request: SearchRequest) -> SearchResponse:
        """Execute a hybrid search and return a structured response.

        Combines keyword search, semantic ranking, and (when a vector is
        available) vector search.  Results are merged via Reciprocal Rank
        Fusion (RRF) which is handled by the AI Search service.

        Parameters
        ----------
        request:
            The search request containing query text, optional filters,
            pagination, and sort preferences.
        """
        start = time.monotonic()

        pagination = request.pagination or PaginationParams()
        skip = (pagination.page - 1) * pagination.page_size

        filter_expr = _build_odata_filter(request.filters)

        # Determine query type — always use semantic for best results
        query_type = "semantic"

        raw = self._client.search(
            search_text=request.query,
            filter_expression=filter_expr,
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

    def suggest(self, prefix: str) -> SuggestResponse:
        """Return autocomplete suggestions for the given prefix.

        Parameters
        ----------
        prefix:
            The text prefix to generate suggestions from.
        """
        raw_suggestions = self._client.suggest(search_text=prefix, top=5)

        suggestions: list[SuggestResult] = []
        for item in raw_suggestions:
            text = item.get("@search.text", item.get("title", ""))
            api_name = item.get("apiName", "")
            suggestions.append(SuggestResult(text=text, apiName=api_name))

        return SuggestResponse(suggestions=suggestions, query_prefix=prefix)
