#!/usr/bin/env python3
"""
大规模Wiki爬取脚本 - 使用CrawlPipeline进行批量数据采集和清洗
"""

import argparse
import logging
import sys
from pathlib import Path

# 添加项目根目录到路径
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.crawler import CrawlPipeline, DataSource

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('crawl.log', encoding='utf-8')
    ]
)
logger = logging.getLogger(__name__)


def main():
    parser = argparse.ArgumentParser(description='大规模Wiki爬取')
    parser.add_argument('--max-pages', type=int, default=None, help='最大爬取数量')
    parser.add_argument('--min-quality', type=float, default=0.2, help='最低质量分数')
    args = parser.parse_args()

    pipeline = CrawlPipeline(
        sources=[DataSource.WIKI_GG],
        min_quality=args.min_quality
    )

    stats = pipeline.run(
        max_pages_per_source=args.max_pages or 1000,
        parallel=False,
        save_intermediate=True
    )

    logger.info(
        f"爬取完成: 成功 {stats['total_crawled']} 页, "
        f"清洗后 {stats['total_cleaned']} 页, "
        f"过滤后 {stats['total_filtered']} 页"
    )


if __name__ == '__main__':
    main()
