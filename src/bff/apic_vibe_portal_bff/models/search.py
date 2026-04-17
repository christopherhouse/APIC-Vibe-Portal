"""Pydantic models for Azure AI Search documents and results.

These models serve two distinct purposes:

1. **Internal AI Search models** (``SearchDocument``, ``SearchResult``):
   Mirror the AI Search index schema so the BFF search layer can deserialise
   SDK results with minimal mapping.

2. **BFF endpoint DTOs** (``SearchRequest``, ``SearchResponse``,
   ``SearchFilters``, ``SearchFacet``, ``SearchFacetValue``, ``SearchFacets``):
   Align with the shared TypeScript DTOs in
   ``src/shared/src/dto/search-request.ts`` and ``search-response.ts`` so the
   BFF API contract matches what the frontend expects.
"""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field

# ---------------------------------------------------------------------------
# Search document (mirrors the AI Search index schema)
# ---------------------------------------------------------------------------


class SearchDocument(BaseModel):
    """A single document as stored in the AI Search index.

    Field names match the camelCase index field names so that the BFF search
    client can pass raw SDK result dicts directly to ``model_validate``.
    """

    id: str
    api_name: str = Field(alias="apiName")
    title: str
    description: str = ""
    kind: str = ""
    lifecycle_stage: str = Field(default="", alias="lifecycleStage")
    versions: list[str] = Field(default_factory=list)
    contacts: list[str] = Field(default_factory=list)
    tags: list[str] = Field(default_factory=list)
    custom_properties: str = Field(default="", alias="customProperties")
    spec_content: str = Field(default="", alias="specContent")
    created_at: str | None = Field(default=None, alias="createdAt")
    updated_at: str | None = Field(default=None, alias="updatedAt")

    model_config = {"populate_by_name": True}


# ---------------------------------------------------------------------------
# Search result (document + relevance metadata)
# ---------------------------------------------------------------------------


class SearchResult(BaseModel):
    """A single hit returned by a hybrid search query.

    Wraps :class:`SearchDocument` with relevance signals provided by the
    AI Search service (score, semantic caption, highlights).
    """

    document: SearchDocument
    score: float = Field(default=0.0, description="@search.score from AI Search")
    reranker_score: float | None = Field(
        default=None,
        description="@search.rerankerScore — semantic re-ranking score (present when semantic search is enabled)",
    )
    highlights: dict[str, list[str]] = Field(
        default_factory=dict,
        description="Hit highlights keyed by field name",
    )
    captions: list[str] = Field(
        default_factory=list,
        description="Semantic captions (short answer extracts) from the document",
    )


# ---------------------------------------------------------------------------
# Facet models — aligned with shared SearchFacet / SearchFacets TS types
# ---------------------------------------------------------------------------


class SearchFacetValue(BaseModel):
    """A single facet bucket returned by AI Search."""

    value: str
    count: int


class SearchFacet(BaseModel):
    """A facet category with all its bucketed values."""

    field: str
    values: list[SearchFacetValue] = Field(default_factory=list)


class SearchFacets(BaseModel):
    """Aggregated facets for filter sidebar rendering.

    Mirrors the TypeScript ``SearchFacets`` interface in
    ``src/shared/src/models/search-result.ts``.
    """

    facets: list[SearchFacet] = Field(default_factory=list)


# ---------------------------------------------------------------------------
# Sort types — aligned with shared SearchSortField / SearchSortOrder TS types
# ---------------------------------------------------------------------------

SearchSortField = Literal["relevance", "name", "updatedAt", "createdAt"]
SearchSortOrder = Literal["asc", "desc"]


# ---------------------------------------------------------------------------
# Search filters — aligned with shared SearchFilters TS type
# ---------------------------------------------------------------------------


class SearchFilters(BaseModel):
    """Optional filters for a search query.

    Mirrors the TypeScript ``SearchFilters`` interface in
    ``src/shared/src/dto/search-request.ts``.
    """

    kind: list[str] = Field(default_factory=list)
    lifecycle_stage: list[str] = Field(default_factory=list, alias="lifecycleStage")
    tags: list[str] = Field(default_factory=list)

    model_config = {"populate_by_name": True}


# ---------------------------------------------------------------------------
# Pagination params — aligned with shared PaginationParams TS type
# ---------------------------------------------------------------------------


class PaginationParams(BaseModel):
    """Pagination request parameters.

    Mirrors the TypeScript ``PaginationParams`` interface in
    ``src/shared/src/models/pagination.ts``.
    """

    page: int = Field(default=1, ge=1)
    page_size: int = Field(default=20, ge=1, le=100, alias="pageSize")

    model_config = {"populate_by_name": True}


# ---------------------------------------------------------------------------
# Search request / response — aligned with shared TS DTOs
# ---------------------------------------------------------------------------


class SearchRequest(BaseModel):
    """Parameters for a hybrid search query.

    Mirrors the TypeScript ``SearchRequest`` interface in
    ``src/shared/src/dto/search-request.ts``.
    """

    query: str = Field(description="Free-text search query")
    filters: SearchFilters | None = Field(default=None)
    sort_by: SearchSortField | None = Field(default=None, alias="sortBy")
    sort_order: SearchSortOrder | None = Field(default=None, alias="sortOrder")
    pagination: PaginationParams | None = Field(default=None)

    model_config = {"populate_by_name": True}


class SearchResponse(BaseModel):
    """Response envelope for a hybrid search query.

    Mirrors the TypeScript ``SearchResult<ApiCatalogItem>`` shape defined in
    ``src/shared/src/models/search-result.ts`` and re-exported as
    ``SearchResponse`` in ``src/shared/src/dto/search-response.ts``.
    """

    items: list[SearchResult]
    total_count: int = Field(description="Total number of matching documents (unbounded)", alias="totalCount")
    facets: SearchFacets | None = Field(default=None)
    query_duration: float = Field(
        default=0.0,
        description="Query execution time in milliseconds",
        alias="queryDuration",
    )

    model_config = {"populate_by_name": True}


# ---------------------------------------------------------------------------
# Suggest response (autocomplete)
# ---------------------------------------------------------------------------


class SuggestResult(BaseModel):
    """A single autocomplete suggestion."""

    text: str
    api_name: str = Field(alias="apiName")

    model_config = {"populate_by_name": True}


class SuggestResponse(BaseModel):
    """Response envelope for autocomplete suggestions."""

    suggestions: list[SuggestResult]
    query_prefix: str = Field(description="The prefix used to generate suggestions")
