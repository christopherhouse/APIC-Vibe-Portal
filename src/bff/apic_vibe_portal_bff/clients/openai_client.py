"""Azure OpenAI client wrapper powered by Microsoft Agent Framework (MAF).

Uses the ``agent-framework`` package to create an AI agent backed by Azure
OpenAI.  The agent uses ``DefaultAzureCredential`` for authentication and
exposes both synchronous-style and streaming chat interfaces.

Error handling is consistent with the existing BFF client patterns.
"""

from __future__ import annotations

import logging
from typing import Any

from azure.identity import DefaultAzureCredential

logger = logging.getLogger(__name__)

# Scope for Azure Cognitive Services token
_COGNITIVE_SERVICES_SCOPE = "https://cognitiveservices.azure.com/.default"


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
    """Thin wrapper around the Azure OpenAI Python SDK via MAF.

    Parameters
    ----------
    endpoint:
        Azure OpenAI service endpoint URL.
    deployment:
        The deployment name for the chat model (e.g. ``gpt-4o``).
    api_version:
        Azure OpenAI API version.
    credential:
        Azure credential object.  Defaults to ``DefaultAzureCredential``.
    """

    def __init__(
        self,
        endpoint: str,
        deployment: str,
        api_version: str = "2024-06-01",
        credential: Any | None = None,
    ) -> None:
        self._endpoint = endpoint.rstrip("/") if endpoint else ""
        self._deployment = deployment
        self._api_version = api_version
        self._credential = credential or DefaultAzureCredential()
        self._client: Any | None = None
        self._chat_client: Any | None = None

    def _get_client(self) -> Any:
        """Lazily create and return the MAF ``OpenAIChatClient``."""
        if self._client is None:
            from agent_framework.openai import OpenAIChatClient

            self._client = OpenAIChatClient(
                model=self._deployment,
                azure_endpoint=self._endpoint,
                api_version=self._api_version,
                credential=self._credential,
            )
        return self._client

    def _get_chat_client(self) -> Any:
        """Lazily create and return an ``AsyncAzureOpenAI`` client for chat completions.

        MAF's ``OpenAIChatClient`` uses ``responses_mode=True`` which sets the
        base URL to ``{endpoint}/openai/v1/`` — correct for the Responses API
        but incorrect for the Chat Completions API (``/openai/deployments/...``).
        This method creates a direct ``AsyncAzureOpenAI`` client that uses the
        standard ``azure_endpoint`` parameter, producing correct URL paths for
        the Chat Completions endpoint.
        """
        if self._chat_client is None:
            from azure.identity import get_bearer_token_provider
            from openai import AsyncAzureOpenAI

            token_provider = get_bearer_token_provider(self._credential, _COGNITIVE_SERVICES_SCOPE)
            self._chat_client = AsyncAzureOpenAI(
                azure_endpoint=self._endpoint,
                azure_deployment=self._deployment,
                api_version=self._api_version,
                azure_ad_token_provider=token_provider,
            )
        return self._chat_client

    def _get_token(self) -> str:
        """Obtain an Entra ID token for Azure Cognitive Services."""
        token = self._credential.get_token(_COGNITIVE_SERVICES_SCOPE)
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
            error = body.get("error") if isinstance(body.get("error"), dict) else body
            code = error.get("code", "")
            if code == "content_filter":
                return True
            inner = error.get("innererror") or {}
            if isinstance(inner, dict) and inner.get("code") == "ResponsibleAIPolicyViolation":
                return True
        # Fallback: check string representation
        exc_str = str(exc)
        return "content_filter" in exc_str or "ResponsibleAIPolicyViolation" in exc_str

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
