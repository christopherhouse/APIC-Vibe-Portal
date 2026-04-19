"""Governance & Compliance Agent — definition, tools, and MAF wiring."""

from __future__ import annotations

import logging
import uuid
from collections.abc import AsyncGenerator
from typing import Any

from apic_vibe_portal_bff.clients.api_center_client import ApiCenterClient
from apic_vibe_portal_bff.utils.logger import sanitize_for_log

from ..base_agent import BaseAgent
from ..types import AgentName, AgentRequest, AgentResponse
from .handler import format_compliance_report, format_score_summary
from .prompts import SYSTEM_PROMPT
from .rules.compliance_checker import ComplianceChecker

logger = logging.getLogger(__name__)


class GovernanceAgent(BaseAgent):
    """Agent specialised in API governance assessment and compliance checking.

    Uses Microsoft Agent Framework (MAF) for tool-calling orchestration.
    Five tools are exposed to the LLM:

    - ``check_api_compliance`` — Run all governance rules against an API
    - ``get_governance_score`` — Calculate overall governance score (0-100)
    - ``list_non_compliant_apis`` — Find APIs failing specific rules
    - ``get_remediation_guidance`` — Get fix instructions for a failing rule
    - ``compare_governance_scores`` — Compare scores across multiple APIs

    Parameters
    ----------
    maf_client:
        MAF ``OpenAIChatClient`` instance.
    api_center_client:
        :class:`~apic_vibe_portal_bff.clients.api_center_client.ApiCenterClient`
        for fetching API metadata.
    checker:
        Optional :class:`~rules.compliance_checker.ComplianceChecker` instance.
        Defaults to a checker using :data:`~rules.governance_rules.DEFAULT_RULES`.
    history_provider:
        Optional MAF ``HistoryProvider`` for conversation persistence.
    model:
        Model name used for token estimation.
    """

    def __init__(
        self,
        maf_client: Any,
        api_center_client: ApiCenterClient,
        checker: ComplianceChecker | None = None,
        history_provider: Any | None = None,
        model: str = "gpt-4o",
    ) -> None:
        self._maf_client = maf_client
        self._api_center = api_center_client
        self._checker = checker or ComplianceChecker()
        self._history_provider = history_provider
        self._model = model
        self._agent = self._create_agent()

    # ------------------------------------------------------------------
    # BaseAgent interface
    # ------------------------------------------------------------------

    @property
    def name(self) -> AgentName:
        return AgentName.GOVERNANCE

    @property
    def description(self) -> str:
        return (
            "Assesses API governance status, checks compliance with organisational standards, "
            "and provides remediation guidance to improve API metadata quality."
        )

    # ------------------------------------------------------------------
    # Tool helpers — fetch API data enriched with versions and deployments
    # ------------------------------------------------------------------

    def _fetch_api_data(self, api_id: str) -> dict[str, Any] | None:
        """Fetch API data from API Center, enriched with versions and deployments.

        Returns ``None`` if the API cannot be found.
        """
        try:
            api = dict(self._api_center.get_api(api_id))
        except Exception as exc:
            logger.warning("GovernanceAgent: failed to fetch API %s — %s", sanitize_for_log(api_id), exc)
            return None

        # Enrich with versions
        try:
            api["versions"] = self._api_center.list_api_versions(api_id)
        except Exception:
            api["versions"] = []

        # Enrich with deployments
        try:
            api["deployments"] = self._api_center.list_deployments(api_id)
        except Exception:
            api["deployments"] = []

        return api

    # ------------------------------------------------------------------
    # Tool factories
    # ------------------------------------------------------------------

    def _make_check_api_compliance_tool(self) -> Any:
        """Create the ``check_api_compliance`` MAF tool."""
        from agent_framework import tool

        agent_self = self

        @tool(
            name="check_api_compliance",
            description=(
                "Run all governance rules against a specific API and return a detailed "
                "compliance report showing which rules pass and fail. "
                "Always call this first when asked about an API's governance status."
            ),
        )
        def check_api_compliance(api_id: str) -> str:
            """Check governance compliance for a specific API.

            Parameters
            ----------
            api_id:
                The API name/ID from the catalog (e.g. ``'payments-api'``).
            """
            api = agent_self._fetch_api_data(api_id)
            if api is None:
                return f"Could not retrieve details for API '{api_id}'. It may not exist in the catalog."

            result = agent_self._checker.check_api(api)
            return format_compliance_report(result)

        return check_api_compliance

    def _make_get_governance_score_tool(self) -> Any:
        """Create the ``get_governance_score`` MAF tool."""
        from agent_framework import tool

        agent_self = self

        @tool(
            name="get_governance_score",
            description=(
                "Return the overall governance score (0–100) and category for a specific API. "
                "Use check_api_compliance for full per-rule details."
            ),
        )
        def get_governance_score(api_id: str) -> str:
            """Get the governance score for a specific API.

            Parameters
            ----------
            api_id:
                The API name/ID from the catalog.
            """
            api = agent_self._fetch_api_data(api_id)
            if api is None:
                return f"Could not retrieve details for API '{api_id}'. It may not exist in the catalog."

            result = agent_self._checker.check_api(api)
            return format_score_summary(api_id, result)

        return get_governance_score

    def _make_list_non_compliant_apis_tool(self) -> Any:
        """Create the ``list_non_compliant_apis`` MAF tool."""
        from agent_framework import tool

        agent_self = self

        @tool(
            name="list_non_compliant_apis",
            description=(
                "List APIs that fail a specific governance rule. "
                "Omit rule_id to list all APIs with at least one critical governance failure. "
                "Returns API names, scores, and the failing rule."
            ),
        )
        def list_non_compliant_apis(rule_id: str = "") -> str:
            """List non-compliant APIs, optionally filtered by rule.

            Parameters
            ----------
            rule_id:
                Optional rule ID to filter by (e.g. ``'metadata.description'``).
                If empty, lists all APIs with critical failures.
            """
            try:
                all_apis = agent_self._api_center.list_apis()
            except Exception as exc:
                logger.warning("GovernanceAgent: list_non_compliant_apis failed — %s", exc)
                return "Could not retrieve the API list. Please try again later."

            if not all_apis:
                return "No APIs found in the catalog."

            lines: list[str] = []
            found = False

            for raw_api in all_apis:
                api_id = raw_api.get("name", "")
                if not api_id:
                    continue

                api = agent_self._fetch_api_data(api_id)
                if api is None:
                    continue

                result = agent_self._checker.check_api(api)

                if rule_id:
                    # Filter to APIs that fail the specific rule
                    matching = [r for r in result.failing_rules if r.rule_id == rule_id]
                    if matching:
                        found = True
                        lines.append(
                            f"- **{result.api_name}** (`{api_id}`): Score {result.score:.0f}/100 — {result.category}"
                        )
                else:
                    # No rule filter — include APIs with any critical failure
                    if result.critical_failures:
                        found = True
                        failures = ", ".join(r.rule_name for r in result.critical_failures)
                        lines.append(
                            f"- **{result.api_name}** (`{api_id}`): "
                            f"Score {result.score:.0f}/100 — {result.category} | "
                            f"Critical failures: {failures}"
                        )

            if not found:
                if rule_id:
                    return f"No APIs are failing the rule '{rule_id}'."
                return "No APIs have critical governance failures. 🎉"

            heading = f"## APIs Failing Rule `{rule_id}`" if rule_id else "## APIs with Critical Governance Failures"
            return heading + "\n\n" + "\n".join(lines)

        return list_non_compliant_apis

    def _make_get_remediation_guidance_tool(self) -> Any:
        """Create the ``get_remediation_guidance`` MAF tool."""
        from agent_framework import tool

        agent_self = self

        @tool(
            name="get_remediation_guidance",
            description=(
                "Get detailed remediation guidance for a specific governance rule failure on an API. "
                "Use check_api_compliance first to identify which rules the API fails."
            ),
        )
        def get_remediation_guidance(api_id: str, rule_id: str) -> str:
            """Get remediation guidance for a specific rule failure.

            Parameters
            ----------
            api_id:
                The API name/ID from the catalog.
            rule_id:
                The rule ID to get guidance for (e.g. ``'metadata.description'``).
            """
            rule = agent_self._checker.get_rule(rule_id)
            if rule is None:
                available = ", ".join(f"`{r.rule_id}`" for r in agent_self._checker.rules)
                return f"Rule '{rule_id}' not found. Available rule IDs: {available}"

            api = agent_self._fetch_api_data(api_id)
            if api is None:
                return f"Could not retrieve details for API '{api_id}'. It may not exist in the catalog."

            rule_result = rule.evaluate(api)

            if rule_result.passed:
                return f"✅ **{rule.name}** — API `{api_id}` already passes this rule. No remediation needed."

            lines = [
                f"## Remediation Guidance: {rule.name}",
                f"**API**: `{api_id}`",
                f"**Severity**: {rule.severity.capitalize()}",
                f"**Rule ID**: `{rule_id}`",
                "",
                "### What to Fix",
                rule.description,
                "",
                "### How to Fix",
                rule.remediation,
            ]
            return "\n".join(lines)

        return get_remediation_guidance

    def _make_compare_governance_scores_tool(self) -> Any:
        """Create the ``compare_governance_scores`` MAF tool."""
        from agent_framework import tool

        agent_self = self

        @tool(
            name="compare_governance_scores",
            description=(
                "Compare governance scores across multiple APIs. "
                "Provide a comma-separated list of API IDs to compare their scores side by side."
            ),
        )
        def compare_governance_scores(api_ids: str) -> str:
            """Compare governance scores for multiple APIs.

            Parameters
            ----------
            api_ids:
                Comma-separated list of API name/IDs to compare
                (e.g. ``'payments-api,weather-api,maps-api'``).
            """
            ids = [a.strip() for a in api_ids.split(",") if a.strip()]
            if not ids:
                return "Please provide at least one API ID to compare."

            lines = [
                "## Governance Score Comparison",
                "",
                "| API | Score | Category | Failing Rules | Critical Failures |",
                "|-----|-------|----------|---------------|-------------------|",
            ]
            found_any = False

            for api_id in ids:
                api = agent_self._fetch_api_data(api_id)
                if api is None:
                    lines.append(f"| `{api_id}` | — | Not found | — | — |")
                    continue

                result = agent_self._checker.check_api(api)
                found_any = True
                from apic_vibe_portal_bff.agents.governance_agent.handler import _CATEGORY_EMOJI  # noqa: PLC0415

                cat_emoji = _CATEGORY_EMOJI.get(result.category, "")
                lines.append(
                    f"| **{result.api_name}** (`{api_id}`) "
                    f"| {result.score:.0f}/100 "
                    f"| {cat_emoji} {result.category} "
                    f"| {len(result.failing_rules)} "
                    f"| {len(result.critical_failures)} |"
                )

            if not found_any:
                return "None of the specified APIs could be found in the catalog."

            return "\n".join(lines)

        return compare_governance_scores

    # ------------------------------------------------------------------
    # MAF Agent construction
    # ------------------------------------------------------------------

    def _create_agent(self) -> Any:
        """Create the MAF :class:`~agent_framework.Agent` wired with all five tools."""
        from agent_framework import Agent

        tools = [
            self._make_check_api_compliance_tool(),
            self._make_get_governance_score_tool(),
            self._make_list_non_compliant_apis_tool(),
            self._make_get_remediation_guidance_tool(),
            self._make_compare_governance_scores_tool(),
        ]

        context_providers = []
        if self._history_provider is not None:
            context_providers.append(self._history_provider)

        return Agent(
            client=self._maf_client,
            instructions=SYSTEM_PROMPT,
            tools=tools,
            context_providers=context_providers,
            name="Governance & Compliance Agent",
            description=self.description,
        )

    # ------------------------------------------------------------------
    # Run / Stream
    # ------------------------------------------------------------------

    async def run(self, request: AgentRequest) -> AgentResponse:
        """Process a governance request through the MAF Agent and return a response."""
        from agent_framework import AgentSession

        effective_session_id = request.session_id or str(uuid.uuid4())

        response = await self._agent.run(
            messages=request.message,
            session=AgentSession(session_id=effective_session_id),
        )
        response_text: str = self._extract_response_text(response)

        return AgentResponse(
            agent_name=self.name,
            content=response_text,
            session_id=effective_session_id,
        )

    async def stream(self, request: AgentRequest) -> AsyncGenerator[str]:
        """Stream the governance agent response as text chunks.

        Delegates to :meth:`run` and yields the full response as a single chunk.
        """
        response = await self.run(request)
        yield response.content

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _extract_response_text(self, response: Any) -> str:
        """Extract a plain-text string from a MAF agent response.

        Handles ``str``, ``list[dict]`` (MAF message format), and objects
        with a ``content`` attribute.
        """
        if isinstance(response, str):
            return response
        if isinstance(response, list):
            parts: list[str] = []
            for item in response:
                if isinstance(item, dict):
                    content = item.get("content", "")
                    if isinstance(content, str):
                        parts.append(content)
                    elif isinstance(content, list):
                        for block in content:
                            if isinstance(block, dict) and block.get("type") == "text":
                                parts.append(block.get("text", ""))
            return "\n".join(parts).strip()
        if hasattr(response, "content"):
            return str(response.content)
        return str(response)
