"""爬虫模块测试"""

import pytest
from unittest.mock import Mock, patch, MagicMock
import json

from src.crawler import WikiCrawler, WikiParser
from src.utils.models import WikiPage, EntityType, GameVersion


class TestWikiCrawler:
    """WikiCrawler测试类"""

    def test_init(self):
        """测试爬虫初始化"""
        crawler = WikiCrawler()
        assert crawler.session is not None
        assert crawler.config is not None
        assert len(crawler.crawled_pages) == 0

    def test_detect_version_dst(self):
        """测试联机版检测"""
        crawler = WikiCrawler()
        version = crawler._detect_version([], "仅联机版内容")
        assert version == GameVersion.DST

    def test_detect_version_ds(self):
        """测试单机版检测"""
        crawler = WikiCrawler()
        version = crawler._detect_version([], "仅单机版内容")
        assert version == GameVersion.DS

    def test_detect_version_both(self):
        """测试通用版本检测"""
        crawler = WikiCrawler()
        version = crawler._detect_version([], "通用内容")
        assert version == GameVersion.BOTH

    def test_detect_entity_type_food(self):
        """测试食物类型检测"""
        crawler = WikiCrawler()
        entity_type = crawler._detect_entity_type(["食物", "烹饪锅食谱"], "肉丸")
        assert entity_type == EntityType.FOOD

    def test_detect_entity_type_boss(self):
        """测试Boss类型检测"""
        crawler = WikiCrawler()
        entity_type = crawler._detect_entity_type(["Boss", "生物"], "蜘蛛女皇")
        assert entity_type == EntityType.BOSS

    @patch("src.crawler.wiki_crawler.requests.Session")
    def test_get_category_pages(self, mock_session):
        """测试获取分类页面"""
        # 模拟API响应
        mock_response = Mock()
        mock_response.json.return_value = {
            "query": {
                "categorymembers": [
                    {"pageid": 1, "title": "物品1", "ns": 0},
                    {"pageid": 2, "title": "物品2", "ns": 0},
                ]
            }
        }
        mock_response.raise_for_status = Mock()

        mock_session_instance = MagicMock()
        mock_session_instance.get.return_value = mock_response
        mock_session.return_value = mock_session_instance

        crawler = WikiCrawler()
        crawler.session = mock_session_instance

        pages = crawler.get_category_pages("物品")
        assert len(pages) == 2
        assert pages[0]["pageid"] == 1

    def test_save_and_load_pages(self, sample_wiki_page, temp_data_dir):
        """测试页面保存和加载"""
        crawler = WikiCrawler()
        crawler.output_dir = temp_data_dir

        # 保存
        crawler.save_pages([sample_wiki_page], "test_pages.json")

        # 加载
        loaded = crawler.load_pages("test_pages.json")
        assert len(loaded) == 1
        assert loaded[0].title == sample_wiki_page.title


class TestWikiParser:
    """WikiParser测试类"""

    def test_init(self):
        """测试解析器初始化"""
        parser = WikiParser()
        assert parser.recipe_patterns is not None

    def test_clean_text(self):
        """测试文本清理"""
        parser = WikiParser()

        text = "[[链接|显示文本]]  多余   空格"
        cleaned = parser.clean_text(text)
        assert "[[" not in cleaned
        assert "  " not in cleaned

    def test_extract_sections(self):
        """测试章节提取"""
        parser = WikiParser()

        html = """
        <h2>材料</h2>
        <p>需要以下材料</p>
        <h2>制作方法</h2>
        <p>步骤说明</p>
        """

        sections = parser.extract_sections(html)
        assert len(sections) >= 2

    def test_extract_tables(self):
        """测试表格提取"""
        parser = WikiParser()

        html = """
        <table>
            <tr><th>名称</th><th>数值</th></tr>
            <tr><td>生命值</td><td>100</td></tr>
        </table>
        """

        tables = parser.extract_tables(html)
        assert len(tables) == 1
        assert len(tables[0]) == 2

    def test_extract_number(self):
        """测试数字提取"""
        parser = WikiParser()

        assert parser._extract_number("100点") == 100.0
        assert parser._extract_number("3.5秒") == 3.5
        assert parser._extract_number("无") is None
        assert parser._extract_number("") is None

    def test_parse_page(self, sample_wiki_page):
        """测试页面解析"""
        parser = WikiParser()
        result = parser.parse_page(sample_wiki_page)

        assert "page" in result
        assert "sections" in result
        assert result["page"].title == "肉丸"
