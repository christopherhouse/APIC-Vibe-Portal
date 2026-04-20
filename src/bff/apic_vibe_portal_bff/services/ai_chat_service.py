"""Agent-powered AI chat service.

Delegates all chat interactions through the agent router (currently the
API Discovery Agent backed by Azure AI Foundry).  The agent handles RAG
retrieval, tool calling, and conversation history internally.

The service layer adds per-session rate limiting, session management for
local message caching, Cosmos DB persistence via :class:`ChatSessionRepository`,
and history/clear operations.
"""

from __future__ import annotations

import json
import logging
import time
import uuid
from collections.abc import AsyncGenerator
from datetime import UTC, datetime
from threading import Lock
from typing import TYPE_CHECKING, Any

from apic_vibe_portal_bff.clients.openai_client import OpenAIContentFilterError
from apic_vibe_portal_bff.data.models.chat_session import ChatMessageDoc, ChatSessionDocument
from apic_vibe_portal_bff.models.chat import ChatMessage, ChatResponse
from apic_vibe_portal_bff.utils.logger import sanitize_for_log

if TYPE_CHECKING:
    from apic_vibe_portal_bff.data.repositories.chat_session_repository import ChatSessionRepository

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

_MAX_CONVERSATION_TURNS = 10  # Sliding window: keep last N messages
_SESSION_EXPIRY_SECONDS = 30 * 60  # 30 minutes
_RATE_LIMIT_PER_SESSION = 30  # Messages per minute per session
_RATE_LIMIT_WINDOW_SECONDS = 60  # Sliding window for rate limiting


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _utc_iso_now() -> str:
    """Return the current UTC time as an ISO 8601 string with ``Z`` suffix."""
    return datetime.now(UTC).isoformat().replace("+00:00", "Z")


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
# Chat service
# ---------------------------------------------------------------------------


class AIChatService:
    """Agent-powered chat service.

    All chat interactions are delegated to the ``agent_router``, which
    routes requests through the multi-agent system (currently the API
    Discovery Agent backed by Azure AI Foundry).

    Parameters
    ----------
    agent_router:
        :class:`~apic_vibe_portal_bff.agents.agent_router.AgentRouter`
        that dispatches chat requests through the agent system.
    history_provider:
        Optional MAF ``HistoryProvider`` reference retained for
        ``clear_history`` support.  The actual conversation persistence
        is managed inside the agent.
    chat_repository:
        Optional :class:`~apic_vibe_portal_bff.data.repositories.chat_session_repository.ChatSessionRepository`
        for persisting chat sessions to Cosmos DB.  When ``None``, chat
        history is kept only in-memory (lost on process restart).
    """

    def __init__(
        self,
        *,
        agent_router: Any,
        history_provider: Any | None = None,
        chat_repository: ChatSessionRepository | None = None,
    ) -> None:
        if agent_router is None:
            raise ValueError("agent_router is required — the direct RAG fallback has been removed")
        self._agent_router = agent_router
        self._history_provider = history_provider
        self._chat_repository = chat_repository
        self._sessions = SessionManager()

    @property
    def session_manager(self) -> SessionManager:
        """Expose session manager for route handlers."""
        return self._sessions

    # ------------------------------------------------------------------
    # Chat (synchronous)
    # ------------------------------------------------------------------

    async def chat(
        self,
        user_message: str,
        session_id: str | None = None,
        accessible_api_ids: list[str] | None = None,
        user_id: str | None = None,
    ) -> ChatResponse:
        """Process a chat message through the agent system.

        The request is dispatched through the agent router, which routes
        it to the appropriate agent (currently API Discovery Agent).

        Parameters
        ----------
        user_message:
            The user's input message.
        session_id:
            Optional session ID for conversation continuity.
        accessible_api_ids:
            When ``None``, no security filter is applied (admin bypass).
            When a list, the agent restricts context to the named APIs
            so the AI cannot reference inaccessible APIs.
        user_id:
            Authenticated user's OID.  Required for Cosmos DB persistence.

        Returns a :class:`ChatResponse` with the assistant's answer and citations.
        """
        session = self._sessions.get_or_create(session_id)

        if not session.check_rate_limit():
            raise ChatRateLimitError(session.session_id)

        from apic_vibe_portal_bff.agents.types import AgentRequest

        agent_request = AgentRequest(
            message=user_message,
            session_id=session.session_id,
            accessible_api_ids=accessible_api_ids,
        )
        agent_response = await self._agent_router.dispatch(agent_request)

        session.add_message("user", user_message)
        session.add_message("assistant", agent_response.content)

        now = _utc_iso_now()
        msg_id = str(uuid.uuid4())

        # Persist to Cosmos DB if repository and user_id are available
        self._persist_messages(session, user_id)

        return ChatResponse(
            sessionId=session.session_id,
            message=ChatMessage(
                id=msg_id,
                role="assistant",
                content=agent_response.content,
                citations=agent_response.citations or None,
                timestamp=now,
            ),
        )

    # ------------------------------------------------------------------
    # Chat (streaming)
    # ------------------------------------------------------------------

    async def chat_stream(
        self,
        user_message: str,
        session_id: str | None = None,
        accessible_api_ids: list[str] | None = None,
        user_id: str | None = None,
    ) -> AsyncGenerator[str]:
        """Stream a chat response as SSE events.

        The request is dispatched through the agent router and the response
        is emitted as a single SSE event sequence (start → content → end).

        Parameters
        ----------
        user_message:
            The user's input message.
        session_id:
            Optional session ID for conversation continuity.
        accessible_api_ids:
            When ``None``, no security filter is applied (admin bypass).
            When a list, the agent restricts context to the named APIs.
        user_id:
            Authenticated user's OID.  Required for Cosmos DB persistence.

        Yields SSE-formatted strings for each token chunk.
        The final event includes citations and metadata.
        """
        session = self._sessions.get_or_create(session_id)

        if not session.check_rate_limit():
            yield f"data: {json.dumps({'error': 'Rate limit exceeded', 'sessionId': session.session_id})}\n\n"
            return

        from apic_vibe_portal_bff.agents.types import AgentRequest

        yield f"data: {json.dumps({'type': 'start', 'sessionId': session.session_id})}\n\n"

        try:
            agent_request = AgentRequest(
                message=user_message,
                session_id=session.session_id,
                accessible_api_ids=accessible_api_ids,
            )
            agent_response = await self._agent_router.dispatch(agent_request)
            full_content = agent_response.content
            if full_content:
                yield f"data: {json.dumps({'type': 'content', 'content': full_content})}\n\n"
            citations = agent_response.citations
        except OpenAIContentFilterError as exc:
            logger.warning("Content filter triggered during agent streaming")
            error_payload = {
                "type": "error",
                "error": str(exc),
                "sessionId": session.session_id,
            }
            yield f"data: {json.dumps(error_payload)}\n\n"
            return
        except Exception:
            logger.exception("Agent streaming error mid-response")
            error_payload = {
                "type": "error",
                "error": "An internal error occurred",
                "sessionId": session.session_id,
            }
            yield f"data: {json.dumps(error_payload)}\n\n"
            return

        session.add_message("user", user_message)
        session.add_message("assistant", full_content)

        # Persist to Cosmos DB if repository and user_id are available
        self._persist_messages(session, user_id)

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

    @staticmethod
    def _to_chat_messages(raw_messages: list[dict[str, str]]) -> list[ChatMessage]:
        """Convert raw message dicts to :class:`ChatMessage` objects.

        Filters out ``system`` messages and assigns fallback IDs/timestamps
        when the original values are missing.
        """
        return [
            ChatMessage(
                id=m.get("id", str(uuid.uuid4())),
                role=m["role"],
                content=m["content"],
                timestamp=m.get("timestamp", _utc_iso_now()),
            )
            for m in raw_messages
            if m.get("role") != "system"
        ]

    def get_history(self, session_id: str, user_id: str | None = None) -> list[ChatMessage]:
        """Return the conversation history for a session.

        Checks the in-memory cache first.  If no in-memory session exists
        and a ``ChatSessionRepository`` is configured, falls back to
        reading from Cosmos DB.

        Parameters
        ----------
        session_id:
            The chat session identifier.
        user_id:
            Authenticated user's OID.  Required for Cosmos DB lookup.
        """
        session = self._sessions.get(session_id)
        if session is not None:
            return self._to_chat_messages(session.get_history_messages())

        # Fallback: read from Cosmos DB
        if self._chat_repository is not None and user_id:
            try:
                doc = self._chat_repository.find_by_id(session_id, user_id)
                if doc is not None:
                    return self._to_chat_messages(doc.get("messages", []))
            except Exception:
                logger.exception(
                    "Failed to read chat history from Cosmos DB for session %s",
                    sanitize_for_log(session_id),
                )

        return []

    def clear_history(self, session_id: str, user_id: str | None = None) -> bool:
        """Clear the conversation history for a session.

        Removes the in-memory session, soft-deletes the Cosmos DB document
        (if the repository is configured), and clears the MAF history
        provider if it has a ``clear`` method.

        Parameters
        ----------
        session_id:
            The chat session identifier.
        user_id:
            Authenticated user's OID.  Required for Cosmos DB soft-delete.
        """
        deleted = self._sessions.delete(session_id)

        # Soft-delete from Cosmos DB
        if self._chat_repository is not None and user_id:
            try:
                result = self._chat_repository.soft_delete(session_id, user_id)
                if result is not None:
                    deleted = True
            except Exception:
                logger.exception(
                    "Failed to soft-delete chat session from Cosmos DB for session %s",
                    sanitize_for_log(session_id),
                )

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

    # ------------------------------------------------------------------
    # Cosmos DB persistence
    # ------------------------------------------------------------------

    def _persist_messages(self, session: _ChatSession, user_id: str | None) -> None:
        """Persist the current in-memory session to Cosmos DB.

        Creates a new ``ChatSessionDocument`` on the first call for a given
        session, and replaces the existing document on subsequent calls.

        This method is best-effort: failures are logged but never raised
        so the chat response is still returned to the caller.
        """
        if self._chat_repository is None or not user_id:
            return

        try:
            # Build the messages list from the in-memory session
            cosmos_messages = [
                ChatMessageDoc(
                    id=msg.get("id", str(uuid.uuid4())),
                    role=msg["role"],
                    content=msg["content"],
                    timestamp=msg.get("timestamp", _utc_iso_now()),
                ).model_dump()
                for msg in session.messages
            ]

            # Try to read the existing document first
            existing = self._chat_repository.find_by_id(session.session_id, user_id)

            if existing is not None:
                # Update existing document with new messages
                existing["messages"] = cosmos_messages
                existing["updatedAt"] = _utc_iso_now()
                self._chat_repository.update(existing)
                logger.debug(
                    "Updated chat session %s in Cosmos DB (%d messages)",
                    session.session_id,
                    len(cosmos_messages),
                )
            else:
                # Derive a title from the first user message
                first_user_msg = next(
                    (m["content"] for m in session.messages if m.get("role") == "user"),
                    "",
                )
                title = first_user_msg[:80] if first_user_msg else ""

                doc = ChatSessionDocument.new(
                    session_id=session.session_id,
                    user_id=user_id,
                    title=title,
                )
                cosmos_dict = doc.to_cosmos_dict()
                cosmos_dict["messages"] = cosmos_messages
                self._chat_repository.create(cosmos_dict)
                logger.info(
                    "Created chat session %s in Cosmos DB for user %s",
                    session.session_id,
                    sanitize_for_log(user_id),
                )
        except Exception:
            logger.exception(
                "Failed to persist chat session %s to Cosmos DB",
                sanitize_for_log(session.session_id),
            )


# ---------------------------------------------------------------------------
# Custom exception for rate limiting
# ---------------------------------------------------------------------------


class ChatRateLimitError(Exception):
    """Raised when a session exceeds the chat rate limit."""

    def __init__(self, session_id: str) -> None:
        super().__init__(f"Rate limit exceeded for session {session_id}")
        self.session_id = session_id
