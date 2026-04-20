"""Intent classifier for routing user queries to appropriate agents.

The classifier analyzes user intent and recommends which agent should handle
the request. Supports both rule-based classification and fallback to LLM-based
classification when confidence is low.
"""

from __future__ import annotations

import logging
from enum import StrEnum

from apic_vibe_portal_bff.agents.types import AgentName

logger = logging.getLogger(__name__)


class IntentCategory(StrEnum):
    """User intent categories that map to agent capabilities."""

    DISCOVERY = "discovery"  # API search, discovery, exploration
    GOVERNANCE = "governance"  # Compliance, governance checks, rules
    COMPARISON = "comparison"  # Compare APIs (routed to Discovery)
    GENERAL = "general"  # General queries (fallback to Discovery)


class IntentClassification:
    """Result of intent classification with confidence score."""

    def __init__(
        self,
        category: IntentCategory,
        confidence: float,
        reasoning: str | None = None,
    ) -> None:
        """Initialize classification result.

        Parameters
        ----------
        category:
            The classified intent category.
        confidence:
            Confidence score between 0.0 and 1.0.
        reasoning:
            Optional explanation of the classification decision.
        """
        self.category = category
        self.confidence = max(0.0, min(1.0, confidence))  # Clamp to [0, 1]
        self.reasoning = reasoning

    def __repr__(self) -> str:
        """Return string representation."""
        return f"IntentClassification(category={self.category}, confidence={self.confidence:.2f})"


# Governance-related keywords (reused from agent_router.py)
_GOVERNANCE_KEYWORDS: frozenset[str] = frozenset(
    {
        "governance",
        "compliance",
        "compliant",
        "non-compliant",
        "noncompliant",
        "non compliant",
        "governance score",
        "governance report",
        "governance status",
        "governance check",
        "governance issue",
        "governance issues",
        "remediat",
        "sunset date",
        "metadata completeness",
        "api standards",
        "api policy",
        "api policies",
        "policy violation",
        "policy check",
        "rule violation",
        "failing rule",
        "failing rules",
        "passes governance",
        "fails governance",
        "governance rule",
        "governance rules",
    }
)

# Discovery/search keywords
_DISCOVERY_KEYWORDS: frozenset[str] = frozenset(
    {
        "search",
        "find",
        "discover",
        "list",
        "show",
        "available",
        "what apis",
        "which apis",
        "how many",
        "get me",
        "give me",
        "looking for",
    }
)

# Comparison keywords
_COMPARISON_KEYWORDS: frozenset[str] = frozenset(
    {
        "compare",
        "comparison",
        "difference",
        "differences",
        "versus",
        "vs",
        "vs.",
        "better than",
        "similar to",
        "which is better",
        "which should i use",
    }
)


class IntentClassifier:
    """Classifies user intent to route queries to appropriate agents.

    Uses a rule-based approach with keyword matching for high-confidence
    classification. Can be extended with LLM-based classification for
    ambiguous queries.

    Parameters
    ----------
    confidence_threshold:
        Minimum confidence score required for direct routing.
        Below this threshold, the system may ask for clarification.
        Default is 0.7 (70%).
    """

    def __init__(self, confidence_threshold: float = 0.7) -> None:
        self.confidence_threshold = confidence_threshold

    def classify(self, message: str) -> IntentClassification:
        """Classify user intent from a message.

        Parameters
        ----------
        message:
            User message to classify.

        Returns
        -------
        IntentClassification
            Classification result with category and confidence score.
        """
        lower = message.lower()

        # Check for governance intent (highest priority)
        if self._has_governance_intent(lower):
            return IntentClassification(
                category=IntentCategory.GOVERNANCE,
                confidence=0.85,
                reasoning="Message contains governance-related keywords",
            )

        # Check for comparison intent
        if self._has_comparison_intent(lower):
            return IntentClassification(
                category=IntentCategory.COMPARISON,
                confidence=0.80,
                reasoning="Message contains comparison keywords",
            )

        # Check for discovery intent
        if self._has_discovery_intent(lower):
            return IntentClassification(
                category=IntentCategory.DISCOVERY,
                confidence=0.75,
                reasoning="Message contains discovery/search keywords",
            )

        # Default to general (routed to Discovery agent)
        return IntentClassification(
            category=IntentCategory.GENERAL,
            confidence=0.50,
            reasoning="No specific intent detected, defaulting to general discovery",
        )

    def recommend_agent(self, classification: IntentClassification) -> AgentName:
        """Recommend an agent based on intent classification.

        Parameters
        ----------
        classification:
            The intent classification result.

        Returns
        -------
        AgentName
            The recommended agent to handle this intent.
        """
        # Map intent categories to agent names
        mapping = {
            IntentCategory.GOVERNANCE: AgentName.GOVERNANCE,
            IntentCategory.DISCOVERY: AgentName.API_DISCOVERY,
            IntentCategory.COMPARISON: AgentName.API_DISCOVERY,  # Discovery agent handles comparisons
            IntentCategory.GENERAL: AgentName.API_DISCOVERY,  # Default fallback
        }
        return mapping[classification.category]

    def should_clarify(self, classification: IntentClassification) -> bool:
        """Determine if clarification should be requested from the user.

        Parameters
        ----------
        classification:
            The intent classification result.

        Returns
        -------
        bool
            ``True`` if confidence is below threshold and clarification is recommended.
        """
        return classification.confidence < self.confidence_threshold

    # Internal helpers

    def _has_governance_intent(self, message: str) -> bool:
        """Check if message contains governance-related keywords."""
        return any(kw in message for kw in _GOVERNANCE_KEYWORDS)

    def _has_discovery_intent(self, message: str) -> bool:
        """Check if message contains discovery/search keywords."""
        return any(kw in message for kw in _DISCOVERY_KEYWORDS)

    def _has_comparison_intent(self, message: str) -> bool:
        """Check if message contains comparison keywords."""
        return any(kw in message for kw in _COMPARISON_KEYWORDS)
