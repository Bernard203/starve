"""查询缓存测试"""

import time
import pytest

from src.retriever.cache import QueryCache, CacheEntry


class TestQueryCache:
    """QueryCache测试"""

    @pytest.fixture
    def cache(self):
        """创建测试缓存"""
        return QueryCache(max_size=10, ttl=5, enabled=True)

    def test_init(self, cache):
        """测试初始化"""
        assert cache.max_size == 10
        assert cache.ttl == 5
        assert cache.enabled is True
        assert cache.size == 0

    def test_set_and_get(self, cache):
        """测试设置和获取"""
        cache.set("test query", ["result1", "result2"])
        result = cache.get("test query")

        assert result == ["result1", "result2"]

    def test_cache_miss(self, cache):
        """测试缓存未命中"""
        result = cache.get("nonexistent query")
        assert result is None

    def test_cache_with_kwargs(self, cache):
        """测试带参数的缓存"""
        cache.set("query", "result1", version="ds")
        cache.set("query", "result2", version="dst")

        assert cache.get("query", version="ds") == "result1"
        assert cache.get("query", version="dst") == "result2"
        assert cache.get("query", version="rog") is None

    def test_cache_expiry(self, cache):
        """测试缓存过期"""
        cache = QueryCache(max_size=10, ttl=1, enabled=True)
        cache.set("query", "result")

        # 立即获取应该成功
        assert cache.get("query") == "result"

        # 等待过期
        time.sleep(1.5)
        assert cache.get("query") is None

    def test_cache_max_size(self, cache):
        """测试缓存容量限制"""
        # 填满缓存
        for i in range(15):
            cache.set(f"query_{i}", f"result_{i}")

        # 应该只保留最近的10个
        assert cache.size == 10

        # 最早的应该被淘汰
        assert cache.get("query_0") is None
        # 最近的应该存在
        assert cache.get("query_14") == "result_14"

    def test_cache_key_generation(self, cache):
        """测试缓存键生成"""
        # 相同查询相同参数应该得到相同的键
        cache.set("query", "result1", version="ds", top_k=5)
        result = cache.get("query", version="ds", top_k=5)
        assert result == "result1"

        # 不同参数应该不命中
        result = cache.get("query", version="ds", top_k=10)
        assert result is None

    def test_cache_invalidate(self, cache):
        """测试使缓存失效"""
        cache.set("query", "result")
        assert cache.get("query") == "result"

        cache.invalidate("query")
        assert cache.get("query") is None

    def test_cache_clear(self, cache):
        """测试清空缓存"""
        cache.set("query1", "result1")
        cache.set("query2", "result2")

        cache.clear()

        assert cache.size == 0
        assert cache.get("query1") is None
        assert cache.get("query2") is None

    def test_cache_disabled(self):
        """测试禁用缓存"""
        cache = QueryCache(enabled=False)

        cache.set("query", "result")
        assert cache.get("query") is None

    def test_cache_hit_rate(self, cache):
        """测试命中率统计"""
        cache.set("query", "result")

        # 3次命中
        cache.get("query")
        cache.get("query")
        cache.get("query")

        # 2次未命中
        cache.get("other")
        cache.get("another")

        assert cache.hit_rate == 3 / 5

    def test_get_stats(self, cache):
        """测试获取统计信息"""
        cache.set("query", "result")
        cache.get("query")
        cache.get("other")

        stats = cache.get_stats()

        assert "size" in stats
        assert "max_size" in stats
        assert "hits" in stats
        assert "misses" in stats
        assert "hit_rate" in stats
        assert "enabled" in stats

    def test_cleanup_expired(self):
        """测试清理过期条目"""
        cache = QueryCache(max_size=10, ttl=1, enabled=True)

        cache.set("query1", "result1")
        cache.set("query2", "result2")

        time.sleep(1.5)

        # 添加一个新条目
        cache.set("query3", "result3")

        # 清理过期
        cache.cleanup_expired()

        # 旧条目应该被清理
        assert cache.size == 1
        assert cache.get("query3") == "result3"

    def test_lru_order(self, cache):
        """测试LRU顺序"""
        cache = QueryCache(max_size=3, ttl=3600, enabled=True)

        cache.set("query1", "result1")
        cache.set("query2", "result2")
        cache.set("query3", "result3")

        # 访问query1，使其变为最近使用
        cache.get("query1")

        # 添加新条目，应该淘汰query2
        cache.set("query4", "result4")

        assert cache.get("query1") == "result1"
        assert cache.get("query2") is None  # 被淘汰
        assert cache.get("query3") == "result3"
        assert cache.get("query4") == "result4"


class TestCacheEntry:
    """CacheEntry测试"""

    def test_create_entry(self):
        """测试创建条目"""
        entry = CacheEntry(
            value="test_value",
            created_at=time.time(),
        )

        assert entry.value == "test_value"
        assert entry.hits == 0
        assert entry.last_accessed is not None

    def test_entry_hits(self):
        """测试访问计数"""
        entry = CacheEntry(
            value="test_value",
            created_at=time.time(),
        )

        entry.hits += 1
        entry.hits += 1

        assert entry.hits == 2
