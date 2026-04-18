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
import re
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any

import structlog
from apic_client.exceptions import ApiCenterNotFoundError

logger = structlog.get_logger()

# Azure AI Search (Lucene) maximum term size in bytes.  Individual tokens
# in a ``searchable`` field that exceed this limit cause a 400 error on
# document upload.  We use a slightly lower value to leave room for any
# UTF-8 multi-byte characters.
_MAX_TERM_BYTES = 32_000


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

        Azure AI Search cannot add a suggester to an existing index whose
        source fields have already been tokenized without prefix sequences.
        When suggesters are expected but missing after ``create_or_update_index``
        this method deletes and recreates the index so the prefix tokenization
        is built from scratch.  The caller should follow up with a full
        reindex to repopulate the documents.

        Parameters
        ----------
        index_schema:
            A :class:`azure.search.documents.indexes.models.SearchIndex`
            built by :func:`~indexer.index_schema.build_index_schema`.
        """
        logger.info("Ensuring AI Search index exists", index=self._index_name)
        self._index_client.create_or_update_index(index_schema)

        # Verify the live index actually has the expected suggesters.
        expected_suggesters = getattr(index_schema, "suggesters", None) or []
        if expected_suggesters:
            self._reconcile_suggesters(index_schema, expected_suggesters)

        logger.info("Index ready", index=self._index_name)

    def _reconcile_suggesters(
        self,
        index_schema: object,
        expected_suggesters: list[object],
    ) -> None:
        """Delete and recreate the index if required suggesters are missing.

        Azure AI Search silently drops suggesters from an
        ``create_or_update_index`` call when the source fields were
        originally indexed without prefix tokenization.  This helper
        detects the mismatch and rebuilds the index.
        """
        live_index = self._index_client.get_index(self._index_name)
        live_suggester_names: set[str] = {s.name for s in (live_index.suggesters or [])}
        expected_names: set[str] = {s.name for s in expected_suggesters}
        missing = expected_names - live_suggester_names
        if not missing:
            return

        logger.warning(
            "Suggesters missing after index update — rebuilding index. "
            "Azure AI Search cannot add suggesters to preexisting fields; "
            "a full delete + recreate is required.",
            index=self._index_name,
            missing_suggesters=sorted(missing),
        )
        self._index_client.delete_index(self._index_name)
        self._index_client.create_or_update_index(index_schema)
        logger.info(
            "Index rebuilt with suggesters",
            index=self._index_name,
            suggesters=sorted(expected_names),
        )

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
            failed_details = [
                {
                    "key": getattr(r, "key", None),
                    "status_code": getattr(r, "status_code", None),
                    "error_message": getattr(r, "error_message", None),
                }
                for r in result
                if not r.succeeded
            ]
            logger.warning(
                "Some documents failed to upload",
                failed=failed,
                total=len(documents),
                failed_documents=failed_details,
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
        if succeeded:
            logger.info("Incremental index result", api=api_name, succeeded=succeeded)
        else:
            upload_result = result[0] if result else None
            logger.warning(
                "Incremental index failed to upload document",
                api=api_name,
                key=getattr(upload_result, "key", None),
                status_code=getattr(upload_result, "status_code", None),
                error_message=getattr(upload_result, "error_message", None),
            )
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
            # Normalize trailing "Z" (UTC) to "+00:00" for fromisoformat()
            normalized_last_updated = (
                last_updated_str[:-1] + "+00:00" if last_updated_str.endswith("Z") else last_updated_str
            )
            try:
                updated_at = datetime.fromisoformat(normalized_last_updated)
            except (ValueError, TypeError) as exc:
                logger.warning(
                    "Failed to parse API lastUpdated timestamp",
                    api_name=api_name,
                    last_updated=last_updated_str,
                    error=str(exc),
                )

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
            "specContent": self._sanitize_spec_content(spec_content or "", api_name),
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
        """Fetch the raw spec content for the first available definition.

        Some API types (e.g. GraphQL) do not support spec download in Azure
        API Center and will return a 404.  This is expected — the API is still
        indexed but without spec content.
        """
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
            except ApiCenterNotFoundError:
                self._log_spec_not_available(api_name, version_name)
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
    def _sanitize_spec_content(spec_content: str, api_name: str = "") -> str:
        """Prepare raw spec content for Azure AI Search indexing.

        Azure AI Search (Lucene) rejects documents whose ``searchable``
        fields contain individual terms longer than 32 766 UTF-8 bytes.
        OpenAPI specs stored as compact/minified JSON can easily exceed
        this limit because the standard text analyser tokenises on
        whitespace and punctuation — a minified JSON blob may consist of
        only a handful of extremely long tokens.

        This method applies two transformations in order:

        1. **Pretty-print JSON** — if the content is valid JSON, it is
           re-serialised with indentation so that every key, value, and
           structural character is separated by whitespace.  This lets the
           analyser split the text into short, meaningful tokens.
        2. **Truncate oversized tokens** — any remaining whitespace-
           delimited token whose UTF-8 byte length still exceeds the
           Lucene limit is truncated to fit.  This handles edge-cases
           like embedded base-64 blobs or extremely long URLs.
        """
        if not spec_content:
            return spec_content

        text = spec_content

        # Step 1: Pretty-print JSON to introduce whitespace for tokenisation.
        try:
            parsed = json.loads(text)
            text = json.dumps(parsed, indent=2, ensure_ascii=False)
            logger.debug(
                "Pretty-printed JSON spec content for indexing",
                api_name=api_name,
            )
        except (json.JSONDecodeError, TypeError, ValueError):
            # Not JSON (e.g. YAML, GraphQL SDL) — leave as-is.
            pass

        # Step 2: Truncate any individual tokens that still exceed the
        # Lucene per-term byte limit.
        def _truncate_token(match: re.Match[str]) -> str:
            token = match.group(0)
            if len(token.encode("utf-8")) <= _MAX_TERM_BYTES:
                return token
            # Truncate character-by-character until byte length fits.
            while len(token.encode("utf-8")) > _MAX_TERM_BYTES:
                token = token[: len(token) - 1]
            return token

        sanitized = re.sub(r"\S+", _truncate_token, text)

        if sanitized != spec_content:
            logger.info(
                "Sanitized spec content for AI Search indexing",
                api_name=api_name,
                original_len=len(spec_content),
                sanitized_len=len(sanitized),
            )

        return sanitized

    @staticmethod
    def _log_spec_not_available(api_name: str, version_name: str) -> None:
        """Log that a spec is not available — expected for some API types."""
        logger.info(
            "Spec not available for API — this is expected for "
            "some API types (e.g. GraphQL). The API will be "
            "indexed without spec content.",
            api_name=api_name,
            version=version_name,
        )

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
