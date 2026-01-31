"""Steam社区指南爬虫"""

import re
from typing import Dict, Generator, List, Optional
from urllib.parse import urljoin, quote
from bs4 import BeautifulSoup

from src.utils.logger import logger
from .base import BaseCrawler, DataSource, RawPage, DEFAULT_SOURCE_CONFIGS


class SteamCrawler(BaseCrawler):
    """Steam社区指南爬虫"""

    source = DataSource.STEAM

    def __init__(self, config: Optional[Dict] = None):
        super().__init__(config)

        source_config = DEFAULT_SOURCE_CONFIGS[DataSource.STEAM]
        self.base_url = source_config.base_url
        self.app_id = source_config.extra.get('app_id', '322330')  # DST
        self.language = source_config.extra.get('language', 'schinese')

        # Steam特定的请求头
        self.session.headers.update({
            'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8',
        })

        # 设置语言Cookie
        self.session.cookies.set('Steam_Language', self.language)

    def _get_guides_url(self, page: int = 1) -> str:
        """获取指南列表URL"""
        return (
            f"{self.base_url}/app/{self.app_id}/guides/"
            f"?browsefilter=toprated&p={page}"
        )

    def _get_guide_url(self, guide_id: str) -> str:
        """获取指南详情URL"""
        return f"{self.base_url}/sharedfiles/filedetails/?id={guide_id}"

    def get_page_list(self, max_list_pages: int = 5, **kwargs) -> Generator[Dict, None, None]:
        """
        获取指南列表

        Args:
            max_list_pages: 最大列表页数

        Yields:
            指南信息字典
        """
        for page_num in range(1, max_list_pages + 1):
            url = self._get_guides_url(page_num)

            try:
                response = self._request(url)
                soup = BeautifulSoup(response.text, 'lxml')

                # 查找指南列表
                guides = soup.find_all('div', class_='workshopItem')

                if not guides:
                    logger.info(f"[Steam] 第{page_num}页没有更多指南")
                    break

                for guide in guides:
                    try:
                        # 提取指南链接
                        link = guide.find('a', class_='ugc')
                        if not link:
                            continue

                        href = link.get('href', '')
                        # 从URL提取ID
                        match = re.search(r'id=(\d+)', href)
                        if not match:
                            continue

                        guide_id = match.group(1)

                        # 提取标题
                        title_elem = guide.find('div', class_='workshopItemTitle')
                        title = title_elem.get_text(strip=True) if title_elem else ''

                        # 提取作者
                        author_elem = guide.find('div', class_='workshopItemAuthorName')
                        author = author_elem.get_text(strip=True) if author_elem else ''

                        # 提取评分
                        rating_elem = guide.find('img', class_='fileRating')
                        rating = rating_elem.get('src', '') if rating_elem else ''

                        yield {
                            'id': guide_id,
                            'title': title,
                            'author': author,
                            'rating': rating,
                        }

                    except Exception as e:
                        logger.warning(f"解析指南失败: {e}")
                        continue

                logger.info(f"[Steam] 第{page_num}页获取 {len(guides)} 个指南")

            except Exception as e:
                logger.error(f"获取指南列表失败: {e}")
                break

    def get_page_content(self, page_id: str, title: str) -> Optional[RawPage]:
        """
        获取指南内容

        Args:
            page_id: 指南ID
            title: 指南标题

        Returns:
            RawPage对象
        """
        url = self._get_guide_url(page_id)

        try:
            response = self._request(url)
            soup = BeautifulSoup(response.text, 'lxml')

            # 提取标题
            title_elem = soup.find('div', class_='workshopItemTitle')
            if title_elem:
                title = title_elem.get_text(strip=True)

            # 提取指南描述/简介
            description = ''
            desc_elem = soup.find('div', class_='workshopItemDescription')
            if desc_elem:
                description = desc_elem.get_text(separator='\n', strip=True)

            # 提取指南正文
            content_parts = []
            guide_content = soup.find('div', class_='guide subSections')

            if guide_content:
                # 遍历所有章节
                sections = guide_content.find_all('div', class_='subSection')

                for section in sections:
                    # 章节标题
                    section_title = section.find('div', class_='subSectionTitle')
                    if section_title:
                        content_parts.append(f"\n## {section_title.get_text(strip=True)}\n")

                    # 章节内容
                    section_body = section.find('div', class_='subSectionDesc')
                    if section_body:
                        text = section_body.get_text(separator='\n', strip=True)
                        content_parts.append(text)

            # 如果没有找到章节结构，尝试获取整个描述
            if not content_parts and description:
                content_parts.append(description)

            if not content_parts:
                logger.warning(f"指南 {title} 没有内容")
                return None

            content = '\n\n'.join(content_parts)
            html_content = str(guide_content) if guide_content else ''

            # 提取标签
            categories = []
            tags = soup.find_all('a', class_='workshopItemTag')
            for tag in tags:
                categories.append(tag.get_text(strip=True))

            return RawPage(
                source=self.source,
                source_id=page_id,
                title=title,
                url=url,
                content=content,
                html_content=html_content,
                categories=categories or ['Steam指南'],
                extra={
                    'app_id': self.app_id,
                    'description': description[:500] if description else '',
                },
            )

        except Exception as e:
            logger.error(f"获取指南 {title} 失败: {e}")
            return None
