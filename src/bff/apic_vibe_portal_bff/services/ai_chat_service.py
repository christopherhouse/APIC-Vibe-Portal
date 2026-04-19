"""RAG-powered AI chat service using Microsoft Agent Framework (MAF).

Uses the MAF ``Agent`` class with:
- ``OpenAIChatClient`` for Azure OpenAI integration
- ``CosmosHistoryProvider`` for persisting chat history to Cosmos DB
- A ``@tool``-decorated search function for RAG retrieval

The pipeline:
1. Receive user question
2. MAF Agent invokes ``search_api_catalog`` tool when grounding is needed
3. LLM generates a response grounded in retrieved API documentation
4. MAF automatically persists conversation history to Cosmos DB

Includes per-session rate limiting, tiktoken-based token estimation,
and OTel metric emission.
"""

from __future__ import annotations

import json
import logging
import time
import uuid
from collections.abc import Generator
from datetime import UTC, datetime
from threading import Lock
from typing import Any

from apic_vibe_portal_bff.clients.ai_search_client import AISearchClient, AISearchClientError
from apic_vibe_portal_bff.clients.openai_client import OpenAIClient
from apic_vibe_portal_bff.models.chat import ChatMessage, ChatResponse, Citation
from apic_vibe_portal_bff.utils.logger import sanitize_for_log

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# System prompt
# ---------------------------------------------------------------------------

SYSTEM_PROMPT = (
    "You are the API Discovery Assistant for an enterprise API portal. "
    "Your role is to help developers find, understand, and use APIs from "
    "the organization's API catalog.\n\n"
    "## Guidelines\n\n"
    "1. **Answer questions about APIs** in the catalog using the provided "
    "context. Always base your answers on the retrieved API documentation.\n"
    "2. **Cite specific APIs** when referencing them. Use the API name and "
    "title from the context.\n"
    "3. **Be professional and helpful**. Provide clear, concise answers "
    "with practical examples when appropriate.\n"
    "4. **Stay on topic**. Only answer questions related to APIs, "
    "integrations, and the API catalog. Politely decline questions "
    "outside this domain.\n"
    "5. **Encourage exploration**. When relevant, suggest the user browse "
    "the catalog for additional APIs or details.\n"
    "6. **Acknowledge limitations**. If the provided context does not "
    "contain enough information to answer a question, say so rather "
    "than guessing.\n\n"
    "## Tools\n\n"
    "You have access to a ``search_api_catalog`` tool. Use it to search "
    "for relevant APIs when the user asks about APIs, capabilities, or "
    "integrations. Always search before answering API-related questions.\n\n"
    "## Response Format\n\n"
    "- Use markdown formatting for readability.\n"
    "- When referencing APIs, mention them by name.\n"
    "- Provide code examples in appropriate languages when helpful.\n"
    "- Keep responses focused and actionable.\n"
)

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

_MAX_CONVERSATION_TURNS = 10  # Sliding window: keep last N messages
_SESSION_EXPIRY_SECONDS = 30 * 60  # 30 minutes
_MAX_CONTEXT_TOKENS = 3000  # Max tokens for RAG context
_MAX_TOTAL_TOKENS = 8000  # Budget for the entire prompt
_RATE_LIMIT_PER_SESSION = 30  # Messages per minute per session
_RATE_LIMIT_WINDOW_SECONDS = 60  # Sliding window for rate limiting
_RAG_TOP_K = 5  # Number of search results to retrieve
_CITATION_EXCERPT_LENGTH = 200  # Max characters for citation content excerpt

# Default per-token pricing (GPT-4o, USD per 1K tokens)
_DEFAULT_PROMPT_PRICE_PER_1K = 0.005
_DEFAULT_COMPLETION_PRICE_PER_1K = 0.015


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _utc_iso_now() -> str:
    """Return the current UTC time as an ISO 8601 string with ``Z`` suffix."""
    return datetime.now(UTC).isoformat().replace("+00:00", "Z")


# ---------------------------------------------------------------------------
# Token estimation with tiktoken
# ---------------------------------------------------------------------------


def _get_encoding(model: str) -> Any:
    """Get tiktoken encoding for a model, with fallback."""
    import tiktoken

    try:
        return tiktoken.encoding_for_model(model)
    except KeyError:
        return tiktoken.get_encoding("cl100k_base")


def estimate_tokens(text: str, model: str = "gpt-4o") -> int:
    """Estimate the number of tokens in a text string."""
    encoding = _get_encoding(model)
    return len(encoding.encode(text))


def estimate_messages_tokens(messages: list[dict[str, str]], model: str = "gpt-4o") -> int:
    """Estimate total tokens for a list of chat messages.

    Uses the OpenAI token counting convention: each message adds overhead
    tokens for role/name framing.
    """
    encoding = _get_encoding(model)
    tokens_per_message = 3  # <|start|>role<|end|>
    total = 0
    for msg in messages:
        total += tokens_per_message
        for value in msg.values():
            total += len(encoding.encode(value))
    total += 3  # reply priming
    return total


# ---------------------------------------------------------------------------
# OTel metric helpers (lazy-init stubs)
# ---------------------------------------------------------------------------

# These emit metrics using the standard logging-based approach.
# Task 019 will replace with proper OTel SDK integration.


def _emit_metric(name: str, value: float, attributes: dict[str, str] | None = None) -> None:
    """Emit an OTel-style metric via structured logging.

    When the OTel SDK is wired up (task 019), these will be replaced with
    real histogram observations.
    """
    logger.info(
        "otel_metric",
        extra={
            "metric_name": name,
            "metric_value": value,
            **(attributes or {}),
        },
    )


# ---------------------------------------------------------------------------
# Session management (in-memory for MVP)
# ---------------------------------------------------------------------------


class _ChatSession:
    """In-memory session state for rate limiting and local message cache.

    Conversation history is also persisted to Cosmos DB via MAF's
    ``CosmosHistoryProvider`` on the Agent.  This class maintains a
    local copy of messages for prompt construction and a sliding window,
    plus monotonic timestamps for per-session rate limiting.

    Each message gets a stable ``id`` and ``timestamp`` assigned on first
    insertion so that ``get_history`` returns deterministic values.
    """

    __slots__ = ("session_id", "messages", "created_at", "updated_at", "_message_timestamps", "_lock")

    def __init__(self, session_id: str) -> None:
        self.session_id = session_id
        self.messages: list[dict[str, str]] = []
        now = time.monotonic()
        self.created_at = now
        self.updated_at = now
        self._message_timestamps: list[float] = []
        self._lock = Lock()

    def is_expired(self) -> bool:
        """Check if the session has expired due to inactivity."""
        return (time.monotonic() - self.updated_at) > _SESSION_EXPIRY_SECONDS

    def touch(self) -> None:
        """Update the last activity timestamp."""
        self.updated_at = time.monotonic()

    def add_message(self, role: str, content: str) -> None:
        """Append a message and trim to the sliding window.

        Each message receives a stable ``id`` and ``timestamp`` so that
        ``get_history`` returns deterministic values across calls.
        """
        now = _utc_iso_now()
        self.messages.append(
            {
                "role": role,
                "content": content,
                "id": str(uuid.uuid4()),
                "timestamp": now,
            }
        )
        max_messages = _MAX_CONVERSATION_TURNS * 2
        if len(self.messages) > max_messages:
            first_message = self.messages[0]
            if first_message.get("role") == "system":
                # Keep the system prompt plus the most recent conversation messages.
                self.messages = [first_message] + self.messages[-(max_messages - 1) :]
            else:
                # No system prompt is stored in the session, so trim to the most recent messages only.
                self.messages = self.messages[-max_messages:]
        self.touch()

    def check_rate_limit(self) -> bool:
        """Return True if the session is within rate limits."""
        now = time.monotonic()
        with self._lock:
            # Prune timestamps older than the rate limit window
            self._message_timestamps = [t for t in self._message_timestamps if now - t < _RATE_LIMIT_WINDOW_SECONDS]
            if len(self._message_timestamps) >= _RATE_LIMIT_PER_SESSION:
                return False
            self._message_timestamps.append(now)
            return True

    def get_history_messages(self) -> list[dict[str, str]]:
        """Return conversation messages (excluding system prompt)."""
        return [m for m in self.messages if m.get("role") != "system"]


class SessionManager:
    """Thread-safe session manager.

    Provides in-memory ``_ChatSession`` objects for rate limiting and
    local message cache.  Persistent conversation history is delegated
    to MAF's ``CosmosHistoryProvider`` which is configured on the
    ``Agent`` instance (see :class:`AIChatService`).
    """

    def __init__(self) -> None:
        self._sessions: dict[str, _ChatSession] = {}
        self._lock = Lock()

    def get_or_create(self, session_id: str | None) -> _ChatSession:
        """Get an existing session or create a new one.

        Expired sessions are replaced with fresh ones.
        """
        with self._lock:
            if session_id and session_id in self._sessions:
                session = self._sessions[session_id]
                if not session.is_expired():
                    return session
                # Expired — remove and create fresh
                del self._sessions[session_id]

            new_id = session_id or str(uuid.uuid4())
            session = _ChatSession(new_id)
            self._sessions[new_id] = session
            return session

    def get(self, session_id: str) -> _ChatSession | None:
        """Get a session by ID, or None if not found or expired."""
        with self._lock:
            session = self._sessions.get(session_id)
            if session is None:
                return None
            if session.is_expired():
                del self._sessions[session_id]
                return None
            return session

    def delete(self, session_id: str) -> bool:
        """Delete a session. Returns True if it existed."""
        with self._lock:
            return self._sessions.pop(session_id, None) is not None

    def cleanup_expired(self) -> int:
        """Remove all expired sessions. Returns the count of removed sessions."""
        with self._lock:
            expired = [sid for sid, s in self._sessions.items() if s.is_expired()]
            for sid in expired:
                del self._sessions[sid]
            return len(expired)


# ---------------------------------------------------------------------------
# MAF search tool factory
# ---------------------------------------------------------------------------


def _create_search_tool(search_client: AISearchClient, model: str) -> Any:
    """Create a MAF-compatible search tool using the ``@tool`` decorator.

    Returns the tool function that the MAF Agent will invoke via function
    calling when it needs to ground its answers.
    """
    from agent_framework import tool

    @tool(
        name="search_api_catalog",
        description=(
            "Search the enterprise API catalog for APIs matching a query. "
            "Returns API names, descriptions, types, and lifecycle stages. "
            "Use this tool to find relevant APIs before answering questions."
        ),
    )
    def search_api_catalog(query: str) -> str:
        """Search the API catalog and return formatted results."""
        try:
            raw = search_client.search(
                search_text=query,
                top=_RAG_TOP_K,
                query_type="semantic",
                semantic_query=query,
            )
            results = raw.get("results", [])
        except AISearchClientError:
            logger.warning("AI Search retrieval failed — returning empty results")
            return "No API documentation found. The search service is currently unavailable."

        if not results:
            return "No APIs found matching your query."

        context_parts: list[str] = []
        total_tokens = 0

        for result in results:
            api_name = result.get("apiName", "Unknown API")
            title = result.get("title", "")
            description = result.get("description", "")
            kind = result.get("kind", "")
            lifecycle = result.get("lifecycleStage", "")

            entry = f"## {api_name}: {title}\n- Kind: {kind}\n- Lifecycle: {lifecycle}\n- Description: {description}\n"

            entry_tokens = estimate_tokens(entry, model)
            if total_tokens + entry_tokens > _MAX_CONTEXT_TOKENS:
                break
            total_tokens += entry_tokens
            context_parts.append(entry)

        return "\n".join(context_parts) if context_parts else "No APIs found."

    return search_api_catalog


# ---------------------------------------------------------------------------
# Chat service
# ---------------------------------------------------------------------------


class AIChatService:
    """RAG-powered chat service using Microsoft Agent Framework.

    The MAF ``Agent`` is configured with:
    - ``OpenAIChatClient`` for Azure OpenAI
    - A ``search_api_catalog`` tool for RAG retrieval
    - A ``HistoryProvider`` for conversation persistence (defaults to
      ``InMemoryHistoryProvider``; use ``CosmosHistoryProvider`` in prod)

    Parameters
    ----------
    openai_client:
        :class:`OpenAIClient` instance providing the MAF ``OpenAIChatClient``.
    search_client:
        :class:`AISearchClient` instance for retrieving API context.
    model:
        Model/deployment name for tiktoken encoding.
    history_provider:
        MAF ``HistoryProvider`` for conversation persistence.  Defaults to
        ``InMemoryHistoryProvider`` when ``None``.
    prompt_price_per_1k:
        Per-1K-token price for prompt tokens (for cost estimation).
    completion_price_per_1k:
        Per-1K-token price for completion tokens (for cost estimation).
    """

    def __init__(
        self,
        openai_client: OpenAIClient,
        search_client: AISearchClient,
        *,
        model: str = "gpt-4o",
        history_provider: Any | None = None,
        prompt_price_per_1k: float = _DEFAULT_PROMPT_PRICE_PER_1K,
        completion_price_per_1k: float = _DEFAULT_COMPLETION_PRICE_PER_1K,
    ) -> None:
        self._openai = openai_client
        self._search = search_client
        self._model = model
        self._prompt_price = prompt_price_per_1k
        self._completion_price = completion_price_per_1k
        self._sessions = SessionManager()

        # Create the MAF search tool
        self._search_tool = _create_search_tool(search_client, model)

        # Set up history provider (Cosmos in prod, in-memory for dev/tests)
        if history_provider is None:
            from agent_framework import InMemoryHistoryProvider

            history_provider = InMemoryHistoryProvider()
        self._history_provider = history_provider

        # Create the MAF Agent wired with the search tool and history provider
        self._agent = self._create_agent()

    @property
    def session_manager(self) -> SessionManager:
        """Expose session manager for route handlers."""
        return self._sessions

    # ------------------------------------------------------------------
    # MAF Agent construction
    # ------------------------------------------------------------------

    def _create_agent(self) -> Any:
        """Create a MAF ``Agent`` wired with tools and history.

        The Agent is configured with:
        - The ``OpenAIChatClient`` from :attr:`_openai`
        - The ``search_api_catalog`` tool for RAG retrieval
        - The ``HistoryProvider`` for conversation persistence
        - The system prompt as instructions
        """
        from agent_framework import Agent

        return Agent(
            client=self._openai.get_maf_client(),
            instructions=SYSTEM_PROMPT,
            tools=[self._search_tool],
            context_providers=[self._history_provider],
            name="API Discovery Assistant",
            description="Helps developers find and use APIs from the catalog",
        )

    # ------------------------------------------------------------------
    # RAG retrieval (direct, for non-agent path and citations)
    # ------------------------------------------------------------------

    def _retrieve_context(self, query: str, accessible_api_ids: list[str] | None = None) -> tuple[str, list[Citation]]:
        """Retrieve relevant API documents from AI Search.

        Parameters
        ----------
        query:
            The user's question to search for.
        accessible_api_ids:
            When ``None``, no security filter is applied (admin bypass).
            When a list, RAG retrieval is restricted to the named APIs.

        Returns
        -------
        (context_text, citations).
        """
        # Build an OData filter for security trimming.
        security_filter: str | None = None
        if accessible_api_ids is not None:
            if not accessible_api_ids:
                return "", []  # No accessible APIs → empty context
            ids_csv = ",".join(accessible_api_ids)
            security_filter = f"search.in(apiName, '{ids_csv}', ',')"

        try:
            raw = self._search.search(
                search_text=query,
                top=_RAG_TOP_K,
                query_type="semantic",
                semantic_query=query,
                filter_expression=security_filter,
            )
            results = raw.get("results", [])
        except AISearchClientError:
            logger.warning("AI Search retrieval failed for RAG context — proceeding without context")
            return "", []

        if not results:
            return "", []

        context_parts: list[str] = []
        citations: list[Citation] = []
        total_tokens = 0

        for result in results:
            api_name = result.get("apiName", "Unknown API")
            title = result.get("title", "")
            description = result.get("description", "")
            kind = result.get("kind", "")
            lifecycle = result.get("lifecycleStage", "")

            entry = f"## {api_name}: {title}\n- Kind: {kind}\n- Lifecycle: {lifecycle}\n- Description: {description}\n"

            entry_tokens = estimate_tokens(entry, self._model)
            if total_tokens + entry_tokens > _MAX_CONTEXT_TOKENS:
                break
            total_tokens += entry_tokens

            context_parts.append(entry)
            citations.append(
                Citation(
                    title=f"{api_name}: {title}" if title else api_name,
                    url=f"/api/catalog/{api_name}",
                    content=description[:_CITATION_EXCERPT_LENGTH] if description else None,
                )
            )

        context_text = "\n".join(context_parts) if context_parts else ""
        return context_text, citations

    # ------------------------------------------------------------------
    # Prompt construction
    # ------------------------------------------------------------------

    def _build_messages(
        self,
        session: _ChatSession,
        user_message: str,
        context: str,
    ) -> list[dict[str, str]]:
        """Build the message list for the OpenAI API call.

        Includes: system prompt, RAG context, conversation history, user message.
        Token budget is enforced by truncating history if needed.
        """
        messages: list[dict[str, str]] = [{"role": "system", "content": SYSTEM_PROMPT}]

        if context:
            messages.append(
                {
                    "role": "system",
                    "content": (
                        "The following API documentation from the catalog is relevant "
                        "to the user's question. Use this information to provide an "
                        "accurate, grounded answer:\n\n" + context
                    ),
                }
            )

        # Add conversation history (sliding window from session)
        history = session.get_history_messages()
        messages.extend(history)

        # Add the new user message
        messages.append({"role": "user", "content": user_message})

        # Enforce token budget — trim history if needed
        while estimate_messages_tokens(messages, self._model) > _MAX_TOTAL_TOKENS and len(messages) > 3:
            # Remove the oldest non-system message
            for i, msg in enumerate(messages):
                if msg["role"] != "system":
                    messages.pop(i)
                    break

        return messages

    # ------------------------------------------------------------------
    # Metric emission
    # ------------------------------------------------------------------

    def _emit_token_metrics(
        self,
        estimated_tokens: int,
        usage: dict[str, int],
    ) -> None:
        """Emit OTel metrics for token estimation and actual usage."""
        _emit_metric("apic.llm.tokens.estimated", float(estimated_tokens), {"component": "chat"})

        prompt_tokens = usage.get("prompt_tokens", 0)
        completion_tokens = usage.get("completion_tokens", 0)
        total_tokens = usage.get("total_tokens", 0)

        _emit_metric("apic.llm.tokens.prompt", float(prompt_tokens))
        _emit_metric("apic.llm.tokens.completion", float(completion_tokens))
        _emit_metric("apic.llm.tokens.total", float(total_tokens))

        # Cost estimation
        cost = (prompt_tokens / 1000 * self._prompt_price) + (completion_tokens / 1000 * self._completion_price)
        _emit_metric("apic.llm.cost.estimated", cost)

        # Warn if estimated vs actual differ by more than 10%
        if estimated_tokens > 0 and prompt_tokens > 0:
            diff_pct = abs(estimated_tokens - prompt_tokens) / estimated_tokens * 100
            if diff_pct > 10:
                logger.warning(
                    "Token estimate drift: estimated=%d actual=%d diff=%.1f%%",
                    estimated_tokens,
                    prompt_tokens,
                    diff_pct,
                )

    # ------------------------------------------------------------------
    # Chat (synchronous)
    # ------------------------------------------------------------------

    def chat(
        self, user_message: str, session_id: str | None = None, accessible_api_ids: list[str] | None = None
    ) -> ChatResponse:
        """Process a chat message through the RAG pipeline.

        Parameters
        ----------
        user_message:
            The user's input message.
        session_id:
            Optional session ID for conversation continuity.
        accessible_api_ids:
            When ``None``, no security filter is applied to RAG retrieval
            (admin bypass).  When a list, the RAG context and citations are
            restricted to the named APIs so the AI cannot reference
            inaccessible APIs.

        Returns a :class:`ChatResponse` with the assistant's answer and citations.
        """
        session = self._sessions.get_or_create(session_id)

        # Rate limit check
        if not session.check_rate_limit():
            raise ChatRateLimitError(session.session_id)

        # 1. Retrieve context (with security filter)
        context, citations = self._retrieve_context(user_message, accessible_api_ids)

        # 2. Build prompt
        messages = self._build_messages(session, user_message, context)

        # 3. Estimate tokens
        estimated = estimate_messages_tokens(messages, self._model)

        # 4. Generate
        result = self._openai.chat_completion(messages, max_tokens=1024)

        # 5. Emit metrics
        self._emit_token_metrics(estimated, result.get("usage", {}))

        # 6. Update local session cache (history persisted by MAF HistoryProvider)
        session.add_message("user", user_message)
        session.add_message("assistant", result["content"])

        now = _utc_iso_now()
        response_message = ChatMessage(
            id=str(uuid.uuid4()),
            role="assistant",
            content=result["content"],
            citations=citations if citations else None,
            timestamp=now,
        )

        return ChatResponse(
            sessionId=session.session_id,
            message=response_message,
        )

    # ------------------------------------------------------------------
    # Chat (streaming)
    # ------------------------------------------------------------------

    def chat_stream(
        self,
        user_message: str,
        session_id: str | None = None,
        accessible_api_ids: list[str] | None = None,
    ) -> Generator[str]:
        """Stream a chat response as SSE events.

        Parameters
        ----------
        user_message:
            The user's input message.
        session_id:
            Optional session ID for conversation continuity.
        accessible_api_ids:
            When ``None``, no security filter is applied to RAG retrieval
            (admin bypass).  When a list, RAG context is restricted to
            the named APIs.

        Yields SSE-formatted strings for each token chunk.
        The final event includes citations and metadata.
        """
        session = self._sessions.get_or_create(session_id)

        if not session.check_rate_limit():
            yield f"data: {json.dumps({'error': 'Rate limit exceeded', 'sessionId': session.session_id})}\n\n"
            return

        # 1. Retrieve context (with security filter)
        context, citations = self._retrieve_context(user_message, accessible_api_ids)

        # 2. Build prompt
        messages = self._build_messages(session, user_message, context)

        # 3. Estimate tokens
        estimated = estimate_messages_tokens(messages, self._model)

        # 4. Stream generation
        full_content = ""
        usage: dict[str, int] = {}

        # Send initial event with session ID
        yield f"data: {json.dumps({'type': 'start', 'sessionId': session.session_id})}\n\n"

        try:
            for chunk in self._openai.chat_completion_stream(messages, max_tokens=1024):
                content = chunk.get("content", "")
                if content:
                    full_content += content
                    yield f"data: {json.dumps({'type': 'content', 'content': content})}\n\n"
                if "usage" in chunk:
                    usage = chunk["usage"]
        except Exception:
            logger.exception("Streaming error mid-response")
            error_payload = {
                "type": "error",
                "error": "An internal error occurred during streaming",
                "sessionId": session.session_id,
            }
            yield f"data: {json.dumps(error_payload)}\n\n"
            return

        # 5. Emit metrics
        if usage:
            self._emit_token_metrics(estimated, usage)

        # 6. Update local session cache (history persisted by MAF HistoryProvider)
        session.add_message("user", user_message)
        session.add_message("assistant", full_content)

        # 7. Send final event with citations
        now = _utc_iso_now()
        message_id = str(uuid.uuid4())
        final_event = {
            "type": "end",
            "message": {
                "id": message_id,
                "role": "assistant",
                "content": full_content,
                "citations": [c.model_dump() for c in citations] if citations else None,
                "timestamp": now,
            },
            "sessionId": session.session_id,
        }
        yield f"data: {json.dumps(final_event)}\n\n"

    # ------------------------------------------------------------------
    # History
    # ------------------------------------------------------------------

    def get_history(self, session_id: str) -> list[ChatMessage]:
        """Return the conversation history for a session.

        Uses stable IDs and timestamps stored alongside each message
        rather than generating new ones on every call.  If a MAF
        ``HistoryProvider`` is configured, it will have received the
        same messages during the ``Agent.run()`` call; this method reads
        from the local in-memory cache for consistency.
        """
        session = self._sessions.get(session_id)
        if session is None:
            return []

        messages: list[ChatMessage] = []
        for msg in session.get_history_messages():
            messages.append(
                ChatMessage(
                    id=msg.get("id", str(uuid.uuid4())),
                    role=msg["role"],
                    content=msg["content"],
                    timestamp=msg.get("timestamp", _utc_iso_now()),
                )
            )
        return messages

    def clear_history(self, session_id: str) -> bool:
        """Clear the conversation history for a session.

        Removes the in-memory session and, if a MAF ``HistoryProvider``
        with a ``clear`` method is configured, also clears persisted
        history.
        """
        deleted = self._sessions.delete(session_id)
        # Also clear from the MAF history provider if it supports it
        if hasattr(self._history_provider, "clear"):
            try:
                self._history_provider.clear(session_id)
            except Exception:
                logger.exception(
                    "Failed to clear history from provider for session %s",
                    sanitize_for_log(session_id),
                )
        return deleted


# ---------------------------------------------------------------------------
# Custom exception for rate limiting
# ---------------------------------------------------------------------------


class ChatRateLimitError(Exception):
    """Raised when a session exceeds the chat rate limit."""

    def __init__(self, session_id: str) -> None:
        super().__init__(f"Rate limit exceeded for session {session_id}")
        self.session_id = session_id
