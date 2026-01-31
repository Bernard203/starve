"""MediaWiki爬虫测试"""

import pytest
from unittest.mock import Mock, MagicMock, patch
import responses

from src.crawler.base import DataSource
from src.crawler.mediawiki_crawler import (
    MediaWikiCrawler,
    WikiGGCrawler,
    FandomCrawler,
    HuijiCrawler,
)
from .fixtures.mock_data import (
    MOCK_WIKI_CATEGORY_RESPONSE,
    MOCK_WIKI_PAGE_RESPONSE,
)


class TestMediaWikiCrawler:
    """MediaWikiCrawler测试"""

    @pytest.fixture
    def crawler(self):
        """创建测试爬虫"""
        return MediaWikiCrawler(
            api_url='https://test.wiki.gg/api.php',
            base_url='https://test.wiki.gg',
            source=DataSource.WIKI_GG,
            categories=['物品', '食物'],
        )

    def test_init(self, crawler):
        """测试初始化"""
        assert crawler.api_url == 'https://test.wiki.gg/api.php'
        assert crawler.source == DataSource.WIKI_GG
        assert len(crawler.categories) == 2

    @responses.activate
    def test_get_category_members(self, crawler):
        """测试获取分类成员"""
        responses.add(
            responses.GET,
            'https://test.wiki.gg/api.php',
            json=MOCK_WIKI_CATEGORY_RESPONSE,
            status=200
        )

        pages = list(crawler.get_category_members('物品'))

        assert len(pages) == 3
        assert pages[0]['title'] == '肉丸'

    @responses.activate
    def test_get_page_content(self, crawler):
        """测试获取页面内容"""
        responses.add(
            responses.GET,
            'https://test.wiki.gg/api.php',
            json=MOCK_WIKI_PAGE_RESPONSE,
            status=200
        )

        page = crawler.get_page_content('1001', '肉丸')

        assert page is not None
        assert page.title == '肉丸'
        assert page.source == DataSource.WIKI_GG
        assert '烹饪锅' in page.content

    @responses.activate
    def test_get_page_content_with_categories(self, crawler):
        """测试页面内容包含分类"""
        responses.add(
            responses.GET,
            'https://test.wiki.gg/api.php',
            json=MOCK_WIKI_PAGE_RESPONSE,
            status=200
        )

        page = crawler.get_page_content('1001', '肉丸')

        assert '食物' in page.categories
        assert '烹饪锅食谱' in page.categories

    @responses.activate
    def test_crawl_by_categories(self, crawler):
        """测试按分类爬取"""
        # 模拟分类API
        responses.add(
            responses.GET,
            'https://test.wiki.gg/api.php',
            json=MOCK_WIKI_CATEGORY_RESPONSE,
            status=200
        )
        # 模拟页面API（多次调用）
        for _ in range(3):
            responses.add(
                responses.GET,
                'https://test.wiki.gg/api.php',
                json=MOCK_WIKI_PAGE_RESPONSE,
                status=200
            )

        pages = list(crawler.crawl(max_pages=2, categories=['物品']))

        assert len(pages) == 2


class TestWikiGGCrawler:
    """WikiGGCrawler测试"""

    def test_init(self):
        """测试初始化"""
        crawler = WikiGGCrawler()

        assert crawler.source == DataSource.WIKI_GG
        assert 'wiki.gg' in crawler.api_url
        assert len(crawler.categories) > 0

    def test_default_categories(self):
        """测试默认分类"""
        crawler = WikiGGCrawler()

        assert '物品' in crawler.categories
        assert '食物' in crawler.categories
        assert 'Boss' in crawler.categories


class TestFandomCrawler:
    """FandomCrawler测试"""

    def test_init(self):
        """测试初始化"""
        crawler = FandomCrawler()

        assert crawler.source == DataSource.FANDOM
        assert 'fandom.com' in crawler.api_url


class TestHuijiCrawler:
    """HuijiCrawler测试"""

    def test_init(self):
        """测试初始化"""
        crawler = HuijiCrawler()

        assert crawler.source == DataSource.HUIJI
        assert 'huijiwiki' in crawler.api_url
