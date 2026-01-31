"""混合检索器 - 向量检索 + BM25 + 多路融合"""

from typing import Optional
from dataclasses import dataclass

from llama_index.core import VectorStoreIndex
from llama_index.core.retrievers import VectorIndexRetriever
from llama_index.core.schema import NodeWithScore

from config import settings
from src.utils.logger import logger
from src.utils.models import DEFAULT_SYNONYMS

from .bm25 import BM25Retriever, BM25Document, BM25IndexBuilder
from .fusion import ReciprocalRankFusion, FusedResult
from .cache import QueryCache
from .query_processor import QueryProcessor, ProcessedQuery, QueryType
from .mmr import MMRDiversifier, ContentBasedDiversifier


@dataclass
class RetrievalResult:
    """检索结果"""
    content: str
    score: float
    metadata: dict
    source_url: Optional[str] = None
    source_title: Optional[str] = None
    doc_id: Optional[str] = None


class HybridRetriever:
    """混合检索器：结合向量检索、BM25和多种优化技术"""

    def __init__(self, index: VectorStoreIndex):
        self.config = settings.retriever
        self.index = index

        # 创建向量检索器
        self.vector_retriever = VectorIndexRetriever(
            index=index,
            similarity_top_k=self.config.top_k * 3,  # 多检索一些用于融合
        )

        # 查询处理器
        self.query_processor = QueryProcessor(DEFAULT_SYNONYMS)

        # BM25检索器（延迟初始化）
        self._bm25_retriever: Optional[BM25Retriever] = None
        if self.config.use_bm25:
            self._init_bm25()

        # RRF融合器
        self.fusion = ReciprocalRankFusion(k=self.config.rrf_k)

        # 查询缓存
        self.cache = QueryCache(
            max_size=self.config.cache_max_size,
            ttl=self.config.cache_ttl,
            enabled=self.config.use_cache,
        )

        # MMR多样性优化器
        self.mmr = MMRDiversifier(lambda_param=self.config.mmr_lambda)

        # 内容去重器
        self.deduplicator = ContentBasedDiversifier(similarity_threshold=0.85)

        # 兼容旧代码的同义词映射
        self.synonyms = self.query_processor._synonym_map

        logger.info(f"混合检索器初始化完成 (BM25={self.config.use_bm25}, "
                    f"Cache={self.config.use_cache}, MMR={self.config.use_mmr})")

    def _init_bm25(self):
        """初始化BM25检索器"""
        try:
            # 从索引中获取所有文档
            docstore = self.index.docstore
            if docstore:
                nodes = list(docstore.docs.values())
                if nodes:
                    bm25_docs = BM25IndexBuilder.from_nodes(nodes)
                    self._bm25_retriever = BM25Retriever(bm25_docs)
                    logger.info(f"BM25索引构建完成: {len(bm25_docs)}个文档")
                else:
                    logger.warning("BM25: 文档库为空")
            else:
                logger.warning("BM25: 无法获取文档库")
        except Exception as e:
            logger.error(f"BM25初始化失败: {e}")
            self._bm25_retriever = None

    def expand_query(self, query: str) -> str:
        """扩展查询（同义词替换）- 兼容旧接口"""
        processed = self.query_processor.process(query)
        return processed.expanded

    def retrieve(
        self,
        query: str,
        top_k: Optional[int] = None,
        filter_version: Optional[str] = None,
    ) -> list[RetrievalResult]:
        """执行混合检索

        Args:
            query: 查询文本
            top_k: 返回结果数量
            filter_version: 版本过滤

        Returns:
            检索结果列表
        """
        if top_k is None:
            top_k = self.config.top_k

        # 1. 检查缓存
        if self.config.use_cache:
            cached = self.cache.get(query, version=filter_version)
            if cached is not None:
                logger.debug(f"缓存命中: '{query[:20]}...'")
                return cached

        # 2. 查询处理
        processed = self.query_processor.process(query)
        expanded_query = processed.expanded

        # 3. 多路检索
        vector_results = self._vector_retrieve(expanded_query)

        # BM25检索
        bm25_results = []
        if self.config.use_bm25 and self._bm25_retriever:
            bm25_results = self._bm25_retrieve(expanded_query)

        # 4. 融合结果
        if bm25_results and vector_results:
            fused = self._fuse_results(vector_results, bm25_results)
        elif vector_results:
            fused = vector_results
        else:
            fused = []

        # 5. 过滤
        filtered = self._filter_results(fused, filter_version=filter_version)

        # 6. MMR多样性优化
        if self.config.use_mmr and len(filtered) > top_k:
            filtered = self._apply_mmr(filtered, top_k * 2)

        # 7. 转换结果格式
        results = self._convert_results(filtered[:top_k])

        # 8. 缓存结果
        if self.config.use_cache and results:
            self.cache.set(query, results, version=filter_version)

        logger.info(f"检索 '{query}' (type={processed.query_type.value}) 返回 {len(results)} 个结果")
        return results

    def _vector_retrieve(self, query: str) -> list[NodeWithScore]:
        """向量检索"""
        try:
            results = self.vector_retriever.retrieve(query)
            return results
        except Exception as e:
            logger.error(f"向量检索失败: {e}")
            return []

    def _bm25_retrieve(self, query: str) -> list[tuple[BM25Document, float]]:
        """BM25检索"""
        if not self._bm25_retriever:
            return []

        try:
            results = self._bm25_retriever.retrieve(
                query,
                top_k=self.config.top_k * 3
            )
            return results
        except Exception as e:
            logger.error(f"BM25检索失败: {e}")
            return []

    def _fuse_results(
        self,
        vector_results: list[NodeWithScore],
        bm25_results: list[tuple[BM25Document, float]],
    ) -> list[NodeWithScore]:
        """融合向量和BM25检索结果"""
        # 准备RRF输入
        vector_list = vector_results
        bm25_list = [doc for doc, _ in bm25_results]

        # 使用文档ID作为匹配依据
        def get_vector_id(node: NodeWithScore) -> str:
            return node.node.node_id

        def get_bm25_id(doc: BM25Document) -> str:
            return doc.doc_id

        # RRF融合
        fused = self.fusion.fuse_with_weights(
            result_lists=[vector_list, bm25_list],
            weights=[self.config.vector_weight, self.config.bm25_weight],
            get_id=lambda x: get_vector_id(x) if isinstance(x, NodeWithScore) else get_bm25_id(x),
        )

        # 转换回NodeWithScore格式（优先使用向量检索的节点）
        result_nodes = []
        node_map = {get_vector_id(n): n for n in vector_results}

        for fused_result in fused:
            item = fused_result.item
            if isinstance(item, NodeWithScore):
                # 更新分数为融合分数
                item.score = fused_result.score
                result_nodes.append(item)
            elif isinstance(item, BM25Document):
                # BM25结果需要转换
                if item.doc_id in node_map:
                    node = node_map[item.doc_id]
                    node.score = fused_result.score
                    result_nodes.append(node)

        return result_nodes

    def _filter_results(
        self,
        nodes: list[NodeWithScore],
        filter_version: Optional[str] = None,
    ) -> list[NodeWithScore]:
        """过滤检索结果"""
        filtered = []

        for node in nodes:
            # 相似度阈值过滤
            if node.score < self.config.similarity_threshold:
                continue

            # 版本过滤
            if filter_version:
                node_version = node.node.metadata.get("version", "both")
                if node_version not in [filter_version, "both"]:
                    continue

            filtered.append(node)

        return filtered

    def _apply_mmr(
        self,
        nodes: list[NodeWithScore],
        top_k: int,
    ) -> list[NodeWithScore]:
        """应用MMR多样性优化"""
        if len(nodes) <= 1:
            return nodes

        # 提取分数
        relevance_scores = [node.score for node in nodes]

        # 使用简化的MMR（基于内容相似度）
        # 由于计算嵌入开销大，这里使用内容去重替代
        deduplicated = self.deduplicator.deduplicate(
            nodes,
            get_content=lambda n: n.node.get_content()[:500],  # 使用前500字符
        )

        return deduplicated[:top_k]

    def _convert_results(self, nodes: list[NodeWithScore]) -> list[RetrievalResult]:
        """转换结果格式"""
        results = []
        for node in nodes:
            result = RetrievalResult(
                content=node.node.get_content(),
                score=node.score,
                metadata=node.node.metadata,
                source_url=node.node.metadata.get("source_url"),
                source_title=node.node.metadata.get("source_title"),
                doc_id=node.node.node_id,
            )
            results.append(result)
        return results

    def get_context_for_qa(
        self,
        query: str,
        top_k: Optional[int] = None,
    ) -> str:
        """获取用于问答的上下文文本"""
        results = self.retrieve(query, top_k=top_k)

        if not results:
            return ""

        context_parts = []
        for i, result in enumerate(results, 1):
            source_info = f"[来源: {result.source_title}]" if result.source_title else ""
            context_parts.append(f"【文档{i}】{source_info}\n{result.content}")

        return "\n\n".join(context_parts)

    def get_cache_stats(self) -> dict:
        """获取缓存统计信息"""
        return self.cache.get_stats()

    def clear_cache(self):
        """清空缓存"""
        self.cache.clear()

    def rebuild_bm25_index(self):
        """重建BM25索引"""
        if self.config.use_bm25:
            self._init_bm25()
