"""数据模型单元测试"""

import pytest
from datetime import datetime
from pydantic import ValidationError

from src.utils.models import (
    GameVersion,
    EntityType,
    WikiPage,
    Recipe,
    GameEntity,
    Document,
    SynonymMapping,
    DEFAULT_SYNONYMS,
)


class TestGameVersion:
    """游戏版本枚举测试"""

    def test_all_versions_defined(self):
        """测试所有版本定义"""
        versions = list(GameVersion)
        assert len(versions) == 6
        assert GameVersion.DS in versions
        assert GameVersion.DST in versions
        assert GameVersion.ROG in versions
        assert GameVersion.SW in versions
        assert GameVersion.HAM in versions
        assert GameVersion.BOTH in versions

    def test_version_values(self):
        """测试版本值"""
        assert GameVersion.DS.value == "ds"
        assert GameVersion.DST.value == "dst"
        assert GameVersion.ROG.value == "rog"
        assert GameVersion.SW.value == "sw"
        assert GameVersion.HAM.value == "ham"
        assert GameVersion.BOTH.value == "both"

    def test_version_from_string(self):
        """测试从字符串创建版本"""
        assert GameVersion("ds") == GameVersion.DS
        assert GameVersion("dst") == GameVersion.DST

    def test_invalid_version(self):
        """测试无效版本"""
        with pytest.raises(ValueError):
            GameVersion("invalid")


class TestEntityType:
    """实体类型枚举测试"""

    def test_all_types_defined(self):
        """测试所有类型定义"""
        types = list(EntityType)
        assert len(types) == 11

    def test_type_values(self):
        """测试类型值"""
        assert EntityType.ITEM.value == "item"
        assert EntityType.FOOD.value == "food"
        assert EntityType.CREATURE.value == "creature"
        assert EntityType.CHARACTER.value == "character"
        assert EntityType.STRUCTURE.value == "structure"
        assert EntityType.RECIPE.value == "recipe"
        assert EntityType.BIOME.value == "biome"
        assert EntityType.SEASON.value == "season"
        assert EntityType.BOSS.value == "boss"
        assert EntityType.MOD.value == "mod"
        assert EntityType.OTHER.value == "other"


class TestWikiPage:
    """WikiPage模型测试"""

    def test_create_wiki_page(self):
        """测试创建WikiPage"""
        page = WikiPage(
            page_id=12345,
            title="肉丸",
            url="https://wiki.example.com/肉丸"
        )
        assert page.page_id == 12345
        assert page.title == "肉丸"
        assert page.url == "https://wiki.example.com/肉丸"

    def test_wiki_page_default_values(self):
        """测试默认值"""
        page = WikiPage(
            page_id=1,
            title="测试",
            url="https://test.com"
        )
        assert page.content == ""
        assert page.html_content == ""
        assert page.categories == []
        assert page.version == GameVersion.BOTH
        assert page.entity_type == EntityType.OTHER
        assert page.last_modified is None
        assert page.crawled_at is not None

    def test_wiki_page_with_all_fields(self):
        """测试所有字段"""
        now = datetime.now()
        page = WikiPage(
            page_id=100,
            title="完整页面",
            url="https://wiki.example.com/test",
            content="纯文本内容",
            html_content="<p>HTML内容</p>",
            categories=["食物", "烹饪"],
            version=GameVersion.DST,
            entity_type=EntityType.FOOD,
            last_modified=now,
            crawled_at=now,
        )
        assert page.content == "纯文本内容"
        assert page.html_content == "<p>HTML内容</p>"
        assert page.categories == ["食物", "烹饪"]
        assert page.version == GameVersion.DST
        assert page.entity_type == EntityType.FOOD

    def test_wiki_page_required_fields(self):
        """测试必填字段"""
        with pytest.raises(ValidationError):
            WikiPage(title="缺少page_id和url")

    def test_wiki_page_enum_serialization(self):
        """测试枚举序列化（use_enum_values=True）"""
        page = WikiPage(
            page_id=1,
            title="测试",
            url="https://test.com",
            version=GameVersion.DST,
            entity_type=EntityType.FOOD,
        )
        data = page.model_dump()
        # 由于use_enum_values=True，枚举应该序列化为字符串值
        assert data["version"] == "dst"
        assert data["entity_type"] == "food"


class TestRecipe:
    """Recipe模型测试"""

    def test_create_recipe(self):
        """测试创建Recipe"""
        recipe = Recipe(
            name="肉丸",
            result="肉丸",
        )
        assert recipe.name == "肉丸"
        assert recipe.result == "肉丸"

    def test_recipe_default_values(self):
        """测试默认值"""
        recipe = Recipe(name="测试", result="结果")
        assert recipe.name_en is None
        assert recipe.recipe_type == "cooking"
        assert recipe.ingredients == []
        assert recipe.result_count == 1
        assert recipe.cook_time is None
        assert recipe.priority is None
        assert recipe.requirements is None
        assert recipe.version == GameVersion.BOTH
        assert recipe.notes is None

    def test_recipe_with_all_fields(self):
        """测试所有字段"""
        recipe = Recipe(
            name="肉丸",
            name_en="Meatballs",
            recipe_type="cooking",
            ingredients=[{"item": "肉", "count": 1}],
            result="肉丸",
            result_count=1,
            cook_time=15.0,
            priority=1,
            requirements="烹饪锅",
            version=GameVersion.BOTH,
            notes="简单的食物",
        )
        assert recipe.name_en == "Meatballs"
        assert recipe.cook_time == 15.0
        assert len(recipe.ingredients) == 1


class TestGameEntity:
    """GameEntity模型测试"""

    def test_create_entity(self):
        """测试创建GameEntity"""
        entity = GameEntity(
            name="蜘蛛",
            entity_type=EntityType.CREATURE,
        )
        assert entity.name == "蜘蛛"
        assert entity.entity_type == EntityType.CREATURE

    def test_entity_default_values(self):
        """测试默认值"""
        entity = GameEntity(
            name="测试",
            entity_type=EntityType.ITEM,
        )
        assert entity.name_en is None
        assert entity.description is None
        assert entity.health is None
        assert entity.damage is None
        assert entity.attack_period is None
        assert entity.walk_speed is None
        assert entity.hunger is None
        assert entity.sanity is None
        assert entity.health_restore is None
        assert entity.perish_time is None
        assert entity.stackable is None
        assert entity.flammable is None
        assert entity.drops == []
        assert entity.spawn_locations == []
        assert entity.related_items == []
        assert entity.version == GameVersion.BOTH
        assert entity.wiki_url is None

    def test_entity_creature_stats(self):
        """测试生物属性"""
        entity = GameEntity(
            name="蜘蛛女皇",
            entity_type=EntityType.BOSS,
            health=1250,
            damage=80,
            attack_period=2.0,
            walk_speed=3.0,
            drops=[{"item": "蜘蛛帽", "count": 1}],
        )
        assert entity.health == 1250
        assert entity.damage == 80
        assert entity.attack_period == 2.0
        assert entity.walk_speed == 3.0
        assert len(entity.drops) == 1

    def test_entity_food_stats(self):
        """测试食物属性"""
        entity = GameEntity(
            name="肉丸",
            entity_type=EntityType.FOOD,
            hunger=62.5,
            sanity=5,
            health_restore=3,
            perish_time=10,
            stackable=40,
        )
        assert entity.hunger == 62.5
        assert entity.sanity == 5
        assert entity.health_restore == 3
        assert entity.perish_time == 10
        assert entity.stackable == 40


class TestDocument:
    """Document模型测试"""

    def test_create_document(self):
        """测试创建Document"""
        doc = Document(
            doc_id="doc-001",
            content="这是文档内容",
        )
        assert doc.doc_id == "doc-001"
        assert doc.content == "这是文档内容"

    def test_document_default_values(self):
        """测试默认值"""
        doc = Document(doc_id="1", content="内容")
        assert doc.metadata == {}
        assert doc.source_type == "wiki"
        assert doc.source_url is None
        assert doc.source_title is None
        assert doc.chunk_index == 0
        assert doc.total_chunks == 1
        assert doc.embedding is None

    def test_document_with_all_fields(self):
        """测试所有字段"""
        doc = Document(
            doc_id="doc-123",
            content="详细的文档内容",
            metadata={"key": "value"},
            source_type="tieba",
            source_url="https://tieba.baidu.com/p/123",
            source_title="帖子标题",
            chunk_index=2,
            total_chunks=5,
            embedding=[0.1, 0.2, 0.3],
        )
        assert doc.metadata == {"key": "value"}
        assert doc.source_type == "tieba"
        assert doc.source_url == "https://tieba.baidu.com/p/123"
        assert doc.chunk_index == 2
        assert doc.total_chunks == 5
        assert len(doc.embedding) == 3

    def test_document_embedding_list(self):
        """测试嵌入向量列表"""
        embedding = [0.1] * 384  # BGE模型维度
        doc = Document(
            doc_id="1",
            content="内容",
            embedding=embedding,
        )
        assert len(doc.embedding) == 384


class TestSynonymMapping:
    """SynonymMapping模型测试"""

    def test_create_synonym_mapping(self):
        """测试创建同义词映射"""
        mapping = SynonymMapping(
            canonical="肉丸",
            synonyms=["蒸肉丸", "肉丸子"],
            entity_type=EntityType.FOOD,
        )
        assert mapping.canonical == "肉丸"
        assert "蒸肉丸" in mapping.synonyms
        assert "肉丸子" in mapping.synonyms

    def test_synonym_mapping_default_values(self):
        """测试默认值"""
        mapping = SynonymMapping(canonical="测试")
        assert mapping.synonyms == []
        assert mapping.entity_type == EntityType.OTHER


class TestDefaultSynonyms:
    """默认同义词列表测试"""

    def test_default_synonyms_not_empty(self):
        """测试默认同义词列表非空"""
        assert len(DEFAULT_SYNONYMS) > 0

    def test_default_synonyms_structure(self):
        """测试默认同义词结构"""
        for mapping in DEFAULT_SYNONYMS:
            assert isinstance(mapping, SynonymMapping)
            assert mapping.canonical is not None
            assert isinstance(mapping.synonyms, list)

    def test_meatballs_synonym(self):
        """测试肉丸同义词"""
        meatballs = next(
            (m for m in DEFAULT_SYNONYMS if m.canonical == "肉丸"),
            None
        )
        assert meatballs is not None
        assert "蒸肉丸" in meatballs.synonyms
        assert "meatballs" in meatballs.synonyms

    def test_spider_queen_synonym(self):
        """测试蜘蛛女皇同义词"""
        spider_queen = next(
            (m for m in DEFAULT_SYNONYMS if m.canonical == "蜘蛛女皇"),
            None
        )
        assert spider_queen is not None
        assert spider_queen.entity_type == EntityType.BOSS


class TestModelValidation:
    """模型验证测试"""

    def test_wiki_page_title_required(self):
        """测试WikiPage标题必填"""
        with pytest.raises(ValidationError):
            WikiPage(page_id=1, url="https://test.com")

    def test_recipe_name_required(self):
        """测试Recipe名称必填"""
        with pytest.raises(ValidationError):
            Recipe(result="结果")

    def test_game_entity_type_required(self):
        """测试GameEntity类型必填"""
        with pytest.raises(ValidationError):
            GameEntity(name="测试")

    def test_document_content_required(self):
        """测试Document内容必填"""
        with pytest.raises(ValidationError):
            Document(doc_id="1")
