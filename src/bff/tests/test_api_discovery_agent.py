"""Tests for the API Discovery Agent and its tools."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from apic_vibe_portal_bff.agents.api_discovery_agent.definition import ApiDiscoveryAgent
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
    mock_maf_agent.run.return_value = "Here are the APIs you requested."

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
    def test_run_returns_agent_response(self, agent):
        request = AgentRequest(message="Find me payment APIs", session_id="sess-1")
        response = agent.run(request)
        assert isinstance(response, AgentResponse)
        assert response.agent_name == AgentName.API_DISCOVERY

    def test_run_uses_maf_agent(self, agent):
        request = AgentRequest(message="What APIs do you have?", session_id="sess-1")
        agent.run(request)
        agent._agent.run.assert_called_once_with(message="What APIs do you have?", session_id="sess-1")

    def test_run_generates_session_id_when_none(self, agent):
        request = AgentRequest(message="Hello", session_id=None)
        response = agent.run(request)
        assert response.session_id  # non-empty

    def test_run_includes_citations(self, agent):
        request = AgentRequest(message="weather API", session_id="sess-1")
        response = agent.run(request)
        # Citations extracted from mock search results
        assert response.citations is not None
        titles = [c.title for c in response.citations]
        assert any("weather-api" in t for t in titles)

    def test_run_empty_accessible_ids_returns_no_citations(self, agent):
        request = AgentRequest(message="APIs", session_id="sess-1", accessible_api_ids=[])
        response = agent.run(request)
        assert response.citations is None or len(response.citations) == 0


# ---------------------------------------------------------------------------
# Stream tests
# ---------------------------------------------------------------------------


class TestApiDiscoveryAgentStream:
    def test_stream_yields_content(self, agent):
        request = AgentRequest(message="Find APIs", session_id="sess-1")
        chunks = list(agent.stream(request))
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

    def test_search_apis_passes_filter(self, agent, mock_search):
        tool_fn = agent._make_search_tool()
        tool_fn(query="test", filters="kind eq 'REST'")
        call_kwargs = mock_search.search.call_args
        assert call_kwargs.kwargs.get("filter_expression") == "kind eq 'REST'"


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
