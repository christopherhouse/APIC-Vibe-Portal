"""System prompt and few-shot examples for the Governance & Compliance Agent."""

from __future__ import annotations

from ..prompts import load_prompt

# Lazy-loaded system prompt from external markdown file
SYSTEM_PROMPT = load_prompt("governance_system")

# Few-shot examples injected into the conversation before user turns.
FEW_SHOT_EXAMPLES: list[dict[str, str]] = [
    {
        "role": "user",
        "content": "Is the payments-api compliant with our governance standards?",
    },
    {
        "role": "assistant",
        "content": (
            "I'll check the compliance status of the payments-api now.\n\n"
            "[Calling: check_api_compliance('payments-api')]\n\n"
            "## Governance Report: payments-api\n\n"
            "**Governance Score: 72 / 100 — Needs Improvement**\n\n"
            "### ❌ Failing Rules\n\n"
            "| Severity | Rule | Remediation |\n"
            "|----------|------|-------------|\n"
            "| 🔴 Critical | Authentication Method Should Be Documented | "
            "Add auth info to the description |\n"
            "| 🟡 Warning | API Should Have Deployment Information | "
            "Register deployment environments |\n\n"
            "### ✅ Passing Rules\n\n"
            "- API Description Required\n"
            "- Contact Information Required\n"
            "- API Must Have at Least One Version\n\n"
            "### Remediation Plan\n\n"
            "1. **[Critical]** Update the API description to mention the authentication method "
            "(e.g. 'Uses OAuth 2.0 with Bearer tokens').\n"
            "2. **[Warning]** Register the production deployment URL in Azure API Center.\n"
        ),
    },
    {
        "role": "user",
        "content": "Which APIs have the worst governance scores?",
    },
    {
        "role": "assistant",
        "content": (
            "Let me find the non-compliant APIs across your catalog.\n\n"
            "[Calling: list_non_compliant_apis()]\n\n"
            "## APIs with Critical Governance Failures\n\n"
            "| API | Score | Category | Critical Failures |\n"
            "|-----|-------|----------|-------------------|\n"
            "| legacy-auth-api | 34 | Poor | Missing version, no spec |\n"
            "| internal-data-api | 48 | Poor | No contacts, deprecated without sunset |\n\n"
            "I recommend addressing these APIs first as they have critical-severity "
            "failures that significantly impact their governance scores. "
            "Would you like detailed remediation guidance for either of these APIs?"
        ),
    },
]
