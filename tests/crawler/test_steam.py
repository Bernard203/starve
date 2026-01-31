"""Steam爬虫测试"""

import pytest
from unittest.mock import Mock, MagicMock, patch
import responses

from src.crawler.steam_crawler import SteamCrawler
from src.crawler.base import DataSource, RawPage
from .fixtures.mock_data import (
    MOCK_STEAM_LIST_HTML,
    MOCK_STEAM_GUIDE_HTML,
)
from .fixtures.mock_responses import (
    MOCK_STEAM_EMPTY_LIST_HTML,
    MOCK_STEAM_GUIDE_NO_SECTIONS_HTML,
    MOCK_STEAM_GUIDE_EMPTY_HTML,
    MOCK_STEAM_GUIDE_WITH_TAGS_HTML,
    MOCK_STEAM_LIST_WITH_RATING_HTML,
)


class TestSteamCrawlerInit:
    """SteamCrawler初始化测试"""

    def test_init_default_config(self):
        """测试默认配置（DST app_id）"""
        crawler = SteamCrawler()

        assert crawler.source == DataSource.STEAM
        assert crawler.app_id == '322330'  # DST的app_id
        assert crawler.language == 'schinese'

    def test_init_language_cookie_set(self):
        """测试语言Cookie设置"""
        crawler = SteamCrawler()

        assert crawler.session.cookies.get('Steam_Language') == 'schinese'

    def test_init_headers_set_correctly(self):
        """测试请求头正确设置"""
        crawler = SteamCrawler()

        assert 'Accept-Language' in crawler.session.headers
        assert 'zh' in crawler.session.headers['Accept-Language']

    def test_source_is_steam(self):
        """测试数据源类型"""
        crawler = SteamCrawler()
        assert crawler.source == DataSource.STEAM


class TestSteamCrawlerUrl:
    """URL生成测试"""

    @pytest.fixture
    def crawler(self):
        return SteamCrawler()

    def test_get_guides_url_first_page(self, crawler):
        """测试指南列表URL"""
        url = crawler._get_guides_url(page=1)

        assert 'steamcommunity.com' in url
        assert '/app/322330/guides/' in url
        assert 'p=1' in url
        assert 'browsefilter=toprated' in url

    def test_get_guides_url_pagination(self, crawler):
        """测试分页URL"""
        url = crawler._get_guides_url(page=3)

        assert 'p=3' in url

    def test_get_guide_url(self, crawler):
        """测试指南详情URL"""
        url = crawler._get_guide_url('123456')

        assert 'steamcommunity.com' in url
        assert 'filedetails' in url
        assert 'id=123456' in url


class TestSteamCrawlerPageList:
    """指南列表获取测试"""

    @pytest.fixture
    def crawler(self):
        return SteamCrawler()

    @responses.activate
    def test_get_page_list_success(self, crawler):
        """测试成功获取指南列表"""
        responses.add(
            responses.GET,
            'https://steamcommunity.com/app/322330/guides/',
            body=MOCK_STEAM_LIST_HTML,
            status=200,
        )

        pages = list(crawler.get_page_list(max_list_pages=1))

        assert len(pages) == 2
        assert pages[0]['title'] == '饥荒新手完全指南'
        assert pages[1]['title'] == 'Boss攻略合集'

    @responses.activate
    def test_get_page_list_extracts_guide_id(self, crawler):
        """测试正确提取指南ID"""
        responses.add(
            responses.GET,
            'https://steamcommunity.com/app/322330/guides/',
            body=MOCK_STEAM_LIST_HTML,
            status=200,
        )

        pages = list(crawler.get_page_list(max_list_pages=1))

        assert pages[0]['id'] == '123456'
        assert pages[1]['id'] == '123457'

    @responses.activate
    def test_get_page_list_extracts_metadata(self, crawler):
        """测试提取标题、作者、评分"""
        responses.add(
            responses.GET,
            'https://steamcommunity.com/app/322330/guides/',
            body=MOCK_STEAM_LIST_WITH_RATING_HTML,
            status=200,
        )

        pages = list(crawler.get_page_list(max_list_pages=1))

        assert len(pages) == 1
        assert 'id' in pages[0]
        assert 'title' in pages[0]
        assert 'author' in pages[0]
        assert 'rating' in pages[0]
        assert pages[0]['author'] == 'TopAuthor'

    @responses.activate
    def test_get_page_list_empty_page(self, crawler):
        """测试空页面处理"""
        responses.add(
            responses.GET,
            'https://steamcommunity.com/app/322330/guides/',
            body=MOCK_STEAM_EMPTY_LIST_HTML,
            status=200,
        )

        pages = list(crawler.get_page_list(max_list_pages=1))

        assert len(pages) == 0

    @responses.activate
    def test_get_page_list_network_error(self, crawler):
        """测试网络错误处理"""
        responses.add(
            responses.GET,
            'https://steamcommunity.com/app/322330/guides/',
            body=Exception('Network Error'),
        )

        pages = list(crawler.get_page_list(max_list_pages=1))

        # 网络错误应该返回空列表
        assert len(pages) == 0


class TestSteamCrawlerPageContent:
    """指南内容获取测试"""

    @pytest.fixture
    def crawler(self):
        return SteamCrawler()

    @responses.activate
    def test_get_page_content_with_sections(self, crawler):
        """测试带章节的指南"""
        responses.add(
            responses.GET,
            'https://steamcommunity.com/sharedfiles/filedetails/',
            body=MOCK_STEAM_GUIDE_HTML,
            status=200,
        )

        result = crawler.get_page_content('123456', '饥荒新手完全指南')

        assert result is not None
        assert isinstance(result, RawPage)
        assert result.source == DataSource.STEAM
        assert '基础介绍' in result.content or '饥荒是一款生存游戏' in result.content
        assert '食物配方' in result.content or '肉丸' in result.content

    @responses.activate
    def test_get_page_content_no_sections(self, crawler):
        """测试无章节结构的指南"""
        responses.add(
            responses.GET,
            'https://steamcommunity.com/sharedfiles/filedetails/',
            body=MOCK_STEAM_GUIDE_NO_SECTIONS_HTML,
            status=200,
        )

        result = crawler.get_page_content('888888', '简单指南')

        assert result is not None
        # 应该回退到使用description
        assert '没有章节结构' in result.content

    @responses.activate
    def test_get_page_content_extracts_tags(self, crawler):
        """测试标签提取"""
        responses.add(
            responses.GET,
            'https://steamcommunity.com/sharedfiles/filedetails/',
            body=MOCK_STEAM_GUIDE_WITH_TAGS_HTML,
            status=200,
        )

        result = crawler.get_page_content('777777', '带标签的指南')

        assert result is not None
        assert len(result.categories) >= 1
        assert '攻略' in result.categories or 'Steam指南' in result.categories

    @responses.activate
    def test_get_page_content_empty_guide(self, crawler):
        """测试空内容指南"""
        responses.add(
            responses.GET,
            'https://steamcommunity.com/sharedfiles/filedetails/',
            body=MOCK_STEAM_GUIDE_EMPTY_HTML,
            status=200,
        )

        result = crawler.get_page_content('666666', '空内容指南')

        # 空内容应该返回None
        assert result is None

    @responses.activate
    def test_get_page_content_returns_raw_page(self, crawler):
        """测试返回正确的RawPage结构"""
        responses.add(
            responses.GET,
            'https://steamcommunity.com/sharedfiles/filedetails/',
            body=MOCK_STEAM_GUIDE_HTML,
            status=200,
        )

        result = crawler.get_page_content('123456', '测试')

        assert result.source == DataSource.STEAM
        assert result.source_id == '123456'
        assert 'steamcommunity.com' in result.url
        assert 'app_id' in result.extra

    @responses.activate
    def test_get_page_content_network_error(self, crawler):
        """测试网络错误返回None"""
        responses.add(
            responses.GET,
            'https://steamcommunity.com/sharedfiles/filedetails/',
            body=Exception('Connection Error'),
        )

        result = crawler.get_page_content('123456', '测试')

        assert result is None


class TestSteamCrawlerIntegration:
    """Steam爬虫集成测试"""

    @pytest.fixture
    def crawler(self):
        return SteamCrawler()

    @responses.activate
    def test_crawl_flow(self, crawler):
        """测试完整爬取流程"""
        # 模拟列表页
        responses.add(
            responses.GET,
            'https://steamcommunity.com/app/322330/guides/',
            body=MOCK_STEAM_LIST_HTML,
            status=200,
        )
        # 模拟指南详情页
        responses.add(
            responses.GET,
            'https://steamcommunity.com/sharedfiles/filedetails/',
            body=MOCK_STEAM_GUIDE_HTML,
            status=200,
        )
        responses.add(
            responses.GET,
            'https://steamcommunity.com/sharedfiles/filedetails/',
            body=MOCK_STEAM_GUIDE_HTML,
            status=200,
        )

        # 爬取
        pages = list(crawler.crawl(max_pages=2))

        assert len(pages) <= 2
        for page in pages:
            assert isinstance(page, RawPage)
            assert page.source == DataSource.STEAM

    def test_get_stats(self, crawler):
        """测试统计信息"""
        stats = crawler.get_stats()

        assert 'source' in stats
        assert stats['source'] == 'steam'
        assert 'crawled_count' in stats
        assert 'failed_count' in stats


class TestSteamCrawlerExtra:
    """Steam爬虫额外测试"""

    @pytest.fixture
    def crawler(self):
        return SteamCrawler()

    def test_extra_contains_app_id(self, crawler):
        """测试extra字段包含app_id"""
        with responses.RequestsMock() as rsps:
            rsps.add(
                responses.GET,
                'https://steamcommunity.com/sharedfiles/filedetails/',
                body=MOCK_STEAM_GUIDE_HTML,
                status=200,
            )

            result = crawler.get_page_content('123456', '测试')

            if result:
                assert result.extra.get('app_id') == '322330'

    def test_description_in_extra(self, crawler):
        """测试extra包含description"""
        with responses.RequestsMock() as rsps:
            rsps.add(
                responses.GET,
                'https://steamcommunity.com/sharedfiles/filedetails/',
                body=MOCK_STEAM_GUIDE_HTML,
                status=200,
            )

            result = crawler.get_page_content('123456', '测试')

            if result:
                assert 'description' in result.extra
