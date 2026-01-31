"""多路检索融合

实现Reciprocal Rank Fusion (RRF)等融合算法
"""

from typing import TypeVar, Callable, Optional
from dataclasses import dataclass
from collections import defaultdict

from src.utils.logger import logger


T = TypeVar('T')


@dataclass
class FusedResult:
    """融合结果"""
    item: any
    score: float
    ranks: dict[str, int]  # {source_name: rank}


class ReciprocalRankFusion:
    """Reciprocal Rank Fusion (RRF) 多路检索融合

    RRF公式: score(d) = sum(1 / (k + rank_i(d)))

    其中k是常数参数，rank_i(d)是文档d在第i个排序列表中的排名
    """

    def __init__(self, k: int = 60):
        """初始化RRF融合器

        Args:
            k: RRF参数，通常设为60。较大的k值会减少高排名文档的优势
        """
        self.k = k

    def fuse(
        self,
        result_lists: list[list[T]],
        get_id: Optional[Callable[[T], str]] = None,
        source_names: Optional[list[str]] = None,
    ) -> list[FusedResult]:
        """融合多路检索结果

        Args:
            result_lists: 多个排序后的结果列表
            get_id: 获取结果唯一标识的函数，默认使用id()
            source_names: 各路检索的名称，用于调试

        Returns:
            融合后的结果列表，按RRF分数降序排列
        """
        if not result_lists:
            return []

        # 过滤空列表
        result_lists = [lst for lst in result_lists if lst]
        if not result_lists:
            return []

        # 默认ID获取函数
        if get_id is None:
            get_id = lambda x: str(id(x))

        # 默认源名称
        if source_names is None:
            source_names = [f"source_{i}" for i in range(len(result_lists))]

        # 计算RRF分数
        scores: dict[str, float] = defaultdict(float)
        ranks: dict[str, dict[str, int]] = defaultdict(dict)
        items: dict[str, T] = {}

        for source_idx, results in enumerate(result_lists):
            source_name = source_names[source_idx] if source_idx < len(source_names) else f"source_{source_idx}"

            for rank, item in enumerate(results, start=1):
                item_id = get_id(item)

                # RRF公式
                rrf_score = 1.0 / (self.k + rank)
                scores[item_id] += rrf_score
                ranks[item_id][source_name] = rank

                # 保存原始项目
                if item_id not in items:
                    items[item_id] = item

        # 构建融合结果
        fused_results = []
        for item_id, score in scores.items():
            fused_results.append(FusedResult(
                item=items[item_id],
                score=score,
                ranks=ranks[item_id],
            ))

        # 按分数降序排列
        fused_results.sort(key=lambda x: x.score, reverse=True)

        logger.debug(f"RRF融合完成: {len(result_lists)}路 -> {len(fused_results)}个结果")

        return fused_results

    def fuse_with_weights(
        self,
        result_lists: list[list[T]],
        weights: list[float],
        get_id: Optional[Callable[[T], str]] = None,
    ) -> list[FusedResult]:
        """带权重的RRF融合

        Args:
            result_lists: 多个排序后的结果列表
            weights: 各路检索的权重
            get_id: 获取结果唯一标识的函数

        Returns:
            融合后的结果列表
        """
        if not result_lists:
            return []

        if len(weights) != len(result_lists):
            raise ValueError("权重数量必须与结果列表数量一致")

        # 默认ID获取函数
        if get_id is None:
            get_id = lambda x: str(id(x))

        # 计算加权RRF分数
        scores: dict[str, float] = defaultdict(float)
        ranks: dict[str, dict[str, int]] = defaultdict(dict)
        items: dict[str, T] = {}

        for source_idx, (results, weight) in enumerate(zip(result_lists, weights)):
            for rank, item in enumerate(results, start=1):
                item_id = get_id(item)

                # 加权RRF公式
                rrf_score = weight / (self.k + rank)
                scores[item_id] += rrf_score
                ranks[item_id][f"source_{source_idx}"] = rank

                if item_id not in items:
                    items[item_id] = item

        # 构建融合结果
        fused_results = []
        for item_id, score in scores.items():
            fused_results.append(FusedResult(
                item=items[item_id],
                score=score,
                ranks=ranks[item_id],
            ))

        fused_results.sort(key=lambda x: x.score, reverse=True)

        return fused_results


class LinearCombination:
    """线性加权融合

    score(d) = sum(w_i * norm_score_i(d))
    """

    def fuse(
        self,
        result_lists: list[list[tuple[T, float]]],
        weights: list[float],
        get_id: Optional[Callable[[T], str]] = None,
    ) -> list[FusedResult]:
        """线性加权融合

        Args:
            result_lists: 多个(item, score)元组列表
            weights: 各路检索的权重，需归一化
            get_id: 获取结果唯一标识的函数

        Returns:
            融合后的结果列表
        """
        if not result_lists:
            return []

        if len(weights) != len(result_lists):
            raise ValueError("权重数量必须与结果列表数量一致")

        # 归一化权重
        weight_sum = sum(weights)
        if weight_sum > 0:
            weights = [w / weight_sum for w in weights]

        # 默认ID获取函数
        if get_id is None:
            get_id = lambda x: str(id(x))

        # 计算加权分数
        scores: dict[str, float] = defaultdict(float)
        items: dict[str, T] = {}
        source_scores: dict[str, dict[str, float]] = defaultdict(dict)

        for source_idx, (results, weight) in enumerate(zip(result_lists, weights)):
            # 获取分数范围用于归一化
            if results:
                max_score = max(score for _, score in results)
                min_score = min(score for _, score in results)
                score_range = max_score - min_score if max_score != min_score else 1.0
            else:
                continue

            for item, score in results:
                item_id = get_id(item)

                # Min-Max归一化
                norm_score = (score - min_score) / score_range if score_range > 0 else 0.5

                # 加权求和
                scores[item_id] += weight * norm_score
                source_scores[item_id][f"source_{source_idx}"] = score

                if item_id not in items:
                    items[item_id] = item

        # 构建融合结果
        fused_results = []
        for item_id, score in scores.items():
            fused_results.append(FusedResult(
                item=items[item_id],
                score=score,
                ranks={},  # 线性融合不保留排名信息
            ))

        fused_results.sort(key=lambda x: x.score, reverse=True)

        return fused_results
