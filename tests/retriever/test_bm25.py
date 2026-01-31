"""BM25检索器测试"""

import pytest

from src.retriever.bm25 import BM25Retriever, BM25Document, BM25IndexBuilder


class TestBM25Retriever:
    """BM25Retriever测试"""

    @pytest.fixture
    def sample_documents(self):
        """创建测试文档"""
        return [
            BM25Document(
                doc_id="1",
                content="肉丸是饥荒中的一种食物，可以用烹饪锅制作。",
                metadata={"type": "food"}
            ),
            BM25Document(
                doc_id="2",
                content="蜘蛛女王是一个强大的Boss，需要好的装备才能击败。",
                metadata={"type": "boss"}
            ),
            BM25Document(
                doc_id="3",
                content="科学机器是解锁科技的重要建筑，需要金块和石头制作。",
                metadata={"type": "structure"}
            ),
        ]

    @pytest.fixture
    def retriever(self, sample_documents):
        """创建BM25检索器"""
        return BM25Retriever(sample_documents)

    def test_init(self, retriever):
        """测试初始化"""
        assert retriever.is_initialized
        assert retriever.doc_count == 3

    def test_tokenize_chinese(self, retriever):
        """测试中文分词"""
        tokens = retriever.tokenize("肉丸怎么做")
        assert len(tokens) > 0
        assert "肉丸" in tokens

    def test_tokenize_empty(self, retriever):
        """测试空文本分词"""
        tokens = retriever.tokenize("")
        assert tokens == []

    def test_tokenize_punctuation(self, retriever):
        """测试标点符号过滤"""
        tokens = retriever.tokenize("你好，世界！")
        # 标点应被过滤
        assert "，" not in tokens
        assert "！" not in tokens

    def test_retrieve_basic(self, retriever):
        """测试基本检索"""
        results = retriever.retrieve("肉丸怎么做", top_k=3)

        assert len(results) > 0
        # 第一个结果应该是肉丸相关的文档
        doc, score = results[0]
        assert "肉丸" in doc.content
        assert score > 0

    def test_retrieve_empty_query(self, retriever):
        """测试空查询"""
        results = retriever.retrieve("", top_k=3)
        assert results == []

    def test_retrieve_no_match(self, retriever):
        """测试无匹配"""
        results = retriever.retrieve("这是一个完全不相关的查询xyz", top_k=3)
        # 可能有部分匹配或无匹配
        assert isinstance(results, list)

    def test_retrieve_top_k(self, retriever):
        """测试top_k限制"""
        results = retriever.retrieve("饥荒", top_k=2)
        assert len(results) <= 2

    def test_get_scores(self, retriever):
        """测试获取所有分数"""
        scores = retriever.get_scores("肉丸")

        assert len(scores) == 3
        assert all(isinstance(s, float) for s in scores)

    def test_uninitialized_retriever(self):
        """测试未初始化的检索器"""
        retriever = BM25Retriever()

        assert not retriever.is_initialized
        assert retriever.retrieve("test", top_k=3) == []
        assert retriever.get_scores("test") == []

    def test_build_index(self):
        """测试索引构建"""
        retriever = BM25Retriever()

        docs = [
            BM25Document(doc_id="1", content="测试文档一"),
            BM25Document(doc_id="2", content="测试文档二"),
        ]
        retriever.build_index(docs)

        assert retriever.is_initialized
        assert retriever.doc_count == 2

    def test_add_documents(self, retriever):
        """测试添加文档"""
        initial_count = retriever.doc_count

        new_docs = [
            BM25Document(doc_id="4", content="新文档内容"),
        ]
        retriever.add_documents(new_docs)

        assert retriever.doc_count == initial_count + 1


class TestBM25IndexBuilder:
    """BM25IndexBuilder测试"""

    def test_from_texts(self):
        """测试从文本构建"""
        texts = ["文本一", "文本二", "文本三"]
        docs = BM25IndexBuilder.from_texts(texts)

        assert len(docs) == 3
        assert docs[0].content == "文本一"
        assert docs[0].doc_id == "0"

    def test_from_texts_with_metadata(self):
        """测试带元数据构建"""
        texts = ["文本一", "文本二"]
        metadatas = [{"key": "value1"}, {"key": "value2"}]

        docs = BM25IndexBuilder.from_texts(texts, metadatas)

        assert docs[0].metadata == {"key": "value1"}
        assert docs[1].metadata == {"key": "value2"}


class TestBM25Document:
    """BM25Document测试"""

    def test_create_document(self):
        """测试创建文档"""
        doc = BM25Document(
            doc_id="test",
            content="测试内容",
            metadata={"type": "test"}
        )

        assert doc.doc_id == "test"
        assert doc.content == "测试内容"
        assert doc.metadata == {"type": "test"}
        assert doc.tokens == []

    def test_document_with_tokens(self):
        """测试带分词的文档"""
        doc = BM25Document(
            doc_id="test",
            content="测试内容",
            tokens=["测试", "内容"],
        )

        assert doc.tokens == ["测试", "内容"]
