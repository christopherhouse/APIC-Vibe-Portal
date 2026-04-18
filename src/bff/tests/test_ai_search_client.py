"""Unit tests for the AI Search client wrapper.

All Azure SDK calls are mocked — no real search service is needed.
"""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from apic_vibe_portal_bff.clients.ai_search_client import (
    FACET_FIELDS,
    HIGHLIGHT_FIELDS,
    AISearchClient,
    AISearchClientError,
    AISearchNotFoundError,
    AISearchUnavailableError,
)

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def mock_credential():
    return MagicMock()


@pytest.fixture
def client(mock_credential):
    return AISearchClient(
        endpoint="https://test-search.search.windows.net",
        index_name="test-index",
        credential=mock_credential,
    )


def _make_mock_search_response(results: list[dict], count: int = 0, facets: dict | None = None):
    """Create a mock search response that behaves like the SDK response."""
    mock_response = MagicMock()
    mock_response.__iter__ = MagicMock(return_value=iter(results))
    mock_response.get_count.return_value = count
    mock_response.get_facets.return_value = facets
    return mock_response


# ---------------------------------------------------------------------------
# Construction
# ---------------------------------------------------------------------------


class TestAISearchClientInit:
    def test_creates_with_provided_credential(self, mock_credential):
        client = AISearchClient(
            endpoint="https://test.search.windows.net",
            index_name="my-index",
            credential=mock_credential,
        )
        assert client._endpoint == "https://test.search.windows.net"
        assert client._index_name == "my-index"
        assert client._credential is mock_credential

    def test_creates_with_default_credential(self):
        with patch("apic_vibe_portal_bff.clients.ai_search_client.DefaultAzureCredential") as mock_cred:
            client = AISearchClient(
                endpoint="https://test.search.windows.net",
                index_name="my-index",
            )
            assert client._credential is mock_cred.return_value

    def test_lazy_client_creation(self, client):
        assert client._client is None

    def test_normalizes_http_to_https(self, mock_credential):
        client = AISearchClient(
            endpoint="http://test.search.windows.net",
            index_name="my-index",
            credential=mock_credential,
        )
        assert client._endpoint == "https://test.search.windows.net"

    def test_prepends_https_when_no_scheme(self, mock_credential):
        client = AISearchClient(
            endpoint="test.search.windows.net",
            index_name="my-index",
            credential=mock_credential,
        )
        assert client._endpoint == "https://test.search.windows.net"

    def test_preserves_https_endpoint(self, mock_credential):
        client = AISearchClient(
            endpoint="https://test.search.windows.net",
            index_name="my-index",
            credential=mock_credential,
        )
        assert client._endpoint == "https://test.search.windows.net"

    def test_handles_empty_endpoint(self, mock_credential):
        client = AISearchClient(
            endpoint="",
            index_name="my-index",
            credential=mock_credential,
        )
        assert client._endpoint == ""


# ---------------------------------------------------------------------------
# Search
# ---------------------------------------------------------------------------


class TestAISearchClientSearch:
    def test_basic_search_returns_results(self, client):
        results = [
            {"id": "1", "apiName": "petstore", "title": "Petstore API", "@search.score": 1.5},
            {"id": "2", "apiName": "weather", "title": "Weather API", "@search.score": 1.2},
        ]
        facets = {"kind": [{"value": "rest", "count": 2}]}
        mock_response = _make_mock_search_response(results, count=2, facets=facets)

        mock_sdk_client = MagicMock()
        mock_sdk_client.search.return_value = mock_response
        client._client = mock_sdk_client

        response = client.search("petstore")

        assert len(response["results"]) == 2
        assert response["count"] == 2
        assert response["facets"] == facets

    def test_search_with_filter_and_pagination(self, client):
        mock_response = _make_mock_search_response([], count=0, facets=None)
        mock_sdk_client = MagicMock()
        mock_sdk_client.search.return_value = mock_response
        client._client = mock_sdk_client

        client.search(
            "test",
            filter_expression="kind eq 'rest'",
            skip=20,
            top=10,
        )

        call_kwargs = mock_sdk_client.search.call_args
        assert call_kwargs.kwargs["filter"] == "kind eq 'rest'"
        assert call_kwargs.kwargs["skip"] == 20
        assert call_kwargs.kwargs["top"] == 10

    def test_search_with_semantic_mode(self, client):
        mock_response = _make_mock_search_response([], count=0)
        mock_sdk_client = MagicMock()
        mock_sdk_client.search.return_value = mock_response
        client._client = mock_sdk_client

        client.search(
            "find user management APIs",
            query_type="semantic",
            semantic_query="user management",
        )

        call_kwargs = mock_sdk_client.search.call_args
        assert call_kwargs.kwargs["query_type"] == "semantic"
        assert call_kwargs.kwargs["semantic_configuration_name"] == "apic-semantic-config"
        assert call_kwargs.kwargs["query_caption"] == "extractive"
        assert call_kwargs.kwargs["semantic_query"] == "user management"

    def test_search_with_vector(self, client):
        mock_response = _make_mock_search_response([], count=0)
        mock_sdk_client = MagicMock()
        mock_sdk_client.search.return_value = mock_response
        client._client = mock_sdk_client

        vector = [0.1] * 1536
        client.search("test", vector=vector)

        call_kwargs = mock_sdk_client.search.call_args
        assert "vector_queries" in call_kwargs.kwargs
        assert len(call_kwargs.kwargs["vector_queries"]) == 1

    def test_search_passes_facets_and_highlights(self, client):
        mock_response = _make_mock_search_response([], count=0)
        mock_sdk_client = MagicMock()
        mock_sdk_client.search.return_value = mock_response
        client._client = mock_sdk_client

        client.search("test")

        call_kwargs = mock_sdk_client.search.call_args
        assert call_kwargs.kwargs["facets"] == FACET_FIELDS
        assert call_kwargs.kwargs["highlight_fields"] == HIGHLIGHT_FIELDS

    def test_search_handles_not_found_error(self, client):
        from azure.core.exceptions import ResourceNotFoundError

        mock_sdk_client = MagicMock()
        mock_sdk_client.search.side_effect = ResourceNotFoundError("Index not found")
        client._client = mock_sdk_client

        with pytest.raises(AISearchNotFoundError):
            client.search("test")

    def test_search_handles_http_error(self, client):
        from azure.core.exceptions import HttpResponseError

        error = HttpResponseError("Bad request")
        error.status_code = 400
        mock_sdk_client = MagicMock()
        mock_sdk_client.search.side_effect = error
        client._client = mock_sdk_client

        with pytest.raises(AISearchClientError) as exc_info:
            client.search("test")
        assert exc_info.value.status_code == 400

    def test_search_handles_server_error(self, client):
        from azure.core.exceptions import HttpResponseError

        error = HttpResponseError("Server error")
        error.status_code = 503
        mock_sdk_client = MagicMock()
        mock_sdk_client.search.side_effect = error
        client._client = mock_sdk_client

        with pytest.raises(AISearchUnavailableError):
            client.search("test")

    def test_search_empty_query(self, client):
        mock_response = _make_mock_search_response([], count=0, facets={})
        mock_sdk_client = MagicMock()
        mock_sdk_client.search.return_value = mock_response
        client._client = mock_sdk_client

        response = client.search("")

        assert response["results"] == []
        assert response["count"] == 0


# ---------------------------------------------------------------------------
# Suggest
# ---------------------------------------------------------------------------


class TestAISearchClientSuggest:
    def test_suggest_returns_results(self, client):
        suggestions = [
            {"apiName": "petstore", "title": "Petstore API", "@search.text": "Petstore API"},
            {"apiName": "weather", "title": "Weather API", "@search.text": "Weather API"},
        ]
        mock_sdk_client = MagicMock()
        mock_sdk_client.suggest.return_value = suggestions
        client._client = mock_sdk_client

        result = client.suggest("pet")

        assert len(result) == 2
        assert result[0]["apiName"] == "petstore"

    def test_suggest_passes_correct_params(self, client):
        mock_sdk_client = MagicMock()
        mock_sdk_client.suggest.return_value = []
        client._client = mock_sdk_client

        client.suggest("test", top=3)

        call_kwargs = mock_sdk_client.suggest.call_args
        assert call_kwargs.kwargs["top"] == 3
        assert call_kwargs.kwargs["suggester_name"] == "sg"
        # select must only contain suggester source fields (no "kind")
        assert call_kwargs.kwargs["select"] == ["apiName", "title", "description"]

    def test_suggest_handles_error(self, client):
        from azure.core.exceptions import HttpResponseError

        error = HttpResponseError("Bad request")
        error.status_code = 400
        mock_sdk_client = MagicMock()
        mock_sdk_client.suggest.side_effect = error
        client._client = mock_sdk_client

        with pytest.raises(AISearchClientError):
            client.suggest("test")


# ---------------------------------------------------------------------------
# Error handling diagnostics
# ---------------------------------------------------------------------------


class TestAISearchClientErrorHandling:
    def test_handle_error_extracts_error_details_from_http_response(self, client):
        """_handle_error should extract error_code and error_message from HttpResponseError."""
        from azure.core.exceptions import HttpResponseError

        error = HttpResponseError("Bad request")
        error.status_code = 400
        # Simulate the OData error structure returned by Azure Search
        error.error = MagicMock()
        error.error.code = "InvalidRequestParameter"
        error.error.message = "The field 'kind' is not valid in this context."
        error.response = MagicMock()
        error.response.text.return_value = (
            '{"error":{"code":"InvalidRequestParameter",'
            '"message":"The field \'kind\' is not valid in this context."}}'
        )

        with pytest.raises(AISearchClientError) as exc_info:
            client._handle_error(error, "suggest query: test")

        assert exc_info.value.status_code == 400
        # The raised exception should carry the detailed error message
        assert "The field 'kind' is not valid in this context." in str(exc_info.value)

    def test_handle_error_falls_back_to_str_when_no_error_detail(self, client):
        """_handle_error should fall back to str(exc) when .error is not set."""
        from azure.core.exceptions import HttpResponseError

        error = HttpResponseError("Operation returned bad status")
        error.status_code = 400
        error.error = None
        error.response = None

        with pytest.raises(AISearchClientError) as exc_info:
            client._handle_error(error, "suggest query: test")

        assert exc_info.value.status_code == 400
        assert "Operation returned bad status" in str(exc_info.value)

    def test_handle_error_logs_response_body(self, client, caplog):
        """_handle_error should log the response body for diagnostics."""
        import logging

        from azure.core.exceptions import HttpResponseError

        error = HttpResponseError("Bad request")
        error.status_code = 400
        error.error = MagicMock()
        error.error.code = "InvalidField"
        error.error.message = "Field error"
        response_body = '{"error":{"code":"InvalidField","message":"Field error"}}'
        mock_response = MagicMock()
        mock_response.text.return_value = response_body
        error.response = mock_response

        with caplog.at_level(logging.ERROR), pytest.raises(AISearchClientError):
            client._handle_error(error, "suggest query: test")

        # Verify both the error code and the response body appear in the log
        assert any("InvalidField" in r.message for r in caplog.records)
        assert any(response_body in r.message for r in caplog.records)

    def test_handle_error_server_error_uses_error_message(self, client):
        """_handle_error should use error_message for 500+ errors when available."""
        from azure.core.exceptions import HttpResponseError

        error = HttpResponseError("Server error")
        error.status_code = 503
        error.error = MagicMock()
        error.error.code = "ServiceUnavailable"
        error.error.message = "Search service is temporarily unavailable"
        error.response = None

        with pytest.raises(AISearchUnavailableError) as exc_info:
            client._handle_error(error, "search query: test")

        assert "Search service is temporarily unavailable" in str(exc_info.value)


# ---------------------------------------------------------------------------
# Lifecycle
# ---------------------------------------------------------------------------


class TestAISearchClientLifecycle:
    def test_close_closes_client(self, client):
        mock_sdk_client = MagicMock()
        client._client = mock_sdk_client

        client.close()

        mock_sdk_client.close.assert_called_once()
        assert client._client is None

    def test_close_noop_when_no_client(self, client):
        client.close()  # Should not raise
        assert client._client is None
