"""Async MCP client for the Streamable HTTP transport.

Communicates with MCP servers using the JSON-RPC 2.0 protocol over HTTP
(Streamable HTTP transport, MCP spec 2024-11-05).  Each request is a POST
to the server URL with a JSON-RPC body; the server replies with either a
plain ``application/json`` response or an SSE stream (``text/event-stream``).

Only the operations needed by the Inspector — ``initialize``, ``tools/list``,
``prompts/list``, ``resources/list``, and ``tools/call`` — are implemented.
"""

from __future__ import annotations

import json
import logging
from typing import Any

import aiohttp

logger = logging.getLogger(__name__)

MCP_PROTOCOL_VERSION = "2024-11-05"
_REQUEST_TIMEOUT = aiohttp.ClientTimeout(total=30)
_SSE_DATA_PREFIX = "data:"


class McpClientError(Exception):
    """Raised when the MCP client encounters a protocol or transport error."""

    def __init__(self, message: str, status_code: int | None = None) -> None:
        super().__init__(message)
        self.status_code = status_code


class McpClient:
    """Async MCP client using the Streamable HTTP transport.

    Parameters
    ----------
    server_url:
        The HTTP URL of the MCP server endpoint.  POST requests with
        JSON-RPC bodies are sent directly to this URL.
    bearer_token:
        Optional bearer token forwarded to the upstream server in the
        ``Authorization`` header.
    """

    def __init__(self, server_url: str, bearer_token: str | None = None) -> None:
        self._server_url = server_url
        self._bearer_token = bearer_token
        self._request_id = 0

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _next_id(self) -> int:
        self._request_id += 1
        return self._request_id

    def _make_headers(self) -> dict[str, str]:
        headers: dict[str, str] = {
            "Content-Type": "application/json",
            "Accept": "application/json, text/event-stream",
        }
        if self._bearer_token:
            headers["Authorization"] = f"Bearer {self._bearer_token}"
        return headers

    async def _send(self, method: str, params: dict[str, Any] | None = None) -> Any:
        """Send a JSON-RPC 2.0 request and return the ``result`` value.

        Handles both plain JSON and SSE streaming responses.

        Raises
        ------
        McpClientError
            On HTTP errors, JSON-RPC errors, or network failures.
        """
        payload: dict[str, Any] = {
            "jsonrpc": "2.0",
            "id": self._next_id(),
            "method": method,
        }
        if params is not None:
            payload["params"] = params

        logger.debug("mcp_request", extra={"method": method, "url": self._server_url})

        try:
            async with aiohttp.ClientSession(timeout=_REQUEST_TIMEOUT) as session:
                async with session.post(
                    self._server_url,
                    json=payload,
                    headers=self._make_headers(),
                ) as response:
                    if response.status >= 400:
                        body = await response.text()
                        raise McpClientError(
                            f"MCP server returned HTTP {response.status}: {body}",
                            status_code=response.status,
                        )

                    content_type = response.headers.get("Content-Type", "")
                    if "text/event-stream" in content_type:
                        return await self._read_sse_result(response)

                    data = await response.json(content_type=None)
                    return self._extract_result(data)

        except McpClientError:
            raise
        except aiohttp.ClientError as exc:
            raise McpClientError(f"Network error connecting to MCP server: {exc}") from exc

    @staticmethod
    def _extract_result(data: Any) -> Any:
        """Extract the ``result`` field from a JSON-RPC response dict."""
        if not isinstance(data, dict):
            return data
        if "error" in data:
            err = data["error"]
            msg = err.get("message", str(err)) if isinstance(err, dict) else str(err)
            raise McpClientError(f"MCP JSON-RPC error: {msg}")
        return data.get("result")

    @staticmethod
    async def _read_sse_result(response: aiohttp.ClientResponse) -> Any:
        """Parse the first complete JSON-RPC result from an SSE stream."""
        async for raw_line in response.content:
            line = raw_line.decode("utf-8", errors="replace").rstrip("\r\n")
            if not line.startswith(_SSE_DATA_PREFIX):
                continue
            data_str = line[len(_SSE_DATA_PREFIX) :].lstrip(" ")
            if data_str == "[DONE]":
                break
            try:
                data = json.loads(data_str)
            except json.JSONDecodeError:
                continue
            if "result" in data:
                return data["result"]
            if "error" in data:
                err = data["error"]
                msg = err.get("message", str(err)) if isinstance(err, dict) else str(err)
                raise McpClientError(f"MCP JSON-RPC error: {msg}")
        return None

    # ------------------------------------------------------------------
    # Public MCP operations
    # ------------------------------------------------------------------

    async def initialize(self) -> dict[str, Any]:
        """Send the MCP ``initialize`` handshake.

        Returns the server's ``InitializeResult`` (capabilities, version, etc.).
        """
        result = await self._send(
            "initialize",
            {
                "protocolVersion": MCP_PROTOCOL_VERSION,
                "capabilities": {},
                "clientInfo": {"name": "apic-vibe-portal", "version": "1.0.0"},
            },
        )
        return result if isinstance(result, dict) else {}

    async def list_tools(self) -> list[dict[str, Any]]:
        """Return the list of tools exposed by the server."""
        result = await self._send("tools/list")
        if not isinstance(result, dict):
            return []
        return result.get("tools") or []

    async def list_prompts(self) -> list[dict[str, Any]]:
        """Return the list of prompts exposed by the server."""
        result = await self._send("prompts/list")
        if not isinstance(result, dict):
            return []
        return result.get("prompts") or []

    async def list_resources(self) -> list[dict[str, Any]]:
        """Return the list of resources exposed by the server."""
        result = await self._send("resources/list")
        if not isinstance(result, dict):
            return []
        return result.get("resources") or []

    async def call_tool(self, name: str, arguments: dict[str, Any]) -> dict[str, Any]:
        """Invoke a tool by name and return the raw ``CallToolResult``."""
        result = await self._send("tools/call", {"name": name, "arguments": arguments})
        return result if isinstance(result, dict) else {}
