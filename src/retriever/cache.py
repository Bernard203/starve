"""查询缓存模块

提供检索结果缓存，减少重复计算
"""

import hashlib
import time
from typing import Optional, Any, TypeVar
from dataclasses import dataclass, field
from collections import OrderedDict
from threading import Lock

from src.utils.logger import logger


T = TypeVar('T')


@dataclass
class CacheEntry:
    """缓存条目"""
    value: Any
    created_at: float
    hits: int = 0
    last_accessed: float = field(default_factory=time.time)


class QueryCache:
    """查询结果缓存

    支持TTL过期和LRU淘汰策略
    """

    def __init__(
        self,
        max_size: int = 1000,
        ttl: int = 3600,
        enabled: bool = True,
    ):
        """初始化缓存

        Args:
            max_size: 最大缓存条目数
            ttl: 缓存过期时间(秒)
            enabled: 是否启用缓存
        """
        self.max_size = max_size
        self.ttl = ttl
        self.enabled = enabled

        self._cache: OrderedDict[str, CacheEntry] = OrderedDict()
        self._lock = Lock()

        # 统计信息
        self._hits = 0
        self._misses = 0

    def _make_key(self, query: str, **kwargs) -> str:
        """生成缓存键

        Args:
            query: 查询文本
            **kwargs: 其他参数（如version_filter等）

        Returns:
            缓存键
        """
        # 构建键字符串
        key_parts = [query]
        for k, v in sorted(kwargs.items()):
            if v is not None:
                key_parts.append(f"{k}={v}")

        key_string = "|".join(key_parts)

        # 使用MD5哈希避免过长的键
        return hashlib.md5(key_string.encode('utf-8')).hexdigest()

    def get(self, query: str, **kwargs) -> Optional[Any]:
        """获取缓存结果

        Args:
            query: 查询文本
            **kwargs: 其他参数

        Returns:
            缓存的结果，未命中或过期返回None
        """
        if not self.enabled:
            return None

        key = self._make_key(query, **kwargs)

        with self._lock:
            entry = self._cache.get(key)

            if entry is None:
                self._misses += 1
                return None

            # 检查是否过期
            if time.time() - entry.created_at > self.ttl:
                del self._cache[key]
                self._misses += 1
                logger.debug(f"缓存过期: {key[:8]}...")
                return None

            # 更新访问信息
            entry.hits += 1
            entry.last_accessed = time.time()

            # 移到末尾（LRU）
            self._cache.move_to_end(key)

            self._hits += 1
            logger.debug(f"缓存命中: {key[:8]}... (hits: {entry.hits})")

            return entry.value

    def set(self, query: str, value: Any, **kwargs):
        """设置缓存

        Args:
            query: 查询文本
            value: 缓存值
            **kwargs: 其他参数
        """
        if not self.enabled:
            return

        key = self._make_key(query, **kwargs)

        with self._lock:
            # 如果已存在，更新
            if key in self._cache:
                self._cache[key].value = value
                self._cache[key].created_at = time.time()
                self._cache.move_to_end(key)
                return

            # 检查容量，必要时淘汰
            while len(self._cache) >= self.max_size:
                oldest_key = next(iter(self._cache))
                del self._cache[oldest_key]
                logger.debug(f"缓存淘汰: {oldest_key[:8]}...")

            # 添加新条目
            self._cache[key] = CacheEntry(
                value=value,
                created_at=time.time(),
            )

            logger.debug(f"缓存设置: {key[:8]}...")

    def invalidate(self, query: str, **kwargs):
        """使特定缓存失效

        Args:
            query: 查询文本
            **kwargs: 其他参数
        """
        key = self._make_key(query, **kwargs)

        with self._lock:
            if key in self._cache:
                del self._cache[key]
                logger.debug(f"缓存失效: {key[:8]}...")

    def clear(self):
        """清空所有缓存"""
        with self._lock:
            self._cache.clear()
            self._hits = 0
            self._misses = 0
            logger.info("缓存已清空")

    def cleanup_expired(self):
        """清理过期条目"""
        current_time = time.time()
        expired_keys = []

        with self._lock:
            for key, entry in self._cache.items():
                if current_time - entry.created_at > self.ttl:
                    expired_keys.append(key)

            for key in expired_keys:
                del self._cache[key]

        if expired_keys:
            logger.debug(f"清理过期缓存: {len(expired_keys)}条")

    @property
    def size(self) -> int:
        """当前缓存条目数"""
        return len(self._cache)

    @property
    def hit_rate(self) -> float:
        """缓存命中率"""
        total = self._hits + self._misses
        return self._hits / total if total > 0 else 0.0

    def get_stats(self) -> dict:
        """获取缓存统计信息"""
        return {
            "size": self.size,
            "max_size": self.max_size,
            "hits": self._hits,
            "misses": self._misses,
            "hit_rate": f"{self.hit_rate:.2%}",
            "ttl": self.ttl,
            "enabled": self.enabled,
        }


class SemanticCache(QueryCache):
    """语义缓存

    基于语义相似度的缓存，相似查询可以复用结果
    """

    def __init__(
        self,
        max_size: int = 1000,
        ttl: int = 3600,
        similarity_threshold: float = 0.95,
        embedding_func: Optional[callable] = None,
        enabled: bool = True,
    ):
        """初始化语义缓存

        Args:
            max_size: 最大缓存条目数
            ttl: 缓存过期时间(秒)
            similarity_threshold: 语义相似度阈值
            embedding_func: 文本嵌入函数
            enabled: 是否启用
        """
        super().__init__(max_size, ttl, enabled)
        self.similarity_threshold = similarity_threshold
        self.embedding_func = embedding_func

        # 存储查询嵌入
        self._embeddings: dict[str, list[float]] = {}

    def get(self, query: str, **kwargs) -> Optional[Any]:
        """语义感知的缓存获取

        首先尝试精确匹配，然后尝试语义匹配
        """
        # 先尝试精确匹配
        result = super().get(query, **kwargs)
        if result is not None:
            return result

        # 如果有嵌入函数，尝试语义匹配
        if self.embedding_func is None:
            return None

        try:
            query_embedding = self.embedding_func(query)
        except Exception:
            return None

        # 查找最相似的缓存
        best_key = None
        best_similarity = 0.0

        with self._lock:
            for key, embedding in self._embeddings.items():
                similarity = self._cosine_similarity(query_embedding, embedding)
                if similarity > best_similarity:
                    best_similarity = similarity
                    best_key = key

        if best_key and best_similarity >= self.similarity_threshold:
            with self._lock:
                entry = self._cache.get(best_key)
                if entry and time.time() - entry.created_at <= self.ttl:
                    entry.hits += 1
                    self._hits += 1
                    logger.debug(f"语义缓存命中: similarity={best_similarity:.3f}")
                    return entry.value

        self._misses += 1
        return None

    def set(self, query: str, value: Any, **kwargs):
        """设置语义缓存"""
        super().set(query, value, **kwargs)

        # 存储查询嵌入
        if self.embedding_func:
            try:
                key = self._make_key(query, **kwargs)
                self._embeddings[key] = self.embedding_func(query)
            except Exception:
                pass

    def _cosine_similarity(self, vec1: list[float], vec2: list[float]) -> float:
        """计算余弦相似度"""
        if len(vec1) != len(vec2):
            return 0.0

        dot_product = sum(a * b for a, b in zip(vec1, vec2))
        norm1 = sum(a * a for a in vec1) ** 0.5
        norm2 = sum(b * b for b in vec2) ** 0.5

        if norm1 == 0 or norm2 == 0:
            return 0.0

        return dot_product / (norm1 * norm2)
