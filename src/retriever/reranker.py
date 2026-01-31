"""重排序器 - 使用BGE Reranker"""

from typing import Optional

from config import settings
from src.utils.logger import logger
from .retriever import RetrievalResult


class Reranker:
    """重排序器：对检索结果进行精排"""

    def __init__(self):
        self.config = settings.retriever
        self.model = None

        if self.config.use_reranker:
            self._init_model()

    def _init_model(self):
        """初始化重排序模型"""
        try:
            from sentence_transformers import CrossEncoder

            device = settings.embedding.device
            if device == "auto":
                import torch
                device = "cuda" if torch.cuda.is_available() else "cpu"

            self.model = CrossEncoder(
                self.config.reranker_model,
                device=device,
            )
            logger.info(f"重排序模型加载完成: {self.config.reranker_model}")

        except Exception as e:
            logger.warning(f"重排序模型加载失败，将使用原始排序: {e}")
            self.model = None

    def rerank(
        self,
        query: str,
        results: list[RetrievalResult],
        top_k: Optional[int] = None,
    ) -> list[RetrievalResult]:
        """对检索结果进行重排序"""
        if not self.model or not results:
            return results

        if top_k is None:
            top_k = len(results)

        # 准备输入对
        pairs = [(query, r.content) for r in results]

        try:
            # 计算相关性分数
            scores = self.model.predict(pairs)

            # 更新分数并排序
            for result, score in zip(results, scores):
                result.score = float(score)

            # 按新分数排序
            reranked = sorted(results, key=lambda x: x.score, reverse=True)

            logger.debug(f"重排序完成，返回前 {top_k} 个结果")
            return reranked[:top_k]

        except Exception as e:
            logger.error(f"重排序失败: {e}")
            return results[:top_k]
