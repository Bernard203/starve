"""爬取流水线 - 端到端数据处理"""

import json
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from typing import Dict, List, Optional

from config import settings, RAW_DATA_DIR, PROCESSED_DATA_DIR
from src.utils.logger import logger
from src.utils.models import WikiPage, GameVersion, EntityType

from .base import DataSource, RawPage
from .factory import CrawlerFactory, CleanerFactory
from .cleaners.base import CleanedPage
from .cleaners.quality import QualityAssessor


class CrawlPipeline:
    """爬取流水线 - 统一处理多数据源的爬取、清洗、转换"""

    def __init__(
        self,
        sources: Optional[List[DataSource]] = None,
        min_quality: float = 0.2
    ):
        """
        初始化流水线

        Args:
            sources: 要处理的数据源列表，None表示处理所有启用的数据源
            min_quality: 最低质量分数阈值
        """
        self.sources = sources or list(DataSource)
        self.min_quality = min_quality
        self.quality_assessor = QualityAssessor()

    def run(
        self,
        max_pages_per_source: int = 100,
        parallel: bool = False,
        save_intermediate: bool = True
    ) -> Dict:
        """
        运行完整流水线

        Args:
            max_pages_per_source: 每个数据源的最大爬取页数
            parallel: 是否并行爬取多个数据源
            save_intermediate: 是否保存中间结果

        Returns:
            运行统计信息
        """
        stats = {
            'total_crawled': 0,
            'total_cleaned': 0,
            'total_filtered': 0,
            'sources': {},
        }

        if parallel and len(self.sources) > 1:
            # 并行爬取
            with ThreadPoolExecutor(max_workers=min(len(self.sources), 3)) as executor:
                futures = {
                    executor.submit(
                        self._process_source,
                        source,
                        max_pages_per_source,
                        save_intermediate
                    ): source
                    for source in self.sources
                }

                for future in as_completed(futures):
                    source = futures[future]
                    try:
                        source_stats = future.result()
                        stats['sources'][source.value] = source_stats
                        stats['total_crawled'] += source_stats['crawled']
                        stats['total_cleaned'] += source_stats['cleaned']
                        stats['total_filtered'] += source_stats['filtered']
                    except Exception as e:
                        logger.error(f"处理 {source.value} 失败: {e}")
                        stats['sources'][source.value] = {'error': str(e)}
        else:
            # 串行爬取
            for source in self.sources:
                try:
                    source_stats = self._process_source(
                        source, max_pages_per_source, save_intermediate
                    )
                    stats['sources'][source.value] = source_stats
                    stats['total_crawled'] += source_stats['crawled']
                    stats['total_cleaned'] += source_stats['cleaned']
                    stats['total_filtered'] += source_stats['filtered']
                except Exception as e:
                    logger.error(f"处理 {source.value} 失败: {e}")
                    stats['sources'][source.value] = {'error': str(e)}

        if save_intermediate:
            self._merge_cleaned_pages()

        logger.info(f"流水线完成: 爬取{stats['total_crawled']}, "
                    f"清洗{stats['total_cleaned']}, 过滤后{stats['total_filtered']}")

        return stats

    def _process_source(
        self,
        source: DataSource,
        max_pages: int,
        save_intermediate: bool
    ) -> Dict:
        """
        处理单个数据源

        Args:
            source: 数据源
            max_pages: 最大爬取页数
            save_intermediate: 是否保存中间结果

        Returns:
            处理统计信息
        """
        logger.info(f"开始处理数据源: {source.value}")

        # 1. 爬取
        crawler = CrawlerFactory.create(source)
        raw_pages = list(crawler.crawl(max_pages=max_pages))

        if save_intermediate:
            crawler.save_results(raw_pages, f"{source.value}_raw.json")

        # 2. 清洗
        cleaner = CleanerFactory.create(source)
        cleaned_pages = []

        for raw_page in raw_pages:
            cleaned = cleaner.clean(raw_page)
            if cleaned:
                cleaned_pages.append(cleaned)

        # 3. 质量过滤
        filtered_pages = self.quality_assessor.filter_by_quality(
            cleaned_pages, self.min_quality
        )

        if save_intermediate:
            self._save_cleaned_pages(filtered_pages, f"{source.value}_cleaned.json")

        stats = {
            'crawled': len(raw_pages),
            'cleaned': len(cleaned_pages),
            'filtered': len(filtered_pages),
            'quality_report': self.quality_assessor.get_quality_report(cleaned_pages),
        }

        logger.info(f"{source.value}: 爬取{stats['crawled']}, "
                    f"清洗{stats['cleaned']}, 过滤后{stats['filtered']}")

        return stats

    def _save_cleaned_pages(self, pages: List[CleanedPage], filename: str):
        """保存清洗后的页面"""
        output_path = PROCESSED_DATA_DIR / filename
        output_path.parent.mkdir(parents=True, exist_ok=True)

        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(
                [page.to_dict() for page in pages],
                f,
                ensure_ascii=False,
                indent=2
            )

        logger.info(f"保存 {len(pages)} 个清洗后页面到 {output_path}")

    def _merge_cleaned_pages(self):
        """合并各数据源的清洗结果为 cleaned_pages.json"""
        all_pages = []

        for source in self.sources:
            source_file = PROCESSED_DATA_DIR / f"{source.value}_cleaned.json"
            if not source_file.exists():
                continue

            with open(source_file, 'r', encoding='utf-8') as f:
                pages = json.load(f)
                all_pages.extend(pages)

        if all_pages:
            output_path = PROCESSED_DATA_DIR / "cleaned_pages.json"
            with open(output_path, 'w', encoding='utf-8') as f:
                json.dump(all_pages, f, ensure_ascii=False, indent=2)
            logger.info(f"合并 {len(all_pages)} 个页面到 {output_path}")

    def to_wiki_pages(self, cleaned_pages: List[CleanedPage]) -> List[WikiPage]:
        """
        将清洗后的页面转换为WikiPage格式（兼容现有系统）

        Args:
            cleaned_pages: 清洗后的页面列表

        Returns:
            WikiPage列表
        """
        wiki_pages = []

        for page in cleaned_pages:
            # 转换版本
            version_map = {
                'ds': GameVersion.DS,
                'dst': GameVersion.DST,
                'rog': GameVersion.ROG,
                'sw': GameVersion.SW,
                'ham': GameVersion.HAM,
                'both': GameVersion.BOTH,
            }
            version = version_map.get(page.game_version, GameVersion.BOTH)

            # 推断实体类型
            entity_type = self._infer_entity_type(page.categories)

            wiki_page = WikiPage(
                page_id=hash(f"{page.source.value}:{page.source_id}") % (10**9),
                title=page.title,
                url=page.url,
                content=page.content,
                html_content="",  # 不再需要HTML
                categories=page.categories,
                version=version,
                entity_type=entity_type,
            )
            wiki_pages.append(wiki_page)

        return wiki_pages

    def _infer_entity_type(self, categories: List[str]) -> EntityType:
        """根据分类推断实体类型"""
        categories_str = ' '.join(categories).lower()

        type_mapping = [
            (EntityType.BOSS, ['boss', 'boss']),
            (EntityType.CHARACTER, ['角色', 'character']),
            (EntityType.FOOD, ['食物', 'food', '烹饪']),
            (EntityType.CREATURE, ['生物', 'creature', 'mob', '怪物']),
            (EntityType.STRUCTURE, ['建筑', 'structure']),
            (EntityType.RECIPE, ['配方', 'recipe']),
            (EntityType.ITEM, ['物品', 'item', '工具', '武器', '护甲']),
            (EntityType.BIOME, ['生物群系', 'biome']),
            (EntityType.SEASON, ['季节', 'season']),
            (EntityType.MOD, ['mod']),
        ]

        for entity_type, keywords in type_mapping:
            if any(kw in categories_str for kw in keywords):
                return entity_type

        return EntityType.OTHER

    def merge_all_sources(self, output_file: str = "all_pages.json") -> List[WikiPage]:
        """
        合并所有数据源的结果

        Args:
            output_file: 输出文件名

        Returns:
            合并后的WikiPage列表
        """
        all_pages = []
        seen_titles = set()

        for source in self.sources:
            cleaned_file = PROCESSED_DATA_DIR / f"{source.value}_cleaned.json"

            if not cleaned_file.exists():
                logger.warning(f"文件不存在: {cleaned_file}")
                continue

            with open(cleaned_file, 'r', encoding='utf-8') as f:
                data = json.load(f)

            for item in data:
                item['source'] = DataSource(item['source'])
                page = CleanedPage(**{k: v for k, v in item.items()
                                      if k in CleanedPage.__dataclass_fields__})

                # 去重（基于标题）
                if page.title not in seen_titles:
                    seen_titles.add(page.title)
                    wiki_pages = self.to_wiki_pages([page])
                    all_pages.extend(wiki_pages)

        # 保存合并结果
        output_path = PROCESSED_DATA_DIR / output_file
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(
                [page.model_dump() for page in all_pages],
                f,
                ensure_ascii=False,
                indent=2,
                default=str
            )

        logger.info(f"合并 {len(all_pages)} 个页面到 {output_path}")
        return all_pages
