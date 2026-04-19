"""Unit tests for the UserContextService — security trimming logic.

Tests cover:
- Group extraction from JWT claims
- Admin bypass (Portal.Admin role)
- Accessible API ID resolution (group matching)
- Default public access when no policy exists
- can_access_api() — individual API access checks
- Policy caching and cache invalidation
- Graceful degradation when Cosmos DB is unavailable
- _build_odata_filter() with security trimming
- ApiCatalogService with accessible_api_ids
- SearchService with accessible_api_ids
- AIChatService._retrieve_context() with accessible_api_ids
"""

from __future__ import annotations

import time
from unittest.mock import AsyncMock, MagicMock

import pytest

from apic_vibe_portal_bff.data.models.api_access_policy import ApiAccessPolicyDocument
from apic_vibe_portal_bff.middleware.auth import AuthenticatedUser
from apic_vibe_portal_bff.services.user_context_service import (
    ADMIN_ROLE,
    UserContextService,
    _PolicyCache,
)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_user(
    oid: str = "user-1",
    roles: list[str] | None = None,
    groups: list[str] | None = None,
) -> AuthenticatedUser:
    """Build an :class:`AuthenticatedUser` for testing."""
    claims: dict = {}
    if groups is not None:
        claims["groups"] = groups
    return AuthenticatedUser(
        oid=oid,
        name="Test User",
        email="test@example.com",
        roles=roles or [],
        claims=claims,
    )


def _admin_user(oid: str = "admin-1") -> AuthenticatedUser:
    return _make_user(oid=oid, roles=[ADMIN_ROLE])


def _make_policy(
    api_name: str,
    *,
    allowed_groups: list[str] | None = None,
    is_public: bool = False,
) -> ApiAccessPolicyDocument:
    return ApiAccessPolicyDocument.new(
        api_name=api_name,
        allowed_groups=allowed_groups or [],
        is_public=is_public,
    )


def _make_service(policies: list[ApiAccessPolicyDocument] | None = None) -> UserContextService:
    """Return a :class:`UserContextService` backed by a mock repository."""
    repo = MagicMock()
    repo.list_all_policies.return_value = policies or []
    return UserContextService(policy_repository=repo)


# ---------------------------------------------------------------------------
# _PolicyCache
# ---------------------------------------------------------------------------


class TestPolicyCache:
    def test_cache_miss_on_empty(self):
        cache = _PolicyCache(ttl_seconds=60)
        assert cache.get() is None

    def test_cache_hit_after_set(self):
        cache = _PolicyCache(ttl_seconds=60)
        data = {"api-1": None}
        cache.set(data)
        assert cache.get() == data

    def test_cache_expires(self):
        cache = _PolicyCache(ttl_seconds=0.01)
        cache.set({"api-1": None})
        time.sleep(0.05)
        assert cache.get() is None

    def test_invalidate_clears_cache(self):
        cache = _PolicyCache(ttl_seconds=60)
        cache.set({"api-1": None})
        cache.invalidate()
        assert cache.get() is None


# ---------------------------------------------------------------------------
# UserContextService.is_admin
# ---------------------------------------------------------------------------


class TestIsAdmin:
    def test_admin_role_returns_true(self):
        svc = _make_service()
        user = _admin_user()
        assert svc.is_admin(user) is True

    def test_portal_user_role_returns_false(self):
        svc = _make_service()
        user = _make_user(roles=["Portal.User"])
        assert svc.is_admin(user) is False

    def test_no_roles_returns_false(self):
        svc = _make_service()
        user = _make_user(roles=[])
        assert svc.is_admin(user) is False

    def test_maintainer_role_returns_false(self):
        svc = _make_service()
        user = _make_user(roles=["Portal.Maintainer"])
        assert svc.is_admin(user) is False


# ---------------------------------------------------------------------------
# UserContextService.get_user_groups
# ---------------------------------------------------------------------------


class TestGetUserGroups:
    def test_extracts_groups_from_claims(self):
        svc = _make_service()
        user = _make_user(groups=["group-a", "group-b"])
        assert svc.get_user_groups(user) == ["group-a", "group-b"]

    def test_returns_empty_when_no_groups_claim(self):
        svc = _make_service()
        user = _make_user(groups=None)
        assert svc.get_user_groups(user) == []

    def test_returns_empty_when_groups_claim_is_non_list(self):
        svc = _make_service()
        user = AuthenticatedUser(oid="u1", name="", email="", roles=[], claims={"groups": "not-a-list"})
        assert svc.get_user_groups(user) == []

    def test_filters_empty_group_oids(self):
        svc = _make_service()
        user = _make_user(groups=["group-a", "", "group-b"])
        result = svc.get_user_groups(user)
        assert result == ["group-a", "group-b"]


# ---------------------------------------------------------------------------
# UserContextService.get_accessible_api_ids
# ---------------------------------------------------------------------------


class TestGetAccessibleApiIds:
    def test_admin_returns_none(self):
        """Admin bypass: None means no filtering (all APIs accessible)."""
        svc = _make_service()
        user = _admin_user()
        result = svc.get_accessible_api_ids(user)
        assert result is None

    def test_no_policies_returns_empty_for_regular_user(self):
        """When there are no policies at all, the policy map is empty.

        Since no APIs are known to the policy system, the accessible list is
        empty.  This differs from the production default because in reality
        APIs with no policy are public — but here there are literally no APIs
        in the policy store.
        """
        svc = _make_service(policies=[])
        user = _make_user(groups=["group-a"])
        result = svc.get_accessible_api_ids(user)
        assert result == []

    def test_public_api_accessible_to_all(self):
        svc = _make_service(policies=[_make_policy("petstore", is_public=True)])
        user = _make_user(groups=[])
        result = svc.get_accessible_api_ids(user)
        assert "petstore" in result

    def test_restricted_api_accessible_when_user_in_group(self):
        svc = _make_service(policies=[_make_policy("internal-api", allowed_groups=["group-a"])])
        user = _make_user(groups=["group-a", "group-b"])
        result = svc.get_accessible_api_ids(user)
        assert "internal-api" in result

    def test_restricted_api_not_accessible_when_user_not_in_group(self):
        svc = _make_service(policies=[_make_policy("internal-api", allowed_groups=["group-a"])])
        user = _make_user(groups=["group-b", "group-c"])
        result = svc.get_accessible_api_ids(user)
        assert "internal-api" not in result

    def test_restricted_api_not_accessible_when_user_has_no_groups(self):
        svc = _make_service(policies=[_make_policy("internal-api", allowed_groups=["group-a"])])
        user = _make_user(groups=[])
        result = svc.get_accessible_api_ids(user)
        assert "internal-api" not in result

    def test_user_a_and_user_b_see_different_apis(self):
        """Two users in different groups see different sets of APIs."""
        policies = [
            _make_policy("team-a-api", allowed_groups=["group-a"]),
            _make_policy("team-b-api", allowed_groups=["group-b"]),
            _make_policy("shared-api", is_public=True),
        ]
        svc = _make_service(policies=policies)

        user_a = _make_user(oid="user-a", groups=["group-a"])
        user_b = _make_user(oid="user-b", groups=["group-b"])

        ids_a = set(svc.get_accessible_api_ids(user_a))
        ids_b = set(svc.get_accessible_api_ids(user_b))

        assert "team-a-api" in ids_a
        assert "team-b-api" not in ids_a
        assert "shared-api" in ids_a

        assert "team-b-api" in ids_b
        assert "team-a-api" not in ids_b
        assert "shared-api" in ids_b

    def test_restricted_api_with_empty_allowed_groups_inaccessible(self):
        """An API with no groups and is_public=False is accessible to nobody."""
        svc = _make_service(policies=[_make_policy("locked-api", allowed_groups=[], is_public=False)])
        user = _make_user(groups=["any-group"])
        result = svc.get_accessible_api_ids(user)
        assert "locked-api" not in result

    def test_policies_loaded_from_repo(self):
        """Repository is queried when cache is cold."""
        repo = MagicMock()
        repo.list_all_policies.return_value = [
            _make_policy("api-1", is_public=True),
        ]
        svc = UserContextService(policy_repository=repo)
        user = _make_user()
        svc.get_accessible_api_ids(user)
        repo.list_all_policies.assert_called_once()

    def test_policy_cache_prevents_repeated_repo_calls(self):
        """Repository is only called once when cache is warm."""
        repo = MagicMock()
        repo.list_all_policies.return_value = [_make_policy("api-1", is_public=True)]
        svc = UserContextService(policy_repository=repo)
        user = _make_user()

        svc.get_accessible_api_ids(user)
        svc.get_accessible_api_ids(user)

        repo.list_all_policies.assert_called_once()

    def test_cache_invalidation_causes_repo_refresh(self):
        """After invalidation, the next call hits the repository again."""
        repo = MagicMock()
        repo.list_all_policies.return_value = [_make_policy("api-1", is_public=True)]
        svc = UserContextService(policy_repository=repo)
        user = _make_user()

        svc.get_accessible_api_ids(user)
        svc.invalidate_policy_cache()
        svc.get_accessible_api_ids(user)

        assert repo.list_all_policies.call_count == 2

    def test_repo_failure_returns_empty_accessible_list(self):
        """When Cosmos DB is unavailable, the service fails open (empty list)."""
        repo = MagicMock()
        repo.list_all_policies.side_effect = Exception("Cosmos DB unavailable")
        svc = UserContextService(policy_repository=repo)
        user = _make_user()
        # Should not raise; returns empty accessible list
        result = svc.get_accessible_api_ids(user)
        assert result == []


# ---------------------------------------------------------------------------
# UserContextService.can_access_api
# ---------------------------------------------------------------------------


class TestCanAccessApi:
    def test_admin_can_access_any_api(self):
        svc = _make_service(policies=[_make_policy("restricted", allowed_groups=["g1"])])
        user = _admin_user()
        assert svc.can_access_api(user, "restricted") is True

    def test_user_in_group_can_access(self):
        svc = _make_service(policies=[_make_policy("api-1", allowed_groups=["g1"])])
        user = _make_user(groups=["g1"])
        assert svc.can_access_api(user, "api-1") is True

    def test_user_not_in_group_cannot_access(self):
        svc = _make_service(policies=[_make_policy("api-1", allowed_groups=["g1"])])
        user = _make_user(groups=["g2"])
        assert svc.can_access_api(user, "api-1") is False

    def test_api_with_no_policy_is_accessible(self):
        """API not in the policy store → public by default."""
        svc = _make_service(policies=[])
        user = _make_user(groups=[])
        assert svc.can_access_api(user, "unknown-api") is True

    def test_public_api_accessible_to_all(self):
        svc = _make_service(policies=[_make_policy("public-api", is_public=True)])
        user = _make_user(groups=[])
        assert svc.can_access_api(user, "public-api") is True

    def test_requesting_inaccessible_api_returns_false(self):
        svc = _make_service(policies=[_make_policy("secret-api", allowed_groups=["g1"])])
        user = _make_user(groups=["g2"])
        assert svc.can_access_api(user, "secret-api") is False


# ---------------------------------------------------------------------------
# ApiCatalogService with accessible_api_ids
# ---------------------------------------------------------------------------


class TestApiCatalogServiceTrimming:
    """Verify that ApiCatalogService respects accessible_api_ids."""

    def _make_catalog_service(self, apis):
        from apic_vibe_portal_bff.services.api_catalog_service import ApiCatalogService
        from tests.api_center_mocks import make_api

        mock_client = MagicMock()
        mock_client.list_apis.return_value = [make_api(name=a) for a in apis]
        return ApiCatalogService(client=mock_client, cache_ttl_seconds=60.0)

    def test_list_apis_no_trimming_when_accessible_is_none(self):
        svc = self._make_catalog_service(["api-1", "api-2", "api-3"])
        result = svc.list_apis(accessible_api_ids=None)
        assert result.pagination.total_count == 3

    def test_list_apis_returns_only_accessible_apis(self):
        svc = self._make_catalog_service(["api-1", "api-2", "api-3"])
        result = svc.list_apis(accessible_api_ids=["api-1", "api-3"])
        assert result.pagination.total_count == 2
        names = {item.name for item in result.items}
        assert names == {"api-1", "api-3"}

    def test_list_apis_empty_accessible_returns_empty(self):
        svc = self._make_catalog_service(["api-1", "api-2"])
        result = svc.list_apis(accessible_api_ids=[])
        assert result.pagination.total_count == 0
        assert result.items == []

    def test_list_apis_pagination_reflects_trimmed_total(self):
        """total_count should be the trimmed count, not the full catalog count."""
        svc = self._make_catalog_service([f"api-{i}" for i in range(10)])
        result = svc.list_apis(page=1, page_size=5, accessible_api_ids=["api-0", "api-1", "api-2"])
        assert result.pagination.total_count == 3
        assert result.pagination.total_pages == 1

    def test_get_api_raises_when_not_in_accessible(self):
        from apic_vibe_portal_bff.services.api_catalog_service import (
            ApiAccessDeniedError,
            ApiCatalogService,
        )

        mock_client = MagicMock()
        svc = ApiCatalogService(client=mock_client, cache_ttl_seconds=60.0)

        with pytest.raises(ApiAccessDeniedError):
            svc.get_api("secret-api", accessible_api_ids=["api-1", "api-2"])

    def test_get_api_no_restriction_when_accessible_is_none(self):
        from apic_vibe_portal_bff.services.api_catalog_service import ApiCatalogService
        from tests.api_center_mocks import make_api

        mock_client = MagicMock()
        mock_client.get_api.return_value = make_api(name="any-api")
        mock_client.list_api_versions.return_value = []
        mock_client.list_deployments.return_value = []
        svc = ApiCatalogService(client=mock_client, cache_ttl_seconds=60.0)

        result = svc.get_api("any-api", accessible_api_ids=None)
        assert result.name == "any-api"


# ---------------------------------------------------------------------------
# SearchService with accessible_api_ids (via _build_odata_filter)
# ---------------------------------------------------------------------------


class TestSearchServiceSecurityFilter:
    """Verify that SearchService._build_odata_filter applies security trimming."""

    def test_no_filter_returns_none_without_security(self):
        from apic_vibe_portal_bff.services.search_service import _build_odata_filter

        assert _build_odata_filter(None, None) is None

    def test_empty_accessible_returns_no_match_filter(self):
        from apic_vibe_portal_bff.services.search_service import _build_odata_filter

        result = _build_odata_filter(None, [])
        assert result is not None
        assert "__no_access__" in result

    def test_accessible_ids_produces_search_in_filter(self):
        from apic_vibe_portal_bff.services.search_service import _build_odata_filter

        result = _build_odata_filter(None, ["api-1", "api-2"])
        assert result is not None
        assert "search.in(apiName" in result
        assert "api-1" in result
        assert "api-2" in result

    def test_combined_user_filter_and_security_filter(self):
        from apic_vibe_portal_bff.models.search import SearchFilters
        from apic_vibe_portal_bff.services.search_service import _build_odata_filter

        filters = SearchFilters(kind=["rest"])
        result = _build_odata_filter(filters, ["api-1"])
        assert result is not None
        assert "kind eq 'rest'" in result
        assert "search.in(apiName" in result
        assert " and " in result

    def test_search_service_passes_filter_to_client(self):
        from apic_vibe_portal_bff.models.search import SearchRequest
        from apic_vibe_portal_bff.services.search_service import SearchService

        mock_client = MagicMock()
        mock_client.search.return_value = {"results": [], "count": 0, "facets": None}
        svc = SearchService(client=mock_client)

        svc.search(SearchRequest(query="test"), accessible_api_ids=["api-1", "api-2"])

        call_kwargs = mock_client.search.call_args.kwargs
        assert call_kwargs["filter_expression"] is not None
        assert "api-1" in call_kwargs["filter_expression"]

    def test_search_service_no_filter_when_accessible_is_none(self):
        from apic_vibe_portal_bff.models.search import SearchRequest
        from apic_vibe_portal_bff.services.search_service import SearchService

        mock_client = MagicMock()
        mock_client.search.return_value = {"results": [], "count": 0, "facets": None}
        svc = SearchService(client=mock_client)

        svc.search(SearchRequest(query="test"), accessible_api_ids=None)

        call_kwargs = mock_client.search.call_args.kwargs
        assert call_kwargs["filter_expression"] is None

    def test_suggest_returns_empty_when_no_accessible_apis(self):
        from apic_vibe_portal_bff.services.search_service import SearchService

        mock_client = MagicMock()
        svc = SearchService(client=mock_client)

        result = svc.suggest("pet", accessible_api_ids=[])

        assert result.suggestions == []
        mock_client.suggest.assert_not_called()

    def test_suggest_passes_security_filter_to_client(self):
        from apic_vibe_portal_bff.services.search_service import SearchService

        mock_client = MagicMock()
        mock_client.suggest.return_value = []
        svc = SearchService(client=mock_client)

        svc.suggest("pet", accessible_api_ids=["petstore"])

        call_kwargs = mock_client.suggest.call_args.kwargs
        assert "petstore" in call_kwargs["filter_expression"]


# ---------------------------------------------------------------------------
# AIChatService accessible_api_ids forwarding
# ---------------------------------------------------------------------------


class TestAIChatServiceSecurityFilter:
    """Verify that AIChatService forwards accessible_api_ids through the agent router.

    Security trimming is enforced inside the agent (search_apis tool and
    SecurityTrimmingMiddleware).  The service layer's responsibility is to
    pass the IDs into the AgentRequest.
    """

    @pytest.mark.asyncio
    async def test_chat_passes_accessible_ids_to_agent_router(self):
        from apic_vibe_portal_bff.agents.types import AgentName, AgentRequest, AgentResponse
        from apic_vibe_portal_bff.services.ai_chat_service import AIChatService

        mock_router = MagicMock()
        mock_router.dispatch = AsyncMock(
            return_value=AgentResponse(
                agent_name=AgentName.API_DISCOVERY,
                content="Here is the answer.",
                session_id="sess-1",
            )
        )

        svc = AIChatService(agent_router=mock_router)
        await svc.chat("What APIs do we have?", accessible_api_ids=["weather-api"])

        call_args = mock_router.dispatch.call_args
        req: AgentRequest = call_args.args[0]
        assert req.accessible_api_ids == ["weather-api"]


# ---------------------------------------------------------------------------
# ApiAccessPolicyDocument
# ---------------------------------------------------------------------------


class TestApiAccessPolicyDocument:
    def test_new_creates_policy_with_defaults(self):
        doc = ApiAccessPolicyDocument.new(api_name="petstore")
        assert doc.id == "petstore"
        assert doc.api_name == "petstore"
        assert doc.allowed_groups == []
        assert doc.is_public is False
        assert doc.schema_version == 1
        assert doc.created_at != ""

    def test_new_with_groups(self):
        doc = ApiAccessPolicyDocument.new(
            api_name="internal-api",
            allowed_groups=["group-a", "group-b"],
        )
        assert doc.allowed_groups == ["group-a", "group-b"]

    def test_new_public_api(self):
        doc = ApiAccessPolicyDocument.new(api_name="public-api", is_public=True)
        assert doc.is_public is True

    def test_to_cosmos_dict_uses_camel_case(self):
        doc = ApiAccessPolicyDocument.new(api_name="my-api", allowed_groups=["g1"])
        data = doc.to_cosmos_dict()
        assert "apiName" in data
        assert "allowedGroups" in data
        assert "isPublic" in data
        assert data["id"] == "my-api"
        assert data["apiName"] == "my-api"
        assert data["allowedGroups"] == ["g1"]
