"""Wiki页面解析器"""

import re
from typing import Optional
from bs4 import BeautifulSoup, Tag

from src.utils.logger import logger
from src.utils.models import WikiPage, Recipe, GameEntity, EntityType, GameVersion


class WikiParser:
    """Wiki页面内容解析器"""

    def __init__(self):
        self.recipe_patterns = {
            "cooking": r"烹饪时间[：:]\s*([\d.]+)",
            "ingredients": r"材料[：:]\s*(.+)",
        }

    def parse_page(self, page: WikiPage) -> dict:
        """解析Wiki页面，提取结构化信息"""
        result = {
            "page": page,
            "sections": self.extract_sections(page.html_content),
            "tables": self.extract_tables(page.html_content),
            "infobox": self.extract_infobox(page.html_content),
        }

        # 根据实体类型进行特殊解析
        if page.entity_type == EntityType.FOOD:
            result["recipe"] = self.parse_food_recipe(page)
        elif page.entity_type == EntityType.CREATURE or page.entity_type == EntityType.BOSS:
            result["entity"] = self.parse_creature(page)

        return result

    def extract_sections(self, html_content: str) -> list[dict]:
        """提取页面章节"""
        soup = BeautifulSoup(html_content, "lxml")
        sections = []

        current_section = {"title": "概述", "level": 1, "content": ""}

        for element in soup.find_all(["h1", "h2", "h3", "h4", "p", "ul", "ol", "table"]):
            if element.name in ["h1", "h2", "h3", "h4"]:
                # 保存当前章节
                if current_section["content"].strip():
                    sections.append(current_section)

                # 开始新章节
                level = int(element.name[1])
                current_section = {
                    "title": element.get_text(strip=True),
                    "level": level,
                    "content": ""
                }
            else:
                # 添加内容到当前章节
                text = element.get_text(separator=" ", strip=True)
                if text:
                    current_section["content"] += text + "\n"

        # 保存最后一个章节
        if current_section["content"].strip():
            sections.append(current_section)

        return sections

    def extract_tables(self, html_content: str) -> list[list[list[str]]]:
        """提取页面中的表格数据"""
        soup = BeautifulSoup(html_content, "lxml")
        tables = []

        for table in soup.find_all("table"):
            table_data = []
            for row in table.find_all("tr"):
                row_data = []
                for cell in row.find_all(["th", "td"]):
                    row_data.append(cell.get_text(strip=True))
                if row_data:
                    table_data.append(row_data)
            if table_data:
                tables.append(table_data)

        return tables

    def extract_infobox(self, html_content: str) -> dict:
        """提取信息框数据"""
        soup = BeautifulSoup(html_content, "lxml")
        infobox = {}

        # 查找信息框（通常是class包含infobox的表格或div）
        infobox_elem = soup.find(class_=lambda x: x and "infobox" in x.lower())

        if not infobox_elem:
            # 尝试查找portable-infobox
            infobox_elem = soup.find(class_="portable-infobox")

        if infobox_elem:
            # 提取键值对
            for row in infobox_elem.find_all("tr"):
                cells = row.find_all(["th", "td"])
                if len(cells) >= 2:
                    key = cells[0].get_text(strip=True)
                    value = cells[1].get_text(strip=True)
                    if key and value:
                        infobox[key] = value

            # 提取data-source属性的内容
            for data_elem in infobox_elem.find_all(attrs={"data-source": True}):
                key = data_elem.get("data-source")
                value_elem = data_elem.find(class_="pi-data-value")
                if value_elem:
                    value = value_elem.get_text(strip=True)
                    if key and value:
                        infobox[key] = value

        return infobox

    def parse_food_recipe(self, page: WikiPage) -> Optional[Recipe]:
        """解析食物配方"""
        try:
            soup = BeautifulSoup(page.html_content, "lxml")
            infobox = self.extract_infobox(page.html_content)

            # 提取配方信息
            ingredients = []
            cook_time = None

            # 从信息框提取
            if "烹饪时间" in infobox:
                match = re.search(r"([\d.]+)", infobox["烹饪时间"])
                if match:
                    cook_time = float(match.group(1))

            # 从内容中提取材料
            content = page.content
            if "材料" in content or "配方" in content:
                # 简单的材料提取逻辑
                lines = content.split("\n")
                for line in lines:
                    if "×" in line or "x" in line.lower():
                        ingredients.append({"raw": line.strip()})

            # 提取饥饿/理智/生命恢复值
            hunger = self._extract_number(infobox.get("饥饿值", ""))
            sanity = self._extract_number(infobox.get("理智值", ""))
            health = self._extract_number(infobox.get("生命值", ""))

            recipe = Recipe(
                name=page.title,
                recipe_type="cooking",
                ingredients=ingredients,
                result=page.title,
                cook_time=cook_time,
                version=page.version,
                notes=f"饥饿:{hunger}, 理智:{sanity}, 生命:{health}"
            )

            return recipe

        except Exception as e:
            logger.error(f"解析食物配方失败 {page.title}: {e}")
            return None

    def parse_creature(self, page: WikiPage) -> Optional[GameEntity]:
        """解析生物/Boss信息"""
        try:
            infobox = self.extract_infobox(page.html_content)

            entity = GameEntity(
                name=page.title,
                entity_type=page.entity_type,
                description=page.content[:500] if page.content else None,
                health=self._extract_number(infobox.get("生命值", "")),
                damage=self._extract_number(infobox.get("伤害", "")),
                attack_period=self._extract_number(infobox.get("攻击间隔", "")),
                walk_speed=self._extract_number(infobox.get("移动速度", "")),
                version=page.version,
                wiki_url=page.url,
            )

            # 提取掉落物
            drops_text = infobox.get("掉落物", "")
            if drops_text:
                entity.drops = [{"raw": drops_text}]

            return entity

        except Exception as e:
            logger.error(f"解析生物信息失败 {page.title}: {e}")
            return None

    def _extract_number(self, text: str) -> Optional[float]:
        """从文本中提取数字"""
        if not text:
            return None
        match = re.search(r"[-+]?[\d.]+", text)
        if match:
            try:
                return float(match.group())
            except ValueError:
                return None
        return None

    def clean_text(self, text: str) -> str:
        """清理文本内容"""
        # 移除多余空白
        text = re.sub(r"\s+", " ", text)
        # 移除Wiki标记残留
        text = re.sub(r"\[\[|\]\]", "", text)
        text = re.sub(r"\{\{.*?\}\}", "", text)
        return text.strip()
