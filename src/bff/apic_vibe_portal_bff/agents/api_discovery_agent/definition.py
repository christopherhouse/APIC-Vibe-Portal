"""API Discovery Agent — definition, tools, and MAF wiring."""

from __future__ import annotations

import logging
import threading
import uuid
from collections.abc import Generator
from typing import Any

from apic_vibe_portal_bff.clients.ai_search_client import AISearchClient, AISearchClientError
from apic_vibe_portal_bff.clients.api_center_client import ApiCenterClient
from apic_vibe_portal_bff.models.chat import ChatMessage, ChatResponse, Citation
from apic_vibe_portal_bff.utils.logger import sanitize_for_log

from ..base_agent import BaseAgent
from ..types import AgentName, AgentRequest, AgentResponse
from .handler import extract_citations_from_results
from .prompts import SYSTEM_PROMPT

logger = logging.getLogger(__name__)

_RAG_TOP_K = 5
_SPEC_MAX_CHARS = 4000
_CITATION_EXCERPT_LENGTH = 200


class SecurityTrimmingMiddleware:
    """MAF ``FunctionMiddleware`` that enforces per-request ``accessible_api_ids`` security
    trimming on API Center tool calls.

    ``accessible_api_ids`` is read from ``context.kwargs``, which is populated
    by passing ``function_invocation_kwargs={"accessible_api_ids": ...}`` to
    :meth:`agent_framework.Agent.run`.

    - ``None`` → admin bypass; all tool calls are permitted.
    - Empty list → caller has no accessible APIs; all API Center calls are blocked.
    - Non-empty list → only calls targeting APIs in the list are permitted.

    The ``search_apis`` tool is not intercepted here because it enforces its own
    OData security filter via the per-request thread-local context set before
    :meth:`agent_framework.Agent.run` is invoked.
    """

    _API_CENTER_TOOLS: frozenset[str] = frozenset({"get_api_details", "get_api_spec", "list_api_versions"})

    async def process(self, context: Any, call_next: Any) -> None:
        """Intercept an API Center tool call and enforce the access list."""
        accessible_api_ids: list[str] | None = context.kwargs.get("accessible_api_ids", None)

        # None = admin bypass: all tool calls are permitted
        if accessible_api_ids is None:
            await call_next()
            return

        if context.function.name in self._API_CENTER_TOOLS:
            # Resolve api_id from arguments (supports both Pydantic model and dict)
            args = context.arguments
            api_id: str = (
                getattr(args, "api_id", None) or (args.get("api_id") if isinstance(args, dict) else None) or ""
            )
            if api_id and api_id not in accessible_api_ids:
                from agent_framework import MiddlewareTermination

                raise MiddlewareTermination(result=f"Access denied: API '{api_id}' is not in your permitted API list.")

        await call_next()


class ApiDiscoveryAgent(BaseAgent):
    """Agent specialised in API catalog discovery and navigation.

    Uses Microsoft Agent Framework (MAF) for tool-calling orchestration.
    Four tools are exposed to the LLM:

    - ``search_apis`` — full-text + semantic search over the AI Search index
    - ``get_api_details`` — metadata, deployments, and contacts from API Center
    - ``get_api_spec`` — export raw spec content for a given version
    - ``list_api_versions`` — enumerate versions registered for an API

    Security trimming is enforced at two levels:

    1. **``search_apis`` tool** — reads ``accessible_api_ids`` from a per-request
       thread-local and injects an OData ``search.in`` filter before forwarding to
       Azure AI Search.
    2. **API Center tools** — :class:`SecurityTrimmingMiddleware` intercepts calls
       and blocks any request for an ``api_id`` not in ``accessible_api_ids``.

    Both mechanisms treat ``None`` as an admin bypass (no filtering).

    Parameters
    ----------
    maf_client:
        MAF ``OpenAIChatClient`` instance.
    search_client:
        :class:`~apic_vibe_portal_bff.clients.ai_search_client.AISearchClient` for catalog search.
    api_center_client:
        :class:`~apic_vibe_portal_bff.clients.api_center_client.ApiCenterClient` for detail/spec retrieval.
    history_provider:
        Optional MAF ``HistoryProvider`` for conversation persistence.
    model:
        Model name used for token estimation.
    """

    def __init__(
        self,
        maf_client: Any,
        search_client: AISearchClient,
        api_center_client: ApiCenterClient,
        history_provider: Any | None = None,
        model: str = "gpt-4o",
    ) -> None:
        self._maf_client = maf_client
        self._search = search_client
        self._api_center = api_center_client
        self._model = model
        self._history_provider = history_provider
        # Per-request thread-local storage — carries accessible_api_ids and
        # captures search results for citation building without an extra search call.
        self._request_context: threading.local = threading.local()
        self._agent = self._create_agent()

    # ------------------------------------------------------------------
    # BaseAgent interface
    # ------------------------------------------------------------------

    @property
    def name(self) -> AgentName:
        return AgentName.API_DISCOVERY

    @property
    def description(self) -> str:
        return "Helps developers find, understand, and use APIs from the catalog."

    # ------------------------------------------------------------------
    # Tool factories
    # ------------------------------------------------------------------

    def _make_search_tool(self) -> Any:
        """Create the ``search_apis`` MAF tool.

        The tool closes over ``self`` (as ``agent_self``) so it can read the
        per-request ``accessible_api_ids`` from the thread-local context and
        capture search results for later citation building.
        """
        from agent_framework import tool

        agent_self = self

        @tool(
            name="search_apis",
            description=(
                "Search the enterprise API catalog for APIs matching a natural-language query. "
                "Returns API names, descriptions, kinds, and lifecycle stages. "
                "Always call this before answering questions about available APIs or capabilities."
            ),
        )
        def search_apis(query: str, filters: str = "") -> str:
            """Search the API catalog.

            Parameters
            ----------
            query:
                Natural-language search query describing the required capability.
            filters:
                Optional OData-style filter expression (e.g. ``kind eq 'REST'``).
            """
            # --- Security trimming ---
            accessible_api_ids: list[str] | None = getattr(agent_self._request_context, "accessible_api_ids", None)
            security_filter: str | None = None
            if accessible_api_ids is not None:
                if not accessible_api_ids:
                    return "No APIs are accessible for your account."
                ids_csv = ",".join(accessible_api_ids)
                security_filter = f"search.in(apiName, '{ids_csv}', ',')"

            # Merge server-side security filter with any model-provided filter
            user_filter = filters.strip() or None
            if security_filter and user_filter:
                filter_expression: str | None = f"({security_filter}) and ({user_filter})"
            else:
                filter_expression = security_filter or user_filter

            try:
                raw = agent_self._search.search(
                    search_text=query,
                    top=_RAG_TOP_K,
                    query_type="semantic",
                    semantic_query=query,
                    filter_expression=filter_expression,
                )
                results = raw.get("results", [])
            except AISearchClientError:
                logger.warning("search_apis tool: AI Search unavailable")
                return "Search is currently unavailable. Please try again later."

            if not results:
                return "No APIs found matching your query."

            # Capture results so run() can build citations without a second search call
            agent_self._request_context.last_search_results = results

            lines: list[str] = []
            for r in results:
                api_name = r.get("apiName", "Unknown")
                title = r.get("title", "")
                kind = r.get("kind", "")
                lifecycle = r.get("lifecycleStage", "")
                desc = r.get("description", "")
                lines.append(f"## {api_name}: {title}\n- Kind: {kind}\n- Lifecycle: {lifecycle}\n- Description: {desc}")

            return "\n\n".join(lines)

        return search_apis

    def _make_get_api_details_tool(self) -> Any:
        """Create the ``get_api_details`` MAF tool."""
        from agent_framework import tool

        agent_self = self

        @tool(
            name="get_api_details",
            description=(
                "Get detailed information about a specific API including metadata, "
                "deployments, and contact information. Use the API name/ID as returned "
                "by search_apis."
            ),
        )
        def get_api_details(api_id: str) -> str:
            """Get full details for a specific API.

            Parameters
            ----------
            api_id:
                The API name/ID from the catalog (e.g. ``'weather-api'``).
            """
            try:
                api = agent_self._api_center.get_api(api_id)
            except Exception as exc:
                logger.warning(
                    "get_api_details: failed to retrieve %s — %s",
                    sanitize_for_log(api_id),
                    exc,
                )
                return f"Could not retrieve details for API '{api_id}'. It may not exist in the catalog."

            title = api.get("title", api.get("name", api_id))
            name = api.get("name", api_id)
            kind = api.get("kind", "Unknown")
            lifecycle = api.get("lifecycleStage", "Unknown")
            description = api.get("description", "No description available.")
            contacts = api.get("contacts", [])
            contact_str = (
                ", ".join(f"{c.get('name', '')} ({c.get('email', '')})" for c in contacts if c) or "Not specified"
            )

            parts = [
                f"## {title} ({name})",
                f"- **Kind**: {kind}",
                f"- **Lifecycle Stage**: {lifecycle}",
                f"- **Description**: {description}",
                f"- **Contact**: {contact_str}",
            ]

            # Add deployments when available
            try:
                deployments = agent_self._api_center.list_deployments(api_id)
                if deployments:
                    parts.append("\n### Deployments")
                    for dep in deployments:
                        dep_name = dep.get("name", "unnamed")
                        server = dep.get("server", {})
                        runtime_uris = server.get("runtimeUri", []) if server else []
                        url = runtime_uris[0] if runtime_uris else ""
                        parts.append(f"- **{dep_name}**: {url}")
            except Exception:
                pass  # Deployments are optional metadata

            return "\n".join(parts)

        return get_api_details

    def _make_get_api_spec_tool(self) -> Any:
        """Create the ``get_api_spec`` MAF tool."""
        from agent_framework import tool

        agent_self = self

        @tool(
            name="get_api_spec",
            description=(
                "Retrieve the API specification document (OpenAPI, WSDL, etc.) for a specific "
                "API version. Use this to answer questions about endpoints, request/response "
                "schemas, and authentication. Call list_api_versions first to find valid version IDs."
            ),
        )
        def get_api_spec(api_id: str, version_id: str = "") -> str:
            """Get the API specification document.

            Parameters
            ----------
            api_id:
                The API name/ID (e.g. ``'payments-api'``).
            version_id:
                The version name (e.g. ``'v1'``). If empty, the first available version is used.
            """
            try:
                versions = agent_self._api_center.list_api_versions(api_id)
            except Exception as exc:
                logger.warning("get_api_spec: failed to list versions for %s — %s", sanitize_for_log(api_id), exc)
                return f"Could not retrieve versions for API '{api_id}'."

            if not versions:
                return f"No versions found for API '{api_id}'."

            # Select version
            if version_id:
                selected = next((v for v in versions if v.get("name") == version_id), None)
                if selected is None:
                    return f"Version '{version_id}' not found for API '{api_id}'."
            else:
                selected = versions[0]

            actual_version = selected.get("name", "")
            try:
                definitions = agent_self._api_center.list_api_definitions(api_id, actual_version)
            except Exception as exc:
                logger.warning("get_api_spec: failed to list definitions — %s", exc)
                return f"Could not retrieve definitions for '{api_id}' version '{actual_version}'."

            if not definitions:
                return f"No specification documents found for '{api_id}' version '{actual_version}'."

            definition_name = definitions[0].get("name", "openapi")
            try:
                spec_content = agent_self._api_center.export_api_specification(api_id, actual_version, definition_name)
            except Exception as exc:
                logger.warning("get_api_spec: export failed — %s", exc)
                return f"Could not export specification for '{api_id}'."

            if not spec_content:
                return f"Specification is empty for '{api_id}' version '{actual_version}'."

            truncated = ""
            if len(spec_content) > _SPEC_MAX_CHARS:
                spec_content = spec_content[:_SPEC_MAX_CHARS]
                truncated = "\n\n... [truncated — the full specification is longer than the display limit]"

            # Use actual_version as-is (it already contains the version string, e.g. "v1")
            return f"# {api_id} {actual_version} Specification\n\n```\n{spec_content}\n```{truncated}"

        return get_api_spec

    def _make_list_api_versions_tool(self) -> Any:
        """Create the ``list_api_versions`` MAF tool."""
        from agent_framework import tool

        agent_self = self

        @tool(
            name="list_api_versions",
            description=(
                "List all available versions of a specific API. "
                "Call this before get_api_spec to find the correct version ID."
            ),
        )
        def list_api_versions(api_id: str) -> str:
            """List available versions for an API.

            Parameters
            ----------
            api_id:
                The API name/ID (e.g. ``'payments-api'``).
            """
            try:
                versions = agent_self._api_center.list_api_versions(api_id)
            except Exception as exc:
                logger.warning("list_api_versions: failed — %s", exc)
                return f"Could not retrieve versions for API '{api_id}'."

            if not versions:
                return f"No versions found for API '{api_id}'."

            lines = [f"## Versions for {api_id}"]
            for v in versions:
                v_name = v.get("name", "unknown")
                lifecycle = v.get("lifecycleStage", "")
                lines.append(f"- **{v_name}** (lifecycle: {lifecycle})")

            return "\n".join(lines)

        return list_api_versions

    # ------------------------------------------------------------------
    # MAF Agent construction
    # ------------------------------------------------------------------

    def _create_agent(self) -> Any:
        """Create the MAF :class:`~agent_framework.Agent` wired with all four tools.

        :class:`SecurityTrimmingMiddleware` is registered as agent-level middleware
        so it applies to every tool call without per-call setup.
        """
        from agent_framework import Agent

        tools = [
            self._make_search_tool(),
            self._make_get_api_details_tool(),
            self._make_get_api_spec_tool(),
            self._make_list_api_versions_tool(),
        ]

        context_providers = []
        if self._history_provider is not None:
            context_providers.append(self._history_provider)

        return Agent(
            client=self._maf_client,
            instructions=SYSTEM_PROMPT,
            tools=tools,
            context_providers=context_providers,
            middleware=[SecurityTrimmingMiddleware()],
            name="API Discovery Agent",
            description=self.description,
        )

    # ------------------------------------------------------------------
    # Run / Stream
    # ------------------------------------------------------------------

    def run(self, request: AgentRequest) -> AgentResponse:
        """Process a request through the MAF Agent and return a response.

        Per-request security context is set on a thread-local before the MAF
        ``Agent.run()`` call and cleaned up in a ``finally`` block so that
        concurrent requests on different threads never bleed into each other.

        Security trimming is enforced at two layers:

        1. The ``search_apis`` tool reads ``accessible_api_ids`` from the
           thread-local and injects an OData security filter.
        2. :class:`SecurityTrimmingMiddleware` (registered on the MAF agent)
           receives ``accessible_api_ids`` via ``function_invocation_kwargs``
           and blocks API Center tool calls for non-permitted APIs.
        """
        from agent_framework import AgentSession

        # Generate the session ID once so both the MAF call and the
        # returned AgentResponse use the same value.
        effective_session_id = request.session_id or str(uuid.uuid4())

        # Initialise thread-local request context
        self._request_context.accessible_api_ids = request.accessible_api_ids
        self._request_context.last_search_results = []

        try:
            response = self._agent.run(
                messages=request.message,
                session=AgentSession(session_id=effective_session_id),
                function_invocation_kwargs={"accessible_api_ids": request.accessible_api_ids},
            )
            # MAF Agent.run() returns Awaitable in production; MagicMock in tests
            # returns the configured return_value directly.
            response_text: str = getattr(response, "text", None) or (
                str(response) if not hasattr(response, "__await__") else ""
            )
        finally:
            # Capture what the search_apis tool stored (if it ran)
            last_search_results = list(getattr(self._request_context, "last_search_results", []))
            # Clean up thread-local so the slot doesn't leak between requests
            try:
                del self._request_context.accessible_api_ids
                del self._request_context.last_search_results
            except AttributeError:
                pass

        # Build citations from tool-captured results to avoid a redundant search call.
        # If search_apis was not invoked during this run, no citations are produced.
        citations: list[Citation] = (
            extract_citations_from_results(last_search_results, excerpt_length=_CITATION_EXCERPT_LENGTH)
            if last_search_results
            else []
        )

        return AgentResponse(
            agent_name=self.name,
            content=response_text,
            session_id=effective_session_id,
            citations=citations or None,
        )

    def stream(self, request: AgentRequest) -> Generator[str]:
        """Stream the agent response as text chunks.

        Delegates to :meth:`run` and yields the full response as a single chunk.
        Token-level streaming is not currently supported because MAF's ``Agent.run()``
        returns a complete response.  When MAF adds a ``run_stream()`` API, this method
        should be updated to yield individual tokens for progressive user feedback.
        """
        response = self.run(request)
        if response.content:
            yield response.content

    # ------------------------------------------------------------------
    # Convenience: build ChatResponse from AgentResponse
    # ------------------------------------------------------------------

    def to_chat_response(self, agent_response: AgentResponse) -> ChatResponse:
        """Convert an :class:`AgentResponse` into a :class:`ChatResponse`.

        Used when the agent response needs to be returned through the
        existing ``/api/chat`` endpoint format.
        """
        from datetime import UTC, datetime

        now = datetime.now(UTC).isoformat().replace("+00:00", "Z")
        return ChatResponse(
            sessionId=agent_response.session_id,
            message=ChatMessage(
                id=str(uuid.uuid4()),
                role="assistant",
                content=agent_response.content,
                citations=agent_response.citations,
                timestamp=now,
            ),
        )
