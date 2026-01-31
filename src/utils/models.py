"""数据模型定义"""

from datetime import datetime
from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field


class GameVersion(str, Enum):
    """游戏版本"""
    DS = "ds"  # 单机版 Don't Starve
    DST = "dst"  # 联机版 Don't Starve Together
    ROG = "rog"  # DLC: Reign of Giants
    SW = "sw"  # DLC: Shipwrecked
    HAM = "ham"  # DLC: Hamlet
    BOTH = "both"  # 通用


class EntityType(str, Enum):
    """实体类型"""
    ITEM = "item"  # 物品
    FOOD = "food"  # 食物
    CREATURE = "creature"  # 生物
    CHARACTER = "character"  # 角色
    STRUCTURE = "structure"  # 建筑
    RECIPE = "recipe"  # 配方
    BIOME = "biome"  # 生物群系
    SEASON = "season"  # 季节
    BOSS = "boss"  # Boss
    MOD = "mod"  # Mod相关
    OTHER = "other"  # 其他


class WikiPage(BaseModel):
    """Wiki页面数据模型"""

    page_id: int = Field(..., description="页面ID")
    title: str = Field(..., description="页面标题")
    url: str = Field(..., description="页面URL")
    content: str = Field(default="", description="页面内容(纯文本)")
    html_content: str = Field(default="", description="原始HTML内容")
    categories: list[str] = Field(default_factory=list, description="所属分类")
    version: GameVersion = Field(default=GameVersion.BOTH, description="适用游戏版本")
    entity_type: EntityType = Field(default=EntityType.OTHER, description="实体类型")
    last_modified: Optional[datetime] = Field(default=None, description="最后修改时间")
    crawled_at: datetime = Field(default_factory=datetime.now, description="爬取时间")

    class Config:
        use_enum_values = True


class Recipe(BaseModel):
    """烹饪/合成配方模型"""

    name: str = Field(..., description="配方名称")
    name_en: Optional[str] = Field(default=None, description="英文名称")
    recipe_type: str = Field(default="cooking", description="配方类型: cooking/crafting")
    ingredients: list[dict] = Field(default_factory=list, description="材料列表")
    result: str = Field(..., description="产出物品")
    result_count: int = Field(default=1, description="产出数量")
    cook_time: Optional[float] = Field(default=None, description="烹饪时间(秒)")
    priority: Optional[int] = Field(default=None, description="配方优先级")
    requirements: Optional[str] = Field(default=None, description="制作要求(科技/建筑)")
    version: GameVersion = Field(default=GameVersion.BOTH, description="适用版本")
    notes: Optional[str] = Field(default=None, description="备注")

    class Config:
        use_enum_values = True


class GameEntity(BaseModel):
    """游戏实体通用模型(生物、物品等)"""

    name: str = Field(..., description="实体名称")
    name_en: Optional[str] = Field(default=None, description="英文名称")
    entity_type: EntityType = Field(..., description="实体类型")
    description: Optional[str] = Field(default=None, description="描述")

    # 数值属性
    health: Optional[float] = Field(default=None, description="生命值")
    damage: Optional[float] = Field(default=None, description="伤害")
    attack_period: Optional[float] = Field(default=None, description="攻击间隔")
    walk_speed: Optional[float] = Field(default=None, description="移动速度")

    # 食物属性
    hunger: Optional[float] = Field(default=None, description="饥饿值")
    sanity: Optional[float] = Field(default=None, description="理智值")
    health_restore: Optional[float] = Field(default=None, description="恢复生命值")
    perish_time: Optional[float] = Field(default=None, description="腐烂时间(天)")

    # 其他属性
    stackable: Optional[int] = Field(default=None, description="可堆叠数量")
    flammable: Optional[bool] = Field(default=None, description="是否可燃")

    # 关联信息
    drops: list[dict] = Field(default_factory=list, description="掉落物")
    spawn_locations: list[str] = Field(default_factory=list, description="出现地点")
    related_items: list[str] = Field(default_factory=list, description="相关物品")

    version: GameVersion = Field(default=GameVersion.BOTH, description="适用版本")
    wiki_url: Optional[str] = Field(default=None, description="Wiki链接")

    class Config:
        use_enum_values = True


class Document(BaseModel):
    """RAG文档模型"""

    doc_id: str = Field(..., description="文档ID")
    content: str = Field(..., description="文档内容")
    metadata: dict = Field(default_factory=dict, description="元数据")

    # 来源信息
    source_type: str = Field(default="wiki", description="来源类型")
    source_url: Optional[str] = Field(default=None, description="来源URL")
    source_title: Optional[str] = Field(default=None, description="来源标题")

    # 分块信息
    chunk_index: int = Field(default=0, description="分块索引")
    total_chunks: int = Field(default=1, description="总分块数")

    # 嵌入向量
    embedding: Optional[list[float]] = Field(default=None, description="向量嵌入")

    class Config:
        arbitrary_types_allowed = True


class SynonymMapping(BaseModel):
    """同义词映射"""

    canonical: str = Field(..., description="标准名称")
    synonyms: list[str] = Field(default_factory=list, description="同义词列表")
    entity_type: EntityType = Field(default=EntityType.OTHER, description="实体类型")


# 预定义的同义词映射
DEFAULT_SYNONYMS: list[SynonymMapping] = [
    SynonymMapping(
        canonical="肉丸",
        synonyms=["蒸肉丸", "肉丸子", "meatballs"],
        entity_type=EntityType.FOOD
    ),
    SynonymMapping(
        canonical="蜘蛛女皇",
        synonyms=["蜘蛛女王", "蜘蛛boss", "spider queen"],
        entity_type=EntityType.BOSS
    ),
    SynonymMapping(
        canonical="烹饪锅",
        synonyms=["锅", "cooking pot", "crock pot"],
        entity_type=EntityType.STRUCTURE
    ),
]
