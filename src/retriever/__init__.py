"""检索增强模块"""

# 独立模块（无llama_index依赖）
from .bm25 import BM25Retriever, BM25Document, BM25IndexBuilder
from .fusion import ReciprocalRankFusion, LinearCombination, FusedResult
from .cache import QueryCache, SemanticCache, CacheEntry
from .query_processor import QueryProcessor, ProcessedQuery, QueryType
from .mmr import MMRDiversifier, ContentBasedDiversifier, MMRResult

# llama_index依赖检测
_HAS_LLAMA_INDEX = False
_LLAMA_INDEX_ERROR = None


class _LlamaIndexNotAvailable:
    """占位类，在llama_index不可用时提供清晰的错误信息"""

    def __init__(self, class_name: str, error: Exception):
        self._class_name = class_name
        self._error = error

    def __call__(self, *args, **kwargs):
        raise ImportError(
            f"{self._class_name} 需要安装 llama_index 相关依赖。\n"
            f"请运行: pip install llama-index-core llama-index-embeddings-huggingface llama-index-vector-stores-chroma\n"
            f"原始错误: {self._error}"
        )

    def __getattr__(self, name):
        raise ImportError(
            f"{self._class_name} 需要安装 llama_index 相关依赖。\n"
            f"请运行: pip install llama-index-core llama-index-embeddings-huggingface llama-index-vector-stores-chroma\n"
            f"原始错误: {self._error}"
        )


# llama_index依赖模块（可选）
try:
    from .retriever import HybridRetriever, RetrievalResult
    from .reranker import Reranker
    _HAS_LLAMA_INDEX = True
except ImportError as e:
    _LLAMA_INDEX_ERROR = e
    HybridRetriever = _LlamaIndexNotAvailable("HybridRetriever", e)
    RetrievalResult = _LlamaIndexNotAvailable("RetrievalResult", e)
    Reranker = _LlamaIndexNotAvailable("Reranker", e)


def has_llama_index() -> bool:
    """检查 llama_index 是否可用"""
    return _HAS_LLAMA_INDEX


def get_llama_index_error() -> Exception:
    """获取 llama_index 导入失败的原始错误"""
    return _LLAMA_INDEX_ERROR


__all__ = [
    # BM25
    "BM25Retriever",
    "BM25Document",
    "BM25IndexBuilder",
    # 融合
    "ReciprocalRankFusion",
    "LinearCombination",
    "FusedResult",
    # 缓存
    "QueryCache",
    "SemanticCache",
    "CacheEntry",
    # 查询处理
    "QueryProcessor",
    "ProcessedQuery",
    "QueryType",
    # MMR
    "MMRDiversifier",
    "ContentBasedDiversifier",
    "MMRResult",
    # 主检索器（可能不可用）
    "HybridRetriever",
    "RetrievalResult",
    "Reranker",
    # 辅助函数
    "has_llama_index",
    "get_llama_index_error",
]
