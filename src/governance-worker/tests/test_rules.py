"""Tests for governance_worker.rules — ComplianceChecker, GovernanceRule, DEFAULT_RULES."""

from __future__ import annotations

import pytest

from governance_worker.rules import (
    DEFAULT_RULES,
    ComplianceChecker,
    ComplianceResult,
    GovernanceCategory,
    GovernanceRule,
    RuleSeverity,
)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _api(**kwargs) -> dict:
    """Build a minimal API dict with sane defaults."""
    base = {
        "name": "test-api",
        "title": "Test API",
        "description": "A test API that uses oauth authentication.",
        "contacts": [{"name": "team", "email": "team@example.com"}],
        "lifecycleStage": "design",
        "versions": [{"name": "v1.0.0", "specifications": [{"name": "openapi"}]}],
        "deployments": [{"name": "prod-deploy", "server": {"runtimeUri": "https://api.example.com"}}],
        "externalDocs": [{"url": "https://docs.example.com"}],
        "customProperties": {"tags": ["payments"], "license": "Proprietary"},
    }
    base.update(kwargs)
    return base


# ---------------------------------------------------------------------------
# GovernanceRule.evaluate
# ---------------------------------------------------------------------------


class TestGovernanceRuleEvaluate:
    def test_passing_rule_returns_passed_true(self):
        rule = GovernanceRule(
            rule_id="test.rule",
            name="Test Rule",
            description="desc",
            severity=RuleSeverity.WARNING,
            remediation="fix it",
            check_fn=lambda api: True,
        )
        result = rule.evaluate({})
        assert result.passed is True
        assert result.remediation == ""
        assert "PASS" in result.message

    def test_failing_rule_returns_passed_false_with_remediation(self):
        rule = GovernanceRule(
            rule_id="test.rule",
            name="Test Rule",
            description="desc",
            severity=RuleSeverity.CRITICAL,
            remediation="Add the thing",
            check_fn=lambda api: False,
        )
        result = rule.evaluate({})
        assert result.passed is False
        assert result.remediation == "Add the thing"
        assert "FAIL" in result.message

    def test_check_fn_exception_propagates(self):
        def bad_fn(api):
            raise ValueError("boom")

        rule = GovernanceRule(
            rule_id="bad.rule",
            name="Bad Rule",
            description="desc",
            severity=RuleSeverity.INFO,
            remediation="",
            check_fn=bad_fn,
        )
        with pytest.raises(ValueError, match="boom"):
            rule.evaluate({})


# ---------------------------------------------------------------------------
# ComplianceChecker
# ---------------------------------------------------------------------------


class TestComplianceChecker:
    def test_check_api_returns_compliance_result(self):
        checker = ComplianceChecker()
        result = checker.check_api(_api())
        assert isinstance(result, ComplianceResult)

    def test_all_pass_gives_100_score(self):
        always_pass = GovernanceRule(
            rule_id="x.pass",
            name="Pass",
            description="",
            severity=RuleSeverity.CRITICAL,
            remediation="",
            check_fn=lambda api: True,
        )
        checker = ComplianceChecker(rules=[always_pass])
        result = checker.check_api(_api())
        assert result.score == 100.0
        assert result.category == GovernanceCategory.EXCELLENT

    def test_all_fail_gives_0_score(self):
        always_fail = GovernanceRule(
            rule_id="x.fail",
            name="Fail",
            description="",
            severity=RuleSeverity.CRITICAL,
            remediation="fix",
            check_fn=lambda api: False,
        )
        checker = ComplianceChecker(rules=[always_fail])
        result = checker.check_api(_api())
        assert result.score == 0.0
        assert result.category == GovernanceCategory.POOR

    def test_empty_rules_gives_100_score(self):
        checker = ComplianceChecker(rules=[])
        result = checker.check_api(_api())
        assert result.score == 100.0

    def test_category_thresholds(self):
        def _make_checker(score_target: float) -> ComplianceResult:
            # Create rules that produce the desired score using only WARNING (weight=2) rules
            # n_pass / n_total * 100 = score_target  → n_pass = n_total * score_target / 100
            n_total = 100
            n_pass = int(n_total * score_target / 100)
            rules = [
                GovernanceRule(
                    rule_id=f"r.{i}",
                    name=f"Rule {i}",
                    description="",
                    severity=RuleSeverity.WARNING,
                    remediation="",
                    check_fn=(lambda _i: lambda api: _i < n_pass)(i),
                )
                for i in range(n_total)
            ]
            return ComplianceChecker(rules=rules).check_api({})

        assert _make_checker(95).category == GovernanceCategory.EXCELLENT
        assert _make_checker(80).category == GovernanceCategory.GOOD
        assert _make_checker(60).category == GovernanceCategory.NEEDS_IMPROVEMENT
        assert _make_checker(30).category == GovernanceCategory.POOR

    def test_severity_weighting(self):
        """Critical rules should count 3x, warning 2x, info 1x."""
        rules = [
            GovernanceRule("c.fail", "C Fail", "", RuleSeverity.CRITICAL, "", lambda api: False),
            GovernanceRule("w.pass", "W Pass", "", RuleSeverity.WARNING, "", lambda api: True),
            GovernanceRule("i.pass", "I Pass", "", RuleSeverity.INFO, "", lambda api: True),
        ]
        # weights: critical=3 (fail), warning=2 (pass), info=1 (pass)
        # total = 6, passed = 3  →  score = 3/6*100 = 50.0
        checker = ComplianceChecker(rules=rules)
        result = checker.check_api({})
        assert result.score == 50.0

    def test_api_id_and_name_extracted(self):
        checker = ComplianceChecker(rules=[])
        api = {"name": "my-api", "title": "My API"}
        result = checker.check_api(api)
        assert result.api_id == "my-api"
        assert result.api_name == "My API"

    def test_api_name_fallback_when_no_title(self):
        checker = ComplianceChecker(rules=[])
        api = {"name": "raw-name"}
        result = checker.check_api(api)
        assert result.api_name == "raw-name"

    def test_failing_rules_property(self):
        rules = [
            GovernanceRule("a.pass", "Pass", "", RuleSeverity.WARNING, "", lambda api: True),
            GovernanceRule("b.fail", "Fail", "", RuleSeverity.CRITICAL, "fix", lambda api: False),
        ]
        checker = ComplianceChecker(rules=rules)
        result = checker.check_api({})
        assert len(result.failing_rules) == 1
        assert result.failing_rules[0].rule_id == "b.fail"


# ---------------------------------------------------------------------------
# DEFAULT_RULES coverage
# ---------------------------------------------------------------------------


class TestDefaultRules:
    def test_default_rules_count(self):
        assert len(DEFAULT_RULES) == 13

    def test_all_default_rule_ids_unique(self):
        ids = [r.rule_id for r in DEFAULT_RULES]
        assert len(ids) == len(set(ids))

    def test_perfect_api_passes_all_rules(self):
        checker = ComplianceChecker()
        result = checker.check_api(_api())
        assert result.score == 100.0
        assert len(result.failing_rules) == 0

    def test_empty_api_fails_critical_rules(self):
        checker = ComplianceChecker()
        result = checker.check_api({})
        critical_failures = [r for r in result.failing_rules if r.severity == RuleSeverity.CRITICAL]
        assert len(critical_failures) > 0

    # -- metadata rules -------------------------------------------------------

    def test_missing_description_fails(self):
        checker = ComplianceChecker()
        result = checker.check_api(_api(description=""))
        failing_ids = {r.rule_id for r in result.failing_rules}
        assert "metadata.description" in failing_ids

    def test_missing_contacts_fails(self):
        checker = ComplianceChecker()
        result = checker.check_api(_api(contacts=[]))
        failing_ids = {r.rule_id for r in result.failing_rules}
        assert "metadata.contacts" in failing_ids

    def test_missing_license_fails_info(self):
        checker = ComplianceChecker()
        api = _api()
        api.pop("customProperties", None)
        result = checker.check_api(api)
        failing_ids = {r.rule_id for r in result.failing_rules}
        assert "metadata.license" in failing_ids

    def test_license_in_custom_properties_passes(self):
        checker = ComplianceChecker()
        result = checker.check_api(_api(customProperties={"license": "MIT", "tags": ["x"]}))
        failing_ids = {r.rule_id for r in result.failing_rules}
        assert "metadata.license" not in failing_ids

    def test_missing_tags_fails(self):
        checker = ComplianceChecker()
        result = checker.check_api(_api(customProperties={}))
        failing_ids = {r.rule_id for r in result.failing_rules}
        assert "metadata.tags" in failing_ids

    # -- versioning rules -----------------------------------------------------

    def test_no_versions_fails_has_version(self):
        checker = ComplianceChecker()
        result = checker.check_api(_api(versions=[]))
        failing_ids = {r.rule_id for r in result.failing_rules}
        assert "versioning.has_version" in failing_ids

    def test_non_semver_version_fails(self):
        checker = ComplianceChecker()
        result = checker.check_api(_api(versions=[{"name": "latest"}]))
        failing_ids = {r.rule_id for r in result.failing_rules}
        assert "versioning.semver" in failing_ids

    def test_semver_version_passes(self):
        checker = ComplianceChecker()
        for version_name in ("v1", "v1.2", "1.0.0", "v2.3.4-rc1"):
            result = checker.check_api(_api(versions=[{"name": version_name}]))
            failing_ids = {r.rule_id for r in result.failing_rules}
            assert "versioning.semver" not in failing_ids, f"Expected {version_name} to pass semver rule"

    # -- spec rules -----------------------------------------------------------

    def test_no_specification_fails(self):
        checker = ComplianceChecker()
        result = checker.check_api(_api(versions=[{"name": "v1", "specifications": []}]))
        failing_ids = {r.rule_id for r in result.failing_rules}
        assert "spec.has_specification" in failing_ids

    def test_no_deployments_fails(self):
        checker = ComplianceChecker()
        result = checker.check_api(_api(deployments=[]))
        failing_ids = {r.rule_id for r in result.failing_rules}
        assert "spec.has_deployments" in failing_ids

    # -- lifecycle rules ------------------------------------------------------

    def test_deprecated_without_sunset_fails(self):
        checker = ComplianceChecker()
        result = checker.check_api(_api(lifecycleStage="deprecated", customProperties={}))
        failing_ids = {r.rule_id for r in result.failing_rules}
        assert "lifecycle.deprecated_has_sunset" in failing_ids

    def test_deprecated_with_sunset_passes(self):
        checker = ComplianceChecker()
        result = checker.check_api(
            _api(lifecycleStage="deprecated", customProperties={"sunsetDate": "2025-12-31", "tags": ["x"]})
        )
        failing_ids = {r.rule_id for r in result.failing_rules}
        assert "lifecycle.deprecated_has_sunset" not in failing_ids

    def test_non_deprecated_passes_sunset_rule(self):
        checker = ComplianceChecker()
        result = checker.check_api(_api(lifecycleStage="design", customProperties={"tags": ["x"]}))
        failing_ids = {r.rule_id for r in result.failing_rules}
        assert "lifecycle.deprecated_has_sunset" not in failing_ids

    def test_production_without_contact_fails(self):
        checker = ComplianceChecker()
        result = checker.check_api(_api(lifecycleStage="production", contacts=[]))
        failing_ids = {r.rule_id for r in result.failing_rules}
        assert "lifecycle.production_has_contact" in failing_ids

    def test_production_with_contact_passes(self):
        checker = ComplianceChecker()
        result = checker.check_api(_api(lifecycleStage="production"))
        failing_ids = {r.rule_id for r in result.failing_rules}
        assert "lifecycle.production_has_contact" not in failing_ids

    # -- security rules -------------------------------------------------------

    def test_no_auth_in_description_fails(self):
        checker = ComplianceChecker()
        result = checker.check_api(_api(description="A simple API."))
        failing_ids = {r.rule_id for r in result.failing_rules}
        assert "security.auth_in_description" in failing_ids

    def test_auth_keyword_in_description_passes(self):
        checker = ComplianceChecker()
        for keyword in ("oauth", "API Key", "JWT", "Bearer", "authentication required"):
            api = _api(description=f"This API uses {keyword}.")
            result = checker.check_api(api)
            failing_ids = {r.rule_id for r in result.failing_rules}
            assert "security.auth_in_description" not in failing_ids, f"Expected '{keyword}' to pass"

    # -- documentation rules --------------------------------------------------

    def test_no_external_docs_fails_info(self):
        checker = ComplianceChecker()
        result = checker.check_api(_api(externalDocs=[]))
        failing_ids = {r.rule_id for r in result.failing_rules}
        assert "documentation.external_docs" in failing_ids

    def test_title_same_as_name_fails(self):
        checker = ComplianceChecker()
        result = checker.check_api(_api(name="my-api", title="my-api"))
        failing_ids = {r.rule_id for r in result.failing_rules}
        assert "documentation.meaningful_title" in failing_ids

    def test_distinct_title_passes(self):
        checker = ComplianceChecker()
        result = checker.check_api(_api(name="my-api", title="My Payments API"))
        failing_ids = {r.rule_id for r in result.failing_rules}
        assert "documentation.meaningful_title" not in failing_ids
