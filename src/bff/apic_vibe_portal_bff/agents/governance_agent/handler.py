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


def _fmt_score(score: float) -> str:
    """Format a governance score for display without rounding artefacts.

    Returns the score as an integer string when the value is whole (e.g. ``85``),
    or with one decimal place when it is fractional (e.g. ``89.9``).

    Using ``:.0f`` would round 89.9 → 90 and make the displayed score disagree
    with the ``Good`` category label (threshold ≥ 90 → Excellent).  This helper
    avoids that inconsistency while keeping clean output for whole-number scores.
    """
    rounded = round(score, 1)
    return str(int(rounded)) if rounded == int(rounded) else f"{rounded:.1f}"


def get_category_emoji(category: GovernanceCategory) -> str:
    """Return the emoji for a :class:`GovernanceCategory`.

    Parameters
    ----------
    category:
        The governance category to look up.

    Returns
    -------
    str
        A single emoji character representing the category.
    """
    return _CATEGORY_EMOJI.get(category, "")


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
    category_emoji = get_category_emoji(result.category)
    lines: list[str] = [
        f"## Governance Report: {result.api_name} (`{result.api_id}`)",
        "",
        f"**Governance Score: {_fmt_score(result.score)} / 100 — {category_emoji} {result.category}**",
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
    category_emoji = get_category_emoji(result.category)
    failing_critical = len(result.critical_failures)
    total_failing = len(result.failing_rules)
    return (
        f"**{result.api_name}** (`{api_id}`): "
        f"Score {_fmt_score(result.score)}/100 — {category_emoji} {result.category} "
        f"({total_failing} failing rule(s), {failing_critical} critical)"
    )
