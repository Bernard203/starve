"""问答引擎"""

from pathlib import Path
from typing import Optional
from dataclasses import dataclass

from llama_index.core import VectorStoreIndex
from llama_index.core.llms import ChatMessage, MessageRole

from config import settings
from src.utils.logger import logger
from src.retriever import HybridRetriever, Reranker
from .prompts import SYSTEM_PROMPT, get_prompt_template
from .llm_factory import LLMFactory, get_all_available_models, get_model_display_name
from .session import SessionManager


@dataclass
class QAResponse:
    """问答响应"""
    answer: str
    sources: list[dict]
    confidence: float


class QAEngine:
    """RAG问答引擎"""

    def __init__(self, index: VectorStoreIndex, chroma_collection=None):
        self.llm_config = settings.llm
        self.index = index

        # 当前LLM状态
        self.current_provider = self.llm_config.active_provider
        self.current_model = self.llm_config.active_model

        # 初始化检索器
        self.retriever = HybridRetriever(index, chroma_collection=chroma_collection)
        self.reranker = Reranker()

        # 初始化LLM
        self._init_llm()

        # 会话管理器（替代原有的全局 chat_history）
        storage_path = Path(settings.project_root) / settings.session.storage_dir
        self.session_manager = SessionManager(
            storage_dir=storage_path,
            max_sessions=settings.session.max_sessions,
        )
        self.max_turns = settings.session.max_turns

        logger.info("问答引擎初始化完成")

    @property
    def config(self):
        """兼容旧代码"""
        return self.llm_config

    @property
    def chat_history(self) -> list[ChatMessage]:
        """向后兼容：返回默认会话的消息"""
        session = self.session_manager.get_session("default")
        return session.messages if session else []

    def _init_llm(self):
        """初始化LLM"""
        self.llm = LLMFactory.create(
            self.current_provider,
            self.current_model,
            self.llm_config
        )
        logger.info(f"LLM初始化完成: {self.current_provider}/{self.current_model}")

    def switch_llm(self, provider: str, model: str = None) -> dict:
        """运行时切换LLM

        Args:
            provider: 提供商名称
            model: 模型名称，为None时使用提供商默认模型

        Returns:
            切换结果字典

        Raises:
            ValueError: 提供商未启用或不存在
        """
        # 获取提供商配置
        provider_config = self.llm_config.get_provider_config(provider)

        if not provider_config.enabled:
            raise ValueError(f"提供商 {provider} 未启用")

        # 使用指定模型或默认模型
        target_model = model or provider_config.default_model

        # 验证模型是否可用
        if target_model not in provider_config.available_models:
            logger.warning(f"模型 {target_model} 不在可用列表中，但仍尝试使用")

        # 创建新的LLM实例
        try:
            self.llm = LLMFactory.create(provider, target_model, self.llm_config)
            self.current_provider = provider
            self.current_model = target_model

            result = {
                "status": "success",
                "provider": provider,
                "model": target_model,
                "display_name": get_model_display_name(provider, target_model),
            }
            logger.info(f"LLM切换成功: {provider}/{target_model}")
            return result

        except Exception as e:
            logger.error(f"LLM切换失败: {e}")
            raise ValueError(f"切换失败: {str(e)}")

    def get_current_llm_info(self) -> dict:
        """获取当前LLM信息

        Returns:
            包含provider, model, display_name的字典
        """
        return {
            "provider": self.current_provider,
            "model": self.current_model,
            "display_name": get_model_display_name(self.current_provider, self.current_model),
        }

    def get_available_llms(self) -> dict[str, list[str]]:
        """获取所有可用的LLM提供商和模型

        Returns:
            {provider: [models]} 字典
        """
        return get_all_available_models(self.llm_config)

    def ask(
        self,
        question: str,
        use_history: bool = True,
        filter_version: Optional[str] = None,
        session_id: str = "default",
    ) -> QAResponse:
        """回答用户问题"""
        logger.info(f"收到问题: {question} (session: {session_id})")

        # 1. 检索相关文档
        results = self.retriever.retrieve(
            question,
            top_k=settings.retriever.top_k,
            filter_version=filter_version,
        )

        # 2. 重排序
        if results and settings.retriever.use_reranker:
            results = self.reranker.rerank(question, results)

        # 3. 构建上下文
        context = self._build_context(results)

        # 4. 选择提示词模板
        prompt_template = get_prompt_template(question)

        # 5. 构建消息
        messages = self._build_messages(
            question,
            context,
            prompt_template,
            use_history,
            session_id,
        )

        # 6. 调用LLM
        try:
            response = self.llm.chat(messages)
            answer = response.message.content

            # 更新对话历史
            if use_history:
                self.session_manager.add_turn(session_id, question, answer)

            # 构建来源信息
            sources = [
                {
                    "title": r.source_title,
                    "url": r.source_url,
                    "score": r.score,
                }
                for r in results
            ]

            # 计算置信度（基于检索结果）
            confidence = self._calculate_confidence(results)

            return QAResponse(
                answer=answer,
                sources=sources,
                confidence=confidence,
            )

        except Exception as e:
            logger.error(f"LLM调用失败: {e}")
            return QAResponse(
                answer=f"抱歉，回答生成失败: {str(e)}",
                sources=[],
                confidence=0.0,
            )

    def _build_context(self, results: list) -> str:
        """构建上下文文本"""
        if not results:
            return "（知识库中未找到相关信息）"

        context_parts = []
        for i, result in enumerate(results, 1):
            source = f"[{result.source_title}]" if result.source_title else ""
            context_parts.append(f"【{i}】{source}\n{result.content}")

        return "\n\n".join(context_parts)

    def _build_messages(
        self,
        question: str,
        context: str,
        prompt_template: str,
        use_history: bool,
        session_id: str = "default",
    ) -> list[ChatMessage]:
        """构建对话消息"""
        messages = [
            ChatMessage(role=MessageRole.SYSTEM, content=SYSTEM_PROMPT)
        ]

        # 添加历史对话（限制长度）
        if use_history:
            recent_history = self.session_manager.get_history(
                session_id, self.max_turns
            )
            messages.extend(recent_history)

        # 添加当前问题
        user_prompt = prompt_template.format(
            context=context,
            question=question,
        )
        messages.append(
            ChatMessage(role=MessageRole.USER, content=user_prompt)
        )

        return messages

    def _calculate_confidence(self, results: list) -> float:
        """计算回答置信度"""
        if not results:
            return 0.3  # 无检索结果时的基础置信度

        # 基于最高相关性分数
        max_score = max(r.score for r in results)

        # 归一化到0-1
        confidence = min(max_score, 1.0)

        return confidence

    def clear_history(self, session_id: str = "default"):
        """清空对话历史"""
        self.session_manager.clear_session(session_id)
        logger.info(f"对话历史已清空: {session_id}")

    def get_history(self, session_id: str = "default") -> list[dict]:
        """获取对话历史"""
        return self.session_manager.get_history_dicts(session_id)
