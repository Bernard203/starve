"""Steam指南内容清洗器"""

import re
from typing import Dict, List
from bs4 import BeautifulSoup

from .base import BaseCleaner, CleanedPage


class SteamCleaner(BaseCleaner):
    """Steam社区指南清洗器"""

    # Steam特有的需要移除的元素
    REMOVE_CLASSES = BaseCleaner.REMOVE_CLASSES + [
        'commentthread', 'commentcount',
        'rateup', 'ratedown', 'rate_section',
        'workshopItemPreviewHolder',
        'breadcrumbs', 'workshopItemControlRow',
    ]

    def _clean_html(self, soup: BeautifulSoup) -> BeautifulSoup:
        """清洗Steam HTML"""
        soup = super()._clean_html(soup)

        # 移除Steam特有的嵌入内容
        for elem in soup.find_all('div', class_='bb_code_header'):
            elem.decompose()

        # 保留图片alt文本
        for img in soup.find_all('img'):
            alt = img.get('alt', '')
            title = img.get('title', '')
            if alt or title:
                img.replace_with(f'[图片: {alt or title}]')
            else:
                img.decompose()

        return soup

    def _extract_content(self, soup: BeautifulSoup) -> str:
        """提取指南内容"""
        content_parts = []

        # 查找指南主体
        guide_content = soup.find('div', class_='guide')

        if guide_content:
            # 遍历章节
            for section in guide_content.find_all('div', class_='subSection'):
                # 章节标题
                title = section.find('div', class_='subSectionTitle')
                if title:
                    content_parts.append(f"\n## {title.get_text(strip=True)}\n")

                # 章节内容
                body = section.find('div', class_='subSectionDesc')
                if body:
                    text = body.get_text(separator='\n', strip=True)
                    content_parts.append(text)
        else:
            # 尝试获取描述
            desc = soup.find('div', class_='workshopItemDescription')
            if desc:
                content_parts.append(desc.get_text(separator='\n', strip=True))

        content = '\n\n'.join(content_parts)

        # 清理格式
        content = re.sub(r'\n{3,}', '\n\n', content)

        return content.strip()

    def _extract_infobox(self, soup: BeautifulSoup, raw_data: Dict) -> Dict:
        """提取指南元信息"""
        infobox = {}

        # 提取作者
        author = soup.find('div', class_='workshopItemAuthorName')
        if author:
            link = author.find('a')
            if link:
                infobox['author'] = link.get_text(strip=True)

        # 提取评分
        rating = soup.find('div', class_='fileRatingDetails')
        if rating:
            infobox['rating'] = rating.get_text(strip=True)

        # 提取发布日期
        date = soup.find('div', class_='detailsStatRight')
        if date:
            infobox['date'] = date.get_text(strip=True)

        # 从extra获取更多信息
        extra = raw_data.get('extra', {})
        if 'description' in extra:
            infobox['description'] = extra['description']

        return infobox

    def _extract_recipes(self, soup: BeautifulSoup, raw_data: Dict) -> List[Dict]:
        """从指南内容提取配方"""
        recipes = []
        content = self._extract_content(soup)

        # Steam指南中的配方通常是列表形式
        from .normalizer import DataNormalizer
        normalizer = DataNormalizer()

        # 查找配方相关段落
        lines = content.split('\n')
        current_recipe = None

        for line in lines:
            line = line.strip()

            # 检查是否是配方标题
            if re.match(r'^(?:配方|材料|合成|制作)[：:]', line):
                if current_recipe and current_recipe.get('ingredients'):
                    recipes.append(current_recipe)
                current_recipe = {'ingredients': [], 'result': '', 'source': 'steam'}

            # 检查是否包含材料信息
            if '×' in line or 'x' in line.lower():
                ingredients = normalizer.extract_ingredients(line)
                if ingredients:
                    if current_recipe is None:
                        current_recipe = {'ingredients': [], 'result': '', 'source': 'steam'}
                    current_recipe['ingredients'].extend(ingredients)

        # 保存最后一个配方
        if current_recipe and current_recipe.get('ingredients'):
            recipes.append(current_recipe)

        return recipes

    def _extract_sections(self, soup: BeautifulSoup) -> List[Dict]:
        """提取指南章节"""
        sections = []

        guide_content = soup.find('div', class_='guide')
        if not guide_content:
            return sections

        for section in guide_content.find_all('div', class_='subSection'):
            title_elem = section.find('div', class_='subSectionTitle')
            body_elem = section.find('div', class_='subSectionDesc')

            if title_elem:
                title = title_elem.get_text(strip=True)
                content = body_elem.get_text(strip=True) if body_elem else ''

                sections.append({
                    'level': 2,
                    'title': title,
                    'content': content,
                })

        return sections
