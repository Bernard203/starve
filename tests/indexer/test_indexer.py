"""索引模块测试"""

import pytest
from unittest.mock import Mock, patch, MagicMock

from src.indexer import DocumentProcessor, VectorIndexer
from src.utils.models import WikiPage, Document


class TestDocumentProcessor:
    """DocumentProcessor测试类"""

    def test_init(self):
        """测试处理器初始化"""
        processor = DocumentProcessor()
        assert processor.chunk_size > 0
        assert processor.chunk_overlap >= 0

    def test_clean_text(self):
        """测试文本清理"""
        processor = DocumentProcessor()

        text = "[[链接]]  {{模板}}  <tag>内容</tag>"
        cleaned = processor._clean_text(text)

        assert "[[" not in cleaned
        assert "{{" not in cleaned
        assert "<tag>" not in cleaned

    def test_split_text_short(self):
        """测试短文本分块（不需要分块）"""
        processor = DocumentProcessor()
        processor.chunk_size = 1000

        text = "这是一段很短的文本"
        chunks = processor._split_text(text)

        assert len(chunks) == 1
        assert chunks[0] == text

    def test_split_text_long(self):
        """测试长文本分块"""
        processor = DocumentProcessor()
        processor.chunk_size = 100
        processor.chunk_overlap = 20

        text = "这是一段很长的文本。" * 50
        chunks = processor._split_text(text)

        assert len(chunks) > 1
        # 每个块不应超过chunk_size太多
        for chunk in chunks:
            assert len(chunk) < processor.chunk_size * 2

    def test_process_wiki_page(self, sample_wiki_page):
        """测试Wiki页面处理"""
        processor = DocumentProcessor()
        documents = processor.process_wiki_page(sample_wiki_page)

        assert len(documents) >= 1
        assert all(isinstance(doc, Document) for doc in documents)
        assert all(doc.source_title == sample_wiki_page.title for doc in documents)

    def test_process_wiki_page_empty(self):
        """测试空页面处理"""
        processor = DocumentProcessor()

        empty_page = WikiPage(
            page_id=1,
            title="空页面",
            url="http://test.com",
            content="",
        )

        documents = processor.process_wiki_page(empty_page)
        assert len(documents) == 0

    def test_process_pages(self, sample_wiki_page):
        """测试批量处理"""
        processor = DocumentProcessor()
        pages = [sample_wiki_page, sample_wiki_page]

        documents = list(processor.process_pages(pages))
        assert len(documents) >= 2

    def test_generate_doc_id(self):
        """测试文档ID生成"""
        processor = DocumentProcessor()

        id1 = processor._generate_doc_id(123, 0)
        id2 = processor._generate_doc_id(123, 1)
        id3 = processor._generate_doc_id(124, 0)

        assert id1 != id2
        assert id1 != id3
        assert len(id1) == 16


class TestVectorIndexer:
    """VectorIndexer测试类"""

    @pytest.fixture
    def mock_embedding_model(self):
        """模拟Embedding模型"""
        with patch("src.indexer.indexer.HuggingFaceEmbedding") as mock:
            mock_instance = MagicMock()
            mock_instance.get_text_embedding.return_value = [0.1] * 768
            mock.return_value = mock_instance
            yield mock

    @pytest.fixture
    def mock_chroma(self):
        """模拟Chroma客户端"""
        with patch("src.indexer.indexer.chromadb.PersistentClient") as mock:
            mock_instance = MagicMock()
            mock_collection = MagicMock()
            mock_collection.count.return_value = 100
            mock_instance.get_or_create_collection.return_value = mock_collection
            mock.return_value = mock_instance
            yield mock

    def test_get_collection_stats(self, mock_embedding_model, mock_chroma):
        """测试获取集合统计"""
        indexer = VectorIndexer(collection_name="test")
        stats = indexer.get_collection_stats()

        assert "name" in stats
        assert "count" in stats
        assert stats["name"] == "test"
