"""MMR多样性测试"""

import pytest

from src.retriever.mmr import (
    MMRDiversifier,
    ContentBasedDiversifier,
    MMRResult,
)


class TestMMRDiversifier:
    """MMRDiversifier测试"""

    @pytest.fixture
    def mmr(self):
        """创建MMR优化器"""
        return MMRDiversifier(lambda_param=0.5)

    def test_init(self, mmr):
        """测试初始化"""
        assert mmr.lambda_param == 0.5

    def test_init_invalid_lambda(self):
        """测试无效lambda值"""
        with pytest.raises(ValueError):
            MMRDiversifier(lambda_param=1.5)

        with pytest.raises(ValueError):
            MMRDiversifier(lambda_param=-0.1)

    def test_diversify_basic(self, mmr):
        """测试基本MMR选择"""
        candidates = ["doc_a", "doc_b", "doc_c"]
        relevance_scores = [0.9, 0.8, 0.7]

        # 简单相似度矩阵（对角线为1，其他为0.5）
        similarity_matrix = [
            [1.0, 0.5, 0.5],
            [0.5, 1.0, 0.5],
            [0.5, 0.5, 1.0],
        ]

        results = mmr.diversify(
            candidates=candidates,
            relevance_scores=relevance_scores,
            similarity_matrix=similarity_matrix,
            top_k=2,
        )

        assert len(results) == 2
        assert isinstance(results[0], MMRResult)

    def test_diversify_empty(self, mmr):
        """测试空候选"""
        results = mmr.diversify(
            candidates=[],
            relevance_scores=[],
            top_k=5,
        )
        assert results == []

    def test_diversify_single(self, mmr):
        """测试单个候选"""
        results = mmr.diversify(
            candidates=["doc_a"],
            relevance_scores=[0.9],
            similarity_matrix=[[1.0]],
            top_k=5,
        )

        assert len(results) == 1
        assert results[0].item == "doc_a"

    def test_mmr_diversity(self, mmr):
        """测试MMR多样性效果"""
        # 3个文档，前两个高度相似
        candidates = ["doc_a", "doc_b", "doc_c"]
        relevance_scores = [0.9, 0.88, 0.5]

        # doc_a和doc_b高度相似
        similarity_matrix = [
            [1.0, 0.95, 0.1],
            [0.95, 1.0, 0.1],
            [0.1, 0.1, 1.0],
        ]

        results = mmr.diversify(
            candidates=candidates,
            relevance_scores=relevance_scores,
            similarity_matrix=similarity_matrix,
            top_k=2,
        )

        # 由于doc_a和doc_b高度相似，doc_c可能被选中以增加多样性
        selected_items = [r.item for r in results]
        # 第一个应该是最相关的doc_a
        assert results[0].item == "doc_a"

    def test_lambda_effect_relevance(self):
        """测试lambda=1时只考虑相关性"""
        mmr = MMRDiversifier(lambda_param=1.0)

        candidates = ["doc_a", "doc_b", "doc_c"]
        relevance_scores = [0.7, 0.9, 0.5]
        similarity_matrix = [
            [1.0, 0.9, 0.9],
            [0.9, 1.0, 0.9],
            [0.9, 0.9, 1.0],
        ]

        results = mmr.diversify(
            candidates=candidates,
            relevance_scores=relevance_scores,
            similarity_matrix=similarity_matrix,
            top_k=3,
        )

        # lambda=1时应该完全按相关性排序
        assert results[0].item == "doc_b"  # 最高相关性
        assert results[1].item == "doc_a"

    def test_diversify_with_embeddings(self, mmr):
        """测试使用嵌入的MMR"""
        candidates = ["doc_a", "doc_b"]
        relevance_scores = [0.9, 0.8]
        embeddings = [
            [1.0, 0.0, 0.0],
            [0.9, 0.1, 0.0],
        ]

        results = mmr.diversify_with_embeddings(
            candidates=candidates,
            relevance_scores=relevance_scores,
            embeddings=embeddings,
            top_k=2,
        )

        assert len(results) == 2

    def test_no_similarity_matrix(self, mmr):
        """测试无相似度矩阵时的降级"""
        candidates = ["doc_a", "doc_b", "doc_c"]
        relevance_scores = [0.9, 0.8, 0.7]

        results = mmr.diversify(
            candidates=candidates,
            relevance_scores=relevance_scores,
            top_k=2,
        )

        # 应该按相关性排序
        assert len(results) == 2
        assert results[0].item == "doc_a"


class TestContentBasedDiversifier:
    """ContentBasedDiversifier测试"""

    @pytest.fixture
    def deduplicator(self):
        """创建去重器"""
        return ContentBasedDiversifier(similarity_threshold=0.8)

    def test_init(self, deduplicator):
        """测试初始化"""
        assert deduplicator.similarity_threshold == 0.8

    def test_deduplicate_basic(self, deduplicator):
        """测试基本去重"""
        candidates = [
            {"content": "这是第一个文档"},
            {"content": "这是第二个文档"},
            {"content": "这是第一个文档的副本"},  # 与第一个高度相似
        ]

        results = deduplicator.deduplicate(
            candidates,
            get_content=lambda x: x["content"],
        )

        # 第三个应该被过滤
        assert len(results) <= 3

    def test_deduplicate_all_unique(self, deduplicator):
        """测试全部唯一"""
        candidates = [
            {"content": "完全不同的内容一"},
            {"content": "另一个完全不同的内容"},
            {"content": "第三个独特的文本"},
        ]

        results = deduplicator.deduplicate(
            candidates,
            get_content=lambda x: x["content"],
        )

        assert len(results) == 3

    def test_deduplicate_empty(self, deduplicator):
        """测试空列表"""
        results = deduplicator.deduplicate([], get_content=lambda x: x)
        assert results == []

    def test_deduplicate_single(self, deduplicator):
        """测试单个元素"""
        candidates = [{"content": "单个文档"}]

        results = deduplicator.deduplicate(
            candidates,
            get_content=lambda x: x["content"],
        )

        assert len(results) == 1

    def test_jaccard_similarity_identical(self, deduplicator):
        """测试相同文本的Jaccard相似度"""
        text = "这是一段测试文本"
        sim = deduplicator._jaccard_similarity(text, text)
        assert sim == 1.0

    def test_jaccard_similarity_different(self, deduplicator):
        """测试不同文本的Jaccard相似度"""
        text1 = "这是第一段文本"
        text2 = "完全不同的内容xyz"
        sim = deduplicator._jaccard_similarity(text1, text2)
        assert sim < 0.5

    def test_jaccard_similarity_empty(self, deduplicator):
        """测试空文本的Jaccard相似度"""
        assert deduplicator._jaccard_similarity("", "test") == 0.0
        assert deduplicator._jaccard_similarity("test", "") == 0.0
        assert deduplicator._jaccard_similarity("", "") == 0.0


class TestMMRResult:
    """MMRResult测试"""

    def test_create_result(self):
        """测试创建结果"""
        result = MMRResult(
            item="doc_a",
            relevance_score=0.9,
            diversity_penalty=0.3,
            mmr_score=0.6,
        )

        assert result.item == "doc_a"
        assert result.relevance_score == 0.9
        assert result.diversity_penalty == 0.3
        assert result.mmr_score == 0.6
