"""BM25检索器

基于BM25算法的关键词检索，使用jieba进行中文分词
"""

from typing import Optional
from dataclasses import dataclass, field

import jieba
from rank_bm25 import BM25Okapi

from src.utils.logger import logger


@dataclass
class BM25Document:
    """BM25文档"""
    doc_id: str
    content: str
    tokens: list[str] = field(default_factory=list)
    metadata: dict = field(default_factory=dict)


class BM25Retriever:
    """BM25关键词检索器"""

    def __init__(self, documents: Optional[list[BM25Document]] = None):
        """初始化BM25检索器

        Args:
            documents: 文档列表，为None时需要后续调用build_index
        """
        self.documents: list[BM25Document] = []
        self.bm25: Optional[BM25Okapi] = None
        self._initialized = False

        # 加载jieba词典（静默模式）
        jieba.setLogLevel(jieba.logging.INFO)

        if documents:
            self.build_index(documents)

    def tokenize(self, text: str) -> list[str]:
        """中文分词

        Args:
            text: 输入文本

        Returns:
            分词结果列表
        """
        if not text:
            return []

        # 使用jieba分词，过滤空白和单字符标点
        tokens = jieba.lcut(text)
        tokens = [t.strip() for t in tokens if t.strip() and len(t.strip()) > 0]

        # 过滤纯标点符号
        tokens = [t for t in tokens if not self._is_punctuation(t)]

        return tokens

    def _is_punctuation(self, token: str) -> bool:
        """检查是否为纯标点符号"""
        import re
        return bool(re.match(r'^[^\w\u4e00-\u9fff]+$', token))

    def build_index(self, documents: list[BM25Document]):
        """构建BM25索引

        Args:
            documents: 文档列表
        """
        if not documents:
            logger.warning("BM25: 文档列表为空")
            return

        self.documents = documents

        # 对所有文档分词
        corpus = []
        for doc in self.documents:
            if not doc.tokens:
                doc.tokens = self.tokenize(doc.content)
            corpus.append(doc.tokens)

        # 构建BM25索引
        self.bm25 = BM25Okapi(corpus)
        self._initialized = True

        logger.info(f"BM25索引构建完成，文档数: {len(documents)}")

    def add_documents(self, documents: list[BM25Document]):
        """添加文档并重建索引

        Args:
            documents: 新增文档列表
        """
        self.documents.extend(documents)
        self.build_index(self.documents)

    def retrieve(
        self,
        query: str,
        top_k: int = 10,
    ) -> list[tuple[BM25Document, float]]:
        """BM25检索

        Args:
            query: 查询文本
            top_k: 返回结果数量

        Returns:
            [(document, score), ...] 按分数降序排列
        """
        if not self._initialized or self.bm25 is None:
            logger.warning("BM25: 索引未初始化")
            return []

        if not query:
            return []

        # 查询分词
        query_tokens = self.tokenize(query)
        if not query_tokens:
            return []

        # 计算BM25分数
        scores = self.bm25.get_scores(query_tokens)

        # 获取top_k结果
        doc_scores = list(zip(self.documents, scores))
        doc_scores.sort(key=lambda x: x[1], reverse=True)

        # 过滤零分结果
        results = [(doc, score) for doc, score in doc_scores[:top_k] if score > 0]

        return results

    def get_scores(self, query: str) -> list[float]:
        """获取所有文档的BM25分数

        Args:
            query: 查询文本

        Returns:
            分数列表，与文档顺序一致
        """
        if not self._initialized or self.bm25 is None:
            return []

        query_tokens = self.tokenize(query)
        if not query_tokens:
            return [0.0] * len(self.documents)

        return list(self.bm25.get_scores(query_tokens))

    @property
    def doc_count(self) -> int:
        """文档数量"""
        return len(self.documents)

    @property
    def is_initialized(self) -> bool:
        """是否已初始化"""
        return self._initialized


class BM25IndexBuilder:
    """BM25索引构建器

    用于从不同数据源构建BM25文档索引
    """

    @staticmethod
    def from_texts(
        texts: list[str],
        metadatas: Optional[list[dict]] = None,
    ) -> list[BM25Document]:
        """从文本列表构建文档

        Args:
            texts: 文本列表
            metadatas: 元数据列表

        Returns:
            BM25文档列表
        """
        documents = []
        metadatas = metadatas or [{}] * len(texts)

        for i, (text, metadata) in enumerate(zip(texts, metadatas)):
            doc = BM25Document(
                doc_id=str(i),
                content=text,
                metadata=metadata,
            )
            documents.append(doc)

        return documents

    @staticmethod
    def from_nodes(nodes: list) -> list[BM25Document]:
        """从LlamaIndex节点构建文档

        Args:
            nodes: LlamaIndex节点列表

        Returns:
            BM25文档列表
        """
        documents = []

        for node in nodes:
            doc = BM25Document(
                doc_id=node.node_id if hasattr(node, 'node_id') else str(id(node)),
                content=node.get_content() if hasattr(node, 'get_content') else str(node),
                metadata=node.metadata if hasattr(node, 'metadata') else {},
            )
            documents.append(doc)

        return documents
