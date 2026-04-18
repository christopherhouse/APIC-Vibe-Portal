"""Unit tests for the search service layer.

The AI Search client is fully mocked — only business logic is tested.
"""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from apic_vibe_portal_bff.models.search import (
    PaginationParams,
    SearchFilters,
    SearchRequest,
)
from apic_vibe_portal_bff.services.search_service import (
    SearchService,
    _build_odata_filter,
    _escape_odata_value,
    _extract_captions,
    _extract_highlights,
    _map_search_result,
    _parse_facets,
)

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def mock_client():
    return MagicMock()


@pytest.fixture
def service(mock_client):
    return SearchService(client=mock_client)


def _make_raw_result(
    id: str = "1",
    api_name: str = "petstore",
    title: str = "Petstore API",
    description: str = "A sample pet store API",
    kind: str = "rest",
    lifecycle: str = "production",
    score: float = 1.5,
    highlights: dict | None = None,
    captions: list | None = None,
) -> dict:
    """Create a raw AI Search result dict."""
    result = {
        "id": id,
        "apiName": api_name,
        "title": title,
        "description": description,
        "kind": kind,
        "lifecycleStage": lifecycle,
        "versions": ["v1"],
        "tags": ["pets", "sample"],
        "@search.score": score,
    }
    if highlights:
        result["@search.highlights"] = highlights
    if captions:
        result["@search.captions"] = captions
    return result


# ---------------------------------------------------------------------------
# OData filter builder
# ---------------------------------------------------------------------------


class TestBuildOdataFilter:
    def test_returns_none_for_none_filters(self):
        assert _build_odata_filter(None) is None

    def test_returns_none_for_empty_filters(self):
        filters = SearchFilters(kind=[], lifecycleStage=[], tags=[])
        assert _build_odata_filter(filters) is None

    def test_single_kind_filter(self):
        filters = SearchFilters(kind=["rest"])
        result = _build_odata_filter(filters)
        assert result == "(kind eq 'rest')"

    def test_multiple_kind_values(self):
        filters = SearchFilters(kind=["rest", "graphql"])
        result = _build_odata_filter(filters)
        assert result == "(kind eq 'rest' or kind eq 'graphql')"

    def test_lifecycle_filter(self):
        filters = SearchFilters(lifecycleStage=["production"])
        result = _build_odata_filter(filters)
        assert result == "(lifecycleStage eq 'production')"

    def test_tags_filter(self):
        filters = SearchFilters(tags=["pets"])
        result = _build_odata_filter(filters)
        assert result == "(tags/any(t: t eq 'pets'))"

    def test_combined_filters(self):
        filters = SearchFilters(kind=["rest"], lifecycleStage=["production"], tags=["pets"])
        result = _build_odata_filter(filters)
        assert "kind eq 'rest'" in result
        assert "lifecycleStage eq 'production'" in result
        assert "tags/any(t: t eq 'pets')" in result
        assert " and " in result

    def test_rejects_value_with_single_quotes(self):
        filters = SearchFilters(kind=["rest'; DROP TABLE--"])
        with pytest.raises(ValueError, match="Invalid filter value"):
            _build_odata_filter(filters)

    def test_rejects_value_with_special_chars(self):
        filters = SearchFilters(tags=["tag$(malicious)"])
        with pytest.raises(ValueError, match="Invalid filter value"):
            _build_odata_filter(filters)


# ---------------------------------------------------------------------------
# OData value escaping
# ---------------------------------------------------------------------------


class TestEscapeOdataValue:
    def test_passes_safe_value(self):
        assert _escape_odata_value("rest") == "rest"

    def test_passes_value_with_hyphen_and_underscore(self):
        assert _escape_odata_value("my-api_v2") == "my-api_v2"

    def test_passes_value_with_spaces(self):
        assert _escape_odata_value("my api") == "my api"

    def test_rejects_injection_attempt(self):
        with pytest.raises(ValueError):
            _escape_odata_value("rest' or 1 eq 1 or kind eq '")

    def test_rejects_semicolons(self):
        with pytest.raises(ValueError):
            _escape_odata_value("rest;evil")


# ---------------------------------------------------------------------------
# Highlight extraction
# ---------------------------------------------------------------------------


class TestExtractHighlights:
    def test_returns_empty_dict_when_no_highlights(self):
        result = {"id": "1"}
        assert _extract_highlights(result) == {}

    def test_extracts_highlights(self):
        result = {
            "@search.highlights": {
                "title": ["<em>Petstore</em> API"],
                "description": ["A sample <em>pet</em> store"],
            }
        }
        highlights = _extract_highlights(result)
        assert highlights["title"] == ["<em>Petstore</em> API"]
        assert highlights["description"] == ["A sample <em>pet</em> store"]


# ---------------------------------------------------------------------------
# Caption extraction
# ---------------------------------------------------------------------------


class TestExtractCaptions:
    def test_returns_empty_list_when_no_captions(self):
        assert _extract_captions({}) == []

    def test_extracts_from_dict_captions(self):
        result = {
            "@search.captions": [
                {"text": "The Petstore API provides pet management."},
            ]
        }
        captions = _extract_captions(result)
        assert captions == ["The Petstore API provides pet management."]

    def test_extracts_from_object_captions(self):
        caption = MagicMock()
        caption.text = "AI-generated caption"
        result = {"@search.captions": [caption]}
        captions = _extract_captions(result)
        assert captions == ["AI-generated caption"]

    def test_skips_empty_text(self):
        result = {"@search.captions": [{"text": ""}, {"text": "Valid caption"}]}
        captions = _extract_captions(result)
        assert captions == ["Valid caption"]


# ---------------------------------------------------------------------------
# Facet parsing
# ---------------------------------------------------------------------------


class TestParseFacets:
    def test_returns_empty_for_none(self):
        facets = _parse_facets(None)
        assert facets.facets == []

    def test_returns_empty_for_empty_dict(self):
        facets = _parse_facets({})
        assert facets.facets == []

    def test_parses_dict_facets(self):
        raw = {
            "kind": [{"value": "rest", "count": 5}, {"value": "graphql", "count": 2}],
            "lifecycleStage": [{"value": "production", "count": 4}],
        }
        facets = _parse_facets(raw)
        assert len(facets.facets) == 2

        kind_facet = next(f for f in facets.facets if f.field == "kind")
        assert len(kind_facet.values) == 2
        assert kind_facet.values[0].value == "rest"
        assert kind_facet.values[0].count == 5

    def test_parses_object_facets(self):
        bucket = MagicMock()
        bucket.value = "rest"
        bucket.count = 3
        raw = {"kind": [bucket]}
        facets = _parse_facets(raw)
        assert len(facets.facets) == 1
        assert facets.facets[0].values[0].value == "rest"
        assert facets.facets[0].values[0].count == 3


# ---------------------------------------------------------------------------
# Result mapping
# ---------------------------------------------------------------------------


class TestMapSearchResult:
    def test_maps_basic_result(self):
        raw = _make_raw_result()
        result = _map_search_result(raw)

        assert result.document.id == "1"
        assert result.document.api_name == "petstore"
        assert result.document.title == "Petstore API"
        assert result.score == 1.5
        assert result.highlights == {}
        assert result.captions == []

    def test_maps_result_with_highlights(self):
        raw = _make_raw_result(highlights={"title": ["<em>Pet</em>store"]})
        result = _map_search_result(raw)
        assert result.highlights == {"title": ["<em>Pet</em>store"]}

    def test_maps_result_with_captions(self):
        raw = _make_raw_result(captions=[{"text": "A caption"}])
        result = _map_search_result(raw)
        assert result.captions == ["A caption"]

    def test_maps_reranker_score_from_camel_case_key(self):
        raw = _make_raw_result()
        raw["@search.rerankerScore"] = 2.75
        result = _map_search_result(raw)
        assert result.reranker_score == 2.75


# ---------------------------------------------------------------------------
# SearchService.search
# ---------------------------------------------------------------------------


class TestSearchServiceSearch:
    def test_basic_search(self, service, mock_client):
        mock_client.search.return_value = {
            "results": [_make_raw_result()],
            "count": 1,
            "facets": {"kind": [{"value": "rest", "count": 1}]},
        }

        request = SearchRequest(query="petstore")
        response = service.search(request)

        assert len(response.items) == 1
        assert response.total_count == 1
        assert response.items[0].document.api_name == "petstore"
        assert response.query_duration > 0

    def test_search_with_pagination(self, service, mock_client):
        mock_client.search.return_value = {
            "results": [_make_raw_result(id="3")],
            "count": 50,
            "facets": None,
        }

        request = SearchRequest(
            query="test",
            pagination=PaginationParams(page=3, pageSize=10),
        )
        service.search(request)

        call_kwargs = mock_client.search.call_args
        assert call_kwargs.kwargs["skip"] == 20  # (3-1) * 10
        assert call_kwargs.kwargs["top"] == 10

    def test_search_with_filters(self, service, mock_client):
        mock_client.search.return_value = {
            "results": [],
            "count": 0,
            "facets": None,
        }

        request = SearchRequest(
            query="test",
            filters=SearchFilters(kind=["rest"], lifecycleStage=["production"]),
        )
        service.search(request)

        call_kwargs = mock_client.search.call_args
        filter_expr = call_kwargs.kwargs["filter_expression"]
        assert "kind eq 'rest'" in filter_expr
        assert "lifecycleStage eq 'production'" in filter_expr

    def test_search_empty_query(self, service, mock_client):
        mock_client.search.return_value = {
            "results": [],
            "count": 0,
            "facets": {},
        }

        request = SearchRequest(query="")
        response = service.search(request)

        assert response.items == []
        assert response.total_count == 0

    def test_search_returns_facets(self, service, mock_client):
        mock_client.search.return_value = {
            "results": [],
            "count": 0,
            "facets": {
                "kind": [{"value": "rest", "count": 5}],
                "tags": [{"value": "pets", "count": 3}],
            },
        }

        request = SearchRequest(query="test")
        response = service.search(request)

        assert response.facets is not None
        assert len(response.facets.facets) == 2

    def test_search_multiple_results(self, service, mock_client):
        mock_client.search.return_value = {
            "results": [
                _make_raw_result(id="1", api_name="petstore", score=2.0),
                _make_raw_result(id="2", api_name="weather", title="Weather API", score=1.5),
            ],
            "count": 2,
            "facets": None,
        }

        request = SearchRequest(query="api")
        response = service.search(request)

        assert len(response.items) == 2
        assert response.items[0].score == 2.0
        assert response.items[1].document.api_name == "weather"

    def test_search_uses_semantic_query_type(self, service, mock_client):
        mock_client.search.return_value = {
            "results": [],
            "count": 0,
            "facets": None,
        }

        request = SearchRequest(query="find user auth APIs")
        service.search(request)

        call_kwargs = mock_client.search.call_args
        assert call_kwargs.kwargs["query_type"] == "semantic"
        assert call_kwargs.kwargs["semantic_query"] == "find user auth APIs"

    def test_search_passes_sort_by_name(self, service, mock_client):
        mock_client.search.return_value = {
            "results": [],
            "count": 0,
            "facets": None,
        }

        request = SearchRequest(query="test", sortBy="name", sortOrder="asc")
        service.search(request)

        call_kwargs = mock_client.search.call_args
        assert call_kwargs.kwargs["order_by"] == ["apiName asc"]

    def test_search_passes_sort_by_updated_at(self, service, mock_client):
        mock_client.search.return_value = {
            "results": [],
            "count": 0,
            "facets": None,
        }

        request = SearchRequest(query="test", sortBy="updatedAt", sortOrder="desc")
        service.search(request)

        call_kwargs = mock_client.search.call_args
        assert call_kwargs.kwargs["order_by"] == ["updatedAt desc"]

    def test_search_no_order_by_for_relevance(self, service, mock_client):
        mock_client.search.return_value = {
            "results": [],
            "count": 0,
            "facets": None,
        }

        request = SearchRequest(query="test", sortBy="relevance")
        service.search(request)

        call_kwargs = mock_client.search.call_args
        assert call_kwargs.kwargs["order_by"] is None

    def test_search_no_order_by_when_sort_not_specified(self, service, mock_client):
        mock_client.search.return_value = {
            "results": [],
            "count": 0,
            "facets": None,
        }

        request = SearchRequest(query="test")
        service.search(request)

        call_kwargs = mock_client.search.call_args
        assert call_kwargs.kwargs["order_by"] is None


# ---------------------------------------------------------------------------
# SearchService.suggest
# ---------------------------------------------------------------------------


class TestSearchServiceSuggest:
    def test_suggest_returns_suggestions(self, service, mock_client):
        mock_client.suggest.return_value = [
            {
                "apiName": "petstore",
                "title": "Petstore API",
                "description": "Manages pets",
                "kind": "rest",
                "@search.text": "Petstore API",
            },
            {
                "apiName": "pets-v2",
                "title": "Pets v2 API",
                "description": "Pets v2",
                "kind": "graphql",
                "@search.text": "Pets v2 API",
            },
        ]

        response = service.suggest("pet")

        assert len(response.suggestions) == 2
        assert response.suggestions[0].api_id == "petstore"
        assert response.suggestions[0].title == "Petstore API"
        assert response.suggestions[0].description == "Manages pets"
        assert response.suggestions[0].kind == "rest"
        assert response.query_prefix == "pet"

    def test_suggest_empty_prefix(self, service, mock_client):
        mock_client.suggest.return_value = []

        response = service.suggest("")

        assert response.suggestions == []
        assert response.query_prefix == ""

    def test_suggest_uses_title_as_fallback(self, service, mock_client):
        mock_client.suggest.return_value = [
            {"apiName": "petstore", "title": "Petstore API"},
        ]

        response = service.suggest("pet")

        assert response.suggestions[0].title == "Petstore API"
