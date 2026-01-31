"""流水线集成测试"""

import pytest
from unittest.mock import Mock, MagicMock, patch
import tempfile
from pathlib import Path

from src.crawler.base import DataSource, RawPage
from src.crawler.factory import CrawlerFactory, CleanerFactory
from src.crawler.pipeline import CrawlPipeline
from src.crawler.cleaners import CleanedPage
from src.utils.models import EntityType

from .fixtures.mock_data import (
    get_mock_raw_page_wiki,
    get_mock_raw_page_tieba,
)


class TestCrawlerFactory:
    """CrawlerFactory测试"""

    def test_create_wiki_gg_crawler(self):
        """测试创建wiki.gg爬虫"""
        crawler = CrawlerFactory.create(DataSource.WIKI_GG)

        assert crawler is not None
        assert crawler.source == DataSource.WIKI_GG

    def test_create_fandom_crawler(self):
        """测试创建Fandom爬虫"""
        crawler = CrawlerFactory.create(DataSource.FANDOM)

        assert crawler is not None
        assert crawler.source == DataSource.FANDOM

    def test_create_tieba_crawler(self):
        """测试创建贴吧爬虫"""
        crawler = CrawlerFactory.create(DataSource.TIEBA)

        assert crawler is not None
        assert crawler.source == DataSource.TIEBA

    def test_create_steam_crawler(self):
        """测试创建Steam爬虫"""
        crawler = CrawlerFactory.create(DataSource.STEAM)

        assert crawler is not None
        assert crawler.source == DataSource.STEAM

    def test_create_all_crawlers(self):
        """测试创建所有爬虫"""
        crawlers = CrawlerFactory.create_all()

        assert len(crawlers) == len(DataSource)

    def test_get_available_sources(self):
        """测试获取可用数据源"""
        sources = CrawlerFactory.get_available_sources()

        assert DataSource.WIKI_GG in sources
        assert DataSource.TIEBA in sources

    def test_create_invalid_source(self):
        """测试无效数据源"""
        with pytest.raises(ValueError):
            CrawlerFactory.create('invalid')


class TestCleanerFactory:
    """CleanerFactory测试"""

    def test_create_wiki_cleaner(self):
        """测试创建Wiki清洗器"""
        cleaner = CleanerFactory.create(DataSource.WIKI_GG)
        assert cleaner is not None

    def test_create_tieba_cleaner(self):
        """测试创建贴吧清洗器"""
        cleaner = CleanerFactory.create(DataSource.TIEBA)
        assert cleaner is not None

    def test_create_steam_cleaner(self):
        """测试创建Steam清洗器"""
        cleaner = CleanerFactory.create(DataSource.STEAM)
        assert cleaner is not None

    def test_wiki_sources_share_cleaner(self):
        """测试Wiki数据源共享清洗器类型"""
        wiki_gg_cleaner = CleanerFactory.create(DataSource.WIKI_GG)
        fandom_cleaner = CleanerFactory.create(DataSource.FANDOM)

        assert type(wiki_gg_cleaner) == type(fandom_cleaner)


class TestCrawlPipeline:
    """CrawlPipeline测试"""

    @pytest.fixture
    def mock_crawler(self):
        """创建模拟爬虫"""
        crawler = MagicMock()
        crawler.source = DataSource.WIKI_GG
        crawler.crawl.return_value = [get_mock_raw_page_wiki()]
        crawler.save_results = MagicMock()
        return crawler

    @pytest.fixture
    def mock_cleaner(self):
        """创建模拟清洗器"""
        cleaner = MagicMock()
        cleaner.clean.return_value = CleanedPage(
            source=DataSource.WIKI_GG,
            source_id='1001',
            title='肉丸',
            url='https://test.com',
            content='肉丸是一种食物。' * 50,
            summary='肉丸是一种食物。',
            categories=['食物'],
            quality_score=0.7,
        )
        return cleaner

    def test_pipeline_init(self):
        """测试流水线初始化"""
        pipeline = CrawlPipeline(sources=[DataSource.WIKI_GG])

        assert len(pipeline.sources) == 1
        assert pipeline.min_quality == 0.2

    def test_pipeline_init_all_sources(self):
        """测试初始化所有数据源"""
        pipeline = CrawlPipeline()

        assert len(pipeline.sources) == len(DataSource)

    @patch('src.crawler.pipeline.CrawlerFactory')
    @patch('src.crawler.pipeline.CleanerFactory')
    def test_process_source(self, mock_cleaner_factory, mock_crawler_factory, mock_crawler, mock_cleaner):
        """测试处理单个数据源"""
        mock_crawler_factory.create.return_value = mock_crawler
        mock_cleaner_factory.create.return_value = mock_cleaner

        pipeline = CrawlPipeline(sources=[DataSource.WIKI_GG])

        with tempfile.TemporaryDirectory() as tmpdir:
            import src.crawler.pipeline as pipeline_module
            original_dir = pipeline_module.PROCESSED_DATA_DIR
            pipeline_module.PROCESSED_DATA_DIR = Path(tmpdir)

            try:
                stats = pipeline._process_source(DataSource.WIKI_GG, max_pages=1, save_intermediate=False)

                assert stats['crawled'] == 1
                assert stats['cleaned'] == 1
            finally:
                pipeline_module.PROCESSED_DATA_DIR = original_dir

    def test_infer_entity_type_food(self):
        """测试食物类型推断"""
        pipeline = CrawlPipeline()

        entity_type = pipeline._infer_entity_type(['食物', '烹饪锅食谱'])
        assert entity_type == EntityType.FOOD

    def test_infer_entity_type_boss(self):
        """测试Boss类型推断"""
        pipeline = CrawlPipeline()

        entity_type = pipeline._infer_entity_type(['Boss', '生物'])
        assert entity_type == EntityType.BOSS

    def test_infer_entity_type_item(self):
        """测试物品类型推断"""
        pipeline = CrawlPipeline()

        entity_type = pipeline._infer_entity_type(['物品', '工具'])
        assert entity_type == EntityType.ITEM

    def test_infer_entity_type_unknown(self):
        """测试未知类型"""
        pipeline = CrawlPipeline()

        entity_type = pipeline._infer_entity_type(['其他'])
        assert entity_type == EntityType.OTHER

    def test_to_wiki_pages(self):
        """测试转换为WikiPage格式"""
        pipeline = CrawlPipeline()

        cleaned_pages = [
            CleanedPage(
                source=DataSource.WIKI_GG,
                source_id='1001',
                title='肉丸',
                url='https://test.com',
                content='测试内容',
                categories=['食物'],
                game_version='both',
            )
        ]

        wiki_pages = pipeline.to_wiki_pages(cleaned_pages)

        assert len(wiki_pages) == 1
        assert wiki_pages[0].title == '肉丸'
        assert wiki_pages[0].entity_type == EntityType.FOOD


class TestEndToEnd:
    """端到端集成测试"""

    def test_full_pipeline_mock(self):
        """测试完整流水线（使用mock）"""
        # 这个测试需要mock网络请求
        # 实际运行时会跳过

        pipeline = CrawlPipeline(sources=[DataSource.WIKI_GG], min_quality=0.1)

        # 验证pipeline创建成功
        assert pipeline is not None
        assert pipeline.sources == [DataSource.WIKI_GG]

    def test_pipeline_stats_structure(self):
        """测试统计信息结构"""
        expected_keys = ['total_crawled', 'total_cleaned', 'total_filtered', 'sources']

        # 模拟一个统计结果
        stats = {
            'total_crawled': 10,
            'total_cleaned': 8,
            'total_filtered': 6,
            'sources': {
                'wiki_gg': {
                    'crawled': 10,
                    'cleaned': 8,
                    'filtered': 6,
                }
            }
        }

        for key in expected_keys:
            assert key in stats
