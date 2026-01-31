"""模型对比器测试"""

import pytest
from unittest.mock import Mock, MagicMock, patch
from dataclasses import dataclass

from src.qa.model_comparator import (
    ModelComparator,
    ModelResponse,
    ComparisonResult,
    ComparisonMetrics,
)


@dataclass
class MockQAResponse:
    """模拟QA响应"""
    answer: str
    sources: list
    confidence: float


class TestModelResponse:
    """ModelResponse测试"""

    def test_success_response(self):
        """测试成功响应"""
        response = ModelResponse(
            provider="openai",
            model="gpt-4",
            answer="这是回答",
            latency=1.5,
            token_count=100,
            sources=[{"title": "test"}],
        )

        assert response.success is True
        assert response.provider == "openai"
        assert response.model == "gpt-4"
        assert response.answer == "这是回答"
        assert response.latency == 1.5
        assert response.token_count == 100

    def test_error_response(self):
        """测试错误响应"""
        response = ModelResponse(
            provider="openai",
            model="gpt-4",
            error="连接超时",
        )

        assert response.success is False
        assert response.error == "连接超时"
        assert response.answer == ""


class TestComparisonMetrics:
    """ComparisonMetrics测试"""

    def test_default_values(self):
        """测试默认值"""
        metrics = ComparisonMetrics()

        assert metrics.fastest_provider == ""
        assert metrics.fastest_latency == 0.0
        assert metrics.longest_answer_provider == ""
        assert metrics.longest_answer_length == 0
        assert metrics.average_latency == 0.0
        assert metrics.success_count == 0
        assert metrics.total_count == 0


class TestComparisonResult:
    """ComparisonResult测试"""

    def test_to_dict(self):
        """测试转换为字典"""
        result = ComparisonResult(
            question="测试问题",
            results={
                "openai/gpt-4": ModelResponse(
                    provider="openai",
                    model="gpt-4",
                    answer="回答1",
                    latency=1.0,
                    token_count=50,
                ),
                "ollama/qwen": ModelResponse(
                    provider="ollama",
                    model="qwen",
                    answer="回答2",
                    latency=2.0,
                    token_count=60,
                ),
            },
            metrics=ComparisonMetrics(
                fastest_provider="openai/gpt-4",
                fastest_latency=1.0,
                success_count=2,
                total_count=2,
            ),
        )

        data = result.to_dict()

        assert data["question"] == "测试问题"
        assert "openai/gpt-4" in data["results"]
        assert data["results"]["openai/gpt-4"]["success"] is True
        assert data["metrics"]["fastest_provider"] == "openai/gpt-4"
        assert data["metrics"]["success_rate"] == "2/2"


class TestModelComparator:
    """ModelComparator测试"""

    @pytest.fixture
    def mock_qa_engine(self):
        """创建模拟QA引擎"""
        engine = MagicMock()
        engine.current_provider = "ollama"
        engine.current_model = "qwen2.5:7b"
        engine.get_available_llms.return_value = {
            "openai": ["gpt-4", "gpt-3.5-turbo"],
            "ollama": ["qwen2.5:7b", "llama3:8b"],
        }
        engine.ask.return_value = MockQAResponse(
            answer="测试回答内容",
            sources=[],
            confidence=0.8,
        )
        engine.switch_llm.return_value = {
            "status": "success",
            "provider": "openai",
            "model": "gpt-4",
            "display_name": "OpenAI / gpt-4",
        }
        return engine

    def test_init(self, mock_qa_engine):
        """测试初始化"""
        comparator = ModelComparator(mock_qa_engine)

        assert comparator.qa_engine == mock_qa_engine
        assert comparator.original_provider == "ollama"
        assert comparator.original_model == "qwen2.5:7b"

    def test_get_default_providers(self, mock_qa_engine):
        """测试获取默认提供商"""
        comparator = ModelComparator(mock_qa_engine)

        providers = comparator._get_default_providers()

        assert len(providers) <= 3
        assert all(isinstance(p, tuple) for p in providers)
        assert all(len(p) == 2 for p in providers)

    def test_estimate_tokens_chinese(self, mock_qa_engine):
        """测试中文token估算"""
        comparator = ModelComparator(mock_qa_engine)

        # 纯中文
        tokens = comparator._estimate_tokens("这是一段中文文本")
        assert tokens > 0

        # 空文本
        tokens = comparator._estimate_tokens("")
        assert tokens == 0

    def test_estimate_tokens_english(self, mock_qa_engine):
        """测试英文token估算"""
        comparator = ModelComparator(mock_qa_engine)

        tokens = comparator._estimate_tokens("This is an English text")
        assert tokens > 0

    def test_estimate_tokens_mixed(self, mock_qa_engine):
        """测试中英混合token估算"""
        comparator = ModelComparator(mock_qa_engine)

        tokens = comparator._estimate_tokens("这是mixed文本test")
        assert tokens > 0

    def test_calculate_metrics_empty(self, mock_qa_engine):
        """测试空结果的指标计算"""
        comparator = ModelComparator(mock_qa_engine)

        metrics = comparator._calculate_metrics({})

        assert metrics.total_count == 0
        assert metrics.success_count == 0

    def test_calculate_metrics_with_results(self, mock_qa_engine):
        """测试有结果的指标计算"""
        comparator = ModelComparator(mock_qa_engine)

        results = {
            "openai/gpt-4": ModelResponse(
                provider="openai",
                model="gpt-4",
                answer="短回答",
                latency=1.0,
                token_count=10,
            ),
            "ollama/qwen": ModelResponse(
                provider="ollama",
                model="qwen",
                answer="这是一个很长很长的回答" * 10,
                latency=2.0,
                token_count=50,
            ),
        }

        metrics = comparator._calculate_metrics(results)

        assert metrics.total_count == 2
        assert metrics.success_count == 2
        assert metrics.fastest_provider == "openai/gpt-4"
        assert metrics.fastest_latency == 1.0
        assert metrics.longest_answer_provider == "ollama/qwen"
        assert metrics.average_latency == 1.5

    def test_calculate_metrics_with_failures(self, mock_qa_engine):
        """测试包含失败结果的指标计算"""
        comparator = ModelComparator(mock_qa_engine)

        results = {
            "openai/gpt-4": ModelResponse(
                provider="openai",
                model="gpt-4",
                answer="回答",
                latency=1.0,
                token_count=10,
            ),
            "ollama/qwen": ModelResponse(
                provider="ollama",
                model="qwen",
                error="连接失败",
            ),
        }

        metrics = comparator._calculate_metrics(results)

        assert metrics.total_count == 2
        assert metrics.success_count == 1

    def test_compare(self, mock_qa_engine):
        """测试对比功能"""
        comparator = ModelComparator(mock_qa_engine)

        result = comparator.compare(
            "测试问题",
            providers=[("openai", "gpt-4"), ("ollama", "qwen")],
        )

        assert isinstance(result, ComparisonResult)
        assert result.question == "测试问题"
        assert len(result.results) == 2
        assert "openai/gpt-4" in result.results
        assert "ollama/qwen" in result.results

    def test_compare_restores_original(self, mock_qa_engine):
        """测试对比后恢复原始模型"""
        comparator = ModelComparator(mock_qa_engine)

        comparator.compare(
            "测试问题",
            providers=[("openai", "gpt-4")],
            restore_original=True,
        )

        # 验证最后一次切换是恢复原始模型
        last_call = mock_qa_engine.switch_llm.call_args_list[-1]
        assert last_call[0] == ("ollama", "qwen2.5:7b")

    def test_compare_no_restore(self, mock_qa_engine):
        """测试对比后不恢复原始模型"""
        comparator = ModelComparator(mock_qa_engine)

        # 记录初始调用次数
        initial_call_count = mock_qa_engine.switch_llm.call_count

        comparator.compare(
            "测试问题",
            providers=[("openai", "gpt-4")],
            restore_original=False,
        )

        # 应该只切换了一次（测试模型），没有恢复调用
        assert mock_qa_engine.switch_llm.call_count == initial_call_count + 1

    def test_generate_report(self, mock_qa_engine):
        """测试生成报告"""
        comparator = ModelComparator(mock_qa_engine)

        result = ComparisonResult(
            question="测试问题",
            results={
                "openai/gpt-4": ModelResponse(
                    provider="openai",
                    model="gpt-4",
                    answer="这是OpenAI的回答",
                    latency=1.0,
                    token_count=50,
                ),
            },
            metrics=ComparisonMetrics(
                fastest_provider="openai/gpt-4",
                fastest_latency=1.0,
                longest_answer_provider="openai/gpt-4",
                longest_answer_length=10,
                average_latency=1.0,
                success_count=1,
                total_count=1,
            ),
        )

        report = comparator.generate_report(result)

        assert "# 模型对比报告" in report
        assert "测试问题" in report
        assert "openai/gpt-4" in report
        assert "1.00s" in report

    def test_generate_report_with_error(self, mock_qa_engine):
        """测试生成包含错误的报告"""
        comparator = ModelComparator(mock_qa_engine)

        result = ComparisonResult(
            question="测试问题",
            results={
                "openai/gpt-4": ModelResponse(
                    provider="openai",
                    model="gpt-4",
                    error="API密钥无效",
                ),
            },
            metrics=ComparisonMetrics(
                success_count=0,
                total_count=1,
            ),
        )

        report = comparator.generate_report(result)

        assert "失败" in report
        assert "API密钥无效" in report


class TestModelComparatorEdgeCases:
    """ModelComparator边缘情况测试"""

    @pytest.fixture
    def mock_qa_engine(self):
        """创建模拟QA引擎"""
        engine = MagicMock()
        engine.current_provider = "ollama"
        engine.current_model = "qwen2.5:7b"
        engine.get_available_llms.return_value = {}
        return engine

    def test_get_default_providers_empty(self, mock_qa_engine):
        """测试没有可用提供商时的默认列表"""
        comparator = ModelComparator(mock_qa_engine)

        providers = comparator._get_default_providers()

        assert providers == []

    def test_compare_with_switch_error(self, mock_qa_engine):
        """测试切换模型失败时的处理"""
        mock_qa_engine.switch_llm.side_effect = ValueError("提供商不可用")

        comparator = ModelComparator(mock_qa_engine)

        result = comparator.compare(
            "测试问题",
            providers=[("unknown", "model")],
        )

        assert len(result.results) == 1
        response = result.results["unknown/model"]
        assert response.success is False
        assert "提供商不可用" in response.error
