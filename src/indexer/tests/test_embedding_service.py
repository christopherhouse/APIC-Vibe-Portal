"""Unit tests for EmbeddingService — mocked Azure OpenAI calls."""

from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest

from indexer.embedding_service import EmbeddingService


def _make_embedding_response(vector: list[float]) -> SimpleNamespace:
    """Build a minimal mock that mimics the openai embeddings response shape."""
    return SimpleNamespace(data=[SimpleNamespace(embedding=vector)])


def _make_service(vector: list[float] | None = None) -> tuple[EmbeddingService, MagicMock]:
    """Return a service wired to a mock OpenAI client."""
    mock_client = MagicMock()
    default_vector = vector if vector is not None else [0.1] * 1536
    mock_client.embeddings.create.return_value = _make_embedding_response(default_vector)
    service = EmbeddingService(client=mock_client, deployment="text-embedding-ada-002", chunk_size=100)
    return service, mock_client


class TestGenerateEmbedding:
    def test_returns_vector_for_short_input(self) -> None:
        service, mock_client = _make_service()

        result = service.generate_embedding("My API", "Does stuff", None)

        assert isinstance(result, list)
        assert len(result) == 1536
        mock_client.embeddings.create.assert_called_once()

    def test_combines_title_description_spec(self) -> None:
        service, mock_client = _make_service()

        service.generate_embedding("Title", "Desc", "spec content short")

        call_args = mock_client.embeddings.create.call_args
        input_text: str = call_args.kwargs["input"]
        assert "Title" in input_text
        assert "Desc" in input_text
        assert "spec content short" in input_text

    def test_no_spec_content_omits_spec(self) -> None:
        service, mock_client = _make_service()

        service.generate_embedding("Title", "Desc", None)

        call_args = mock_client.embeddings.create.call_args
        input_text: str = call_args.kwargs["input"]
        assert "Title" in input_text
        # Only one call — no chunking
        assert mock_client.embeddings.create.call_count == 1

    def test_empty_spec_content_treated_as_missing(self) -> None:
        service, mock_client = _make_service()

        service.generate_embedding("Title", "Desc", "")

        assert mock_client.embeddings.create.call_count == 1

    def test_large_spec_content_is_chunked(self) -> None:
        """chunk_size=100; spec >100 chars should trigger multiple embed calls."""
        service, mock_client = _make_service([0.5] * 1536)
        long_spec = "x" * 300  # 3 chunks of 100

        result = service.generate_embedding("T", "D", long_spec)

        # base_text = "T D" (3 chars) + spec = 303 > 100  → chunked
        assert mock_client.embeddings.create.call_count >= 2
        assert len(result) == 1536

    def test_average_vectors_computed_correctly(self) -> None:
        service, _ = _make_service()

        vecs = [[1.0, 2.0], [3.0, 4.0]]
        avg = service._average_vectors(vecs)

        assert avg == [2.0, 3.0]

    def test_average_vectors_raises_on_empty(self) -> None:
        service, _ = _make_service()

        with pytest.raises(ValueError, match="empty"):
            service._average_vectors([])

    def test_chunk_text_splits_correctly(self) -> None:
        service, _ = _make_service()

        chunks = service._chunk_text("abcdefghij")  # chunk_size=100, all in one
        assert chunks == ["abcdefghij"]

        service2 = EmbeddingService(client=MagicMock(), chunk_size=3)
        chunks2 = service2._chunk_text("abcdefghij")
        assert chunks2 == ["abc", "def", "ghi", "j"]
