"""System prompt and few-shot examples for the API Discovery Agent."""

from __future__ import annotations

from ..prompts import load_prompt

# Lazy-loaded system prompt from external markdown file
SYSTEM_PROMPT = load_prompt("api_discovery_system")

# Few-shot examples injected into the conversation before user turns.
FEW_SHOT_EXAMPLES: list[dict[str, str]] = [
    {
        "role": "user",
        "content": "What APIs do you have for sending emails?",
    },
    {
        "role": "assistant",
        "content": (
            "Let me search the catalog for email-related APIs.\n\n"
            "[Calling: search_apis('email sending notification')]\n\n"
            "Based on the catalog, here are the available email APIs:\n\n"
            "1. **Notification API** — A unified messaging API that supports email, "
            "SMS, and push notifications. Currently in **Production** (REST).\n"
            "2. **SMTP Gateway API** — Direct SMTP relay for transactional emails. "
            "Suitable for high-volume sends.\n\n"
            "I recommend the **Notification API** for most use cases as it provides "
            "a unified interface. Would you like more details or the API specification?"
        ),
    },
    {
        "role": "user",
        "content": "Show me the endpoints for the Notification API.",
    },
    {
        "role": "assistant",
        "content": (
            "I'll look up the available versions and then fetch the specification.\n\n"
            "[Calling: list_api_versions('notification-api')]\n"
            "[Calling: get_api_spec('notification-api', 'v1')]\n\n"
            "The **Notification API v1** exposes these key endpoints:\n\n"
            "- `POST /notifications/email` — Send an email notification\n"
            "- `POST /notifications/sms` — Send an SMS message\n"
            "- `GET /notifications/{id}` — Check delivery status\n"
            "- `DELETE /notifications/{id}` — Cancel a pending notification\n\n"
            "See the full spec for request/response schemas and authentication details."
        ),
    },
]
