"""
饥荒RAG问答助手 - 配置管理模块

支持从环境变量和.env文件加载配置
"""

import os
from pathlib import Path
from typing import Literal

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


# 项目根目录
PROJECT_ROOT = Path(__file__).parent.parent
DATA_DIR = PROJECT_ROOT / "data"
RAW_DATA_DIR = DATA_DIR / "raw"
PROCESSED_DATA_DIR = DATA_DIR / "processed"
VECTOR_DB_DIR = DATA_DIR / "vectors"

# 确保目录存在
for dir_path in [RAW_DATA_DIR, PROCESSED_DATA_DIR, VECTOR_DB_DIR]:
    dir_path.mkdir(parents=True, exist_ok=True)


class CrawlerSettings(BaseSettings):
    """爬虫配置"""

    model_config = SettingsConfigDict(env_prefix="CRAWLER_")

    # Wiki URL配置
    wiki_base_url: str = "https://dontstarve.wiki.gg"
    wiki_api_url: str = "https://dontstarve.wiki.gg/zh/api.php"
    wiki_lang: str = "zh"

    # 爬取限制
    request_delay: float = Field(default=1.0, description="请求间隔(秒)")
    max_pages: int = Field(default=1000, description="最大爬取页数")
    timeout: int = Field(default=30, description="请求超时(秒)")
    max_retries: int = Field(default=3, description="最大重试次数")

    # User-Agent
    user_agent: str = "StarveRAG/1.0 (Educational Purpose)"

    # 需要爬取的主要分类
    categories: list[str] = [
        "物品", "食物", "生物", "角色", "合成",
        "烹饪锅食谱", "建筑", "工具", "武器", "护甲",
        "魔法", "科学", "生物群系", "季节", "Boss",
    ]

    # 需要排除的命名空间
    exclude_namespaces: list[str] = [
        "Template", "Category", "File", "User",
        "Talk", "Help", "MediaWiki",
    ]


class EmbeddingSettings(BaseSettings):
    """Embedding模型配置"""

    model_config = SettingsConfigDict(env_prefix="EMBEDDING_")

    # 模型选择
    model_name: str = Field(
        default="BAAI/bge-large-zh-v1.5",
        description="Embedding模型名称"
    )

    # 分块参数
    chunk_size: int = Field(default=512, description="文档分块大小")
    chunk_overlap: int = Field(default=100, description="分块重叠大小")

    # 设备配置
    device: str = Field(default="auto", description="计算设备: auto/cpu/cuda")


class LLMProviderConfig(BaseSettings):
    """单个LLM提供商配置"""

    enabled: bool = Field(default=True, description="是否启用")
    api_key: str = Field(default="", description="API密钥")
    api_base: str = Field(default="", description="API地址")
    default_model: str = Field(default="", description="默认模型")
    available_models: list[str] = Field(default_factory=list, description="可用模型列表")


class LLMSettings(BaseSettings):
    """LLM配置"""

    model_config = SettingsConfigDict(env_prefix="LLM_")

    # 当前激活的提供商和模型
    active_provider: str = Field(default="ollama", description="当前提供商")
    active_model: str = Field(default="qwen2.5:7b", description="当前模型")

    # 生成参数
    temperature: float = Field(default=0.7, description="生成温度")
    max_tokens: int = Field(default=2048, description="最大生成token数")

    # 各提供商配置
    openai: LLMProviderConfig = Field(
        default_factory=lambda: LLMProviderConfig(
            enabled=True,
            api_base="https://api.openai.com/v1",
            default_model="gpt-3.5-turbo",
            available_models=["gpt-4", "gpt-4-turbo", "gpt-3.5-turbo", "gpt-4o", "gpt-4o-mini"],
        )
    )

    anthropic: LLMProviderConfig = Field(
        default_factory=lambda: LLMProviderConfig(
            enabled=True,
            api_base="https://api.anthropic.com",
            default_model="claude-3-sonnet-20240229",
            available_models=["claude-3-opus-20240229", "claude-3-sonnet-20240229", "claude-3-haiku-20240307"],
        )
    )

    ollama: LLMProviderConfig = Field(
        default_factory=lambda: LLMProviderConfig(
            enabled=True,
            api_base="http://localhost:11434",
            default_model="qwen2.5:7b",
            available_models=["qwen2.5:7b", "qwen2.5:14b", "llama3:8b", "mistral:7b", "gemma2:9b"],
        )
    )

    dashscope: LLMProviderConfig = Field(
        default_factory=lambda: LLMProviderConfig(
            enabled=True,
            api_base="https://dashscope.aliyuncs.com/api/v1",
            default_model="qwen-turbo",
            available_models=["qwen-turbo", "qwen-plus", "qwen-max"],
        )
    )

    kimi: LLMProviderConfig = Field(
        default_factory=lambda: LLMProviderConfig(
            enabled=True,
            api_base="https://api.moonshot.cn/v1",
            default_model="moonshot-v1-8k",
            available_models=["moonshot-v1-8k", "moonshot-v1-32k", "moonshot-v1-128k"],
        )
    )

    gemini: LLMProviderConfig = Field(
        default_factory=lambda: LLMProviderConfig(
            enabled=True,
            api_base="https://generativelanguage.googleapis.com/v1",
            default_model="gemini-pro",
            available_models=["gemini-pro", "gemini-1.5-pro", "gemini-1.5-flash"],
        )
    )

    deepseek: LLMProviderConfig = Field(
        default_factory=lambda: LLMProviderConfig(
            enabled=True,
            api_base="https://api.deepseek.com/v1",
            default_model="deepseek-chat",
            available_models=["deepseek-chat", "deepseek-coder"],
        )
    )

    # 兼容旧配置（向后兼容）
    @property
    def provider(self) -> str:
        """兼容旧配置"""
        return self.active_provider

    @property
    def model_name(self) -> str:
        """兼容旧配置"""
        return self.active_model

    @property
    def api_key(self) -> str:
        """获取当前提供商的API密钥"""
        provider_config = getattr(self, self.active_provider, None)
        return provider_config.api_key if provider_config else ""

    @property
    def api_base(self) -> str:
        """获取当前提供商的API地址"""
        provider_config = getattr(self, self.active_provider, None)
        return provider_config.api_base if provider_config else ""

    def get_provider_config(self, provider: str) -> LLMProviderConfig:
        """获取指定提供商配置"""
        config = getattr(self, provider, None)
        if config is None:
            raise ValueError(f"未知的提供商: {provider}")
        return config


class RetrieverSettings(BaseSettings):
    """检索器配置"""

    model_config = SettingsConfigDict(env_prefix="RETRIEVER_")

    # 基本检索参数
    top_k: int = Field(default=5, description="返回的文档数量")
    similarity_threshold: float = Field(default=0.5, description="相似度阈值")

    # 混合检索权重
    vector_weight: float = Field(default=0.7, description="向量检索权重")
    bm25_weight: float = Field(default=0.3, description="BM25检索权重")

    # BM25配置
    use_bm25: bool = Field(default=True, description="是否启用BM25检索")

    # RRF融合配置
    rrf_k: int = Field(default=60, description="RRF融合参数k")

    # Reranker配置
    use_reranker: bool = Field(default=True, description="是否使用重排序")
    reranker_model: str = Field(
        default="BAAI/bge-reranker-base",
        description="重排序模型"
    )

    # 缓存配置
    use_cache: bool = Field(default=True, description="是否启用查询缓存")
    cache_max_size: int = Field(default=1000, description="缓存最大条目数")
    cache_ttl: int = Field(default=3600, description="缓存过期时间(秒)")

    # MMR多样性配置
    use_mmr: bool = Field(default=True, description="是否启用MMR多样性优化")
    mmr_lambda: float = Field(default=0.5, description="MMR多样性参数(0-1)")

    # 查询处理配置
    use_query_expansion: bool = Field(default=True, description="是否启用查询扩展")


class SessionSettings(BaseSettings):
    """会话管理配置"""

    model_config = SettingsConfigDict(env_prefix="SESSION_")

    storage_dir: str = Field(default="data/sessions", description="会话持久化目录")
    max_sessions: int = Field(default=100, description="最大会话数量")
    max_turns: int = Field(default=5, description="历史对话保留轮数")


class AppSettings(BaseSettings):
    """应用配置"""

    model_config = SettingsConfigDict(env_prefix="APP_")

    # 服务配置
    host: str = Field(default="0.0.0.0", description="服务主机")
    port: int = Field(default=8000, description="服务端口")
    debug: bool = Field(default=False, description="调试模式")

    # Discord配置
    discord_token: str = Field(default="", description="Discord Bot Token")
    discord_prefix: str = Field(default="!", description="命令前缀")


class Settings(BaseSettings):
    """全局配置"""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore"
    )

    # 子配置
    crawler: CrawlerSettings = Field(default_factory=CrawlerSettings)
    embedding: EmbeddingSettings = Field(default_factory=EmbeddingSettings)
    llm: LLMSettings = Field(default_factory=LLMSettings)
    retriever: RetrieverSettings = Field(default_factory=RetrieverSettings)
    session: SessionSettings = Field(default_factory=SessionSettings)
    app: AppSettings = Field(default_factory=AppSettings)

    # 路径配置
    project_root: Path = PROJECT_ROOT
    data_dir: Path = DATA_DIR
    raw_data_dir: Path = RAW_DATA_DIR
    processed_data_dir: Path = PROCESSED_DATA_DIR
    vector_db_dir: Path = VECTOR_DB_DIR


# 全局配置实例
settings = Settings()
