"""MediaWiki API 通用爬虫"""

from typing import Dict, Generator, List, Optional
from bs4 import BeautifulSoup

from src.utils.logger import logger
from .base import BaseCrawler, DataSource, RawPage, CrawlerConfig, DEFAULT_SOURCE_CONFIGS


class MediaWikiCrawler(BaseCrawler):
    """MediaWiki API 通用爬虫基类"""

    source: DataSource = None

    def __init__(
        self,
        api_url: str,
        base_url: str,
        source: DataSource,
        categories: Optional[List[str]] = None,
        config: Optional[Dict] = None
    ):
        """
        初始化MediaWiki爬虫

        Args:
            api_url: MediaWiki API地址
            base_url: Wiki基础URL
            source: 数据源类型
            categories: 要爬取的分类列表
            config: 额外配置
        """
        super().__init__(config)
        self.api_url = api_url
        self.base_url = base_url
        self.source = source
        self.categories = categories or []

        # 更新请求头
        self.session.headers.update({
            'Accept': 'application/json',
        })

    def _api_request(self, params: Dict) -> Dict:
        """
        发送MediaWiki API请求

        Args:
            params: API参数

        Returns:
            JSON响应
        """
        params.setdefault('format', 'json')
        response = self._request(self.api_url, params=params)
        return response.json()

    def get_category_members(
        self,
        category: str,
        limit: int = 500
    ) -> Generator[Dict, None, None]:
        """
        获取指定分类下的页面

        Args:
            category: 分类名称
            limit: 每次请求的数量

        Yields:
            页面信息字典
        """
        params = {
            'action': 'query',
            'list': 'categorymembers',
            'cmtitle': f'Category:{category}',
            'cmlimit': min(limit, 500),
            'cmnamespace': 0,  # 主命名空间
        }

        while True:
            try:
                data = self._api_request(params)

                if 'query' in data and 'categorymembers' in data['query']:
                    for page in data['query']['categorymembers']:
                        yield {
                            'id': page.get('pageid'),
                            'title': page.get('title'),
                        }

                # 处理分页
                if 'continue' in data:
                    params['cmcontinue'] = data['continue']['cmcontinue']
                else:
                    break

            except Exception as e:
                logger.error(f"获取分类 {category} 失败: {e}")
                break

    def get_all_pages(self, limit: int = 500) -> Generator[Dict, None, None]:
        """
        获取所有页面（通过allpages API）

        Args:
            limit: 每次请求的数量

        Yields:
            页面信息字典
        """
        params = {
            'action': 'query',
            'list': 'allpages',
            'aplimit': min(limit, 500),
            'apnamespace': 0,
        }

        while True:
            try:
                data = self._api_request(params)

                if 'query' in data and 'allpages' in data['query']:
                    for page in data['query']['allpages']:
                        yield {
                            'id': page.get('pageid'),
                            'title': page.get('title'),
                        }

                if 'continue' in data:
                    params['apcontinue'] = data['continue']['apcontinue']
                else:
                    break

            except Exception as e:
                logger.error(f"获取所有页面失败: {e}")
                break

    def get_page_list(self, **kwargs) -> Generator[Dict, None, None]:
        """
        获取页面列表

        如果指定了categories，则按分类爬取；否则爬取所有页面
        """
        categories = kwargs.get('categories', self.categories)

        if categories:
            # 按分类爬取，去重
            seen_ids = set()
            for category in categories:
                logger.info(f"[{self.source.value}] 获取分类: {category}")
                for page_info in self.get_category_members(category):
                    page_id = page_info.get('id')
                    if page_id and page_id not in seen_ids:
                        seen_ids.add(page_id)
                        yield page_info
        else:
            # 爬取所有页面
            yield from self.get_all_pages()

    def get_page_content(self, page_id: str, title: str) -> Optional[RawPage]:
        """
        获取单个页面内容

        Args:
            page_id: 页面ID
            title: 页面标题

        Returns:
            RawPage对象
        """
        params = {
            'action': 'parse',
            'pageid': page_id,
            'prop': 'text|categories|revid|displaytitle',
        }

        try:
            data = self._api_request(params)

            if 'parse' not in data:
                logger.warning(f"页面 {title} 解析失败: {data}")
                return None

            parse_data = data['parse']
            html_content = parse_data.get('text', {}).get('*', '')

            # 解析HTML获取纯文本
            soup = BeautifulSoup(html_content, 'lxml')

            # 移除不需要的元素
            for element in soup.find_all(['script', 'style', 'nav', 'footer', 'aside']):
                element.decompose()

            # 移除编辑链接等
            for element in soup.find_all(class_=['mw-editsection', 'navbox', 'toc']):
                element.decompose()

            text_content = soup.get_text(separator='\n', strip=True)

            # 获取分类
            categories = [
                cat.get('*', cat.get('title', ''))
                for cat in parse_data.get('categories', [])
            ]

            # 构建URL
            page_title_encoded = title.replace(' ', '_')
            url = f"{self.base_url}/wiki/{page_title_encoded}"

            return RawPage(
                source=self.source,
                source_id=str(page_id),
                title=parse_data.get('displaytitle', title),
                url=url,
                content=text_content,
                html_content=html_content,
                categories=categories,
                raw_data={
                    'revid': parse_data.get('revid'),
                },
            )

        except Exception as e:
            logger.error(f"获取页面 {title} 内容失败: {e}")
            return None

    def get_page_wikitext(self, page_id: str) -> Optional[str]:
        """
        获取页面的Wikitext源码

        Args:
            page_id: 页面ID

        Returns:
            Wikitext内容
        """
        params = {
            'action': 'query',
            'pageids': page_id,
            'prop': 'revisions',
            'rvprop': 'content',
            'rvslots': 'main',
        }

        try:
            data = self._api_request(params)
            pages = data.get('query', {}).get('pages', {})
            page_data = pages.get(str(page_id), {})
            revisions = page_data.get('revisions', [])

            if revisions:
                return revisions[0].get('slots', {}).get('main', {}).get('*', '')

        except Exception as e:
            logger.error(f"获取Wikitext失败: {e}")

        return None


class WikiGGCrawler(MediaWikiCrawler):
    """dontstarve.wiki.gg 爬虫"""

    source = DataSource.WIKI_GG

    def __init__(self, config: Optional[Dict] = None):
        source_config = DEFAULT_SOURCE_CONFIGS[DataSource.WIKI_GG]
        super().__init__(
            api_url=source_config.api_url,
            base_url=source_config.base_url,
            source=DataSource.WIKI_GG,
            categories=source_config.categories,
            config=config,
        )


class FandomCrawler(MediaWikiCrawler):
    """Fandom Wiki 爬虫 (dontstarve.fandom.com)"""

    source = DataSource.FANDOM

    def __init__(self, config: Optional[Dict] = None):
        source_config = DEFAULT_SOURCE_CONFIGS[DataSource.FANDOM]
        super().__init__(
            api_url=source_config.api_url,
            base_url=soure_config.base_url,
            source=DataSource.FANDOM,
            categories=source_config.categories,
            config=config,
        )


class HuijiCrawler(MediaWikiCrawler):
    """灰机Wiki爬虫 (dontstarve.huijiwiki.com)"""

    source = DataSource.HUIJI

    def __init__(self, config: Optional[Dict] = None):
        source_config = DEFAULT_SOURCE_CONFIGS[DataSource.HUIJI]
        super().__init__(
            api_url=source_config.api_url,
            base_url=source_config.base_url,
            source=DataSource.HUIJI,
            categories=source_config.categories,
            config=config,
        )
