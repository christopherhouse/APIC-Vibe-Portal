#!/usr/bin/env python3
"""Operational script — print Azure AI Search index statistics.

Usage
-----
    cd /path/to/repo
    python scripts/index_stats.py

Required environment variables (or set them in a .env file):
    AI_SEARCH_ENDPOINT

Optional:
    AI_SEARCH_INDEX_NAME (default: apic-apis)
    LOG_LEVEL            (default: INFO)
"""

from __future__ import annotations

import sys
from pathlib import Path

# Allow running from the repo root without installing the package
sys.path.insert(0, str(Path(__file__).parent.parent / "src" / "indexer"))

from indexer.config import get_settings  # noqa: E402


def main() -> None:
    import logging

    from azure.identity import DefaultAzureCredential
    from azure.search.documents.indexes import SearchIndexClient

    from indexer.indexer_service import IndexerService

    settings = get_settings()
    logging.basicConfig(level=getattr(logging, settings.log_level.upper(), logging.INFO))

    credential = DefaultAzureCredential()
    search_index_client = SearchIndexClient(
        endpoint=settings.ai_search_endpoint,
        credential=credential,
    )

    # search_client is not used for stats, pass a minimal stand-in
    from unittest.mock import MagicMock

    indexer = IndexerService(
        apic_client=MagicMock(),
        search_index_client=search_index_client,
        search_client=MagicMock(),
        embedding_service=MagicMock(),
        resource_group=settings.api_center_resource_group,
        service_name=settings.api_center_service_name,
        index_name=settings.ai_search_index_name,
    )

    stats = indexer.get_index_stats()
    print(f"Index:          {stats.index_name}")
    print(f"Document count: {stats.document_count}")


if __name__ == "__main__":
    main()
