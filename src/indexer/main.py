"""索引模块入口"""

import argparse
from pathlib import Path

from config import PROCESSED_DATA_DIR
from src.utils.logger import logger
from .document_processor import DocumentProcessor
from .indexer import VectorIndexer


def main():
    """索引主程序入口
      从 cleaned_pages.json（CleanedPage 格式）建结构化索引
    """
    parser = argparse.ArgumentParser(description="饥荒知识库索引工具")
    parser.add_argument(
        "--input",
        type=str,
        default=None,
        help="输入文件路径，默认：data/processed/cleaned_pages.json",
    )
    parser.add_argument(
        "--collection",
        type=str,
        default="starve_knowledge",
        help="向量集合名称（默认：starve_knowledge）",
    )
    parser.add_argument(
        "--clear",
        action="store_true",
        help="清空现有集合后重建",
    )
    args = parser.parse_args()

    processor = DocumentProcessor()
    indexer = VectorIndexer(collection_name=args.collection)

    if args.clear:
        indexer.clear_collection()
        logger.info("已清空现有集合")

    input_path = args.input or str(PROCESSED_DATA_DIR / "cleaned_pages.json")

    pages = DocumentProcessor.load_cleaned_pages(input_path)
    if not pages:
        logger.error("没有可用的 CleanedPage 数据，请先运行爬虫和清洗流程")
        return

    logger.info(f"加载 {len(pages)} 个页面")

    documents = list(processor.process_cleaned_pages(pages))
    if not documents:
        logger.error("文档块生成为空，请检查数据")
        return

    # 统计各类型块数量
    type_counts: dict[str, int] = {}
    for doc in documents:
        t = doc.metadata.get("chunk_type", "unknown")
        type_counts[t] = type_counts.get(t, 0) + 1

    logger.info(
        f"生成 {len(documents)} 个文档块：" +
        "、".join(f"{t}×{n}" for t, n in sorted(type_counts.items()))
    )

    # ------------------------------------------------------------------
    # 建向量索引
    # ------------------------------------------------------------------
    indexer.index_documents(documents)

    stats = indexer.get_collection_stats()
    logger.info(f"索引完成：集合={stats['name']}，文档数={stats['count']}")


if __name__ == "__main__":
    main()
