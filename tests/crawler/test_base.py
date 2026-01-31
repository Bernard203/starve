"""爬虫基类测试"""

import pytest
from unittest.mock import Mock, MagicMock, patch
import json
import tempfile
from pathlib import Path

from src.crawler.base import (
    DataSource,
    RawPage,
    BaseCrawler,
    CrawlerConfig,
    DEFAULT_SOURCE_CONFIGS,
)


class TestDataSource:
    """DataSource枚举测试"""

    def test_all_sources_defined(self):
        """测试所有数据源都已定义"""
        expected = ['wiki_gg', 'fandom', 'huiji', 'tieba', 'steam']
        actual = [ds.value for ds in DataSource]
        assert set(actual) == set(expected)

    def test_source_from_string(self):
        """测试从字符串创建数据源"""
        assert DataSource('wiki_gg') == DataSource.WIKI_GG
        assert DataSource('fandom') == DataSource.FANDOM

    def test_invalid_source(self):
        """测试无效数据源"""
        with pytest.raises(ValueError):
            DataSource('invalid')


class TestRawPage:
    """RawPage数据类测试"""

    def test_create_raw_page(self):
        """测试创建RawPage"""
        page = RawPage(
            source=DataSource.WIKI_GG,
            source_id='123',
            title='测试页面',
            url='https://example.com/test',
            content='测试内容',
            html_content='<p>测试内容</p>',
        )

        assert page.source == DataSource.WIKI_GG
        assert page.source_id == '123'
        assert page.title == '测试页面'
        assert page.categories == []

    def test_to_dict(self):
        """测试转换为字典"""
        page = RawPage(
            source=DataSource.WIKI_GG,
            source_id='123',
            title='测试页面',
            url='https://example.com/test',
            content='测试内容',
            html_content='<p>测试内容</p>',
            categories=['分类1', '分类2'],
        )

        data = page.to_dict()

        assert data['source'] == 'wiki_gg'
        assert data['source_id'] == '123'
        assert data['categories'] == ['分类1', '分类2']

    def test_from_dict(self):
        """测试从字典创建"""
        data = {
            'source': 'wiki_gg',
            'source_id': '123',
            'title': '测试页面',
            'url': 'https://example.com/test',
            'content': '测试内容',
            'html_content': '<p>测试内容</p>',
            'categories': ['分类1'],
            'crawled_at': '2024-01-01T00:00:00',
            'raw_data': {},
            'extra': {},
        }

        page = RawPage.from_dict(data)

        assert page.source == DataSource.WIKI_GG
        assert page.title == '测试页面'


class TestCrawlerConfig:
    """CrawlerConfig测试"""

    def test_default_config(self):
        """测试默认配置"""
        config = CrawlerConfig()

        assert config.enabled is True
        assert config.max_pages == 1000
        assert config.request_delay == 1.0

    def test_custom_config(self):
        """测试自定义配置"""
        config = CrawlerConfig(
            enabled=False,
            max_pages=500,
            api_url='https://test.com/api',
        )

        assert config.enabled is False
        assert config.max_pages == 500
        assert config.api_url == 'https://test.com/api'


class TestDefaultSourceConfigs:
    """默认数据源配置测试"""

    def test_all_sources_configured(self):
        """测试所有数据源都有配置"""
        for source in DataSource:
            assert source in DEFAULT_SOURCE_CONFIGS

    def test_wiki_gg_config(self):
        """测试wiki.gg配置"""
        config = DEFAULT_SOURCE_CONFIGS[DataSource.WIKI_GG]

        assert config.enabled is True
        assert 'wiki.gg' in config.api_url
        assert len(config.categories) > 0

    def test_tieba_config(self):
        """测试贴吧配置"""
        config = DEFAULT_SOURCE_CONFIGS[DataSource.TIEBA]

        assert config.enabled is True
        assert 'tieba' in config.base_url
        assert config.extra.get('forum_name') == '饥荒'


class ConcreteTestCrawler(BaseCrawler):
    """用于测试的具体爬虫实现"""

    source = DataSource.WIKI_GG

    def get_page_list(self, **kwargs):
        yield {'id': '1', 'title': '页面1'}
        yield {'id': '2', 'title': '页面2'}

    def get_page_content(self, page_id, title):
        return RawPage(
            source=self.source,
            source_id=page_id,
            title=title,
            url=f'https://test.com/{page_id}',
            content=f'内容{page_id}',
            html_content=f'<p>内容{page_id}</p>',
        )


class TestBaseCrawler:
    """BaseCrawler测试"""

    def test_init(self):
        """测试初始化"""
        crawler = ConcreteTestCrawler()

        assert crawler.session is not None
        assert len(crawler.crawled_ids) == 0
        assert len(crawler.failed_ids) == 0

    def test_crawl(self):
        """测试爬取流程"""
        crawler = ConcreteTestCrawler()
        pages = list(crawler.crawl(max_pages=2))

        assert len(pages) == 2
        assert pages[0].title == '页面1'
        assert pages[1].title == '页面2'

    def test_crawl_max_pages(self):
        """测试最大页数限制"""
        crawler = ConcreteTestCrawler()
        pages = list(crawler.crawl(max_pages=1))

        assert len(pages) == 1

    def test_crawl_skip_duplicates(self):
        """测试跳过重复页面"""
        crawler = ConcreteTestCrawler()
        crawler.crawled_ids.add('1')

        pages = list(crawler.crawl(max_pages=2))

        assert len(pages) == 1
        assert pages[0].source_id == '2'

    def test_get_stats(self):
        """测试获取统计信息"""
        crawler = ConcreteTestCrawler()
        list(crawler.crawl(max_pages=2))

        stats = crawler.get_stats()

        assert stats['source'] == 'wiki_gg'
        assert stats['crawled_count'] == 2
        assert stats['failed_count'] == 0

    def test_save_and_load_results(self):
        """测试保存和加载结果"""
        with tempfile.TemporaryDirectory() as tmpdir:
            crawler = ConcreteTestCrawler()
            crawler.output_dir = Path(tmpdir)

            pages = list(crawler.crawl(max_pages=2))
            crawler.save_results(pages, 'test.json')

            loaded = crawler.load_results('test.json')

            assert len(loaded) == 2
            assert loaded[0].title == '页面1'

    def test_load_nonexistent_file(self):
        """测试加载不存在的文件"""
        with tempfile.TemporaryDirectory() as tmpdir:
            crawler = ConcreteTestCrawler()
            crawler.output_dir = Path(tmpdir)

            loaded = crawler.load_results('nonexistent.json')

            assert loaded == []
