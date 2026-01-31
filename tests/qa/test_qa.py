"""问答模块测试"""

import pytest
from unittest.mock import Mock, MagicMock, patch

from src.qa import QAEngine, SYSTEM_PROMPT
from src.qa.prompts import get_prompt_template, QA_PROMPT_TEMPLATE, RECIPE_PROMPT_TEMPLATE


class TestPrompts:
    """提示词测试类"""

    def test_system_prompt_not_empty(self):
        """测试系统提示词非空"""
        assert len(SYSTEM_PROMPT) > 0
        assert "饥荒" in SYSTEM_PROMPT

    def test_get_prompt_template_default(self):
        """测试默认模板选择"""
        template = get_prompt_template("这是一个普通问题")
        assert template == QA_PROMPT_TEMPLATE

    def test_get_prompt_template_recipe(self):
        """测试配方模板选择"""
        questions = [
            "肉丸怎么做",
            "怎么合成长矛",
            "需要什么材料",
        ]

        for q in questions:
            template = get_prompt_template(q)
            assert template == RECIPE_PROMPT_TEMPLATE

    def test_get_prompt_template_boss(self):
        """测试Boss模板选择"""
        from src.qa.prompts import BOSS_PROMPT_TEMPLATE

        questions = [
            "蜘蛛女皇怎么打",
            "远古守护者多少血",
            "boss攻略",
        ]

        for q in questions:
            template = get_prompt_template(q)
            assert template == BOSS_PROMPT_TEMPLATE

    def test_get_prompt_template_strategy(self):
        """测试策略模板选择"""
        from src.qa.prompts import STRATEGY_PROMPT_TEMPLATE

        questions = [
            "新手怎么过冬天",
            "有什么生存技巧",
        ]

        for q in questions:
            template = get_prompt_template(q)
            assert template == STRATEGY_PROMPT_TEMPLATE


class TestQAEngine:
    """QAEngine测试类"""

    @pytest.fixture
    def mock_index(self):
        """模拟向量索引"""
        return MagicMock()

    @pytest.fixture
    def mock_llm(self):
        """模拟LLM"""
        mock = MagicMock()
        mock_response = MagicMock()
        mock_response.message.content = "这是一个测试回答"
        mock.chat.return_value = mock_response
        return mock

    @pytest.fixture
    def mock_retriever(self):
        """模拟检索器"""
        mock = MagicMock()
        mock.retrieve.return_value = []
        return mock

    def test_build_context_empty(self):
        """测试空结果上下文构建"""
        with patch.object(QAEngine, "__init__", lambda x, y: None):
            engine = QAEngine(None)
            context = engine._build_context([])
            assert "未找到" in context

    def test_build_context_with_results(self):
        """测试有结果时的上下文构建"""
        with patch.object(QAEngine, "__init__", lambda x, y: None):
            engine = QAEngine(None)

            # 创建模拟结果
            from src.retriever.retriever import RetrievalResult
            results = [
                RetrievalResult(
                    content="内容1",
                    score=0.9,
                    metadata={},
                    source_title="来源1"
                ),
                RetrievalResult(
                    content="内容2",
                    score=0.8,
                    metadata={},
                    source_title="来源2"
                ),
            ]

            context = engine._build_context(results)

            assert "内容1" in context
            assert "内容2" in context
            assert "来源1" in context

    def test_calculate_confidence_no_results(self):
        """测试无结果时的置信度"""
        with patch.object(QAEngine, "__init__", lambda x, y: None):
            engine = QAEngine(None)
            confidence = engine._calculate_confidence([])
            assert confidence == 0.3

    def test_calculate_confidence_with_results(self):
        """测试有结果时的置信度"""
        with patch.object(QAEngine, "__init__", lambda x, y: None):
            engine = QAEngine(None)

            from src.retriever.retriever import RetrievalResult
            results = [
                RetrievalResult(content="", score=0.95, metadata={}),
                RetrievalResult(content="", score=0.7, metadata={}),
            ]

            confidence = engine._calculate_confidence(results)
            assert confidence == 0.95

    def test_clear_history(self):
        """测试清空历史"""
        with patch.object(QAEngine, "__init__", lambda x, y: None):
            from src.qa.session import SessionManager

            engine = QAEngine(None)
            engine.session_manager = SessionManager()
            engine.session_manager.add_turn("default", "问题", "回答")

            engine.clear_history()
            assert len(engine.chat_history) == 0

    def test_get_history(self):
        """测试获取历史"""
        with patch.object(QAEngine, "__init__", lambda x, y: None):
            from src.qa.session import SessionManager

            engine = QAEngine(None)
            engine.session_manager = SessionManager()
            engine.session_manager.add_turn("default", "问题", "回答")

            history = engine.get_history()
            assert len(history) == 2
            assert history[0]["role"] == "user"
            assert history[1]["role"] == "assistant"
