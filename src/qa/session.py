"""会话管理器 - 支持多会话隔离和持久化"""

import json
from datetime import datetime
from pathlib import Path
from typing import Optional

from llama_index.core.llms import ChatMessage, MessageRole

from src.utils.logger import logger


class ConversationSession:
    """单个对话会话"""

    def __init__(self, session_id: str):
        self.session_id = session_id
        self.messages: list[ChatMessage] = []
        self.created_at = datetime.now()
        self.updated_at = datetime.now()

    def add_turn(self, user_msg: str, assistant_msg: str):
        """追加一轮对话（用户问题 + 助手回答）"""
        self.messages.append(ChatMessage(role=MessageRole.USER, content=user_msg))
        self.messages.append(ChatMessage(role=MessageRole.ASSISTANT, content=assistant_msg))
        self.updated_at = datetime.now()

    def get_recent(self, max_turns: int = 5) -> list[ChatMessage]:
        """获取最近 max_turns 轮对话（2*max_turns 条消息）"""
        if not self.messages:
            return []
        return self.messages[-(max_turns * 2):]

    def clear(self):
        """清空消息"""
        self.messages = []
        self.updated_at = datetime.now()

    def to_dict(self) -> dict:
        """序列化为字典"""
        return {
            "session_id": self.session_id,
            "messages": [
                {"role": msg.role.value, "content": msg.content}
                for msg in self.messages
            ],
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
        }

    @classmethod
    def from_dict(cls, data: dict) -> "ConversationSession":
        """从字典反序列化"""
        session = cls(data["session_id"])
        session.messages = [
            ChatMessage(
                role=MessageRole(m["role"]),
                content=m["content"],
            )
            for m in data.get("messages", [])
        ]
        session.created_at = datetime.fromisoformat(data["created_at"])
        session.updated_at = datetime.fromisoformat(data["updated_at"])
        return session


class SessionManager:
    """多会话管理器，支持持久化和LRU驱逐"""

    def __init__(self, storage_dir: Optional[Path] = None, max_sessions: int = 100):
        self.sessions: dict[str, ConversationSession] = {}
        self.storage_dir = storage_dir
        self.max_sessions = max_sessions

        if self.storage_dir:
            self.storage_dir.mkdir(parents=True, exist_ok=True)
            self._load_sessions()

        logger.info(f"会话管理器初始化完成, 已加载 {len(self.sessions)} 个会话")

    def get_or_create(self, session_id: str) -> ConversationSession:
        """获取已有会话或创建新会话"""
        if session_id not in self.sessions:
            self._evict_if_needed()
            self.sessions[session_id] = ConversationSession(session_id)
        return self.sessions[session_id]

    def get_session(self, session_id: str) -> Optional[ConversationSession]:
        """获取已有会话，不存在返回 None"""
        return self.sessions.get(session_id)

    def add_turn(self, session_id: str, user_msg: str, assistant_msg: str):
        """向指定会话添加一轮对话"""
        session = self.get_or_create(session_id)
        session.add_turn(user_msg, assistant_msg)
        self._save_session(session_id)

    def get_history(self, session_id: str, max_turns: int = 5) -> list[ChatMessage]:
        """获取指定会话的最近历史（ChatMessage 列表）"""
        session = self.sessions.get(session_id)
        if not session:
            return []
        return session.get_recent(max_turns)

    def get_history_dicts(self, session_id: str) -> list[dict]:
        """获取指定会话的完整历史（dict 列表）"""
        session = self.sessions.get(session_id)
        if not session:
            return []
        return [
            {"role": msg.role.value, "content": msg.content}
            for msg in session.messages
        ]

    def clear_session(self, session_id: str):
        """清空指定会话的历史"""
        session = self.sessions.get(session_id)
        if session:
            session.clear()
            self._save_session(session_id)

    def delete_session(self, session_id: str):
        """删除指定会话（内存 + 磁盘）"""
        if session_id in self.sessions:
            del self.sessions[session_id]
        if self.storage_dir:
            path = self.storage_dir / f"{session_id}.json"
            if path.exists():
                path.unlink()

    def list_sessions(self) -> list[dict]:
        """列出所有会话的元信息"""
        return [
            {
                "session_id": s.session_id,
                "message_count": len(s.messages),
                "created_at": s.created_at.isoformat(),
                "updated_at": s.updated_at.isoformat(),
            }
            for s in sorted(
                self.sessions.values(),
                key=lambda x: x.updated_at,
                reverse=True,
            )
        ]

    def _save_session(self, session_id: str):
        """将会话持久化到 JSON 文件"""
        if not self.storage_dir:
            return
        session = self.sessions.get(session_id)
        if not session:
            return
        path = self.storage_dir / f"{session_id}.json"
        with open(path, "w", encoding="utf-8") as f:
            json.dump(session.to_dict(), f, ensure_ascii=False, indent=2)

    def _load_sessions(self):
        """从磁盘加载所有会话"""
        if not self.storage_dir:
            return
        for path in self.storage_dir.glob("*.json"):
            try:
                with open(path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                session = ConversationSession.from_dict(data)
                self.sessions[session.session_id] = session
            except Exception as e:
                logger.warning(f"加载会话失败 {path}: {e}")

    def _evict_if_needed(self):
        """超出最大会话数时驱逐最旧的会话"""
        if len(self.sessions) >= self.max_sessions:
            oldest = min(self.sessions.values(), key=lambda s: s.updated_at)
            self.delete_session(oldest.session_id)
            logger.info(f"驱逐最旧会话: {oldest.session_id}")
