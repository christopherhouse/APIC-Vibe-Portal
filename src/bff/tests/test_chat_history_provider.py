"""Unit tests for custom ChatHistoryProvider."""

import uuid
from datetime import datetime
from unittest.mock import AsyncMock, MagicMock

import pytest
from azure.cosmos.exceptions import CosmosResourceNotFoundError

from apic_vibe_portal_bff.agents.chat_history_provider import ChatHistoryProvider


@pytest.fixture
def mock_container():
    """Mock Cosmos DB ContainerProxy."""
    container = MagicMock()
    container.id = "chat-sessions"
    return container


@pytest.fixture
def provider(mock_container):
    """ChatHistoryProvider instance with mocked container."""
    return ChatHistoryProvider(container=mock_container)


def test_serialize_content_string(provider):
    """Test content serialization for string values."""
    content = "Hello world"
    result = provider._serialize_content(content)
    assert result == "Hello world"


def test_serialize_content_list(provider):
    """Test content serialization for list values."""
    content = [{"type": "text", "text": "Hello"}]
    result = provider._serialize_content(content)
    assert result == content


def test_serialize_content_dict(provider):
    """Test content serialization for dict values."""
    content = {"type": "text", "text": "Hello"}
    result = provider._serialize_content(content)
    assert result == content


def test_serialize_content_other(provider):
    """Test content serialization for non-standard values."""
    content = 123
    result = provider._serialize_content(content)
    assert result == "123"


@pytest.mark.asyncio
async def test_load_messages_success(provider, mock_container):
    """Test loading messages from an existing session."""
    session_id = str(uuid.uuid4())
    mock_messages = [
        {"role": "user", "content": "Hello"},
        {"role": "assistant", "content": "Hi there!"},
    ]
    mock_container.read_item.return_value = {
        "id": session_id,
        "sessionId": session_id,
        "messages": mock_messages,
    }

    result = await provider._load_messages(session_id)

    assert result == mock_messages
    mock_container.read_item.assert_called_once_with(item=session_id, partition_key=session_id)


@pytest.mark.asyncio
async def test_load_messages_not_found(provider, mock_container):
    """Test loading messages when session doesn't exist."""
    session_id = str(uuid.uuid4())
    mock_container.read_item.side_effect = CosmosResourceNotFoundError()

    result = await provider._load_messages(session_id)

    assert result == []


@pytest.mark.asyncio
async def test_save_messages_new_session(provider, mock_container):
    """Test saving messages for a new session."""
    session_id = str(uuid.uuid4())
    messages = [
        {"role": "user", "content": "Hello"},
        {"role": "assistant", "content": "Hi!"},
    ]
    mock_container.read_item.side_effect = CosmosResourceNotFoundError()

    await provider._save_messages(session_id, messages)

    mock_container.upsert_item.assert_called_once()
    call_args = mock_container.upsert_item.call_args
    saved_doc = call_args.kwargs["body"]
    assert saved_doc["id"] == session_id
    assert saved_doc["sessionId"] == session_id
    assert len(saved_doc["messages"]) == 2
    assert "createdAt" in saved_doc
    assert "updatedAt" in saved_doc


@pytest.mark.asyncio
async def test_save_messages_existing_session(provider, mock_container):
    """Test saving messages for an existing session."""
    session_id = str(uuid.uuid4())
    created_at = "2026-04-01T00:00:00Z"
    messages = [{"role": "user", "content": "Hello"}]
    mock_container.read_item.return_value = {
        "id": session_id,
        "createdAt": created_at,
    }

    await provider._save_messages(session_id, messages)

    mock_container.upsert_item.assert_called_once()
    call_args = mock_container.upsert_item.call_args
    saved_doc = call_args.kwargs["body"]
    assert saved_doc["createdAt"] == created_at  # Preserved


@pytest.mark.asyncio
async def test_before_run_new_session(provider, mock_container):
    """Test before_run with a new session (no existing messages)."""
    session_id = str(uuid.uuid4())
    new_messages = [{"role": "user", "content": "Hello"}]
    mock_container.read_item.side_effect = CosmosResourceNotFoundError()

    result = await provider.before_run(session_id=session_id, messages=new_messages)

    assert result == new_messages


@pytest.mark.asyncio
async def test_before_run_existing_session(provider, mock_container):
    """Test before_run with existing messages."""
    session_id = str(uuid.uuid4())
    existing = [{"role": "user", "content": "Hello"}]
    new_messages = [{"role": "assistant", "content": "Hi"}]
    mock_container.read_item.return_value = {
        "id": session_id,
        "messages": existing,
    }

    result = await provider.before_run(session_id=session_id, messages=new_messages)

    assert len(result) == 2
    assert result[0] == existing[0]
    assert result[1] == new_messages[0]


@pytest.mark.asyncio
async def test_after_run(provider, mock_container):
    """Test after_run saves messages."""
    session_id = str(uuid.uuid4())
    messages = [{"role": "user", "content": "Hello"}]
    mock_container.read_item.side_effect = CosmosResourceNotFoundError()

    await provider.after_run(session_id=session_id, messages=messages)

    mock_container.upsert_item.assert_called_once()


def test_clear_success(provider, mock_container):
    """Test clearing session history."""
    session_id = str(uuid.uuid4())

    provider.clear(session_id)

    mock_container.delete_item.assert_called_once_with(item=session_id, partition_key=session_id)


def test_clear_not_found(provider, mock_container):
    """Test clearing non-existent session (should not raise)."""
    session_id = str(uuid.uuid4())
    mock_container.delete_item.side_effect = CosmosResourceNotFoundError()

    # Should not raise
    provider.clear(session_id)

    mock_container.delete_item.assert_called_once()
