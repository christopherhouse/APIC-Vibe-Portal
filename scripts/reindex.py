#!/usr/bin/env python3
"""Operational script — trigger a full reindex of API Center data.

Usage
-----
    cd /path/to/repo
    python scripts/reindex.py

Required environment variables (or set them in a .env file):
    AI_SEARCH_ENDPOINT
    OPENAI_ENDPOINT
    API_CENTER_ENDPOINT

Optional:
    AI_SEARCH_INDEX_NAME        (default: apic-apis)
    API_CENTER_WORKSPACE_NAME   (default: default)
    OPENAI_API_VERSION          (default: 2025-03-01-preview)
    OPENAI_EMBEDDING_DEPLOYMENT (default: text-embedding-ada-002)
    OPENAI_EMBEDDING_DIMENSIONS (default: 1536)
    LOG_LEVEL                   (default: INFO)
"""

from __future__ import annotations

import sys
from pathlib import Path

# Allow running from the repo root without installing the package
sys.path.insert(0, str(Path(__file__).parent.parent / "src" / "indexer"))
sys.path.insert(0, str(Path(__file__).parent.parent / "src" / "apic_client"))

from indexer.config import get_settings  # noqa: E402
from indexer.embedding_service import EmbeddingService  # noqa: E402
from indexer.index_schema import build_index_schema  # noqa: E402
from indexer.indexer_service import IndexerService  # noqa: E402


def main() -> None:
    import logging

    from apic_client import ApiCenterDataPlaneClient
    from azure.identity import DefaultAzureCredential
    from azure.search.documents import SearchClient
    from azure.search.documents.indexes import SearchIndexClient
    from openai import AzureOpenAI

    settings = get_settings()
    logging.basicConfig(level=getattr(logging, settings.log_level.upper(), logging.INFO))
    log = logging.getLogger(__name__)

    log.info("Starting full reindex…")

    credential = DefaultAzureCredential()

    apic_client = ApiCenterDataPlaneClient(
        base_url=settings.api_center_endpoint,
        workspace_name=settings.api_center_workspace_name,
        credential=credential,
    )
    search_index_client = SearchIndexClient(
        endpoint=settings.ai_search_endpoint,
        credential=credential,
    )
    search_client = SearchClient(
        endpoint=settings.ai_search_endpoint,
        index_name=settings.ai_search_index_name,
        credential=credential,
    )
    openai_client = AzureOpenAI(
        azure_endpoint=settings.openai_endpoint,
        azure_deployment=settings.openai_embedding_deployment,
        api_version=settings.openai_api_version,
        azure_ad_token_provider=lambda: credential.get_token(
            "https://cognitiveservices.azure.com/.default"
        ).token,
    )

    embedding_service = EmbeddingService(
        client=openai_client,
        deployment=settings.openai_embedding_deployment,
        chunk_size=settings.embedding_chunk_size,
    )
    indexer = IndexerService(
        apic_client=apic_client,
        search_index_client=search_index_client,
        search_client=search_client,
        embedding_service=embedding_service,
        index_name=settings.ai_search_index_name,
    )

    schema = build_index_schema(
        index_name=settings.ai_search_index_name,
        embedding_dimensions=settings.openai_embedding_dimensions,
    )
    indexer.ensure_index(schema)

    count = indexer.full_reindex()
    log.info("Reindex complete. Documents indexed: %d", count)


if __name__ == "__main__":
    main()
