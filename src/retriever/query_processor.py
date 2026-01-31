"""查询处理器

提供查询预处理、分类、实体识别和同义词扩展
"""

import re
from enum import Enum
from typing import Optional
from dataclasses import dataclass, field

from src.utils.models import DEFAULT_SYNONYMS, SynonymMapping
from src.utils.logger import logger


class QueryType(Enum):
    """查询类型"""
    RECIPE = "recipe"           # 食谱/烹饪相关
    CRAFTING = "crafting"       # 合成/制作相关
    COMBAT = "combat"           # 战斗/Boss相关
    SURVIVAL = "survival"       # 生存技巧相关
    CHARACTER = "character"     # 角色相关
    ITEM = "item"               # 物品属性相关
    LOCATION = "location"       # 地点/生物群系相关
    GENERAL = "general"         # 通用问题


@dataclass
class ProcessedQuery:
    """处理后的查询"""
    original: str                           # 原始查询
    expanded: str                           # 扩展后的查询
    query_type: QueryType                   # 查询类型
    entities: list[str] = field(default_factory=list)  # 识别的实体
    keywords: list[str] = field(default_factory=list)  # 关键词


class QueryProcessor:
    """查询预处理器"""

    # 查询类型关键词映射
    TYPE_KEYWORDS = {
        QueryType.RECIPE: [
            "怎么做", "食谱", "烹饪", "煮", "烤", "炸",
            "配方", "材料", "锅", "料理", "食物",
            "饥饿", "血量", "理智", "恢复",
        ],
        QueryType.CRAFTING: [
            "怎么合成", "合成", "制作", "建造", "解锁",
            "需要什么", "科学机器", "炼金", "魔法",
            "配方", "材料", "制造",
        ],
        QueryType.COMBAT: [
            "怎么打", "攻击", "伤害", "血量", "boss",
            "击杀", "战斗", "打法", "攻略",
            "武器", "护甲", "防御",
        ],
        QueryType.SURVIVAL: [
            "怎么活", "生存", "过冬", "夏天", "春天", "秋天",
            "季节", "温度", "食物", "保暖", "降温",
            "新手", "技巧", "攻略",
        ],
        QueryType.CHARACTER: [
            "角色", "人物", "技能", "能力", "特性",
            "威尔逊", "薇洛", "沃尔夫冈", "温蒂",
        ],
        QueryType.ITEM: [
            "什么是", "有什么用", "属性", "效果", "作用",
            "在哪", "哪里", "获取", "掉落",
        ],
        QueryType.LOCATION: [
            "地图", "地点", "生物群系", "洞穴", "遗迹",
            "沼泽", "森林", "草原", "沙漠",
        ],
    }

    # 游戏实体关键词（用于实体识别）
    GAME_ENTITIES = [
        # 食物
        "肉丸", "火腿", "培根", "蜜汁火腿", "火龙果派",
        "鱼排", "饺子", "太妃糖", "曼德拉草汤",
        # Boss
        "蜘蛛女王", "独眼巨鹿", "熊獾", "龙蝇",
        "远古守护者", "暗影骑士", "蚁狮",
        # 物品
        "背包", "猪皮包", "冰箱", "灭火器",
        "矛", "火把", "铲子", "斧头", "镐",
        # 结构
        "烹饪锅", "科学机器", "炼金引擎",
        "晾肉架", "蜂箱", "农场",
        # 角色
        "威尔逊", "薇洛", "沃尔夫冈", "温蒂", "WX-78",
        "麦克斯韦", "薇格弗德", "韦伯",
    ]

    def __init__(self, synonyms: Optional[list[SynonymMapping]] = None):
        """初始化查询处理器

        Args:
            synonyms: 同义词映射列表
        """
        self.synonyms = synonyms or DEFAULT_SYNONYMS
        self._synonym_map = self._build_synonym_map()

    def _build_synonym_map(self) -> dict[str, str]:
        """构建同义词映射字典"""
        mapping = {}
        for item in self.synonyms:
            for synonym in item.synonyms:
                mapping[synonym.lower()] = item.canonical
        return mapping

    def process(self, query: str) -> ProcessedQuery:
        """处理查询

        Args:
            query: 原始查询文本

        Returns:
            处理后的查询对象
        """
        if not query:
            return ProcessedQuery(
                original="",
                expanded="",
                query_type=QueryType.GENERAL,
            )

        # 1. 清理查询
        cleaned = self._clean_query(query)

        # 2. 同义词扩展
        expanded = self._expand_synonyms(cleaned)

        # 3. 分类查询
        query_type = self._classify_query(cleaned)

        # 4. 提取实体
        entities = self._extract_entities(cleaned)

        # 5. 提取关键词
        keywords = self._extract_keywords(cleaned)

        result = ProcessedQuery(
            original=query,
            expanded=expanded,
            query_type=query_type,
            entities=entities,
            keywords=keywords,
        )

        logger.debug(f"查询处理: '{query}' -> type={query_type.value}, entities={entities}")

        return result

    def _clean_query(self, query: str) -> str:
        """清理查询文本"""
        # 去除多余空白
        query = re.sub(r'\s+', ' ', query.strip())

        # 去除无意义的问号和标点
        query = re.sub(r'[？?!！。.]+$', '', query)

        return query

    def _expand_synonyms(self, query: str) -> str:
        """同义词扩展"""
        expanded = query
        query_lower = query.lower()

        for synonym, canonical in self._synonym_map.items():
            if synonym in query_lower:
                # 使用正则替换，保留大小写
                pattern = re.compile(re.escape(synonym), re.IGNORECASE)
                expanded = pattern.sub(canonical, expanded)
                logger.debug(f"同义词替换: {synonym} -> {canonical}")

        return expanded

    def _classify_query(self, query: str) -> QueryType:
        """分类查询类型"""
        query_lower = query.lower()

        # 计算每个类型的匹配分数
        type_scores = {}
        for qtype, keywords in self.TYPE_KEYWORDS.items():
            score = sum(1 for kw in keywords if kw in query_lower)
            if score > 0:
                type_scores[qtype] = score

        if not type_scores:
            return QueryType.GENERAL

        # 返回分数最高的类型
        return max(type_scores, key=type_scores.get)

    def _extract_entities(self, query: str) -> list[str]:
        """提取游戏实体"""
        entities = []
        query_lower = query.lower()

        for entity in self.GAME_ENTITIES:
            if entity.lower() in query_lower:
                entities.append(entity)

        # 也从同义词映射中提取
        for synonym, canonical in self._synonym_map.items():
            if synonym in query_lower and canonical not in entities:
                entities.append(canonical)

        return entities

    def _extract_keywords(self, query: str) -> list[str]:
        """提取关键词"""
        # 简单分词
        words = re.findall(r'[\u4e00-\u9fff]+|[a-zA-Z]+', query)

        # 过滤停用词
        stopwords = {'的', '是', '在', '有', '和', '了', '不', '吗', '呢', '怎么', '什么', '如何'}
        keywords = [w for w in words if w not in stopwords and len(w) > 1]

        return keywords

    def get_query_type_prompt(self, query_type: QueryType) -> str:
        """获取查询类型对应的提示词补充

        Args:
            query_type: 查询类型

        Returns:
            额外的提示词
        """
        prompts = {
            QueryType.RECIPE: "请重点说明食材配方、数值效果和烹饪技巧。",
            QueryType.CRAFTING: "请说明所需材料、解锁条件和制作步骤。",
            QueryType.COMBAT: "请说明战斗技巧、推荐装备和注意事项。",
            QueryType.SURVIVAL: "请说明生存策略、时间规划和资源管理。",
            QueryType.CHARACTER: "请说明角色特性、优缺点和玩法建议。",
            QueryType.ITEM: "请说明物品属性、获取方式和使用场景。",
            QueryType.LOCATION: "请说明地点特征、资源分布和探索建议。",
            QueryType.GENERAL: "",
        }
        return prompts.get(query_type, "")
