"""检索模块测试"""

import pytest
from unittest.mock import Mock, MagicMock, patch
from dataclasses import dataclass

from src.retriever import HybridRetriever, Reranker
from src.retriever.retriever import RetrievalResult


class TestHybridRetriever:
    """HybridRetriever测试类"""

    @pytest.fixture
    def mock_index(self):
        """模拟向量索引"""
        mock = MagicMock()
        return mock

    @pytest.fixture
    def mock_retriever(self, mock_index):
        """创建模拟的检索器"""
        with patch.object(HybridRetriever, "_build_synonym_map", return_value={}):
            with patch("src.retriever.retriever.VectorIndexRetriever"):
                retriever = HybridRetriever(mock_index)
                return retriever

    def test_expand_query_with_synonym(self):
        """测试同义词扩展"""
        with patch.object(HybridRetriever, "__init__", lambda x, y: None):
            retriever = HybridRetriever(None)
            retriever.synonyms = {"肉丸子": "肉丸", "蒸肉丸": "肉丸"}
            retriever.config = MagicMock()

            query = "怎么做肉丸子"
            expanded = retriever.expand_query(query)

            assert "肉丸" in expanded

    def test_expand_query_no_synonym(self):
        """测试无同义词时不变"""
        with patch.object(HybridRetriever, "__init__", lambda x, y: None):
            retriever = HybridRetriever(None)
            retriever.synonyms = {"其他词": "替换词"}
            retriever.config = MagicMock()

            query = "怎么打蜘蛛女皇"
            expanded = retriever.expand_query(query)

            assert expanded == query

    def test_build_synonym_map(self):
        """测试同义词映射构建"""
        with patch.object(HybridRetriever, "__init__", lambda x, y: None):
            retriever = HybridRetriever(None)
            synonym_map = retriever._build_synonym_map()

            # 检查默认同义词
            assert "蒸肉丸" in synonym_map
            assert synonym_map["蒸肉丸"] == "肉丸"


class TestReranker:
    """Reranker测试类"""

    def test_init_disabled(self):
        """测试禁用重排序"""
        with patch("config.settings") as mock_settings:
            mock_settings.retriever.use_reranker = False
            reranker = Reranker()
            assert reranker.model is None

    def test_rerank_no_model(self):
        """测试无模型时直接返回"""
        reranker = Reranker()
        reranker.model = None

        results = [
            RetrievalResult(content="内容1", score=0.8, metadata={}),
            RetrievalResult(content="内容2", score=0.6, metadata={}),
        ]

        reranked = reranker.rerank("查询", results)
        assert reranked == results

    def test_rerank_empty_results(self):
        """测试空结果"""
        reranker = Reranker()
        reranked = reranker.rerank("查询", [])
        assert len(reranked) == 0

    @patch("src.retriever.reranker.CrossEncoder")
    def test_rerank_with_model(self, mock_cross_encoder):
        """测试有模型时的重排序"""
        # 设置模拟
        mock_model = MagicMock()
        mock_model.predict.return_value = [0.9, 0.3, 0.7]
        mock_cross_encoder.return_value = mock_model

        with patch("config.settings") as mock_settings:
            mock_settings.retriever.use_reranker = True
            mock_settings.retriever.reranker_model = "test-model"
            mock_settings.embedding.device = "cpu"

            reranker = Reranker()
            reranker.model = mock_model

            results = [
                RetrievalResult(content="内容1", score=0.5, metadata={}),
                RetrievalResult(content="内容2", score=0.5, metadata={}),
                RetrievalResult(content="内容3", score=0.5, metadata={}),
            ]

            reranked = reranker.rerank("查询", results, top_k=2)

            assert len(reranked) == 2
            # 分数最高的应该在前面
            assert reranked[0].score == 0.9

    @patch("src.retriever.reranker.CrossEncoder")
    def test_rerank_preserves_order_by_score(self, mock_cross_encoder):
        """测试重排序后按分数降序排列"""
        mock_model = MagicMock()
        mock_model.predict.return_value = [0.3, 0.9, 0.5, 0.7]
        mock_cross_encoder.return_value = mock_model

        with patch("config.settings") as mock_settings:
            mock_settings.retriever.use_reranker = True
            mock_settings.retriever.reranker_model = "test-model"
            mock_settings.embedding.device = "cpu"

            reranker = Reranker()
            reranker.model = mock_model

            results = [
                RetrievalResult(content="A", score=0.5, metadata={}),
                RetrievalResult(content="B", score=0.5, metadata={}),
                RetrievalResult(content="C", score=0.5, metadata={}),
                RetrievalResult(content="D", score=0.5, metadata={}),
            ]

            reranked = reranker.rerank("查询", results)

            # 验证按分数降序
            assert reranked[0].content == "B"  # 0.9
            assert reranked[1].content == "D"  # 0.7
            assert reranked[2].content == "C"  # 0.5
            assert reranked[3].content == "A"  # 0.3

    @patch("src.retriever.reranker.CrossEncoder")
    def test_rerank_top_k_default(self, mock_cross_encoder):
        """测试top_k默认返回所有结果"""
        mock_model = MagicMock()
        mock_model.predict.return_value = [0.5, 0.8, 0.3]
        mock_cross_encoder.return_value = mock_model

        with patch("config.settings") as mock_settings:
            mock_settings.retriever.use_reranker = True
            mock_settings.retriever.reranker_model = "test-model"
            mock_settings.embedding.device = "cpu"

            reranker = Reranker()
            reranker.model = mock_model

            results = [
                RetrievalResult(content="1", score=0.5, metadata={}),
                RetrievalResult(content="2", score=0.5, metadata={}),
                RetrievalResult(content="3", score=0.5, metadata={}),
            ]

            reranked = reranker.rerank("查询", results)

            assert len(reranked) == 3  # 返回所有

    def test_rerank_model_predict_exception(self):
        """测试模型预测异常时的回退"""
        with patch("config.settings") as mock_settings:
            mock_settings.retriever.use_reranker = False

            reranker = Reranker()

            # 创建一个会抛出异常的模型
            mock_model = MagicMock()
            mock_model.predict.side_effect = Exception("预测失败")
            reranker.model = mock_model

            results = [
                RetrievalResult(content="内容1", score=0.8, metadata={}),
                RetrievalResult(content="内容2", score=0.6, metadata={}),
            ]

            # 应该返回原始结果（截断到top_k）
            reranked = reranker.rerank("查询", results, top_k=1)
            assert len(reranked) == 1
            assert reranked[0].content == "内容1"

    @patch("src.retriever.reranker.CrossEncoder")
    def test_init_model_failure_graceful(self, mock_cross_encoder):
        """测试模型初始化失败时的优雅降级"""
        mock_cross_encoder.side_effect = Exception("模型加载失败")

        with patch("config.settings") as mock_settings:
            mock_settings.retriever.use_reranker = True
            mock_settings.retriever.reranker_model = "invalid-model"
            mock_settings.embedding.device = "cpu"

            # 不应该抛出异常
            reranker = Reranker()
            assert reranker.model is None

    @patch("src.retriever.reranker.CrossEncoder")
    def test_rerank_updates_scores_in_place(self, mock_cross_encoder):
        """测试重排序会更新结果的分数"""
        mock_model = MagicMock()
        mock_model.predict.return_value = [0.95, 0.55]
        mock_cross_encoder.return_value = mock_model

        with patch("config.settings") as mock_settings:
            mock_settings.retriever.use_reranker = True
            mock_settings.retriever.reranker_model = "test-model"
            mock_settings.embedding.device = "cpu"

            reranker = Reranker()
            reranker.model = mock_model

            result1 = RetrievalResult(content="内容1", score=0.3, metadata={})
            result2 = RetrievalResult(content="内容2", score=0.7, metadata={})

            reranked = reranker.rerank("查询", [result1, result2])

            # 分数应该被更新
            assert result1.score == 0.95
            assert result2.score == 0.55

    @patch("src.retriever.reranker.CrossEncoder")
    def test_rerank_with_auto_device(self, mock_cross_encoder):
        """测试auto设备检测"""
        mock_cross_encoder.return_value = MagicMock()

        with patch("config.settings") as mock_settings:
            mock_settings.retriever.use_reranker = True
            mock_settings.retriever.reranker_model = "test-model"
            mock_settings.embedding.device = "auto"

            with patch("torch.cuda.is_available", return_value=False):
                reranker = Reranker()

            # 应该成功初始化
            assert reranker.model is not None


class TestRetrievalResult:
    """RetrievalResult测试类"""

    def test_create_result(self):
        """测试创建检索结果"""
        result = RetrievalResult(
            content="测试内容",
            score=0.85,
            metadata={"key": "value"},
            source_url="http://test.com",
            source_title="测试标题",
        )

        assert result.content == "测试内容"
        assert result.score == 0.85
        assert result.source_title == "测试标题"
