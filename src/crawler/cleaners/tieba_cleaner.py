"""贴吧内容清洗器"""

import re
from typing import Dict, List
from bs4 import BeautifulSoup

from .base import BaseCleaner, CleanedPage


class TiebaCleaner(BaseCleaner):
    """贴吧内容清洗器"""

    # 贴吧特有的需要移除的元素
    REMOVE_CLASSES = BaseCleaner.REMOVE_CLASSES + [
        'ad', 'floor_ad', 'ad_content',
        'save_face_bg', 'louzhubiaoshi',
        'share_btn', 'lzl_panel',
    ]

    def _clean_html(self, soup: BeautifulSoup) -> BeautifulSoup:
        """清洗贴吧HTML"""
        soup = super()._clean_html(soup)

        # 移除表情图片（保留文字描述）
        for img in soup.find_all('img', class_='BDE_Smiley'):
            alt = img.get('alt', '')
            if alt:
                img.replace_with(f'[{alt}]')
            else:
                img.decompose()

        # 移除其他图片链接
        for img in soup.find_all('img'):
            img.decompose()

        return soup

    def _extract_content(self, soup: BeautifulSoup) -> str:
        """提取帖子内容"""
        content_parts = []

        # 查找所有楼层内容
        floors = soup.find_all('div', class_='d_post_content')

        for floor in floors:
            text = floor.get_text(separator='\n', strip=True)
            if text and len(text) > 10:  # 过滤太短的回复
                content_parts.append(text)

        # 如果没有找到楼层结构，尝试直接提取
        if not content_parts:
            content_parts.append(soup.get_text(separator='\n', strip=True))

        content = '\n\n---\n\n'.join(content_parts)

        # 清理多余空行和特殊字符
        content = re.sub(r'\n{3,}', '\n\n', content)
        content = re.sub(r'[^\S\n]+', ' ', content)  # 多个空格合并

        return content.strip()

    def _extract_infobox(self, soup: BeautifulSoup, raw_data: Dict) -> Dict:
        """贴吧没有标准信息框，返回帖子元数据"""
        return {
            'forum': raw_data.get('extra', {}).get('forum', ''),
            'pages_crawled': raw_data.get('extra', {}).get('pages_crawled', 1),
        }

    def _extract_recipes(self, soup: BeautifulSoup, raw_data: Dict) -> List[Dict]:
        """从帖子内容提取可能的配方信息"""
        recipes = []
        content = self._extract_content(soup)

        # 查找配方相关的内容块
        recipe_patterns = [
            r'材料[：:]\s*([^\n]+)',
            r'配方[：:]\s*([^\n]+)',
            r'需要[：:]\s*([^\n]+)',
        ]

        from .normalizer import DataNormalizer
        normalizer = DataNormalizer()

        for pattern in recipe_patterns:
            matches = re.findall(pattern, content)
            for match in matches:
                ingredients = normalizer.extract_ingredients(match)
                if ingredients:
                    recipes.append({
                        'ingredients': ingredients,
                        'result': '',
                        'source': 'tieba',
                    })

        return recipes

    def _extract_summary(self, content: str) -> str:
        """提取帖子摘要"""
        # 取第一段有意义的内容
        paragraphs = content.split('\n\n')

        for para in paragraphs:
            para = para.strip()
            # 跳过分隔符
            if para == '---':
                continue
            # 跳过太短的内容
            if len(para) < 20:
                continue
            # 跳过楼主标记
            if para.startswith('[楼主]'):
                para = para[4:].strip()

            return para[:500]

        return ""

    def _extract_sections(self, soup: BeautifulSoup) -> List[Dict]:
        """贴吧帖子按楼层分节"""
        sections = []

        floors = soup.find_all('div', class_='l_post')

        for i, floor in enumerate(floors):
            content_div = floor.find('div', class_='d_post_content')
            if content_div:
                text = content_div.get_text(strip=True)
                if text and len(text) > 20:
                    is_lz = floor.find('span', class_='louzhubiaoshi_wrap') is not None
                    sections.append({
                        'level': 2,
                        'title': f"{'楼主' if is_lz else '回复'} #{i + 1}",
                        'content': text,
                    })

        return sections
