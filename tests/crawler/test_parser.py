"""WikiParser 单元测试"""

import pytest
from datetime import datetime

from src.crawler.parser import WikiParser
from src.utils.models import WikiPage, EntityType, GameVersion


@pytest.fixture
def parser():
    """创建解析器实例"""
    return WikiParser()


@pytest.fixture
def sample_html_with_sections():
    """包含章节的HTML示例"""
    return """
    <html>
    <body>
        <p>这是概述内容。</p>
        <h2>获取方式</h2>
        <p>可以通过烹饪获得。</p>
        <ul>
            <li>材料1</li>
            <li>材料2</li>
        </ul>
        <h2>用途</h2>
        <p>可以恢复饥饿值。</p>
        <h3>食用效果</h3>
        <p>饥饿+50, 理智+5</p>
    </body>
    </html>
    """


@pytest.fixture
def sample_html_with_table():
    """包含表格的HTML示例"""
    return """
    <html>
    <body>
        <table>
            <tr>
                <th>材料</th>
                <th>数量</th>
            </tr>
            <tr>
                <td>肉</td>
                <td>2</td>
            </tr>
            <tr>
                <td>蔬菜</td>
                <td>1</td>
            </tr>
        </table>
    </body>
    </html>
    """


@pytest.fixture
def sample_html_with_infobox():
    """包含信息框的HTML示例"""
    return """
    <html>
    <body>
        <table class="infobox">
            <tr>
                <th>生命值</th>
                <td>100</td>
            </tr>
            <tr>
                <th>伤害</th>
                <td>50</td>
            </tr>
            <tr>
                <th>移动速度</th>
                <td>6.0</td>
            </tr>
        </table>
    </body>
    </html>
    """


@pytest.fixture
def sample_html_with_portable_infobox():
    """包含portable-infobox的HTML示例"""
    return """
    <html>
    <body>
        <aside class="portable-infobox">
            <div data-source="health">
                <span class="pi-data-value">150</span>
            </div>
            <div data-source="damage">
                <span class="pi-data-value">75</span>
            </div>
        </aside>
    </body>
    </html>
    """


@pytest.fixture
def sample_food_page():
    """食物类Wiki页面示例"""
    return WikiPage(
        page_id=1001,
        title="肉丸",
        url="https://wiki.example.com/肉丸",
        content="""
        肉丸是一种烹饪食物。
        配方：
        肉类 x1
        填充物 x3
        """,
        html_content="""
        <html>
        <body>
            <table class="infobox">
                <tr><th>烹饪时间</th><td>15秒</td></tr>
                <tr><th>饥饿值</th><td>62.5</td></tr>
                <tr><th>理智值</th><td>5</td></tr>
                <tr><th>生命值</th><td>3</td></tr>
            </table>
            <p>肉丸是一种烹饪食物。</p>
        </body>
        </html>
        """,
        entity_type=EntityType.FOOD,
        version=GameVersion.BOTH
    )


@pytest.fixture
def sample_creature_page():
    """生物类Wiki页面示例"""
    return WikiPage(
        page_id=2001,
        title="蜘蛛",
        url="https://wiki.example.com/蜘蛛",
        content="蜘蛛是一种常见的敌对生物，主要在夜间活动。",
        html_content="""
        <html>
        <body>
            <table class="infobox">
                <tr><th>生命值</th><td>100</td></tr>
                <tr><th>伤害</th><td>20</td></tr>
                <tr><th>攻击间隔</th><td>3秒</td></tr>
                <tr><th>移动速度</th><td>3.0</td></tr>
                <tr><th>掉落物</th><td>蜘蛛网, 怪物肉, 蜘蛛腺体</td></tr>
            </table>
        </body>
        </html>
        """,
        entity_type=EntityType.CREATURE,
        version=GameVersion.BOTH
    )


@pytest.fixture
def sample_boss_page():
    """Boss类Wiki页面示例"""
    return WikiPage(
        page_id=3001,
        title="蜘蛛女皇",
        url="https://wiki.example.com/蜘蛛女皇",
        content="蜘蛛女皇是游戏中的Boss之一，具有强大的攻击力和召唤蜘蛛的能力。",
        html_content="""
        <html>
        <body>
            <table class="infobox">
                <tr><th>生命值</th><td>1250</td></tr>
                <tr><th>伤害</th><td>80</td></tr>
                <tr><th>攻击间隔</th><td>2秒</td></tr>
                <tr><th>掉落物</th><td>蜘蛛帽, 蜘蛛卵</td></tr>
            </table>
        </body>
        </html>
        """,
        entity_type=EntityType.BOSS,
        version=GameVersion.DST
    )


class TestExtractSections:
    """测试章节提取功能"""

    def test_extract_sections_basic(self, parser, sample_html_with_sections):
        """测试基本章节提取"""
        sections = parser.extract_sections(sample_html_with_sections)

        assert len(sections) >= 3
        assert sections[0]["title"] == "概述"
        assert "概述内容" in sections[0]["content"]

    def test_extract_sections_with_headers(self, parser, sample_html_with_sections):
        """测试带标题的章节提取"""
        sections = parser.extract_sections(sample_html_with_sections)

        titles = [s["title"] for s in sections]
        assert "获取方式" in titles
        assert "用途" in titles
        assert "食用效果" in titles

    def test_extract_sections_levels(self, parser, sample_html_with_sections):
        """测试章节层级"""
        sections = parser.extract_sections(sample_html_with_sections)

        # h2 = level 2, h3 = level 3
        for section in sections:
            if section["title"] == "获取方式":
                assert section["level"] == 2
            if section["title"] == "食用效果":
                assert section["level"] == 3

    def test_extract_sections_empty_html(self, parser):
        """测试空HTML"""
        sections = parser.extract_sections("")
        assert sections == []

    def test_extract_sections_no_headers(self, parser):
        """测试无标题HTML"""
        html = "<html><body><p>只有段落内容</p></body></html>"
        sections = parser.extract_sections(html)

        assert len(sections) == 1
        assert sections[0]["title"] == "概述"
        assert "只有段落内容" in sections[0]["content"]

    def test_extract_sections_includes_lists(self, parser, sample_html_with_sections):
        """测试包含列表的章节"""
        sections = parser.extract_sections(sample_html_with_sections)

        # 获取方式章节应包含列表内容
        for section in sections:
            if section["title"] == "获取方式":
                assert "材料1" in section["content"]
                assert "材料2" in section["content"]


class TestExtractTables:
    """测试表格提取功能"""

    def test_extract_tables_basic(self, parser, sample_html_with_table):
        """测试基本表格提取"""
        tables = parser.extract_tables(sample_html_with_table)

        assert len(tables) == 1
        assert len(tables[0]) == 3  # 表头 + 2行数据

    def test_extract_tables_headers(self, parser, sample_html_with_table):
        """测试表头提取"""
        tables = parser.extract_tables(sample_html_with_table)

        header = tables[0][0]
        assert "材料" in header
        assert "数量" in header

    def test_extract_tables_data(self, parser, sample_html_with_table):
        """测试表格数据提取"""
        tables = parser.extract_tables(sample_html_with_table)

        # 检查数据行
        assert tables[0][1] == ["肉", "2"]
        assert tables[0][2] == ["蔬菜", "1"]

    def test_extract_tables_empty_html(self, parser):
        """测试空HTML"""
        tables = parser.extract_tables("")
        assert tables == []

    def test_extract_tables_no_tables(self, parser):
        """测试无表格HTML"""
        html = "<html><body><p>没有表格</p></body></html>"
        tables = parser.extract_tables(html)
        assert tables == []

    def test_extract_multiple_tables(self, parser):
        """测试多表格提取"""
        html = """
        <html><body>
            <table><tr><td>表1</td></tr></table>
            <table><tr><td>表2</td></tr></table>
        </body></html>
        """
        tables = parser.extract_tables(html)
        assert len(tables) == 2


class TestExtractInfobox:
    """测试信息框提取功能"""

    def test_extract_infobox_basic(self, parser, sample_html_with_infobox):
        """测试基本信息框提取"""
        infobox = parser.extract_infobox(sample_html_with_infobox)

        assert "生命值" in infobox
        assert infobox["生命值"] == "100"

    def test_extract_infobox_multiple_fields(self, parser, sample_html_with_infobox):
        """测试多字段提取"""
        infobox = parser.extract_infobox(sample_html_with_infobox)

        assert infobox["伤害"] == "50"
        assert infobox["移动速度"] == "6.0"

    def test_extract_portable_infobox(self, parser, sample_html_with_portable_infobox):
        """测试portable-infobox提取"""
        infobox = parser.extract_infobox(sample_html_with_portable_infobox)

        assert "health" in infobox
        assert infobox["health"] == "150"
        assert infobox["damage"] == "75"

    def test_extract_infobox_empty_html(self, parser):
        """测试空HTML"""
        infobox = parser.extract_infobox("")
        assert infobox == {}

    def test_extract_infobox_no_infobox(self, parser):
        """测试无信息框HTML"""
        html = "<html><body><p>没有信息框</p></body></html>"
        infobox = parser.extract_infobox(html)
        assert infobox == {}

    def test_extract_infobox_case_insensitive(self, parser):
        """测试信息框类名大小写不敏感"""
        html = """
        <html><body>
            <table class="InfoBox">
                <tr><th>测试</th><td>值</td></tr>
            </table>
        </body></html>
        """
        infobox = parser.extract_infobox(html)
        assert "测试" in infobox


class TestParseFoodRecipe:
    """测试食物配方解析"""

    def test_parse_food_recipe_basic(self, parser, sample_food_page):
        """测试基本食物配方解析"""
        recipe = parser.parse_food_recipe(sample_food_page)

        assert recipe is not None
        assert recipe.name == "肉丸"
        assert recipe.recipe_type == "cooking"

    def test_parse_food_recipe_cook_time(self, parser, sample_food_page):
        """测试烹饪时间解析"""
        recipe = parser.parse_food_recipe(sample_food_page)

        assert recipe.cook_time == 15.0

    def test_parse_food_recipe_stats(self, parser, sample_food_page):
        """测试食物属性解析"""
        recipe = parser.parse_food_recipe(sample_food_page)

        assert "饥饿:62.5" in recipe.notes
        assert "理智:5" in recipe.notes
        assert "生命:3" in recipe.notes

    def test_parse_food_recipe_ingredients(self, parser, sample_food_page):
        """测试材料提取"""
        recipe = parser.parse_food_recipe(sample_food_page)

        # 检查是否提取了材料
        assert isinstance(recipe.ingredients, list)

    def test_parse_food_recipe_version(self, parser, sample_food_page):
        """测试版本信息"""
        recipe = parser.parse_food_recipe(sample_food_page)

        assert recipe.version == GameVersion.BOTH

    def test_parse_food_recipe_no_infobox(self, parser):
        """测试无信息框的食物页面"""
        page = WikiPage(
            page_id=1002,
            title="测试食物",
            url="https://wiki.example.com/测试",
            content="这是测试食物",
            html_content="<html><body><p>无信息框</p></body></html>",
            entity_type=EntityType.FOOD
        )
        recipe = parser.parse_food_recipe(page)

        assert recipe is not None
        assert recipe.name == "测试食物"


class TestParseCreature:
    """测试生物解析"""

    def test_parse_creature_basic(self, parser, sample_creature_page):
        """测试基本生物解析"""
        entity = parser.parse_creature(sample_creature_page)

        assert entity is not None
        assert entity.name == "蜘蛛"
        assert entity.entity_type == EntityType.CREATURE

    def test_parse_creature_stats(self, parser, sample_creature_page):
        """测试生物属性解析"""
        entity = parser.parse_creature(sample_creature_page)

        assert entity.health == 100
        assert entity.damage == 20
        assert entity.attack_period == 3.0
        assert entity.walk_speed == 3.0

    def test_parse_creature_drops(self, parser, sample_creature_page):
        """测试掉落物解析"""
        entity = parser.parse_creature(sample_creature_page)

        assert len(entity.drops) > 0
        assert "蜘蛛网" in entity.drops[0]["raw"]

    def test_parse_creature_description(self, parser, sample_creature_page):
        """测试描述截取"""
        entity = parser.parse_creature(sample_creature_page)

        assert entity.description is not None
        assert len(entity.description) <= 500

    def test_parse_boss(self, parser, sample_boss_page):
        """测试Boss解析"""
        entity = parser.parse_creature(sample_boss_page)

        assert entity is not None
        assert entity.name == "蜘蛛女皇"
        assert entity.entity_type == EntityType.BOSS
        assert entity.health == 1250
        assert entity.damage == 80

    def test_parse_creature_wiki_url(self, parser, sample_creature_page):
        """测试Wiki URL"""
        entity = parser.parse_creature(sample_creature_page)

        assert entity.wiki_url == "https://wiki.example.com/蜘蛛"


class TestExtractNumber:
    """测试数字提取"""

    def test_extract_number_integer(self, parser):
        """测试整数提取"""
        assert parser._extract_number("100") == 100.0
        assert parser._extract_number("生命值: 100") == 100.0

    def test_extract_number_float(self, parser):
        """测试浮点数提取"""
        assert parser._extract_number("3.5") == 3.5
        assert parser._extract_number("移动速度: 6.0") == 6.0

    def test_extract_number_negative(self, parser):
        """测试负数提取"""
        assert parser._extract_number("-10") == -10.0
        assert parser._extract_number("理智: -5") == -5.0

    def test_extract_number_with_unit(self, parser):
        """测试带单位的数字"""
        assert parser._extract_number("15秒") == 15.0
        assert parser._extract_number("100点") == 100.0

    def test_extract_number_empty(self, parser):
        """测试空字符串"""
        assert parser._extract_number("") is None
        assert parser._extract_number(None) is None

    def test_extract_number_no_number(self, parser):
        """测试无数字文本"""
        assert parser._extract_number("没有数字") is None


class TestCleanText:
    """测试文本清理"""

    def test_clean_text_whitespace(self, parser):
        """测试空白字符清理"""
        text = "  多个   空格  "
        result = parser.clean_text(text)
        assert result == "多个 空格"

    def test_clean_text_wiki_links(self, parser):
        """测试Wiki链接清理"""
        text = "这是[[链接]]文本"
        result = parser.clean_text(text)
        assert "[[" not in result
        assert "]]" not in result

    def test_clean_text_wiki_templates(self, parser):
        """测试Wiki模板清理"""
        text = "这是{{模板|参数}}文本"
        result = parser.clean_text(text)
        assert "{{" not in result
        assert "}}" not in result

    def test_clean_text_newlines(self, parser):
        """测试换行符清理"""
        text = "行1\n\n行2\t行3"
        result = parser.clean_text(text)
        assert "\n" not in result
        assert "\t" not in result

    def test_clean_text_empty(self, parser):
        """测试空字符串"""
        assert parser.clean_text("") == ""
        assert parser.clean_text("   ") == ""


class TestParsePage:
    """测试完整页面解析"""

    def test_parse_page_food(self, parser, sample_food_page):
        """测试食物页面解析"""
        result = parser.parse_page(sample_food_page)

        assert "page" in result
        assert "sections" in result
        assert "tables" in result
        assert "infobox" in result
        assert "recipe" in result
        assert result["page"] == sample_food_page

    def test_parse_page_creature(self, parser, sample_creature_page):
        """测试生物页面解析"""
        result = parser.parse_page(sample_creature_page)

        assert "entity" in result
        assert result["entity"].name == "蜘蛛"

    def test_parse_page_boss(self, parser, sample_boss_page):
        """测试Boss页面解析"""
        result = parser.parse_page(sample_boss_page)

        assert "entity" in result
        assert result["entity"].entity_type == EntityType.BOSS

    def test_parse_page_other_type(self, parser):
        """测试其他类型页面解析"""
        page = WikiPage(
            page_id=4001,
            title="测试建筑",
            url="https://wiki.example.com/测试建筑",
            content="这是一个建筑",
            html_content="<html><body><p>建筑内容</p></body></html>",
            entity_type=EntityType.STRUCTURE
        )
        result = parser.parse_page(page)

        # 其他类型不应有recipe或entity
        assert "recipe" not in result
        assert "entity" not in result


class TestEdgeCases:
    """边界情况测试"""

    def test_malformed_html(self, parser):
        """测试畸形HTML"""
        html = "<html><body><table><tr><td>未闭合"
        # 不应抛出异常
        sections = parser.extract_sections(html)
        tables = parser.extract_tables(html)
        infobox = parser.extract_infobox(html)

        assert isinstance(sections, list)
        assert isinstance(tables, list)
        assert isinstance(infobox, dict)

    def test_unicode_content(self, parser):
        """测试Unicode内容"""
        html = """
        <html><body>
            <h2>中文标题</h2>
            <p>包含特殊字符：饥饿值♥100</p>
            <table class="infobox">
                <tr><th>属性</th><td>值→100</td></tr>
            </table>
        </body></html>
        """
        sections = parser.extract_sections(html)
        infobox = parser.extract_infobox(html)

        assert len(sections) > 0
        assert "属性" in infobox

    def test_deeply_nested_html(self, parser):
        """测试深度嵌套HTML"""
        html = """
        <html><body>
            <div><div><div>
                <table class="infobox">
                    <tr><th>深层</th><td>值</td></tr>
                </table>
            </div></div></div>
        </body></html>
        """
        infobox = parser.extract_infobox(html)
        assert "深层" in infobox

    def test_empty_cells(self, parser):
        """测试空单元格"""
        html = """
        <html><body>
            <table>
                <tr><td></td><td>值</td></tr>
                <tr><td>键</td><td></td></tr>
            </table>
        </body></html>
        """
        tables = parser.extract_tables(html)
        assert len(tables) == 1

    def test_very_long_content(self, parser):
        """测试超长内容"""
        long_text = "a" * 10000
        html = f"<html><body><p>{long_text}</p></body></html>"
        sections = parser.extract_sections(html)

        assert len(sections) > 0
        assert len(sections[0]["content"]) > 0
