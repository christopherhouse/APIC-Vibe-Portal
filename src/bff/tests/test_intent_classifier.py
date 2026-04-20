"""Tests for the intent classifier."""

import pytest

from apic_vibe_portal_bff.agents.intent_classifier import (
    IntentCategory,
    IntentClassification,
    IntentClassifier,
)
from apic_vibe_portal_bff.agents.types import AgentName


class TestIntentClassification:
    """Tests for IntentClassification."""

    def test_init(self):
        """Test IntentClassification initialization."""
        classification = IntentClassification(
            category=IntentCategory.DISCOVERY,
            confidence=0.8,
            reasoning="Test reasoning",
        )
        assert classification.category == IntentCategory.DISCOVERY
        assert classification.confidence == 0.8
        assert classification.reasoning == "Test reasoning"

    def test_confidence_clamping(self):
        """Test that confidence is clamped to [0, 1]."""
        # Above 1.0
        classification = IntentClassification(
            category=IntentCategory.DISCOVERY,
            confidence=1.5,
        )
        assert classification.confidence == 1.0

        # Below 0.0
        classification = IntentClassification(
            category=IntentCategory.DISCOVERY,
            confidence=-0.5,
        )
        assert classification.confidence == 0.0

    def test_repr(self):
        """Test string representation."""
        classification = IntentClassification(
            category=IntentCategory.GOVERNANCE,
            confidence=0.75,
        )
        assert "governance" in repr(classification).lower()
        assert "0.75" in repr(classification)


class TestIntentClassifier:
    """Tests for IntentClassifier."""

    @pytest.fixture
    def classifier(self):
        """Create an IntentClassifier instance."""
        return IntentClassifier(confidence_threshold=0.7)

    # Governance intent tests

    def test_classify_governance_compliance(self, classifier):
        """Test classification of governance/compliance queries."""
        messages = [
            "Is this API compliant?",
            "Show me governance issues",
            "Check compliance for the payment API",
            "What are the governance rules?",
        ]
        for msg in messages:
            classification = classifier.classify(msg)
            assert classification.category == IntentCategory.GOVERNANCE
            assert classification.confidence >= 0.7

    def test_classify_governance_remediation(self, classifier):
        """Test classification of remediation queries."""
        messages = [
            "How do I fix remediation issues?",
            "Show me remediation guidance",
            "What's needed for remediation?",
        ]
        for msg in messages:
            classification = classifier.classify(msg)
            assert classification.category == IntentCategory.GOVERNANCE

    def test_classify_governance_policy(self, classifier):
        """Test classification of policy-related queries."""
        messages = [
            "Are there any policy violations?",
            "Check API policy compliance",
            "Show failing rules",
        ]
        for msg in messages:
            classification = classifier.classify(msg)
            assert classification.category == IntentCategory.GOVERNANCE

    # Discovery intent tests

    def test_classify_discovery_search(self, classifier):
        """Test classification of search/discovery queries."""
        messages = [
            "Search for payment APIs",
            "Find APIs related to authentication",
            "Show me available APIs",
            "What APIs do we have?",
        ]
        for msg in messages:
            classification = classifier.classify(msg)
            assert classification.category == IntentCategory.DISCOVERY
            assert classification.confidence >= 0.7

    def test_classify_discovery_list(self, classifier):
        """Test classification of listing queries."""
        messages = [
            "List all APIs",
            "Give me a list of payment APIs",
            "Show APIs for customer data",
        ]
        for msg in messages:
            classification = classifier.classify(msg)
            assert classification.category == IntentCategory.DISCOVERY

    # Comparison intent tests

    def test_classify_comparison(self, classifier):
        """Test classification of comparison queries."""
        messages = [
            "Compare API A vs API B",
            "What's the difference between these APIs?",
            "Which is better: X or Y?",
            "How does A compare to B?",
        ]
        for msg in messages:
            classification = classifier.classify(msg)
            assert classification.category == IntentCategory.COMPARISON
            assert classification.confidence >= 0.7

    # General/fallback intent tests

    def test_classify_general(self, classifier):
        """Test classification of general queries."""
        messages = [
            "Tell me about the portal",
            "How does this work?",
            "Can you help me?",
        ]
        for msg in messages:
            classification = classifier.classify(msg)
            assert classification.category == IntentCategory.GENERAL
            assert classification.confidence < 0.7  # Low confidence

    def test_classify_empty_message(self, classifier):
        """Test classification of empty message."""
        classification = classifier.classify("")
        assert classification.category == IntentCategory.GENERAL
        assert classification.confidence < 0.7

    # Agent recommendation tests

    def test_recommend_agent_governance(self, classifier):
        """Test agent recommendation for governance intent."""
        classification = IntentClassification(
            category=IntentCategory.GOVERNANCE,
            confidence=0.85,
        )
        agent = classifier.recommend_agent(classification)
        assert agent == AgentName.GOVERNANCE

    def test_recommend_agent_discovery(self, classifier):
        """Test agent recommendation for discovery intent."""
        classification = IntentClassification(
            category=IntentCategory.DISCOVERY,
            confidence=0.80,
        )
        agent = classifier.recommend_agent(classification)
        assert agent == AgentName.API_DISCOVERY

    def test_recommend_agent_comparison(self, classifier):
        """Test agent recommendation for comparison intent."""
        classification = IntentClassification(
            category=IntentCategory.COMPARISON,
            confidence=0.75,
        )
        agent = classifier.recommend_agent(classification)
        assert agent == AgentName.API_DISCOVERY  # Comparison routed to Discovery

    def test_recommend_agent_general(self, classifier):
        """Test agent recommendation for general intent."""
        classification = IntentClassification(
            category=IntentCategory.GENERAL,
            confidence=0.50,
        )
        agent = classifier.recommend_agent(classification)
        assert agent == AgentName.API_DISCOVERY  # General routed to Discovery

    # Clarification tests

    def test_should_clarify_low_confidence(self, classifier):
        """Test clarification recommendation for low confidence."""
        classification = IntentClassification(
            category=IntentCategory.GENERAL,
            confidence=0.50,
        )
        assert classifier.should_clarify(classification) is True

    def test_should_not_clarify_high_confidence(self, classifier):
        """Test no clarification for high confidence."""
        classification = IntentClassification(
            category=IntentCategory.GOVERNANCE,
            confidence=0.85,
        )
        assert classifier.should_clarify(classification) is False

    def test_should_clarify_at_threshold(self, classifier):
        """Test clarification at exact threshold."""
        classification = IntentClassification(
            category=IntentCategory.DISCOVERY,
            confidence=0.7,
        )
        assert classifier.should_clarify(classification) is False  # At threshold, don't clarify

        classification = IntentClassification(
            category=IntentCategory.DISCOVERY,
            confidence=0.69,
        )
        assert classifier.should_clarify(classification) is True  # Below threshold

    # Custom threshold tests

    def test_custom_threshold(self):
        """Test classifier with custom confidence threshold."""
        classifier = IntentClassifier(confidence_threshold=0.9)
        classification = IntentClassification(
            category=IntentCategory.DISCOVERY,
            confidence=0.85,
        )
        assert classifier.should_clarify(classification) is True  # Below custom threshold

    # Case sensitivity tests

    def test_case_insensitive_classification(self, classifier):
        """Test that classification is case-insensitive."""
        messages = [
            "GOVERNANCE ISSUES",
            "Governance Issues",
            "governance issues",
        ]
        for msg in messages:
            classification = classifier.classify(msg)
            assert classification.category == IntentCategory.GOVERNANCE
