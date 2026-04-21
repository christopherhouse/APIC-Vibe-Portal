"""Repository for API access policy documents.

Container: ``api-access-policies``, partition key: ``/apiName``.

Each document represents the access control rules for one API.  The ``id``
and ``apiName`` fields are identical, which allows both point-reads (by ID)
and cross-partition scans (list all policies) efficiently.
"""

from __future__ import annotations

import logging
from collections.abc import Callable
from datetime import UTC, datetime
from typing import TYPE_CHECKING, Any

from azure.cosmos.exceptions import CosmosResourceNotFoundError

from apic_vibe_portal_bff.data.models.api_access_policy import ApiAccessPolicyDocument
from apic_vibe_portal_bff.data.repositories.base_repository import BaseRepository

if TYPE_CHECKING:
    from azure.cosmos.container import ContainerProxy

logger = logging.getLogger(__name__)

_RU_CHARGE_HEADER = "x-ms-request-charge"


def _make_simple_ru_hook(container_name: str, operation: str) -> Callable[[dict, Any], None]:
    """Return a response_hook that logs RU cost for a Cosmos operation."""

    def _hook(response_headers: dict, result: Any) -> None:  # noqa: ANN401
        try:
            charge_str = response_headers.get(_RU_CHARGE_HEADER)
            if charge_str is None:
                return
            charge = float(charge_str)
            logger.debug(
                "cosmos.ru_charge",
                extra={"container": container_name, "operation": operation, "ru": charge},
            )
        except Exception:  # noqa: BLE001
            pass

    return _hook


class ApiAccessPolicyRepository(BaseRepository):
    """Data access for the ``api-access-policies`` container.

    Documents use the API's short name (``apiName``) as both the document ID
    and the partition key.  This allows efficient point-reads and full-scan
    queries without cross-partition fan-out.
    """

    _MIGRATIONS: dict = {}

    def __init__(self, container: ContainerProxy) -> None:
        super().__init__(container, partition_key_field="apiName")

    # ------------------------------------------------------------------
    # Migrations hook
    # ------------------------------------------------------------------

    def _apply_migrations(self, document: dict) -> dict:
        return document  # No migrations yet; reserved for future schema changes

    # ------------------------------------------------------------------
    # Domain-specific helpers
    # ------------------------------------------------------------------

    def get_policy(self, api_name: str) -> ApiAccessPolicyDocument | None:
        """Return the access policy for a specific API, or ``None`` if not set.

        ``None`` means the API has no explicit policy and is considered public.
        """
        doc = self.find_by_id(api_name, api_name)
        if doc is None:
            return None
        return ApiAccessPolicyDocument.model_validate(doc)

    def upsert_policy(self, policy: ApiAccessPolicyDocument) -> ApiAccessPolicyDocument:
        """Create or replace the access policy for an API.

        Uses Cosmos DB upsert semantics: creates the document if it does not
        exist, replaces it otherwise.
        """
        now = datetime.now(UTC).isoformat().replace("+00:00", "Z")
        body = policy.to_cosmos_dict()
        body["updatedAt"] = now

        result = self._container.upsert_item(
            body=body,
            response_hook=_make_simple_ru_hook(self._container.id, "upsert"),
        )
        return ApiAccessPolicyDocument.model_validate(result)

    def delete_policy(self, api_name: str) -> bool:
        """Hard-delete the access policy for an API.

        Returns ``True`` if the policy was found and deleted, ``False`` if it
        did not exist.  Hard-delete is appropriate here because access policies
        have no compliance/audit retention requirement beyond the live record.
        """
        return self.hard_delete(api_name, api_name)

    def list_all_policies(self) -> list[ApiAccessPolicyDocument]:
        """Return all non-deleted access policies across all APIs.

        This is a cross-partition query.  For a large catalog (thousands of
        APIs) the caller should consider caching the result rather than
        calling this on every request.
        """
        query = "SELECT * FROM c WHERE NOT IS_DEFINED(c.isDeleted) OR c.isDeleted = false"
        try:
            items = list(
                self._container.query_items(
                    query=query,
                    enable_cross_partition_query=True,
                    response_hook=_make_simple_ru_hook(self._container.id, "list_all"),
                )
            )
        except CosmosResourceNotFoundError:
            logger.warning("api_access_policy_repository.list_all: container not found")
            return []

        policies: list[ApiAccessPolicyDocument] = []
        for doc in items:
            try:
                policies.append(ApiAccessPolicyDocument.model_validate(doc))
            except Exception:  # noqa: BLE001
                logger.warning(
                    "api_access_policy_repository.list_all: failed to parse document %s",
                    doc.get("id"),
                )
        return policies
