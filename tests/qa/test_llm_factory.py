"""LLM工厂测试"""

import pytest
from unittest.mock import Mock, MagicMock, patch

from config.settings import LLMSettings, LLMProviderConfig
from src.qa.llm_factory import (
    LLMFactory,
    get_all_available_models,
    get_model_display_name,
)


class TestLLMFactory:
    """LLMFactory测试"""

    @pytest.fixture
    def llm_settings(self):
        """创建测试用LLM配置"""
        return LLMSettings()

    def test_get_available_providers(self):
        """测试获取可用提供商"""
        providers = LLMFactory.get_available_providers()

        assert "openai" in providers
        assert "anthropic" in providers
        assert "ollama" in providers
        assert "dashscope" in providers
        assert "kimi" in providers
        assert "gemini" in providers
        assert "deepseek" in providers

    def test_is_registered(self):
        """测试检查提供商是否注册"""
        assert LLMFactory.is_registered("openai") is True
        assert LLMFactory.is_registered("ollama") is True
        assert LLMFactory.is_registered("unknown_provider") is False

    def test_create_unknown_provider(self, llm_settings):
        """测试创建未知提供商"""
        with pytest.raises(ValueError) as exc_info:
            LLMFactory.create("unknown_provider", "model", llm_settings)

        assert "未知的LLM提供商" in str(exc_info.value)

    def test_create_disabled_provider(self, llm_settings):
        """测试创建被禁用的提供商"""
        # 禁用openai
        llm_settings.openai.enabled = False

        with pytest.raises(ValueError) as exc_info:
            LLMFactory.create("openai", "gpt-4", llm_settings)

        assert "未启用" in str(exc_info.value)

    @patch("src.qa.llm_factory.Ollama")
    def test_create_ollama(self, mock_ollama_class, llm_settings):
        """测试创建Ollama实例"""
        mock_llm = MagicMock()
        mock_ollama_class.return_value = mock_llm

        with patch("llama_index.llms.ollama.Ollama", mock_ollama_class):
            result = LLMFactory.create("ollama", "qwen2.5:7b", llm_settings)

        mock_ollama_class.assert_called_once()
        call_kwargs = mock_ollama_class.call_args.kwargs
        assert call_kwargs["model"] == "qwen2.5:7b"
        assert "localhost:11434" in call_kwargs["base_url"]

    @patch("src.qa.llm_factory.OpenAI")
    def test_create_openai(self, mock_openai_class, llm_settings):
        """测试创建OpenAI实例"""
        mock_llm = MagicMock()
        mock_openai_class.return_value = mock_llm

        # 设置API密钥
        llm_settings.openai.api_key = "test-api-key"

        with patch("llama_index.llms.openai.OpenAI", mock_openai_class):
            result = LLMFactory.create("openai", "gpt-4", llm_settings)

        mock_openai_class.assert_called_once()
        call_kwargs = mock_openai_class.call_args.kwargs
        assert call_kwargs["model"] == "gpt-4"
        assert call_kwargs["api_key"] == "test-api-key"

    @patch("src.qa.llm_factory.OpenAI")
    def test_create_kimi(self, mock_openai_class, llm_settings):
        """测试创建Kimi实例（使用OpenAI兼容接口）"""
        mock_llm = MagicMock()
        mock_openai_class.return_value = mock_llm

        llm_settings.kimi.api_key = "test-kimi-key"

        with patch("llama_index.llms.openai.OpenAI", mock_openai_class):
            result = LLMFactory.create("kimi", "moonshot-v1-8k", llm_settings)

        mock_openai_class.assert_called_once()
        call_kwargs = mock_openai_class.call_args.kwargs
        assert call_kwargs["model"] == "moonshot-v1-8k"
        assert "moonshot" in call_kwargs["api_base"]

    @patch("src.qa.llm_factory.OpenAI")
    def test_create_deepseek(self, mock_openai_class, llm_settings):
        """测试创建DeepSeek实例（使用OpenAI兼容接口）"""
        mock_llm = MagicMock()
        mock_openai_class.return_value = mock_llm

        llm_settings.deepseek.api_key = "test-deepseek-key"

        with patch("llama_index.llms.openai.OpenAI", mock_openai_class):
            result = LLMFactory.create("deepseek", "deepseek-chat", llm_settings)

        mock_openai_class.assert_called_once()
        call_kwargs = mock_openai_class.call_args.kwargs
        assert call_kwargs["model"] == "deepseek-chat"
        assert "deepseek" in call_kwargs["api_base"]


class TestGetAllAvailableModels:
    """get_all_available_models测试"""

    def test_get_all_enabled_models(self):
        """测试获取所有启用的模型"""
        settings = LLMSettings()

        available = get_all_available_models(settings)

        assert "ollama" in available
        assert "openai" in available
        assert len(available["ollama"]) > 0
        assert len(available["openai"]) > 0

    def test_disabled_provider_not_included(self):
        """测试禁用的提供商不包含在结果中"""
        settings = LLMSettings()
        settings.anthropic.enabled = False

        available = get_all_available_models(settings)

        assert "anthropic" not in available

    def test_empty_models_not_included(self):
        """测试空模型列表的提供商不包含在结果中"""
        settings = LLMSettings()
        settings.gemini.available_models = []

        available = get_all_available_models(settings)

        assert "gemini" not in available


class TestGetModelDisplayName:
    """get_model_display_name测试"""

    def test_known_providers(self):
        """测试已知提供商的显示名"""
        assert get_model_display_name("openai", "gpt-4") == "OpenAI / gpt-4"
        assert get_model_display_name("anthropic", "claude-3") == "Anthropic / claude-3"
        assert get_model_display_name("ollama", "qwen2.5") == "Ollama / qwen2.5"
        assert get_model_display_name("dashscope", "qwen-turbo") == "通义千问 / qwen-turbo"
        assert get_model_display_name("kimi", "moonshot-v1") == "Kimi / moonshot-v1"
        assert get_model_display_name("gemini", "gemini-pro") == "Gemini / gemini-pro"
        assert get_model_display_name("deepseek", "deepseek-chat") == "DeepSeek / deepseek-chat"

    def test_unknown_provider(self):
        """测试未知提供商的显示名"""
        assert get_model_display_name("custom", "model") == "Custom / model"


class TestLLMProviderConfig:
    """LLMProviderConfig测试"""

    def test_default_values(self):
        """测试默认值"""
        config = LLMProviderConfig()

        assert config.enabled is True
        assert config.api_key == ""
        assert config.api_base == ""
        assert config.default_model == ""
        assert config.available_models == []

    def test_custom_values(self):
        """测试自定义值"""
        config = LLMProviderConfig(
            enabled=False,
            api_key="test-key",
            api_base="https://api.test.com",
            default_model="test-model",
            available_models=["model1", "model2"],
        )

        assert config.enabled is False
        assert config.api_key == "test-key"
        assert config.api_base == "https://api.test.com"
        assert config.default_model == "test-model"
        assert config.available_models == ["model1", "model2"]


class TestLLMSettings:
    """LLMSettings测试"""

    def test_default_provider_configs(self):
        """测试默认提供商配置"""
        settings = LLMSettings()

        # 检查所有提供商都有配置
        assert settings.openai is not None
        assert settings.anthropic is not None
        assert settings.ollama is not None
        assert settings.dashscope is not None
        assert settings.kimi is not None
        assert settings.gemini is not None
        assert settings.deepseek is not None

    def test_get_provider_config(self):
        """测试获取提供商配置"""
        settings = LLMSettings()

        config = settings.get_provider_config("openai")
        assert config.default_model == "gpt-3.5-turbo"

        config = settings.get_provider_config("ollama")
        assert config.default_model == "qwen2.5:7b"

    def test_get_unknown_provider_config(self):
        """测试获取未知提供商配置"""
        settings = LLMSettings()

        with pytest.raises(ValueError) as exc_info:
            settings.get_provider_config("unknown")

        assert "未知的提供商" in str(exc_info.value)

    def test_backward_compatibility(self):
        """测试向后兼容性属性"""
        settings = LLMSettings()

        # 测试provider属性
        assert settings.provider == settings.active_provider

        # 测试model_name属性
        assert settings.model_name == settings.active_model
