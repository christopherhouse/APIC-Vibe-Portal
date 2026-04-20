"""Multi-agent orchestrator with intent classification and hand-off protocol.

Coordinates multiple agents to handle complex queries, with support for
agent hand-offs and context preservation across agent switches.
"""

from __future__ import annotations

import logging
from collections.abc import AsyncGenerator

from apic_vibe_portal_bff.agents.agent_registry import AgentRegistry
from apic_vibe_portal_bff.agents.context_manager import ContextManager
from apic_vibe_portal_bff.agents.intent_classifier import IntentClassifier
from apic_vibe_portal_bff.agents.types import AgentName, AgentRequest, AgentResponse

logger = logging.getLogger(__name__)


class AgentOrchestrator:
    """Orchestrates multi-agent conversations with intent classification.

    The orchestrator analyzes user intent, selects the appropriate agent,
    and manages conversation context across agent switches. Supports both
    synchronous and streaming responses.

    Parameters
    ----------
    registry:
        Agent registry containing registered agents.
    classifier:
        Intent classifier for routing queries.
    context_manager:
        Context manager for conversation state.
    """

    def __init__(
        self,
        registry: AgentRegistry,
        classifier: IntentClassifier | None = None,
        context_manager: ContextManager | None = None,
    ) -> None:
        self._registry = registry
        self._classifier = classifier or IntentClassifier()
        self._context_manager = context_manager or ContextManager()

    async def process(self, request: AgentRequest) -> AgentResponse:
        """Process a request through the orchestrator.

        Classifies intent, routes to appropriate agent, and maintains context.

        Parameters
        ----------
        request:
            Incoming agent request.

        Returns
        -------
        AgentResponse
            Response from the selected agent.

        Raises
        ------
        ValueError
            If no agent is available for the classified intent.
        """
        # Get or create context for this session
        session_id = request.session_id or "default"
        context = self._context_manager.get_or_create_context(session_id)

        # Classify intent
        classification = self._classifier.classify(request.message)
        recommended_agent = self._classifier.recommend_agent(classification)

        logger.info(
            "Orchestrator classified intent: category=%s confidence=%.2f agent=%s",
            classification.category,
            classification.confidence,
            recommended_agent,
        )

        # Check if we need to hand off to a different agent
        if context.current_agent != recommended_agent:
            # Record the hand-off
            context.record_handoff(
                from_agent=context.current_agent,
                to_agent=recommended_agent,
                reason=f"Intent classification: {classification.category}",
                context_summary=context.get_context_summary(),
            )

        # Get the agent with fallback to Discovery
        agent = self._registry.get(recommended_agent)
        if agent is None:
            logger.warning(
                "Agent %s not registered, falling back to API_DISCOVERY",
                recommended_agent,
            )
            recommended_agent = AgentName.API_DISCOVERY
            agent = self._registry.get(recommended_agent)

        if agent is None:
            raise ValueError(f"No agent available for intent {classification.category}")

        # Dispatch to agent
        logger.info(
            "Orchestrator dispatching to agent=%s session=%s",
            recommended_agent,
            session_id,
        )
        response = await agent.run(request)

        # Add turn to context
        context.add_turn(
            agent_name=recommended_agent,
            user_message=request.message,
            agent_response=response.content,
            metadata={
                "citations": response.citations or [],
                "tool_calls": response.tool_calls,
                "classification": {
                    "category": classification.category,
                    "confidence": classification.confidence,
                    "reasoning": classification.reasoning,
                },
            },
        )

        return response

    async def process_stream(self, request: AgentRequest) -> AsyncGenerator[str]:
        """Process a request and stream the response.

        Similar to :meth:`process` but streams response chunks.

        Parameters
        ----------
        request:
            Incoming agent request.

        Yields
        ------
        str
            Response chunks from the agent.

        Raises
        ------
        ValueError
            If no agent is available for the classified intent.
        """
        # Get or create context for this session
        session_id = request.session_id or "default"
        context = self._context_manager.get_or_create_context(session_id)

        # Classify intent
        classification = self._classifier.classify(request.message)
        recommended_agent = self._classifier.recommend_agent(classification)

        logger.info(
            "Orchestrator classified intent (streaming): category=%s confidence=%.2f agent=%s",
            classification.category,
            classification.confidence,
            recommended_agent,
        )

        # Check if we need to hand off to a different agent
        if context.current_agent != recommended_agent:
            # Record the hand-off
            context.record_handoff(
                from_agent=context.current_agent,
                to_agent=recommended_agent,
                reason=f"Intent classification: {classification.category}",
                context_summary=context.get_context_summary(),
            )

            # Optionally yield a notification about the hand-off
            notification = f"[Connecting to {recommended_agent.replace('_', ' ').title()} specialist...]\n\n"
            yield notification

        # Get the agent with fallback to Discovery
        agent = self._registry.get(recommended_agent)
        if agent is None:
            logger.warning(
                "Agent %s not registered, falling back to API_DISCOVERY",
                recommended_agent,
            )
            recommended_agent = AgentName.API_DISCOVERY
            agent = self._registry.get(recommended_agent)

        if agent is None:
            raise ValueError(f"No agent available for intent {classification.category}")

        # Dispatch to agent and stream response
        logger.info(
            "Orchestrator streaming from agent=%s session=%s",
            recommended_agent,
            session_id,
        )

        # Collect response chunks for context
        response_chunks: list[str] = []

        async for chunk in agent.stream(request):
            response_chunks.append(chunk)
            yield chunk

        # Add turn to context
        full_response = "".join(response_chunks)
        context.add_turn(
            agent_name=recommended_agent,
            user_message=request.message,
            agent_response=full_response,
            metadata={
                "classification": {
                    "category": classification.category,
                    "confidence": classification.confidence,
                    "reasoning": classification.reasoning,
                },
            },
        )

    def get_context(self, session_id: str) -> dict:
        """Get conversation context for a session.

        Parameters
        ----------
        session_id:
            Session identifier.

        Returns
        -------
        dict
            Serialized conversation context.
        """
        context = self._context_manager.get_or_create_context(session_id)
        return context.to_dict()

    def clear_context(self, session_id: str) -> None:
        """Clear conversation context for a session.

        Parameters
        ----------
        session_id:
            Session to clear.
        """
        self._context_manager.clear_context(session_id)
