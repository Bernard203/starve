"""清洗器测试"""

import pytest
from bs4 import BeautifulSoup

from src.crawler.base import DataSource, RawPage
from src.crawler.cleaners import (
    BaseCleaner,
    CleanedPage,
    MediaWikiCleaner,
    TiebaCleaner,
    SteamCleaner,
    DataNormalizer,
    QualityAssessor,
)
from .fixtures.mock_data import (
    get_mock_raw_page_wiki,
    get_mock_raw_page_tieba,
    get_mock_raw_page_steam,
    MOCK_WIKI_PAGE_RESPONSE,
)


class TestDataNormalizer:
    """DataNormalizer测试"""

    @pytest.fixture
    def normalizer(self):
        return DataNormalizer()

    def test_normalize_stat_name_chinese(self, normalizer):
        """测试中文属性名标准化"""
        assert normalizer.normalize_stat_name('生命值') == 'health'
        assert normalizer.normalize_stat_name('饥饿值') == 'hunger'
        assert normalizer.normalize_stat_name('理智值') == 'sanity'
        assert normalizer.normalize_stat_name('伤害') == 'damage'

    def test_normalize_stat_name_english(self, normalizer):
        """测试英文属性名标准化"""
        assert normalizer.normalize_stat_name('Health') == 'health'
        assert normalizer.normalize_stat_name('Hunger') == 'hunger'
        assert normalizer.normalize_stat_name('HP') == 'health'

    def test_normalize_stat_name_unknown(self, normalizer):
        """测试未知属性名"""
        assert normalizer.normalize_stat_name('未知属性') is None
        assert normalizer.normalize_stat_name('') is None

    def test_normalize_value_number(self, normalizer):
        """测试数值标准化"""
        assert normalizer.normalize_value(100) == 100.0
        assert normalizer.normalize_value(62.5) == 62.5

    def test_normalize_value_string(self, normalizer):
        """测试字符串数值提取"""
        assert normalizer.normalize_value('100点') == 100.0
        assert normalizer.normalize_value('62.5') == 62.5
        assert normalizer.normalize_value('+15') == 15.0

    def test_normalize_value_range(self, normalizer):
        """测试范围值"""
        assert normalizer.normalize_value('10-20') == 15.0
        assert normalizer.normalize_value('10~20') == 15.0

    def test_normalize_value_invalid(self, normalizer):
        """测试无效值"""
        assert normalizer.normalize_value('无') is None
        assert normalizer.normalize_value(None) is None

    def test_normalize_item_name(self, normalizer):
        """测试物品名标准化"""
        assert normalizer.normalize_item_name('蒸肉丸') == '肉丸'
        assert normalizer.normalize_item_name('肉丸子') == '肉丸'
        assert normalizer.normalize_item_name('蜘蛛女王') == '蜘蛛女皇'

    def test_extract_ingredients(self, normalizer):
        """测试材料提取"""
        text = '怪物肉 × 1 + 浆果 × 3'
        ingredients = normalizer.extract_ingredients(text)

        assert len(ingredients) == 2
        assert ingredients[0]['name'] == '怪物肉'
        assert ingredients[0]['count'] == 1
        assert ingredients[1]['count'] == 3


class TestQualityAssessor:
    """QualityAssessor测试"""

    @pytest.fixture
    def assessor(self):
        return QualityAssessor()

    @pytest.fixture
    def high_quality_page(self):
        """高质量页面"""
        return CleanedPage(
            source=DataSource.WIKI_GG,
            source_id='1',
            title='测试页面',
            url='https://test.com',
            content='这是一段很长的内容。' * 100,  # 长内容
            summary='这是摘要，包含有用的信息。',
            sections=[
                {'level': 2, 'title': '章节1', 'content': '内容1'},
                {'level': 2, 'title': '章节2', 'content': '内容2'},
                {'level': 2, 'title': '章节3', 'content': '内容3'},
            ],
            infobox={'属性1': '值1', '属性2': '值2', '属性3': '值3', '属性4': '值4'},
            stats={'health': 100, 'hunger': 50, 'sanity': 30},
            recipes=[{'ingredients': [], 'result': '产物'}],
            categories=['分类1', '分类2', '分类3'],
            related_pages=['页面1', '页面2', '页面3', '页面4', '页面5', '页面6'],
        )

    @pytest.fixture
    def low_quality_page(self):
        """低质量页面"""
        return CleanedPage(
            source=DataSource.WIKI_GG,
            source_id='2',
            title='',
            url='',
            content='短内容',
        )

    def test_assess_high_quality(self, assessor, high_quality_page):
        """测试高质量页面评分"""
        score = assessor.assess(high_quality_page)
        assert score > 0.6

    def test_assess_low_quality(self, assessor, low_quality_page):
        """测试低质量页面评分"""
        score = assessor.assess(low_quality_page)
        assert score < 0.3

    def test_filter_by_quality(self, assessor, high_quality_page, low_quality_page):
        """测试质量过滤"""
        pages = [high_quality_page, low_quality_page]
        filtered = assessor.filter_by_quality(pages, min_score=0.5)

        assert len(filtered) == 1
        assert filtered[0].title == '测试页面'

    def test_quality_report(self, assessor, high_quality_page, low_quality_page):
        """测试质量报告"""
        pages = [high_quality_page, low_quality_page]
        report = assessor.get_quality_report(pages)

        assert report['total'] == 2
        assert 'average_score' in report
        assert 'distribution' in report


class TestMediaWikiCleaner:
    """MediaWikiCleaner测试"""

    @pytest.fixture
    def cleaner(self):
        return MediaWikiCleaner()

    def test_clean_wiki_page(self, cleaner):
        """测试Wiki页面清洗"""
        raw_page = get_mock_raw_page_wiki()
        cleaned = cleaner.clean(raw_page)

        assert cleaned is not None
        assert cleaned.title == '肉丸'
        assert '烹饪锅' in cleaned.content

    def test_extract_infobox(self, cleaner):
        """测试信息框提取"""
        html = MOCK_WIKI_PAGE_RESPONSE['parse']['text']['*']
        soup = BeautifulSoup(html, 'lxml')

        infobox = cleaner._extract_infobox(soup, {})

        assert '饥饿值' in infobox or 'hunger' in str(infobox).lower()

    def test_extract_stats(self, cleaner):
        """测试属性提取"""
        infobox = {'饥饿值': '62.5', '理智值': '5'}
        content = '生命值: 3'

        stats = cleaner._extract_stats(infobox, content)

        assert 'hunger' in stats
        assert stats['hunger'] == 62.5

    def test_detect_game_version_dst(self, cleaner):
        """测试DST版本检测"""
        version = cleaner._detect_game_version('这是联机版内容', [])
        assert version == 'dst'

    def test_detect_game_version_ds(self, cleaner):
        """测试DS版本检测"""
        version = cleaner._detect_game_version('这是单机版内容', [])
        assert version == 'ds'

    def test_detect_game_version_both(self, cleaner):
        """测试通用版本"""
        version = cleaner._detect_game_version('普通内容', [])
        assert version == 'both'


class TestTiebaCleaner:
    """TiebaCleaner测试"""

    @pytest.fixture
    def cleaner(self):
        return TiebaCleaner()

    def test_clean_tieba_page(self, cleaner):
        """测试贴吧页面清洗"""
        raw_page = get_mock_raw_page_tieba()
        cleaned = cleaner.clean(raw_page)

        assert cleaned is not None
        assert cleaned.source == DataSource.TIEBA

    def test_extract_content_floors(self, cleaner):
        """测试楼层内容提取"""
        from .fixtures.mock_data import MOCK_TIEBA_POST_HTML
        soup = BeautifulSoup(MOCK_TIEBA_POST_HTML, 'lxml')

        content = cleaner._extract_content(soup)

        assert '肉丸' in content
        assert '配方' in content


class TestSteamCleaner:
    """SteamCleaner测试"""

    @pytest.fixture
    def cleaner(self):
        return SteamCleaner()

    def test_clean_steam_page(self, cleaner):
        """测试Steam页面清洗"""
        raw_page = get_mock_raw_page_steam()
        cleaned = cleaner.clean(raw_page)

        assert cleaned is not None
        assert cleaned.source == DataSource.STEAM

    def test_extract_sections(self, cleaner):
        """测试章节提取"""
        from .fixtures.mock_data import MOCK_STEAM_GUIDE_HTML
        soup = BeautifulSoup(MOCK_STEAM_GUIDE_HTML, 'lxml')

        sections = cleaner._extract_sections(soup)

        assert len(sections) >= 2
        assert any('基础' in s['title'] for s in sections)
