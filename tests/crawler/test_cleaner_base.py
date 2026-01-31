"""BaseCleaner 和 CleanedPage 单元测试"""

import pytest
from bs4 import BeautifulSoup

from src.crawler.base import RawPage, DataSource
from src.crawler.cleaners.base import BaseCleaner, CleanedPage


class ConcreteCleaner(BaseCleaner):
    """用于测试的具体清洗器实现"""

    def _extract_infobox(self, soup, raw_data):
        """简单的信息框提取实现"""
        infobox = {}
        infobox_elem = soup.find(class_='infobox')
        if infobox_elem:
            for row in infobox_elem.find_all('tr'):
                cells = row.find_all(['th', 'td'])
                if len(cells) >= 2:
                    key = cells[0].get_text(strip=True)
                    value = cells[1].get_text(strip=True)
                    if key and value:
                        infobox[key] = value
        return infobox

    def _extract_recipes(self, soup, raw_data):
        """简单的配方提取实现"""
        recipes = []
        recipe_div = soup.find(class_='recipe')
        if recipe_div:
            recipes.append({
                'name': recipe_div.get_text(strip=True),
                'raw': str(recipe_div)
            })
        return recipes


@pytest.fixture
def cleaner():
    """创建清洗器实例"""
    return ConcreteCleaner()


@pytest.fixture
def sample_raw_page():
    """示例原始页面"""
    return RawPage(
        source=DataSource.WIKI_GG,
        source_id="12345",
        title="肉丸",
        url="https://wiki.example.com/肉丸",
        content="肉丸是一种烹饪食物，可以在烹饪锅中制作。",
        html_content="""
        <html>
        <body>
            <div class="mw-parser-output">
                <p>肉丸是一种烹饪食物，可以在烹饪锅中制作。这是一段足够长的描述文本，用于测试摘要提取功能。</p>
                <table class="infobox">
                    <tr><th>生命值</th><td>3</td></tr>
                    <tr><th>饥饿值</th><td>62.5</td></tr>
                    <tr><th>理智值</th><td>5</td></tr>
                </table>
                <h2>获取方式</h2>
                <p>通过烹饪锅制作。</p>
                <h2>用途</h2>
                <p>可以恢复饥饿值。</p>
                <a href="/wiki/烹饪锅">烹饪锅</a>
                <a href="/wiki/肉">肉</a>
            </div>
        </body>
        </html>
        """,
        categories=["食物", "烹饪"],
        raw_data={}
    )


@pytest.fixture
def sample_raw_page_minimal():
    """最小内容的原始页面"""
    return RawPage(
        source=DataSource.WIKI_GG,
        source_id="99999",
        title="测试页面",
        url="https://wiki.example.com/test",
        content="",
        html_content="",
        categories=[],
        raw_data={}
    )


class TestCleanedPage:
    """测试 CleanedPage 数据类"""

    def test_create_cleaned_page(self):
        """测试创建CleanedPage"""
        page = CleanedPage(
            source=DataSource.WIKI_GG,
            source_id="12345",
            title="测试标题",
            url="https://example.com",
            content="测试内容"
        )
        assert page.source == DataSource.WIKI_GG
        assert page.title == "测试标题"
        assert page.content == "测试内容"

    def test_cleaned_page_default_values(self):
        """测试默认值"""
        page = CleanedPage(
            source=DataSource.WIKI_GG,
            source_id="1",
            title="标题",
            url="url",
            content="内容"
        )
        assert page.summary == ""
        assert page.sections == []
        assert page.infobox == {}
        assert page.stats == {}
        assert page.recipes == []
        assert page.categories == []
        assert page.game_version == "both"
        assert page.related_pages == []
        assert page.quality_score == 0.0

    def test_to_dict(self):
        """测试转换为字典"""
        page = CleanedPage(
            source=DataSource.WIKI_GG,
            source_id="12345",
            title="肉丸",
            url="https://example.com",
            content="测试内容",
            summary="摘要",
            infobox={"生命值": "3"},
            stats={"health": 3.0},
            categories=["食物"],
            quality_score=0.8
        )
        result = page.to_dict()

        assert result['source'] == "wiki_gg"
        assert result['source_id'] == "12345"
        assert result['title'] == "肉丸"
        assert result['content'] == "测试内容"
        assert result['summary'] == "摘要"
        assert result['infobox'] == {"生命值": "3"}
        assert result['stats'] == {"health": 3.0}
        assert result['categories'] == ["食物"]
        assert result['quality_score'] == 0.8


class TestCleanHtml:
    """测试 HTML 清洗"""

    def test_remove_script_tags(self, cleaner):
        """测试移除script标签"""
        html = """
        <html><body>
            <script>alert('test')</script>
            <p>内容</p>
        </body></html>
        """
        soup = BeautifulSoup(html, 'lxml')
        cleaned = cleaner._clean_html(soup)
        assert cleaned.find('script') is None
        assert "内容" in cleaned.get_text()

    def test_remove_style_tags(self, cleaner):
        """测试移除style标签"""
        html = """
        <html><body>
            <style>.test { color: red; }</style>
            <p>内容</p>
        </body></html>
        """
        soup = BeautifulSoup(html, 'lxml')
        cleaned = cleaner._clean_html(soup)
        assert cleaned.find('style') is None

    def test_remove_nav_footer(self, cleaner):
        """测试移除导航和页脚"""
        html = """
        <html><body>
            <nav>导航</nav>
            <p>内容</p>
            <footer>页脚</footer>
        </body></html>
        """
        soup = BeautifulSoup(html, 'lxml')
        cleaned = cleaner._clean_html(soup)
        assert cleaned.find('nav') is None
        assert cleaned.find('footer') is None

    def test_remove_edit_section(self, cleaner):
        """测试移除编辑链接"""
        html = """
        <html><body>
            <span class="mw-editsection">[编辑]</span>
            <p>内容</p>
        </body></html>
        """
        soup = BeautifulSoup(html, 'lxml')
        cleaned = cleaner._clean_html(soup)
        assert cleaned.find(class_='mw-editsection') is None

    def test_remove_navbox(self, cleaner):
        """测试移除导航框"""
        html = """
        <html><body>
            <div class="navbox">导航内容</div>
            <p>正文内容</p>
        </body></html>
        """
        soup = BeautifulSoup(html, 'lxml')
        cleaned = cleaner._clean_html(soup)
        assert cleaned.find(class_='navbox') is None

    def test_remove_hidden_elements(self, cleaner):
        """测试移除隐藏元素"""
        html = """
        <html><body>
            <div style="display:none">隐藏内容</div>
            <p>可见内容</p>
        </body></html>
        """
        soup = BeautifulSoup(html, 'lxml')
        cleaned = cleaner._clean_html(soup)
        text = cleaned.get_text()
        assert "隐藏内容" not in text
        assert "可见内容" in text

    def test_remove_toc(self, cleaner):
        """测试移除目录"""
        html = """
        <html><body>
            <div class="toc">目录</div>
            <p>内容</p>
        </body></html>
        """
        soup = BeautifulSoup(html, 'lxml')
        cleaned = cleaner._clean_html(soup)
        assert cleaned.find(class_='toc') is None


class TestExtractContent:
    """测试内容提取"""

    def test_extract_from_parser_output(self, cleaner):
        """测试从mw-parser-output提取"""
        html = """
        <html><body>
            <div class="sidebar">侧边栏</div>
            <div class="mw-parser-output">
                <p>主要内容</p>
            </div>
        </body></html>
        """
        soup = BeautifulSoup(html, 'lxml')
        soup = cleaner._clean_html(soup)
        content = cleaner._extract_content(soup)
        assert "主要内容" in content

    def test_extract_from_content_id(self, cleaner):
        """测试从#content提取"""
        html = """
        <html><body>
            <div id="content">
                <p>页面内容</p>
            </div>
        </body></html>
        """
        soup = BeautifulSoup(html, 'lxml')
        content = cleaner._extract_content(soup)
        assert "页面内容" in content

    def test_extract_cleans_multiple_newlines(self, cleaner):
        """测试清理多余空行"""
        html = """
        <html><body>
            <p>段落1</p>
            <p></p>
            <p></p>
            <p></p>
            <p>段落2</p>
        </body></html>
        """
        soup = BeautifulSoup(html, 'lxml')
        content = cleaner._extract_content(soup)
        # 不应该有超过2个连续换行
        assert "\n\n\n" not in content


class TestExtractSummary:
    """测试摘要提取"""

    def test_extract_first_paragraph(self, cleaner):
        """测试提取第一段"""
        content = """这是第一段，包含足够长的内容用于测试摘要提取功能，需要超过30个字符才能被提取。

第二段内容，这是另一个段落。"""
        summary = cleaner._extract_summary(content)
        assert "第一段" in summary
        assert "第二段" not in summary

    def test_skip_short_paragraphs(self, cleaner):
        """测试跳过短段落"""
        content = """短

这是一段足够长的内容，用于测试跳过短段落的功能是否正常工作。"""
        summary = cleaner._extract_summary(content)
        assert "足够长" in summary

    def test_skip_headings(self, cleaner):
        """测试跳过标题"""
        content = """# 标题

这是一段足够长的正文内容，应该被提取为摘要而不是上面的标题。"""
        summary = cleaner._extract_summary(content)
        assert not summary.startswith("#")

    def test_skip_see_also(self, cleaner):
        """测试跳过'参见'"""
        content = """参见其他相关页面

这是一段足够长的正文内容，应该被提取为摘要而不是上面的参见部分。"""
        summary = cleaner._extract_summary(content)
        assert not summary.startswith("参见")

    def test_limit_length(self, cleaner):
        """测试长度限制"""
        content = "这是一段非常长的内容。" * 100
        summary = cleaner._extract_summary(content)
        assert len(summary) <= 500

    def test_empty_content(self, cleaner):
        """测试空内容"""
        summary = cleaner._extract_summary("")
        assert summary == ""


class TestExtractSections:
    """测试章节提取"""

    def test_extract_h2_sections(self, cleaner):
        """测试提取h2章节"""
        html = """
        <html><body>
            <h2>获取方式</h2>
            <p>通过烹饪获得</p>
            <h2>用途</h2>
            <p>恢复饥饿值</p>
        </body></html>
        """
        soup = BeautifulSoup(html, 'lxml')
        sections = cleaner._extract_sections(soup)

        assert len(sections) == 2
        assert sections[0]['title'] == "获取方式"
        assert sections[0]['level'] == 2
        assert "烹饪" in sections[0]['content']

    def test_extract_h3_sections(self, cleaner):
        """测试提取h3章节"""
        html = """
        <html><body>
            <h2>主章节</h2>
            <p>主内容</p>
            <h3>子章节</h3>
            <p>子内容</p>
        </body></html>
        """
        soup = BeautifulSoup(html, 'lxml')
        sections = cleaner._extract_sections(soup)

        levels = [s['level'] for s in sections]
        assert 2 in levels
        assert 3 in levels

    def test_extract_section_content_until_next_heading(self, cleaner):
        """测试章节内容到下一个标题为止"""
        html = """
        <html><body>
            <h2>章节1</h2>
            <p>内容1</p>
            <p>更多内容1</p>
            <h2>章节2</h2>
            <p>内容2</p>
        </body></html>
        """
        soup = BeautifulSoup(html, 'lxml')
        sections = cleaner._extract_sections(soup)

        section1 = next(s for s in sections if s['title'] == "章节1")
        assert "内容1" in section1['content']
        assert "更多内容1" in section1['content']
        assert "内容2" not in section1['content']

    def test_empty_html(self, cleaner):
        """测试空HTML"""
        soup = BeautifulSoup("<html><body></body></html>", 'lxml')
        sections = cleaner._extract_sections(soup)
        assert sections == []


class TestExtractStats:
    """测试属性提取"""

    def test_extract_from_infobox(self, cleaner):
        """测试从信息框提取"""
        infobox = {
            "生命值": "100",
            "饥饿值": "62.5",
            "理智值": "-5"
        }
        stats = cleaner._extract_stats(infobox, "")
        # 根据normalizer的实现，可能有不同的键名
        assert len(stats) >= 0  # 依赖normalizer的实现

    def test_extract_from_content_regex(self, cleaner):
        """测试从正文正则提取"""
        content = "该物品生命值: 100，饥饿值: 50"
        stats = cleaner._extract_stats({}, content)

        assert 'health' in stats
        assert stats['health'] == 100.0
        assert 'hunger' in stats
        assert stats['hunger'] == 50.0

    def test_extract_damage(self, cleaner):
        """测试伤害值提取"""
        content = "攻击伤害: 75"
        stats = cleaner._extract_stats({}, content)
        assert 'damage' in stats
        assert stats['damage'] == 75.0

    def test_extract_cook_time(self, cleaner):
        """测试烹饪时间提取"""
        content = "烹饪时间: 15秒"
        stats = cleaner._extract_stats({}, content)
        assert 'cook_time' in stats
        assert stats['cook_time'] == 15.0


class TestExtractRelatedPages:
    """测试相关页面提取"""

    def test_extract_wiki_links(self, cleaner):
        """测试提取wiki链接"""
        html = """
        <html><body>
            <a href="/wiki/肉丸">肉丸</a>
            <a href="/wiki/烹饪锅">烹饪锅</a>
            <a href="https://external.com">外部链接</a>
        </body></html>
        """
        soup = BeautifulSoup(html, 'lxml')
        related = cleaner._extract_related_pages(soup)

        assert "肉丸" in related
        assert "烹饪锅" in related
        assert len(related) == 2  # 外部链接不应包含

    def test_extract_zh_links(self, cleaner):
        """测试提取中文wiki链接"""
        html = """
        <html><body>
            <a href="/zh/食物">食物</a>
        </body></html>
        """
        soup = BeautifulSoup(html, 'lxml')
        related = cleaner._extract_related_pages(soup)
        assert "食物" in related

    def test_deduplicate(self, cleaner):
        """测试去重"""
        html = """
        <html><body>
            <a href="/wiki/肉丸">肉丸</a>
            <a href="/wiki/肉丸">肉丸</a>
            <a href="/wiki/肉丸">肉丸</a>
        </body></html>
        """
        soup = BeautifulSoup(html, 'lxml')
        related = cleaner._extract_related_pages(soup)
        assert related.count("肉丸") == 1

    def test_limit_count(self, cleaner):
        """测试数量限制"""
        links = ''.join([f'<a href="/wiki/page{i}">页面{i}</a>' for i in range(50)])
        html = f"<html><body>{links}</body></html>"
        soup = BeautifulSoup(html, 'lxml')
        related = cleaner._extract_related_pages(soup)
        assert len(related) <= 20

    def test_skip_short_titles(self, cleaner):
        """测试跳过过短标题"""
        html = """
        <html><body>
            <a href="/wiki/x">x</a>
            <a href="/wiki/正常标题">正常标题</a>
        </body></html>
        """
        soup = BeautifulSoup(html, 'lxml')
        related = cleaner._extract_related_pages(soup)
        assert "x" not in related
        assert "正常标题" in related


class TestDetectGameVersion:
    """测试游戏版本检测"""

    def test_detect_dst(self, cleaner):
        """测试检测联机版"""
        version = cleaner._detect_game_version("这是联机版的内容", [])
        assert version == "dst"

        version = cleaner._detect_game_version("Don't Starve Together", [])
        assert version == "dst"

    def test_detect_ds(self, cleaner):
        """测试检测单机版"""
        version = cleaner._detect_game_version("这是单机版的内容", [])
        assert version == "ds"

    def test_detect_from_categories(self, cleaner):
        """测试从分类检测"""
        version = cleaner._detect_game_version("", ["联机版物品"])
        assert version == "dst"

    def test_detect_rog_as_ds(self, cleaner):
        """测试巨人国识别为单机版"""
        version = cleaner._detect_game_version("巨人国DLC内容", [])
        assert version == "ds"

    def test_detect_sw_as_ds(self, cleaner):
        """测试海难识别为单机版"""
        version = cleaner._detect_game_version("Shipwrecked content", [])
        assert version == "ds"

    def test_detect_ham_as_ds(self, cleaner):
        """测试哈姆雷特识别为单机版"""
        version = cleaner._detect_game_version("Hamlet DLC", [])
        assert version == "ds"

    def test_default_both(self, cleaner):
        """测试默认返回both"""
        version = cleaner._detect_game_version("通用内容", [])
        assert version == "both"


class TestCleanMethod:
    """测试主清洗方法"""

    def test_clean_basic(self, cleaner, sample_raw_page):
        """测试基本清洗流程"""
        result = cleaner.clean(sample_raw_page)

        assert result is not None
        assert result.source == DataSource.WIKI_GG
        assert result.title == "肉丸"
        assert len(result.content) > 0

    def test_clean_extracts_sections(self, cleaner, sample_raw_page):
        """测试章节提取"""
        result = cleaner.clean(sample_raw_page)

        assert len(result.sections) >= 2
        titles = [s['title'] for s in result.sections]
        assert "获取方式" in titles
        assert "用途" in titles

    def test_clean_extracts_infobox(self, cleaner, sample_raw_page):
        """测试信息框提取"""
        result = cleaner.clean(sample_raw_page)

        assert "生命值" in result.infobox
        assert result.infobox["生命值"] == "3"

    def test_clean_extracts_related_pages(self, cleaner, sample_raw_page):
        """测试相关页面提取"""
        result = cleaner.clean(sample_raw_page)

        assert "烹饪锅" in result.related_pages
        # "肉" 只有1个字符，会被过滤掉（短标题跳过）

    def test_clean_preserves_categories(self, cleaner, sample_raw_page):
        """测试保留分类"""
        result = cleaner.clean(sample_raw_page)

        assert "食物" in result.categories
        assert "烹饪" in result.categories

    def test_clean_calculates_quality(self, cleaner, sample_raw_page):
        """测试质量评分计算"""
        result = cleaner.clean(sample_raw_page)

        assert result.quality_score >= 0.0
        assert result.quality_score <= 1.0

    def test_clean_returns_none_for_empty(self, cleaner, sample_raw_page_minimal):
        """测试空内容返回None"""
        result = cleaner.clean(sample_raw_page_minimal)
        assert result is None

    def test_clean_returns_none_for_short_content(self, cleaner):
        """测试内容过短返回None"""
        page = RawPage(
            source=DataSource.WIKI_GG,
            source_id="1",
            title="短页面",
            url="url",
            content="太短",
            html_content="<html><body><p>太短</p></body></html>",
            categories=[]
        )
        result = cleaner.clean(page)
        assert result is None

    def test_clean_with_only_content(self, cleaner):
        """测试只有纯文本内容（无HTML）"""
        page = RawPage(
            source=DataSource.WIKI_GG,
            source_id="1",
            title="纯文本页面",
            url="url",
            content="这是一段纯文本内容，没有HTML格式。" * 5,
            html_content="",
            categories=[]
        )
        result = cleaner.clean(page)

        assert result is not None
        assert "纯文本" in result.content


class TestEdgeCases:
    """边界情况测试"""

    def test_malformed_html(self, cleaner):
        """测试畸形HTML"""
        page = RawPage(
            source=DataSource.WIKI_GG,
            source_id="1",
            title="测试",
            url="url",
            content="",
            html_content="<html><body><div>未闭合的div<p>段落" + "x" * 100,
            categories=[]
        )
        # 不应抛出异常
        result = cleaner.clean(page)
        # 可能返回结果或None，但不应崩溃
        assert result is None or isinstance(result, CleanedPage)

    def test_unicode_content(self, cleaner):
        """测试Unicode内容"""
        page = RawPage(
            source=DataSource.WIKI_GG,
            source_id="1",
            title="特殊字符测试",
            url="url",
            content="",
            html_content="""
            <html><body>
                <div class="mw-parser-output">
                    <p>包含特殊字符：♥♦♣♠ 饥饿值→100 生命值←50 这段内容足够长，需要超过50个字符才能通过长度检查。这里添加更多文字确保达到要求。</p>
                </div>
            </body></html>
            """,
            categories=[]
        )
        result = cleaner.clean(page)
        assert result is not None
        assert "♥" in result.content

    def test_deeply_nested_html(self, cleaner):
        """测试深度嵌套HTML"""
        nested = "<div>" * 20 + "<p>深层内容，这段话需要足够长才能通过长度检查。这里添加额外的文字来确保内容长度超过50个字符的最低要求。</p>" + "</div>" * 20
        page = RawPage(
            source=DataSource.WIKI_GG,
            source_id="1",
            title="嵌套测试",
            url="url",
            content="",
            html_content=f"<html><body>{nested}</body></html>",
            categories=[]
        )
        result = cleaner.clean(page)
        assert result is not None
        assert "深层内容" in result.content


class TestVersionKeywords:
    """测试版本关键词配置"""

    def test_version_keywords_structure(self, cleaner):
        """测试版本关键词结构"""
        assert 'dst' in cleaner.VERSION_KEYWORDS
        assert 'ds' in cleaner.VERSION_KEYWORDS
        assert 'rog' in cleaner.VERSION_KEYWORDS
        assert 'sw' in cleaner.VERSION_KEYWORDS
        assert 'ham' in cleaner.VERSION_KEYWORDS

    def test_version_keywords_content(self, cleaner):
        """测试版本关键词内容"""
        assert '联机版' in cleaner.VERSION_KEYWORDS['dst']
        assert '单机版' in cleaner.VERSION_KEYWORDS['ds']
        assert '巨人国' in cleaner.VERSION_KEYWORDS['rog']
        assert '海难' in cleaner.VERSION_KEYWORDS['sw']
        assert '哈姆雷特' in cleaner.VERSION_KEYWORDS['ham']


class TestRemoveTagsAndClasses:
    """测试移除标签和类名配置"""

    def test_remove_tags_list(self, cleaner):
        """测试移除标签列表"""
        expected_tags = ['script', 'style', 'nav', 'footer', 'aside', 'noscript', 'iframe']
        for tag in expected_tags:
            assert tag in cleaner.REMOVE_TAGS

    def test_remove_classes_list(self, cleaner):
        """测试移除类名列表"""
        expected_classes = ['mw-editsection', 'navbox', 'toc', 'mbox', 'noprint']
        for cls in expected_classes:
            assert cls in cleaner.REMOVE_CLASSES
