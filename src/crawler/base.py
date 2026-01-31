"""爬虫基类和数据模型定义"""

import json
import time
from abc import ABC, abstractmethod
from dataclasses import dataclass, field, asdict
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any, Dict, Generator, List, Optional

import requests
from tenacity import retry, stop_after_attempt, wait_exponential

from config import settings, RAW_DATA_DIR
from src.utils.logger import logger


class DataSource(str, Enum):
    """数据源类型"""
    WIKI_GG = "wiki_gg"      # dontstarve.wiki.gg
    FANDOM = "fandom"        # dontstarve.fandom.com
    HUIJI = "huiji"          # huijiwiki.com
    TIEBA = "tieba"          # 百度贴吧
    STEAM = "steam"          # Steam指南


@dataclass
class RawPage:
    """原始页面数据（统一结构）"""
    source: DataSource
    source_id: str              # 数据源内的唯一ID
    title: str
    url: str
    content: str                # 纯文本内容
    html_content: str           # HTML原文
    categories: List[str] = field(default_factory=list)
    crawled_at: str = field(default_factory=lambda: datetime.now().isoformat())
    raw_data: Dict = field(default_factory=dict)  # 原始API响应
    extra: Dict = field(default_factory=dict)     # 数据源特有字段

    def to_dict(self) -> Dict:
        """转换为字典"""
        data = asdict(self)
        data['source'] = self.source.value
        return data

    @classmethod
    def from_dict(cls, data: Dict) -> 'RawPage':
        """从字典创建"""
        data = data.copy()
        data['source'] = DataSource(data['source'])
        return cls(**data)


class BaseCrawler(ABC):
    """爬虫抽象基类"""

    source: DataSource = None

    def __init__(self, config: Optional[Dict] = None):
        """
        初始化爬虫

        Args:
            config: 可选的配置覆盖
        """
        self.config = config or {}
        self.session = self._create_session()
        self.crawled_ids: set = set()
        self.failed_ids: List[str] = []
        self.output_dir = RAW_DATA_DIR

        # 从全局配置获取默认值
        self.request_delay = self.config.get(
            'request_delay',
            settings.crawler.request_delay
        )
        self.max_retries = self.config.get(
            'max_retries',
            settings.crawler.max_retries
        )
        self.timeout = self.config.get(
            'timeout',
            settings.crawler.timeout
        )

    def _create_session(self) -> requests.Session:
        """创建HTTP会话"""
        session = requests.Session()
        user_agent = self.config.get(
            'user_agent',
            settings.crawler.user_agent
        )
        session.headers.update({
            'User-Agent': user_agent,
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
            'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8',
        })
        return session

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10)
    )
    def _request(
        self,
        url: str,
        params: Optional[Dict] = None,
        method: str = 'GET',
        **kwargs
    ) -> requests.Response:
        """
        发送HTTP请求（带重试机制）

        Args:
            url: 请求URL
            params: 请求参数
            method: 请求方法
            **kwargs: 其他参数传递给requests

        Returns:
            Response对象
        """
        time.sleep(self.request_delay)

        kwargs.setdefault('timeout', self.timeout)
        kwargs.setdefault('params', params)

        response = self.session.request(method, url, **kwargs)
        response.raise_for_status()
        return response

    @abstractmethod
    def get_page_list(self, **kwargs) -> Generator[Dict, None, None]:
        """
        获取页面列表

        Yields:
            包含页面信息的字典，至少包含 'id' 和 'title' 字段
        """
        pass

    @abstractmethod
    def get_page_content(self, page_id: str, title: str) -> Optional[RawPage]:
        """
        获取单个页面内容

        Args:
            page_id: 页面ID
            title: 页面标题

        Returns:
            RawPage对象，失败返回None
        """
        pass

    def crawl(
        self,
        max_pages: Optional[int] = None,
        **kwargs
    ) -> Generator[RawPage, None, None]:
        """
        爬取页面

        Args:
            max_pages: 最大爬取页数，None表示无限制
            **kwargs: 传递给get_page_list的参数

        Yields:
            RawPage对象
        """
        if max_pages is None:
            max_pages = settings.crawler.max_pages

        count = 0
        for page_info in self.get_page_list(**kwargs):
            if count >= max_pages:
                break

            page_id = str(page_info.get('id', page_info.get('pageid', page_info.get('title'))))
            title = page_info.get('title', '')

            if page_id in self.crawled_ids:
                continue

            try:
                page = self.get_page_content(page_id, title)
                if page:
                    self.crawled_ids.add(page_id)
                    count += 1
                    logger.info(f"[{self.source.value}] 已爬取: {title} ({count}/{max_pages})")
                    yield page
                else:
                    self.failed_ids.append(page_id)
            except Exception as e:
                logger.error(f"[{self.source.value}] 爬取失败 {title}: {e}")
                self.failed_ids.append(page_id)

    def get_stats(self) -> Dict:
        """获取爬取统计信息"""
        return {
            'source': self.source.value if self.source else 'unknown',
            'crawled_count': len(self.crawled_ids),
            'failed_count': len(self.failed_ids),
            'failed_ids': self.failed_ids[:100],  # 只返回前100个
        }

    def save_results(
        self,
        pages: List[RawPage],
        filename: Optional[str] = None
    ) -> Path:
        """
        保存爬取结果到JSON文件

        Args:
            pages: 页面列表
            filename: 文件名，默认为 {source}_pages.json

        Returns:
            保存的文件路径
        """
        if filename is None:
            source_name = self.source.value if self.source else 'unknown'
            filename = f"{source_name}_pages.json"

        output_path = self.output_dir / filename
        output_path.parent.mkdir(parents=True, exist_ok=True)

        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(
                [page.to_dict() for page in pages],
                f,
                ensure_ascii=False,
                indent=2
            )

        logger.info(f"保存 {len(pages)} 个页面到 {output_path}")
        return output_path

    def load_results(self, filename: str) -> List[RawPage]:
        """
        从JSON文件加载页面

        Args:
            filename: 文件名

        Returns:
            页面列表
        """
        input_path = self.output_dir / filename

        if not input_path.exists():
            logger.warning(f"文件不存在: {input_path}")
            return []

        with open(input_path, 'r', encoding='utf-8') as f:
            data = json.load(f)

        return [RawPage.from_dict(item) for item in data]


@dataclass
class CrawlerConfig:
    """单个数据源的爬虫配置"""
    enabled: bool = True
    api_url: str = ""
    base_url: str = ""
    categories: List[str] = field(default_factory=list)
    max_pages: int = 1000
    request_delay: float = 1.0
    timeout: int = 30
    extra: Dict = field(default_factory=dict)


# 预定义的数据源配置
DEFAULT_SOURCE_CONFIGS: Dict[DataSource, CrawlerConfig] = {
    DataSource.WIKI_GG: CrawlerConfig(
        enabled=True,
        api_url="https://dontstarve.wiki.gg/zh/api.php",
        base_url="https://dontstarve.wiki.gg",
        categories=[
            "物品", "食物", "生物", "角色", "合成",
            "烹饪锅食谱", "建筑", "工具", "武器", "护甲",
            "魔法", "科学", "生物群系", "季节", "Boss",
        ],
    ),
    DataSource.FANDOM: CrawlerConfig(
        enabled=True,
        api_url="https://dontstarve.fandom.com/zh/api.php",
        base_url="https://dontstarve.fandom.com/zh",
        categories=[
            "物品", "食物", "生物", "角色",
            "烹饪锅食谱", "建筑", "武器", "Boss",
        ],
    ),
    DataSource.HUIJI: CrawlerConfig(
        enabled=True,
        api_url="https://dontstarve.huijiwiki.com/api.php",
        base_url="https://dontstarve.huijiwiki.com",
        categories=[
            "物品", "食物", "生物", "角色", "建筑",
        ],
    ),
    DataSource.TIEBA: CrawlerConfig(
        enabled=True,
        base_url="https://tieba.baidu.com",
        extra={
            'forum_name': '饥荒',
            'only_good': True,  # 只爬精华帖
        },
    ),
    DataSource.STEAM: CrawlerConfig(
        enabled=True,
        base_url="https://steamcommunity.com",
        extra={
            'app_id': '322330',  # Don't Starve Together
            'language': 'schinese',
        },
    ),
}
