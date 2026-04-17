"""AI Search indexing service.

Orchestrates the full and incremental indexing pipelines: fetches API
metadata from Azure API Center, generates embeddings via Azure OpenAI, and
upserts/deletes documents in the Azure AI Search index.

The Azure ``Api`` SDK model follows the ARM resource pattern: most user-facing
fields (``title``, ``description``, ``kind``, etc.) live under
``api.properties``, **not** directly on the ``Api`` object.  Only ARM envelope
fields (``name``, ``id``, ``type``, ``system_data``) are top-level.  The
helper :meth:`_props` centralises this access pattern so callers never need
to worry about the nesting.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import UTC, datetime

import structlog
from azure.core.exceptions import HttpResponseError, ResourceNotFoundError

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
            service=self._service_name,
            resource_group=self._resource_group,
            workspace=self._workspace_name,
        )

        # Verify the configured workspace exists before listing APIs.
        self._verify_workspace()

        apis = list(
            self._apic.apis.list(
                resource_group_name=self._resource_group,
                service_name=self._service_name,
                workspace_name=self._workspace_name,
            )
        )
        logger.info("Fetched APIs from API Center", count=len(apis))

        if not apis:
            logger.warning(
                "No APIs found in API Center — nothing to index. "
                "Verify that the resource group, service name, and workspace "
                "are correct, and that the indexer identity has the "
                "'Azure API Center Data Reader' role assignment.",
                resource_group=self._resource_group,
                service=self._service_name,
                workspace=self._workspace_name,
            )
            return 0

        documents = []
        for i, api in enumerate(apis, start=1):
            api_name = getattr(api, "name", "<unknown>") or "<unknown>"
            props = self._props(api)
            api_title = getattr(props, "title", "") or ""
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

        api = self._apic.apis.get(
            resource_group_name=self._resource_group,
            service_name=self._service_name,
            workspace_name=self._workspace_name,
            api_name=api_name,
        )
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
    # Workspace verification
    # ------------------------------------------------------------------

    def _verify_workspace(self) -> None:
        """List available workspaces and warn if the configured one is missing."""
        try:
            workspaces = list(
                self._apic.workspaces.list(
                    resource_group_name=self._resource_group,
                    service_name=self._service_name,
                )
            )
            workspace_names = [getattr(w, "name", "<unknown>") for w in workspaces]
            logger.info(
                "Available API Center workspaces",
                workspaces=workspace_names,
                configured_workspace=self._workspace_name,
            )
            if self._workspace_name not in workspace_names:
                logger.error(
                    "Configured workspace does not exist in API Center. "
                    "The indexer will not find any APIs. Update the "
                    "API_CENTER_WORKSPACE_NAME setting to one of the "
                    "available workspaces.",
                    configured_workspace=self._workspace_name,
                    available_workspaces=workspace_names,
                )
        except Exception as exc:  # noqa: BLE001
            logger.warning(
                "Unable to list API Center workspaces — workspace "
                "verification skipped. This may indicate a permissions "
                "issue with the indexer identity.",
                error=str(exc),
            )

    # ------------------------------------------------------------------
    # Document construction
    # ------------------------------------------------------------------

    @staticmethod
    def _props(api: object) -> object:
        """Return the ``properties`` sub-object of an ARM API resource.

        The Azure ``Api`` SDK model places user-facing fields (``title``,
        ``description``, ``kind``, ``contacts``, etc.) under
        ``api.properties``.  Only ARM envelope fields (``name``, ``id``,
        ``type``, ``system_data``) are directly on the ``Api`` object.

        If the object does *not* have a ``properties`` attribute (e.g. in
        tests using plain ``SimpleNamespace`` objects) the object itself
        is returned so that the legacy ``getattr(api, "title", …)`` style
        continues to work.
        """
        props = getattr(api, "properties", None)
        return props if props is not None else api

    def _build_document(self, api: object) -> dict[str, object]:
        """Convert an API Center API object into an AI Search document.

        Generates an embedding vector by combining the title, description,
        and (if available) the first version's spec content.
        """
        # ARM envelope field — lives directly on the Api object.
        api_name: str = getattr(api, "name", "") or ""

        # All other fields live under api.properties in the real SDK.
        props = self._props(api)
        title: str = getattr(props, "title", "") or ""
        description: str = getattr(props, "description", "") or ""
        kind: str = str(getattr(props, "kind", "") or "")
        lifecycle_stage: str = str(getattr(props, "lifecycle_stage", "") or "")

        # Contacts as serialisable strings
        raw_contacts = getattr(props, "contacts", None) or []
        contacts: list[str] = [self._contact_to_str(c) for c in raw_contacts]

        # Tags (custom_properties keys used as a tag proxy if no tags field)
        custom_props: dict[str, object] = getattr(props, "custom_properties", None) or {}
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
        """Fetch the raw spec content for the first available definition.

        Some API types (e.g. GraphQL) do not support spec download in Azure
        API Center and will return a 404.  This is expected — the API is still
        indexed but without spec content.
        """
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
                    logger.debug(
                        "No definitions found for version",
                        api_name=api_name,
                        version=version_name,
                    )
                    continue
                def_name = getattr(defs[0], "name", None)
                if def_name is None:
                    continue
                logger.debug(
                    "Exporting spec content",
                    api_name=api_name,
                    version=version_name,
                    definition=def_name,
                )
                poller = self._apic.api_definitions.begin_export_specification(
                    resource_group_name=self._resource_group,
                    service_name=self._service_name,
                    workspace_name=self._workspace_name,
                    api_name=api_name,
                    version_name=version_name,
                    definition_name=def_name,
                )
                result = poller.result()
                return result.value if result and result.value else None
            except ResourceNotFoundError:
                logger.info(
                    "Spec not available for API — this is expected for "
                    "some API types (e.g. GraphQL). The API will be "
                    "indexed without spec content.",
                    api_name=api_name,
                    version=version_name,
                )
                continue
            except HttpResponseError as exc:
                if exc.status_code == 404:
                    logger.info(
                        "Spec not available for API — this is expected for "
                        "some API types (e.g. GraphQL). The API will be "
                        "indexed without spec content.",
                        api_name=api_name,
                        version=version_name,
                    )
                else:
                    logger.warning(
                        "Failed to fetch spec content for API",
                        api_name=api_name,
                        version=version_name,
                        error=str(exc),
                        status_code=exc.status_code,
                    )
                continue
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
    def _contact_to_str(contact: object) -> str:
        """Serialise a contact object to a human-readable string."""
        name = getattr(contact, "name", None) or ""
        email = getattr(contact, "email", None) or ""
        if email:
            return f"{name} <{email}>" if name else email
        return name
