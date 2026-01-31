"""多轮对话流程测试"""

import pytest
from unittest.mock import patch, MagicMock

from llama_index.core.llms import ChatMessage, MessageRole

from src.qa.qa_engine import QAEngine
from src.qa.session import SessionManager


class TestMultiTurnFlow:
    """测试多轮对话通过 QAEngine.ask() 的完整流程"""

    @pytest.fixture
    def engine(self):
        """创建一个内部组件被 mock 的 QAEngine"""
        with patch.object(QAEngine, "__init__", lambda self, index: None):
            engine = QAEngine(None)

        # Mock LLM
        engine.llm = MagicMock()

        # Mock retriever / reranker
        engine.retriever = MagicMock()
        engine.retriever.retrieve.return_value = []
        engine.reranker = MagicMock()
        engine.llm_config = MagicMock()

        # 使用内存中的 SessionManager
        engine.session_manager = SessionManager()
        engine.max_turns = 5

        return engine

    def _set_llm_response(self, engine, text):
        mock_response = MagicMock()
        mock_response.message.content = text
        engine.llm.chat.return_value = mock_response

    def test_single_turn(self, engine):
        """单轮对话应正常工作"""
        self._set_llm_response(engine, "肉丸需要肉度>=0.5")
        response = engine.ask("肉丸怎么做", session_id="s1")

        assert response.answer == "肉丸需要肉度>=0.5"
        engine.llm.chat.assert_called_once()

    def test_history_passed_to_llm(self, engine):
        """第二轮对话时，历史消息应被传入 LLM"""
        self._set_llm_response(engine, "回答1")
        engine.ask("问题1", session_id="s1")

        self._set_llm_response(engine, "回答2")
        engine.ask("问题2", session_id="s1")

        # 检查第二次调用的消息
        call_args = engine.llm.chat.call_args_list[1]
        messages = call_args[0][0]

        # 应包含: system + history(user+assistant) + current_user
        assert messages[0].role == MessageRole.SYSTEM
        # 中间应有历史消息
        history_msgs = messages[1:-1]
        assert len(history_msgs) == 2  # 1 turn = 2 messages
        assert history_msgs[0].role == MessageRole.USER
        assert history_msgs[0].content == "问题1"
        assert history_msgs[1].role == MessageRole.ASSISTANT

    def test_first_turn_no_history(self, engine):
        """第一轮对话时，不应有历史消息"""
        self._set_llm_response(engine, "回答")
        engine.ask("问题", session_id="s1")

        call_args = engine.llm.chat.call_args_list[0]
        messages = call_args[0][0]

        # 只有 system + current_user
        assert len(messages) == 2
        assert messages[0].role == MessageRole.SYSTEM
        assert messages[1].role == MessageRole.USER

    def test_history_not_passed_when_disabled(self, engine):
        """use_history=False 时不传历史"""
        self._set_llm_response(engine, "回答1")
        engine.ask("问题1", session_id="s1")

        self._set_llm_response(engine, "回答2")
        engine.ask("问题2", use_history=False, session_id="s1")

        call_args = engine.llm.chat.call_args_list[1]
        messages = call_args[0][0]
        # 只有 system + current_user
        assert len(messages) == 2

    def test_history_not_saved_when_disabled(self, engine):
        """use_history=False 时不保存到历史"""
        self._set_llm_response(engine, "回答1")
        engine.ask("问题1", use_history=False, session_id="s1")

        history = engine.get_history(session_id="s1")
        assert len(history) == 0

    def test_session_isolation(self, engine):
        """不同 session_id 应有独立的历史"""
        self._set_llm_response(engine, "A回答")
        engine.ask("A问题", session_id="session-a")

        self._set_llm_response(engine, "B回答")
        engine.ask("B问题", session_id="session-b")

        history_a = engine.get_history(session_id="session-a")
        history_b = engine.get_history(session_id="session-b")

        assert len(history_a) == 2
        assert len(history_b) == 2
        assert history_a[0]["content"] == "A问题"
        assert history_b[0]["content"] == "B问题"

    def test_session_isolation_in_llm_call(self, engine):
        """session-b 的 LLM 调用不应包含 session-a 的历史"""
        self._set_llm_response(engine, "A回答")
        engine.ask("A问题", session_id="session-a")

        self._set_llm_response(engine, "B回答")
        engine.ask("B问题", session_id="session-b")

        # session-b 的调用不应有历史
        call_args = engine.llm.chat.call_args_list[1]
        messages = call_args[0][0]
        assert len(messages) == 2  # system + current only

    def test_history_window_truncation(self, engine):
        """超过 max_turns 的历史应被截断"""
        engine.max_turns = 2

        for i in range(5):
            self._set_llm_response(engine, f"回答{i}")
            engine.ask(f"问题{i}", session_id="s1")

        # 最后一次调用
        call_args = engine.llm.chat.call_args_list[-1]
        messages = call_args[0][0]

        # system(1) + history(2 turns * 2 = 4) + current(1) = 6
        history_msgs = messages[1:-1]
        assert len(history_msgs) == 4

    def test_clear_history_for_session(self, engine):
        """清空历史只影响指定 session"""
        self._set_llm_response(engine, "a")
        engine.ask("q", session_id="s1")
        engine.ask("q", session_id="s2")

        engine.clear_history(session_id="s1")

        assert len(engine.get_history("s1")) == 0
        assert len(engine.get_history("s2")) == 2

    def test_default_session_backward_compat(self, engine):
        """不传 session_id 时使用默认 session"""
        self._set_llm_response(engine, "答案")
        engine.ask("问题")

        history = engine.get_history()  # 不传 session_id
        assert len(history) == 2
        assert history[0]["content"] == "问题"
        assert history[1]["content"] == "答案"

    def test_chat_history_property_backward_compat(self, engine):
        """chat_history 属性应返回默认 session 的消息"""
        self._set_llm_response(engine, "答案")
        engine.ask("问题")

        chat_history = engine.chat_history
        assert len(chat_history) == 2
        assert isinstance(chat_history[0], ChatMessage)

    def test_multi_turn_accumulation(self, engine):
        """验证多轮对话正确累积"""
        for i in range(3):
            self._set_llm_response(engine, f"回答{i}")
            engine.ask(f"问题{i}", session_id="s1")

        history = engine.get_history("s1")
        assert len(history) == 6  # 3 turns * 2

        # 验证顺序正确
        expected = ["问题0", "回答0", "问题1", "回答1", "问题2", "回答2"]
        actual = [h["content"] for h in history]
        assert actual == expected
