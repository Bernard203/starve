"""MediaWiki内容清洗器"""

import re
from typing import Dict, List, Optional
from bs4 import BeautifulSoup

from .base import BaseCleaner, CleanedPage
from .normalizer import DataNormalizer


class MediaWikiCleaner(BaseCleaner):
    """MediaWiki内容清洗器 - 适用于wiki.gg、Fandom、灰机Wiki"""

    # MediaWiki特有的需要移除的类
    REMOVE_CLASSES = BaseCleaner.REMOVE_CLASSES + [
        'reference', 'references', 'reflist',
        'catlinks', 'printfooter', 'mw-empty-elt',
        'external', 'sister-project',
    ]

    def _extract_infobox(self, soup: BeautifulSoup, raw_data: Dict) -> Dict:
        """提取信息框数据"""
        infobox = {}

        # 方式1: 查找 portable-infobox (Fandom/wiki.gg 常用)
        portable_infobox = soup.find('aside', class_='portable-infobox')
        if portable_infobox:
            infobox.update(self._parse_portable_infobox(portable_infobox))

        # 方式2: 查找传统表格infobox
        table_infobox = soup.find('table', class_=lambda x: x and 'infobox' in str(x).lower())
        if table_infobox:
            infobox.update(self._parse_table_infobox(table_infobox))

        # 方式3: 从wikitext提取（如果可用）
        wikitext = raw_data.get('wikitext', '')
        if wikitext:
            infobox.update(self._parse_wikitext_infobox(wikitext))

        return infobox

    def _parse_portable_infobox(self, infobox: BeautifulSoup) -> Dict:
        """解析 portable-infobox 格式"""
        data = {}

        # 提取数据项
        for item in infobox.find_all('div', class_='pi-data'):
            label_elem = item.find(class_='pi-data-label')
            value_elem = item.find(class_='pi-data-value')

            if label_elem and value_elem:
                label = label_elem.get_text(strip=True)
                value = value_elem.get_text(strip=True)
                if label and value:
                    data[label] = value

        # 提取标题
        title_elem = infobox.find('h2', class_='pi-title')
        if title_elem:
            data['_title'] = title_elem.get_text(strip=True)

        return data

    def _parse_table_infobox(self, table: BeautifulSoup) -> Dict:
        """解析表格格式的infobox"""
        data = {}

        for row in table.find_all('tr'):
            cells = row.find_all(['th', 'td'])
            if len(cells) >= 2:
                label = cells[0].get_text(strip=True)
                value = cells[1].get_text(strip=True)
                if label and value:
                    data[label] = value

        return data

    def _parse_wikitext_infobox(self, wikitext: str) -> Dict:
        """从wikitext解析infobox模板"""
        data = {}

        # 匹配 {{Infobox ... }} 模板
        infobox_pattern = r'\{\{[Ii]nfo[Bb]ox[^}]*\|([^}]+)\}\}'
        match = re.search(infobox_pattern, wikitext, re.DOTALL)

        if match:
            content = match.group(1)
            # 解析 key = value 对
            pairs = re.findall(r'\|?\s*(\w+)\s*=\s*([^|]+)', content)
            for key, value in pairs:
                key = key.strip()
                value = value.strip()
                if key and value:
                    data[key] = value

        return data

    def _extract_recipes(self, soup: BeautifulSoup, raw_data: Dict) -> List[Dict]:
        """提取配方数据"""
        recipes = []

        # 方式1: 从HTML表格提取
        recipe_tables = soup.find_all('table', class_=lambda x: x and 'recipe' in str(x).lower())
        for table in recipe_tables:
            recipe = self._parse_recipe_table(table)
            if recipe:
                recipes.append(recipe)

        # 方式2: 从wikitext提取配方模板
        wikitext = raw_data.get('wikitext', '')
        if wikitext:
            recipes.extend(self._parse_wikitext_recipes(wikitext))

        # 方式3: 从正文提取
        content_recipes = self._extract_recipes_from_content(soup)
        recipes.extend(content_recipes)

        return recipes

    def _parse_recipe_table(self, table: BeautifulSoup) -> Optional[Dict]:
        """解析配方表格"""
        recipe = {
            'ingredients': [],
            'result': '',
            'station': '',
        }

        for row in table.find_all('tr'):
            cells = row.find_all(['th', 'td'])
            if len(cells) >= 2:
                label = cells[0].get_text(strip=True).lower()
                value = cells[1].get_text(strip=True)

                if '材料' in label or 'ingredient' in label:
                    normalizer = DataNormalizer()
                    recipe['ingredients'] = normalizer.extract_ingredients(value)
                elif '结果' in label or 'result' in label:
                    recipe['result'] = value
                elif '制作站' in label or 'station' in label:
                    recipe['station'] = value

        if recipe['result'] or recipe['ingredients']:
            return recipe
        return None

    def _parse_wikitext_recipes(self, wikitext: str) -> List[Dict]:
        """从wikitext解析配方模板"""
        recipes = []

        # 匹配常见配方模板
        patterns = [
            r'\{\{(?:Crock[Pp]ot|烹饪锅)\|([^}]+)\}\}',
            r'\{\{(?:Recipe|配方)\|([^}]+)\}\}',
            r'\{\{(?:CraftingRecipe|合成配方)\|([^}]+)\}\}',
        ]

        for pattern in patterns:
            matches = re.findall(pattern, wikitext, re.DOTALL)
            for match in matches:
                recipe = self._parse_template_content(match)
                if recipe:
                    recipes.append(recipe)

        return recipes

    def _parse_template_content(self, content: str) -> Optional[Dict]:
        """解析模板内容"""
        recipe = {
            'ingredients': [],
            'result': '',
            'station': '',
            'cook_time': None,
        }

        # 解析参数
        params = {}
        for part in content.split('|'):
            if '=' in part:
                key, value = part.split('=', 1)
                params[key.strip().lower()] = value.strip()
            else:
                # 位置参数
                if 'result' not in recipe or not recipe['result']:
                    recipe['result'] = part.strip()

        # 提取材料
        normalizer = DataNormalizer()
        for key in ['材料', 'ingredients', 'ingredient', 'input']:
            if key in params:
                recipe['ingredients'] = normalizer.extract_ingredients(params[key])
                break

        # 提取结果
        for key in ['结果', 'result', 'output', 'name']:
            if key in params:
                recipe['result'] = params[key]
                break

        # 提取制作站
        for key in ['制作站', 'station', 'tab']:
            if key in params:
                recipe['station'] = params[key]
                break

        # 提取烹饪时间
        for key in ['时间', 'time', 'cooktime']:
            if key in params:
                try:
                    recipe['cook_time'] = float(re.search(r'[\d.]+', params[key]).group())
                except:
                    pass
                break

        if recipe['result'] or recipe['ingredients']:
            return recipe
        return None

    def _extract_recipes_from_content(self, soup: BeautifulSoup) -> List[Dict]:
        """从正文内容提取配方信息"""
        recipes = []

        # 查找包含"配方"或"材料"的段落
        for para in soup.find_all(['p', 'li']):
            text = para.get_text()
            if '配方' in text or '材料' in text or '×' in text:
                normalizer = DataNormalizer()
                ingredients = normalizer.extract_ingredients(text)
                if len(ingredients) >= 2:  # 至少2种材料
                    recipes.append({
                        'ingredients': ingredients,
                        'result': '',
                        'source': 'content',
                    })

        return recipes
