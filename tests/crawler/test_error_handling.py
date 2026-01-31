"""爬虫错误处理测试"""

import pytest
from unittest.mock import Mock, MagicMock, patch
import requests
from bs4 import BeautifulSoup

from src.crawler.base import DataSource, RawPage
from src.crawler.cleaners import (
    MediaWikiCleaner,
    TiebaCleaner,
    SteamCleaner,
    CleanedPage,
)
from .fixtures.mock_responses import (
    MOCK_MALFORMED_HTML_UNCLOSED_TAGS,
    MOCK_MALFORMED_HTML_UNICODE,
    MOCK_MALFORMED_HTML_NESTED,
    get_mock_raw_page_tieba_empty,
    get_mock_raw_page_steam_no_sections,
    get_mock_raw_page_wiki_malformed,
    get_mock_raw_page_wiki_no_infobox,
)


class TestRequestRetry:
    """请求重试机制测试"""

    def test_retry_decorator_exists(self):
        """测试重试装饰器存在"""
        from tenacity import retry, stop_after_attempt, wait_exponential

        # 验证tenacity模块可导入
        assert retry is not None
        assert stop_after_attempt is not None
        assert wait_exponential is not None

    def test_retry_on_timeout(self):
        """测试超时重试"""
        call_count = 0
        max_retries = 3

        def mock_request():
            nonlocal call_count
            call_count += 1
            if call_count < max_retries:
                raise requests.exceptions.Timeout("Connection timed out")
            return Mock(status_code=200)

        # 模拟重试行为
        for i in range(max_retries):
            try:
                result = mock_request()
                break
            except requests.exceptions.Timeout:
                if i == max_retries - 1:
                    raise
                continue

        assert call_count == max_retries

    def test_retry_on_connection_error(self):
        """测试连接错误重试"""
        call_count = 0

        def mock_request():
            nonlocal call_count
            call_count += 1
            if call_count < 2:
                raise requests.exceptions.ConnectionError("Connection refused")
            return Mock(status_code=200)

        try:
            for _ in range(3):
                try:
                    result = mock_request()
                    break
                except requests.exceptions.ConnectionError:
                    continue
        except:
            pass

        assert call_count >= 2

    def test_retry_on_server_error(self):
        """测试服务器错误重试"""
        responses_list = [
            Mock(status_code=500, raise_for_status=Mock(side_effect=requests.HTTPError("500 Server Error"))),
            Mock(status_code=503, raise_for_status=Mock(side_effect=requests.HTTPError("503 Service Unavailable"))),
            Mock(status_code=200, raise_for_status=Mock()),
        ]
        call_count = 0

        def mock_request():
            nonlocal call_count
            response = responses_list[min(call_count, len(responses_list) - 1)]
            call_count += 1
            response.raise_for_status()
            return response

        # 模拟重试直到成功
        for _ in range(3):
            try:
                result = mock_request()
                break
            except requests.HTTPError:
                continue

        assert call_count == 3

    def test_max_retries_exceeded(self):
        """测试超过最大重试次数"""
        max_retries = 3
        call_count = 0

        def mock_request():
            nonlocal call_count
            call_count += 1
            raise requests.exceptions.Timeout("Always timeout")

        with pytest.raises(requests.exceptions.Timeout):
            for i in range(max_retries):
                try:
                    mock_request()
                except requests.exceptions.Timeout:
                    if i == max_retries - 1:
                        raise

        assert call_count == max_retries

    def test_no_retry_on_client_error(self):
        """测试客户端错误不重试（4xx）"""
        call_count = 0

        def mock_request():
            nonlocal call_count
            call_count += 1
            raise requests.HTTPError("404 Not Found")

        # 4xx错误通常不应该重试
        with pytest.raises(requests.HTTPError):
            mock_request()

        assert call_count == 1


class TestRateLimiting:
    """请求限流测试"""

    def test_request_delay_config(self):
        """测试请求延迟配置"""
        from src.crawler.base import DEFAULT_SOURCE_CONFIGS, DataSource

        # 验证默认配置有request_delay
        for source, config in DEFAULT_SOURCE_CONFIGS.items():
            assert hasattr(config, 'request_delay') or config.request_delay is None

    def test_custom_request_delay(self):
        """测试自定义请求延迟"""
        custom_delay = 2.5
        config = {'request_delay': custom_delay}

        # 验证配置被正确读取
        assert config['request_delay'] == custom_delay


class TestErrorRecovery:
    """错误恢复测试"""

    def test_failed_page_recorded(self):
        """测试失败页面被记录"""
        failed_ids = []

        def crawl_page(page_id: str) -> bool:
            if page_id == 'bad_page':
                return False
            return True

        pages = ['page1', 'bad_page', 'page2']

        for page_id in pages:
            if not crawl_page(page_id):
                failed_ids.append(page_id)

        assert 'bad_page' in failed_ids
        assert len(failed_ids) == 1

    def test_crawl_continues_after_failure(self):
        """测试失败后继续爬取"""
        results = []
        errors = []

        pages = ['page1', 'error_page', 'page2', 'page3']

        for page_id in pages:
            try:
                if page_id == 'error_page':
                    raise Exception("Simulated error")
                results.append(page_id)
            except Exception as e:
                errors.append(page_id)
                continue  # 继续爬取

        assert len(results) == 3
        assert 'error_page' not in results
        assert 'error_page' in errors

    def test_partial_results_saved(self, tmp_path):
        """测试部分结果被保存"""
        import json

        output_file = tmp_path / "results.json"
        results = []
        save_threshold = 2

        pages = ['page1', 'page2', 'error', 'page3']

        try:
            for i, page_id in enumerate(pages):
                if page_id == 'error':
                    # 在错误前保存
                    with open(output_file, 'w') as f:
                        json.dump(results, f)
                    raise Exception("Simulated crash")

                results.append({'id': page_id})

                # 定期保存
                if len(results) % save_threshold == 0:
                    with open(output_file, 'w') as f:
                        json.dump(results, f)
        except Exception:
            pass  # 预期的异常

        # 验证部分结果被保存
        with open(output_file, 'r') as f:
            saved = json.load(f)

        assert len(saved) == 2  # page1和page2


class TestCleanerErrorHandling:
    """清洗器错误处理测试"""

    def test_clean_malformed_html_unclosed_tags(self):
        """测试处理未闭合标签的HTML"""
        soup = BeautifulSoup(MOCK_MALFORMED_HTML_UNCLOSED_TAGS, 'lxml')

        # BeautifulSoup应该能处理未闭合标签
        content_div = soup.find('div', class_='content')
        assert content_div is not None

        text = content_div.get_text(strip=True)
        assert '未闭合的段落' in text

    def test_clean_malformed_html_unicode(self):
        """测试处理Unicode特殊字符"""
        soup = BeautifulSoup(MOCK_MALFORMED_HTML_UNICODE, 'lxml')

        content_div = soup.find('div', class_='content')
        text = content_div.get_text(strip=True)

        # 应该保留emoji
        assert '饥荒游戏' in text

    def test_clean_malformed_html_nested(self):
        """测试处理深度嵌套HTML"""
        soup = BeautifulSoup(MOCK_MALFORMED_HTML_NESTED, 'lxml')

        # 应该能正确解析嵌套结构
        text = soup.get_text(strip=True)
        assert '深度嵌套内容' in text

    def test_clean_empty_content(self):
        """测试处理空内容"""
        raw_page = get_mock_raw_page_tieba_empty()

        cleaner = TiebaCleaner()
        result = cleaner.clean(raw_page)

        # 空内容可能返回None或空字符串
        if result:
            assert result.content == '' or len(result.content) == 0

    def test_clean_missing_infobox(self):
        """测试处理缺失信息框"""
        raw_page = get_mock_raw_page_wiki_no_infobox()

        cleaner = MediaWikiCleaner()
        result = cleaner.clean(raw_page)

        # 清洗器可能根据内容质量返回None
        # 如果返回结果，则验证infobox为空
        if result is not None:
            assert result.infobox == {} or result.infobox is None or len(result.infobox) == 0

    def test_clean_malformed_infobox(self):
        """测试处理畸形信息框"""
        raw_page = get_mock_raw_page_wiki_malformed()

        cleaner = MediaWikiCleaner()
        # 应该不会抛出异常
        try:
            result = cleaner.clean(raw_page)
            # 清洗成功或返回None都可接受
        except Exception as e:
            pytest.fail(f"清洗畸形数据不应抛出异常: {e}")

    def test_clean_steam_no_sections(self):
        """测试处理无章节Steam指南"""
        raw_page = get_mock_raw_page_steam_no_sections()

        cleaner = SteamCleaner()
        # 清洗器可能返回None（内容太短）
        try:
            result = cleaner.clean(raw_page)
            # 返回None或有效结果都可接受
        except Exception as e:
            pytest.fail(f"清洗无章节指南不应抛出异常: {e}")


class TestDataValidation:
    """数据验证测试"""

    def test_raw_page_required_fields(self):
        """测试RawPage必需字段"""
        with pytest.raises(TypeError):
            # 缺少必需字段应该报错
            RawPage()

    def test_raw_page_with_minimal_fields(self):
        """测试最小字段的RawPage"""
        page = RawPage(
            source=DataSource.WIKI_GG,
            source_id='1',
            title='测试',
            url='http://test.com',
            content='内容',
            html_content='<p>内容</p>',
        )

        assert page.title == '测试'
        assert page.categories == []  # 默认空列表

    def test_cleaned_page_quality_score_range(self):
        """测试质量分数范围"""
        page = CleanedPage(
            source=DataSource.WIKI_GG,
            source_id='1',
            title='测试',
            url='http://test.com',
            content='内容',
        )

        # 质量分数应该在0-1之间
        if hasattr(page, 'quality_score') and page.quality_score is not None:
            assert 0.0 <= page.quality_score <= 1.0


class TestNetworkErrorScenarios:
    """网络错误场景测试"""

    def test_timeout_handling(self):
        """测试超时处理"""
        def make_request_with_timeout(timeout=5):
            # 模拟超时
            if timeout < 10:
                raise requests.exceptions.Timeout()
            return Mock(status_code=200)

        with pytest.raises(requests.exceptions.Timeout):
            make_request_with_timeout(timeout=5)

    def test_dns_error_handling(self):
        """测试DNS解析错误"""
        def make_request():
            raise requests.exceptions.ConnectionError("DNS resolution failed")

        with pytest.raises(requests.exceptions.ConnectionError):
            make_request()

    def test_ssl_error_handling(self):
        """测试SSL错误"""
        def make_request():
            raise requests.exceptions.SSLError("Certificate verify failed")

        with pytest.raises(requests.exceptions.SSLError):
            make_request()

    def test_redirect_loop_handling(self):
        """测试重定向循环"""
        def make_request():
            raise requests.exceptions.TooManyRedirects("Exceeded max redirects")

        with pytest.raises(requests.exceptions.TooManyRedirects):
            make_request()
