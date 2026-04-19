"""User context service — resolves group membership and API access permissions.

Extracts Entra ID group memberships from JWT token claims and checks them
against API access policies stored in Cosmos DB.

## Design

- **Groups from token**: Entra ID tokens include a ``groups`` claim with the
  object IDs (OIDs) of the groups the user belongs to.  For large tenants the
  claim may be omitted (group overage); the service handles this gracefully by
  treating the user as having no additional group memberships.

- **Default access**: If no policy document exists for an API the API is
  treated as *public* — all authenticated users can see it.  This prevents
  accidentally hiding the whole catalog when policies are first deployed.

- **Admin bypass**: Users with the ``Portal.Admin`` role bypass all security
  trimming and see every API regardless of group membership.

- **Caching**: API access policies are cached in-memory with a configurable
  TTL (default: 5 minutes) to avoid Cosmos DB reads on every request.
"""

from __future__ import annotations

import logging
import time
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from apic_vibe_portal_bff.data.repositories.api_access_policy_repository import ApiAccessPolicyRepository
    from apic_vibe_portal_bff.middleware.auth import AuthenticatedUser

logger = logging.getLogger(__name__)

# Role that grants full visibility over the entire catalog, bypassing trimming.
ADMIN_ROLE = "Portal.Admin"

# Default cache TTL for the full policy list (seconds).
DEFAULT_POLICY_CACHE_TTL = 300  # 5 minutes


class _PolicyCache:
    """Simple in-process TTL cache for the full list of API access policies.

    The cache stores (all_policies_dict, fetch_time) and is invalidated when
    ``fetch_time + ttl_seconds < now``.  All replicas maintain their own
    independent in-memory caches — a cross-replica invalidation bus is not
    required for the current scale.
    """

    __slots__ = ("_data", "_fetched_at", "_ttl")

    def __init__(self, ttl_seconds: float = DEFAULT_POLICY_CACHE_TTL) -> None:
        # Maps api_name → ApiAccessPolicyDocument (or None sentinel)
        self._data: dict | None = None
        self._fetched_at: float = 0.0
        self._ttl = ttl_seconds

    def get(self) -> dict | None:
        """Return the cached policies dict, or ``None`` if expired / empty."""
        if self._data is None:
            return None
        if time.monotonic() - self._fetched_at > self._ttl:
            self._data = None
            return None
        return self._data

    def set(self, data: dict) -> None:
        """Store a fresh policy snapshot."""
        self._data = data
        self._fetched_at = time.monotonic()

    def invalidate(self) -> None:
        """Force the next call to ``get()`` to return ``None``."""
        self._data = None


class UserContextService:
    """Resolves user permissions and applies security trimming.

    Parameters
    ----------
    policy_repository:
        Repository for loading API access policies from Cosmos DB.
    policy_cache_ttl_seconds:
        TTL for the in-memory policy cache.  Defaults to 5 minutes.
    """

    def __init__(
        self,
        policy_repository: ApiAccessPolicyRepository,
        policy_cache_ttl_seconds: float = DEFAULT_POLICY_CACHE_TTL,
    ) -> None:
        self._repo = policy_repository
        self._cache = _PolicyCache(ttl_seconds=policy_cache_ttl_seconds)

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def is_admin(self, user: AuthenticatedUser) -> bool:
        """Return ``True`` if the user has the ``Portal.Admin`` role."""
        return ADMIN_ROLE in user.roles

    def get_user_groups(self, user: AuthenticatedUser) -> list[str]:
        """Return the list of Entra ID group OIDs the user belongs to.

        Groups are extracted from the ``groups`` JWT claim.  If the claim is
        absent (Entra ID group overage scenario or token issued without the
        ``groups`` claim) an empty list is returned.
        """
        groups = user.claims.get("groups", [])
        if not isinstance(groups, list):
            return []
        return [str(g) for g in groups if g]

    def get_accessible_api_ids(self, user: AuthenticatedUser) -> list[str] | None:
        """Return the set of API names the user may access.

        Returns
        -------
        None
            Admin users — bypass all filtering (see all APIs).
        list[str]
            The API names accessible to the user.  An empty list means no
            APIs are accessible.  The caller should pass this to service
            methods to apply security trimming.
        """
        if self.is_admin(user):
            logger.debug(
                "user_context_service.get_accessible_api_ids.admin_bypass",
                extra={"user_oid": user.oid},
            )
            return None  # None signals "no filtering"

        policies = self._load_policies()
        user_groups = set(self.get_user_groups(user))

        accessible: list[str] = []
        for api_name, policy in policies.items():
            if policy is None:
                # No policy — public by default
                accessible.append(api_name)
            elif policy.is_public:
                accessible.append(api_name)
            elif user_groups & set(policy.allowed_groups):
                accessible.append(api_name)
            # else: policy exists with restricted groups that user isn't in — skip

        logger.debug(
            "user_context_service.get_accessible_api_ids",
            extra={
                "user_oid": user.oid,
                "user_group_count": len(user_groups),
                "accessible_count": len(accessible),
                "total_policy_count": len(policies),
            },
        )
        return accessible

    def can_access_api(self, user: AuthenticatedUser, api_name: str) -> bool:
        """Return ``True`` if the user may access the named API.

        Parameters
        ----------
        user:
            The authenticated user to check.
        api_name:
            The short API name (``ApiDefinition.name``).
        """
        if self.is_admin(user):
            return True

        policies = self._load_policies()

        if api_name not in policies:
            # No policy → public by default
            return True

        policy = policies[api_name]
        if policy is None or policy.is_public:
            return True

        user_groups = set(self.get_user_groups(user))
        return bool(user_groups & set(policy.allowed_groups))

    def invalidate_policy_cache(self) -> None:
        """Force the policy cache to be refreshed on the next request.

        Call this after creating, updating, or deleting an access policy so
        that subsequent requests pick up the change without waiting for the
        TTL to expire.
        """
        self._cache.invalidate()

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _load_policies(self) -> dict:
        """Return a mapping of api_name → ``ApiAccessPolicyDocument | None``.

        The result is served from cache when fresh; otherwise the Cosmos DB
        repository is queried and the result is stored in cache.

        Note: APIs that have *no* policy document are not present in this dict.
        Callers should treat a missing key as "public" (accessible by all).
        """
        cached = self._cache.get()
        if cached is not None:
            return cached

        try:
            all_policies = self._repo.list_all_policies()
        except Exception:  # noqa: BLE001
            logger.warning(
                "user_context_service.load_policies.failed — treating all APIs as public",
                exc_info=True,
            )
            # Fail open: if we can't load policies, return empty dict so all
            # APIs appear accessible.  This avoids a Cosmos DB outage causing
            # a full service outage.
            empty: dict = {}
            return empty

        policy_map = {p.api_name: p for p in all_policies}
        self._cache.set(policy_map)

        logger.debug(
            "user_context_service.load_policies.refreshed",
            extra={"policy_count": len(policy_map)},
        )
        return policy_map
