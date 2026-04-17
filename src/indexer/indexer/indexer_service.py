"""AI Search indexing service.

Orchestrates the full and incremental indexing pipelines: fetches API
metadata from Azure API Center via the **data-plane** REST API, generates
embeddings via Azure OpenAI, and upserts/deletes documents in the Azure AI
Search index.

The data-plane API returns flat JSON objects where all fields (``title``,
``description``, ``kind``, ``lifecycleStage``, ``contacts``, etc.) live
directly on the object — there is no ARM envelope ``properties`` sub-object.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any

import structlog

logger = structlog.get_logger()


@dataclass
class IndexStats:
    """Basic statistics about the search index."""

    document_count: int
    index_name: str


class IndexerService:
    """Indexes Azure API Center data into Azure AI Search.

    Parameters
    ----------
    apic_client:
        An :class:`apic_client.ApiCenterDataPlaneClient` instance (or
        compatible mock) used to fetch API metadata.
    search_index_client:
        An ``azure.search.documents.indexes.SearchIndexClient`` used to
        create / update the index schema.
    search_client:
        An ``azure.search.documents.SearchClient`` used to upload and delete
        documents.
    embedding_service:
        An :class:`~indexer.embedding_service.EmbeddingService` that
        generates vector embeddings for each API document.
    index_name:
        Target AI Search index name.
    workspace_name:
        API Center workspace name (default: ``"default"``).
    """

    def __init__(
        self,
        apic_client: object,
        search_index_client: object,
        search_client: object,
        embedding_service: object,
        index_name: str,
        workspace_name: str = "default",
    ) -> None:
        self._apic = apic_client
        self._index_client = search_index_client
        self._search_client = search_client
        self._embeddings = embedding_service
        self._workspace_name = workspace_name
        self._index_name = index_name

    # ------------------------------------------------------------------
    # Index lifecycle
    # ------------------------------------------------------------------

    def ensure_index(self, index_schema: object) -> None:
        """Create or update the AI Search index with the given schema.

        Parameters
        ----------
        index_schema:
            A :class:`azure.search.documents.indexes.models.SearchIndex`
            built by :func:`~indexer.index_schema.build_index_schema`.
        """
        logger.info("Ensuring AI Search index exists", index=self._index_name)
        self._index_client.create_or_update_index(index_schema)
        logger.info("Index ready", index=self._index_name)

    # ------------------------------------------------------------------
    # Indexing operations
    # ------------------------------------------------------------------

    def full_reindex(self) -> int:
        """Fetch all APIs from API Center, generate embeddings, and upsert.

        Returns the number of documents indexed.
        """
        logger.info(
            "Starting full reindex",
            workspace=self._workspace_name,
        )

        apis: list[dict[str, Any]] = self._apic.list_apis()
        logger.info("Fetched APIs from API Center", count=len(apis))

        if not apis:
            logger.warning(
                "No APIs found in API Center — nothing to index. "
                "Verify that the endpoint and workspace are correct, "
                "and that the identity has the "
                "'Azure API Center Data Reader' role assignment.",
                workspace=self._workspace_name,
            )
            return 0

        documents = []
        for i, api in enumerate(apis, start=1):
            api_name = api.get("name", "<unknown>") or "<unknown>"
            api_title = api.get("title", "") or ""
            logger.info(
                "Processing API",
                progress=f"{i}/{len(apis)}",
                api_name=api_name,
                title=api_title,
            )
            doc = self._build_document(api)
            documents.append(doc)

        result = self._search_client.upload_documents(documents=documents)
        succeeded = sum(1 for r in result if r.succeeded)
        failed = len(documents) - succeeded
        logger.info(
            "Upserted documents into search index",
            succeeded=succeeded,
            failed=failed,
            total=len(documents),
        )
        if failed:
            logger.warning(
                "Some documents failed to upload",
                failed=failed,
                total=len(documents),
            )
        return succeeded

    def incremental_index(self, api_name: str) -> bool:
        """Fetch and reindex a single API by name.

        Parameters
        ----------
        api_name:
            The API Center API name (resource name, not display title).

        Returns ``True`` if the document was successfully indexed.
        """
        logger.info("Incremental index", api=api_name)

        api: dict[str, Any] = self._apic.get_api(api_name)
        doc = self._build_document(api)
        result = self._search_client.upload_documents(documents=[doc])
        succeeded = result[0].succeeded if result else False
        logger.info("Incremental index result", api=api_name, succeeded=succeeded)
        return bool(succeeded)

    def delete_from_index(self, api_id: str) -> bool:
        """Remove a document from the search index by its ID.

        Parameters
        ----------
        api_id:
            The ``id`` field value used when the document was indexed.

        Returns ``True`` if the deletion was acknowledged.
        """
        logger.info("Deleting document from index", id=api_id)
        result = self._search_client.delete_documents(documents=[{"id": api_id}])
        succeeded = result[0].succeeded if result else False
        logger.info("Delete result", id=api_id, succeeded=succeeded)
        return bool(succeeded)

    def get_index_stats(self) -> IndexStats:
        """Return basic statistics about the search index."""
        stats = self._index_client.get_index_statistics(self._index_name)
        return IndexStats(
            document_count=stats.document_count,
            index_name=self._index_name,
        )

    # ------------------------------------------------------------------
    # Document construction
    # ------------------------------------------------------------------

    def _build_document(self, api: dict[str, Any]) -> dict[str, object]:
        """Convert an API Center data-plane API dict into an AI Search document.

        Generates an embedding vector by combining the title, description,
        and (if available) the first version's spec content.
        """
        api_name: str = api.get("name", "") or ""
        title: str = api.get("title", "") or ""
        description: str = api.get("description", "") or ""
        kind: str = str(api.get("kind", "") or "")
        lifecycle_stage: str = str(api.get("lifecycleStage", "") or "")

        # Contacts as serialisable strings
        raw_contacts: list[dict[str, str]] = api.get("contacts") or []
        contacts: list[str] = [self._contact_to_str(c) for c in raw_contacts]

        # Tags (custom_properties keys used as a tag proxy if no tags field)
        custom_props: dict[str, object] = api.get("customProperties") or {}
        tags: list[str] = list(custom_props.keys()) if custom_props else []

        # Versions (names only)
        try:
            raw_versions: list[dict[str, Any]] = self._apic.list_api_versions(api_name)
            versions: list[str] = [v.get("name", "") or "" for v in raw_versions]
            logger.debug("Fetched versions", api_name=api_name, versions=versions)
        except Exception as exc:  # noqa: BLE001
            logger.warning(
                "Failed to list versions for API",
                api_name=api_name,
                error=str(exc),
            )
            versions = []

        # Spec content from first available version/definition
        spec_content: str | None = self._fetch_spec_content(api_name, versions)
        logger.debug(
            "Spec content lookup",
            api_name=api_name,
            spec_found=spec_content is not None,
        )

        # Timestamps — data-plane uses ``lastUpdated`` (ISO 8601 string)
        last_updated_str: str | None = api.get("lastUpdated")
        created_at: datetime | None = None
        updated_at: datetime | None = None
        if last_updated_str:
            try:
                updated_at = datetime.fromisoformat(last_updated_str)
            except ValueError, TypeError:
                pass

        # Embedding vector
        vector = self._embeddings.generate_embedding(title, description, spec_content)

        doc: dict[str, object] = {
            "id": api_name,
            "apiName": api_name,
            "title": title,
            "description": description,
            "kind": kind,
            "lifecycleStage": lifecycle_stage,
            "versions": versions,
            "contacts": contacts,
            "tags": tags,
            "customProperties": json.dumps(custom_props) if custom_props else "",
            "specContent": spec_content or "",
            "contentVector": vector,
        }
        if created_at is not None:
            if created_at.tzinfo is None:
                created_at = created_at.replace(tzinfo=UTC)
            doc["createdAt"] = created_at
        if updated_at is not None:
            if updated_at.tzinfo is None:
                updated_at = updated_at.replace(tzinfo=UTC)
            doc["updatedAt"] = updated_at

        return doc

    def _fetch_spec_content(self, api_name: str, versions: list[str]) -> str | None:
        """Fetch the raw spec content for the first available definition."""
        for version_name in versions:
            try:
                defs: list[dict[str, Any]] = self._apic.list_api_definitions(api_name, version_name)
                if not defs:
                    logger.debug(
                        "No definitions found for version",
                        api_name=api_name,
                        version=version_name,
                    )
                    continue
                def_name = defs[0].get("name")
                if def_name is None:
                    continue
                logger.debug(
                    "Exporting spec content",
                    api_name=api_name,
                    version=version_name,
                    definition=def_name,
                )
                content = self._apic.export_api_specification(api_name, version_name, def_name)
                return content if content else None
            except Exception as exc:  # noqa: BLE001
                logger.warning(
                    "Failed to fetch spec content for API",
                    api_name=api_name,
                    version=version_name,
                    error=str(exc),
                )
                continue
        return None

    @staticmethod
    def _contact_to_str(contact: dict[str, str] | object) -> str:
        """Serialise a contact object/dict to a human-readable string."""
        if isinstance(contact, dict):
            name = contact.get("name", "") or ""
            email = contact.get("email", "") or ""
        else:
            name = getattr(contact, "name", None) or ""
            email = getattr(contact, "email", None) or ""
        if email:
            return f"{name} <{email}>" if name else email
        return name
