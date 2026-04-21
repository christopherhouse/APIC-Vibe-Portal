"""Custom Chat History Provider for MAF Agents.

Replaces the buggy MAF `CosmosHistoryProvider` with a custom implementation
that stores chat messages directly in Cosmos DB using the Azure SDK.

This provider implements the MAF HistoryProvider interface and stores messages
in the `chat-sessions` Cosmos DB container with the session ID as the partition key.
"""

from __future__ import annotations

import logging
from collections.abc import Sequence
from datetime import UTC, datetime
from typing import Any

from agent_framework import HistoryProvider, Message
from azure.cosmos.container import ContainerProxy
from azure.cosmos.exceptions import CosmosResourceNotFoundError

logger = logging.getLogger(__name__)


class ChatHistoryProvider(HistoryProvider):
    """Custom MAF history provider for persisting chat history to Cosmos DB.

    Implements the MAF HistoryProvider interface (get_messages, save_messages) to
    automatically load and save conversation messages with each agent interaction.

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
    source_id:
        Unique identifier for this provider instance. Used by the agent
        framework for message/tool attribution. Defaults to "chat_history".
    """

    def __init__(self, container: ContainerProxy, source_id: str = "chat_history") -> None:
        super().__init__(source_id, load_messages=True)
        self._container = container

    async def get_messages(
        self,
        session_id: str | None,
        *,
        state: dict[str, Any] | None = None,
        **kwargs: Any,
    ) -> list[Message]:
        """Load existing messages for the session.

        This is called by MAF before invoking the agent to populate the
        conversation history context.

        Parameters
        ----------
        session_id:
            The chat session identifier.
        state:
            MAF state object (unused).
        **kwargs:
            Additional context from MAF.

        Returns
        -------
        list[Message]
            The complete conversation history for this session.
        """
        if not session_id:
            logger.debug("ChatHistoryProvider.get_messages: no session_id, returning empty list")
            return []

        logger.debug("ChatHistoryProvider.get_messages session=%s", session_id)

        # Load existing messages from Cosmos DB
        message_dicts = await self._load_messages(session_id)

        # Convert to Message objects.
        # Cosmos stores messages in OpenAI format (``content`` key) while
        # MAF ``Message.from_dict`` expects the ``contents`` key, so we
        # transform each dict before deserialisation.
        results: list[Message] = []
        for msg in message_dicts:
            maf_dict: dict[str, Any] = {"role": msg.get("role", "user")}
            raw_content = msg.get("content") or msg.get("contents")
            if raw_content is not None:
                # Normalise to a list of content items that from_dict expects
                if isinstance(raw_content, list):
                    maf_dict["contents"] = raw_content
                else:
                    maf_dict["contents"] = [str(raw_content)]
            results.append(Message.from_dict(maf_dict))
        return results

    async def save_messages(
        self,
        session_id: str | None,
        messages: Sequence[Message],
        *,
        state: dict[str, Any] | None = None,
        **kwargs: Any,
    ) -> None:
        """Save messages to Cosmos DB after the agent completes.

        This is called by MAF after the agent finishes processing to persist
        the updated conversation history.

        Parameters
        ----------
        session_id:
            The chat session identifier.
        messages:
            Complete conversation history to save.
        state:
            MAF state object (unused).
        **kwargs:
            Additional context from MAF.
        """
        if not session_id:
            logger.debug("ChatHistoryProvider.save_messages: no session_id, skipping")
            return

        logger.debug("ChatHistoryProvider.save_messages session=%s message_count=%d", session_id, len(messages))

        if not messages:
            return

        # Convert Message objects to dicts in the OpenAI-style format used
        # by the Cosmos DB storage layer (``content`` key, not ``contents``).
        message_dicts: list[dict[str, Any]] = []
        for msg in messages:
            maf = msg.to_dict()
            # Extract plain text content from MAF contents list
            contents = maf.get("contents", [])
            if isinstance(contents, list) and len(contents) == 1:
                item = contents[0]
                if isinstance(item, dict) and item.get("type") == "text":
                    plain = item.get("text", "")
                else:
                    plain = contents
            else:
                plain = contents if contents else ""
            message_dicts.append(
                {
                    "role": maf.get("role", "user"),
                    "content": plain,
                }
            )

        await self._save_messages(session_id, message_dicts)

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
