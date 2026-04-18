"""Unit tests for persistence Pydantic data models."""

from __future__ import annotations

from apic_vibe_portal_bff.data.models.analytics import AnalyticsEventDocument
from apic_vibe_portal_bff.data.models.chat_session import ChatMessageDoc, ChatSessionDocument
from apic_vibe_portal_bff.data.models.governance import GovernanceFinding, GovernanceSnapshotDocument


class TestChatSessionDocument:
    """Tests for :class:`ChatSessionDocument`."""

    def test_new_factory(self):
        session = ChatSessionDocument.new(session_id="s1", user_id="u1", title="Test")
        assert session.id == "s1"
        assert session.user_id == "u1"
        assert session.title == "Test"
        assert session.messages == []
        assert session.schema_version == 1
        assert session.is_deleted is False
        assert session.deleted_at is None
        assert session.created_at.endswith("Z")
        assert session.updated_at.endswith("Z")

    def test_to_cosmos_dict_uses_aliases(self):
        session = ChatSessionDocument.new(session_id="s1", user_id="u1")
        d = session.to_cosmos_dict()
        assert "userId" in d
        assert "createdAt" in d
        assert "updatedAt" in d
        assert "schemaVersion" in d
        assert "isDeleted" in d
        assert "deletedAt" in d
        assert "tokensUsed" in d
        # Python field names should not appear in the dict
        assert "user_id" not in d
        assert "created_at" not in d

    def test_from_cosmos_dict(self):
        data = {
            "id": "s1",
            "userId": "u1",
            "title": "Hello",
            "messages": [{"id": "m1", "role": "user", "content": "Hi", "timestamp": "2026-01-01T00:00:00Z"}],
            "createdAt": "2026-01-01T00:00:00Z",
            "updatedAt": "2026-01-01T00:00:00Z",
            "schemaVersion": 1,
            "isDeleted": False,
            "deletedAt": None,
            "tokensUsed": 10,
        }
        session = ChatSessionDocument.model_validate(data)
        assert session.user_id == "u1"
        assert session.tokens_used == 10
        assert len(session.messages) == 1
        assert session.messages[0].role == "user"

    def test_chat_message_doc(self):
        msg = ChatMessageDoc(id="m1", role="assistant", content="Hello!", timestamp="2026-01-01T00:00:00Z")
        assert msg.role == "assistant"


class TestGovernanceSnapshotDocument:
    """Tests for :class:`GovernanceSnapshotDocument`."""

    def test_new_factory(self):
        snap = GovernanceSnapshotDocument.new(snapshot_id="g1", api_id="api-1", compliance_score=85.5)
        assert snap.id == "g1"
        assert snap.api_id == "api-1"
        assert snap.compliance_score == 85.5
        assert snap.findings == []
        assert snap.schema_version == 1
        assert snap.is_deleted is False

    def test_to_cosmos_dict(self):
        snap = GovernanceSnapshotDocument.new(snapshot_id="g1", api_id="api-1")
        d = snap.to_cosmos_dict()
        assert "apiId" in d
        assert "complianceScore" in d
        assert "schemaVersion" in d
        assert "isDeleted" in d

    def test_with_findings(self):
        finding = GovernanceFinding(ruleId="r1", ruleName="Has Description", severity="high", passed=True, message="OK")
        snap = GovernanceSnapshotDocument.new(snapshot_id="g1", api_id="api-1", findings=[finding])
        assert len(snap.findings) == 1
        assert snap.findings[0].rule_id == "r1"


class TestAnalyticsEventDocument:
    """Tests for :class:`AnalyticsEventDocument`."""

    def test_new_factory(self):
        event = AnalyticsEventDocument.new(event_id="e1", event_type="page_view", user_id="u1")
        assert event.id == "e1"
        assert event.event_type == "page_view"
        assert event.user_id == "u1"
        assert event.metadata == {}
        assert event.schema_version == 1
        assert event.is_deleted is False

    def test_to_cosmos_dict(self):
        event = AnalyticsEventDocument.new(event_id="e1", event_type="search_query", metadata={"q": "test"})
        d = event.to_cosmos_dict()
        assert "eventType" in d
        assert "userId" in d
        assert d["metadata"] == {"q": "test"}

    def test_from_cosmos_dict(self):
        data = {
            "id": "e1",
            "eventType": "api_view",
            "timestamp": "2026-01-01T00:00:00Z",
            "userId": "u1",
            "apiId": "api-1",
            "metadata": {"source": "catalog"},
            "schemaVersion": 1,
            "isDeleted": False,
            "deletedAt": None,
        }
        event = AnalyticsEventDocument.model_validate(data)
        assert event.event_type == "api_view"
        assert event.api_id == "api-1"
