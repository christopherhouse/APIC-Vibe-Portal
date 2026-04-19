"""Tests for the Governance & Compliance Agent and its tools."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from apic_vibe_portal_bff.agents.governance_agent.definition import GovernanceAgent
from apic_vibe_portal_bff.agents.governance_agent.handler import format_compliance_report, format_score_summary
from apic_vibe_portal_bff.agents.governance_agent.prompts import FEW_SHOT_EXAMPLES, SYSTEM_PROMPT
from apic_vibe_portal_bff.agents.governance_agent.rules.compliance_checker import (
    ComplianceChecker,
)
from apic_vibe_portal_bff.agents.types import AgentName, AgentRequest, AgentResponse

# ---------------------------------------------------------------------------
# Sample API data
# ---------------------------------------------------------------------------

_COMPLIANT_API = {
    "name": "weather-api",
    "title": "Weather API",
    "kind": "REST",
    "lifecycleStage": "Production",
    "description": "Provides real-time weather data using OAuth 2.0 authentication.",
    "contacts": [{"name": "Weather Team", "email": "weather@example.com"}],
    "license": "Proprietary",
    "externalDocs": [{"url": "https://docs.example.com/weather"}],
    "customProperties": {"tags": ["weather", "data"]},
    "versions": [{"name": "v1", "lifecycleStage": "Production", "specifications": [{"name": "openapi"}]}],
    "deployments": [{"name": "prod", "server": {"runtimeUri": ["https://api.example.com/weather"]}}],
}

_MINIMAL_API = {
    "name": "bare-api",
    "title": "bare-api",
    "kind": "REST",
    "lifecycleStage": "Development",
    "versions": [],
    "deployments": [],
}


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def mock_maf_client():
    return MagicMock()


@pytest.fixture
def mock_api_center():
    client = MagicMock()
    client.get_api.return_value = dict(_COMPLIANT_API)
    client.list_api_versions.return_value = _COMPLIANT_API["versions"]
    client.list_deployments.return_value = _COMPLIANT_API["deployments"]
    client.list_apis.return_value = [
        {"name": "weather-api", "title": "Weather API"},
        {"name": "bare-api", "title": "bare-api"},
    ]
    return client


@pytest.fixture
def checker():
    return ComplianceChecker()


@pytest.fixture
def agent(mock_maf_client, mock_api_center, checker):
    """Return a GovernanceAgent with a mocked MAF agent."""
    mock_maf_agent = MagicMock()
    mock_maf_agent.run = AsyncMock(return_value="Governance report for weather-api.")

    with patch("agent_framework.Agent", return_value=mock_maf_agent):
        a = GovernanceAgent(
            maf_client=mock_maf_client,
            api_center_client=mock_api_center,
            checker=checker,
        )
        a._agent = mock_maf_agent
        return a


# ---------------------------------------------------------------------------
# GovernanceAgent identity
# ---------------------------------------------------------------------------


class TestGovernanceAgentIdentity:
    def test_name(self, agent):
        assert agent.name == AgentName.GOVERNANCE

    def test_description_mentions_governance(self, agent):
        assert "governance" in agent.description.lower()


# ---------------------------------------------------------------------------
# _fetch_api_data
# ---------------------------------------------------------------------------


class TestFetchApiData:
    def test_returns_dict_with_versions_and_deployments(self, agent, mock_api_center):
        data = agent._fetch_api_data("weather-api")
        assert data is not None
        assert "versions" in data
        assert "deployments" in data

    def test_returns_none_on_api_center_error(self, agent, mock_api_center):
        mock_api_center.get_api.side_effect = Exception("Not found")
        data = agent._fetch_api_data("nonexistent")
        assert data is None

    def test_versions_defaults_to_empty_on_error(self, agent, mock_api_center):
        mock_api_center.list_api_versions.side_effect = Exception("Network error")
        data = agent._fetch_api_data("weather-api")
        assert data is not None
        assert data["versions"] == []

    def test_deployments_defaults_to_empty_on_error(self, agent, mock_api_center):
        mock_api_center.list_deployments.side_effect = Exception("Network error")
        data = agent._fetch_api_data("weather-api")
        assert data is not None
        assert data["deployments"] == []


# ---------------------------------------------------------------------------
# Tool: check_api_compliance
# ---------------------------------------------------------------------------


class TestCheckApiComplianceTool:
    def test_returns_compliance_report_for_valid_api(self, agent):
        tool_fn = agent._make_check_api_compliance_tool()
        result = tool_fn(api_id="weather-api")
        assert "Governance Report" in result
        assert "weather-api" in result

    def test_returns_error_message_for_unknown_api(self, agent, mock_api_center):
        mock_api_center.get_api.side_effect = Exception("Not found")
        tool_fn = agent._make_check_api_compliance_tool()
        result = tool_fn(api_id="nonexistent-api")
        assert "not exist" in result.lower() or "could not" in result.lower()

    def test_includes_score_in_report(self, agent):
        tool_fn = agent._make_check_api_compliance_tool()
        result = tool_fn(api_id="weather-api")
        assert "/100" in result or "Score" in result

    def test_includes_failing_rules_section(self, agent, mock_api_center):
        # Provide a minimal API that will fail many rules
        mock_api_center.get_api.return_value = dict(_MINIMAL_API)
        mock_api_center.list_api_versions.return_value = []
        mock_api_center.list_deployments.return_value = []
        tool_fn = agent._make_check_api_compliance_tool()
        result = tool_fn(api_id="bare-api")
        assert "Failing" in result or "FAIL" in result


# ---------------------------------------------------------------------------
# Tool: get_governance_score
# ---------------------------------------------------------------------------


class TestGetGovernanceScoreTool:
    def test_returns_score_summary(self, agent):
        tool_fn = agent._make_get_governance_score_tool()
        result = tool_fn(api_id="weather-api")
        assert "Score" in result or "/100" in result

    def test_returns_error_for_unknown_api(self, agent, mock_api_center):
        mock_api_center.get_api.side_effect = Exception("Not found")
        tool_fn = agent._make_get_governance_score_tool()
        result = tool_fn(api_id="nonexistent")
        assert "could not" in result.lower()

    def test_includes_api_id_in_result(self, agent):
        tool_fn = agent._make_get_governance_score_tool()
        result = tool_fn(api_id="weather-api")
        assert "weather-api" in result


# ---------------------------------------------------------------------------
# Tool: list_non_compliant_apis
# ---------------------------------------------------------------------------


class TestListNonCompliantApisTool:
    def test_lists_all_critical_failures_when_no_rule_filter(self, agent, mock_api_center):
        # Make bare-api fail critical rules
        def get_api_side_effect(api_id):
            if api_id == "bare-api":
                return dict(_MINIMAL_API)
            return dict(_COMPLIANT_API)

        mock_api_center.get_api.side_effect = get_api_side_effect
        mock_api_center.list_api_versions.return_value = []
        mock_api_center.list_deployments.return_value = []

        tool_fn = agent._make_list_non_compliant_apis_tool()
        result = tool_fn(rule_id="")
        # bare-api should appear since it has critical failures
        assert "bare-api" in result

    def test_filters_by_rule_id(self, agent, mock_api_center):
        # Make both APIs fail the description rule
        def get_api_side_effect(api_id):
            return {
                "name": api_id,
                "title": api_id,
                "lifecycleStage": "Development",
                "versions": [],
                "deployments": [],
                "description": "",
            }

        mock_api_center.get_api.side_effect = get_api_side_effect
        mock_api_center.list_api_versions.return_value = []
        mock_api_center.list_deployments.return_value = []

        tool_fn = agent._make_list_non_compliant_apis_tool()
        result = tool_fn(rule_id="metadata.description")
        assert "weather-api" in result or "bare-api" in result

    def test_reports_no_failures_when_all_pass(self, agent, mock_api_center):
        # Both APIs are compliant for the description rule
        def get_api_side_effect(api_id):
            return dict(_COMPLIANT_API, name=api_id)

        mock_api_center.get_api.side_effect = get_api_side_effect
        tool_fn = agent._make_list_non_compliant_apis_tool()
        result = tool_fn(rule_id="metadata.description")
        assert "No APIs" in result or "no apis" in result.lower()

    def test_handles_api_center_error_gracefully(self, agent, mock_api_center):
        mock_api_center.list_apis.side_effect = Exception("Service unavailable")
        tool_fn = agent._make_list_non_compliant_apis_tool()
        result = tool_fn(rule_id="")
        assert "could not" in result.lower() or "try again" in result.lower()

    def test_handles_empty_catalog(self, agent, mock_api_center):
        mock_api_center.list_apis.return_value = []
        tool_fn = agent._make_list_non_compliant_apis_tool()
        result = tool_fn(rule_id="")
        assert "No APIs" in result

    def test_returns_celebration_when_all_compliant(self, agent, mock_api_center):
        mock_api_center.get_api.return_value = dict(_COMPLIANT_API)
        mock_api_center.list_api_versions.return_value = _COMPLIANT_API["versions"]
        mock_api_center.list_deployments.return_value = _COMPLIANT_API["deployments"]
        tool_fn = agent._make_list_non_compliant_apis_tool()
        result = tool_fn(rule_id="")
        # All APIs pass critical rules — should see a success message
        assert "No APIs" in result or "🎉" in result or "no" in result.lower()


# ---------------------------------------------------------------------------
# Tool: get_remediation_guidance
# ---------------------------------------------------------------------------


class TestGetRemediationGuidanceTool:
    def test_returns_guidance_for_failing_rule(self, agent, mock_api_center):
        # Minimal API will fail metadata.description
        mock_api_center.get_api.return_value = dict(_MINIMAL_API)
        mock_api_center.list_api_versions.return_value = []
        mock_api_center.list_deployments.return_value = []

        tool_fn = agent._make_get_remediation_guidance_tool()
        result = tool_fn(api_id="bare-api", rule_id="metadata.description")
        assert "Remediation" in result or "Fix" in result or "description" in result.lower()

    def test_returns_pass_message_for_passing_rule(self, agent):
        tool_fn = agent._make_get_remediation_guidance_tool()
        result = tool_fn(api_id="weather-api", rule_id="metadata.description")
        assert "already passes" in result or "✅" in result

    def test_returns_error_for_unknown_rule(self, agent):
        tool_fn = agent._make_get_remediation_guidance_tool()
        result = tool_fn(api_id="weather-api", rule_id="nonexistent.rule")
        assert "not found" in result.lower() or "available" in result.lower()

    def test_returns_error_for_unknown_api(self, agent, mock_api_center):
        mock_api_center.get_api.side_effect = Exception("Not found")
        tool_fn = agent._make_get_remediation_guidance_tool()
        result = tool_fn(api_id="missing-api", rule_id="metadata.description")
        assert "could not" in result.lower()

    def test_includes_rule_id_in_response(self, agent, mock_api_center):
        mock_api_center.get_api.return_value = dict(_MINIMAL_API)
        mock_api_center.list_api_versions.return_value = []
        mock_api_center.list_deployments.return_value = []
        tool_fn = agent._make_get_remediation_guidance_tool()
        result = tool_fn(api_id="bare-api", rule_id="metadata.description")
        assert "metadata.description" in result


# ---------------------------------------------------------------------------
# Tool: compare_governance_scores
# ---------------------------------------------------------------------------


class TestCompareGovernanceScoresTool:
    def test_returns_comparison_table(self, agent):
        tool_fn = agent._make_compare_governance_scores_tool()
        result = tool_fn(api_ids="weather-api,bare-api")
        assert "Governance Score Comparison" in result
        assert "weather-api" in result

    def test_handles_single_api(self, agent):
        tool_fn = agent._make_compare_governance_scores_tool()
        result = tool_fn(api_ids="weather-api")
        assert "weather-api" in result

    def test_handles_empty_input(self, agent):
        tool_fn = agent._make_compare_governance_scores_tool()
        result = tool_fn(api_ids="")
        assert "Please provide" in result or "at least one" in result.lower()

    def test_shows_not_found_for_missing_api(self, agent, mock_api_center):
        def get_api_side_effect(api_id):
            if api_id == "missing":
                raise Exception("Not found")
            return dict(_COMPLIANT_API)

        mock_api_center.get_api.side_effect = get_api_side_effect
        tool_fn = agent._make_compare_governance_scores_tool()
        result = tool_fn(api_ids="weather-api,missing")
        assert "missing" in result
        assert "Not found" in result or "—" in result

    def test_handles_whitespace_in_api_ids(self, agent):
        tool_fn = agent._make_compare_governance_scores_tool()
        result = tool_fn(api_ids=" weather-api , weather-api ")
        assert "weather-api" in result


# ---------------------------------------------------------------------------
# GovernanceAgent.run
# ---------------------------------------------------------------------------


class TestGovernanceAgentRun:
    @pytest.mark.asyncio
    async def test_run_returns_agent_response(self, agent):
        request = AgentRequest(message="Is payments-api compliant?", session_id="sess-1")
        response = await agent.run(request)
        assert isinstance(response, AgentResponse)
        assert response.agent_name == AgentName.GOVERNANCE

    @pytest.mark.asyncio
    async def test_run_uses_maf_agent(self, agent):
        request = AgentRequest(message="Check governance", session_id="sess-1")
        await agent.run(request)
        agent._agent.run.assert_called_once()

    @pytest.mark.asyncio
    async def test_run_preserves_session_id(self, agent):
        request = AgentRequest(message="Governance check", session_id="my-session")
        response = await agent.run(request)
        assert response.session_id == "my-session"

    @pytest.mark.asyncio
    async def test_run_generates_session_id_when_none(self, agent):
        request = AgentRequest(message="Governance check", session_id=None)
        response = await agent.run(request)
        assert response.session_id  # Should be a non-empty generated UUID

    @pytest.mark.asyncio
    async def test_run_passes_message_to_maf(self, agent):
        request = AgentRequest(message="Show me compliance for weather-api", session_id="s1")
        await agent.run(request)
        call_kwargs = agent._agent.run.call_args
        assert call_kwargs.kwargs.get("messages") == "Show me compliance for weather-api"


# ---------------------------------------------------------------------------
# GovernanceAgent.stream
# ---------------------------------------------------------------------------


class TestGovernanceAgentStream:
    @pytest.mark.asyncio
    async def test_stream_yields_content(self, agent):
        request = AgentRequest(message="Check governance", session_id="sess-1")
        chunks = [chunk async for chunk in agent.stream(request)]
        assert len(chunks) > 0
        assert "".join(chunks) == "Governance report for weather-api."


# ---------------------------------------------------------------------------
# _extract_response_text
# ---------------------------------------------------------------------------


class TestExtractResponseText:
    def test_returns_str_as_is(self, agent):
        assert agent._extract_response_text("Hello") == "Hello"

    def test_extracts_from_list_of_dicts(self, agent):
        response = [{"role": "assistant", "content": "Hello from governance."}]
        assert agent._extract_response_text(response) == "Hello from governance."

    def test_extracts_from_list_of_content_blocks(self, agent):
        response = [{"role": "assistant", "content": [{"type": "text", "text": "Block content"}]}]
        assert agent._extract_response_text(response) == "Block content"

    def test_extracts_content_attribute(self, agent):
        class FakeResponse:
            content = "Attribute content"

        assert agent._extract_response_text(FakeResponse()) == "Attribute content"

    def test_falls_back_to_str_for_unknown_type(self, agent):
        result = agent._extract_response_text(42)
        assert result == "42"


# ---------------------------------------------------------------------------
# Prompts
# ---------------------------------------------------------------------------


class TestGovernancePrompts:
    def test_system_prompt_is_non_empty(self):
        assert len(SYSTEM_PROMPT) > 100

    def test_system_prompt_mentions_governance(self):
        assert "governance" in SYSTEM_PROMPT.lower()

    def test_system_prompt_mentions_all_tool_names(self):
        tool_names = [
            "check_api_compliance",
            "get_governance_score",
            "list_non_compliant_apis",
            "get_remediation_guidance",
            "compare_governance_scores",
        ]
        for tool_name in tool_names:
            assert tool_name in SYSTEM_PROMPT, f"Tool '{tool_name}' not mentioned in system prompt"

    def test_few_shot_examples_non_empty(self):
        assert len(FEW_SHOT_EXAMPLES) > 0

    def test_few_shot_examples_have_role_and_content(self):
        for example in FEW_SHOT_EXAMPLES:
            assert "role" in example
            assert "content" in example


# ---------------------------------------------------------------------------
# Handler helpers
# ---------------------------------------------------------------------------


class TestHandlerHelpers:
    def test_format_compliance_report_includes_score(self):
        checker = ComplianceChecker()
        api = {
            "name": "test-api",
            "title": "Test API",
            "lifecycleStage": "Development",
            "description": "",
            "versions": [],
            "deployments": [],
        }
        result = checker.check_api(api)
        report = format_compliance_report(result)
        assert "Governance Report" in report
        assert "100" in report  # Score always shown relative to 100

    def test_format_score_summary_is_concise(self):
        checker = ComplianceChecker()
        api = {"name": "test-api", "title": "Test API", "description": "Uses OAuth."}
        result = checker.check_api(api)
        summary = format_score_summary("test-api", result)
        assert "test-api" in summary
        assert "Score" in summary or "/100" in summary
