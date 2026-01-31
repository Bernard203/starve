"""MMR多样性优化

实现Maximum Marginal Relevance (MMR)算法，优化检索结果多样性
"""

from typing import Optional, Callable, TypeVar
from dataclasses import dataclass

from src.utils.logger import logger


T = TypeVar('T')


@dataclass
class MMRResult:
    """MMR选择结果"""
    item: any
    relevance_score: float      # 与查询的相关性分数
    diversity_penalty: float    # 多样性惩罚
    mmr_score: float            # 最终MMR分数


class MMRDiversifier:
    """最大边际相关性(MMR)多样性优化器

    MMR公式:
    MMR = λ * sim(d, q) - (1-λ) * max(sim(d, d_selected))

    其中:
    - λ (lambda): 平衡相关性和多样性的参数，λ=1时只考虑相关性
    - sim(d, q): 文档d与查询q的相似度
    - sim(d, d_selected): 文档d与已选文档的最大相似度
    """

    def __init__(self, lambda_param: float = 0.5):
        """初始化MMR优化器

        Args:
            lambda_param: 多样性参数，范围[0, 1]
                - 1.0: 完全基于相关性（无多样性）
                - 0.5: 平衡相关性和多样性
                - 0.0: 完全基于多样性（忽略相关性）
        """
        if not 0 <= lambda_param <= 1:
            raise ValueError("lambda_param必须在[0, 1]范围内")

        self.lambda_param = lambda_param

    def diversify(
        self,
        candidates: list[T],
        relevance_scores: list[float],
        similarity_matrix: Optional[list[list[float]]] = None,
        get_embedding: Optional[Callable[[T], list[float]]] = None,
        top_k: int = 5,
    ) -> list[MMRResult]:
        """MMR多样性选择

        Args:
            candidates: 候选文档列表
            relevance_scores: 文档相关性分数（与candidates顺序一致）
            similarity_matrix: 文档间相似度矩阵，如不提供则使用get_embedding计算
            get_embedding: 获取文档嵌入的函数
            top_k: 返回的文档数量

        Returns:
            MMR选择后的结果列表
        """
        if not candidates:
            return []

        if len(candidates) != len(relevance_scores):
            raise ValueError("candidates和relevance_scores长度必须一致")

        n = len(candidates)
        top_k = min(top_k, n)

        # 如果没有相似度矩阵，尝试计算
        if similarity_matrix is None:
            if get_embedding is not None:
                similarity_matrix = self._compute_similarity_matrix(candidates, get_embedding)
            else:
                # 无法计算多样性，直接按相关性排序
                logger.warning("MMR: 无法计算文档相似度，退化为相关性排序")
                return self._simple_select(candidates, relevance_scores, top_k)

        # MMR选择
        selected_indices: list[int] = []
        remaining_indices = set(range(n))
        results: list[MMRResult] = []

        for _ in range(top_k):
            best_idx = None
            best_mmr = float('-inf')
            best_diversity_penalty = 0.0

            for idx in remaining_indices:
                # 计算MMR分数
                relevance = relevance_scores[idx]

                # 计算与已选文档的最大相似度
                if selected_indices:
                    max_sim_to_selected = max(
                        similarity_matrix[idx][sel_idx]
                        for sel_idx in selected_indices
                    )
                else:
                    max_sim_to_selected = 0.0

                # MMR公式
                mmr_score = (
                    self.lambda_param * relevance -
                    (1 - self.lambda_param) * max_sim_to_selected
                )

                if mmr_score > best_mmr:
                    best_mmr = mmr_score
                    best_idx = idx
                    best_diversity_penalty = max_sim_to_selected

            if best_idx is None:
                break

            # 添加到结果
            results.append(MMRResult(
                item=candidates[best_idx],
                relevance_score=relevance_scores[best_idx],
                diversity_penalty=best_diversity_penalty,
                mmr_score=best_mmr,
            ))

            selected_indices.append(best_idx)
            remaining_indices.remove(best_idx)

        logger.debug(f"MMR选择完成: {n}个候选 -> {len(results)}个结果")

        return results

    def diversify_with_embeddings(
        self,
        candidates: list[T],
        relevance_scores: list[float],
        embeddings: list[list[float]],
        top_k: int = 5,
    ) -> list[MMRResult]:
        """使用预计算的嵌入进行MMR选择

        Args:
            candidates: 候选文档列表
            relevance_scores: 文档相关性分数
            embeddings: 文档嵌入列表
            top_k: 返回的文档数量

        Returns:
            MMR选择后的结果列表
        """
        # 计算相似度矩阵
        similarity_matrix = self._compute_similarity_from_embeddings(embeddings)

        return self.diversify(
            candidates=candidates,
            relevance_scores=relevance_scores,
            similarity_matrix=similarity_matrix,
            top_k=top_k,
        )

    def _compute_similarity_matrix(
        self,
        candidates: list[T],
        get_embedding: Callable[[T], list[float]],
    ) -> list[list[float]]:
        """计算文档间相似度矩阵"""
        embeddings = [get_embedding(c) for c in candidates]
        return self._compute_similarity_from_embeddings(embeddings)

    def _compute_similarity_from_embeddings(
        self,
        embeddings: list[list[float]],
    ) -> list[list[float]]:
        """从嵌入计算相似度矩阵"""
        n = len(embeddings)
        matrix = [[0.0] * n for _ in range(n)]

        for i in range(n):
            for j in range(i, n):
                if i == j:
                    matrix[i][j] = 1.0
                else:
                    sim = self._cosine_similarity(embeddings[i], embeddings[j])
                    matrix[i][j] = sim
                    matrix[j][i] = sim

        return matrix

    def _cosine_similarity(self, vec1: list[float], vec2: list[float]) -> float:
        """计算余弦相似度"""
        if len(vec1) != len(vec2) or len(vec1) == 0:
            return 0.0

        dot_product = sum(a * b for a, b in zip(vec1, vec2))
        norm1 = sum(a * a for a in vec1) ** 0.5
        norm2 = sum(b * b for b in vec2) ** 0.5

        if norm1 == 0 or norm2 == 0:
            return 0.0

        return dot_product / (norm1 * norm2)

    def _simple_select(
        self,
        candidates: list[T],
        relevance_scores: list[float],
        top_k: int,
    ) -> list[MMRResult]:
        """简单选择（按相关性排序）"""
        indexed = list(enumerate(relevance_scores))
        indexed.sort(key=lambda x: x[1], reverse=True)

        results = []
        for idx, score in indexed[:top_k]:
            results.append(MMRResult(
                item=candidates[idx],
                relevance_score=score,
                diversity_penalty=0.0,
                mmr_score=score,
            ))

        return results


class ContentBasedDiversifier:
    """基于内容的多样性优化

    通过比较文档内容避免重复
    """

    def __init__(self, similarity_threshold: float = 0.8):
        """初始化

        Args:
            similarity_threshold: 相似度阈值，超过此值视为重复
        """
        self.similarity_threshold = similarity_threshold

    def deduplicate(
        self,
        candidates: list[T],
        get_content: Callable[[T], str],
    ) -> list[T]:
        """去除重复文档

        Args:
            candidates: 候选文档列表
            get_content: 获取文档内容的函数

        Returns:
            去重后的文档列表
        """
        if not candidates:
            return []

        selected = [candidates[0]]
        selected_contents = [get_content(candidates[0])]

        for candidate in candidates[1:]:
            content = get_content(candidate)

            # 检查与已选文档的相似度
            is_duplicate = False
            for sel_content in selected_contents:
                sim = self._jaccard_similarity(content, sel_content)
                if sim >= self.similarity_threshold:
                    is_duplicate = True
                    break

            if not is_duplicate:
                selected.append(candidate)
                selected_contents.append(content)

        logger.debug(f"内容去重: {len(candidates)} -> {len(selected)}")

        return selected

    def _jaccard_similarity(self, text1: str, text2: str) -> float:
        """计算Jaccard相似度（基于字符n-gram）"""
        if not text1 or not text2:
            return 0.0

        # 使用3-gram
        ngrams1 = set(text1[i:i+3] for i in range(len(text1) - 2))
        ngrams2 = set(text2[i:i+3] for i in range(len(text2) - 2))

        if not ngrams1 or not ngrams2:
            return 0.0

        intersection = len(ngrams1 & ngrams2)
        union = len(ngrams1 | ngrams2)

        return intersection / union if union > 0 else 0.0
