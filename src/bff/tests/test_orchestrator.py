"""Tests for the multi-agent orchestrator."""

from unittest.mock import AsyncMock, Mock

import pytest

from apic_vibe_portal_bff.agents.agent_registry import AgentRegistry
from apic_vibe_portal_bff.agents.context_manager import ContextManager
from apic_vibe_portal_bff.agents.intent_classifier import IntentClassifier
from apic_vibe_portal_bff.agents.orchestrator import AgentOrchestrator
from apic_vibe_portal_bff.agents.types import AgentName, AgentRequest, AgentResponse


@pytest.fixture
def mock_discovery_agent():
    """Create a mock API Discovery agent."""
    agent = Mock()
    agent.name = AgentName.API_DISCOVERY
    agent.description = "API Discovery Agent"
    agent.run = AsyncMock(
        return_value=AgentResponse(
            agent_name=AgentName.API_DISCOVERY,
            content="Discovery response",
            session_id="test-session",
            citations=[],
            tool_calls=["searchApis"],
        )
    )

    async def mock_stream(request):  # Accept request parameter
        yield "Discovery "
        yield "streaming "
        yield "response"

    agent.stream = mock_stream
    return agent


@pytest.fixture
def mock_governance_agent():
    """Create a mock Governance agent."""
    agent = Mock()
    agent.name = AgentName.GOVERNANCE
    agent.description = "Governance Agent"
    agent.run = AsyncMock(
        return_value=AgentResponse(
            agent_name=AgentName.GOVERNANCE,
            content="Governance response",
            session_id="test-session",
            citations=[],
            tool_calls=["checkApiCompliance"],
        )
    )

    async def mock_stream(request):  # Accept request parameter
        yield "Governance "
        yield "streaming "
        yield "response"

    agent.stream = mock_stream
    return agent


@pytest.fixture
def registry(mock_discovery_agent, mock_governance_agent):
    """Create an agent registry with mock agents."""
    registry = AgentRegistry()
    registry.register(mock_discovery_agent)
    registry.register(mock_governance_agent)
    return registry


@pytest.fixture
def orchestrator(registry):
    """Create an orchestrator with mock agents."""
    classifier = IntentClassifier()
    context_manager = ContextManager()
    return AgentOrchestrator(registry, classifier, context_manager)


class TestAgentOrchestrator:
    """Tests for AgentOrchestrator."""

    @pytest.mark.asyncio
    async def test_process_discovery_intent(self, orchestrator, mock_discovery_agent):
        """Test processing a discovery intent."""
        request = AgentRequest(
            message="Find payment APIs",
            session_id="test-session",
        )

        response = await orchestrator.process(request)

        assert response.agent_name == AgentName.API_DISCOVERY
        assert response.content == "Discovery response"
        mock_discovery_agent.run.assert_called_once()

    @pytest.mark.asyncio
    async def test_process_governance_intent(self, orchestrator, mock_governance_agent):
        """Test processing a governance intent."""
        request = AgentRequest(
            message="Check API compliance",
            session_id="test-session",
        )

        response = await orchestrator.process(request)

        assert response.agent_name == AgentName.GOVERNANCE
        assert response.content == "Governance response"
        mock_governance_agent.run.assert_called_once()

    @pytest.mark.asyncio
    async def test_process_creates_context(self, orchestrator):
        """Test that processing creates conversation context."""
        request = AgentRequest(
            message="Find APIs",
            session_id="test-session",
        )

        await orchestrator.process(request)

        context = orchestrator.get_context("test-session")
        assert context["session_id"] == "test-session"
        assert len(context["turns"]) == 1

    @pytest.mark.asyncio
    async def test_process_records_handoff(self, orchestrator):
        """Test that agent handoff is recorded."""
        # First request to Discovery
        request1 = AgentRequest(
            message="Find APIs",
            session_id="test-session",
        )
        await orchestrator.process(request1)

        # Second request to Governance (should trigger handoff)
        request2 = AgentRequest(
            message="Check compliance",
            session_id="test-session",
        )
        await orchestrator.process(request2)

        context = orchestrator.get_context("test-session")
        assert len(context["handoffs"]) == 1
        assert context["handoffs"][0]["from_agent"] == AgentName.API_DISCOVERY
        assert context["handoffs"][0]["to_agent"] == AgentName.GOVERNANCE

    @pytest.mark.asyncio
    async def test_process_no_handoff_same_agent(self, orchestrator):
        """Test that no handoff is recorded when staying with same agent."""
        # Both requests to Discovery
        request1 = AgentRequest(
            message="Find APIs",
            session_id="test-session",
        )
        await orchestrator.process(request1)

        request2 = AgentRequest(
            message="Search for more APIs",
            session_id="test-session",
        )
        await orchestrator.process(request2)

        context = orchestrator.get_context("test-session")
        assert len(context["handoffs"]) == 0

    @pytest.mark.asyncio
    async def test_process_default_session_id(self, orchestrator):
        """Test processing with no session ID uses default."""
        request = AgentRequest(
            message="Find APIs",
            session_id=None,
        )

        response = await orchestrator.process(request)

        assert response.session_id == "test-session"
        context = orchestrator.get_context("default")
        assert context is not None

    @pytest.mark.asyncio
    async def test_process_fallback_to_discovery(self, orchestrator):
        """Test fallback to Discovery agent when target agent not registered."""
        # Create orchestrator with only Discovery agent
        registry = AgentRegistry()
        mock_agent = Mock()
        mock_agent.name = AgentName.API_DISCOVERY
        mock_agent.run = AsyncMock(
            return_value=AgentResponse(
                agent_name=AgentName.API_DISCOVERY,
                content="Fallback response",
                session_id="test-session",
                citations=[],
                tool_calls=[],
            )
        )
        registry.register(mock_agent)

        orchestrator = AgentOrchestrator(registry)

        # Request governance (should fall back to Discovery)
        request = AgentRequest(
            message="Check compliance",
            session_id="test-session",
        )

        response = await orchestrator.process(request)

        assert response.agent_name == AgentName.API_DISCOVERY
        assert response.content == "Fallback response"

    @pytest.mark.asyncio
    async def test_process_no_agents_raises_error(self):
        """Test that processing with no agents raises ValueError."""
        registry = AgentRegistry()
        orchestrator = AgentOrchestrator(registry)

        request = AgentRequest(
            message="Find APIs",
            session_id="test-session",
        )

        with pytest.raises(ValueError, match="No agent available"):
            await orchestrator.process(request)

    @pytest.mark.asyncio
    async def test_process_stream_discovery(self, orchestrator):
        """Test streaming response from Discovery agent."""
        request = AgentRequest(
            message="Find APIs",
            session_id="test-session",
        )

        chunks = []
        async for chunk in orchestrator.process_stream(request):
            chunks.append(chunk)

        assert "Discovery" in "".join(chunks)
        assert "streaming" in "".join(chunks)

    @pytest.mark.asyncio
    async def test_process_stream_governance(self, orchestrator):
        """Test streaming response from Governance agent."""
        request = AgentRequest(
            message="Check compliance",
            session_id="test-session",
        )

        chunks = []
        async for chunk in orchestrator.process_stream(request):
            chunks.append(chunk)

        assert "Governance" in "".join(chunks)

    @pytest.mark.asyncio
    async def test_process_stream_handoff_notification(self, orchestrator):
        """Test that handoff includes notification in stream."""
        # First request to Discovery
        request1 = AgentRequest(
            message="Find APIs",
            session_id="test-session",
        )
        async for _ in orchestrator.process_stream(request1):
            pass

        # Second request to Governance (should include notification)
        request2 = AgentRequest(
            message="Check compliance",
            session_id="test-session",
        )

        chunks = []
        async for chunk in orchestrator.process_stream(request2):
            chunks.append(chunk)

        full_response = "".join(chunks)
        assert "Connecting" in full_response or "connecting" in full_response.lower()

    @pytest.mark.asyncio
    async def test_process_stream_creates_context(self, orchestrator):
        """Test that streaming creates conversation context."""
        request = AgentRequest(
            message="Find APIs",
            session_id="test-session",
        )

        async for _ in orchestrator.process_stream(request):
            pass

        context = orchestrator.get_context("test-session")
        assert context["session_id"] == "test-session"
        assert len(context["turns"]) == 1

    def test_get_context(self, orchestrator):
        """Test retrieving context."""
        context = orchestrator.get_context("new-session")
        assert context["session_id"] == "new-session"
        assert len(context["turns"]) == 0

    def test_clear_context(self, orchestrator):
        """Test clearing context."""
        # Create a context
        orchestrator.get_context("test-session")

        # Clear it
        orchestrator.clear_context("test-session")

        # Should create a new empty context
        context = orchestrator.get_context("test-session")
        assert len(context["turns"]) == 0
