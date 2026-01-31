"""爬虫工厂 - 统一创建和管理爬虫实例"""

from typing import Dict, List, Optional, Type

from src.utils.logger import logger
from .base import BaseCrawler, DataSource, CrawlerConfig, DEFAULT_SOURCE_CONFIGS
from .mediawiki_crawler import WikiGGCrawler, FandomCrawler, HuijiCrawler
from .tieba_crawler import TiebaCrawler
from .steam_crawler import SteamCrawler
from .cleaners.base import BaseCleaner
from .cleaners.mediawiki_cleaner import MediaWikiCleaner
from .cleaners.tieba_cleaner import TiebaCleaner
from .cleaners.steam_cleaner import SteamCleaner


class CrawlerFactory:
    """爬虫工厂"""

    # 爬虫类映射
    _crawlers: Dict[DataSource, Type[BaseCrawler]] = {
        DataSource.WIKI_GG: WikiGGCrawler,
        DataSource.FANDOM: FandomCrawler,
        DataSource.HUIJI: HuijiCrawler,
        DataSource.TIEBA: TiebaCrawler,
        DataSource.STEAM: SteamCrawler,
    }

    @classmethod
    def create(
        cls,
        source: DataSource,
        config: Optional[Dict] = None
    ) -> BaseCrawler:
        """
        创建指定数据源的爬虫实例

        Args:
            source: 数据源类型
            config: 可选的配置覆盖

        Returns:
            爬虫实例

        Raises:
            ValueError: 不支持的数据源
        """
        crawler_class = cls._crawlers.get(source)
        if not crawler_class:
            raise ValueError(f"不支持的数据源: {source}")

        logger.info(f"创建爬虫: {source.value}")
        return crawler_class(config=config)

    @classmethod
    def create_all(
        cls,
        sources: Optional[List[DataSource]] = None,
        config: Optional[Dict] = None
    ) -> List[BaseCrawler]:
        """
        创建多个数据源的爬虫实例

        Args:
            sources: 数据源列表，None表示创建所有
            config: 可选的配置覆盖

        Returns:
            爬虫实例列表
        """
        if sources is None:
            sources = list(cls._crawlers.keys())

        return [cls.create(source, config) for source in sources]

    @classmethod
    def create_enabled(cls, config: Optional[Dict] = None) -> List[BaseCrawler]:
        """
        创建所有启用的爬虫实例

        Args:
            config: 可选的配置覆盖

        Returns:
            启用的爬虫实例列表
        """
        crawlers = []
        for source, source_config in DEFAULT_SOURCE_CONFIGS.items():
            if source_config.enabled:
                crawlers.append(cls.create(source, config))
        return crawlers

    @classmethod
    def get_available_sources(cls) -> List[DataSource]:
        """获取所有可用的数据源"""
        return list(cls._crawlers.keys())

    @classmethod
    def register(cls, source: DataSource, crawler_class: Type[BaseCrawler]):
        """
        注册新的爬虫类

        Args:
            source: 数据源类型
            crawler_class: 爬虫类
        """
        cls._crawlers[source] = crawler_class
        logger.info(f"注册爬虫: {source.value} -> {crawler_class.__name__}")


class CleanerFactory:
    """清洗器工厂"""

    # 清洗器类映射
    _cleaners: Dict[DataSource, Type[BaseCleaner]] = {
        DataSource.WIKI_GG: MediaWikiCleaner,
        DataSource.FANDOM: MediaWikiCleaner,
        DataSource.HUIJI: MediaWikiCleaner,
        DataSource.TIEBA: TiebaCleaner,
        DataSource.STEAM: SteamCleaner,
    }

    @classmethod
    def create(cls, source: DataSource) -> BaseCleaner:
        """
        创建指定数据源的清洗器实例

        Args:
            source: 数据源类型

        Returns:
            清洗器实例

        Raises:
            ValueError: 不支持的数据源
        """
        cleaner_class = cls._cleaners.get(source)
        if not cleaner_class:
            raise ValueError(f"不支持的数据源: {source}")

        return cleaner_class()

    @classmethod
    def register(cls, source: DataSource, cleaner_class: Type[BaseCleaner]):
        """
        注册新的清洗器类

        Args:
            source: 数据源类型
            cleaner_class: 清洗器类
        """
        cls._cleaners[source] = cleaner_class
        logger.info(f"注册清洗器: {source.value} -> {cleaner_class.__name__}")
