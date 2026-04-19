"""Compliance checker — evaluates governance rules and calculates governance scores.

The :class:`ComplianceChecker` applies the full set of :data:`DEFAULT_RULES`
(or a custom rule list) to an API definition dict and returns a
:class:`ComplianceResult` with per-rule outcomes, an overall score, and a
human-readable governance category.

Scoring
-------
Rules are weighted by severity:

- ``critical`` → 3 points
- ``warning``  → 2 points
- ``info``     → 1 point

Score = (sum of weights for passing rules) / (total weight) × 100

Categories:

- **Excellent**  — score ≥ 90
- **Good**       — 75 ≤ score < 90
- **Needs Improvement** — 50 ≤ score < 75
- **Poor**       — score < 50
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
from typing import Any

from apic_vibe_portal_bff.agents.governance_agent.rules.governance_rules import (
    DEFAULT_RULES,
    GovernanceRule,
    RuleResult,
    RuleSeverity,
)

# ---------------------------------------------------------------------------
# Severity weights
# ---------------------------------------------------------------------------

SEVERITY_WEIGHTS: dict[RuleSeverity, int] = {
    RuleSeverity.CRITICAL: 3,
    RuleSeverity.WARNING: 2,
    RuleSeverity.INFO: 1,
}


# ---------------------------------------------------------------------------
# Governance category
# ---------------------------------------------------------------------------


class GovernanceCategory(StrEnum):
    """Human-readable governance compliance category."""

    EXCELLENT = "Excellent"
    GOOD = "Good"
    NEEDS_IMPROVEMENT = "Needs Improvement"
    POOR = "Poor"


# ---------------------------------------------------------------------------
# ComplianceResult
# ---------------------------------------------------------------------------


@dataclass
class ComplianceResult:
    """The result of running all governance rules against a single API.

    Attributes
    ----------
    api_id:
        The API name/identifier.
    api_name:
        The human-readable API title.
    rule_results:
        Ordered list of :class:`~governance_rules.RuleResult` objects,
        one per evaluated rule.
    score:
        Overall governance score (0–100), weighted by rule severity.
    category:
        Human-readable :class:`GovernanceCategory` derived from the score.
    """

    api_id: str
    api_name: str
    rule_results: list[RuleResult]
    score: float
    category: GovernanceCategory

    @property
    def passing_rules(self) -> list[RuleResult]:
        """Rules that the API passes."""
        return [r for r in self.rule_results if r.passed]

    @property
    def failing_rules(self) -> list[RuleResult]:
        """Rules that the API fails."""
        return [r for r in self.rule_results if not r.passed]

    @property
    def critical_failures(self) -> list[RuleResult]:
        """Critical-severity rules that the API fails."""
        return [r for r in self.rule_results if not r.passed and r.severity == RuleSeverity.CRITICAL]


# ---------------------------------------------------------------------------
# ComplianceChecker
# ---------------------------------------------------------------------------


class ComplianceChecker:
    """Evaluates governance rules against API definitions and calculates scores.

    Parameters
    ----------
    rules:
        Optional list of :class:`~governance_rules.GovernanceRule` instances
        to apply.  Defaults to :data:`~governance_rules.DEFAULT_RULES`.
    """

    def __init__(self, rules: list[GovernanceRule] | None = None) -> None:
        self.rules: list[GovernanceRule] = rules if rules is not None else DEFAULT_RULES

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def check_api(self, api: dict[str, Any]) -> ComplianceResult:
        """Run all rules against *api* and return a :class:`ComplianceResult`.

        Parameters
        ----------
        api:
            API definition dict as returned by ``ApiCenterClient.get_api()``,
            optionally extended with a ``versions`` list and ``deployments`` list.
        """
        results = [rule.evaluate(api) for rule in self.rules]
        score = self._calculate_score(results)
        category = self._categorize(score)
        api_id = api.get("name", "unknown")
        api_name = api.get("title", api_id)
        return ComplianceResult(
            api_id=api_id,
            api_name=api_name,
            rule_results=results,
            score=score,
            category=category,
        )

    def get_rule(self, rule_id: str) -> GovernanceRule | None:
        """Return the rule with the given *rule_id*, or ``None`` if not found."""
        for rule in self.rules:
            if rule.rule_id == rule_id:
                return rule
        return None

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _calculate_score(self, results: list[RuleResult]) -> float:
        """Calculate weighted governance score from rule results.

        Returns 100.0 when there are no rules to evaluate.
        """
        total_weight = sum(SEVERITY_WEIGHTS[r.severity] for r in results)
        if total_weight == 0:
            return 100.0
        passed_weight = sum(SEVERITY_WEIGHTS[r.severity] for r in results if r.passed)
        return round(passed_weight / total_weight * 100, 1)

    def _categorize(self, score: float) -> GovernanceCategory:
        """Map a numeric score to a :class:`GovernanceCategory`."""
        if score >= 90:
            return GovernanceCategory.EXCELLENT
        if score >= 75:
            return GovernanceCategory.GOOD
        if score >= 50:
            return GovernanceCategory.NEEDS_IMPROVEMENT
        return GovernanceCategory.POOR
