"""LLM工厂模块

支持多种LLM提供商的动态创建和切换
"""

from typing import Callable, Any
from llama_index.core.llms import LLM

from config.settings import LLMProviderConfig, LLMSettings
from src.utils.logger import logger


class LLMFactory:
    """LLM实例工厂"""

    _creators: dict[str, Callable[[str, LLMProviderConfig, LLMSettings], LLM]] = {}

    @classmethod
    def register(cls, name: str, creator: Callable[[str, LLMProviderConfig, LLMSettings], LLM]):
        """注册LLM提供商创建函数

        Args:
            name: 提供商名称
            creator: 创建函数，接收(model, provider_config, llm_settings)
        """
        cls._creators[name] = creator
        logger.debug(f"注册LLM提供商: {name}")

    @classmethod
    def create(cls, provider: str, model: str, llm_settings: LLMSettings) -> LLM:
        """创建LLM实例

        Args:
            provider: 提供商名称
            model: 模型名称
            llm_settings: LLM配置

        Returns:
            LLM实例

        Raises:
            ValueError: 未知提供商或提供商未启用
        """
        if provider not in cls._creators:
            raise ValueError(f"未知的LLM提供商: {provider}，可用提供商: {list(cls._creators.keys())}")

        provider_config = llm_settings.get_provider_config(provider)
        if not provider_config.enabled:
            raise ValueError(f"提供商 {provider} 未启用")

        llm = cls._creators[provider](model, provider_config, llm_settings)
        logger.info(f"创建LLM实例: {provider}/{model}")
        return llm

    @classmethod
    def get_available_providers(cls) -> list[str]:
        """获取已注册的提供商列表"""
        return list(cls._creators.keys())

    @classmethod
    def is_registered(cls, provider: str) -> bool:
        """检查提供商是否已注册"""
        return provider in cls._creators


# ==================== 提供商创建函数 ====================

def _create_openai(model: str, config: LLMProviderConfig, llm_settings: LLMSettings) -> LLM:
    """创建OpenAI LLM实例"""
    from llama_index.llms.openai import OpenAI

    return OpenAI(
        model=model,
        api_key=config.api_key,
        api_base=config.api_base if config.api_base else None,
        temperature=llm_settings.temperature,
        max_tokens=llm_settings.max_tokens,
    )


def _create_anthropic(model: str, config: LLMProviderConfig, llm_settings: LLMSettings) -> LLM:
    """创建Anthropic LLM实例"""
    from llama_index.llms.anthropic import Anthropic

    return Anthropic(
        model=model,
        api_key=config.api_key,
        temperature=llm_settings.temperature,
        max_tokens=llm_settings.max_tokens,
    )


def _create_ollama(model: str, config: LLMProviderConfig, llm_settings: LLMSettings) -> LLM:
    """创建Ollama LLM实例"""
    from llama_index.llms.ollama import Ollama

    return Ollama(
        model=model,
        base_url=config.api_base,
        temperature=llm_settings.temperature,
        request_timeout=120,
    )


def _create_dashscope(model: str, config: LLMProviderConfig, llm_settings: LLMSettings) -> LLM:
    """创建DashScope (通义千问) LLM实例"""
    from llama_index.llms.dashscope import DashScope

    return DashScope(
        model_name=model,
        api_key=config.api_key,
        temperature=llm_settings.temperature,
        max_tokens=llm_settings.max_tokens,
    )


def _create_kimi(model: str, config: LLMProviderConfig, llm_settings: LLMSettings) -> LLM:
    """创建Kimi (Moonshot) LLM实例

    Kimi使用OpenAI兼容接口
    """
    from llama_index.llms.openai import OpenAI

    return OpenAI(
        model=model,
        api_key=config.api_key,
        api_base=config.api_base,
        temperature=llm_settings.temperature,
        max_tokens=llm_settings.max_tokens,
    )


def _create_gemini(model: str, config: LLMProviderConfig, llm_settings: LLMSettings) -> LLM:
    """创建Gemini LLM实例"""
    from llama_index.llms.gemini import Gemini

    return Gemini(
        model=model,
        api_key=config.api_key,
        temperature=llm_settings.temperature,
        max_tokens=llm_settings.max_tokens,
    )


def _create_deepseek(model: str, config: LLMProviderConfig, llm_settings: LLMSettings) -> LLM:
    """创建DeepSeek LLM实例

    DeepSeek使用OpenAI兼容接口
    """
    from llama_index.llms.openai import OpenAI

    return OpenAI(
        model=model,
        api_key=config.api_key,
        api_base=config.api_base,
        temperature=llm_settings.temperature,
        max_tokens=llm_settings.max_tokens,
    )


# ==================== 注册所有提供商 ====================

def _register_all_providers():
    """注册所有LLM提供商"""
    LLMFactory.register("openai", _create_openai)
    LLMFactory.register("anthropic", _create_anthropic)
    LLMFactory.register("ollama", _create_ollama)
    LLMFactory.register("dashscope", _create_dashscope)
    LLMFactory.register("kimi", _create_kimi)
    LLMFactory.register("gemini", _create_gemini)
    LLMFactory.register("deepseek", _create_deepseek)


# 模块加载时自动注册
_register_all_providers()


# ==================== 辅助函数 ====================

def get_all_available_models(llm_settings: LLMSettings) -> dict[str, list[str]]:
    """获取所有启用提供商的可用模型

    Args:
        llm_settings: LLM配置

    Returns:
        {provider: [models]} 字典
    """
    available = {}
    for provider in LLMFactory.get_available_providers():
        try:
            config = llm_settings.get_provider_config(provider)
            if config.enabled and config.available_models:
                available[provider] = config.available_models
        except ValueError:
            pass
    return available


def get_model_display_name(provider: str, model: str) -> str:
    """获取模型显示名称

    Args:
        provider: 提供商名称
        model: 模型名称

    Returns:
        显示名称，如 "OpenAI / gpt-4"
    """
    provider_names = {
        "openai": "OpenAI",
        "anthropic": "Anthropic",
        "ollama": "Ollama",
        "dashscope": "通义千问",
        "kimi": "Kimi",
        "gemini": "Gemini",
        "deepseek": "DeepSeek",
    }
    display_provider = provider_names.get(provider, provider.title())
    return f"{display_provider} / {model}"
