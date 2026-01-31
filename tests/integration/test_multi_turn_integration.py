"""多轮对话集成测试"""

import pytest
from unittest.mock import MagicMock, patch
from fastapi.testclient import TestClient

from src.qa.session import SessionManager


class TestMultiTurnIntegration:
    """通过 API 进行的端到端多轮对话测试"""

    @pytest.fixture
    def client_with_engine(self):
        """创建带模拟引擎的测试客户端"""
        with patch("src.app.api.VectorIndexer"):
            with patch("src.app.api.QAEngine"):
                from src.app.api import create_app
                app = create_app()

                mock_engine = MagicMock()
                session_mgr = SessionManager()

                mock_engine.session_manager = session_mgr

                def mock_ask(**kwargs):
                    question = kwargs["question"]
                    session_id = kwargs.get("session_id", "default")
                    use_history = kwargs.get("use_history", True)
                    answer = f"Answer to: {question}"
                    if use_history:
                        session_mgr.add_turn(session_id, question, answer)
                    return MagicMock(
                        answer=answer,
                        sources=[],
                        confidence=0.9,
                    )

                mock_engine.ask.side_effect = mock_ask
                mock_engine.get_history.side_effect = lambda sid="default": (
                    session_mgr.get_history_dicts(sid)
                )
                mock_engine.clear_history.side_effect = lambda sid="default": (
                    session_mgr.clear_session(sid)
                )

                import src.app.api as api_module
                api_module.qa_engine = mock_engine

                yield TestClient(app)

    def test_multi_turn_flow(self, client_with_engine):
        """多轮对话端到端流程"""
        client = client_with_engine
        session_id = "integration-test"

        # Turn 1
        r1 = client.post("/ask", json={
            "question": "肉丸怎么做",
            "session_id": session_id,
        })
        assert r1.status_code == 200
        assert r1.json()["session_id"] == session_id
        assert "肉丸怎么做" in r1.json()["answer"]

        # Turn 2
        r2 = client.post("/ask", json={
            "question": "还有什么简单的食物",
            "session_id": session_id,
        })
        assert r2.status_code == 200
        assert r2.json()["session_id"] == session_id

        # 检查历史
        r3 = client.get(f"/history?session_id={session_id}")
        assert r3.status_code == 200
        history = r3.json()["history"]
        assert len(history) == 4  # 2 turns * 2

    def test_session_isolation_via_api(self, client_with_engine):
        """API 层面的会话隔离"""
        client = client_with_engine

        client.post("/ask", json={"question": "q1", "session_id": "alice"})
        client.post("/ask", json={"question": "q2", "session_id": "bob"})

        r1 = client.get("/history?session_id=alice")
        r2 = client.get("/history?session_id=bob")

        assert r1.status_code == 200
        assert r2.status_code == 200

        h1 = r1.json()["history"]
        h2 = r2.json()["history"]

        assert len(h1) == 2
        assert len(h2) == 2
        assert h1[0]["content"] == "q1"
        assert h2[0]["content"] == "q2"

    def test_clear_history_via_api(self, client_with_engine):
        """通过 API 清空指定会话"""
        client = client_with_engine

        client.post("/ask", json={"question": "q", "session_id": "s1"})
        client.post("/ask", json={"question": "q", "session_id": "s2"})

        # 清空 s1
        r = client.post("/clear_history?session_id=s1")
        assert r.status_code == 200

        # s1 应为空
        r1 = client.get("/history?session_id=s1")
        assert len(r1.json()["history"]) == 0

        # s2 不受影响
        r2 = client.get("/history?session_id=s2")
        assert len(r2.json()["history"]) == 2

    def test_sessions_list_endpoint(self, client_with_engine):
        """会话列表端点"""
        client = client_with_engine

        client.post("/ask", json={"question": "q", "session_id": "s1"})
        client.post("/ask", json={"question": "q", "session_id": "s2"})

        r = client.get("/sessions")
        assert r.status_code == 200
        sessions = r.json()["sessions"]
        assert len(sessions) == 2
        session_ids = {s["session_id"] for s in sessions}
        assert session_ids == {"s1", "s2"}

    def test_auto_generated_session_id(self, client_with_engine):
        """不传 session_id 时自动生成"""
        client = client_with_engine

        r = client.post("/ask", json={"question": "test"})
        assert r.status_code == 200
        session_id = r.json()["session_id"]
        assert session_id is not None
        assert len(session_id) > 0

    def test_reuse_session_id(self, client_with_engine):
        """客户端可复用返回的 session_id"""
        client = client_with_engine

        # 第一次不传 session_id
        r1 = client.post("/ask", json={"question": "first"})
        session_id = r1.json()["session_id"]

        # 使用返回的 session_id 继续对话
        r2 = client.post("/ask", json={
            "question": "second",
            "session_id": session_id,
        })
        assert r2.json()["session_id"] == session_id
