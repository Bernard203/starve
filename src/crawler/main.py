"""爬虫模块入口 - 支持多数据源"""

import argparse
from typing import List, Optional

from src.utils.logger import logger
from .base import DataSource
from .factory import CrawlerFactory
from .pipeline import CrawlPipeline


def parse_sources(source_str: str) -> List[DataSource]:
    """解析数据源字符串"""
    if source_str.lower() == 'all':
        return list(DataSource)

    sources = []
    for s in source_str.split(','):
        s = s.strip().lower()
        try:
            sources.append(DataSource(s))
        except ValueError:
            # 尝试匹配名称
            for ds in DataSource:
                if ds.value == s or ds.name.lower() == s:
                    sources.append(ds)
                    break
            else:
                logger.warning(f"未知数据源: {s}")

    return sources


def main():
    """爬虫主程序入口"""
    parser = argparse.ArgumentParser(
        description="饥荒RAG多数据源爬虫",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
数据源选项:
  wiki_gg   - dontstarve.wiki.gg (默认)
  fandom    - dontstarve.fandom.com
  huiji     - 灰机Wiki
  tieba     - 百度贴吧饥荒吧
  steam     - Steam社区指南
  all       - 所有数据源

示例:
  python -m src.crawler.main --source wiki_gg --max-pages 100
  python -m src.crawler.main --source fandom,huiji --max-pages 50
  python -m src.crawler.main --source all --max-pages 20 --parallel
        """
    )

    parser.add_argument(
        "--source", "-s",
        type=str,
        default="wiki_gg",
        help="数据源，多个用逗号分隔，或使用'all' (默认: wiki_gg)"
    )
    parser.add_argument(
        "--max-pages", "-n",
        type=int,
        default=100,
        help="每个数据源的最大爬取页数 (默认: 100)"
    )
    parser.add_argument(
        "--output", "-o",
        type=str,
        default=None,
        help="输出文件名 (默认: {source}_raw.json)"
    )
    parser.add_argument(
        "--parallel", "-p",
        action="store_true",
        help="并行爬取多个数据源"
    )
    parser.add_argument(
        "--min-quality", "-q",
        type=float,
        default=0.2,
        help="最低质量分数阈值 (默认: 0.2)"
    )
    parser.add_argument(
        "--no-clean",
        action="store_true",
        help="跳过清洗步骤，只爬取原始数据"
    )
    parser.add_argument(
        "--merge",
        action="store_true",
        help="合并所有数据源的结果"
    )
    parser.add_argument(
        "--list-sources",
        action="store_true",
        help="列出所有可用的数据源"
    )

    args = parser.parse_args()

    # 列出数据源
    if args.list_sources:
        print("可用的数据源:")
        for ds in DataSource:
            print(f"  {ds.value:10} - {ds.name}")
        return

    # 解析数据源
    sources = parse_sources(args.source)
    if not sources:
        logger.error("没有有效的数据源")
        return

    logger.info(f"准备爬取数据源: {[s.value for s in sources]}")

    if args.no_clean:
        # 只爬取，不清洗
        for source in sources:
            logger.info(f"开始爬取: {source.value}")
            crawler = CrawlerFactory.create(source)
            pages = list(crawler.crawl(max_pages=args.max_pages))

            output_file = args.output or f"{source.value}_raw.json"
            crawler.save_results(pages, output_file)

            stats = crawler.get_stats()
            logger.info(f"完成: 成功 {stats['crawled_count']}, 失败 {stats['failed_count']}")
    else:
        # 完整流水线
        pipeline = CrawlPipeline(
            sources=sources,
            min_quality=args.min_quality
        )

        stats = pipeline.run(
            max_pages_per_source=args.max_pages,
            parallel=args.parallel,
            save_intermediate=True
        )

        # 打印统计
        print("\n" + "=" * 50)
        print("爬取统计")
        print("=" * 50)
        print(f"总计爬取: {stats['total_crawled']}")
        print(f"总计清洗: {stats['total_cleaned']}")
        print(f"质量过滤后: {stats['total_filtered']}")
        print("-" * 50)

        for source, source_stats in stats['sources'].items():
            if 'error' in source_stats:
                print(f"{source}: 错误 - {source_stats['error']}")
            else:
                print(f"{source}: 爬取{source_stats['crawled']}, "
                      f"清洗{source_stats['cleaned']}, "
                      f"过滤后{source_stats['filtered']}")

        # 合并结果
        if args.merge and len(sources) > 1:
            logger.info("合并所有数据源结果...")
            merged = pipeline.merge_all_sources("all_pages.json")
            print(f"\n合并完成: {len(merged)} 个页面")


if __name__ == "__main__":
    main()
