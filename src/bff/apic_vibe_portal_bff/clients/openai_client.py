"""Azure OpenAI client wrapper.

Wraps the ``openai`` Python package with Azure-specific configuration,
DefaultAzureCredential authentication, and error handling consistent
with the existing BFF client patterns.
"""

from __future__ import annotations

import logging
from collections.abc import Generator
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


class OpenAIUnavailableError(OpenAIClientError):
    """Raised when the Azure OpenAI service is unavailable."""

    def __init__(self, detail: str = "Azure OpenAI service unavailable") -> None:
        super().__init__(detail, status_code=503)


# ---------------------------------------------------------------------------
# Client
# ---------------------------------------------------------------------------


class OpenAIClient:
    """Thin wrapper around the Azure OpenAI Python SDK.

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

    def _get_client(self) -> Any:
        """Lazily create and return the AzureOpenAI client."""
        if self._client is None:
            from openai import AzureOpenAI

            self._client = AzureOpenAI(
                azure_endpoint=self._endpoint,
                azure_deployment=self._deployment,
                api_version=self._api_version,
                azure_ad_token_provider=self._get_token,
            )
        return self._client

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
            raise OpenAIClientError(str(exc), status_code=status) from exc
        raise OpenAIClientError(str(exc)) from exc

    # ------------------------------------------------------------------
    # Chat completion
    # ------------------------------------------------------------------

    def chat_completion(
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
            client = self._get_client()
            response = client.chat.completions.create(
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
        except Exception as exc:
            self._handle_error(exc, "chat_completion")
            return {}  # unreachable

    def chat_completion_stream(
        self,
        messages: list[dict[str, str]],
        *,
        temperature: float = 0.3,
        max_tokens: int = 1024,
    ) -> Generator[dict[str, Any]]:
        """Stream a chat completion and yield chunks.

        Each yielded dict has keys: ``content`` (str), ``finish_reason`` (str | None).
        The final chunk includes ``usage`` when available.
        """
        try:
            client = self._get_client()
            stream = client.chat.completions.create(
                model=self._deployment,
                messages=messages,
                temperature=temperature,
                max_tokens=max_tokens,
                stream=True,
                stream_options={"include_usage": True},
            )
            for chunk in stream:
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
        except Exception as exc:
            self._handle_error(exc, "chat_completion_stream")

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------

    def close(self) -> None:
        """Close the underlying client."""
        if self._client is not None:
            self._client.close()
            self._client = None
