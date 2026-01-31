"""饥荒Wiki爬虫"""

import json
import time
from pathlib import Path
from typing import Generator, Optional

import requests
from bs4 import BeautifulSoup
from tenacity import retry, stop_after_attempt, wait_exponential
from tqdm import tqdm

from config import settings, RAW_DATA_DIR
from src.utils.logger import logger
from src.utils.models import WikiPage, GameVersion, EntityType


class WikiCrawler:
    """饥荒Wiki爬虫类"""

    def __init__(self):
        self.config = settings.crawler
        self.session = requests.Session()
        self.session.headers.update({
            "User-Agent": self.config.user_agent,
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
        })
        self.crawled_pages: set[int] = set()
        self.output_dir = RAW_DATA_DIR

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10)
    )
    def _make_request(self, url: str, params: Optional[dict] = None) -> requests.Response:
        """发送HTTP请求，带重试机制"""
        time.sleep(self.config.request_delay)
        response = self.session.get(
            url,
            params=params,
            timeout=self.config.timeout
        )
        response.raise_for_status()
        return response

    def get_category_pages(self, category: str) -> list[dict]:
        """获取指定分类下的所有页面"""
        pages = []
        params = {
            "action": "query",
            "format": "json",
            "list": "categorymembers",
            "cmtitle": f"Category:{category}",
            "cmlimit": 500,
        }

        while True:
            try:
                response = self._make_request(self.config.wiki_api_url, params)
                data = response.json()

                if "query" in data and "categorymembers" in data["query"]:
                    for page in data["query"]["categorymembers"]:
                        # 排除非文章命名空间
                        if page.get("ns", 0) == 0:
                            pages.append({
                                "pageid": page["pageid"],
                                "title": page["title"],
                            })

                # 处理分页
                if "continue" in data:
                    params["cmcontinue"] = data["continue"]["cmcontinue"]
                else:
                    break

            except Exception as e:
                logger.error(f"获取分类 {category} 失败: {e}")
                break

        return pages

    def get_all_category_pages(self) -> list[dict]:
        """获取所有配置分类下的页面"""
        all_pages = {}

        for category in tqdm(self.config.categories, desc="获取分类页面"):
            pages = self.get_category_pages(category)
            for page in pages:
                if page["pageid"] not in all_pages:
                    all_pages[page["pageid"]] = page

            logger.info(f"分类 {category}: {len(pages)} 个页面")

        return list(all_pages.values())

    def get_page_content(self, page_id: int, title: str) -> Optional[WikiPage]:
        """获取单个页面的内容"""
        if page_id in self.crawled_pages:
            return None

        params = {
            "action": "parse",
            "format": "json",
            "pageid": page_id,
            "prop": "text|categories|revid",
        }

        try:
            response = self._make_request(self.config.wiki_api_url, params)
            data = response.json()

            if "parse" not in data:
                logger.warning(f"页面 {title} 解析失败")
                return None

            parse_data = data["parse"]
            html_content = parse_data.get("text", {}).get("*", "")

            # 解析HTML获取纯文本
            soup = BeautifulSoup(html_content, "lxml")

            # 移除不需要的元素
            for element in soup.find_all(["script", "style", "nav", "footer"]):
                element.decompose()

            text_content = soup.get_text(separator="\n", strip=True)

            # 获取分类
            categories = [
                cat["*"] for cat in parse_data.get("categories", [])
            ]

            # 判断游戏版本
            version = self._detect_version(categories, text_content)

            # 判断实体类型
            entity_type = self._detect_entity_type(categories, title)

            wiki_page = WikiPage(
                page_id=page_id,
                title=title,
                url=f"{self.config.wiki_base_url}/zh/{title.replace(' ', '_')}",
                content=text_content,
                html_content=html_content,
                categories=categories,
                version=version,
                entity_type=entity_type,
            )

            self.crawled_pages.add(page_id)
            return wiki_page

        except Exception as e:
            logger.error(f"获取页面 {title} 内容失败: {e}")
            return None

    def _detect_version(self, categories: list[str], content: str) -> GameVersion:
        """检测页面适用的游戏版本"""
        content_lower = content.lower()

        if "仅联机版" in content or "dst only" in content_lower:
            return GameVersion.DST
        if "仅单机版" in content or "ds only" in content_lower:
            return GameVersion.DS
        if "海难" in content or "shipwrecked" in content_lower:
            return GameVersion.SW
        if "哈姆雷特" in content or "hamlet" in content_lower:
            return GameVersion.HAM
        if "巨人统治" in content or "reign of giants" in content_lower:
            return GameVersion.ROG

        return GameVersion.BOTH

    def _detect_entity_type(self, categories: list[str], title: str) -> EntityType:
        """检测实体类型"""
        categories_str = " ".join(categories).lower()

        type_mapping = {
            ("boss", "boss"): EntityType.BOSS,
            ("角色", "character"): EntityType.CHARACTER,
            ("食物", "food"): EntityType.FOOD,
            ("生物", "creature", "mob"): EntityType.CREATURE,
            ("建筑", "structure"): EntityType.STRUCTURE,
            ("配方", "recipe"): EntityType.RECIPE,
            ("物品", "item"): EntityType.ITEM,
            ("生物群系", "biome"): EntityType.BIOME,
            ("季节", "season"): EntityType.SEASON,
            ("mod",): EntityType.MOD,
        }

        for keywords, entity_type in type_mapping.items():
            if any(kw in categories_str for kw in keywords):
                return entity_type

        return EntityType.OTHER

    def crawl(self, max_pages: Optional[int] = None) -> Generator[WikiPage, None, None]:
        """爬取Wiki页面"""
        if max_pages is None:
            max_pages = self.config.max_pages

        # 获取所有页面列表
        all_pages = self.get_all_category_pages()
        logger.info(f"共发现 {len(all_pages)} 个页面")

        # 限制爬取数量
        pages_to_crawl = all_pages[:max_pages]

        for page_info in tqdm(pages_to_crawl, desc="爬取页面内容"):
            wiki_page = self.get_page_content(
                page_info["pageid"],
                page_info["title"]
            )
            if wiki_page:
                yield wiki_page

    def save_pages(self, pages: list[WikiPage], filename: str = "wiki_pages.json"):
        """保存爬取的页面到JSON文件"""
        output_path = self.output_dir / filename
        output_path.parent.mkdir(parents=True, exist_ok=True)

        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(
                [page.model_dump() for page in pages],
                f,
                ensure_ascii=False,
                indent=2,
                default=str
            )

        logger.info(f"保存 {len(pages)} 个页面到 {output_path}")

    def load_pages(self, filename: str = "wiki_pages.json") -> list[WikiPage]:
        """从JSON文件加载页面"""
        input_path = self.output_dir / filename

        if not input_path.exists():
            logger.warning(f"文件不存在: {input_path}")
            return []

        with open(input_path, "r", encoding="utf-8") as f:
            data = json.load(f)

        return [WikiPage(**page) for page in data]
