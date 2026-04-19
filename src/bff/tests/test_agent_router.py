"""Tests for the AgentRegistry and AgentRouter."""

from __future__ import annotations

from collections.abc import AsyncGenerator

import pytest

from apic_vibe_portal_bff.agents.agent_registry import AgentRegistry
from apic_vibe_portal_bff.agents.agent_router import AgentRouter, _is_governance_intent
from apic_vibe_portal_bff.agents.base_agent import BaseAgent
from apic_vibe_portal_bff.agents.types import AgentName, AgentRequest, AgentResponse
from apic_vibe_portal_bff.models.chat import Citation

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_agent(name: AgentName = AgentName.API_DISCOVERY, content: str = "Agent response") -> BaseAgent:
    """Create a minimal concrete BaseAgent for testing."""

    class _StubAgent(BaseAgent):
        @property
        def name(self) -> AgentName:
            return name

        @property
        def description(self) -> str:
            return "Stub agent"

        async def run(self, request: AgentRequest) -> AgentResponse:
            return AgentResponse(
                agent_name=name,
                content=content,
                session_id=request.session_id or "new-session",
                citations=[Citation(title="Test API", url="/api/catalog/test-api")],
            )

        async def stream(self, request: AgentRequest) -> AsyncGenerator[str]:
            yield content

    return _StubAgent()


def _make_request(message: str = "Hello", session_id: str | None = None) -> AgentRequest:
    return AgentRequest(message=message, session_id=session_id)


# ---------------------------------------------------------------------------
# AgentRegistry tests
# ---------------------------------------------------------------------------


class TestAgentRegistry:
    def test_empty_registry_returns_none(self):
        registry = AgentRegistry()
        assert registry.get(AgentName.API_DISCOVERY) is None

    def test_register_and_retrieve(self):
        registry = AgentRegistry()
        agent = _make_agent()
        registry.register(agent)
        assert registry.get(AgentName.API_DISCOVERY) is agent

    def test_register_replaces_existing(self):
        registry = AgentRegistry()
        agent1 = _make_agent(content="first")
        agent2 = _make_agent(content="second")
        registry.register(agent1)
        registry.register(agent2)
        assert registry.get(AgentName.API_DISCOVERY) is agent2

    def test_list_names_empty(self):
        registry = AgentRegistry()
        assert registry.list_names() == []

    def test_list_names_after_register(self):
        registry = AgentRegistry()
        agent = _make_agent()
        registry.register(agent)
        assert AgentName.API_DISCOVERY in registry.list_names()

    def test_len_empty(self):
        registry = AgentRegistry()
        assert len(registry) == 0

    def test_len_after_register(self):
        registry = AgentRegistry()
        registry.register(_make_agent())
        assert len(registry) == 1


# ---------------------------------------------------------------------------
# AgentRouter tests
# ---------------------------------------------------------------------------


class TestAgentRouterRoute:
    def test_route_returns_api_discovery_for_generic_query(self):
        registry = AgentRegistry()
        router = AgentRouter(registry)
        request = _make_request("Tell me about APIs")
        assert router.route(request) == AgentName.API_DISCOVERY

    def test_route_returns_governance_for_compliance_query(self):
        registry = AgentRegistry()
        router = AgentRouter(registry)
        request = _make_request("Is the payments-api compliant?")
        assert router.route(request) == AgentName.GOVERNANCE

    def test_route_returns_governance_for_governance_keyword(self):
        registry = AgentRegistry()
        router = AgentRouter(registry)
        request = _make_request("Show me governance issues")
        assert router.route(request) == AgentName.GOVERNANCE

    def test_route_returns_governance_for_remediation_query(self):
        registry = AgentRegistry()
        router = AgentRouter(registry)
        request = _make_request("How can I remediate the failing rules?")
        assert router.route(request) == AgentName.GOVERNANCE

    def test_route_returns_api_discovery_for_ambiguous_query(self):
        registry = AgentRegistry()
        router = AgentRouter(registry)
        # Ambiguous query defaults to discovery
        request = _make_request("show me all APIs")
        assert router.route(request) == AgentName.API_DISCOVERY

    def test_route_is_consistent_for_same_type(self):
        registry = AgentRegistry()
        router = AgentRouter(registry)
        r1 = router.route(_make_request("find APIs"))
        r2 = router.route(_make_request("show me an API"))
        assert r1 == r2 == AgentName.API_DISCOVERY


class TestAgentRouterDispatch:
    @pytest.mark.asyncio
    async def test_dispatch_calls_agent_run(self):
        registry = AgentRegistry()
        agent = _make_agent(content="Here are your APIs")
        registry.register(agent)
        router = AgentRouter(registry)

        request = _make_request("What APIs exist?", session_id="sess-1")
        response = await router.dispatch(request)

        assert response.content == "Here are your APIs"
        assert response.agent_name == AgentName.API_DISCOVERY
        assert response.session_id == "sess-1"

    @pytest.mark.asyncio
    async def test_dispatch_no_agent_raises(self):
        registry = AgentRegistry()  # empty — no agents registered
        router = AgentRouter(registry)
        with pytest.raises(ValueError, match="No agent registered"):
            await router.dispatch(_make_request("help"))

    @pytest.mark.asyncio
    async def test_dispatch_returns_citations(self):
        registry = AgentRegistry()
        registry.register(_make_agent())
        router = AgentRouter(registry)

        response = await router.dispatch(_make_request("payments API"))
        assert response.citations is not None
        assert len(response.citations) > 0
        assert response.citations[0].title == "Test API"


class TestAgentRouterDispatchStream:
    @pytest.mark.asyncio
    async def test_dispatch_stream_yields_content(self):
        registry = AgentRegistry()
        registry.register(_make_agent(content="streaming content"))
        router = AgentRouter(registry)

        chunks = [chunk async for chunk in router.dispatch_stream(_make_request("stream me"))]
        assert chunks == ["streaming content"]

    @pytest.mark.asyncio
    async def test_dispatch_stream_no_agent_raises(self):
        registry = AgentRegistry()
        router = AgentRouter(registry)
        with pytest.raises(ValueError, match="No agent registered"):
            async for _ in router.dispatch_stream(_make_request("stream me")):
                pass


# ---------------------------------------------------------------------------
# AgentRequest / AgentResponse model tests
# ---------------------------------------------------------------------------


class TestAgentRequestModel:
    def test_minimal_request(self):
        req = AgentRequest(message="Hello")
        assert req.message == "Hello"
        assert req.session_id is None
        assert req.accessible_api_ids is None
        assert req.metadata == {}

    def test_full_request(self):
        req = AgentRequest(
            message="Find APIs",
            session_id="sess-123",
            accessible_api_ids=["api-a", "api-b"],
            metadata={"source": "chat"},
        )
        assert req.session_id == "sess-123"
        assert req.accessible_api_ids == ["api-a", "api-b"]
        assert req.metadata["source"] == "chat"

    def test_empty_accessible_ids_allowed(self):
        req = AgentRequest(message="Hello", accessible_api_ids=[])
        assert req.accessible_api_ids == []


class TestAgentResponseModel:
    def test_minimal_response(self):
        resp = AgentResponse(
            agent_name=AgentName.API_DISCOVERY,
            content="Here you go",
            session_id="sess-1",
        )
        assert resp.citations is None
        assert resp.tool_calls == []

    def test_response_with_citations(self):
        resp = AgentResponse(
            agent_name=AgentName.API_DISCOVERY,
            content="Here you go",
            session_id="sess-1",
            citations=[Citation(title="API A", url="/api/catalog/api-a")],
            tool_calls=["search_apis"],
        )
        assert len(resp.citations) == 1
        assert resp.tool_calls == ["search_apis"]


# ---------------------------------------------------------------------------
# _is_governance_intent
# ---------------------------------------------------------------------------


class TestIsGovernanceIntent:
    @pytest.mark.parametrize(
        "message",
        [
            "Is the payments-api compliant?",
            "Show me governance issues",
            "Check API compliance",
            "How do I remediate failing rules?",
            "What is the governance score for weather-api?",
            "List non-compliant APIs",
            "What governance rules does this API fail?",
            "API policies for this endpoint",
            "Show governance status",
            "This API has a policy violation",
        ],
    )
    def test_governance_intent_detected(self, message):
        assert _is_governance_intent(message) is True

    @pytest.mark.parametrize(
        "message",
        [
            "Find me payment APIs",
            "What APIs do you have?",
            "Show me the weather API spec",
            "How do I use the maps API?",
            "List all available APIs",
            "Tell me about the REST APIs",
        ],
    )
    def test_non_governance_intent_not_detected(self, message):
        assert _is_governance_intent(message) is False

    def test_case_insensitive(self):
        assert _is_governance_intent("IS THIS API COMPLIANT?") is True

    def test_empty_message_is_not_governance(self):
        assert _is_governance_intent("") is False


# ---------------------------------------------------------------------------
# AgentRouter dispatch — governance agent routing
# ---------------------------------------------------------------------------


class TestAgentRouterGovernanceDispatch:
    @pytest.mark.asyncio
    async def test_dispatches_governance_query_to_governance_agent(self):
        registry = AgentRegistry()
        governance_agent = _make_agent(name=AgentName.GOVERNANCE, content="Governance response")
        registry.register(governance_agent)

        router = AgentRouter(registry)
        request = _make_request("Is this API compliant with governance standards?")
        response = await router.dispatch(request)

        assert response.agent_name == AgentName.GOVERNANCE
        assert response.content == "Governance response"

    @pytest.mark.asyncio
    async def test_dispatches_discovery_query_to_discovery_agent(self):
        registry = AgentRegistry()
        discovery_agent = _make_agent(name=AgentName.API_DISCOVERY, content="Discovery response")
        registry.register(discovery_agent)

        router = AgentRouter(registry)
        request = _make_request("Find me all REST APIs")
        response = await router.dispatch(request)

        assert response.agent_name == AgentName.API_DISCOVERY
        assert response.content == "Discovery response"

    @pytest.mark.asyncio
    async def test_governance_dispatch_raises_when_not_registered(self):
        registry = AgentRegistry()  # Empty — no governance agent
        router = AgentRouter(registry)
        with pytest.raises(ValueError, match="No agent registered"):
            await router.dispatch(_make_request("Check compliance status"))

    @pytest.mark.asyncio
    async def test_governance_stream_dispatches_correctly(self):
        registry = AgentRegistry()
        governance_agent = _make_agent(name=AgentName.GOVERNANCE, content="Streamed governance")
        registry.register(governance_agent)

        router = AgentRouter(registry)
        chunks = [chunk async for chunk in router.dispatch_stream(_make_request("Show governance report"))]
        assert chunks == ["Streamed governance"]
