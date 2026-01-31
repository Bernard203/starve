"""API接口测试"""

import pytest
from unittest.mock import Mock, MagicMock, patch
from fastapi.testclient import TestClient


class TestAPI:
    """API测试类"""

    @pytest.fixture
    def client(self):
        """创建测试客户端"""
        with patch("src.app.api.VectorIndexer"):
            with patch("src.app.api.QAEngine"):
                from src.app.api import create_app
                app = create_app()
                return TestClient(app)

    def test_health_check(self, client):
        """测试健康检查接口"""
        with patch("src.app.api.VectorIndexer") as mock_indexer:
            mock_instance = MagicMock()
            mock_instance.get_collection_stats.return_value = {"count": 100}
            mock_indexer.return_value = mock_instance

            response = client.get("/health")
            assert response.status_code == 200

            data = response.json()
            assert "status" in data
            assert "version" in data
            assert "index_stats" in data

    def test_ask_no_engine(self, client):
        """测试无引擎时的问答"""
        import src.app.api as api_module
        api_module.qa_engine = None

        response = client.post("/ask", json={"question": "测试问题"})
        assert response.status_code == 503

    def test_ask_success(self, client):
        """测试成功问答"""
        import src.app.api as api_module

        # 模拟引擎
        mock_engine = MagicMock()
        mock_engine.ask.return_value = MagicMock(
            answer="测试回答",
            sources=[{"title": "来源", "url": "http://test.com"}],
            confidence=0.9,
        )
        api_module.qa_engine = mock_engine

        response = client.post("/ask", json={"question": "测试问题"})
        assert response.status_code == 200

        data = response.json()
        assert data["answer"] == "测试回答"
        assert data["confidence"] == 0.9

    def test_ask_with_version_filter(self, client):
        """测试带版本过滤的问答"""
        import src.app.api as api_module

        mock_engine = MagicMock()
        mock_engine.ask.return_value = MagicMock(
            answer="回答",
            sources=[],
            confidence=0.8,
        )
        api_module.qa_engine = mock_engine

        response = client.post("/ask", json={
            "question": "测试问题",
            "version_filter": "dst"
        })

        assert response.status_code == 200
        mock_engine.ask.assert_called_once()
        call_args = mock_engine.ask.call_args
        assert call_args[1]["filter_version"] == "dst"

    def test_clear_history(self, client):
        """测试清空历史"""
        import src.app.api as api_module

        mock_engine = MagicMock()
        api_module.qa_engine = mock_engine

        response = client.post("/clear_history")
        assert response.status_code == 200
        mock_engine.clear_history.assert_called_once_with("default")

    def test_get_history(self, client):
        """测试获取历史"""
        import src.app.api as api_module

        mock_engine = MagicMock()
        mock_engine.get_history.return_value = [
            {"role": "user", "content": "问题"}
        ]
        api_module.qa_engine = mock_engine

        response = client.get("/history")
        assert response.status_code == 200

        data = response.json()
        assert "history" in data
        assert len(data["history"]) == 1
        mock_engine.get_history.assert_called_once_with("default")

    def test_ask_validation_error(self, client):
        """测试请求验证错误"""
        response = client.post("/ask", json={"question": ""})
        assert response.status_code == 422

    def test_ask_question_too_long(self, client):
        """测试问题过长"""
        long_question = "问" * 1001
        response = client.post("/ask", json={"question": long_question})
        assert response.status_code == 422

    # ==================== 会话管理测试 ====================

    def test_ask_returns_session_id(self, client):
        """不传 session_id 时应自动生成并返回"""
        import src.app.api as api_module

        mock_engine = MagicMock()
        mock_engine.ask.return_value = MagicMock(
            answer="回答", sources=[], confidence=0.8
        )
        api_module.qa_engine = mock_engine

        response = client.post("/ask", json={"question": "测试"})
        data = response.json()
        assert "session_id" in data
        assert data["session_id"] is not None
        assert len(data["session_id"]) > 0

    def test_ask_with_session_id(self, client):
        """传入 session_id 应正确传递"""
        import src.app.api as api_module

        mock_engine = MagicMock()
        mock_engine.ask.return_value = MagicMock(
            answer="回答", sources=[], confidence=0.8
        )
        api_module.qa_engine = mock_engine

        response = client.post("/ask", json={
            "question": "测试",
            "session_id": "my-session",
        })
        data = response.json()
        assert data["session_id"] == "my-session"
        mock_engine.ask.assert_called_once()
        assert mock_engine.ask.call_args[1]["session_id"] == "my-session"

    def test_clear_history_with_session(self, client):
        """清空指定会话的历史"""
        import src.app.api as api_module

        mock_engine = MagicMock()
        api_module.qa_engine = mock_engine

        response = client.post("/clear_history?session_id=s1")
        assert response.status_code == 200
        mock_engine.clear_history.assert_called_once_with("s1")

    def test_get_history_with_session(self, client):
        """获取指定会话的历史"""
        import src.app.api as api_module

        mock_engine = MagicMock()
        mock_engine.get_history.return_value = []
        api_module.qa_engine = mock_engine

        response = client.get("/history?session_id=s1")
        assert response.status_code == 200
        mock_engine.get_history.assert_called_once_with("s1")

    def test_list_sessions(self, client):
        """测试会话列表端点"""
        import src.app.api as api_module

        mock_engine = MagicMock()
        mock_engine.session_manager.list_sessions.return_value = [
            {"session_id": "s1", "message_count": 4,
             "created_at": "2024-01-01", "updated_at": "2024-01-01"}
        ]
        api_module.qa_engine = mock_engine

        response = client.get("/sessions")
        assert response.status_code == 200
        data = response.json()
        assert len(data["sessions"]) == 1
        assert data["sessions"][0]["session_id"] == "s1"

    def test_list_sessions_no_engine(self, client):
        """无引擎时会话列表返回空"""
        import src.app.api as api_module
        api_module.qa_engine = None

        response = client.get("/sessions")
        assert response.status_code == 200
        assert response.json()["sessions"] == []
