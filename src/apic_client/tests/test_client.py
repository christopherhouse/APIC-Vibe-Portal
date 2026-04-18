"""Unit tests for ApiCenterDataPlaneClient."""

from __future__ import annotations

import json
from unittest.mock import MagicMock, patch

import httpx
import pytest

from apic_client.client import _DATA_PLANE_SCOPE, ApiCenterDataPlaneClient
from apic_client.exceptions import (
    ApiCenterAuthError,
    ApiCenterClientError,
    ApiCenterNotFoundError,
    ApiCenterUnavailableError,
)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_BASE_URL = "https://myapic.data.eastus.azure-apicenter.ms"

SAMPLE_API = {
    "name": "petstore-api",
    "title": "Petstore API",
    "kind": "rest",
    "description": "A sample pet store API",
    "lifecycleStage": "production",
    "lastUpdated": "2024-03-20T14:30:00Z",
    "contacts": [{"name": "API Team", "email": "api-team@example.com"}],
    "externalDocumentation": [{"title": "Docs", "url": "https://docs.example.com"}],
    "customProperties": {"owner": "platform-team"},
    "termsOfService": {"url": "https://example.com/tos"},
    "license": {"name": "MIT", "url": "https://opensource.org/licenses/MIT"},
}

SAMPLE_VERSION = {
    "name": "v1",
    "title": "Version 1",
    "lifecycleStage": "production",
}

SAMPLE_DEFINITION = {
    "name": "openapi",
    "title": "OpenAPI Definition",
    "specification": {"name": "openapi", "version": "3.0.1"},
}

SAMPLE_ENVIRONMENT = {
    "name": "prod-env",
    "title": "Production Environment",
    "description": "Main production environment",
    "kind": "production",
}

SAMPLE_DEPLOYMENT = {
    "name": "dep-v1",
    "title": "v1 Production Deployment",
    "description": "Main deployment",
    "environmentId": "/workspaces/default/environments/prod-env",
    "server": {"runtimeUri": ["https://api.example.com/v1"]},
}


def _make_client(mock_credential: MagicMock | None = None) -> ApiCenterDataPlaneClient:
    """Return a client with a mock credential."""
    cred = mock_credential or MagicMock()
    cred.get_token.return_value = MagicMock(token="fake-token", expires_on=9999999999.0)
    return ApiCenterDataPlaneClient(
        base_url=_BASE_URL,
        credential=cred,
    )


def _mock_response(
    status_code: int = 200,
    json_data: dict | list | None = None,
    headers: dict[str, str] | None = None,
) -> httpx.Response:
    """Build a mock httpx.Response."""
    content = json.dumps(json_data).encode() if json_data is not None else b""
    return httpx.Response(
        status_code=status_code,
        content=content,
        headers=headers or {},
        request=httpx.Request("GET", _BASE_URL),
    )


# ---------------------------------------------------------------------------
# Token management
# ---------------------------------------------------------------------------


class TestTokenManagement:
    def test_get_token_calls_credential(self) -> None:
        cred = MagicMock()
        cred.get_token.return_value = MagicMock(token="tok-123", expires_on=9999999999.0)
        client = ApiCenterDataPlaneClient(base_url=_BASE_URL, credential=cred)
        token = client._get_token()
        assert token == "tok-123"
        cred.get_token.assert_called_once_with(_DATA_PLANE_SCOPE)

    def test_token_is_cached(self) -> None:
        cred = MagicMock()
        cred.get_token.return_value = MagicMock(token="tok-123", expires_on=9999999999.0)
        client = ApiCenterDataPlaneClient(base_url=_BASE_URL, credential=cred)
        client._get_token()
        client._get_token()
        assert cred.get_token.call_count == 1


# ---------------------------------------------------------------------------
# list_apis
# ---------------------------------------------------------------------------


class TestListApis:
    def test_returns_list_of_apis(self) -> None:
        client = _make_client()
        resp = _mock_response(json_data={"value": [SAMPLE_API], "nextLink": None})
        with patch.object(client, "_client") as mock_http:
            mock_http.return_value.get.return_value = resp
            result = client.list_apis()
        assert len(result) == 1
        assert result[0]["name"] == "petstore-api"

    def test_follows_pagination(self) -> None:
        client = _make_client()
        page1 = _mock_response(
            json_data={
                "value": [SAMPLE_API],
                "nextLink": f"{_BASE_URL}/workspaces/default/apis?skip=1",
            }
        )
        page2 = _mock_response(json_data={"value": [{"name": "api-2"}], "nextLink": None})
        with patch.object(client, "_client") as mock_http:
            mock_http.return_value.get.side_effect = [page1, page2]
            result = client.list_apis()
        assert len(result) == 2

    def test_not_found_raises_domain_error(self) -> None:
        client = _make_client()
        resp = _mock_response(status_code=404, json_data={"error": {"message": "not found"}})
        with patch.object(client, "_client") as mock_http:
            mock_http.return_value.get.return_value = resp
            with pytest.raises(ApiCenterNotFoundError):
                client.list_apis()

    def test_auth_error_raises_domain_error(self) -> None:
        client = _make_client()
        resp = _mock_response(status_code=401, json_data={"error": {"message": "Unauthorized"}})
        with patch.object(client, "_client") as mock_http:
            mock_http.return_value.get.return_value = resp
            with pytest.raises(ApiCenterAuthError):
                client.list_apis()

    def test_forbidden_raises_auth_error(self) -> None:
        client = _make_client()
        resp = _mock_response(status_code=403, json_data={"error": {"message": "Forbidden"}})
        with patch.object(client, "_client") as mock_http:
            mock_http.return_value.get.return_value = resp
            with pytest.raises(ApiCenterAuthError):
                client.list_apis()

    def test_service_unavailable_raises_domain_error(self) -> None:
        client = _make_client()
        resp = _mock_response(status_code=503, json_data={"error": {"message": "Service Unavailable"}})
        with patch.object(client, "_client") as mock_http:
            mock_http.return_value.get.return_value = resp
            with pytest.raises(ApiCenterUnavailableError):
                client.list_apis()

    def test_generic_http_error_raises_client_error(self) -> None:
        client = _make_client()
        resp = _mock_response(status_code=400, json_data={"error": {"message": "Bad Request"}})
        with patch.object(client, "_client") as mock_http:
            mock_http.return_value.get.return_value = resp
            with pytest.raises(ApiCenterClientError) as exc_info:
                client.list_apis()
            assert exc_info.value.status_code == 400


# ---------------------------------------------------------------------------
# get_api
# ---------------------------------------------------------------------------


class TestGetApi:
    def test_returns_single_api(self) -> None:
        client = _make_client()
        resp = _mock_response(json_data=SAMPLE_API)
        with patch.object(client, "_client") as mock_http:
            mock_http.return_value.get.return_value = resp
            result = client.get_api("petstore-api")
        assert result["name"] == "petstore-api"
        assert result["title"] == "Petstore API"

    def test_not_found_raises_domain_error(self) -> None:
        client = _make_client()
        resp = _mock_response(status_code=404, json_data={"error": {"message": "not found"}})
        with patch.object(client, "_client") as mock_http:
            mock_http.return_value.get.return_value = resp
            with pytest.raises(ApiCenterNotFoundError):
                client.get_api("missing-api")


# ---------------------------------------------------------------------------
# list_api_versions
# ---------------------------------------------------------------------------


class TestListApiVersions:
    def test_returns_list(self) -> None:
        client = _make_client()
        resp = _mock_response(json_data={"value": [SAMPLE_VERSION]})
        with patch.object(client, "_client") as mock_http:
            mock_http.return_value.get.return_value = resp
            result = client.list_api_versions("petstore-api")
        assert len(result) == 1
        assert result[0]["name"] == "v1"


# ---------------------------------------------------------------------------
# list_api_definitions
# ---------------------------------------------------------------------------


class TestListApiDefinitions:
    def test_returns_list(self) -> None:
        client = _make_client()
        resp = _mock_response(json_data={"value": [SAMPLE_DEFINITION]})
        with patch.object(client, "_client") as mock_http:
            mock_http.return_value.get.return_value = resp
            result = client.list_api_definitions("petstore-api", "v1")
        assert len(result) == 1
        assert result[0]["name"] == "openapi"


# ---------------------------------------------------------------------------
# export_api_specification
# ---------------------------------------------------------------------------


class TestExportApiSpecification:
    def test_returns_spec_content_from_sync_200(self) -> None:
        client = _make_client()
        resp = _mock_response(
            status_code=200,
            json_data={
                "status": "Succeeded",
                "result": {"value": '{"openapi": "3.0.1"}', "format": "inline"},
            },
        )
        with patch.object(client, "_client") as mock_http:
            mock_http.return_value.post.return_value = resp
            result = client.export_api_specification("petstore-api", "v1", "openapi")
        assert result == '{"openapi": "3.0.1"}'

    def test_returns_spec_content_from_async_202(self) -> None:
        client = _make_client()
        accept_resp = _mock_response(
            status_code=202,
            json_data={},
            headers={"Operation-Location": f"{_BASE_URL}/operations/op-123"},
        )
        poll_resp = _mock_response(
            status_code=200,
            json_data={
                "status": "Succeeded",
                "result": {"value": '{"openapi": "3.0.1"}'},
            },
        )
        with (
            patch.object(client, "_client") as mock_http,
            patch("apic_client.client.time.sleep"),
        ):
            mock_http.return_value.post.return_value = accept_resp
            mock_http.return_value.get.return_value = poll_resp
            result = client.export_api_specification("petstore-api", "v1", "openapi")
        assert result == '{"openapi": "3.0.1"}'

    def test_returns_none_when_result_is_empty(self) -> None:
        client = _make_client()
        resp = _mock_response(
            status_code=200,
            json_data={"status": "Succeeded", "result": {"value": None}},
        )
        with patch.object(client, "_client") as mock_http:
            mock_http.return_value.post.return_value = resp
            result = client.export_api_specification("petstore-api", "v1", "openapi")
        assert result is None

    def test_poll_failure_raises_client_error(self) -> None:
        client = _make_client()
        accept_resp = _mock_response(
            status_code=202,
            json_data={},
            headers={"Operation-Location": f"{_BASE_URL}/operations/op-123"},
        )
        poll_resp = _mock_response(
            status_code=200,
            json_data={"status": "Failed", "error": {"message": "Export failed"}},
        )
        with (
            patch.object(client, "_client") as mock_http,
            patch("apic_client.client.time.sleep"),
        ):
            mock_http.return_value.post.return_value = accept_resp
            mock_http.return_value.get.return_value = poll_resp
            with pytest.raises(ApiCenterClientError, match="Export failed"):
                client.export_api_specification("petstore-api", "v1", "openapi")

    def test_returns_spec_content_from_link_format_sync_200(self) -> None:
        """When format is 'link', the value is a URL; the spec must be fetched from it."""
        client = _make_client()
        spec_url = "https://storage.example.com/specs/petstore.json?sas=token"
        post_resp = _mock_response(
            status_code=200,
            json_data={
                "status": "Succeeded",
                "result": {"value": spec_url, "format": "link"},
            },
        )
        link_resp = httpx.Response(
            status_code=200,
            content=b'{"openapi": "3.0.1"}',
            headers={"content-type": "application/json"},
            request=httpx.Request("GET", spec_url),
        )
        with (
            patch.object(client, "_client") as mock_http,
            patch("apic_client.client.httpx.get", return_value=link_resp) as mock_get,
        ):
            mock_http.return_value.post.return_value = post_resp
            result = client.export_api_specification("petstore-api", "v1", "openapi")
        mock_get.assert_called_once_with(spec_url, timeout=30.0)
        assert result == '{"openapi": "3.0.1"}'

    def test_returns_spec_content_from_link_format_async_202(self) -> None:
        """link format works correctly in the async (202) polling path."""
        client = _make_client()
        spec_url = "https://storage.example.com/specs/petstore.json?sas=token"
        accept_resp = _mock_response(
            status_code=202,
            json_data={},
            headers={"Operation-Location": f"{_BASE_URL}/operations/op-456"},
        )
        poll_resp = _mock_response(
            status_code=200,
            json_data={
                "status": "Succeeded",
                "result": {"value": spec_url, "format": "link"},
            },
        )
        link_resp = httpx.Response(
            status_code=200,
            content=b'{"openapi": "3.0.1"}',
            headers={"content-type": "application/json"},
            request=httpx.Request("GET", spec_url),
        )
        with (
            patch.object(client, "_client") as mock_http,
            patch("apic_client.client.time.sleep"),
            patch("apic_client.client.httpx.get", return_value=link_resp) as mock_get,
        ):
            mock_http.return_value.post.return_value = accept_resp
            mock_http.return_value.get.return_value = poll_resp
            result = client.export_api_specification("petstore-api", "v1", "openapi")
        mock_get.assert_called_once_with(spec_url, timeout=30.0)
        assert result == '{"openapi": "3.0.1"}'


# ---------------------------------------------------------------------------
# list_environments
# ---------------------------------------------------------------------------


class TestListEnvironments:
    def test_returns_list(self) -> None:
        client = _make_client()
        resp = _mock_response(json_data={"value": [SAMPLE_ENVIRONMENT]})
        with patch.object(client, "_client") as mock_http:
            mock_http.return_value.get.return_value = resp
            result = client.list_environments()
        assert len(result) == 1
        assert result[0]["name"] == "prod-env"


# ---------------------------------------------------------------------------
# list_deployments
# ---------------------------------------------------------------------------


class TestListDeployments:
    def test_returns_list(self) -> None:
        client = _make_client()
        resp = _mock_response(json_data={"value": [SAMPLE_DEPLOYMENT]})
        with patch.object(client, "_client") as mock_http:
            mock_http.return_value.get.return_value = resp
            result = client.list_deployments("petstore-api")
        assert len(result) == 1
        assert result[0]["name"] == "dep-v1"


# ---------------------------------------------------------------------------
# close
# ---------------------------------------------------------------------------


class TestClose:
    def test_close_clears_http_client(self) -> None:
        client = _make_client()
        # Force client creation
        _ = client._client()
        client.close()
        assert client._http is None

    def test_close_is_idempotent(self) -> None:
        client = _make_client()
        client.close()
        client.close()  # Should not raise


# ---------------------------------------------------------------------------
# Error response parsing
# ---------------------------------------------------------------------------


class TestErrorParsing:
    def test_non_json_error_body(self) -> None:
        client = _make_client()
        resp = httpx.Response(
            status_code=500,
            content=b"Internal Server Error",
            request=httpx.Request("GET", _BASE_URL),
        )
        with patch.object(client, "_client") as mock_http:
            mock_http.return_value.get.return_value = resp
            with pytest.raises(ApiCenterUnavailableError):
                client.list_apis()
