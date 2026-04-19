"""API Discovery Agent — definition, tools, and MAF wiring."""

from __future__ import annotations

import logging
import uuid
from collections.abc import Generator
from typing import Any

from apic_vibe_portal_bff.clients.ai_search_client import AISearchClient, AISearchClientError
from apic_vibe_portal_bff.clients.api_center_client import ApiCenterClient
from apic_vibe_portal_bff.models.chat import ChatMessage, ChatResponse, Citation
from apic_vibe_portal_bff.utils.logger import sanitize_for_log

from ..base_agent import BaseAgent
from ..types import AgentName, AgentRequest, AgentResponse
from .prompts import SYSTEM_PROMPT

logger = logging.getLogger(__name__)

_RAG_TOP_K = 5
_SPEC_MAX_CHARS = 4000
_CITATION_EXCERPT_LENGTH = 200


class ApiDiscoveryAgent(BaseAgent):
    """Agent specialised in API catalog discovery and navigation.

    Uses Microsoft Agent Framework (MAF) for tool-calling orchestration.
    Four tools are exposed to the LLM:

    - ``search_apis`` — full-text + semantic search over the AI Search index
    - ``get_api_details`` — metadata, deployments, and contacts from API Center
    - ``get_api_spec`` — export raw spec content for a given version
    - ``list_api_versions`` — enumerate versions registered for an API

    Parameters
    ----------
    maf_client:
        MAF ``OpenAIChatClient`` instance (from
        :meth:`~apic_vibe_portal_bff.clients.foundry_agent_client.FoundryAgentClient.get_maf_client`
        or :meth:`~apic_vibe_portal_bff.clients.openai_client.OpenAIClient.get_maf_client`).
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
        """Create the ``search_apis`` MAF tool."""
        from agent_framework import tool

        search = self._search

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
            filter_expression = filters.strip() or None
            try:
                raw = search.search(
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

        api_center = self._api_center

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
                api = api_center.get_api(api_id)
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
                deployments = api_center.list_deployments(api_id)
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

        api_center = self._api_center

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
                versions = api_center.list_api_versions(api_id)
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
                definitions = api_center.list_api_definitions(api_id, actual_version)
            except Exception as exc:
                logger.warning("get_api_spec: failed to list definitions — %s", exc)
                return f"Could not retrieve definitions for '{api_id}' version '{actual_version}'."

            if not definitions:
                return f"No specification documents found for '{api_id}' version '{actual_version}'."

            definition_name = definitions[0].get("name", "openapi")
            try:
                spec_content = api_center.export_api_specification(api_id, actual_version, definition_name)
            except Exception as exc:
                logger.warning("get_api_spec: export failed — %s", exc)
                return f"Could not export specification for '{api_id}'."

            if not spec_content:
                return f"Specification is empty for '{api_id}' version '{actual_version}'."

            truncated = ""
            if len(spec_content) > _SPEC_MAX_CHARS:
                spec_content = spec_content[:_SPEC_MAX_CHARS]
                truncated = "\n\n... [truncated — request a specific section for more detail]"

            return f"# {api_id} v{actual_version} Specification\n\n```\n{spec_content}\n```{truncated}"

        return get_api_spec

    def _make_list_api_versions_tool(self) -> Any:
        """Create the ``list_api_versions`` MAF tool."""
        from agent_framework import tool

        api_center = self._api_center

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
                versions = api_center.list_api_versions(api_id)
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
        """Create the MAF :class:`~agent_framework.Agent` wired with all four tools."""
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
            name="API Discovery Agent",
            description=self.description,
        )

    # ------------------------------------------------------------------
    # Run / Stream
    # ------------------------------------------------------------------

    def run(self, request: AgentRequest) -> AgentResponse:
        """Process a request through the MAF Agent and return a response.

        The MAF Agent handles tool-calling automatically: when the LLM decides
        to call one of the registered tools, MAF executes it and feeds the
        result back before generating the final answer.
        """
        response_text = self._agent.run(
            message=request.message,
            session_id=request.session_id or "",
        )

        citations = self._extract_citations(request.message, request.accessible_api_ids)

        return AgentResponse(
            agent_name=self.name,
            content=response_text or "",
            session_id=request.session_id or str(uuid.uuid4()),
            citations=citations or None,
        )

    def stream(self, request: AgentRequest) -> Generator[str]:
        """Stream the agent response as text chunks.

        Delegates to :meth:`run` and yields the full response as a single
        chunk.  Fine-grained streaming is handled at the chat service layer.
        """
        response = self.run(request)
        if response.content:
            yield response.content

    # ------------------------------------------------------------------
    # Citation extraction
    # ------------------------------------------------------------------

    def _extract_citations(
        self,
        query: str,
        accessible_api_ids: list[str] | None,
    ) -> list[Citation]:
        """Search the catalog for *query* and build citation objects.

        The same security-trimming filter used by the chat service is applied
        so citations only reference APIs the current user can access.
        """
        security_filter: str | None = None
        if accessible_api_ids is not None:
            if not accessible_api_ids:
                return []
            ids_csv = ",".join(accessible_api_ids)
            security_filter = f"search.in(apiName, '{ids_csv}', ',')"

        try:
            raw = self._search.search(
                search_text=query,
                top=_RAG_TOP_K,
                query_type="semantic",
                semantic_query=query,
                filter_expression=security_filter,
            )
            results = raw.get("results", [])
        except AISearchClientError:
            logger.warning("ApiDiscoveryAgent: citation extraction search failed")
            return []

        citations: list[Citation] = []
        for result in results:
            api_name = result.get("apiName", "")
            if not api_name:
                continue
            title = result.get("title", "")
            description = result.get("description", "")
            citations.append(
                Citation(
                    title=f"{api_name}: {title}" if title else api_name,
                    url=f"/api/catalog/{api_name}",
                    content=description[:_CITATION_EXCERPT_LENGTH] if description else None,
                )
            )

        return citations

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
