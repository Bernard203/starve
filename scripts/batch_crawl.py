#!/usr/bin/env python3
"""
大规模Wiki爬取脚本 - 支持断点续爬和自动清洗

使用新的src.crawler模块
"""

import json
import time
import signal
import sys
import logging
from pathlib import Path
from datetime import datetime

# 添加项目根目录到路径
sys.path.insert(0, str(Path(__file__).parent.parent))

from config import RAW_DATA_DIR, PROCESSED_DATA_DIR
from src.crawler import WikiCrawler, MediaWikiCleaner, CleanedPage
from src.crawler.base import RawPage, DataSource

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('crawl.log', encoding='utf-8')
    ]
)
logger = logging.getLogger(__name__)


class BatchCrawler:
    """批量爬取器 - 支持断点续爬"""

    def __init__(self):
        self.crawler = WikiCrawler()
        self.cleaner = MediaWikiCleaner()

        # 状态文件
        self.state_file = RAW_DATA_DIR / "crawl_state.json"
        self.output_file = RAW_DATA_DIR / "wiki_pages_full.json"

        # 爬取状态
        self.crawled_titles = set()
        self.failed_titles = []
        self.results = []

        # 中断标志
        self.interrupted = False
        signal.signal(signal.SIGINT, self._handle_interrupt)
        signal.signal(signal.SIGTERM, self._handle_interrupt)

    def _handle_interrupt(self, signum, frame):
        """处理中断信号"""
        logger.warning("收到中断信号，正在保存进度...")
        self.interrupted = True

    def load_state(self) -> bool:
        """加载断点状态"""
        if not self.state_file.exists():
            return False

        try:
            with open(self.state_file, 'r', encoding='utf-8') as f:
                state = json.load(f)

            self.crawled_titles = set(state.get('crawled_titles', []))
            self.failed_titles = state.get('failed_titles', [])

            # 加载已爬取的结果
            if self.output_file.exists():
                with open(self.output_file, 'r', encoding='utf-8') as f:
                    self.results = json.load(f)

            logger.info(f"恢复断点: 已爬取 {len(self.crawled_titles)} 页, 失败 {len(self.failed_titles)} 页")
            return True

        except Exception as e:
            logger.error(f"加载状态失败: {e}")
            return False

    def save_state(self):
        """保存断点状态"""
        state = {
            'crawled_titles': list(self.crawled_titles),
            'failed_titles': self.failed_titles,
            'last_update': datetime.now().isoformat(),
        }

        with open(self.state_file, 'w', encoding='utf-8') as f:
            json.dump(state, f, ensure_ascii=False, indent=2)

        with open(self.output_file, 'w', encoding='utf-8') as f:
            json.dump(self.results, f, ensure_ascii=False, indent=2)

        logger.info(f"进度已保存: {len(self.results)} 页")

    def crawl_all(self, max_pages: int = None, save_interval: int = 50):
        """
        爬取所有页面

        Args:
            max_pages: 最大爬取数量（None表示全部）
            save_interval: 每多少页保存一次
        """
        # 获取所有页面列表
        logger.info("获取Wiki页面列表...")
        all_pages = self.crawler.get_all_category_pages()
        total = len(all_pages)

        if max_pages:
            all_pages = all_pages[:max_pages]
            total = len(all_pages)

        logger.info(f"共 {total} 个页面待爬取")

        # 过滤已爬取的
        pending = [p for p in all_pages if p['title'] not in self.crawled_titles]
        logger.info(f"跳过已爬取 {total - len(pending)} 页, 剩余 {len(pending)} 页")

        start_time = time.time()
        processed = 0

        for i, page in enumerate(pending):
            if self.interrupted:
                break

            title = page['title']
            page_id = page.get('pageid', 0)

            # 爬取页面
            wiki_page = self.crawler.get_page_content(page_id, title)

            if wiki_page:
                # 转换为字典保存
                self.results.append({
                    'page_id': wiki_page.page_id,
                    'title': wiki_page.title,
                    'url': wiki_page.url,
                    'content': wiki_page.content,
                    'html_content': wiki_page.html_content,
                    'categories': wiki_page.categories,
                    'version': wiki_page.version,
                    'entity_type': wiki_page.entity_type,
                })
                self.crawled_titles.add(title)
                processed += 1

                # 进度显示
                elapsed = time.time() - start_time
                speed = processed / elapsed * 60 if elapsed > 0 else 0
                remaining = (len(pending) - i - 1) / (speed / 60) if speed > 0 else 0

                logger.info(
                    f"[{len(self.crawled_titles)}/{total}] ✓ {title} "
                    f"({speed:.1f}页/分, 剩余{remaining:.0f}分)"
                )
            else:
                self.failed_titles.append(title)
                logger.warning(f"[{len(self.crawled_titles)}/{total}] ✗ {title}")

            # 定期保存
            if (i + 1) % save_interval == 0:
                self.save_state()

            # 请求延迟
            time.sleep(self.crawler.config.request_delay)

        # 最终保存
        self.save_state()

        elapsed = time.time() - start_time
        logger.info(f"爬取完成: 成功 {len(self.results)} 页, 失败 {len(self.failed_titles)} 页, 耗时 {elapsed/60:.1f} 分钟")

        return self.results

    def clean_all(self, min_quality: float = 0.2):
        """清洗所有爬取的数据"""
        if not self.results:
            # 尝试从文件加载
            if self.output_file.exists():
                with open(self.output_file, 'r', encoding='utf-8') as f:
                    self.results = json.load(f)

        if not self.results:
            logger.error("没有数据可清洗")
            return []

        logger.info(f"开始清洗 {len(self.results)} 个页面...")

        cleaned_pages = []
        for page_data in self.results:
            # 转换为RawPage格式
            raw_page = RawPage(
                source=DataSource.WIKI_GG,
                source_id=str(page_data.get('page_id', '')),
                title=page_data.get('title', ''),
                url=page_data.get('url', ''),
                content=page_data.get('content', ''),
                html_content=page_data.get('html_content', ''),
                categories=page_data.get('categories', []),
                raw_data=page_data
            )

            # 清洗
            cleaned = self.cleaner.clean(raw_page)
            if cleaned and cleaned.quality_score >= min_quality:
                cleaned_pages.append(cleaned.to_dict())

        # 保存清洗后的数据
        output_file = PROCESSED_DATA_DIR / "cleaned_pages_full.json"
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(cleaned_pages, f, ensure_ascii=False, indent=2)

        logger.info(f"清洗完成: {len(cleaned_pages)} 个页面 (过滤质量分数 < {min_quality})")
        return cleaned_pages

    def run(self, max_pages: int = None, clean: bool = True, min_quality: float = 0.2):
        """运行完整流程"""
        # 尝试恢复断点
        self.load_state()

        # 爬取
        self.crawl_all(max_pages=max_pages)

        if self.interrupted:
            logger.info("爬取被中断，下次运行将从断点继续")
            return

        # 清洗
        if clean:
            self.clean_all(min_quality=min_quality)

        logger.info("全部完成！")


def main():
    import argparse

    parser = argparse.ArgumentParser(description='大规模Wiki爬取')
    parser.add_argument('--max-pages', type=int, default=None, help='最大爬取数量')
    parser.add_argument('--no-clean', action='store_true', help='不执行清洗')
    parser.add_argument('--min-quality', type=float, default=0.2, help='最低质量分数')
    parser.add_argument('--reset', action='store_true', help='重置状态，从头开始')

    args = parser.parse_args()

    crawler = BatchCrawler()

    if args.reset:
        if crawler.state_file.exists():
            crawler.state_file.unlink()
            logger.info("状态已重置")

    crawler.run(
        max_pages=args.max_pages,
        clean=not args.no_clean,
        min_quality=args.min_quality
    )


if __name__ == '__main__':
    main()
