"""Pytest fixtures for the backup job tests."""

from __future__ import annotations

from typing import Any

import pytest


@pytest.fixture
def fake_apic_client() -> Any:
    """Return a fake API Center client returning a small fixed catalog."""

    class _FakeApiCenterClient:
        def __init__(self) -> None:
            self.exported: list[tuple[str, str, str]] = []

        def list_apis(self) -> list[dict]:
            return [
                {"name": "petstore", "properties": {"title": "Petstore"}},
                {"name": "weather", "properties": {"title": "Weather"}},
            ]

        def list_api_versions(self, api_name: str) -> list[dict]:
            return [{"name": "v1"}]

        def list_api_definitions(self, api_name: str, version_name: str) -> list[dict]:
            return [{"name": "openapi", "specification": {"name": "openapi"}}]

        def export_api_specification(self, api_name: str, version_name: str, definition_name: str) -> str:
            self.exported.append((api_name, version_name, definition_name))
            return f'{{"openapi": "3.0.0", "info": {{"title": "{api_name}"}}}}'

        def list_environments(self) -> list[dict]:
            return [{"name": "production"}, {"name": "staging"}]

        def list_deployments(self, api_name: str) -> list[dict]:
            return [{"name": f"{api_name}-prod"}]

    return _FakeApiCenterClient()


@pytest.fixture
def fake_container_client() -> Any:
    """Return a fake blob ContainerClient that records uploads in memory."""

    class _FakeBlob:
        def __init__(self, name: str, url: str) -> None:
            self.name = name
            self.url = url

    class _FakeContainerClient:
        def __init__(self) -> None:
            self.uploads: dict[str, dict[str, Any]] = {}
            self.deletions: list[str] = []

        def upload_blob(
            self,
            name: str,
            data: bytes,
            *,
            overwrite: bool = False,
            metadata: dict[str, str] | None = None,
            content_settings: Any | None = None,
        ) -> _FakeBlob:
            self.uploads[name] = {
                "data": bytes(data),
                "metadata": dict(metadata or {}),
                "overwrite": overwrite,
            }
            return _FakeBlob(name=name, url=f"https://fake.blob/{name}")

        def get_blob_client(self, name: str) -> _FakeBlob:
            return _FakeBlob(name=name, url=f"https://fake.blob/{name}")

        def delete_blob(self, blob: str) -> None:
            self.deletions.append(blob)

    return _FakeContainerClient()


@pytest.fixture
def fake_metadata_container() -> Any:
    """Return a fake Cosmos container client."""

    class _FakeCosmosContainer:
        def __init__(self) -> None:
            self.items: dict[str, dict] = {}
            self.deleted: list[str] = []

        def upsert_item(self, body: dict) -> dict:
            self.items[body["id"]] = dict(body)
            return body

        def query_items(self, query: str, parameters=None, partition_key=None, **_: Any):
            del query, parameters, partition_key
            return list(self.items.values())

        def delete_item(self, item: str, partition_key: str) -> None:
            del partition_key
            self.deleted.append(item)
            self.items.pop(item, None)

        def read_item(self, item: str, partition_key: str) -> dict:
            del partition_key
            return self.items[item]

    return _FakeCosmosContainer()
