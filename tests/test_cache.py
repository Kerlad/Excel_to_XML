import sys, os, time
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

import pytest
from utils.cache import (
    LRUCache, Throttle,
    invalidate_summary_cache, is_summary_cache_valid,
    set_summary_cache, get_summary_cache,
    api_throttle
)


class TestLRUCache:
    def test_get_set(self):
        cache = LRUCache(maxsize=10, ttl_seconds=60)
        cache.set("key1", "value1")
        assert cache.get("key1") == "value1"

    def test_get_missing(self):
        cache = LRUCache(maxsize=10, ttl_seconds=60)
        assert cache.get("nonexistent") is None

    def test_ttl_expiry(self):
        cache = LRUCache(maxsize=10, ttl_seconds=0.1)
        cache.set("key", "val")
        time.sleep(0.15)
        assert cache.get("key") is None

    def test_lru_eviction(self):
        cache = LRUCache(maxsize=3, ttl_seconds=60)
        cache.set("a", 1)
        cache.set("b", 2)
        cache.set("c", 3)
        cache.set("d", 4)
        assert cache.get("a") is None
        assert cache.get("d") == 4

    def test_clear(self):
        cache = LRUCache(maxsize=10, ttl_seconds=60)
        cache.set("key", "val")
        cache.clear()
        assert cache.get("key") is None

    def test_invalidate_prefix(self):
        cache = LRUCache(maxsize=10, ttl_seconds=60)
        cache.set("user_1", "a")
        cache.set("user_2", "b")
        cache.set("admin_1", "c")
        cache.invalidate("user_")
        assert cache.get("user_1") is None
        assert cache.get("user_2") is None
        assert cache.get("admin_1") == "c"

    def test_size(self):
        cache = LRUCache(maxsize=10, ttl_seconds=60)
        assert cache.size == 0
        cache.set("a", 1)
        assert cache.size == 1

    def test_lru_order(self):
        cache = LRUCache(maxsize=3, ttl_seconds=60)
        cache.set("a", 1)
        cache.set("b", 2)
        cache.set("c", 3)
        cache.get("a")
        cache.set("d", 4)
        assert cache.get("a") == 1
        assert cache.get("b") is None

    def test_maxsize_one(self):
        cache = LRUCache(maxsize=1, ttl_seconds=60)
        cache.set("a", 1)
        cache.set("b", 2)
        assert cache.get("a") is None
        assert cache.get("b") == 2


class TestSummaryCache:
    def test_invalidate(self):
        set_summary_cache({"data": "test"})
        assert is_summary_cache_valid()
        invalidate_summary_cache()
        assert not is_summary_cache_valid()

    def test_get_set(self):
        data = {"employees": [1, 2, 3], "stats": {"a": 1}}
        set_summary_cache(data)
        assert get_summary_cache() == data

    def test_get_after_invalidate(self):
        set_summary_cache("test")
        invalidate_summary_cache()
        assert get_summary_cache() is None

    def test_default_invalid(self):
        assert not is_summary_cache_valid()


class TestThrottle:
    def test_no_wait_first_call(self):
        t = Throttle(min_interval=0.1)
        start = time.time()
        t.wait()
        elapsed = time.time() - start
        assert elapsed < 0.05

    def test_wait_between_calls(self):
        t = Throttle(min_interval=0.2)
        t.wait()
        start = time.time()
        t.wait()
        elapsed = time.time() - start
        assert elapsed >= 0.15

    def test_reset(self):
        t = Throttle(min_interval=0.2)
        t.wait()
        t.reset()
        start = time.time()
        t.wait()
        assert time.time() - start < 0.05

    def test_api_throttle_exists(self):
        assert api_throttle is not None
