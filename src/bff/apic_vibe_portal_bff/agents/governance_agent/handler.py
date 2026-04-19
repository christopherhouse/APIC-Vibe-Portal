"""Response processing helpers for the Governance & Compliance Agent."""

from __future__ import annotations

from apic_vibe_portal_bff.agents.governance_agent.rules.compliance_checker import (
    ComplianceResult,
    GovernanceCategory,
)
from apic_vibe_portal_bff.agents.governance_agent.rules.governance_rules import RuleSeverity

# Severity emoji map for markdown output
_SEVERITY_EMOJI: dict[RuleSeverity, str] = {
    RuleSeverity.CRITICAL: "🔴",
    RuleSeverity.WARNING: "🟡",
    RuleSeverity.INFO: "🔵",
}

_CATEGORY_EMOJI: dict[GovernanceCategory, str] = {
    GovernanceCategory.EXCELLENT: "✅",
    GovernanceCategory.GOOD: "🟢",
    GovernanceCategory.NEEDS_IMPROVEMENT: "🟡",
    GovernanceCategory.POOR: "🔴",
}


def format_compliance_report(result: ComplianceResult) -> str:
    """Format a :class:`ComplianceResult` as a human-readable markdown report.

    Parameters
    ----------
    result:
        The compliance result to format.

    Returns
    -------
    str
        Markdown-formatted governance compliance report.
    """
    category_emoji = _CATEGORY_EMOJI.get(result.category, "")
    lines: list[str] = [
        f"## Governance Report: {result.api_name} (`{result.api_id}`)",
        "",
        f"**Governance Score: {result.score:.0f} / 100 — {category_emoji} {result.category}**",
        "",
    ]

    failing = result.failing_rules
    passing = result.passing_rules

    if failing:
        lines.append("### ❌ Failing Rules")
        lines.append("")
        lines.append("| Severity | Rule | Remediation |")
        lines.append("|----------|------|-------------|")
        # Sort by severity weight descending (critical first)
        _severity_order = {RuleSeverity.CRITICAL: 0, RuleSeverity.WARNING: 1, RuleSeverity.INFO: 2}
        for r in sorted(failing, key=lambda x: _severity_order[x.severity]):
            emoji = _SEVERITY_EMOJI.get(r.severity, "")
            remediation = r.remediation.replace("|", "\\|")
            lines.append(f"| {emoji} {r.severity.capitalize()} | {r.rule_name} | {remediation} |")
        lines.append("")

    if passing:
        lines.append("### ✅ Passing Rules")
        lines.append("")
        for r in passing:
            lines.append(f"- {r.rule_name}")
        lines.append("")

    if failing:
        lines.append("### Remediation Plan")
        lines.append("")
        _severity_order = {RuleSeverity.CRITICAL: 0, RuleSeverity.WARNING: 1, RuleSeverity.INFO: 2}
        for i, r in enumerate(sorted(failing, key=lambda x: _severity_order[x.severity]), start=1):
            emoji = _SEVERITY_EMOJI.get(r.severity, "")
            lines.append(f"{i}. **[{r.severity.capitalize()}]** {r.remediation}")
        lines.append("")

    return "\n".join(lines)


def format_score_summary(api_id: str, result: ComplianceResult) -> str:
    """Format a brief governance score summary for an API.

    Parameters
    ----------
    api_id:
        The API identifier.
    result:
        The compliance result to summarise.

    Returns
    -------
    str
        Single-line markdown summary.
    """
    category_emoji = _CATEGORY_EMOJI.get(result.category, "")
    failing_critical = len(result.critical_failures)
    total_failing = len(result.failing_rules)
    return (
        f"**{result.api_name}** (`{api_id}`): "
        f"Score {result.score:.0f}/100 — {category_emoji} {result.category} "
        f"({total_failing} failing rule(s), {failing_critical} critical)"
    )
