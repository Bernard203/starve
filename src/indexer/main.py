"""索引模块入口"""

import argparse
from src.utils.logger import logger
from src.crawler import WikiCrawler
from .document_processor import DocumentProcessor
from .indexer import VectorIndexer


def main():
    """索引主程序入口"""
    parser = argparse.ArgumentParser(description="饥荒知识库索引工具")
    parser.add_argument(
        "--input",
        type=str,
        default="wiki_pages.json",
        help="输入文件名 (默认: wiki_pages.json)"
    )
    parser.add_argument(
        "--collection",
        type=str,
        default="starve_knowledge",
        help="向量集合名称 (默认: starve_knowledge)"
    )
    parser.add_argument(
        "--clear",
        action="store_true",
        help="清空现有集合后重建"
    )
    args = parser.parse_args()

    logger.info("开始构建知识库索引...")

    # 加载Wiki页面
    crawler = WikiCrawler()
    pages = crawler.load_pages(args.input)

    if not pages:
        logger.error("没有可用的页面数据，请先运行爬虫")
        return

    logger.info(f"加载 {len(pages)} 个页面")

    # 处理文档
    processor = DocumentProcessor()
    documents = list(processor.process_pages(pages))

    logger.info(f"生成 {len(documents)} 个文档块")

    # 创建索引
    indexer = VectorIndexer(collection_name=args.collection)

    if args.clear:
        indexer.clear_collection()

    indexer.index_documents(documents)

    # 显示统计
    stats = indexer.get_collection_stats()
    logger.info(f"索引完成: {stats}")


if __name__ == "__main__":
    main()
