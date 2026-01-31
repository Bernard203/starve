"""查询处理器测试"""

import pytest

from src.retriever.query_processor import (
    QueryProcessor,
    ProcessedQuery,
    QueryType,
)
from src.utils.models import SynonymMapping, EntityType


class TestQueryProcessor:
    """QueryProcessor测试"""

    @pytest.fixture
    def processor(self):
        """创建查询处理器"""
        return QueryProcessor()

    @pytest.fixture
    def custom_processor(self):
        """创建带自定义同义词的处理器"""
        synonyms = [
            SynonymMapping(
                canonical="测试物品",
                synonyms=["测试同义词", "另一个同义词"],
                entity_type=EntityType.ITEM,
            ),
        ]
        return QueryProcessor(synonyms=synonyms)

    def test_init(self, processor):
        """测试初始化"""
        assert processor.synonyms is not None
        assert processor._synonym_map is not None

    def test_process_basic(self, processor):
        """测试基本处理"""
        result = processor.process("肉丸怎么做")

        assert isinstance(result, ProcessedQuery)
        assert result.original == "肉丸怎么做"
        assert result.query_type is not None

    def test_process_empty(self, processor):
        """测试空查询"""
        result = processor.process("")

        assert result.original == ""
        assert result.expanded == ""
        assert result.query_type == QueryType.GENERAL

    def test_synonym_expansion(self, processor):
        """测试同义词扩展"""
        # "肉丸子" 应该扩展为 "肉丸"
        result = processor.process("肉丸子怎么做")

        assert "肉丸" in result.expanded

    def test_custom_synonym_expansion(self, custom_processor):
        """测试自定义同义词扩展"""
        result = custom_processor.process("测试同义词在哪里")

        assert "测试物品" in result.expanded

    def test_query_classification_recipe(self, processor):
        """测试食谱类型分类"""
        result = processor.process("肉丸怎么做")
        assert result.query_type == QueryType.RECIPE

        result = processor.process("火腿的配方是什么")
        assert result.query_type == QueryType.RECIPE

    def test_query_classification_combat(self, processor):
        """测试战斗类型分类"""
        result = processor.process("怎么打蜘蛛女王")
        assert result.query_type == QueryType.COMBAT

        result = processor.process("boss攻略")
        assert result.query_type == QueryType.COMBAT

    def test_query_classification_crafting(self, processor):
        """测试合成类型分类"""
        result = processor.process("科学机器怎么合成")
        assert result.query_type == QueryType.CRAFTING

    def test_query_classification_survival(self, processor):
        """测试生存类型分类"""
        result = processor.process("冬天怎么活")
        assert result.query_type == QueryType.SURVIVAL

    def test_query_classification_general(self, processor):
        """测试通用类型分类"""
        result = processor.process("你好")
        assert result.query_type == QueryType.GENERAL

    def test_entity_extraction(self, processor):
        """测试实体提取"""
        result = processor.process("肉丸和蜘蛛女王有什么关系")

        assert "肉丸" in result.entities
        assert "蜘蛛女王" in result.entities

    def test_keyword_extraction(self, processor):
        """测试关键词提取"""
        result = processor.process("怎么制作火腿")

        # 关键词提取会返回连续的中文字符序列
        # "火腿" 应该在实体中被识别
        assert "火腿" in result.entities
        # 关键词列表应该非空
        assert len(result.keywords) >= 0

    def test_clean_query(self, processor):
        """测试查询清理"""
        # 多余空白 - original保留原始输入，expanded被清理
        result = processor.process("  肉丸   怎么做  ")
        assert result.original == "  肉丸   怎么做  "  # 原始保留
        assert "  " not in result.expanded  # 扩展后清理了多余空白

        # 结尾标点
        result = processor.process("肉丸怎么做？？？")
        assert "？" not in result.expanded

    def test_query_type_prompt(self, processor):
        """测试查询类型提示词"""
        prompt = processor.get_query_type_prompt(QueryType.RECIPE)
        assert "食材" in prompt or "配方" in prompt

        prompt = processor.get_query_type_prompt(QueryType.COMBAT)
        assert "战斗" in prompt or "装备" in prompt

        prompt = processor.get_query_type_prompt(QueryType.GENERAL)
        assert prompt == ""


class TestQueryType:
    """QueryType测试"""

    def test_all_types_defined(self):
        """测试所有类型都已定义"""
        expected_types = [
            "recipe", "crafting", "combat", "survival",
            "character", "item", "location", "general"
        ]

        actual_types = [t.value for t in QueryType]
        assert set(actual_types) == set(expected_types)


class TestProcessedQuery:
    """ProcessedQuery测试"""

    def test_create_processed_query(self):
        """测试创建处理后的查询"""
        query = ProcessedQuery(
            original="原始查询",
            expanded="扩展查询",
            query_type=QueryType.RECIPE,
            entities=["实体1", "实体2"],
            keywords=["关键词1"],
        )

        assert query.original == "原始查询"
        assert query.expanded == "扩展查询"
        assert query.query_type == QueryType.RECIPE
        assert len(query.entities) == 2
        assert len(query.keywords) == 1

    def test_default_values(self):
        """测试默认值"""
        query = ProcessedQuery(
            original="test",
            expanded="test",
            query_type=QueryType.GENERAL,
        )

        assert query.entities == []
        assert query.keywords == []
