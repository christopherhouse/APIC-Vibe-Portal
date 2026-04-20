"""Custom Chat History Provider for MAF Agents.

Replaces the buggy MAF `CosmosHistoryProvider` with a custom implementation
that stores chat messages directly in Cosmos DB using the Azure SDK.

This provider implements the MAF context provider interface and stores messages
in the `chat-sessions` Cosmos DB container with the session ID as the partition key.
"""

from __future__ import annotations

import json
import logging
import uuid
from datetime import UTC, datetime
from typing import Any

from azure.cosmos.container import ContainerProxy
from azure.cosmos.exceptions import CosmosResourceNotFoundError

logger = logging.getLogger(__name__)


class ChatHistoryProvider:
    """Custom MAF context provider for persisting chat history to Cosmos DB.

    Implements the MAF context provider interface (before_run, after_run) to
    automatically save conversation messages after each agent interaction.

    Messages are stored in the `chat-sessions` container with the following schema:
    - id: <session_id>
    - sessionId: <session_id> (partition key)
    - messages: list[dict] - array of message objects
    - createdAt: ISO timestamp
    - updatedAt: ISO timestamp

    Parameters
    ----------
    container:
        Cosmos DB ContainerProxy for the chat-sessions container.
    """

    def __init__(self, container: ContainerProxy) -> None:
        self._container = container

    async def before_run(
        self,
        *,
        session_id: str,
        context: Any = None,
        messages: list[dict[str, Any]] | None = None,
        **kwargs: Any,
    ) -> list[dict[str, Any]]:
        """Load existing messages for the session before the agent runs.

        This is called by MAF before invoking the agent to populate the
        conversation history context.

        Parameters
        ----------
        session_id:
            The chat session identifier.
        context:
            MAF context object (unused).
        messages:
            Current messages list (may be empty or contain new user message).
        **kwargs:
            Additional context from MAF.

        Returns the complete conversation history including any previously
        saved messages for this session.
        """
        logger.debug("ChatHistoryProvider.before_run session=%s", session_id)

        # Load existing messages from Cosmos DB
        existing_messages = await self._load_messages(session_id)

        # If we have new messages in the current batch, append them
        if messages:
            existing_messages.extend(messages)

        return existing_messages

    async def after_run(
        self,
        *,
        session_id: str,
        context: Any = None,
        messages: list[dict[str, Any]] | None = None,
        state: Any = None,
        **kwargs: Any,
    ) -> None:
        """Save messages to Cosmos DB after the agent completes.

        This is called by MAF after the agent finishes processing to persist
        the updated conversation history.

        Parameters
        ----------
        session_id:
            The chat session identifier.
        context:
            MAF context object (unused).
        messages:
            Complete conversation history to save.
        state:
            MAF state object (unused).
        **kwargs:
            Additional context from MAF.
        """
        logger.debug("ChatHistoryProvider.after_run session=%s message_count=%d", session_id, len(messages or []))

        if not messages:
            return

        await self._save_messages(session_id, messages)

    async def _load_messages(self, session_id: str) -> list[dict[str, Any]]:
        """Load messages for a session from Cosmos DB.

        Returns an empty list if the session doesn't exist yet.
        """
        try:
            doc = self._container.read_item(item=session_id, partition_key=session_id)
            messages = doc.get("messages", [])
            logger.debug("Loaded %d messages for session %s", len(messages), session_id)
            return messages
        except CosmosResourceNotFoundError:
            logger.debug("No existing messages found for session %s", session_id)
            return []
        except Exception:
            logger.exception("Failed to load messages for session %s", session_id)
            return []

    async def _save_messages(self, session_id: str, messages: list[dict[str, Any]]) -> None:
        """Save messages for a session to Cosmos DB.

        Creates a new document or updates the existing one.
        """
        now = datetime.now(UTC).isoformat().replace("+00:00", "Z")

        # Try to read existing document to preserve createdAt
        try:
            existing = self._container.read_item(item=session_id, partition_key=session_id)
            created_at = existing.get("createdAt", now)
        except CosmosResourceNotFoundError:
            created_at = now
        except Exception:
            logger.exception("Failed to read existing document for session %s", session_id)
            created_at = now

        # Serialize messages to ensure they're JSON-safe
        serialized_messages = []
        for msg in messages:
            # MAF messages are already dicts, but we want to ensure clean serialization
            serialized = {
                "role": msg.get("role", "user"),
                "content": self._serialize_content(msg.get("content", "")),
            }
            # Preserve any additional fields like timestamp, id, etc.
            for key in ("id", "timestamp", "name", "tool_call_id", "tool_calls"):
                if key in msg:
                    serialized[key] = msg[key]
            serialized_messages.append(serialized)

        document = {
            "id": session_id,
            "sessionId": session_id,
            "messages": serialized_messages,
            "createdAt": created_at,
            "updatedAt": now,
        }

        try:
            self._container.upsert_item(body=document, partition_key=session_id)
            logger.debug("Saved %d messages for session %s", len(messages), session_id)
        except Exception:
            logger.exception("Failed to save messages for session %s", session_id)
            raise

    def _serialize_content(self, content: Any) -> Any:
        """Serialize message content to ensure it's JSON-safe.

        MAF messages can have complex content (strings, lists of blocks, etc.).
        This ensures everything can be stored in Cosmos DB.
        """
        if isinstance(content, str):
            return content
        if isinstance(content, (list, dict)):
            # Already JSON-serializable structures
            return content
        # For anything else, convert to string
        return str(content)

    def clear(self, session_id: str) -> None:
        """Clear all messages for a session (synchronous).

        This is called from the chat service's clear_history method.
        """
        try:
            self._container.delete_item(item=session_id, partition_key=session_id)
            logger.info("Cleared history for session %s", session_id)
        except CosmosResourceNotFoundError:
            logger.debug("No history to clear for session %s", session_id)
        except Exception:
            logger.exception("Failed to clear history for session %s", session_id)
            raise
