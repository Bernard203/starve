"""贴吧爬虫测试"""

import pytest
from unittest.mock import Mock, MagicMock, patch
from urllib.parse import quote
import responses

from src.crawler.tieba_crawler import TiebaCrawler
from src.crawler.base import DataSource, RawPage
from .fixtures.mock_data import (
    MOCK_TIEBA_LIST_HTML,
    MOCK_TIEBA_POST_HTML,
)
from .fixtures.mock_responses import (
    MOCK_TIEBA_EMPTY_LIST_HTML,
    MOCK_TIEBA_MALFORMED_HTML,
    MOCK_TIEBA_POST_MULTI_PAGE_HTML_PAGE1,
    MOCK_TIEBA_POST_MULTI_PAGE_HTML_PAGE2,
    MOCK_TIEBA_POST_EMPTY_HTML,
    MOCK_TIEBA_POST_LZ_ONLY_HTML,
)


class TestTiebaCrawlerInit:
    """TiebaCrawler初始化测试"""

    def test_init_default_config(self):
        """测试默认配置初始化"""
        crawler = TiebaCrawler()

        assert crawler.source == DataSource.TIEBA
        assert crawler.forum_name == '饥荒'
        assert crawler.only_good is True
        assert 'tieba.baidu.com' in crawler.base_url

    def test_init_headers_set_correctly(self):
        """测试请求头正确设置"""
        crawler = TiebaCrawler()

        assert 'Referer' in crawler.session.headers
        assert '饥荒' in crawler.session.headers['Referer'] or \
               quote('饥荒') in crawler.session.headers['Referer']

    def test_source_is_tieba(self):
        """测试数据源类型"""
        crawler = TiebaCrawler()
        assert crawler.source == DataSource.TIEBA


class TestTiebaCrawlerUrl:
    """URL生成测试"""

    @pytest.fixture
    def crawler(self):
        return TiebaCrawler()

    def test_get_forum_url_first_page(self, crawler):
        """测试首页URL生成"""
        url = crawler._get_forum_url(page=0)

        assert 'tieba.baidu.com' in url
        assert 'kw=' in url
        assert 'tab=good' in url  # 精华帖

    def test_get_forum_url_with_pagination(self, crawler):
        """测试分页URL生成"""
        url = crawler._get_forum_url(page=2)

        assert 'pn=100' in url  # page * 50 = 2 * 50 = 100

    def test_get_forum_url_page_zero_no_pn(self, crawler):
        """测试第0页不含pn参数"""
        url = crawler._get_forum_url(page=0)

        assert 'pn=' not in url

    def test_get_thread_url(self, crawler):
        """测试帖子URL生成"""
        url = crawler._get_thread_url('12345')

        assert url == 'https://tieba.baidu.com/p/12345'


class TestTiebaCrawlerPageList:
    """帖子列表获取测试"""

    @pytest.fixture
    def crawler(self):
        return TiebaCrawler()

    @responses.activate
    def test_get_page_list_success(self, crawler):
        """测试成功获取帖子列表"""
        responses.add(
            responses.GET,
            'https://tieba.baidu.com/f',
            body=MOCK_TIEBA_LIST_HTML,
            status=200,
        )

        pages = list(crawler.get_page_list(max_list_pages=1))

        assert len(pages) == 2
        assert pages[0]['id'] == '12345'
        assert pages[0]['title'] == '新手攻略：肉丸配方详解'

    @responses.activate
    def test_get_page_list_extracts_all_fields(self, crawler):
        """测试提取所有字段"""
        responses.add(
            responses.GET,
            'https://tieba.baidu.com/f',
            body=MOCK_TIEBA_LIST_HTML,
            status=200,
        )

        pages = list(crawler.get_page_list(max_list_pages=1))

        assert 'id' in pages[0]
        assert 'title' in pages[0]
        assert 'author' in pages[0]
        assert 'reply_count' in pages[0]
        assert pages[0]['author'] == '作者A'
        assert pages[0]['reply_count'] == '100'

    @responses.activate
    def test_get_page_list_empty_page(self, crawler):
        """测试空页面处理"""
        responses.add(
            responses.GET,
            'https://tieba.baidu.com/f',
            body=MOCK_TIEBA_EMPTY_LIST_HTML,
            status=200,
        )

        pages = list(crawler.get_page_list(max_list_pages=1))

        assert len(pages) == 0

    @responses.activate
    def test_get_page_list_handles_missing_elements(self, crawler):
        """测试处理缺失元素"""
        responses.add(
            responses.GET,
            'https://tieba.baidu.com/f',
            body=MOCK_TIEBA_MALFORMED_HTML,
            status=200,
        )

        pages = list(crawler.get_page_list(max_list_pages=1))

        # 应该跳过畸形数据，只返回有效的帖子
        # 第一个缺少data-tid，第二个data-tid为空，第三个缺少标题
        # 都应该被跳过或部分处理
        for page in pages:
            assert page.get('id')  # 必须有ID

    @responses.activate
    def test_get_page_list_network_error(self, crawler):
        """测试网络错误处理"""
        responses.add(
            responses.GET,
            'https://tieba.baidu.com/f',
            body=Exception('Network Error'),
        )

        pages = list(crawler.get_page_list(max_list_pages=1))

        # 网络错误应该返回空列表，不抛出异常
        assert len(pages) == 0


class TestTiebaCrawlerPageContent:
    """帖子内容获取测试"""

    @pytest.fixture
    def crawler(self):
        return TiebaCrawler()

    @responses.activate
    def test_get_page_content_single_page(self, crawler):
        """测试单页帖子内容获取"""
        responses.add(
            responses.GET,
            'https://tieba.baidu.com/p/12345',
            body=MOCK_TIEBA_POST_HTML,
            status=200,
        )

        result = crawler.get_page_content('12345', '测试标题')

        assert result is not None
        assert isinstance(result, RawPage)
        assert result.source == DataSource.TIEBA
        assert result.source_id == '12345'
        assert result.title == '测试标题'
        assert '肉丸' in result.content

    @responses.activate
    def test_get_page_content_multi_page(self, crawler):
        """测试多页帖子内容获取"""
        # 第一页
        responses.add(
            responses.GET,
            'https://tieba.baidu.com/p/12345?pn=1',
            body=MOCK_TIEBA_POST_MULTI_PAGE_HTML_PAGE1,
            status=200,
        )
        # 第二页
        responses.add(
            responses.GET,
            'https://tieba.baidu.com/p/12345?pn=2',
            body=MOCK_TIEBA_POST_MULTI_PAGE_HTML_PAGE2,
            status=200,
        )

        result = crawler.get_page_content('12345', '多页帖子')

        assert result is not None
        assert '第一页楼主内容' in result.content
        assert '第二页楼主内容' in result.content
        assert result.extra.get('pages_crawled', 0) >= 1

    @responses.activate
    def test_get_page_content_lz_only(self, crawler):
        """测试楼主标识"""
        responses.add(
            responses.GET,
            'https://tieba.baidu.com/p/12345',
            body=MOCK_TIEBA_POST_LZ_ONLY_HTML,
            status=200,
        )

        result = crawler.get_page_content('12345', '楼主帖子')

        assert result is not None
        # 楼主内容应该被标记
        assert '[楼主]' in result.content or '楼主发布的内容' in result.content

    @responses.activate
    def test_get_page_content_empty_post(self, crawler):
        """测试空帖子处理"""
        responses.add(
            responses.GET,
            'https://tieba.baidu.com/p/99999',
            body=MOCK_TIEBA_POST_EMPTY_HTML,
            status=200,
        )

        result = crawler.get_page_content('99999', '空帖子')

        # 空帖子应该返回None
        assert result is None

    @responses.activate
    def test_get_page_content_returns_raw_page(self, crawler):
        """测试返回正确的RawPage结构"""
        responses.add(
            responses.GET,
            'https://tieba.baidu.com/p/12345',
            body=MOCK_TIEBA_POST_HTML,
            status=200,
        )

        result = crawler.get_page_content('12345', '测试')

        assert result.source == DataSource.TIEBA
        assert result.url == 'https://tieba.baidu.com/p/12345'
        assert result.categories == ['贴吧攻略']
        assert 'forum' in result.extra

    @responses.activate
    def test_get_page_content_network_error(self, crawler):
        """测试网络错误返回None"""
        responses.add(
            responses.GET,
            'https://tieba.baidu.com/p/12345',
            body=Exception('Connection Error'),
        )

        result = crawler.get_page_content('12345', '测试')

        # 网络错误应该返回None
        assert result is None


class TestTiebaCrawlerIntegration:
    """贴吧爬虫集成测试"""

    @pytest.fixture
    def crawler(self):
        return TiebaCrawler()

    @responses.activate
    def test_crawl_flow(self, crawler):
        """测试完整爬取流程"""
        # 模拟列表页
        responses.add(
            responses.GET,
            'https://tieba.baidu.com/f',
            body=MOCK_TIEBA_LIST_HTML,
            status=200,
        )
        # 模拟帖子页
        responses.add(
            responses.GET,
            'https://tieba.baidu.com/p/12345',
            body=MOCK_TIEBA_POST_HTML,
            status=200,
        )
        responses.add(
            responses.GET,
            'https://tieba.baidu.com/p/12346',
            body=MOCK_TIEBA_POST_HTML,
            status=200,
        )

        # 爬取
        pages = list(crawler.crawl(max_pages=2))

        assert len(pages) <= 2
        for page in pages:
            assert isinstance(page, RawPage)
            assert page.source == DataSource.TIEBA

    def test_get_stats(self, crawler):
        """测试统计信息"""
        stats = crawler.get_stats()

        assert 'source' in stats
        assert stats['source'] == 'tieba'
        assert 'crawled_count' in stats
        assert 'failed_count' in stats
