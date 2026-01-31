"""百度贴吧爬虫"""

import re
from typing import Dict, Generator, List, Optional
from urllib.parse import quote, urljoin
from bs4 import BeautifulSoup

from src.utils.logger import logger
from .base import BaseCrawler, DataSource, RawPage, DEFAULT_SOURCE_CONFIGS


class TiebaCrawler(BaseCrawler):
    """百度贴吧爬虫 - 爬取饥荒吧精华帖"""

    source = DataSource.TIEBA

    def __init__(self, config: Optional[Dict] = None):
        super().__init__(config)

        source_config = DEFAULT_SOURCE_CONFIGS[DataSource.TIEBA]
        self.base_url = source_config.base_url
        self.forum_name = source_config.extra.get('forum_name', '饥荒')
        self.only_good = source_config.extra.get('only_good', True)

        # 贴吧特定的请求头
        self.session.headers.update({
            'Referer': f'{self.base_url}/f?kw={quote(self.forum_name)}',
        })

    def _get_forum_url(self, page: int = 0) -> str:
        """获取贴吧列表URL"""
        base = f"{self.base_url}/f?kw={quote(self.forum_name)}"
        if self.only_good:
            base += "&tab=good"  # 精华帖
        if page > 0:
            base += f"&pn={page * 50}"
        return base

    def _get_thread_url(self, thread_id: str) -> str:
        """获取帖子URL"""
        return f"{self.base_url}/p/{thread_id}"

    def get_page_list(self, max_list_pages: int = 10, **kwargs) -> Generator[Dict, None, None]:
        """
        获取帖子列表

        Args:
            max_list_pages: 最大列表页数

        Yields:
            帖子信息字典
        """
        for page_num in range(max_list_pages):
            url = self._get_forum_url(page_num)

            try:
                response = self._request(url)
                soup = BeautifulSoup(response.text, 'lxml')

                # 查找帖子列表
                threads = soup.find_all('li', class_='j_thread_list')

                if not threads:
                    logger.info(f"[贴吧] 第{page_num + 1}页没有更多帖子")
                    break

                for thread in threads:
                    try:
                        # 提取帖子信息
                        thread_id = thread.get('data-tid')
                        if not thread_id:
                            continue

                        title_elem = thread.find('a', class_='j_th_tit')
                        title = title_elem.get_text(strip=True) if title_elem else ''

                        # 获取作者
                        author_elem = thread.find('span', class_='tb_icon_author')
                        author = author_elem.get_text(strip=True) if author_elem else ''

                        # 获取回复数
                        reply_elem = thread.find('span', class_='threadlist_rep_num')
                        reply_count = reply_elem.get_text(strip=True) if reply_elem else '0'

                        yield {
                            'id': thread_id,
                            'title': title,
                            'author': author,
                            'reply_count': reply_count,
                        }

                    except Exception as e:
                        logger.warning(f"解析帖子失败: {e}")
                        continue

                logger.info(f"[贴吧] 第{page_num + 1}页获取 {len(threads)} 个帖子")

            except Exception as e:
                logger.error(f"获取帖子列表失败: {e}")
                break

    def get_page_content(self, page_id: str, title: str) -> Optional[RawPage]:
        """
        获取帖子内容

        Args:
            page_id: 帖子ID
            title: 帖子标题

        Returns:
            RawPage对象
        """
        url = self._get_thread_url(page_id)

        try:
            # 获取帖子内容（可能需要多页）
            all_content = []
            all_html = []
            page_num = 1
            max_pages = 5  # 最多爬取5页回复

            while page_num <= max_pages:
                page_url = f"{url}?pn={page_num}"
                response = self._request(page_url)
                soup = BeautifulSoup(response.text, 'lxml')

                # 查找所有楼层
                floors = soup.find_all('div', class_='l_post')

                if not floors:
                    break

                for floor in floors:
                    try:
                        # 检查是否是楼主
                        is_lz = floor.find('span', class_='louzhubiaoshi_wrap') is not None

                        # 获取内容
                        content_div = floor.find('div', class_='d_post_content')
                        if content_div:
                            # 只保留楼主的回复（或全部）
                            if is_lz or page_num == 1:  # 第一页全部保留
                                text = content_div.get_text(separator='\n', strip=True)
                                html = str(content_div)

                                if text:
                                    floor_marker = "[楼主] " if is_lz else ""
                                    all_content.append(f"{floor_marker}{text}")
                                    all_html.append(html)

                    except Exception as e:
                        logger.warning(f"解析楼层失败: {e}")
                        continue

                # 检查是否有下一页
                next_page = soup.find('a', class_='next')
                if not next_page:
                    break

                page_num += 1

            if not all_content:
                return None

            # 合并内容
            content = '\n\n---\n\n'.join(all_content)
            html_content = '\n'.join(all_html)

            return RawPage(
                source=self.source,
                source_id=page_id,
                title=title,
                url=url,
                content=content,
                html_content=html_content,
                categories=['贴吧攻略'],
                extra={
                    'forum': self.forum_name,
                    'pages_crawled': page_num,
                },
            )

        except Exception as e:
            logger.error(f"获取帖子 {title} 失败: {e}")
            return None
