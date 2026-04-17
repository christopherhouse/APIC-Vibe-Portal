"""Pydantic models for Azure AI Search documents and results.

These models describe the shape of documents stored in (and retrieved from)
the AI Search index, and the response envelope the BFF returns to the
frontend.  They intentionally mirror the index field names defined in
``src/indexer/indexer/index_schema.py`` so that the BFF search layer can
deserialise AI Search responses with minimal mapping.
"""

from __future__ import annotations

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
# Facet value (used in filter UI)
# ---------------------------------------------------------------------------


class FacetValue(BaseModel):
    """A single facet bucket returned by AI Search."""

    value: str
    count: int


class SearchFacets(BaseModel):
    """Aggregated facet counts for filter sidebar rendering."""

    kind: list[FacetValue] = Field(default_factory=list)
    lifecycle_stage: list[FacetValue] = Field(default_factory=list)
    tags: list[FacetValue] = Field(default_factory=list)


# ---------------------------------------------------------------------------
# Search request / response
# ---------------------------------------------------------------------------


class SearchRequest(BaseModel):
    """Parameters for a hybrid search query issued by the frontend."""

    query: str = Field(description="Free-text search query")
    page: int = Field(default=1, ge=1, description="1-based page number")
    page_size: int = Field(default=20, ge=1, le=100, description="Results per page")
    kind_filter: list[str] = Field(default_factory=list, description="Filter to specific API kinds")
    lifecycle_filter: list[str] = Field(
        default_factory=list,
        description="Filter to specific lifecycle stages",
    )
    tag_filter: list[str] = Field(default_factory=list, description="Filter to specific tags")


class SearchResponse(BaseModel):
    """Response envelope for a hybrid search query."""

    results: list[SearchResult]
    total_count: int = Field(description="Total number of matching documents (unbounded)")
    page: int
    page_size: int
    facets: SearchFacets = Field(default_factory=SearchFacets)
    query: str = Field(description="The original query string echoed back")


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
