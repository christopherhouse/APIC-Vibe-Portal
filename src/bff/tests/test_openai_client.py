"""Tests for the OpenAI client wrapper."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import pytest

from apic_vibe_portal_bff.clients.openai_client import (
    OpenAIClient,
    OpenAIClientError,
    OpenAIContentFilterError,
    OpenAIRateLimitError,
    OpenAIUnavailableError,
)

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def mock_credential():
    """Return a mock Azure credential."""
    cred = MagicMock()
    token = MagicMock()
    token.token = "test-token"
    cred.get_token.return_value = token
    return cred


@pytest.fixture
def client(mock_credential):
    """Return an OpenAIClient with a mock credential."""
    return OpenAIClient(
        endpoint="https://test.openai.azure.com",
        deployment="gpt-4o",
        credential=mock_credential,
    )


def _inject_mock_client(client: OpenAIClient) -> MagicMock:
    """Inject a mock MAF OpenAIChatClient into the wrapper and return it.

    The mock simulates ``maf_client.client.chat.completions.create(...)``
    which is how the wrapper accesses the underlying openai SDK client
    via the MAF ``OpenAIChatClient.client`` property.
    """
    mock_maf_client = MagicMock()
    client._client = mock_maf_client
    return mock_maf_client


def _inject_mock_chat_client(client: OpenAIClient) -> MagicMock:
    """Inject a mock ``AsyncOpenAI`` chat client into the wrapper.

    The mock simulates ``chat_client.chat.completions.create(...)``
    which is the direct ``AsyncOpenAI`` client used for chat completions.
    """
    mock_chat_client = MagicMock()
    mock_chat_client.chat.completions.create = AsyncMock()
    client._chat_client = mock_chat_client
    return mock_chat_client


def _mock_completion_response(
    content: str = "Hello!",
    finish_reason: str = "stop",
    prompt_tokens: int = 50,
    completion_tokens: int = 20,
    total_tokens: int = 70,
    usage_present: bool = True,
) -> MagicMock:
    """Build a mock ChatCompletion response."""
    choice = MagicMock()
    choice.message.content = content
    choice.finish_reason = finish_reason

    response = MagicMock()
    response.choices = [choice]

    if usage_present:
        usage = MagicMock()
        usage.prompt_tokens = prompt_tokens
        usage.completion_tokens = completion_tokens
        usage.total_tokens = total_tokens
        response.usage = usage
    else:
        response.usage = None

    return response


# ---------------------------------------------------------------------------
# Construction / configuration tests
# ---------------------------------------------------------------------------


class TestOpenAIClientInit:
    def test_endpoint_trailing_slash_stripped(self, mock_credential):
        c = OpenAIClient(endpoint="https://test.openai.azure.com/", deployment="gpt-4o", credential=mock_credential)
        assert c._endpoint == "https://test.openai.azure.com"

    def test_empty_endpoint(self, mock_credential):
        c = OpenAIClient(endpoint="", deployment="gpt-4o", credential=mock_credential)
        assert c._endpoint == ""

    def test_no_api_version_attribute(self, client):
        """v1 API clients should not store an api_version."""
        assert not hasattr(client, "_api_version")


# ---------------------------------------------------------------------------
# Token acquisition
# ---------------------------------------------------------------------------


class TestTokenAcquisition:
    def test_get_token_calls_credential(self, client, mock_credential):
        token = client._get_token()
        assert token == "test-token"
        mock_credential.get_token.assert_called_once_with("https://ai.azure.com/.default")


# ---------------------------------------------------------------------------
# Chat completion tests
# ---------------------------------------------------------------------------


class TestChatCompletion:
    @pytest.mark.asyncio
    async def test_successful_chat_completion(self, client):
        mock = _inject_mock_chat_client(client)
        mock.chat.completions.create.return_value = _mock_completion_response(
            content="Hello! I can help you find APIs.",
        )

        messages = [
            {"role": "system", "content": "You are an assistant."},
            {"role": "user", "content": "What APIs are available?"},
        ]
        result = await client.chat_completion(messages)

        assert result["content"] == "Hello! I can help you find APIs."
        assert result["finish_reason"] == "stop"
        assert result["usage"]["prompt_tokens"] == 50
        assert result["usage"]["completion_tokens"] == 20
        assert result["usage"]["total_tokens"] == 70

    @pytest.mark.asyncio
    async def test_chat_completion_empty_content(self, client):
        mock = _inject_mock_chat_client(client)
        mock.chat.completions.create.return_value = _mock_completion_response(content=None)

        result = await client.chat_completion([{"role": "user", "content": "test"}])
        assert result["content"] == ""

    @pytest.mark.asyncio
    async def test_chat_completion_rate_limit_error(self, client):
        from openai import RateLimitError

        mock = _inject_mock_chat_client(client)
        mock_response = MagicMock()
        mock_response.status_code = 429
        mock_response.headers = {}
        mock.chat.completions.create.side_effect = RateLimitError(
            message="Rate limit exceeded",
            response=mock_response,
            body=None,
        )

        with pytest.raises(OpenAIRateLimitError):
            await client.chat_completion([{"role": "user", "content": "test"}])

    @pytest.mark.asyncio
    async def test_chat_completion_server_error(self, client):
        from openai import InternalServerError

        mock = _inject_mock_chat_client(client)
        mock_response = MagicMock()
        mock_response.status_code = 500
        mock_response.headers = {}
        mock.chat.completions.create.side_effect = InternalServerError(
            message="Internal server error",
            response=mock_response,
            body=None,
        )

        with pytest.raises(OpenAIUnavailableError):
            await client.chat_completion([{"role": "user", "content": "test"}])

    @pytest.mark.asyncio
    async def test_chat_completion_content_filter_error(self, client):
        from openai import BadRequestError

        mock = _inject_mock_chat_client(client)
        mock_response = MagicMock()
        mock_response.status_code = 400
        mock_response.headers = {}
        mock.chat.completions.create.side_effect = BadRequestError(
            message="Content filter triggered",
            response=mock_response,
            body={
                "error": {
                    "message": (
                        "The response was filtered due to the prompt "
                        "triggering Azure OpenAI's content management policy."
                    ),
                    "type": None,
                    "param": "prompt",
                    "code": "content_filter",
                    "status": 400,
                    "innererror": {
                        "code": "ResponsibleAIPolicyViolation",
                        "content_filter_result": {
                            "jailbreak": {"filtered": True, "detected": True},
                        },
                    },
                }
            },
        )

        with pytest.raises(OpenAIContentFilterError):
            await client.chat_completion([{"role": "user", "content": "test"}])

    @pytest.mark.asyncio
    async def test_chat_completion_generic_error(self, client):
        mock = _inject_mock_chat_client(client)
        mock.chat.completions.create.side_effect = RuntimeError("Unexpected")

        with pytest.raises(OpenAIClientError, match="Unexpected"):
            await client.chat_completion([{"role": "user", "content": "test"}])

    @pytest.mark.asyncio
    async def test_chat_completion_no_usage(self, client):
        mock = _inject_mock_chat_client(client)
        mock.chat.completions.create.return_value = _mock_completion_response(usage_present=False)

        result = await client.chat_completion([{"role": "user", "content": "test"}])
        assert result["usage"]["prompt_tokens"] == 0
        assert result["usage"]["completion_tokens"] == 0
        assert result["usage"]["total_tokens"] == 0


# ---------------------------------------------------------------------------
# Streaming tests
# ---------------------------------------------------------------------------


class TestChatCompletionStream:
    @pytest.mark.asyncio
    async def test_stream_yields_content(self, client):
        mock = _inject_mock_chat_client(client)

        # Create stream chunks
        chunk1 = MagicMock()
        chunk1.choices = [MagicMock()]
        chunk1.choices[0].delta.content = "Hello"
        chunk1.choices[0].finish_reason = None

        chunk2 = MagicMock()
        chunk2.choices = [MagicMock()]
        chunk2.choices[0].delta.content = " world"
        chunk2.choices[0].finish_reason = "stop"

        # Final usage chunk
        chunk3 = MagicMock()
        chunk3.choices = []
        chunk3.usage = MagicMock()
        chunk3.usage.prompt_tokens = 50
        chunk3.usage.completion_tokens = 10
        chunk3.usage.total_tokens = 60

        # Return an async iterator
        async def async_stream():
            for c in [chunk1, chunk2, chunk3]:
                yield c

        mock.chat.completions.create.return_value = async_stream()

        chunks = [chunk async for chunk in client.chat_completion_stream([{"role": "user", "content": "test"}])]
        assert len(chunks) == 3
        assert chunks[0]["content"] == "Hello"
        assert chunks[1]["content"] == " world"
        assert chunks[1]["finish_reason"] == "stop"
        assert chunks[2]["usage"]["total_tokens"] == 60

    @pytest.mark.asyncio
    async def test_stream_error_raises(self, client):
        mock = _inject_mock_chat_client(client)
        mock.chat.completions.create.side_effect = RuntimeError("Stream failed")

        with pytest.raises(OpenAIClientError, match="Stream failed"):
            _ = [chunk async for chunk in client.chat_completion_stream([{"role": "user", "content": "test"}])]

    @pytest.mark.asyncio
    async def test_stream_content_filter_error_raises(self, client):
        from openai import BadRequestError

        mock = _inject_mock_chat_client(client)
        mock_response = MagicMock()
        mock_response.status_code = 400
        mock_response.headers = {}
        mock.chat.completions.create.side_effect = BadRequestError(
            message="Content filter triggered",
            response=mock_response,
            body={
                "error": {
                    "code": "content_filter",
                    "innererror": {"code": "ResponsibleAIPolicyViolation"},
                }
            },
        )

        with pytest.raises(OpenAIContentFilterError):
            _ = [chunk async for chunk in client.chat_completion_stream([{"role": "user", "content": "test"}])]


# ---------------------------------------------------------------------------
# Lifecycle
# ---------------------------------------------------------------------------


class TestClientLifecycle:
    def test_close_releases_client(self, client):
        _inject_mock_client(client)
        _inject_mock_chat_client(client)
        assert client._client is not None
        assert client._chat_client is not None

        client.close()
        assert client._client is None
        assert client._chat_client is None

    def test_close_when_not_initialized(self, client):
        # Should not raise
        client.close()
        assert client._client is None
        assert client._chat_client is None
