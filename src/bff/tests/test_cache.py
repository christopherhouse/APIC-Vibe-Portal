"""Unit tests for the in-memory TTL cache."""

from __future__ import annotations

import time

from apic_vibe_portal_bff.utils.cache import InMemoryCache


class TestInMemoryCache:
    def setup_method(self) -> None:
        self.cache: InMemoryCache[str] = InMemoryCache(default_ttl_seconds=60.0)

    # ------------------------------------------------------------------
    # Basic get / set
    # ------------------------------------------------------------------

    def test_set_and_get_returns_value(self) -> None:
        self.cache.set("key1", "hello")
        assert self.cache.get("key1") == "hello"

    def test_get_missing_key_returns_none(self) -> None:
        assert self.cache.get("nonexistent") is None

    def test_set_overwrites_existing_value(self) -> None:
        self.cache.set("key1", "first")
        self.cache.set("key1", "second")
        assert self.cache.get("key1") == "second"

    # ------------------------------------------------------------------
    # Expiry
    # ------------------------------------------------------------------

    def test_expired_entry_returns_none(self) -> None:
        self.cache.set("key1", "value", ttl_seconds=0.01)
        time.sleep(0.05)
        assert self.cache.get("key1") is None

    def test_non_expired_entry_still_returned(self) -> None:
        self.cache.set("key1", "value", ttl_seconds=60.0)
        assert self.cache.get("key1") == "value"

    def test_ttl_override_overrides_default(self) -> None:
        # Default is 60 s; override to expire immediately
        self.cache.set("key1", "value", ttl_seconds=0.01)
        time.sleep(0.05)
        assert self.cache.get("key1") is None

    # ------------------------------------------------------------------
    # Delete
    # ------------------------------------------------------------------

    def test_delete_removes_entry(self) -> None:
        self.cache.set("key1", "value")
        self.cache.delete("key1")
        assert self.cache.get("key1") is None

    def test_delete_nonexistent_key_is_noop(self) -> None:
        self.cache.delete("nonexistent")  # should not raise

    # ------------------------------------------------------------------
    # Clear
    # ------------------------------------------------------------------

    def test_clear_evicts_all_entries(self) -> None:
        self.cache.set("a", "1")
        self.cache.set("b", "2")
        self.cache.clear()
        assert self.cache.get("a") is None
        assert self.cache.get("b") is None

    # ------------------------------------------------------------------
    # invalidate_prefix
    # ------------------------------------------------------------------

    def test_invalidate_prefix_removes_matching_keys(self) -> None:
        self.cache.set("apis:all:1:20", "list1")
        self.cache.set("apis:all:2:20", "list2")
        self.cache.set("api:petstore", "detail")
        removed = self.cache.invalidate_prefix("apis:")
        assert removed == 2
        assert self.cache.get("apis:all:1:20") is None
        assert self.cache.get("apis:all:2:20") is None
        # Non-matching key untouched
        assert self.cache.get("api:petstore") == "detail"

    def test_invalidate_prefix_returns_zero_when_no_match(self) -> None:
        self.cache.set("key1", "v")
        removed = self.cache.invalidate_prefix("xyz:")
        assert removed == 0

    # ------------------------------------------------------------------
    # __len__
    # ------------------------------------------------------------------

    def test_len_counts_live_entries(self) -> None:
        self.cache.set("a", "1")
        self.cache.set("b", "2")
        assert len(self.cache) == 2

    def test_len_excludes_expired_entries(self) -> None:
        self.cache.set("live", "1", ttl_seconds=60.0)
        self.cache.set("dead", "2", ttl_seconds=0.01)
        time.sleep(0.05)
        assert len(self.cache) == 1

    def test_len_empty_cache_is_zero(self) -> None:
        assert len(self.cache) == 0

    # ------------------------------------------------------------------
    # get_with_staleness
    # ------------------------------------------------------------------

    def test_get_with_staleness_returns_value_and_no_refresh_when_fresh(self) -> None:
        self.cache.set("k", "fresh", ttl_seconds=60.0)
        result = self.cache.get_with_staleness("k", original_ttl_seconds=60.0)
        assert result.value == "fresh"
        assert result.needs_refresh is False

    def test_get_with_staleness_returns_none_on_miss(self) -> None:
        result = self.cache.get_with_staleness("missing", original_ttl_seconds=60.0)
        assert result.value is None
        assert result.needs_refresh is False

    def test_get_with_staleness_returns_none_on_expired(self) -> None:
        self.cache.set("k", "expired", ttl_seconds=0.01)
        time.sleep(0.05)
        result = self.cache.get_with_staleness("k", original_ttl_seconds=60.0)
        assert result.value is None
        assert result.needs_refresh is False

    def test_get_with_staleness_signals_refresh_when_near_expiry(self) -> None:
        # TTL of 0.1 s — sleep 0.09 s so only ~10% remains (< 20% threshold)
        self.cache.set("k", "stale", ttl_seconds=0.1)
        time.sleep(0.09)
        result = self.cache.get_with_staleness("k", original_ttl_seconds=0.1)
        assert result.value == "stale"
        assert result.needs_refresh is True
