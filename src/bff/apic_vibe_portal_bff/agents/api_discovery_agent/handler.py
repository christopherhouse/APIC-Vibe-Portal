"""Response processing helpers for the API Discovery Agent.

Provides utilities that transform raw agent output and tool results
into the final :class:`~apic_vibe_portal_bff.models.chat.ChatResponse`
format consumed by the chat endpoints.
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from typing import Any

from apic_vibe_portal_bff.models.chat import ChatMessage, ChatResponse, Citation


def build_chat_response(
    session_id: str,
    content: str,
    citations: list[Citation] | None = None,
) -> ChatResponse:
    """Build a :class:`ChatResponse` from agent output.

    Parameters
    ----------
    session_id:
        The session identifier for the conversation.
    content:
        The text content produced by the agent.
    citations:
        Optional list of :class:`Citation` objects to include.

    Returns
    -------
    :class:`~apic_vibe_portal_bff.models.chat.ChatResponse`
    """
    now = datetime.now(UTC).isoformat().replace("+00:00", "Z")
    return ChatResponse(
        sessionId=session_id,
        message=ChatMessage(
            id=str(uuid.uuid4()),
            role="assistant",
            content=content,
            citations=citations or None,
            timestamp=now,
        ),
    )


def format_search_result(result: dict[str, Any]) -> str:
    """Format a single AI Search result document as readable text.

    Parameters
    ----------
    result:
        A document dict returned by :meth:`~apic_vibe_portal_bff.clients.ai_search_client.AISearchClient.search`.

    Returns
    -------
    str
        Markdown-formatted API summary.
    """
    api_name = result.get("apiName", "Unknown")
    title = result.get("title", "")
    kind = result.get("kind", "")
    lifecycle = result.get("lifecycleStage", "")
    description = result.get("description", "")
    return f"## {api_name}: {title}\n- Kind: {kind}\n- Lifecycle: {lifecycle}\n- Description: {description}"


def extract_citations_from_results(results: list[dict[str, Any]], excerpt_length: int = 200) -> list[Citation]:
    """Build :class:`Citation` objects from AI Search result documents.

    Parameters
    ----------
    results:
        List of document dicts from :meth:`~apic_vibe_portal_bff.clients.ai_search_client.AISearchClient.search`.
    excerpt_length:
        Maximum number of characters for the citation content excerpt.

    Returns
    -------
    list[:class:`~apic_vibe_portal_bff.models.chat.Citation`]
    """
    citations: list[Citation] = []
    for result in results:
        api_name = result.get("apiName", "")
        if not api_name:
            continue
        title = result.get("title", "")
        description = result.get("description", "")
        citations.append(
            Citation(
                title=f"{api_name}: {title}" if title else api_name,
                url=f"/api/catalog/{api_name}",
                content=description[:excerpt_length] if description else None,
            )
        )
    return citations
