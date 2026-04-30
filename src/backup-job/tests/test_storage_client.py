"""Tests for :mod:`apic_backup.clients.storage_client`."""

from __future__ import annotations

import io

import pytest
from azure.core.exceptions import ResourceNotFoundError

from apic_backup.clients.storage_client import BackupStorageClient


class _FakeBlob:
    def __init__(self, name: str) -> None:
        self.name = name
        self.url = f"https://fake.blob/{name}"


def test_upload_backup_uses_bytes_path() -> None:
    captured: dict = {}

    class _Container:
        def upload_blob(self, name, data, **kwargs):
            captured["name"] = name
            captured["data"] = data
            captured["kwargs"] = kwargs
            return _FakeBlob(name)

    client = BackupStorageClient(_Container())
    url = client.upload_backup("foo.zip", b"abc", metadata={"x": "1"})

    assert url == "https://fake.blob/foo.zip"
    assert captured["data"] == b"abc"
    assert captured["kwargs"]["metadata"] == {"x": "1"}
    # bytes upload path does NOT pass length / max_concurrency
    assert "length" not in captured["kwargs"]


def test_upload_backup_stream_passes_length_and_concurrency() -> None:
    captured: dict = {}

    class _Container:
        def upload_blob(self, name, data, **kwargs):
            captured["name"] = name
            captured["data"] = data
            captured["kwargs"] = kwargs
            return _FakeBlob(name)

    client = BackupStorageClient(_Container())
    payload = b"hello-streamed"
    stream = io.BytesIO(payload)
    url = client.upload_backup_stream("stream.zip", stream, len(payload), metadata={"k": "v"})

    assert url == "https://fake.blob/stream.zip"
    assert captured["data"] is stream
    assert captured["kwargs"]["length"] == len(payload)
    assert captured["kwargs"]["max_concurrency"] == 4
    assert captured["kwargs"]["metadata"] == {"k": "v"}


def test_delete_backup_swallows_not_found() -> None:
    class _Container:
        def __init__(self) -> None:
            self.calls: list[str] = []

        def delete_blob(self, blob: str) -> None:
            self.calls.append(blob)
            raise ResourceNotFoundError("blob missing")

    container = _Container()
    BackupStorageClient(container).delete_backup("missing.zip")  # must not raise
    assert container.calls == ["missing.zip"]


def test_delete_backup_reraises_other_errors() -> None:
    class _Container:
        def delete_blob(self, blob: str) -> None:
            raise PermissionError("forbidden")

    with pytest.raises(PermissionError):
        BackupStorageClient(_Container()).delete_backup("any.zip")
