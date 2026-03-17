#!/usr/bin/env python3
"""
饥荒Wiki数据采集 - 一键运行脚本

使用新的src.crawler模块进行数据采集和清洗
"""

import argparse
import logging
import os
import sys
import time
from functools import wraps
from pathlib import Path
from typing import Optional, Callable, Any

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# ============================================================================
# 错误处理和重试机制
# ============================================================================

class DependencyError(Exception):
    """依赖缺失错误"""
    pass


class ConfigurationError(Exception):
    """配置错误"""
    pass


def retry(max_attempts: int = 3, delay: float = 1.0, backoff: float = 2.0,
          exceptions: tuple = (Exception,)):
    """
    重试装饰器

    Args:
        max_attempts: 最大尝试次数
        delay: 初始延迟秒数
        backoff: 延迟倍数（指数退避）
        exceptions: 需要重试的异常类型
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs) -> Any:
            current_delay = delay
            last_exception = None

            for attempt in range(1, max_attempts + 1):
                try:
                    return func(*args, **kwargs)
                except exceptions as e:
                    last_exception = e
                    if attempt < max_attempts:
                        logger.warning(
                            f"操作失败 (尝试 {attempt}/{max_attempts}): {e}"
                        )
                        logger.info(f"等待 {current_delay:.1f} 秒后重试...")
                        time.sleep(current_delay)
                        current_delay *= backoff
                    else:
                        logger.error(f"操作失败，已达最大重试次数: {e}")

            raise last_exception
        return wrapper
    return decorator


def check_dependencies() -> list[str]:
    """
    检查必需的依赖是否已安装

    Returns:
        缺失依赖的列表
    """
    missing = []

    # 核心依赖
    required = [
        ('requests', 'requests'),
        ('bs4', 'beautifulsoup4'),
        ('pydantic', 'pydantic'),
    ]

    # 可选依赖（用于完整功能）
    optional = [
        ('chromadb', 'chromadb'),
        ('llama_index', 'llama-index'),
        ('sentence_transformers', 'sentence-transformers'),
    ]

    for module_name, package_name in required:
        try:
            __import__(module_name)
        except ImportError:
            missing.append(package_name)

    for module_name, package_name in optional:
        try:
            __import__(module_name)
        except ImportError:
            logger.warning(f"可选依赖 {package_name} 未安装，部分功能可能不可用")

    return missing


def check_configuration() -> list[str]:
    """
    检查配置是否正确

    Returns:
        配置问题列表
    """
    issues = []

    try:
        from config import RAW_DATA_DIR, PROCESSED_DATA_DIR

        # 检查数据目录是否存在，不存在则创建
        for dir_path in [RAW_DATA_DIR, PROCESSED_DATA_DIR]:
            if not dir_path.exists():
                try:
                    dir_path.mkdir(parents=True, exist_ok=True)
                    logger.info(f"创建目录: {dir_path}")
                except PermissionError:
                    issues.append(f"无法创建目录: {dir_path}")
            elif not dir_path.is_dir():
                issues.append(f"路径存在但不是目录: {dir_path}")
            elif not os.access(dir_path, os.W_OK):
                issues.append(f"目录无写入权限: {dir_path}")

    except ImportError as e:
        issues.append(f"配置模块导入失败: {e}")

    return issues


def validate_arguments(args) -> list[str]:
    """
    验证命令行参数

    Returns:
        参数问题列表
    """
    issues = []

    if args.max_pages is not None and args.max_pages < 1:
        issues.append("--max-pages 必须大于 0")

    if not 0 <= args.min_quality <= 1:
        issues.append("--min-quality 必须在 0 到 1 之间")

    return issues


def preflight_check(args) -> bool:
    """
    运行前检查

    Returns:
        检查是否通过
    """
    logger.info("正在进行运行前检查...")

    # 1. 检查依赖
    missing_deps = check_dependencies()
    if missing_deps:
        logger.error(f"缺失必要依赖: {', '.join(missing_deps)}")
        logger.error(f"请运行: pip install {' '.join(missing_deps)}")
        return False

    # 2. 检查配置
    config_issues = check_configuration()
    if config_issues:
        for issue in config_issues:
            logger.error(f"配置问题: {issue}")
        return False

    # 3. 验证参数
    arg_issues = validate_arguments(args)
    if arg_issues:
        for issue in arg_issues:
            logger.error(f"参数错误: {issue}")
        return False

    logger.info("运行前检查通过")
    return True


@retry(max_attempts=3, delay=2.0, exceptions=(ConnectionError, TimeoutError))
def run_crawler(mode: str = 'categories', max_pages: int = None, categories: list = None):
    """
    运行爬虫

    Args:
        mode: 爬取模式
        max_pages: 最大页面数
        categories: 分类列表

    Returns:
        爬取的页面数量

    Raises:
        ConnectionError: 网络连接失败
        RuntimeError: 爬虫运行错误
    """
    try:
        from src.crawler import WikiGGCrawler
    except ImportError as e:
        raise DependencyError(f"无法导入爬虫模块: {e}") from e

    logger.info("=" * 50)
    logger.info("步骤 1/3: 爬取Wiki数据")
    logger.info("=" * 50)

    try:
        import json
        from config import RAW_DATA_DIR
        crawler = WikiGGCrawler()
    except Exception as e:
        raise RuntimeError(f"爬虫初始化失败: {e}") from e

    try:
        pages = list(crawler.crawl(max_pages=max_pages))

        if not pages:
            logger.warning("未爬取到任何页面")
            return 0

        output_path = RAW_DATA_DIR / "wiki_pages.json"
        with open(output_path, "w", encoding="utf-8") as f:
            json.dump([p.to_dict() for p in pages], f, ensure_ascii=False, indent=2)

        logger.info(f"爬取完成，共 {len(pages)} 个页面")
        return len(pages)

    except requests.exceptions.ConnectionError as e:
        logger.error(f"网络连接失败: {e}")
        logger.info("提示: 请检查网络连接或代理设置")
        raise ConnectionError(f"网络连接失败: {e}") from e
    except requests.exceptions.Timeout as e:
        logger.error(f"请求超时: {e}")
        logger.info("提示: 可以尝试增加超时时间或减少并发数")
        raise TimeoutError(f"请求超时: {e}") from e
    except Exception as e:
        logger.error(f"爬虫运行错误: {e}")
        raise


def run_cleaner(min_quality: float = 0.2):
    """
    运行数据清洗

    Args:
        min_quality: 最低质量分数阈值

    Returns:
        清洗后的页面数量

    Raises:
        FileNotFoundError: 原始数据文件不存在
        RuntimeError: 清洗过程错误
    """
    try:
        from src.crawler import CrawlPipeline, DataSource
    except ImportError as e:
        raise DependencyError(f"无法导入清洗模块: {e}") from e

    logger.info("=" * 50)
    logger.info("步骤 2/3: 清洗数据")
    logger.info("=" * 50)

    try:
        from config import RAW_DATA_DIR, PROCESSED_DATA_DIR
        import json
    except ImportError as e:
        raise ConfigurationError(f"配置导入失败: {e}") from e

    raw_file = RAW_DATA_DIR / "wiki_pages.json"
    if not raw_file.exists():
        logger.error(f"未找到原始数据文件: {raw_file}")
        logger.info("提示: 请先运行爬虫步骤 (python run.py --step crawl)")
        raise FileNotFoundError(f"原始数据文件不存在: {raw_file}")

    try:
        with open(raw_file, 'r', encoding='utf-8') as f:
            raw_data = json.load(f)
    except json.JSONDecodeError as e:
        logger.error(f"原始数据文件格式错误: {e}")
        logger.info("提示: 数据文件可能已损坏，请重新运行爬虫")
        raise RuntimeError(f"JSON解析失败: {e}") from e
    except PermissionError as e:
        logger.error(f"无法读取数据文件: {e}")
        raise

    if not raw_data:
        logger.warning("原始数据文件为空")
        return 0

    logger.info(f"加载了 {len(raw_data)} 个原始页面")

    try:
        # 使用清洗器处理
        from src.crawler import MediaWikiCleaner, CleanedPage
        from src.crawler.base import RawPage, DataSource as DS

        cleaner = MediaWikiCleaner()
        cleaned_pages = []
        failed_count = 0

        for i, page_data in enumerate(raw_data):
            try:
                # 转换为RawPage格式
                raw_page = RawPage(
                    source=DS.WIKI_GG,
                    source_id=str(page_data.get('source_id', page_data.get('page_id', ''))),
                    title=page_data.get('title', ''),
                    url=page_data.get('url', ''),
                    content=page_data.get('content', ''),
                    html_content=page_data.get('html_content', ''),
                    categories=page_data.get('categories', []),
                    raw_data=page_data
                )

                # 清洗
                cleaned = cleaner.clean(raw_page)
                if cleaned and cleaned.quality_score >= min_quality:
                    cleaned_pages.append(cleaned.to_dict())

            except Exception as e:
                failed_count += 1
                if failed_count <= 5:  # 只显示前5个错误
                    logger.warning(f"清洗页面 '{page_data.get('title', '未知')}' 失败: {e}")
                elif failed_count == 6:
                    logger.warning("更多错误已省略...")

        if failed_count > 0:
            logger.warning(f"共有 {failed_count} 个页面清洗失败")

        # 保存清洗后的数据
        output_file = PROCESSED_DATA_DIR / "cleaned_pages.json"
        try:
            with open(output_file, 'w', encoding='utf-8') as f:
                json.dump(cleaned_pages, f, ensure_ascii=False, indent=2)
        except PermissionError as e:
            logger.error(f"无法写入输出文件: {e}")
            raise

        logger.info(f"清洗完成，共 {len(cleaned_pages)} 个页面 (过滤质量分数 < {min_quality})")
        return len(cleaned_pages)

    except Exception as e:
        logger.error(f"清洗过程错误: {e}")
        raise RuntimeError(f"数据清洗失败: {e}") from e


def run_document_processor():
    """
    运行文档处理器（结构化分块 + 向量建索引）

    从 cleaned_pages.json 读取 CleanedPage 数据，
    利用结构化字段（sections/infobox/recipes）分块后写入向量数据库。

    Returns:
        生成的文档块数量

    Raises:
        DependencyError: 索引模块不可用
        RuntimeError: 文档处理错误
    """
    try:
        from src.indexer.document_processor import DocumentProcessor
        from src.indexer.indexer import VectorIndexer
    except ImportError as e:
        raise DependencyError(
            f"无法导入文档处理模块: {e}\n"
            "提示: 请确保已安装 llama-index 相关依赖"
        ) from e

    logger.info("=" * 50)
    logger.info("步骤 3/3: 生成RAG文档（结构化分块）")
    logger.info("=" * 50)

    try:
        from config import PROCESSED_DATA_DIR

        cleaned_file = PROCESSED_DATA_DIR / "cleaned_pages.json"
        if not cleaned_file.exists():
            logger.error(f"未找到清洗数据: {cleaned_file}")
            logger.info("提示: 请先运行清洗步骤 (python run.py --step clean)")
            raise FileNotFoundError(f"清洗数据文件不存在: {cleaned_file}")

        pages = DocumentProcessor.load_cleaned_pages(str(cleaned_file))
        if not pages:
            logger.warning("未加载到任何页面，请检查数据文件")
            return 0

        processor = DocumentProcessor()
        documents = list(processor.process_cleaned_pages(pages))

        if not documents:
            logger.warning("未生成任何文档块")
            logger.info("提示: 请确保已运行清洗步骤且有有效数据")
            return 0

        # 写入向量数据库
        indexer = VectorIndexer()
        indexer.index_documents(documents)

        stats = indexer.get_collection_stats()
        logger.info(f"文档生成完成，共 {len(documents)} 个文档块（索引总量: {stats['count']}）")
        return len(documents)

    except FileNotFoundError:
        raise
    except Exception as e:
        logger.error(f"文档处理错误: {e}")
        raise RuntimeError(f"文档生成失败: {e}") from e


@retry(max_attempts=2, delay=5.0, exceptions=(ConnectionError, TimeoutError))
def run_full_pipeline(max_pages: int = None, min_quality: float = 0.2):
    """
    运行完整流水线（推荐方式）

    Args:
        max_pages: 每个数据源的最大页面数
        min_quality: 最低质量分数

    Returns:
        运行统计信息字典

    Raises:
        DependencyError: 爬虫模块不可用
        RuntimeError: 流水线运行错误
    """
    try:
        from src.crawler import CrawlPipeline, DataSource
    except ImportError as e:
        raise DependencyError(f"无法导入爬虫模块: {e}") from e

    logger.info("=" * 50)
    logger.info("运行完整流水线")
    logger.info("=" * 50)

    try:
        pipeline = CrawlPipeline(
            sources=[DataSource.WIKI_GG],
            min_quality=min_quality
        )

        stats = pipeline.run(
            max_pages_per_source=max_pages or 100,
            parallel=False,
            save_intermediate=True
        )

        logger.info(f"流水线完成:")
        logger.info(f"  - 爬取: {stats['total_crawled']} 页")
        logger.info(f"  - 清洗: {stats['total_cleaned']} 页")
        logger.info(f"  - 过滤后: {stats['total_filtered']} 页")

        if stats['total_crawled'] == 0:
            logger.warning("警告: 未爬取到任何页面")
            logger.info("提示: 请检查网络连接或目标网站可用性")

        return stats

    except Exception as e:
        logger.error(f"流水线运行错误: {e}")
        raise RuntimeError(f"流水线执行失败: {e}") from e


def main():
    parser = argparse.ArgumentParser(
        description='饥荒Wiki数据采集工具',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  python run.py                        # 完整流水线
  python run.py --max-pages 100        # 限制爬取数量
  python run.py --step crawl           # 只运行爬虫
  python run.py --step clean           # 只运行清洗
  python run.py --step docs            # 只生成文档
  python run.py --min-quality 0.3      # 设置最低质量分数
  python run.py --skip-check           # 跳过运行前检查

高级用法:
  python -m src.crawler.main --help    # 使用新版多数据源爬虫

故障排除:
  - 网络错误: 检查代理设置，或使用 --max-pages 减少请求量
  - 依赖错误: 运行 pip install -e ".[dev]" 安装所有依赖
  - 权限错误: 确保 data/ 目录有写入权限
        """
    )

    parser.add_argument('--max-pages', type=int, default=None,
                        help='最大爬取页面数')
    parser.add_argument('--step', choices=['crawl', 'clean', 'docs', 'all', 'pipeline'],
                        default='pipeline',
                        help='运行步骤: crawl/clean/docs/all/pipeline (默认: pipeline)')
    parser.add_argument('--min-quality', type=float, default=0.2,
                        help='最低质量分数 (0-1)')
    parser.add_argument('--skip-check', action='store_true',
                        help='跳过运行前检查')
    parser.add_argument('--verbose', '-v', action='store_true',
                        help='显示详细日志')

    args = parser.parse_args()

    # 设置日志级别
    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)
        logger.debug("已启用详细日志模式")

    # 运行前检查
    if not args.skip_check:
        if not preflight_check(args):
            logger.error("运行前检查失败，使用 --skip-check 可跳过检查")
            sys.exit(1)

    # 导入requests用于异常处理
    try:
        import requests
        globals()['requests'] = requests
    except ImportError:
        pass

    exit_code = 0

    try:
        if args.step == 'pipeline':
            # 推荐：使用完整流水线
            run_full_pipeline(args.max_pages, args.min_quality)

        elif args.step == 'all':
            # 分步执行
            page_count = run_crawler(max_pages=args.max_pages)
            if page_count == 0:
                logger.warning("未爬取到任何页面")
                logger.info("提示: 检查网络连接或尝试减少 --max-pages 值")
            else:
                run_cleaner(args.min_quality)
                run_document_processor()

        elif args.step == 'crawl':
            run_crawler(max_pages=args.max_pages)

        elif args.step == 'clean':
            run_cleaner(args.min_quality)

        elif args.step == 'docs':
            run_document_processor()

        logger.info("=" * 50)
        logger.info("全部完成！")
        logger.info("=" * 50)
        logger.info("输出文件:")
        logger.info("  - data/raw/wiki_pages.json (原始数据)")
        logger.info("  - data/processed/cleaned_pages.json (清洗数据)")
        logger.info("  - data/processed/documents.json (RAG文档)")

    except KeyboardInterrupt:
        logger.info("\n用户中断，正在退出...")
        exit_code = 130  # 标准SIGINT退出码

    except DependencyError as e:
        logger.error(f"依赖错误: {e}")
        logger.info("请运行: pip install -e \".[dev]\" 安装所有依赖")
        exit_code = 2

    except ConfigurationError as e:
        logger.error(f"配置错误: {e}")
        logger.info("请检查 config/settings.py 和 .env 文件")
        exit_code = 3

    except FileNotFoundError as e:
        logger.error(f"文件未找到: {e}")
        exit_code = 4

    except (ConnectionError, TimeoutError) as e:
        logger.error(f"网络错误: {e}")
        logger.info("提示: 请检查网络连接，或稍后重试")
        exit_code = 5

    except Exception as e:
        logger.error(f"运行出错: {e}")
        if args.verbose:
            import traceback
            logger.debug(traceback.format_exc())
        exit_code = 1

    sys.exit(exit_code)


if __name__ == '__main__':
    main()
