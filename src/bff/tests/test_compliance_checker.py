"""Tests for ComplianceChecker — score calculation and categorisation."""

from __future__ import annotations

import pytest

from apic_vibe_portal_bff.agents.governance_agent.rules.compliance_checker import (
    SEVERITY_WEIGHTS,
    ComplianceChecker,
    ComplianceResult,
    GovernanceCategory,
)
from apic_vibe_portal_bff.agents.governance_agent.rules.governance_rules import (
    DEFAULT_RULES,
    GovernanceRule,
    RuleResult,
    RuleSeverity,
)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_rule(rule_id: str, severity: RuleSeverity, passes: bool) -> GovernanceRule:
    return GovernanceRule(
        rule_id=rule_id,
        name=f"Rule {rule_id}",
        description="Test rule.",
        severity=severity,
        remediation="Fix it.",
        check_fn=lambda api, _passes=passes: _passes,
    )


# ---------------------------------------------------------------------------
# SEVERITY_WEIGHTS
# ---------------------------------------------------------------------------


class TestSeverityWeights:
    def test_critical_has_highest_weight(self):
        assert SEVERITY_WEIGHTS[RuleSeverity.CRITICAL] > SEVERITY_WEIGHTS[RuleSeverity.WARNING]

    def test_warning_has_higher_weight_than_info(self):
        assert SEVERITY_WEIGHTS[RuleSeverity.WARNING] > SEVERITY_WEIGHTS[RuleSeverity.INFO]

    def test_critical_weight_is_3(self):
        assert SEVERITY_WEIGHTS[RuleSeverity.CRITICAL] == 3

    def test_warning_weight_is_2(self):
        assert SEVERITY_WEIGHTS[RuleSeverity.WARNING] == 2

    def test_info_weight_is_1(self):
        assert SEVERITY_WEIGHTS[RuleSeverity.INFO] == 1


# ---------------------------------------------------------------------------
# GovernanceCategory
# ---------------------------------------------------------------------------


class TestGovernanceCategory:
    def test_all_categories_are_strings(self):
        for cat in GovernanceCategory:
            assert isinstance(str(cat), str)


# ---------------------------------------------------------------------------
# ComplianceChecker._calculate_score
# ---------------------------------------------------------------------------


class TestCalculateScore:
    def test_all_passing_gives_100(self):
        checker = ComplianceChecker(rules=[])
        result = checker._calculate_score([])
        assert result == 100.0

    def test_all_critical_passing_gives_100(self):
        checker = ComplianceChecker()
        results = [
            RuleResult("r1", "R1", True, RuleSeverity.CRITICAL, "PASS: R1", ""),
            RuleResult("r2", "R2", True, RuleSeverity.WARNING, "PASS: R2", ""),
        ]
        score = checker._calculate_score(results)
        assert score == 100.0

    def test_all_failing_gives_0(self):
        checker = ComplianceChecker()
        results = [
            RuleResult("r1", "R1", False, RuleSeverity.CRITICAL, "FAIL: R1", "Fix"),
            RuleResult("r2", "R2", False, RuleSeverity.WARNING, "FAIL: R2", "Fix"),
        ]
        score = checker._calculate_score(results)
        assert score == 0.0

    def test_mixed_results_weighted_correctly(self):
        """1 critical (3) passes, 1 warning (2) fails, 1 info (1) passes.

        passed_weight = 3 + 1 = 4
        total_weight = 3 + 2 + 1 = 6
        score = 4/6 * 100 ≈ 66.7
        """
        checker = ComplianceChecker()
        results = [
            RuleResult("r1", "R1", True, RuleSeverity.CRITICAL, "PASS: R1", ""),  # +3
            RuleResult("r2", "R2", False, RuleSeverity.WARNING, "FAIL: R2", "Fix"),  # +0
            RuleResult("r3", "R3", True, RuleSeverity.INFO, "PASS: R3", ""),  # +1
        ]
        score = checker._calculate_score(results)
        assert score == pytest.approx(66.7, abs=0.1)

    def test_only_critical_failing_lowers_score_most(self):
        checker = ComplianceChecker()
        # Critical fails (weight 3), info and warning pass (weights 1 + 2 = 3)
        results_critical_fail = [
            RuleResult("r1", "R1", False, RuleSeverity.CRITICAL, "FAIL", "Fix"),
            RuleResult("r2", "R2", True, RuleSeverity.WARNING, "PASS", ""),
            RuleResult("r3", "R3", True, RuleSeverity.INFO, "PASS", ""),
        ]
        # Info fails (weight 1), critical and warning pass (weights 3 + 2 = 5)
        results_info_fail = [
            RuleResult("r1", "R1", True, RuleSeverity.CRITICAL, "PASS", ""),
            RuleResult("r2", "R2", True, RuleSeverity.WARNING, "PASS", ""),
            RuleResult("r3", "R3", False, RuleSeverity.INFO, "FAIL", "Fix"),
        ]
        score_critical_fail = checker._calculate_score(results_critical_fail)
        score_info_fail = checker._calculate_score(results_info_fail)
        assert score_critical_fail < score_info_fail

    def test_score_rounded_to_one_decimal(self):
        checker = ComplianceChecker()
        # 2 passing info (1+1=2), 1 failing warning (2), total = 4
        # score = 2/4 * 100 = 50.0
        results = [
            RuleResult("r1", "R1", True, RuleSeverity.INFO, "PASS", ""),
            RuleResult("r2", "R2", True, RuleSeverity.INFO, "PASS", ""),
            RuleResult("r3", "R3", False, RuleSeverity.WARNING, "FAIL", "Fix"),
        ]
        score = checker._calculate_score(results)
        assert score == 50.0


# ---------------------------------------------------------------------------
# ComplianceChecker._categorize
# ---------------------------------------------------------------------------


class TestCategorize:
    def test_score_100_is_excellent(self):
        assert ComplianceChecker()._categorize(100.0) == GovernanceCategory.EXCELLENT

    def test_score_90_is_excellent(self):
        assert ComplianceChecker()._categorize(90.0) == GovernanceCategory.EXCELLENT

    def test_score_89_is_good(self):
        assert ComplianceChecker()._categorize(89.9) == GovernanceCategory.GOOD

    def test_score_75_is_good(self):
        assert ComplianceChecker()._categorize(75.0) == GovernanceCategory.GOOD

    def test_score_74_is_needs_improvement(self):
        assert ComplianceChecker()._categorize(74.9) == GovernanceCategory.NEEDS_IMPROVEMENT

    def test_score_50_is_needs_improvement(self):
        assert ComplianceChecker()._categorize(50.0) == GovernanceCategory.NEEDS_IMPROVEMENT

    def test_score_49_is_poor(self):
        assert ComplianceChecker()._categorize(49.9) == GovernanceCategory.POOR

    def test_score_0_is_poor(self):
        assert ComplianceChecker()._categorize(0.0) == GovernanceCategory.POOR


# ---------------------------------------------------------------------------
# ComplianceChecker.check_api
# ---------------------------------------------------------------------------


class TestCheckApi:
    def test_returns_compliance_result(self):
        checker = ComplianceChecker(rules=[_make_rule("r1", RuleSeverity.CRITICAL, True)])
        api = {"name": "test-api", "title": "Test API"}
        result = checker.check_api(api)
        assert isinstance(result, ComplianceResult)

    def test_api_id_from_name_field(self):
        checker = ComplianceChecker(rules=[_make_rule("r1", RuleSeverity.INFO, True)])
        result = checker.check_api({"name": "my-api", "title": "My API"})
        assert result.api_id == "my-api"

    def test_api_name_from_title_field(self):
        checker = ComplianceChecker(rules=[_make_rule("r1", RuleSeverity.INFO, True)])
        result = checker.check_api({"name": "my-api", "title": "My API"})
        assert result.api_name == "My API"

    def test_api_name_defaults_to_api_id(self):
        checker = ComplianceChecker(rules=[_make_rule("r1", RuleSeverity.INFO, True)])
        result = checker.check_api({"name": "bare-api"})
        assert result.api_name == "bare-api"

    def test_api_id_defaults_to_unknown(self):
        checker = ComplianceChecker(rules=[_make_rule("r1", RuleSeverity.INFO, True)])
        result = checker.check_api({})
        assert result.api_id == "unknown"

    def test_rule_results_count_matches_rules(self):
        rules = [_make_rule(f"r{i}", RuleSeverity.INFO, True) for i in range(5)]
        checker = ComplianceChecker(rules=rules)
        result = checker.check_api({"name": "api"})
        assert len(result.rule_results) == 5

    def test_all_passing_gives_excellent(self):
        rules = [_make_rule("r1", RuleSeverity.CRITICAL, True)]
        checker = ComplianceChecker(rules=rules)
        result = checker.check_api({"name": "api"})
        assert result.score == 100.0
        assert result.category == GovernanceCategory.EXCELLENT

    def test_all_failing_gives_poor(self):
        rules = [
            _make_rule("r1", RuleSeverity.CRITICAL, False),
            _make_rule("r2", RuleSeverity.WARNING, False),
        ]
        checker = ComplianceChecker(rules=rules)
        result = checker.check_api({"name": "api"})
        assert result.score == 0.0
        assert result.category == GovernanceCategory.POOR


# ---------------------------------------------------------------------------
# ComplianceResult properties
# ---------------------------------------------------------------------------


class TestComplianceResult:
    @pytest.fixture
    def mixed_result(self):
        rules = [
            _make_rule("r1", RuleSeverity.CRITICAL, True),
            _make_rule("r2", RuleSeverity.CRITICAL, False),
            _make_rule("r3", RuleSeverity.WARNING, False),
            _make_rule("r4", RuleSeverity.INFO, True),
        ]
        checker = ComplianceChecker(rules=rules)
        return checker.check_api({"name": "api", "title": "API"})

    def test_passing_rules_property(self, mixed_result):
        assert len(mixed_result.passing_rules) == 2
        assert all(r.passed for r in mixed_result.passing_rules)

    def test_failing_rules_property(self, mixed_result):
        assert len(mixed_result.failing_rules) == 2
        assert all(not r.passed for r in mixed_result.failing_rules)

    def test_critical_failures_property(self, mixed_result):
        assert len(mixed_result.critical_failures) == 1
        assert mixed_result.critical_failures[0].severity == RuleSeverity.CRITICAL
        assert not mixed_result.critical_failures[0].passed


# ---------------------------------------------------------------------------
# ComplianceChecker.get_rule
# ---------------------------------------------------------------------------


class TestGetRule:
    def test_returns_rule_by_id(self):
        rules = [_make_rule("metadata.desc", RuleSeverity.WARNING, True)]
        checker = ComplianceChecker(rules=rules)
        rule = checker.get_rule("metadata.desc")
        assert rule is not None
        assert rule.rule_id == "metadata.desc"

    def test_returns_none_for_unknown_id(self):
        checker = ComplianceChecker(rules=[])
        assert checker.get_rule("nonexistent") is None


# ---------------------------------------------------------------------------
# ComplianceChecker with DEFAULT_RULES
# ---------------------------------------------------------------------------


class TestComplianceCheckerWithDefaultRules:
    def test_default_checker_uses_default_rules(self):
        checker = ComplianceChecker()
        assert len(checker.rules) == len(DEFAULT_RULES)

    def test_custom_rules_override_defaults(self):
        custom_rules = [_make_rule("custom.rule", RuleSeverity.INFO, True)]
        checker = ComplianceChecker(rules=custom_rules)
        assert len(checker.rules) == 1

    def test_fully_compliant_api_scores_high(self):
        """A fully described, versioned, and deployed API should score well."""
        api = {
            "name": "payments-api",
            "title": "Payments Processing API",
            "description": "Handles payments using OAuth 2.0 authentication.",
            "lifecycleStage": "Production",
            "contacts": [{"name": "Payments Team", "email": "payments@example.com"}],
            "license": "Proprietary",
            "externalDocs": [{"url": "https://docs.example.com", "title": "Docs"}],
            "customProperties": {"tags": ["payments"]},
            "versions": [
                {
                    "name": "v1",
                    "lifecycleStage": "Production",
                    "specifications": [{"name": "openapi"}],
                }
            ],
            "deployments": [{"name": "prod", "server": {"runtimeUri": ["https://api.example.com"]}}],
        }
        checker = ComplianceChecker()
        result = checker.check_api(api)
        assert result.score >= 75.0

    def test_empty_api_scores_poorly(self):
        checker = ComplianceChecker()
        result = checker.check_api({"name": "empty-api"})
        assert result.score < 50.0

    def test_deprecated_api_without_sunset_fails_relevant_rule(self):
        api = {
            "name": "old-api",
            "title": "Old API",
            "lifecycleStage": "Deprecated",
            "contacts": [{"name": "Team"}],
            "description": "Old API using token auth.",
            "customProperties": {},
            "versions": [],
            "deployments": [],
        }
        checker = ComplianceChecker()
        result = checker.check_api(api)
        failing_ids = {r.rule_id for r in result.failing_rules}
        assert "lifecycle.deprecated_has_sunset" in failing_ids
