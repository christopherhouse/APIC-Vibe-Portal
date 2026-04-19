"""Tests for governance rules and the ComplianceChecker."""

from __future__ import annotations

import pytest

from apic_vibe_portal_bff.agents.governance_agent.rules.governance_rules import (
    _SEMVER_RE,
    DEFAULT_RULES,
    GovernanceRule,
    RuleSeverity,
    _auth_mentioned_in_description,
    _deprecated_has_sunset,
    _has_contacts,
    _has_deployments,
    _has_description,
    _has_external_docs,
    _has_license,
    _has_meaningful_title,
    _has_security_contact,
    _has_specification,
    _has_tags,
    _has_version,
    _production_has_contact,
    _version_follows_semver,
)

# ---------------------------------------------------------------------------
# Fixtures — reusable API dicts
# ---------------------------------------------------------------------------

FULL_COMPLIANT_API: dict = {
    "name": "payments-api",
    "title": "Payments Processing API",
    "kind": "REST",
    "lifecycleStage": "Production",
    "description": "Handles payment processing using OAuth 2.0 bearer token authentication.",
    "contacts": [{"name": "Payments Team", "email": "payments@example.com"}],
    "license": "Proprietary",
    "externalDocs": [{"url": "https://docs.example.com/payments", "title": "Payments Docs"}],
    "customProperties": {"tags": ["payments", "finance"]},
    "versions": [
        {
            "name": "v1",
            "lifecycleStage": "Production",
            "specifications": [{"name": "openapi"}],
        }
    ],
    "deployments": [{"name": "prod", "server": {"runtimeUri": ["https://api.example.com/payments"]}}],
}

MINIMAL_API: dict = {
    "name": "minimal-api",
    "title": "minimal-api",
    "kind": "REST",
    "lifecycleStage": "Development",
}

DEPRECATED_WITH_SUNSET: dict = {
    "name": "legacy-api",
    "title": "Legacy API",
    "kind": "REST",
    "lifecycleStage": "Deprecated",
    "description": "Old legacy API using API key authentication.",
    "contacts": [{"name": "Platform Team", "email": "platform@example.com"}],
    "customProperties": {"sunsetDate": "2025-12-31"},
    "versions": [{"name": "v1", "lifecycleStage": "Deprecated", "specifications": [{"name": "openapi"}]}],
    "deployments": [],
}

DEPRECATED_WITHOUT_SUNSET: dict = {
    "name": "old-api",
    "title": "Old API",
    "kind": "REST",
    "lifecycleStage": "Deprecated",
    "description": "Old API.",
    "contacts": [],
    "customProperties": {},
    "versions": [],
    "deployments": [],
}


# ---------------------------------------------------------------------------
# Semver regex
# ---------------------------------------------------------------------------


class TestSemverRegex:
    @pytest.mark.parametrize(
        "version",
        ["v1", "v1.2", "v1.2.3", "1.0", "1.0.0", "2.0.0-beta", "v3.1.0-rc1"],
    )
    def test_matches_valid_semver(self, version):
        assert _SEMVER_RE.match(version) is not None

    @pytest.mark.parametrize("version", ["", "abc", "version-one", "latest", "main"])
    def test_rejects_non_semver(self, version):
        assert _SEMVER_RE.match(version) is None


# ---------------------------------------------------------------------------
# Individual rule predicates
# ---------------------------------------------------------------------------


class TestHasDescription:
    def test_passes_with_description(self):
        assert _has_description({"description": "A useful API."}) is True

    def test_fails_with_empty_string(self):
        assert _has_description({"description": ""}) is False

    def test_fails_with_whitespace_only(self):
        assert _has_description({"description": "   "}) is False

    def test_fails_with_missing_key(self):
        assert _has_description({}) is False

    def test_fails_with_none(self):
        assert _has_description({"description": None}) is False


class TestHasContacts:
    def test_passes_with_contact(self):
        assert _has_contacts({"contacts": [{"name": "Team", "email": "team@example.com"}]}) is True

    def test_fails_with_empty_list(self):
        assert _has_contacts({"contacts": []}) is False

    def test_fails_with_missing_key(self):
        assert _has_contacts({}) is False

    def test_fails_with_none(self):
        assert _has_contacts({"contacts": None}) is False


class TestHasLicense:
    def test_passes_with_direct_license(self):
        assert _has_license({"license": "MIT"}) is True

    def test_passes_with_custom_property_license(self):
        assert _has_license({"customProperties": {"license": "Apache-2.0"}}) is True

    def test_passes_with_uppercase_custom_property(self):
        assert _has_license({"customProperties": {"License": "Proprietary"}}) is True

    def test_fails_with_no_license(self):
        assert _has_license({}) is False

    def test_fails_with_empty_custom_properties(self):
        assert _has_license({"customProperties": {}}) is False


class TestHasTags:
    def test_passes_with_tags(self):
        assert _has_tags({"customProperties": {"tags": ["finance", "payments"]}}) is True

    def test_passes_with_uppercase_tags(self):
        assert _has_tags({"customProperties": {"Tags": ["internal"]}}) is True

    def test_fails_with_empty_tags(self):
        assert _has_tags({"customProperties": {"tags": []}}) is False

    def test_fails_with_no_custom_properties(self):
        assert _has_tags({}) is False


class TestHasVersion:
    def test_passes_with_versions(self):
        assert _has_version({"versions": [{"name": "v1"}]}) is True

    def test_fails_with_empty_list(self):
        assert _has_version({"versions": []}) is False

    def test_fails_with_missing_key(self):
        assert _has_version({}) is False


class TestVersionFollowsSemver:
    def test_passes_with_semver_version_name(self):
        assert _version_follows_semver({"versions": [{"name": "v1"}]}) is True

    def test_passes_with_multiple_versions_one_semver(self):
        api = {"versions": [{"name": "latest"}, {"name": "v2.1.0"}]}
        assert _version_follows_semver(api) is True

    def test_fails_with_no_semver_versions(self):
        api = {"versions": [{"name": "latest"}, {"name": "main"}, {"name": "current"}]}
        assert _version_follows_semver(api) is False

    def test_fails_with_empty_versions(self):
        assert _version_follows_semver({"versions": []}) is False

    def test_fails_with_no_versions_key(self):
        assert _version_follows_semver({}) is False

    def test_uses_title_fallback(self):
        api = {"versions": [{"title": "v3.0"}]}
        assert _version_follows_semver(api) is True


class TestHasSpecification:
    def test_passes_with_spec_in_version(self):
        api = {"versions": [{"name": "v1", "specifications": [{"name": "openapi"}]}]}
        assert _has_specification(api) is True

    def test_fails_with_version_but_no_spec(self):
        api = {"versions": [{"name": "v1", "specifications": []}]}
        assert _has_specification(api) is False

    def test_passes_with_has_specification_flag(self):
        assert _has_specification({"hasSpecification": True}) is True

    def test_fails_with_no_versions(self):
        assert _has_specification({}) is False


class TestHasDeployments:
    def test_passes_with_deployments(self):
        assert _has_deployments({"deployments": [{"name": "prod"}]}) is True

    def test_fails_with_empty_deployments(self):
        assert _has_deployments({"deployments": []}) is False

    def test_fails_with_missing_key(self):
        assert _has_deployments({}) is False


class TestDeprecatedHasSunset:
    def test_passes_for_non_deprecated_api(self):
        assert _deprecated_has_sunset({"lifecycleStage": "Production"}) is True

    def test_passes_for_deprecated_with_sunset(self):
        assert _deprecated_has_sunset(DEPRECATED_WITH_SUNSET) is True

    def test_fails_for_deprecated_without_sunset(self):
        assert _deprecated_has_sunset(DEPRECATED_WITHOUT_SUNSET) is False

    def test_passes_for_deprecated_with_snake_case_sunset(self):
        api = {"lifecycleStage": "Deprecated", "customProperties": {"sunset_date": "2026-01-01"}}
        assert _deprecated_has_sunset(api) is True

    def test_passes_for_deprecated_with_uppercase_sunset(self):
        api = {"lifecycleStage": "Deprecated", "customProperties": {"SunsetDate": "2026-01-01"}}
        assert _deprecated_has_sunset(api) is True

    def test_passes_when_no_lifecycle(self):
        # No lifecycleStage key — not deprecated, so rule doesn't apply
        assert _deprecated_has_sunset({}) is True


class TestProductionHasContact:
    def test_passes_for_non_production_api(self):
        assert _production_has_contact({"lifecycleStage": "Development"}) is True

    def test_passes_for_production_with_contact(self):
        api = {"lifecycleStage": "Production", "contacts": [{"name": "Team"}]}
        assert _production_has_contact(api) is True

    def test_fails_for_production_without_contact(self):
        api = {"lifecycleStage": "Production", "contacts": []}
        assert _production_has_contact(api) is False

    def test_fails_for_production_missing_contacts(self):
        api = {"lifecycleStage": "Production"}
        assert _production_has_contact(api) is False


class TestAuthMentionedInDescription:
    @pytest.mark.parametrize(
        "desc",
        [
            "Uses OAuth 2.0 for authentication.",
            "Requires a Bearer token.",
            "Authentication is via JWT.",
            "Protected by an API key.",
            "Requires an apikey in headers.",
        ],
    )
    def test_passes_with_auth_keyword(self, desc):
        assert _auth_mentioned_in_description({"description": desc}) is True

    def test_fails_with_no_auth_keywords(self):
        assert _auth_mentioned_in_description({"description": "Provides weather data."}) is False

    def test_fails_with_empty_description(self):
        assert _auth_mentioned_in_description({"description": ""}) is False

    def test_fails_with_missing_description(self):
        assert _auth_mentioned_in_description({}) is False


class TestHasSecurityContact:
    def test_passes_with_security_in_name(self):
        api = {"contacts": [{"name": "Security Team", "email": "sec@example.com"}]}
        assert _has_security_contact(api) is True

    def test_passes_with_security_in_email(self):
        api = {"contacts": [{"name": "Platform", "email": "security@example.com"}]}
        assert _has_security_contact(api) is True

    def test_fails_with_no_security_contact(self):
        api = {"contacts": [{"name": "Payments Team", "email": "payments@example.com"}]}
        assert _has_security_contact(api) is False

    def test_fails_with_no_contacts(self):
        assert _has_security_contact({"contacts": []}) is False


class TestHasExternalDocs:
    def test_passes_with_external_docs(self):
        api = {"externalDocs": [{"url": "https://docs.example.com", "title": "Docs"}]}
        assert _has_external_docs(api) is True

    def test_fails_with_empty_external_docs(self):
        assert _has_external_docs({"externalDocs": []}) is False

    def test_fails_with_missing_key(self):
        assert _has_external_docs({}) is False


class TestHasMeaningfulTitle:
    def test_passes_when_title_differs_from_name(self):
        assert _has_meaningful_title({"name": "payments-api", "title": "Payments Processing API"}) is True

    def test_fails_when_title_equals_name(self):
        assert _has_meaningful_title({"name": "payments-api", "title": "payments-api"}) is False

    def test_fails_when_title_equals_name_case_insensitive(self):
        assert _has_meaningful_title({"name": "PAYMENTS-API", "title": "payments-api"}) is False

    def test_fails_with_empty_title(self):
        assert _has_meaningful_title({"name": "api", "title": ""}) is False

    def test_passes_when_only_title_set(self):
        assert _has_meaningful_title({"title": "Great API"}) is True


# ---------------------------------------------------------------------------
# GovernanceRule class
# ---------------------------------------------------------------------------


class TestGovernanceRule:
    def test_evaluate_returns_pass(self):
        rule = GovernanceRule(
            rule_id="test.pass",
            name="Test Pass Rule",
            description="Always passes.",
            severity=RuleSeverity.WARNING,
            remediation="Not needed.",
            check_fn=lambda api: True,
        )
        result = rule.evaluate({"name": "my-api"})
        assert result.passed is True
        assert result.rule_id == "test.pass"
        assert result.severity == RuleSeverity.WARNING
        assert result.remediation == ""  # No remediation when passing

    def test_evaluate_returns_fail(self):
        rule = GovernanceRule(
            rule_id="test.fail",
            name="Test Fail Rule",
            description="Always fails.",
            severity=RuleSeverity.CRITICAL,
            remediation="Fix it.",
            check_fn=lambda api: False,
        )
        result = rule.evaluate({})
        assert result.passed is False
        assert result.remediation == "Fix it."

    def test_evaluate_passes_api_dict_to_check_fn(self):
        received: list = []

        def capture(api):
            received.append(api)
            return True

        rule = GovernanceRule(
            rule_id="test.capture",
            name="Capture",
            description="Captures the API dict.",
            severity=RuleSeverity.INFO,
            remediation="",
            check_fn=capture,
        )
        api = {"name": "some-api"}
        rule.evaluate(api)
        assert received == [api]

    def test_evaluate_message_contains_pass(self):
        rule = GovernanceRule(
            rule_id="r",
            name="R",
            description="D",
            severity=RuleSeverity.INFO,
            remediation="",
            check_fn=lambda a: True,
        )
        result = rule.evaluate({})
        assert "PASS" in result.message

    def test_evaluate_message_contains_fail(self):
        rule = GovernanceRule(
            rule_id="r",
            name="R",
            description="D",
            severity=RuleSeverity.INFO,
            remediation="",
            check_fn=lambda a: False,
        )
        result = rule.evaluate({})
        assert "FAIL" in result.message


# ---------------------------------------------------------------------------
# DEFAULT_RULES
# ---------------------------------------------------------------------------


class TestDefaultRules:
    def test_default_rules_is_nonempty(self):
        assert len(DEFAULT_RULES) > 0

    def test_all_rules_have_unique_ids(self):
        ids = [r.rule_id for r in DEFAULT_RULES]
        assert len(ids) == len(set(ids))

    def test_all_rules_have_valid_severity(self):
        for rule in DEFAULT_RULES:
            assert rule.severity in (RuleSeverity.CRITICAL, RuleSeverity.WARNING, RuleSeverity.INFO)

    def test_all_rules_have_remediation(self):
        for rule in DEFAULT_RULES:
            assert rule.remediation.strip(), f"Rule {rule.rule_id} has no remediation guidance"

    def test_compliant_api_passes_most_rules(self):
        results = [rule.evaluate(FULL_COMPLIANT_API) for rule in DEFAULT_RULES]
        passing = [r for r in results if r.passed]
        # A well-formed API should pass the majority of rules
        assert len(passing) >= len(results) * 0.7

    def test_minimal_api_fails_most_rules(self):
        results = [rule.evaluate(MINIMAL_API) for rule in DEFAULT_RULES]
        failing = [r for r in results if not r.passed]
        # A bare-minimum API should fail several rules
        assert len(failing) >= 3

    def test_rule_categories_present(self):
        rule_ids = {r.rule_id for r in DEFAULT_RULES}
        expected_prefixes = {"metadata.", "versioning.", "spec.", "lifecycle.", "security.", "documentation."}
        found_prefixes = {rid.split(".")[0] + "." for rid in rule_ids}
        assert expected_prefixes.issubset(found_prefixes)
