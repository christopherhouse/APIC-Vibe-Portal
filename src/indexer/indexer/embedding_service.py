"""Azure OpenAI embedding service.

Generates dense vector embeddings for API metadata using the Azure OpenAI
embeddings API.  Large spec content is chunked to fit within token limits
before generating a single averaged embedding vector.
"""

from __future__ import annotations

import logging

logger = logging.getLogger(__name__)

# Maximum characters per chunk when splitting large spec content.
# At ~4 chars/token this allows ~2 000 tokens per chunk, keeping
# the concatenated input well within the 8 192-token limit of
# text-embedding-ada-002.
_DEFAULT_CHUNK_SIZE = 8000


class EmbeddingService:
    """Generates embeddings via the Azure OpenAI embeddings API.

    Parameters
    ----------
    client:
        An ``openai.AzureOpenAI`` (or compatible) client instance.
    deployment:
        The Azure OpenAI deployment name for the embedding model
        (e.g. ``"text-embedding-ada-002"``).
    chunk_size:
        Maximum number of characters per chunk for large inputs.
    """

    def __init__(
        self,
        client: object,
        deployment: str = "text-embedding-ada-002",
        chunk_size: int = _DEFAULT_CHUNK_SIZE,
    ) -> None:
        self._client = client
        self._deployment = deployment
        self._chunk_size = chunk_size

    # ------------------------------------------------------------------
    # Public interface
    # ------------------------------------------------------------------

    def generate_embedding(self, title: str, description: str, spec_content: str | None) -> list[float]:
        """Return an embedding vector for the given API text.

        The embedding input is formed by concatenating *title*,
        *description*, and (optionally) *spec_content*.  When the
        combined text exceeds :attr:`chunk_size`, the spec content is
        chunked and each chunk is embedded independently; the final
        vector is the element-wise average of all chunk embeddings.

        Parameters
        ----------
        title:
            API display title.
        description:
            API description text.
        spec_content:
            Raw API specification content (OpenAPI JSON/YAML, etc.).
            Pass ``None`` or an empty string to skip.
        """
        base_text = f"{title} {description}".strip()
        if not spec_content:
            return self._embed(base_text)

        combined = f"{base_text} {spec_content}"
        if len(combined) <= self._chunk_size:
            return self._embed(combined)

        # Split spec_content into chunks and average the embeddings
        chunks = self._chunk_text(spec_content)
        chunk_texts = [f"{base_text} {chunk}" for chunk in chunks]

        logger.debug(
            "Chunking spec content for embedding",
            extra={"chunks": len(chunk_texts)},
        )

        vectors = [self._embed(t) for t in chunk_texts]
        return self._average_vectors(vectors)

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    def _embed(self, text: str) -> list[float]:
        """Call the Azure OpenAI embeddings endpoint and return the vector."""
        response = self._client.embeddings.create(
            input=text,
            model=self._deployment,
        )
        return response.data[0].embedding

    def _chunk_text(self, text: str) -> list[str]:
        """Split *text* into chunks of at most :attr:`chunk_size` characters."""
        return [text[i : i + self._chunk_size] for i in range(0, len(text), self._chunk_size)]

    @staticmethod
    def _average_vectors(vectors: list[list[float]]) -> list[float]:
        """Return the element-wise average of a list of equal-length vectors."""
        if not vectors:
            raise ValueError("Cannot average an empty list of vectors")
        length = len(vectors[0])
        result = [0.0] * length
        for vec in vectors:
            for i, val in enumerate(vec):
                result[i] += val
        n = len(vectors)
        return [v / n for v in result]
