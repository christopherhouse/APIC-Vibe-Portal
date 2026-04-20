"""Tests for the FoundryAgentClient."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from apic_vibe_portal_bff.clients.foundry_agent_client import (
    FoundryAgentClient,
    FoundryAgentClientError,
    FoundryAgentUnavailableError,
)


class TestFoundryAgentClientInit:
    def test_endpoint_normalised_to_https(self):
        client = FoundryAgentClient(
            project_endpoint="http://my-foundry.api.azureml.ms",
            deployment="gpt-4o",
        )
        assert client._endpoint.startswith("https://")

    def test_endpoint_with_scheme_unchanged(self):
        client = FoundryAgentClient(
            project_endpoint="https://my-foundry.api.azureml.ms",
            deployment="gpt-4o",
        )
        assert client._endpoint == "https://my-foundry.api.azureml.ms"

    def test_endpoint_without_scheme_gets_https(self):
        client = FoundryAgentClient(
            project_endpoint="my-foundry.api.azureml.ms",
            deployment="gpt-4o",
        )
        assert client._endpoint == "https://my-foundry.api.azureml.ms"

    def test_empty_endpoint_preserved(self):
        client = FoundryAgentClient(project_endpoint="", deployment="gpt-4o")
        assert client._endpoint == ""

    def test_custom_credential_stored(self):
        mock_cred = MagicMock()
        client = FoundryAgentClient(
            project_endpoint="https://ep.azureml.ms",
            deployment="gpt-4o",
            credential=mock_cred,
        )
        assert client._credential is mock_cred

    def test_no_api_version_attribute(self):
        """v1 API clients should not store an api_version."""
        client = FoundryAgentClient(project_endpoint="https://ep.azureml.ms", deployment="gpt-4o")
        assert not hasattr(client, "_api_version")


class TestFoundryAgentClientIsConfigured:
    def test_configured_when_endpoint_set(self):
        client = FoundryAgentClient(project_endpoint="https://ep.azureml.ms", deployment="gpt-4o")
        assert client.is_configured() is True

    def test_not_configured_when_endpoint_empty(self):
        client = FoundryAgentClient(project_endpoint="", deployment="gpt-4o")
        assert client.is_configured() is False

    def test_not_configured_when_whitespace_only(self):
        client = FoundryAgentClient(project_endpoint="   ", deployment="gpt-4o")
        assert client.is_configured() is False


class TestFoundryAgentClientGetMafClient:
    def test_get_maf_client_returns_openai_chat_client(self):
        mock_maf = MagicMock()
        mock_token_provider = MagicMock()
        client = FoundryAgentClient(
            project_endpoint="https://ep.azureml.ms",
            deployment="gpt-4o",
        )
        with (
            patch("agent_framework.openai.OpenAIChatClient", return_value=mock_maf) as mock_cls,
            patch(
                "apic_vibe_portal_bff.clients.foundry_agent_client.get_bearer_token_provider",
                return_value=mock_token_provider,
            ),
        ):
            result = client.get_maf_client()
            assert result is mock_maf
            mock_cls.assert_called_once_with(
                model="gpt-4o",
                base_url="https://ep.azureml.ms/openai/v1/",
                api_key=mock_token_provider,
            )

    def test_get_maf_client_lazy_init(self):
        mock_maf = MagicMock()
        client = FoundryAgentClient(
            project_endpoint="https://ep.azureml.ms",
            deployment="gpt-4o",
        )
        with (
            patch("agent_framework.openai.OpenAIChatClient", return_value=mock_maf),
            patch(
                "apic_vibe_portal_bff.clients.foundry_agent_client.get_bearer_token_provider",
                return_value=MagicMock(),
            ),
        ):
            first = client.get_maf_client()
            second = client.get_maf_client()
            assert first is second  # same instance returned

    def test_get_maf_client_uses_v1_base_url(self):
        """Verify the v1 base_url is constructed from the endpoint."""
        mock_maf = MagicMock()
        mock_token_provider = MagicMock()
        client = FoundryAgentClient(
            project_endpoint="https://my-foundry.api.azureml.ms",
            deployment="gpt-4o",
        )
        with (
            patch("agent_framework.openai.OpenAIChatClient", return_value=mock_maf) as mock_cls,
            patch(
                "apic_vibe_portal_bff.clients.foundry_agent_client.get_bearer_token_provider",
                return_value=mock_token_provider,
            ),
        ):
            client.get_maf_client()
            _, call_kwargs = mock_cls.call_args
            assert "base_url" in call_kwargs
            assert call_kwargs["base_url"] == "https://my-foundry.api.azureml.ms/openai/v1/"

    def test_get_maf_client_uses_ai_azure_scope(self):
        """Verify the token provider uses the ai.azure.com scope."""
        mock_cred = MagicMock()
        client = FoundryAgentClient(
            project_endpoint="https://ep.azureml.ms",
            deployment="gpt-4o",
            credential=mock_cred,
        )
        with (
            patch("agent_framework.openai.OpenAIChatClient", return_value=MagicMock()),
            patch(
                "apic_vibe_portal_bff.clients.foundry_agent_client.get_bearer_token_provider",
                return_value=MagicMock(),
            ) as mock_get_provider,
        ):
            client.get_maf_client()
            mock_get_provider.assert_called_once_with(mock_cred, "https://ai.azure.com/.default")


class TestFoundryAgentClientClose:
    def test_close_clears_client(self):
        mock_maf = MagicMock()
        client = FoundryAgentClient(project_endpoint="https://ep.azureml.ms", deployment="gpt-4o")
        with (
            patch("agent_framework.openai.OpenAIChatClient", return_value=mock_maf),
            patch(
                "apic_vibe_portal_bff.clients.foundry_agent_client.get_bearer_token_provider",
                return_value=MagicMock(),
            ),
        ):
            client.get_maf_client()
            assert client._client is not None
            client.close()
            assert client._client is None

    def test_close_when_not_initialised_is_safe(self):
        client = FoundryAgentClient(project_endpoint="https://ep.azureml.ms", deployment="gpt-4o")
        client.close()  # Should not raise


class TestFoundryAgentClientNormalizeEndpoint:
    @pytest.mark.parametrize(
        ("input_ep", "expected"),
        [
            ("https://ep.azureml.ms", "https://ep.azureml.ms"),
            ("http://ep.azureml.ms", "https://ep.azureml.ms"),
            ("ep.azureml.ms", "https://ep.azureml.ms"),
            ("", ""),
            ("   ", ""),
        ],
    )
    def test_normalize(self, input_ep, expected):
        result = FoundryAgentClient._normalize_endpoint(input_ep)
        assert result == expected


class TestFoundryAgentClientErrors:
    def test_foundry_client_error_has_status_code(self):
        err = FoundryAgentClientError("test error", status_code=400)
        assert err.status_code == 400
        assert str(err) == "test error"

    def test_foundry_unavailable_error_default_message(self):
        err = FoundryAgentUnavailableError()
        assert err.status_code == 503
        assert "unavailable" in str(err).lower()
