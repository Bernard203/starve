"""模型性能对比模块

支持多模型回答对比和性能指标分析
"""

import time
from typing import Optional, TYPE_CHECKING
from dataclasses import dataclass, field

from src.utils.logger import logger

if TYPE_CHECKING:
    from .qa_engine import QAEngine


@dataclass
class ModelResponse:
    """单个模型的响应"""
    provider: str
    model: str
    answer: str = ""
    latency: float = 0.0  # 响应延迟(秒)
    token_count: int = 0  # 输出token数(估算)
    sources: list[dict] = field(default_factory=list)
    error: Optional[str] = None

    @property
    def success(self) -> bool:
        """是否成功"""
        return self.error is None


@dataclass
class ComparisonMetrics:
    """对比指标"""
    fastest_provider: str = ""
    fastest_latency: float = 0.0
    longest_answer_provider: str = ""
    longest_answer_length: int = 0
    average_latency: float = 0.0
    success_count: int = 0
    total_count: int = 0


@dataclass
class ComparisonResult:
    """对比结果"""
    question: str
    results: dict[str, ModelResponse]  # "provider/model" -> response
    metrics: ComparisonMetrics = field(default_factory=ComparisonMetrics)
    timestamp: float = field(default_factory=time.time)

    def to_dict(self) -> dict:
        """转换为字典"""
        return {
            "question": self.question,
            "results": {
                key: {
                    "provider": r.provider,
                    "model": r.model,
                    "answer": r.answer,
                    "latency": round(r.latency, 3),
                    "token_count": r.token_count,
                    "success": r.success,
                    "error": r.error,
                }
                for key, r in self.results.items()
            },
            "metrics": {
                "fastest_provider": self.metrics.fastest_provider,
                "fastest_latency": round(self.metrics.fastest_latency, 3),
                "longest_answer_provider": self.metrics.longest_answer_provider,
                "longest_answer_length": self.metrics.longest_answer_length,
                "average_latency": round(self.metrics.average_latency, 3),
                "success_rate": f"{self.metrics.success_count}/{self.metrics.total_count}",
            },
            "timestamp": self.timestamp,
        }


class ModelComparator:
    """模型性能对比器"""

    def __init__(self, qa_engine: "QAEngine"):
        """初始化对比器

        Args:
            qa_engine: QA引擎实例
        """
        self.qa_engine = qa_engine
        self.original_provider = qa_engine.current_provider
        self.original_model = qa_engine.current_model

    def compare(
        self,
        question: str,
        providers: Optional[list[tuple[str, str]]] = None,
        restore_original: bool = True,
    ) -> ComparisonResult:
        """对比多个模型的回答

        Args:
            question: 问题
            providers: 要对比的模型列表 [(provider, model), ...]，为None时使用默认列表
            restore_original: 是否在对比后恢复原始模型

        Returns:
            对比结果
        """
        if providers is None:
            providers = self._get_default_providers()

        results: dict[str, ModelResponse] = {}

        for provider, model in providers:
            key = f"{provider}/{model}"
            response = self._test_single_model(question, provider, model)
            results[key] = response

        # 计算指标
        metrics = self._calculate_metrics(results)

        # 恢复原始模型
        if restore_original:
            try:
                self.qa_engine.switch_llm(self.original_provider, self.original_model)
            except Exception as e:
                logger.warning(f"恢复原始模型失败: {e}")

        return ComparisonResult(
            question=question,
            results=results,
            metrics=metrics,
        )

    async def compare_async(
        self,
        question: str,
        providers: Optional[list[tuple[str, str]]] = None,
        restore_original: bool = True,
    ) -> ComparisonResult:
        """异步对比多个模型（并行执行）

        注意：由于QAEngine是单例模式，实际上仍是串行切换模型

        Args:
            question: 问题
            providers: 要对比的模型列表
            restore_original: 是否恢复原始模型

        Returns:
            对比结果
        """
        # 由于LLM切换不是线程安全的，这里使用同步方式
        # 未来可以考虑为每个提供商创建独立的QAEngine实例
        return self.compare(question, providers, restore_original)

    def _test_single_model(
        self,
        question: str,
        provider: str,
        model: str,
    ) -> ModelResponse:
        """测试单个模型

        Args:
            question: 问题
            provider: 提供商
            model: 模型名称

        Returns:
            模型响应
        """
        try:
            # 切换模型
            self.qa_engine.switch_llm(provider, model)

            # 计时并获取回答
            start_time = time.time()
            response = self.qa_engine.ask(question, use_history=False)
            latency = time.time() - start_time

            # 估算token数（简单按字符数估算）
            token_count = self._estimate_tokens(response.answer)

            return ModelResponse(
                provider=provider,
                model=model,
                answer=response.answer,
                latency=latency,
                token_count=token_count,
                sources=response.sources,
            )

        except Exception as e:
            logger.error(f"模型 {provider}/{model} 测试失败: {e}")
            return ModelResponse(
                provider=provider,
                model=model,
                error=str(e),
            )

    def _get_default_providers(self) -> list[tuple[str, str]]:
        """获取默认对比模型列表

        Returns:
            [(provider, model), ...]
        """
        available = self.qa_engine.get_available_llms()
        providers = []

        for provider, models in available.items():
            if models:
                # 每个提供商取第一个（默认）模型
                providers.append((provider, models[0]))

        return providers[:3]  # 最多3个，避免太慢

    def _calculate_metrics(self, results: dict[str, ModelResponse]) -> ComparisonMetrics:
        """计算对比指标

        Args:
            results: 模型响应字典

        Returns:
            对比指标
        """
        metrics = ComparisonMetrics(total_count=len(results))

        successful = [(k, r) for k, r in results.items() if r.success]
        metrics.success_count = len(successful)

        if not successful:
            return metrics

        # 最快响应
        fastest_key, fastest_response = min(successful, key=lambda x: x[1].latency)
        metrics.fastest_provider = fastest_key
        metrics.fastest_latency = fastest_response.latency

        # 最长回答
        longest_key, longest_response = max(successful, key=lambda x: len(x[1].answer))
        metrics.longest_answer_provider = longest_key
        metrics.longest_answer_length = len(longest_response.answer)

        # 平均延迟
        total_latency = sum(r.latency for _, r in successful)
        metrics.average_latency = total_latency / len(successful)

        return metrics

    def _estimate_tokens(self, text: str) -> int:
        """估算token数

        简单估算：中文约1.5字符/token，英文约4字符/token

        Args:
            text: 文本

        Returns:
            估算的token数
        """
        if not text:
            return 0

        # 统计中英文字符
        chinese_count = sum(1 for c in text if '\u4e00' <= c <= '\u9fff')
        other_count = len(text) - chinese_count

        # 估算
        estimated = chinese_count / 1.5 + other_count / 4
        return int(estimated)

    def generate_report(self, result: ComparisonResult) -> str:
        """生成对比报告

        Args:
            result: 对比结果

        Returns:
            Markdown格式的报告
        """
        lines = [
            f"# 模型对比报告",
            f"",
            f"**问题**: {result.question}",
            f"",
            f"## 汇总指标",
            f"",
            f"- 成功率: {result.metrics.success_count}/{result.metrics.total_count}",
            f"- 最快响应: {result.metrics.fastest_provider} ({result.metrics.fastest_latency:.2f}s)",
            f"- 最长回答: {result.metrics.longest_answer_provider} ({result.metrics.longest_answer_length}字)",
            f"- 平均延迟: {result.metrics.average_latency:.2f}s",
            f"",
            f"## 详细结果",
            f"",
        ]

        for key, response in result.results.items():
            lines.append(f"### {key}")
            lines.append(f"")

            if response.success:
                lines.append(f"- 延迟: {response.latency:.2f}s")
                lines.append(f"- Token数: ~{response.token_count}")
                lines.append(f"- 回答长度: {len(response.answer)}字")
                lines.append(f"")
                lines.append(f"**回答**:")
                lines.append(f"")
                lines.append(f"> {response.answer[:500]}{'...' if len(response.answer) > 500 else ''}")
            else:
                lines.append(f"- 状态: 失败")
                lines.append(f"- 错误: {response.error}")

            lines.append(f"")

        return "\n".join(lines)
