"""Governance rule definitions for the APIC Vibe Portal Governance Agent.

Each rule is a :class:`GovernanceRule` instance that evaluates an API
definition dict and returns a :class:`RuleResult` indicating whether the
API passes or fails the rule, along with remediation guidance for failures.

API definition dicts are expected to use the camelCase field names returned
by the ``ApiCenterClient`` (e.g. ``lifecycleStage``, ``externalDocs``).
"""

from __future__ import annotations

import re
from collections.abc import Callable
from dataclasses import dataclass
from enum import StrEnum
from typing import Any

# ---------------------------------------------------------------------------
# Severity & result types
# ---------------------------------------------------------------------------


class RuleSeverity(StrEnum):
    """Severity of a governance rule violation."""

    CRITICAL = "critical"
    WARNING = "warning"
    INFO = "info"


@dataclass
class RuleResult:
    """Result of evaluating a single governance rule against an API."""

    rule_id: str
    rule_name: str
    passed: bool
    severity: RuleSeverity
    message: str
    remediation: str


# ---------------------------------------------------------------------------
# GovernanceRule
# ---------------------------------------------------------------------------


class GovernanceRule:
    """A configurable governance rule with an evaluation function.

    Parameters
    ----------
    rule_id:
        Unique dot-separated identifier (e.g. ``"metadata.description"``).
    name:
        Human-readable rule name.
    description:
        Longer description of what the rule checks.
    severity:
        Rule severity — ``critical``, ``warning``, or ``info``.
    remediation:
        Actionable guidance shown when the rule fails.
    check_fn:
        A callable ``(api: dict[str, Any]) -> bool`` that returns ``True``
        when the API passes the rule.
    """

    def __init__(
        self,
        rule_id: str,
        name: str,
        description: str,
        severity: RuleSeverity,
        remediation: str,
        check_fn: Callable[[dict[str, Any]], bool],
    ) -> None:
        self.rule_id = rule_id
        self.name = name
        self.description = description
        self.severity = severity
        self.remediation = remediation
        self._check = check_fn

    def evaluate(self, api: dict[str, Any]) -> RuleResult:
        """Evaluate the rule against *api* and return a :class:`RuleResult`.

        Parameters
        ----------
        api:
            API definition dict as returned by ``ApiCenterClient.get_api()``,
            optionally extended with ``versions`` and ``deployments`` lists.
        """
        passed = bool(self._check(api))
        message = f"PASS: {self.name}" if passed else f"FAIL: {self.name}"
        return RuleResult(
            rule_id=self.rule_id,
            rule_name=self.name,
            passed=passed,
            severity=self.severity,
            message=message,
            remediation="" if passed else self.remediation,
        )


# ---------------------------------------------------------------------------
# Helper predicates
# ---------------------------------------------------------------------------

_SEMVER_RE = re.compile(
    r"^v?(\d+)(?:\.(\d+)(?:\.(\d+))?)?(?:[.-][a-zA-Z0-9]+)*$",
    re.IGNORECASE,
)

_AUTH_KEYWORDS = frozenset(
    {
        "auth",
        "authentication",
        "authorization",
        "oauth",
        "apikey",
        "api-key",
        "api_key",
        "api key",
        "bearer",
        "jwt",
        "token",
        "basic",
        "hmac",
        "secret",
        "credential",
    }
)


def _has_description(api: dict[str, Any]) -> bool:
    desc = api.get("description", "") or ""
    return len(desc.strip()) > 0


def _has_contacts(api: dict[str, Any]) -> bool:
    contacts = api.get("contacts", []) or []
    return len(contacts) > 0


def _has_license(api: dict[str, Any]) -> bool:
    # Check direct license field or customProperties
    if api.get("license"):
        return True
    custom = api.get("customProperties", {}) or {}
    return bool(custom.get("license") or custom.get("License"))


def _has_tags(api: dict[str, Any]) -> bool:
    custom = api.get("customProperties", {}) or {}
    tags = custom.get("tags") or custom.get("Tags") or []
    return len(tags) > 0


def _has_version(api: dict[str, Any]) -> bool:
    versions = api.get("versions", []) or []
    return len(versions) > 0


def _version_follows_semver(api: dict[str, Any]) -> bool:
    versions = api.get("versions", []) or []
    if not versions:
        return False
    for v in versions:
        name = v.get("name", "") or v.get("title", "") or ""
        if name and _SEMVER_RE.match(name):
            return True
    return False


def _has_specification(api: dict[str, Any]) -> bool:
    # Check if any version has a specification
    versions = api.get("versions", []) or []
    for v in versions:
        specs = v.get("specifications", []) or []
        if specs:
            return True
    # Also accept a top-level "hasSpecification" flag set by the governance tool
    return bool(api.get("hasSpecification", False))


def _has_deployments(api: dict[str, Any]) -> bool:
    deployments = api.get("deployments", []) or []
    return len(deployments) > 0


def _deprecated_has_sunset(api: dict[str, Any]) -> bool:
    lifecycle = (api.get("lifecycleStage") or "").lower()
    if lifecycle != "deprecated":
        return True  # Rule only applies to deprecated APIs
    custom = api.get("customProperties", {}) or {}
    return bool(custom.get("sunsetDate") or custom.get("SunsetDate") or custom.get("sunset_date"))


def _production_has_contact(api: dict[str, Any]) -> bool:
    lifecycle = (api.get("lifecycleStage") or "").lower()
    if lifecycle != "production":
        return True  # Rule only applies to production APIs
    contacts = api.get("contacts", []) or []
    return len(contacts) > 0


def _auth_mentioned_in_description(api: dict[str, Any]) -> bool:
    desc = (api.get("description", "") or "").lower()
    if not desc:
        return False
    return any(kw in desc for kw in _AUTH_KEYWORDS)


def _has_external_docs(api: dict[str, Any]) -> bool:
    docs = api.get("externalDocs", []) or []
    return len(docs) > 0


def _has_meaningful_title(api: dict[str, Any]) -> bool:
    title = (api.get("title", "") or "").strip()
    name = (api.get("name", "") or "").strip()
    # Title is meaningful if it's non-empty and different from the raw name
    return bool(title) and title.lower() != name.lower()


# ---------------------------------------------------------------------------
# Default rule set
# ---------------------------------------------------------------------------

#: Default governance rules evaluated by :class:`ComplianceChecker`.
DEFAULT_RULES: list[GovernanceRule] = [
    # -- Metadata completeness ------------------------------------------------
    GovernanceRule(
        rule_id="metadata.description",
        name="API Description Required",
        description="The API must have a non-empty description explaining its purpose.",
        severity=RuleSeverity.WARNING,
        remediation=(
            "Add a meaningful description to the API in Azure API Center. "
            "The description should explain the API's purpose, capabilities, and target audience."
        ),
        check_fn=_has_description,
    ),
    GovernanceRule(
        rule_id="metadata.contacts",
        name="Contact Information Required",
        description="The API must have at least one contact defined (owner or team).",
        severity=RuleSeverity.WARNING,
        remediation=(
            "Add contact information to the API in Azure API Center. "
            "Include the owning team name and a reachable email address."
        ),
        check_fn=_has_contacts,
    ),
    GovernanceRule(
        rule_id="metadata.license",
        name="License Information Recommended",
        description="The API should specify license terms or usage conditions.",
        severity=RuleSeverity.INFO,
        remediation=(
            "Specify the API license in the API Center metadata or as a custom property. "
            "Common values: 'MIT', 'Apache-2.0', 'Proprietary', 'Internal Use Only'."
        ),
        check_fn=_has_license,
    ),
    GovernanceRule(
        rule_id="metadata.tags",
        name="Tags Recommended",
        description="The API should have tags or custom properties to aid discoverability.",
        severity=RuleSeverity.INFO,
        remediation=(
            "Add tags to the API via custom properties in Azure API Center. "
            "Tags improve searchability and categorization in the portal."
        ),
        check_fn=_has_tags,
    ),
    # -- Versioning -----------------------------------------------------------
    GovernanceRule(
        rule_id="versioning.has_version",
        name="API Must Have at Least One Version",
        description="Every API must have at least one registered version in API Center.",
        severity=RuleSeverity.CRITICAL,
        remediation=(
            "Register at least one version for this API in Azure API Center. "
            "Without a version, consumers cannot reference a stable API contract."
        ),
        check_fn=_has_version,
    ),
    GovernanceRule(
        rule_id="versioning.semver",
        name="Version Should Follow Semantic Versioning",
        description="At least one API version name should follow semantic versioning (e.g. v1, v1.2, 1.0.0).",
        severity=RuleSeverity.INFO,
        remediation=(
            "Rename API versions to follow semantic versioning conventions (e.g. v1, v1.2.0). "
            "Semantic versioning communicates compatibility expectations to API consumers."
        ),
        check_fn=_version_follows_semver,
    ),
    # -- Specification quality ------------------------------------------------
    GovernanceRule(
        rule_id="spec.has_specification",
        name="API Specification Required",
        description="The API must have at least one specification document (OpenAPI, WSDL, etc.).",
        severity=RuleSeverity.CRITICAL,
        remediation=(
            "Upload an API specification document (e.g. OpenAPI/Swagger) to Azure API Center. "
            "A specification document enables automated validation, documentation generation, and SDK creation."
        ),
        check_fn=_has_specification,
    ),
    GovernanceRule(
        rule_id="spec.has_deployments",
        name="API Should Have Deployment Information",
        description="The API should have at least one deployment registered with a runtime URL.",
        severity=RuleSeverity.WARNING,
        remediation=(
            "Register deployment environments and runtime URIs for this API in Azure API Center. "
            "Deployment information helps consumers find the correct endpoint."
        ),
        check_fn=_has_deployments,
    ),
    # -- Lifecycle compliance -------------------------------------------------
    GovernanceRule(
        rule_id="lifecycle.deprecated_has_sunset",
        name="Deprecated API Must Have Sunset Date",
        description="Deprecated APIs must specify a sunset date so consumers can plan migrations.",
        severity=RuleSeverity.WARNING,
        remediation=(
            "Set a 'sunsetDate' custom property on this deprecated API in Azure API Center. "
            "Use ISO-8601 format (e.g. '2025-12-31'). "
            "Communicate the sunset date to all known API consumers."
        ),
        check_fn=_deprecated_has_sunset,
    ),
    GovernanceRule(
        rule_id="lifecycle.production_has_contact",
        name="Production API Must Have Contact Information",
        description="APIs in production must have at least one contact for support and incident escalation.",
        severity=RuleSeverity.CRITICAL,
        remediation=(
            "Add an owner or support contact to this production API in Azure API Center. "
            "Include a team name and a monitored email address."
        ),
        check_fn=_production_has_contact,
    ),
    # -- Security -------------------------------------------------------------
    GovernanceRule(
        rule_id="security.auth_in_description",
        name="Authentication Method Should Be Documented",
        description=("The API description should mention the authentication mechanism (e.g. OAuth 2.0, API Key, JWT)."),
        severity=RuleSeverity.CRITICAL,
        remediation=(
            "Update the API description to include authentication requirements. "
            "Clearly state the supported authentication method(s), required scopes, and "
            "where to obtain credentials."
        ),
        check_fn=_auth_mentioned_in_description,
    ),
    # -- Documentation --------------------------------------------------------
    GovernanceRule(
        rule_id="documentation.external_docs",
        name="External Documentation Recommended",
        description="The API should link to external documentation (e.g. developer portal, wiki).",
        severity=RuleSeverity.INFO,
        remediation=(
            "Add external documentation links to the API in Azure API Center. "
            "Link to a developer portal, Confluence page, or README that provides "
            "integration guides and examples."
        ),
        check_fn=_has_external_docs,
    ),
    GovernanceRule(
        rule_id="documentation.meaningful_title",
        name="API Title Should Be Human-Readable",
        description="The API title should be distinct from the raw API name and human-friendly.",
        severity=RuleSeverity.WARNING,
        remediation=(
            "Set a human-readable title for this API in Azure API Center. "
            "Use a descriptive name (e.g. 'Payments Processing API') rather than a technical slug."
        ),
        check_fn=_has_meaningful_title,
    ),
]
