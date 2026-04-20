"""Azure OpenAI client wrapper powered by Microsoft Agent Framework (MAF).

Uses the ``agent-framework`` package to create an AI agent backed by Azure
OpenAI.  The agent uses ``DefaultAzureCredential`` for authentication and
exposes both synchronous-style and streaming chat interfaces.

Both the MAF agent path and the direct chat-completions path use the
**v1 API** (``/openai/v1/`` base URL), which removes the need for dated
``api-version`` query parameters.  Authentication uses a bearer token
provider with the ``https://ai.azure.com/.default`` scope.

Error handling is consistent with the existing BFF client patterns.
"""

from __future__ import annotations

import logging
from typing import Any

from azure.identity import DefaultAzureCredential, get_bearer_token_provider

logger = logging.getLogger(__name__)

# Token scope for Azure AI / Azure OpenAI v1 API
_AI_FOUNDRY_SCOPE = "https://ai.azure.com/.default"


def _async_token_provider(credential: Any) -> Any:
    """Return an **async** callable that provides a bearer token.

    ``get_bearer_token_provider`` returns a *synchronous* callable.  Newer
    versions of the OpenAI SDK ``await`` the ``api_key`` provider inside
    ``AsyncOpenAI._refresh_api_key``.  If the provider is synchronous the
    ``await`` receives a plain ``str`` and raises
    ``TypeError: 'str' object can't be awaited``.

    Wrapping the sync provider in a thin ``async`` function satisfies the
    SDK contract while keeping the existing ``DefaultAzureCredential``
    (sync) auth path.
    """
    sync_provider = get_bearer_token_provider(credential, _AI_FOUNDRY_SCOPE)

    async def _provider() -> str:
        return sync_provider()

    return _provider


# ---------------------------------------------------------------------------
# Custom exceptions
# ---------------------------------------------------------------------------


class OpenAIClientError(Exception):
    """Base error raised by :class:`OpenAIClient`."""

    def __init__(self, message: str, status_code: int | None = None) -> None:
        super().__init__(message)
        self.status_code = status_code


class OpenAIRateLimitError(OpenAIClientError):
    """Raised when the Azure OpenAI service returns 429."""

    def __init__(self, detail: str = "Azure OpenAI rate limit exceeded") -> None:
        super().__init__(detail, status_code=429)


class OpenAIContentFilterError(OpenAIClientError):
    """Raised when the prompt is rejected by Azure OpenAI content filtering."""

    _DEFAULT_MESSAGE = (
        "Your message was flagged by the content safety filter. Please rephrase your message and try again."
    )

    def __init__(self, detail: str = "") -> None:
        super().__init__(detail or self._DEFAULT_MESSAGE, status_code=400)


class OpenAIUnavailableError(OpenAIClientError):
    """Raised when the Azure OpenAI service is unavailable."""

    def __init__(self, detail: str = "Azure OpenAI service unavailable") -> None:
        super().__init__(detail, status_code=503)


# ---------------------------------------------------------------------------
# Client
# ---------------------------------------------------------------------------


class OpenAIClient:
    """Thin wrapper around the Azure OpenAI Python SDK via MAF (v1 API).

    Uses the v1 API approach: ``base_url={endpoint}/openai/v1/`` with a
    bearer token provider as ``api_key``, which routes through the standard
    ``AsyncOpenAI`` client and avoids the deprecated dated ``api-version``
    query parameter.

    Parameters
    ----------
    endpoint:
        Azure OpenAI service endpoint URL.
    deployment:
        The deployment name for the chat model (e.g. ``gpt-4o``).
    credential:
        Azure credential object.  Defaults to ``DefaultAzureCredential``.
    """

    def __init__(
        self,
        endpoint: str,
        deployment: str,
        credential: Any | None = None,
    ) -> None:
        self._endpoint = endpoint.rstrip("/") if endpoint else ""
        self._deployment = deployment
        self._credential = credential or DefaultAzureCredential()
        self._client: Any | None = None
        self._chat_client: Any | None = None

    def _get_client(self) -> Any:
        """Lazily create and return the MAF ``OpenAIChatClient`` using the v1 API.

        Uses OpenAI routing (``base_url`` + ``api_key``) instead of Azure
        routing (``azure_endpoint`` + ``credential``) so that the
        underlying ``AsyncOpenAI`` client does not append a dated
        ``api-version`` query parameter.
        """
        if self._client is None:
            from agent_framework.openai import OpenAIChatClient

            token_provider = _async_token_provider(self._credential)
            base_url = f"{self._endpoint.rstrip('/')}/openai/v1/"

            self._client = OpenAIChatClient(
                model=self._deployment,
                base_url=base_url,
                api_key=token_provider,
            )
        return self._client

    def _get_chat_client(self) -> Any:
        """Lazily create and return an ``AsyncOpenAI`` client for chat completions (v1 API).

        Uses the v1 API approach: ``base_url={endpoint}/openai/v1/`` with a
        bearer token provider as ``api_key``.  This avoids the deprecated
        dated ``api-version`` query parameter that ``AsyncAzureOpenAI``
        would append.
        """
        if self._chat_client is None:
            from openai import AsyncOpenAI

            token_provider = _async_token_provider(self._credential)
            base_url = f"{self._endpoint.rstrip('/')}/openai/v1/"

            self._chat_client = AsyncOpenAI(
                base_url=base_url,
                api_key=token_provider,
            )
        return self._chat_client

    def _get_token(self) -> str:
        """Obtain an Entra ID token for Azure AI Foundry v1 API."""
        token = self._credential.get_token(_AI_FOUNDRY_SCOPE)
        return token.token

    def _handle_error(self, exc: Exception, context: str) -> None:
        """Translate openai SDK exceptions into domain errors."""
        from openai import APIStatusError, RateLimitError

        if isinstance(exc, RateLimitError):
            logger.warning("OpenAI rate limit hit: %s", context)
            raise OpenAIRateLimitError() from exc
        if isinstance(exc, APIStatusError):
            status = exc.status_code
            logger.error(
                "OpenAI API error — status=%s context=%s message=%s",
                status,
                context,
                str(exc),
            )
            if status >= 500:
                raise OpenAIUnavailableError(str(exc)) from exc
            # Detect Azure OpenAI content filter rejections
            if self._is_content_filter_error(exc):
                logger.warning("Content filter triggered: %s", context)
                raise OpenAIContentFilterError() from exc
            raise OpenAIClientError(str(exc), status_code=status) from exc
        raise OpenAIClientError(str(exc)) from exc

    @staticmethod
    def _is_content_filter_error(exc: Exception) -> bool:
        """Return ``True`` if *exc* represents an Azure content-filter rejection."""
        body = getattr(exc, "body", None)
        if isinstance(body, dict):
            error_value = body.get("error")
            error = error_value if isinstance(error_value, dict) else body
            code = error.get("code", "")
            if code == "content_filter":
                return True
            inner = error.get("innererror") or {}
            if isinstance(inner, dict) and inner.get("code") == "ResponsibleAIPolicyViolation":
                return True
        return False

    # ------------------------------------------------------------------
    # Chat completion (async)
    # ------------------------------------------------------------------

    async def chat_completion(
        self,
        messages: list[dict[str, str]],
        *,
        temperature: float = 0.3,
        max_tokens: int = 1024,
    ) -> dict[str, Any]:
        """Send a chat completion request and return the response.

        Returns a dict with keys: ``content``, ``usage``, ``finish_reason``.
        """
        try:
            client = self._get_chat_client()
            response = await client.chat.completions.create(
                model=self._deployment,
                messages=messages,
                temperature=temperature,
                max_tokens=max_tokens,
            )
            choice = response.choices[0]
            usage = response.usage
            return {
                "content": choice.message.content or "",
                "finish_reason": choice.finish_reason,
                "usage": {
                    "prompt_tokens": usage.prompt_tokens if usage else 0,
                    "completion_tokens": usage.completion_tokens if usage else 0,
                    "total_tokens": usage.total_tokens if usage else 0,
                },
            }
        except OpenAIClientError:
            raise
        except Exception as exc:
            self._handle_error(exc, "chat_completion")
            return {}  # unreachable

    async def chat_completion_stream(
        self,
        messages: list[dict[str, str]],
        *,
        temperature: float = 0.3,
        max_tokens: int = 1024,
    ) -> Any:
        """Stream a chat completion and yield chunks.

        Each yielded dict has keys: ``content`` (str), ``finish_reason`` (str | None).
        The final chunk includes ``usage`` when available.
        """
        try:
            client = self._get_chat_client()
            stream = await client.chat.completions.create(
                model=self._deployment,
                messages=messages,
                temperature=temperature,
                max_tokens=max_tokens,
                stream=True,
                stream_options={"include_usage": True},
            )
            async for chunk in stream:
                if not chunk.choices:
                    # Final chunk with usage only
                    if chunk.usage:
                        yield {
                            "content": "",
                            "finish_reason": None,
                            "usage": {
                                "prompt_tokens": chunk.usage.prompt_tokens,
                                "completion_tokens": chunk.usage.completion_tokens,
                                "total_tokens": chunk.usage.total_tokens,
                            },
                        }
                    continue
                delta = chunk.choices[0].delta
                yield {
                    "content": delta.content or "",
                    "finish_reason": chunk.choices[0].finish_reason,
                }
        except OpenAIClientError:
            raise
        except Exception as exc:
            self._handle_error(exc, "chat_completion_stream")

    # ------------------------------------------------------------------
    # MAF Agent access
    # ------------------------------------------------------------------

    def get_maf_client(self) -> Any:
        """Return the underlying MAF ``OpenAIChatClient`` for Agent usage."""
        return self._get_client()

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------

    def close(self) -> None:
        """Close the underlying clients."""
        self._client = None
        self._chat_client = None
