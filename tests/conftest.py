"""pytest配置和通用fixtures"""

import pytest
from pathlib import Path
import json
import tempfile

from src.utils.models import WikiPage, Document, GameVersion, EntityType


@pytest.fixture
def sample_wiki_page() -> WikiPage:
    """示例Wiki页面"""
    return WikiPage(
        page_id=12345,
        title="肉丸",
        url="https://dontstarve.wiki.gg/zh/肉丸",
        content="""肉丸是一种可以用烹饪锅制作的食物。

制作配方：
- 肉度 >= 0.5
- 不能有蔬菜度
- 烹饪时间: 15秒

属性:
- 饥饿值: +62.5
- 理智值: +5
- 生命值: +3

肉丸是新手最常用的食物之一，因为配方简单且饥饿恢复量大。""",
        html_content="<div>...</div>",
        categories=["食物", "烹饪锅食谱"],
        version=GameVersion.BOTH,
        entity_type=EntityType.FOOD,
    )


@pytest.fixture
def sample_boss_page() -> WikiPage:
    """示例Boss页面"""
    return WikiPage(
        page_id=54321,
        title="蜘蛛女皇",
        url="https://dontstarve.wiki.gg/zh/蜘蛛女皇",
        content="""蜘蛛女皇是一种Boss级别的生物。

属性：
- 生命值: 2500
- 伤害: 80
- 攻击间隔: 3秒

掉落物：
- 蜘蛛帽（100%）
- 蜘蛛卵（1个）
- 怪物肉（4-8个）

战斗策略：
蜘蛛女皇会召唤小蜘蛛，建议先清理小蜘蛛再攻击女皇。""",
        html_content="<div>...</div>",
        categories=["Boss", "生物"],
        version=GameVersion.BOTH,
        entity_type=EntityType.BOSS,
    )


@pytest.fixture
def sample_documents(sample_wiki_page: WikiPage) -> list[Document]:
    """示例文档列表"""
    return [
        Document(
            doc_id="doc_001",
            content="肉丸是一种可以用烹饪锅制作的食物。制作配方：肉度 >= 0.5，不能有蔬菜度。",
            metadata={
                "page_id": 12345,
                "title": "肉丸",
                "entity_type": "food",
                "version": "both",
            },
            source_url="https://dontstarve.wiki.gg/zh/肉丸",
            source_title="肉丸",
            chunk_index=0,
            total_chunks=2,
        ),
        Document(
            doc_id="doc_002",
            content="肉丸属性: 饥饿值+62.5，理智值+5，生命值+3。是新手最常用的食物之一。",
            metadata={
                "page_id": 12345,
                "title": "肉丸",
                "entity_type": "food",
                "version": "both",
            },
            source_url="https://dontstarve.wiki.gg/zh/肉丸",
            source_title="肉丸",
            chunk_index=1,
            total_chunks=2,
        ),
    ]


@pytest.fixture
def temp_data_dir():
    """临时数据目录"""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield Path(tmpdir)


@pytest.fixture
def sample_wiki_pages_file(temp_data_dir: Path, sample_wiki_page: WikiPage) -> Path:
    """示例Wiki页面JSON文件"""
    file_path = temp_data_dir / "wiki_pages.json"
    with open(file_path, "w", encoding="utf-8") as f:
        json.dump([sample_wiki_page.model_dump()], f, ensure_ascii=False, default=str)
    return file_path
