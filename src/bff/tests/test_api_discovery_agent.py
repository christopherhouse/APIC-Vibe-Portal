"""Tests for the API Discovery Agent and its tools."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
import pytest_asyncio  # noqa: F401 — registers asyncio mode

from apic_vibe_portal_bff.agents.api_discovery_agent.definition import ApiDiscoveryAgent, SecurityTrimmingMiddleware
from apic_vibe_portal_bff.agents.api_discovery_agent.handler import (
    build_chat_response,
    extract_citations_from_results,
    format_search_result,
)
from apic_vibe_portal_bff.agents.api_discovery_agent.prompts import FEW_SHOT_EXAMPLES, SYSTEM_PROMPT
from apic_vibe_portal_bff.agents.types import AgentName, AgentRequest, AgentResponse
from apic_vibe_portal_bff.models.chat import Citation

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def mock_maf_client():
    return MagicMock()


@pytest.fixture
def mock_search():
    client = MagicMock()
    client.search.return_value = {
        "results": [
            {
                "apiName": "weather-api",
                "title": "Weather API",
                "description": "Real-time weather data.",
                "kind": "REST",
                "lifecycleStage": "Production",
            },
            {
                "apiName": "maps-api",
                "title": "Maps API",
                "description": "Geocoding and mapping services.",
                "kind": "REST",
                "lifecycleStage": "Beta",
            },
        ],
        "count": 2,
        "facets": None,
    }
    return client


@pytest.fixture
def mock_api_center():
    client = MagicMock()
    client.get_api.return_value = {
        "name": "weather-api",
        "title": "Weather API",
        "kind": "REST",
        "lifecycleStage": "Production",
        "description": "Provides real-time weather data.",
        "contacts": [{"name": "Weather Team", "email": "weather@example.com"}],
    }
    client.list_api_versions.return_value = [
        {"name": "v1", "lifecycleStage": "Production"},
        {"name": "v2", "lifecycleStage": "Preview"},
    ]
    client.list_api_definitions.return_value = [{"name": "openapi"}]
    client.export_api_specification.return_value = '{"openapi": "3.0.0", "info": {"title": "Weather API"}}'
    client.list_deployments.return_value = [
        {"name": "prod", "server": {"runtimeUri": ["https://api.example.com/weather"]}}
    ]
    return client


@pytest.fixture
def agent(mock_maf_client, mock_search, mock_api_center):
    """Return an ApiDiscoveryAgent with a mock MAF agent that returns a fixed response."""
    mock_maf_agent = MagicMock()
    # Agent.run() is awaited, so the mock must return a coroutine
    mock_maf_agent.run = AsyncMock(return_value="Here are the APIs you requested.")

    with patch("agent_framework.Agent", return_value=mock_maf_agent):
        a = ApiDiscoveryAgent(
            maf_client=mock_maf_client,
            search_client=mock_search,
            api_center_client=mock_api_center,
            model="gpt-4o",
        )
        a._agent = mock_maf_agent
        return a


# ---------------------------------------------------------------------------
# ApiDiscoveryAgent identity tests
# ---------------------------------------------------------------------------


class TestApiDiscoveryAgentIdentity:
    def test_name(self, agent):
        assert agent.name == AgentName.API_DISCOVERY

    def test_description(self, agent):
        assert "API" in agent.description


# ---------------------------------------------------------------------------
# Run tests
# ---------------------------------------------------------------------------


class TestApiDiscoveryAgentRun:
    @pytest.mark.asyncio
    async def test_run_returns_agent_response(self, agent):
        request = AgentRequest(message="Find me payment APIs", session_id="sess-1")
        response = await agent.run(request)
        assert isinstance(response, AgentResponse)
        assert response.agent_name == AgentName.API_DISCOVERY

    @pytest.mark.asyncio
    async def test_run_uses_maf_agent(self, agent):
        request = AgentRequest(message="What APIs do you have?", session_id="sess-1")
        await agent.run(request)
        agent._agent.run.assert_called_once()
        call_kwargs = agent._agent.run.call_args
        assert call_kwargs.kwargs.get("messages") == "What APIs do you have?"

    @pytest.mark.asyncio
    async def test_run_session_id_is_consistent(self, agent):
        # Session ID is generated once and used for both MAF call and response.
        request = AgentRequest(message="Hello", session_id=None)
        response = await agent.run(request)
        assert response.session_id  # non-empty UUID
        # The same session ID must have been passed to Agent.run()
        call_kwargs = agent._agent.run.call_args
        session_arg = call_kwargs.kwargs.get("session")
        assert session_arg is not None
        assert session_arg.session_id == response.session_id

    @pytest.mark.asyncio
    async def test_run_preserves_explicit_session_id(self, agent):
        request = AgentRequest(message="Hello", session_id="my-session")
        response = await agent.run(request)
        assert response.session_id == "my-session"

    @pytest.mark.asyncio
    async def test_run_citations_from_tool_results(self, agent, mock_search):
        """Citations are built from search_apis tool results captured during agent run."""
        search_results = mock_search.search.return_value["results"]

        # Simulate search_apis tool being invoked during MAF agent.run()
        async def side_effect_run(**kwargs):
            agent._request_context.last_search_results = search_results
            return "Here are the APIs you requested."

        agent._agent.run.side_effect = side_effect_run

        request = AgentRequest(message="weather API", session_id="sess-1")
        response = await agent.run(request)

        # No extra search call — citations come from the tool-captured results
        mock_search.search.assert_not_called()
        assert response.citations is not None
        titles = [c.title for c in response.citations]
        assert any("weather-api" in t for t in titles)

    @pytest.mark.asyncio
    async def test_run_no_citations_when_search_tool_not_invoked(self, agent, mock_search):
        """When search_apis is not invoked, no extra search call and no citations."""
        request = AgentRequest(message="Hello", session_id="sess-1")
        # Do NOT populate last_search_results (tool was not called)
        response = await agent.run(request)
        # No search calls
        mock_search.search.assert_not_called()
        # No citations because search_apis was not invoked
        assert response.citations is None

    @pytest.mark.asyncio
    async def test_run_empty_accessible_ids_returns_no_citations(self, agent):
        request = AgentRequest(message="APIs", session_id="sess-1", accessible_api_ids=[])
        response = await agent.run(request)
        assert response.citations is None or len(response.citations) == 0

    @pytest.mark.asyncio
    async def test_run_passes_accessible_api_ids_to_maf(self, agent):
        """accessible_api_ids is forwarded to Agent.run() via function_invocation_kwargs."""
        request = AgentRequest(message="APIs", session_id="sess-1", accessible_api_ids=["api-a"])
        await agent.run(request)
        call_kwargs = agent._agent.run.call_args
        fik = call_kwargs.kwargs.get("function_invocation_kwargs")
        assert fik is not None
        assert fik.get("accessible_api_ids") == ["api-a"]

    @pytest.mark.asyncio
    async def test_run_thread_local_cleaned_up_after_run(self, agent):
        """Thread-local is cleared after run() so leaks between requests are impossible."""
        request = AgentRequest(message="Hello", session_id="sess-1", accessible_api_ids=["api-a"])
        await agent.run(request)
        assert not hasattr(agent._request_context, "accessible_api_ids")
        assert not hasattr(agent._request_context, "last_search_results")


# ---------------------------------------------------------------------------
# Stream tests
# ---------------------------------------------------------------------------


class TestApiDiscoveryAgentStream:
    @pytest.mark.asyncio
    async def test_stream_yields_content(self, agent):
        request = AgentRequest(message="Find APIs", session_id="sess-1")
        chunks = [chunk async for chunk in agent.stream(request)]
        assert len(chunks) > 0
        assert "".join(chunks) == "Here are the APIs you requested."


# ---------------------------------------------------------------------------
# Tool: search_apis
# ---------------------------------------------------------------------------


class TestSearchApisTool:
    def test_search_apis_returns_formatted_results(self, agent, mock_search):
        tool_fn = agent._make_search_tool()
        result = tool_fn(query="weather")
        assert "weather-api" in result
        assert "Weather API" in result

    def test_search_apis_no_results(self, agent, mock_search):
        mock_search.search.return_value = {"results": [], "count": 0, "facets": None}
        tool_fn = agent._make_search_tool()
        result = tool_fn(query="nonexistent")
        assert "No APIs found" in result

    def test_search_apis_search_failure(self, agent, mock_search):
        from apic_vibe_portal_bff.clients.ai_search_client import AISearchClientError

        mock_search.search.side_effect = AISearchClientError("Service down")
        tool_fn = agent._make_search_tool()
        result = tool_fn(query="anything")
        assert "unavailable" in result.lower() or "Search" in result

    def test_search_apis_passes_user_filter(self, agent, mock_search):
        tool_fn = agent._make_search_tool()
        tool_fn(query="test", filters="kind eq 'REST'")
        call_kwargs = mock_search.search.call_args
        assert call_kwargs.kwargs.get("filter_expression") == "kind eq 'REST'"

    def test_search_apis_injects_security_filter_when_accessible_ids_set(self, agent, mock_search):
        """When accessible_api_ids is set in the thread-local, an OData filter is injected."""
        agent._request_context.accessible_api_ids = ["weather-api", "maps-api"]
        tool_fn = agent._make_search_tool()
        tool_fn(query="test")
        call_kwargs = mock_search.search.call_args
        assert "search.in(apiName" in call_kwargs.kwargs.get("filter_expression", "")

    def test_search_apis_merges_security_and_user_filter(self, agent, mock_search):
        agent._request_context.accessible_api_ids = ["weather-api"]
        tool_fn = agent._make_search_tool()
        tool_fn(query="test", filters="kind eq 'REST'")
        call_kwargs = mock_search.search.call_args
        fe = call_kwargs.kwargs.get("filter_expression", "")
        assert "search.in(apiName" in fe
        assert "kind eq 'REST'" in fe

    def test_search_apis_blocks_when_accessible_ids_empty(self, agent, mock_search):
        agent._request_context.accessible_api_ids = []
        tool_fn = agent._make_search_tool()
        result = tool_fn(query="anything")
        assert "No APIs are accessible" in result
        mock_search.search.assert_not_called()

    def test_search_apis_no_filter_when_admin_bypass(self, agent, mock_search):
        """When accessible_api_ids is None (admin bypass), no security filter is injected."""
        agent._request_context.accessible_api_ids = None
        tool_fn = agent._make_search_tool()
        tool_fn(query="test")
        call_kwargs = mock_search.search.call_args
        assert call_kwargs.kwargs.get("filter_expression") is None

    def test_search_apis_captures_results_in_thread_local(self, agent, mock_search):
        """Results are stored in thread-local so run() can build citations without extra search."""
        tool_fn = agent._make_search_tool()
        tool_fn(query="weather")
        captured = getattr(agent._request_context, "last_search_results", [])
        assert len(captured) == 2
        assert captured[0]["apiName"] == "weather-api"


# ---------------------------------------------------------------------------
# Tool: get_api_details
# ---------------------------------------------------------------------------


class TestGetApiDetailsTool:
    def test_returns_api_info(self, agent, mock_api_center):
        tool_fn = agent._make_get_api_details_tool()
        result = tool_fn(api_id="weather-api")
        assert "Weather API" in result
        assert "REST" in result
        assert "Production" in result

    def test_returns_contact_info(self, agent, mock_api_center):
        tool_fn = agent._make_get_api_details_tool()
        result = tool_fn(api_id="weather-api")
        assert "Weather Team" in result

    def test_returns_deployment_info(self, agent, mock_api_center):
        tool_fn = agent._make_get_api_details_tool()
        result = tool_fn(api_id="weather-api")
        assert "prod" in result

    def test_handles_api_not_found(self, agent, mock_api_center):
        mock_api_center.get_api.side_effect = Exception("Not found")
        tool_fn = agent._make_get_api_details_tool()
        result = tool_fn(api_id="nonexistent-api")
        assert "nonexistent-api" in result
        assert "Could not retrieve" in result or "not exist" in result

    def test_handles_no_contacts(self, agent, mock_api_center):
        mock_api_center.get_api.return_value = {
            "name": "bare-api",
            "title": "Bare API",
            "kind": "REST",
            "lifecycleStage": "Production",
            "description": "Minimal.",
            "contacts": [],
        }
        tool_fn = agent._make_get_api_details_tool()
        result = tool_fn(api_id="bare-api")
        assert "Not specified" in result


# ---------------------------------------------------------------------------
# Tool: get_api_spec
# ---------------------------------------------------------------------------


class TestGetApiSpecTool:
    def test_returns_spec_content(self, agent, mock_api_center):
        tool_fn = agent._make_get_api_spec_tool()
        result = tool_fn(api_id="weather-api")
        assert "openapi" in result.lower()
        assert "weather-api" in result
        # Version should not be doubled (no "vv1")
        assert "vv" not in result

    def test_uses_specified_version(self, agent, mock_api_center):
        tool_fn = agent._make_get_api_spec_tool()
        tool_fn(api_id="weather-api", version_id="v1")
        mock_api_center.export_api_specification.assert_called_once_with("weather-api", "v1", "openapi")

    def test_falls_back_to_first_version_when_not_specified(self, agent, mock_api_center):
        tool_fn = agent._make_get_api_spec_tool()
        tool_fn(api_id="weather-api")
        # Should use v1 (first returned by list_api_versions)
        mock_api_center.export_api_specification.assert_called_once_with("weather-api", "v1", "openapi")

    def test_version_not_found(self, agent, mock_api_center):
        tool_fn = agent._make_get_api_spec_tool()
        result = tool_fn(api_id="weather-api", version_id="v99")
        assert "v99" in result
        assert "not found" in result.lower()

    def test_no_versions_returns_message(self, agent, mock_api_center):
        mock_api_center.list_api_versions.return_value = []
        tool_fn = agent._make_get_api_spec_tool()
        result = tool_fn(api_id="bare-api")
        assert "No versions found" in result

    def test_spec_truncated_when_too_long(self, agent, mock_api_center):
        mock_api_center.export_api_specification.return_value = "x" * 5000
        tool_fn = agent._make_get_api_spec_tool()
        result = tool_fn(api_id="weather-api")
        assert "truncated" in result

    def test_handles_export_failure(self, agent, mock_api_center):
        mock_api_center.export_api_specification.side_effect = Exception("Export failed")
        tool_fn = agent._make_get_api_spec_tool()
        result = tool_fn(api_id="weather-api")
        assert "Could not export" in result


# ---------------------------------------------------------------------------
# Tool: list_api_versions
# ---------------------------------------------------------------------------


class TestListApiVersionsTool:
    def test_returns_version_list(self, agent, mock_api_center):
        tool_fn = agent._make_list_api_versions_tool()
        result = tool_fn(api_id="weather-api")
        assert "v1" in result
        assert "v2" in result

    def test_includes_lifecycle(self, agent, mock_api_center):
        tool_fn = agent._make_list_api_versions_tool()
        result = tool_fn(api_id="weather-api")
        assert "Production" in result or "Preview" in result

    def test_no_versions(self, agent, mock_api_center):
        mock_api_center.list_api_versions.return_value = []
        tool_fn = agent._make_list_api_versions_tool()
        result = tool_fn(api_id="empty-api")
        assert "No versions found" in result

    def test_handles_exception(self, agent, mock_api_center):
        mock_api_center.list_api_versions.side_effect = Exception("API Center down")
        tool_fn = agent._make_list_api_versions_tool()
        result = tool_fn(api_id="broken-api")
        assert "Could not retrieve" in result


# ---------------------------------------------------------------------------
# Handler helper tests
# ---------------------------------------------------------------------------


class TestHandlerHelpers:
    def test_format_search_result(self):
        result = {
            "apiName": "test-api",
            "title": "Test API",
            "kind": "REST",
            "lifecycleStage": "Production",
            "description": "A test API.",
        }
        formatted = format_search_result(result)
        assert "test-api" in formatted
        assert "Test API" in formatted
        assert "REST" in formatted

    def test_extract_citations_from_results(self):
        results = [
            {"apiName": "api-a", "title": "API A", "description": "First API."},
            {"apiName": "api-b", "title": "API B", "description": "Second API."},
        ]
        citations = extract_citations_from_results(results)
        assert len(citations) == 2
        assert citations[0].title == "api-a: API A"
        assert citations[0].url == "/api/catalog/api-a"

    def test_extract_citations_skips_missing_api_name(self):
        results = [
            {"apiName": "", "title": "No Name", "description": "desc"},
            {"title": "Also No Name"},
        ]
        citations = extract_citations_from_results(results)
        assert len(citations) == 0

    def test_extract_citations_excerpt_truncated(self):
        results = [{"apiName": "api", "title": "T", "description": "x" * 500}]
        citations = extract_citations_from_results(results, excerpt_length=50)
        assert len(citations[0].content) == 50

    def test_build_chat_response(self):
        resp = build_chat_response("sess-1", "Hello world")
        assert resp.session_id == "sess-1"
        assert resp.message.content == "Hello world"
        assert resp.message.role == "assistant"
        assert resp.message.id  # non-empty UUID

    def test_build_chat_response_with_citations(self):
        citations = [Citation(title="API X", url="/api/catalog/api-x")]
        resp = build_chat_response("sess-1", "Here are APIs", citations=citations)
        assert resp.message.citations is not None
        assert resp.message.citations[0].title == "API X"


# ---------------------------------------------------------------------------
# Prompts tests
# ---------------------------------------------------------------------------


class TestPrompts:
    def test_system_prompt_not_empty(self):
        assert len(SYSTEM_PROMPT) > 100

    def test_system_prompt_mentions_tools(self):
        assert "search_apis" in SYSTEM_PROMPT
        assert "get_api_details" in SYSTEM_PROMPT
        assert "get_api_spec" in SYSTEM_PROMPT
        assert "list_api_versions" in SYSTEM_PROMPT

    def test_few_shot_examples_have_user_and_assistant(self):
        roles = {ex["role"] for ex in FEW_SHOT_EXAMPLES}
        assert "user" in roles
        assert "assistant" in roles


# ---------------------------------------------------------------------------
# to_chat_response helper
# ---------------------------------------------------------------------------


class TestToChatResponse:
    def test_converts_agent_response_to_chat_response(self, agent):
        agent_resp = AgentResponse(
            agent_name=AgentName.API_DISCOVERY,
            content="Here are APIs",
            session_id="sess-42",
            citations=[Citation(title="API A", url="/api/catalog/api-a")],
        )
        chat_resp = agent.to_chat_response(agent_resp)
        assert chat_resp.session_id == "sess-42"
        assert chat_resp.message.content == "Here are APIs"
        assert chat_resp.message.role == "assistant"
        assert chat_resp.message.citations is not None


# ---------------------------------------------------------------------------
# SecurityTrimmingMiddleware tests
# ---------------------------------------------------------------------------


def _make_middleware_context(tool_name: str, args: dict | None = None, accessible_api_ids: list | None = None):
    """Build a minimal FunctionInvocationContext-like object for middleware tests."""
    context = MagicMock()
    context.function.name = tool_name
    context.arguments = args or {}
    context.kwargs = {"accessible_api_ids": accessible_api_ids}
    context.result = None
    return context


class TestSecurityTrimmingMiddleware:
    """Unit tests for SecurityTrimmingMiddleware using pytest-asyncio."""

    @pytest.mark.asyncio
    async def test_admin_bypass_allows_all_tools(self):
        """When accessible_api_ids is None, all tool calls are permitted."""
        middleware = SecurityTrimmingMiddleware()

        for tool_name in ("search_apis", "get_api_details", "get_api_spec", "list_api_versions"):
            called: list[bool] = []
            ctx = _make_middleware_context(tool_name, {"api_id": "secret-api"}, accessible_api_ids=None)

            async def call_next(tracker=called):
                tracker.append(True)

            await middleware.process(ctx, call_next)
            assert called, f"call_next not invoked for {tool_name}"

    @pytest.mark.asyncio
    async def test_permitted_api_center_call_proceeds(self):
        middleware = SecurityTrimmingMiddleware()
        called: list[bool] = []

        async def call_next():
            called.append(True)

        context = _make_middleware_context("get_api_details", {"api_id": "weather-api"}, ["weather-api", "maps-api"])
        await middleware.process(context, call_next)
        assert called

    @pytest.mark.asyncio
    async def test_blocked_api_center_call_raises_termination(self):
        """API Center calls for non-permitted api_id raise MiddlewareTermination."""
        from agent_framework import MiddlewareTermination

        middleware = SecurityTrimmingMiddleware()

        async def call_next():
            pass

        for tool_name in ("get_api_details", "get_api_spec", "list_api_versions"):
            ctx = _make_middleware_context(tool_name, {"api_id": "forbidden-api"}, ["weather-api"])
            with pytest.raises(MiddlewareTermination):
                await middleware.process(ctx, call_next)

    @pytest.mark.asyncio
    async def test_empty_accessible_ids_blocks_all_api_center_tools(self):
        """Empty accessible_api_ids list blocks every API Center call."""
        from agent_framework import MiddlewareTermination

        middleware = SecurityTrimmingMiddleware()

        async def call_next():
            pass

        context = _make_middleware_context("get_api_details", {"api_id": "any-api"}, accessible_api_ids=[])
        with pytest.raises(MiddlewareTermination):
            await middleware.process(context, call_next)

    @pytest.mark.asyncio
    async def test_search_apis_not_blocked_by_middleware(self):
        """search_apis handles its own security trimming; middleware does not block it."""
        middleware = SecurityTrimmingMiddleware()
        called: list[bool] = []

        async def call_next():
            called.append(True)

        context = _make_middleware_context("search_apis", {}, accessible_api_ids=["api-a"])
        await middleware.process(context, call_next)
        assert called

    @pytest.mark.asyncio
    async def test_middleware_reads_api_id_from_pydantic_model(self):
        """api_id is also resolved from Pydantic-like objects (via getattr)."""
        from agent_framework import MiddlewareTermination

        middleware = SecurityTrimmingMiddleware()

        async def call_next():
            pass

        args = MagicMock()
        args.api_id = "forbidden-api"
        context = _make_middleware_context("get_api_details", args, accessible_api_ids=["permitted-api"])
        with pytest.raises(MiddlewareTermination):
            await middleware.process(context, call_next)
