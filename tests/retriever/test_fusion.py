"""RRF融合测试"""

import pytest

from src.retriever.fusion import ReciprocalRankFusion, LinearCombination, FusedResult


class TestReciprocalRankFusion:
    """ReciprocalRankFusion测试"""

    @pytest.fixture
    def rrf(self):
        """创建RRF融合器"""
        return ReciprocalRankFusion(k=60)

    def test_init(self, rrf):
        """测试初始化"""
        assert rrf.k == 60

    def test_fuse_basic(self, rrf):
        """测试基本融合"""
        list1 = ["doc_a", "doc_b", "doc_c"]
        list2 = ["doc_b", "doc_c", "doc_d"]

        results = rrf.fuse(
            [list1, list2],
            get_id=lambda x: x,
        )

        assert len(results) == 4  # a, b, c, d
        assert isinstance(results[0], FusedResult)

        # doc_b在两个列表中都出现，应该排名较高
        doc_ids = [r.item for r in results]
        assert "doc_b" in doc_ids[:2]  # 应在前两位

    def test_fuse_single_list(self, rrf):
        """测试单路结果"""
        list1 = ["doc_a", "doc_b"]

        results = rrf.fuse([list1], get_id=lambda x: x)

        assert len(results) == 2
        assert results[0].item == "doc_a"

    def test_fuse_empty_lists(self, rrf):
        """测试空列表"""
        results = rrf.fuse([])
        assert results == []

        results = rrf.fuse([[], []])
        assert results == []

    def test_fuse_with_source_names(self, rrf):
        """测试带源名称"""
        list1 = ["doc_a"]
        list2 = ["doc_a"]

        results = rrf.fuse(
            [list1, list2],
            get_id=lambda x: x,
            source_names=["vector", "bm25"],
        )

        assert len(results) == 1
        assert "vector" in results[0].ranks
        assert "bm25" in results[0].ranks

    def test_rrf_score_calculation(self, rrf):
        """测试RRF分数计算"""
        # 单个文档在rank 1位置
        list1 = ["doc_a"]

        results = rrf.fuse([list1], get_id=lambda x: x)

        # RRF分数 = 1/(k+rank) = 1/(60+1) ≈ 0.0164
        expected_score = 1.0 / (60 + 1)
        assert abs(results[0].score - expected_score) < 0.001

    def test_fuse_with_weights(self, rrf):
        """测试带权重融合"""
        list1 = ["doc_a", "doc_b"]
        list2 = ["doc_b", "doc_a"]

        results = rrf.fuse_with_weights(
            [list1, list2],
            weights=[0.7, 0.3],
            get_id=lambda x: x,
        )

        assert len(results) == 2
        # 两个文档都出现在两个列表中，但权重不同
        # doc_a: 0.7/(60+1) + 0.3/(60+2)
        # doc_b: 0.7/(60+2) + 0.3/(60+1)


class TestLinearCombination:
    """LinearCombination测试"""

    @pytest.fixture
    def lc(self):
        """创建线性融合器"""
        return LinearCombination()

    def test_fuse_basic(self, lc):
        """测试基本融合"""
        list1 = [("doc_a", 0.9), ("doc_b", 0.8)]
        list2 = [("doc_b", 0.95), ("doc_c", 0.7)]

        results = lc.fuse(
            [list1, list2],
            weights=[0.5, 0.5],
            get_id=lambda x: x,
        )

        assert len(results) == 3  # a, b, c

    def test_fuse_weight_normalization(self, lc):
        """测试权重归一化"""
        list1 = [("doc_a", 1.0)]
        list2 = [("doc_a", 1.0)]

        # 权重不归一化但应内部处理
        results = lc.fuse(
            [list1, list2],
            weights=[2.0, 2.0],
            get_id=lambda x: x,
        )

        assert len(results) == 1

    def test_fuse_empty(self, lc):
        """测试空结果"""
        results = lc.fuse([], weights=[])
        assert results == []


class TestFusedResult:
    """FusedResult测试"""

    def test_create_result(self):
        """测试创建结果"""
        result = FusedResult(
            item="doc_a",
            score=0.5,
            ranks={"vector": 1, "bm25": 2},
        )

        assert result.item == "doc_a"
        assert result.score == 0.5
        assert result.ranks["vector"] == 1
        assert result.ranks["bm25"] == 2
