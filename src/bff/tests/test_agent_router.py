"""Tests for the AgentRegistry and AgentRouter."""

from __future__ import annotations

from collections.abc import Generator

import pytest

from apic_vibe_portal_bff.agents.agent_registry import AgentRegistry
from apic_vibe_portal_bff.agents.agent_router import AgentRouter
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

        def run(self, request: AgentRequest) -> AgentResponse:
            return AgentResponse(
                agent_name=name,
                content=content,
                session_id=request.session_id or "new-session",
                citations=[Citation(title="Test API", url="/api/catalog/test-api")],
            )

        def stream(self, request: AgentRequest) -> Generator[str]:
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
    def test_route_returns_api_discovery(self):
        registry = AgentRegistry()
        router = AgentRouter(registry)
        request = _make_request("Tell me about APIs")
        assert router.route(request) == AgentName.API_DISCOVERY

    def test_route_is_consistent(self):
        registry = AgentRegistry()
        router = AgentRouter(registry)
        r1 = router.route(_make_request("find APIs"))
        r2 = router.route(_make_request("something else"))
        assert r1 == r2


class TestAgentRouterDispatch:
    def test_dispatch_calls_agent_run(self):
        registry = AgentRegistry()
        agent = _make_agent(content="Here are your APIs")
        registry.register(agent)
        router = AgentRouter(registry)

        request = _make_request("What APIs exist?", session_id="sess-1")
        response = router.dispatch(request)

        assert response.content == "Here are your APIs"
        assert response.agent_name == AgentName.API_DISCOVERY
        assert response.session_id == "sess-1"

    def test_dispatch_no_agent_raises(self):
        registry = AgentRegistry()  # empty — no agents registered
        router = AgentRouter(registry)
        with pytest.raises(ValueError, match="No agent registered"):
            router.dispatch(_make_request("help"))

    def test_dispatch_returns_citations(self):
        registry = AgentRegistry()
        registry.register(_make_agent())
        router = AgentRouter(registry)

        response = router.dispatch(_make_request("payments API"))
        assert response.citations is not None
        assert len(response.citations) > 0
        assert response.citations[0].title == "Test API"


class TestAgentRouterDispatchStream:
    def test_dispatch_stream_yields_content(self):
        registry = AgentRegistry()
        registry.register(_make_agent(content="streaming content"))
        router = AgentRouter(registry)

        chunks = list(router.dispatch_stream(_make_request("stream me")))
        assert chunks == ["streaming content"]

    def test_dispatch_stream_no_agent_raises(self):
        registry = AgentRegistry()
        router = AgentRouter(registry)
        with pytest.raises(ValueError, match="No agent registered"):
            list(router.dispatch_stream(_make_request("stream me")))


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
