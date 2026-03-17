"""数据采集模块

支持多数据源爬取：
- wiki.gg (dontstarve.wiki.gg)
- Fandom Wiki (dontstarve.fandom.com)
- 灰机Wiki (huijiwiki.com)
- 百度贴吧 (饥荒吧)
- Steam社区指南
"""

# 基础类和数据模型
from .base import (
    DataSource,
    RawPage,
    BaseCrawler,
    CrawlerConfig,
    DEFAULT_SOURCE_CONFIGS,
)

# 具体爬虫实现
from .mediawiki_crawler import (
    MediaWikiCrawler,
    WikiGGCrawler,
    FandomCrawler,
    HuijiCrawler,
)
from .tieba_crawler import TiebaCrawler
from .steam_crawler import SteamCrawler

# 工厂和流水线
from .factory import CrawlerFactory, CleanerFactory
from .pipeline import CrawlPipeline

# 清洗器
from .cleaners import (
    BaseCleaner,
    CleanedPage,
    MediaWikiCleaner,
    TiebaCleaner,
    SteamCleaner,
    DataNormalizer,
    QualityAssessor,
)

# 入口函数
from .main import main

__all__ = [
    # 基础
    'DataSource',
    'RawPage',
    'BaseCrawler',
    'CrawlerConfig',
    'DEFAULT_SOURCE_CONFIGS',

    # 爬虫
    'MediaWikiCrawler',
    'WikiGGCrawler',
    'FandomCrawler',
    'HuijiCrawler',
    'TiebaCrawler',
    'SteamCrawler',

    # 工厂和流水线
    'CrawlerFactory',
    'CleanerFactory',
    'CrawlPipeline',

    # 清洗器
    'BaseCleaner',
    'CleanedPage',
    'MediaWikiCleaner',
    'TiebaCleaner',
    'SteamCleaner',
    'DataNormalizer',
    'QualityAssessor',

    # 入口
    'main',
]
