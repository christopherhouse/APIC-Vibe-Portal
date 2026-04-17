"""AI Search indexing service.

Orchestrates the full and incremental indexing pipelines: fetches API
metadata from Azure API Center, generates embeddings via Azure OpenAI, and
upserts/deletes documents in the Azure AI Search index.
"""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass
from datetime import UTC, datetime

logger = logging.getLogger(__name__)


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
        An :class:`azure.mgmt.apicenter.ApiCenterMgmtClient` instance (or
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
    resource_group:
        Azure resource group containing the API Center service.
    service_name:
        API Center service name.
    workspace_name:
        API Center workspace name (default: ``"default"``).
    index_name:
        Target AI Search index name.
    """

    def __init__(
        self,
        apic_client: object,
        search_index_client: object,
        search_client: object,
        embedding_service: object,
        resource_group: str,
        service_name: str,
        index_name: str,
        workspace_name: str = "default",
    ) -> None:
        self._apic = apic_client
        self._index_client = search_index_client
        self._search_client = search_client
        self._embeddings = embedding_service
        self._resource_group = resource_group
        self._service_name = service_name
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
        logger.info("Ensuring AI Search index exists", extra={"index": self._index_name})
        self._index_client.create_or_update_index(index_schema)
        logger.info("Index ready", extra={"index": self._index_name})

    # ------------------------------------------------------------------
    # Indexing operations
    # ------------------------------------------------------------------

    def full_reindex(self) -> int:
        """Fetch all APIs from API Center, generate embeddings, and upsert.

        Returns the number of documents indexed.
        """
        logger.info("Starting full reindex", extra={"service": self._service_name})

        apis = list(
            self._apic.apis.list(
                resource_group_name=self._resource_group,
                service_name=self._service_name,
                workspace_name=self._workspace_name,
            )
        )
        logger.info("Fetched APIs from API Center", extra={"count": len(apis)})

        documents = []
        for api in apis:
            doc = self._build_document(api)
            documents.append(doc)

        if documents:
            result = self._search_client.upload_documents(documents=documents)
            succeeded = sum(1 for r in result if r.succeeded)
            logger.info("Upserted documents", extra={"succeeded": succeeded, "total": len(documents)})
            return succeeded

        logger.info("No APIs found; nothing to index")
        return 0

    def incremental_index(self, api_name: str) -> bool:
        """Fetch and reindex a single API by name.

        Parameters
        ----------
        api_name:
            The API Center API name (resource name, not display title).

        Returns ``True`` if the document was successfully indexed.
        """
        logger.info("Incremental index", extra={"api": api_name})

        api = self._apic.apis.get(
            resource_group_name=self._resource_group,
            service_name=self._service_name,
            workspace_name=self._workspace_name,
            api_name=api_name,
        )
        doc = self._build_document(api)
        result = self._search_client.upload_documents(documents=[doc])
        succeeded = result[0].succeeded if result else False
        logger.info("Incremental index result", extra={"api": api_name, "succeeded": succeeded})
        return bool(succeeded)

    def delete_from_index(self, api_id: str) -> bool:
        """Remove a document from the search index by its ID.

        Parameters
        ----------
        api_id:
            The ``id`` field value used when the document was indexed.

        Returns ``True`` if the deletion was acknowledged.
        """
        logger.info("Deleting document from index", extra={"id": api_id})
        result = self._search_client.delete_documents(documents=[{"id": api_id}])
        succeeded = result[0].succeeded if result else False
        logger.info("Delete result", extra={"id": api_id, "succeeded": succeeded})
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

    def _build_document(self, api: object) -> dict[str, object]:
        """Convert an API Center API object into an AI Search document.

        Generates an embedding vector by combining the title, description,
        and (if available) the first version's spec content.
        """
        api_name: str = getattr(api, "name", "") or ""
        title: str = getattr(api, "title", "") or ""
        description: str = getattr(api, "description", "") or ""
        kind: str = str(getattr(api, "kind", "") or "")
        lifecycle_stage: str = str(getattr(api, "lifecycle_stage", "") or "")

        # Contacts as serialisable strings
        raw_contacts = getattr(api, "contacts", None) or []
        contacts: list[str] = [self._contact_to_str(c) for c in raw_contacts]

        # Tags (custom_properties keys used as a tag proxy if no tags field)
        custom_props: dict[str, object] = getattr(api, "custom_properties", None) or {}
        tags: list[str] = list(custom_props.keys()) if custom_props else []

        # Versions (names only)
        try:
            raw_versions = list(
                self._apic.api_versions.list(
                    resource_group_name=self._resource_group,
                    service_name=self._service_name,
                    workspace_name=self._workspace_name,
                    api_name=api_name,
                )
            )
            versions: list[str] = [getattr(v, "name", "") or "" for v in raw_versions]
        except Exception as exc:  # noqa: BLE001
            logger.warning(
                "Failed to list versions for API '%s': %s",
                api_name,
                exc,
                exc_info=True,
            )
            versions = []

        # Spec content from first available version/definition
        spec_content: str | None = self._fetch_spec_content(api_name, versions)

        # Timestamps from system_data — normalize to UTC-aware datetimes so
        # that the AI Search SDK serialises them as proper DateTimeOffset values.
        system_data = getattr(api, "system_data", None)
        created_at: datetime | None = getattr(system_data, "created_at", None)
        updated_at: datetime | None = getattr(system_data, "last_modified_at", None)

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
            # Ensure timezone-aware so the SDK serialises as DateTimeOffset
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
                defs = list(
                    self._apic.api_definitions.list(
                        resource_group_name=self._resource_group,
                        service_name=self._service_name,
                        workspace_name=self._workspace_name,
                        api_name=api_name,
                        version_name=version_name,
                    )
                )
                if not defs:
                    continue
                def_name = getattr(defs[0], "name", None)
                if def_name is None:
                    continue
                result = self._apic.api_definitions.export_specification(
                    resource_group_name=self._resource_group,
                    service_name=self._service_name,
                    workspace_name=self._workspace_name,
                    api_name=api_name,
                    version_name=version_name,
                    definition_name=def_name,
                )
                return result.value if result and result.value else None
            except Exception as exc:  # noqa: BLE001
                logger.warning(
                    "Failed to fetch spec content for api '%s', version '%s': %s",
                    api_name,
                    version_name,
                    exc,
                    exc_info=True,
                )
                continue
        return None

    @staticmethod
    def _contact_to_str(contact: object) -> str:
        """Serialise a contact object to a human-readable string."""
        name = getattr(contact, "name", None) or ""
        email = getattr(contact, "email", None) or ""
        if email:
            return f"{name} <{email}>" if name else email
        return name
