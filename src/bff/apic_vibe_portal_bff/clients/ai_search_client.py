"""Azure AI Search client wrapper.

Wraps ``azure-search-documents`` SDK with error handling, structured logging,
and a clean interface consumed by the search service layer.  Authentication
uses ``DefaultAzureCredential`` (managed identity in production, developer
credential chain locally).
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Any

from azure.core.credentials import AzureKeyCredential, TokenCredential
from azure.core.exceptions import HttpResponseError, ResourceNotFoundError
from azure.identity import DefaultAzureCredential

if TYPE_CHECKING:
    from azure.search.documents import SearchClient as _SearchClientType

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Constants matching the indexer's schema
# ---------------------------------------------------------------------------

_SEMANTIC_CONFIG_NAME = "apic-semantic-config"
_VECTOR_FIELD_NAME = "contentVector"

# Facetable fields in the index schema
FACET_FIELDS = ["kind", "lifecycleStage", "tags"]

# Searchable text fields for highlight extraction
HIGHLIGHT_FIELDS = "title,description,apiName"

# Fields for the suggest endpoint
SUGGEST_FIELDS = ["apiName", "title", "description", "kind"]


# ---------------------------------------------------------------------------
# Custom exceptions
# ---------------------------------------------------------------------------


class AISearchClientError(Exception):
    """Base error raised by :class:`AISearchClient`."""

    def __init__(self, message: str, status_code: int | None = None) -> None:
        super().__init__(message)
        self.status_code = status_code


class AISearchNotFoundError(AISearchClientError):
    """Raised when the search index or resource is not found."""

    def __init__(self, resource: str) -> None:
        super().__init__(f"Resource not found: {resource}", status_code=404)


class AISearchUnavailableError(AISearchClientError):
    """Raised when the AI Search service is unavailable."""

    def __init__(self, detail: str = "AI Search service unavailable") -> None:
        super().__init__(detail, status_code=503)


# ---------------------------------------------------------------------------
# Client
# ---------------------------------------------------------------------------


class AISearchClient:
    """Thin wrapper around the Azure AI Search Python SDK.

    Parameters
    ----------
    endpoint:
        Azure AI Search service endpoint URL
        (e.g. ``https://my-search.search.windows.net``).
        If the URL uses ``http://``, it is automatically upgraded to
        ``https://`` because the Azure SDK requires TLS for bearer-token
        authentication.
    index_name:
        Name of the search index to query.
    credential:
        An Azure credential object.  Defaults to ``DefaultAzureCredential``.
    """

    def __init__(
        self,
        endpoint: str,
        index_name: str,
        credential: TokenCredential | AzureKeyCredential | None = None,
    ) -> None:
        self._endpoint = self._normalize_endpoint(endpoint)
        self._index_name = index_name
        self._credential = credential or DefaultAzureCredential()
        self._client: _SearchClientType | None = None

    @staticmethod
    def _normalize_endpoint(endpoint: str) -> str:
        """Ensure the endpoint uses HTTPS.

        The Azure SDK enforces HTTPS for bearer-token authentication.
        This method upgrades ``http://`` to ``https://`` and prepends
        ``https://`` when no scheme is present.
        """
        stripped = endpoint.strip()
        if not stripped:
            return stripped
        if stripped.startswith("http://"):
            logger.warning(
                "AI Search endpoint uses http:// — upgrading to https://",
                extra={"original_endpoint": stripped},
            )
            return "https://" + stripped[len("http://") :]
        if not stripped.startswith("https://"):
            return "https://" + stripped
        return stripped

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _get_client(self) -> _SearchClientType:
        """Lazily create and return the search client."""
        if self._client is None:
            from azure.search.documents import SearchClient

            self._client = SearchClient(
                endpoint=self._endpoint,
                index_name=self._index_name,
                credential=self._credential,
            )
        return self._client

    def _handle_error(self, exc: Exception, context: str) -> None:
        """Translate Azure SDK exceptions into domain errors."""
        if isinstance(exc, ResourceNotFoundError):
            raise AISearchNotFoundError(context) from exc
        if isinstance(exc, HttpResponseError):
            status = exc.status_code
            if status is not None and status >= 500:
                raise AISearchUnavailableError(str(exc)) from exc
            raise AISearchClientError(str(exc), status_code=status) from exc
        raise AISearchClientError(str(exc)) from exc

    # ------------------------------------------------------------------
    # Search
    # ------------------------------------------------------------------

    def search(
        self,
        search_text: str,
        *,
        filter_expression: str | None = None,
        order_by: list[str] | None = None,
        skip: int = 0,
        top: int = 20,
        include_total_count: bool = True,
        semantic_query: str | None = None,
        vector: list[float] | None = None,
        query_type: str = "simple",
    ) -> dict[str, Any]:
        """Execute a search query against the AI Search index.

        Parameters
        ----------
        search_text:
            The search query text.
        filter_expression:
            OData filter expression.
        order_by:
            List of fields and directions for sorting (e.g. ``["title asc"]``).
        skip:
            Number of results to skip (for pagination).
        top:
            Maximum number of results to return.
        include_total_count:
            Whether to include the total count of matching documents.
        semantic_query:
            Natural-language query for semantic ranking.
        vector:
            Embedding vector for vector search.
        query_type:
            ``"simple"`` or ``"semantic"``.

        Returns
        -------
        dict with ``results``, ``count``, and ``facets`` keys.
        """
        logger.debug(
            "AISearchClient.search",
            extra={
                "query": search_text,
                "filter": filter_expression,
                "skip": skip,
                "top": top,
                "query_type": query_type,
            },
        )

        try:
            from azure.search.documents.models import VectorizedQuery

            search_kwargs: dict[str, Any] = {
                "search_text": search_text,
                "filter": filter_expression,
                "order_by": order_by,
                "skip": skip,
                "top": top,
                "include_total_count": include_total_count,
                "facets": FACET_FIELDS,
                "highlight_fields": HIGHLIGHT_FIELDS,
                "query_type": query_type,
            }

            # Semantic configuration
            if query_type == "semantic":
                search_kwargs["semantic_configuration_name"] = _SEMANTIC_CONFIG_NAME
                search_kwargs["query_caption"] = "extractive"
                if semantic_query:
                    search_kwargs["semantic_query"] = semantic_query

            # Vector search
            if vector is not None:
                search_kwargs["vector_queries"] = [
                    VectorizedQuery(
                        vector=vector,
                        k_nearest_neighbors=top,
                        fields=_VECTOR_FIELD_NAME,
                    )
                ]

            client = self._get_client()
            response = client.search(**search_kwargs)

            results: list[dict[str, Any]] = []
            for result in response:
                results.append(dict(result))

            return {
                "results": results,
                "count": response.get_count(),
                "facets": response.get_facets(),
            }

        except (ResourceNotFoundError, HttpResponseError) as exc:
            self._handle_error(exc, f"search query: {search_text}")
            return {"results": [], "count": 0, "facets": None}  # unreachable; satisfies type checker

    # ------------------------------------------------------------------
    # Suggest (autocomplete)
    # ------------------------------------------------------------------

    def suggest(
        self,
        search_text: str,
        suggester_name: str = "sg",
        *,
        top: int = 5,
        filter_expression: str | None = None,
    ) -> list[dict[str, Any]]:
        """Return autocomplete suggestions for a prefix.

        Parameters
        ----------
        search_text:
            The prefix text to get suggestions for.
        suggester_name:
            Name of the suggester defined on the index.
        top:
            Maximum number of suggestions.
        filter_expression:
            Optional OData filter.

        Returns
        -------
        List of suggestion dicts.
        """
        logger.debug(
            "AISearchClient.suggest",
            extra={"prefix": search_text, "top": top},
        )
        try:
            client = self._get_client()
            response = client.suggest(
                search_text=search_text,
                suggester_name=suggester_name,
                top=top,
                filter=filter_expression,
                select=SUGGEST_FIELDS,
            )
            return [dict(r) for r in response]

        except (ResourceNotFoundError, HttpResponseError) as exc:
            self._handle_error(exc, f"suggest query: {search_text}")
            return []  # unreachable; satisfies type checker

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------

    def close(self) -> None:
        """Close the underlying search client."""
        if self._client is not None:
            self._client.close()
            self._client = None
