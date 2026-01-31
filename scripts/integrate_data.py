"""
数据集成脚本 - 将清洗后的数据导入向量索引
"""

import json
import argparse
import logging
from pathlib import Path
from typing import List, Generator

from config import settings, PROCESSED_DATA_DIR, VECTOR_DB_DIR
from src.utils.models import Document, WikiPage, EntityType, GameVersion

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


class DataIntegrator:
    """数据集成器 - 连接爬虫输出与RAG索引"""

    # 分类到实体类型映射
    CATEGORY_TO_TYPE = {
        '物品': EntityType.ITEM,
        '食物': EntityType.FOOD,
        '生物': EntityType.CREATURE,
        '角色': EntityType.CHARACTER,
        '建筑': EntityType.STRUCTURE,
        '合成': EntityType.RECIPE,
        '烹饪': EntityType.RECIPE,
        'Boss': EntityType.BOSS,
        '季节': EntityType.SEASON,
        '生物群系': EntityType.BIOME,
        '武器': EntityType.ITEM,
        '护甲': EntityType.ITEM,
        '工具': EntityType.ITEM,
    }

    # 版本映射
    VERSION_MAP = {
        'DS': GameVersion.DS,
        'DST': GameVersion.DST,
        'ROG': GameVersion.ROG,
        'SW': GameVersion.SW,
        'HAM': GameVersion.HAM,
    }

    def __init__(self):
        self.chunk_size = settings.embedding.chunk_size
        self.chunk_overlap = settings.embedding.chunk_overlap

    def load_cleaned_data(self, filename: str = "cleaned_pages.json") -> List[dict]:
        """加载清洗后的数据"""
        filepath = PROCESSED_DATA_DIR / filename
        if not filepath.exists():
            logger.error(f"文件不存在: {filepath}")
            return []

        with open(filepath, 'r', encoding='utf-8') as f:
            data = json.load(f)

        logger.info(f"加载 {len(data)} 个清洗后的页面")
        return data

    def convert_to_wiki_pages(self, cleaned_pages: List[dict]) -> List[WikiPage]:
        """将清洗数据转换为WikiPage对象"""
        wiki_pages = []

        for page in cleaned_pages:
            entity_type = self._detect_entity_type(page.get('categories', []))
            version = self.VERSION_MAP.get(page.get('game_version', 'DS'), GameVersion.BOTH)

            wiki_page = WikiPage(
                page_id=page.get('page_id') or hash(page['title']) % 1000000,
                title=page['title'],
                url=f"https://dontstarve.wiki.gg/zh/wiki/{page['title']}",
                content=page.get('content', ''),
                html_content='',  # 已清洗，不需要
                categories=page.get('categories', []),
                version=version,
                entity_type=entity_type,
            )
            wiki_pages.append(wiki_page)

        return wiki_pages

    def _detect_entity_type(self, categories: List[str]) -> EntityType:
        """根据分类检测实体类型"""
        for cat in categories:
            for keyword, entity_type in self.CATEGORY_TO_TYPE.items():
                if keyword in cat:
                    return entity_type
        return EntityType.OTHER

    def create_documents(self, cleaned_pages: List[dict]) -> Generator[Document, None, None]:
        """直接从清洗数据创建Document对象"""
        for page in cleaned_pages:
            title = page['title']
            content = page.get('content', '')
            summary = page.get('summary', '')
            infobox = page.get('infobox', {})
            stats = page.get('stats', {})
            recipes = page.get('recipes', [])
            version = page.get('game_version', 'DS')
            categories = page.get('categories', [])

            entity_type = self._detect_entity_type(categories)
            base_url = f"https://dontstarve.wiki.gg/zh/wiki/{title}"

            # 生成摘要文档
            if summary:
                yield Document(
                    doc_id=self._generate_id(title, 'summary'),
                    content=f"【{title}】{summary}",
                    metadata={
                        'doc_type': 'summary',
                        'entity_type': entity_type.value,
                        'version': version,
                        'categories': categories[:5],
                    },
                    source_type='wiki',
                    source_url=base_url,
                    source_title=title,
                    chunk_index=0,
                    total_chunks=1,
                )

            # 生成信息框文档
            if infobox or stats:
                combined = {**infobox, **stats}
                info_text = f"【{title}】属性信息：\n"
                info_text += '\n'.join(f"- {k}: {v}" for k, v in combined.items() if v)

                yield Document(
                    doc_id=self._generate_id(title, 'infobox'),
                    content=info_text,
                    metadata={
                        'doc_type': 'infobox',
                        'entity_type': entity_type.value,
                        'version': version,
                        'stats': stats,
                    },
                    source_type='wiki',
                    source_url=base_url,
                    source_title=title,
                    chunk_index=0,
                    total_chunks=1,
                )

            # 生成配方文档
            for i, recipe in enumerate(recipes):
                ingredients = recipe.get('ingredients', [])
                result = recipe.get('result', title)
                station = recipe.get('station', '')

                if ingredients:
                    recipe_text = f"【{result}】配方：\n"
                    recipe_text += f"材料: {', '.join(ingredients)}\n"
                    if station:
                        recipe_text += f"制作站: {station}"

                    yield Document(
                        doc_id=self._generate_id(title, f'recipe_{i}'),
                        content=recipe_text,
                        metadata={
                            'doc_type': 'recipe',
                            'entity_type': 'recipe',
                            'version': version,
                            'ingredients': ingredients,
                        },
                        source_type='wiki',
                        source_url=base_url,
                        source_title=title,
                        chunk_index=0,
                        total_chunks=1,
                    )

            # 生成正文分块
            if content:
                chunks = self._chunk_content(content, title)
                for i, chunk in enumerate(chunks):
                    yield Document(
                        doc_id=self._generate_id(title, f'content_{i}'),
                        content=chunk,
                        metadata={
                            'doc_type': 'content',
                            'entity_type': entity_type.value,
                            'version': version,
                            'categories': categories[:5],
                        },
                        source_type='wiki',
                        source_url=base_url,
                        source_title=title,
                        chunk_index=i,
                        total_chunks=len(chunks),
                    )

    def _chunk_content(self, content: str, title: str) -> List[str]:
        """分块内容"""
        if len(content) <= self.chunk_size:
            return [f"【{title}】\n{content}"]

        chunks = []
        sentences = self._split_sentences(content)

        current_chunk = f"【{title}】\n"
        current_len = len(current_chunk)

        for sentence in sentences:
            if current_len + len(sentence) > self.chunk_size:
                if current_chunk.strip():
                    chunks.append(current_chunk.strip())

                # 添加重叠
                overlap = current_chunk[-self.chunk_overlap:] if len(current_chunk) > self.chunk_overlap else ""
                current_chunk = f"【{title}(续)】\n{overlap}{sentence}"
                current_len = len(current_chunk)
            else:
                current_chunk += sentence
                current_len += len(sentence)

        if current_chunk.strip():
            chunks.append(current_chunk.strip())

        return chunks

    def _split_sentences(self, text: str) -> List[str]:
        """分割句子"""
        import re
        parts = re.split(r'([。！？\n])', text)
        sentences = []
        for i in range(0, len(parts) - 1, 2):
            sentence = parts[i] + (parts[i + 1] if i + 1 < len(parts) else '')
            if sentence.strip():
                sentences.append(sentence)
        return sentences

    def _generate_id(self, title: str, suffix: str) -> str:
        """生成文档ID"""
        import hashlib
        content = f"{title}_{suffix}"
        return hashlib.md5(content.encode()).hexdigest()[:16]

    def build_index(
        self,
        input_file: str = "cleaned_pages.json",
        collection_name: str = "starve_knowledge",
        clear_existing: bool = False
    ):
        """构建向量索引"""
        from src.indexer import VectorIndexer

        # 加载数据
        cleaned_pages = self.load_cleaned_data(input_file)
        if not cleaned_pages:
            logger.error("没有可用数据")
            return

        # 生成文档
        documents = list(self.create_documents(cleaned_pages))
        logger.info(f"生成 {len(documents)} 个文档块")

        # 创建索引
        indexer = VectorIndexer(collection_name=collection_name)

        if clear_existing:
            indexer.clear_collection()
            logger.info("已清空现有索引")

        # 索引文档
        index = indexer.index_documents(documents)

        # 统计
        stats = indexer.get_collection_stats()
        logger.info(f"索引完成: {stats}")

        return index


def main():
    parser = argparse.ArgumentParser(description='数据集成 - 导入清洗数据到向量索引')
    parser.add_argument('--input', type=str, default='cleaned_pages.json', help='输入文件')
    parser.add_argument('--collection', type=str, default='starve_knowledge', help='集合名称')
    parser.add_argument('--clear', action='store_true', help='清空现有索引')

    args = parser.parse_args()

    integrator = DataIntegrator()
    integrator.build_index(
        input_file=args.input,
        collection_name=args.collection,
        clear_existing=args.clear
    )


if __name__ == '__main__':
    main()
