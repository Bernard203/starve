"""会话管理器测试"""

import json
import tempfile
from pathlib import Path

import pytest
from llama_index.core.llms import ChatMessage, MessageRole

from src.qa.session import ConversationSession, SessionManager


class TestConversationSession:
    """ConversationSession 单元测试"""

    def test_create_session(self):
        session = ConversationSession("test-id")
        assert session.session_id == "test-id"
        assert len(session.messages) == 0

    def test_add_turn(self):
        session = ConversationSession("test-id")
        session.add_turn("你好", "你好！有什么问题？")
        assert len(session.messages) == 2
        assert session.messages[0].role == MessageRole.USER
        assert session.messages[0].content == "你好"
        assert session.messages[1].role == MessageRole.ASSISTANT
        assert session.messages[1].content == "你好！有什么问题？"

    def test_add_multiple_turns(self):
        session = ConversationSession("test-id")
        session.add_turn("q1", "a1")
        session.add_turn("q2", "a2")
        assert len(session.messages) == 4

    def test_get_recent_within_limit(self):
        session = ConversationSession("test-id")
        session.add_turn("q1", "a1")
        session.add_turn("q2", "a2")
        recent = session.get_recent(max_turns=5)
        assert len(recent) == 4

    def test_get_recent_exceeds_limit(self):
        session = ConversationSession("test-id")
        for i in range(10):
            session.add_turn(f"q{i}", f"a{i}")
        recent = session.get_recent(max_turns=3)
        assert len(recent) == 6  # 3 turns * 2 messages
        # 验证是最后3轮
        assert recent[0].content == "q7"
        assert recent[1].content == "a7"
        assert recent[-2].content == "q9"
        assert recent[-1].content == "a9"

    def test_get_recent_empty(self):
        session = ConversationSession("test-id")
        recent = session.get_recent()
        assert recent == []

    def test_clear(self):
        session = ConversationSession("test-id")
        session.add_turn("q", "a")
        session.clear()
        assert len(session.messages) == 0

    def test_updated_at_changes(self):
        session = ConversationSession("test-id")
        created = session.updated_at
        session.add_turn("q", "a")
        assert session.updated_at >= created

    def test_to_dict(self):
        session = ConversationSession("test-id")
        session.add_turn("肉丸怎么做", "需要肉度>=0.5")
        data = session.to_dict()

        assert data["session_id"] == "test-id"
        assert len(data["messages"]) == 2
        assert data["messages"][0]["role"] == "user"
        assert data["messages"][0]["content"] == "肉丸怎么做"
        assert "created_at" in data
        assert "updated_at" in data

    def test_from_dict(self):
        session = ConversationSession("test-id")
        session.add_turn("肉丸怎么做", "需要肉度>=0.5")
        data = session.to_dict()

        restored = ConversationSession.from_dict(data)
        assert restored.session_id == "test-id"
        assert len(restored.messages) == 2
        assert restored.messages[0].content == "肉丸怎么做"
        assert restored.messages[1].content == "需要肉度>=0.5"

    def test_roundtrip_serialization(self):
        session = ConversationSession("roundtrip")
        session.add_turn("q1", "a1")
        session.add_turn("q2", "a2")

        data = session.to_dict()
        json_str = json.dumps(data, ensure_ascii=False)
        parsed = json.loads(json_str)
        restored = ConversationSession.from_dict(parsed)

        assert restored.session_id == session.session_id
        assert len(restored.messages) == len(session.messages)
        for orig, rest in zip(session.messages, restored.messages):
            assert orig.role == rest.role
            assert orig.content == rest.content


class TestSessionManager:
    """SessionManager 单元测试"""

    @pytest.fixture
    def temp_dir(self):
        with tempfile.TemporaryDirectory() as d:
            yield Path(d)

    def test_get_or_create_new(self):
        mgr = SessionManager()
        session = mgr.get_or_create("s1")
        assert session.session_id == "s1"
        assert len(session.messages) == 0

    def test_get_or_create_existing(self):
        mgr = SessionManager()
        s1 = mgr.get_or_create("s1")
        s1.add_turn("q", "a")
        s2 = mgr.get_or_create("s1")
        assert s2 is s1
        assert len(s2.messages) == 2

    def test_get_session_existing(self):
        mgr = SessionManager()
        mgr.get_or_create("s1")
        assert mgr.get_session("s1") is not None

    def test_get_session_nonexistent(self):
        mgr = SessionManager()
        assert mgr.get_session("nonexistent") is None

    def test_add_turn(self):
        mgr = SessionManager()
        mgr.add_turn("s1", "q", "a")
        session = mgr.get_session("s1")
        assert session is not None
        assert len(session.messages) == 2

    def test_session_isolation(self):
        """不同会话有独立的历史"""
        mgr = SessionManager()
        mgr.add_turn("session-a", "question A", "answer A")
        mgr.add_turn("session-b", "question B", "answer B")

        history_a = mgr.get_history_dicts("session-a")
        history_b = mgr.get_history_dicts("session-b")

        assert len(history_a) == 2
        assert len(history_b) == 2
        assert history_a[0]["content"] == "question A"
        assert history_b[0]["content"] == "question B"

    def test_get_history_as_chat_messages(self):
        mgr = SessionManager()
        mgr.add_turn("s1", "q1", "a1")
        mgr.add_turn("s1", "q2", "a2")

        history = mgr.get_history("s1", max_turns=5)
        assert len(history) == 4
        assert all(isinstance(m, ChatMessage) for m in history)

    def test_get_history_with_window(self):
        mgr = SessionManager()
        for i in range(10):
            mgr.add_turn("s1", f"q{i}", f"a{i}")

        history = mgr.get_history("s1", max_turns=2)
        assert len(history) == 4  # 2 turns * 2

    def test_get_history_nonexistent(self):
        mgr = SessionManager()
        assert mgr.get_history("nonexistent") == []
        assert mgr.get_history_dicts("nonexistent") == []

    def test_clear_session(self):
        mgr = SessionManager()
        mgr.add_turn("s1", "q", "a")
        mgr.clear_session("s1")
        assert mgr.get_history_dicts("s1") == []
        # 会话仍然存在，只是历史为空
        assert mgr.get_session("s1") is not None

    def test_clear_nonexistent_session(self):
        mgr = SessionManager()
        mgr.clear_session("nonexistent")  # 不应抛异常

    def test_delete_session(self, temp_dir):
        mgr = SessionManager(storage_dir=temp_dir)
        mgr.add_turn("s1", "q", "a")
        assert (temp_dir / "s1.json").exists()

        mgr.delete_session("s1")
        assert mgr.get_session("s1") is None
        assert not (temp_dir / "s1.json").exists()

    def test_delete_nonexistent_session(self):
        mgr = SessionManager()
        mgr.delete_session("nonexistent")  # 不应抛异常

    def test_persistence_save(self, temp_dir):
        mgr = SessionManager(storage_dir=temp_dir)
        mgr.add_turn("s1", "蜘蛛女皇怎么打", "先清小蜘蛛")

        # 验证文件已写入
        path = temp_dir / "s1.json"
        assert path.exists()

        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        assert data["session_id"] == "s1"
        assert len(data["messages"]) == 2

    def test_persistence_load(self, temp_dir):
        # 先保存
        mgr1 = SessionManager(storage_dir=temp_dir)
        mgr1.add_turn("s1", "蜘蛛女皇怎么打", "先清小蜘蛛")
        mgr1.add_turn("s1", "需要什么装备", "建议大理石甲+火腿棒")

        # 新管理器加载
        mgr2 = SessionManager(storage_dir=temp_dir)
        history = mgr2.get_history_dicts("s1")
        assert len(history) == 4
        assert history[0]["content"] == "蜘蛛女皇怎么打"

    def test_persistence_multiple_sessions(self, temp_dir):
        mgr1 = SessionManager(storage_dir=temp_dir)
        mgr1.add_turn("alice", "hello", "hi")
        mgr1.add_turn("bob", "hey", "yo")

        mgr2 = SessionManager(storage_dir=temp_dir)
        assert len(mgr2.sessions) == 2
        assert mgr2.get_session("alice") is not None
        assert mgr2.get_session("bob") is not None

    def test_max_sessions_eviction(self):
        mgr = SessionManager(max_sessions=3)
        mgr.add_turn("s1", "q1", "a1")
        mgr.add_turn("s2", "q2", "a2")
        mgr.add_turn("s3", "q3", "a3")
        # 第4个会话应驱逐最旧的
        mgr.add_turn("s4", "q4", "a4")

        assert mgr.get_session("s1") is None
        assert mgr.get_session("s4") is not None
        assert len(mgr.sessions) == 3

    def test_list_sessions(self):
        mgr = SessionManager()
        mgr.add_turn("s1", "q", "a")
        mgr.add_turn("s2", "q", "a")

        sessions = mgr.list_sessions()
        assert len(sessions) == 2
        assert all("session_id" in s for s in sessions)
        assert all("message_count" in s for s in sessions)
        assert all("created_at" in s for s in sessions)
        assert all("updated_at" in s for s in sessions)

    def test_list_sessions_sorted_by_updated(self):
        mgr = SessionManager()
        mgr.add_turn("s1", "q", "a")
        mgr.add_turn("s2", "q", "a")
        # s2 was updated last, so it should be first
        sessions = mgr.list_sessions()
        assert sessions[0]["session_id"] == "s2"

    def test_corrupted_file_skipped(self, temp_dir):
        (temp_dir / "bad.json").write_text("not valid json")
        mgr = SessionManager(storage_dir=temp_dir)
        assert "bad" not in mgr.sessions

    def test_no_persistence_without_storage_dir(self):
        mgr = SessionManager()
        mgr.add_turn("s1", "q", "a")
        # 不应抛异常，且没有文件系统操作
        assert mgr.get_session("s1") is not None

    def test_storage_dir_auto_created(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            new_dir = Path(tmpdir) / "sessions" / "nested"
            mgr = SessionManager(storage_dir=new_dir)
            assert new_dir.exists()
            mgr.add_turn("s1", "q", "a")
            assert (new_dir / "s1.json").exists()
