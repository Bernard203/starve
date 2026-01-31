"""清洗器基类定义"""

import re
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from bs4 import BeautifulSoup

from src.crawler.base import RawPage, DataSource


@dataclass
class CleanedPage:
    """清洗后的页面数据"""
    # 基本信息
    source: DataSource
    source_id: str
    title: str
    url: str

    # 内容
    content: str                    # 清洗后的纯文本
    summary: str = ""               # 摘要
    sections: List[Dict] = field(default_factory=list)  # 章节结构

    # 结构化数据
    infobox: Dict = field(default_factory=dict)    # 信息框
    stats: Dict = field(default_factory=dict)      # 数值属性
    recipes: List[Dict] = field(default_factory=list)  # 配方

    # 元数据
    categories: List[str] = field(default_factory=list)
    game_version: str = "both"      # ds/dst/both
    related_pages: List[str] = field(default_factory=list)

    # 质量评估
    quality_score: float = 0.0

    def to_dict(self) -> Dict:
        """转换为字典"""
        return {
            'source': self.source.value,
            'source_id': self.source_id,
            'title': self.title,
            'url': self.url,
            'content': self.content,
            'summary': self.summary,
            'sections': self.sections,
            'infobox': self.infobox,
            'stats': self.stats,
            'recipes': self.recipes,
            'categories': self.categories,
            'game_version': self.game_version,
            'related_pages': self.related_pages,
            'quality_score': self.quality_score,
        }


class BaseCleaner(ABC):
    """清洗器抽象基类"""

    # 需要移除的HTML标签
    REMOVE_TAGS = ['script', 'style', 'nav', 'footer', 'aside', 'noscript', 'iframe']

    # 需要移除的CSS类
    REMOVE_CLASSES = [
        'mw-editsection', 'navbox', 'toc', 'mbox', 'ambox',
        'noprint', 'metadata', 'stub', 'navigation',
    ]

    # 版本关键词
    VERSION_KEYWORDS = {
        'dst': ['联机版', 'together', 'dst', '联机', '多人'],
        'ds': ['单机版', "don't starve", '单机'],
        'rog': ['巨人国', 'reign of giants', 'rog', '巨人统治'],
        'sw': ['海难', 'shipwrecked', 'sw'],
        'ham': ['哈姆雷特', 'hamlet', 'ham', '猪镇'],
    }

    def clean(self, raw_page: RawPage) -> Optional[CleanedPage]:
        """
        清洗原始页面

        Args:
            raw_page: 原始页面数据

        Returns:
            清洗后的页面数据，失败返回None
        """
        if not raw_page.html_content and not raw_page.content:
            return None

        # 解析HTML
        soup = None
        if raw_page.html_content:
            soup = BeautifulSoup(raw_page.html_content, 'lxml')
            soup = self._clean_html(soup)

        # 提取内容
        content = self._extract_content(soup) if soup else raw_page.content
        if not content or len(content.strip()) < 50:
            return None

        # 提取各部分
        summary = self._extract_summary(content)
        sections = self._extract_sections(soup) if soup else []
        infobox = self._extract_infobox(soup, raw_page.raw_data) if soup else {}
        stats = self._extract_stats(infobox, content)
        recipes = self._extract_recipes(soup, raw_page.raw_data) if soup else []
        related_pages = self._extract_related_pages(soup) if soup else []
        game_version = self._detect_game_version(content, raw_page.categories)

        cleaned = CleanedPage(
            source=raw_page.source,
            source_id=raw_page.source_id,
            title=raw_page.title,
            url=raw_page.url,
            content=content,
            summary=summary,
            sections=sections,
            infobox=infobox,
            stats=stats,
            recipes=recipes,
            categories=raw_page.categories,
            game_version=game_version,
            related_pages=related_pages,
        )

        # 计算质量分数
        from .quality import QualityAssessor
        assessor = QualityAssessor()
        cleaned.quality_score = assessor.assess(cleaned)

        return cleaned

    def _clean_html(self, soup: BeautifulSoup) -> BeautifulSoup:
        """清洗HTML结构"""
        # 移除指定标签
        for tag in self.REMOVE_TAGS:
            for element in soup.find_all(tag):
                element.decompose()

        # 移除指定类名的元素
        for class_name in self.REMOVE_CLASSES:
            for element in soup.find_all(class_=lambda x: x and class_name in str(x).lower()):
                element.decompose()

        # 移除隐藏元素
        for element in soup.find_all(style=lambda x: x and 'display:none' in str(x).lower()):
            element.decompose()

        return soup

    def _extract_content(self, soup: BeautifulSoup) -> str:
        """提取纯文本内容"""
        # 查找主内容区域
        main_content = soup.find('div', class_='mw-parser-output')
        if not main_content:
            main_content = soup.find('div', id='content')
        if not main_content:
            main_content = soup

        text = main_content.get_text(separator='\n', strip=True)

        # 清理多余空行
        text = re.sub(r'\n{3,}', '\n\n', text)

        return text.strip()

    def _extract_summary(self, content: str) -> str:
        """提取摘要（第一段有意义的文本）"""
        paragraphs = content.split('\n\n')

        for para in paragraphs:
            para = para.strip()
            # 跳过太短的段落
            if len(para) < 30:
                continue
            # 跳过看起来像标题的内容
            if para.startswith('#') or para.startswith('='):
                continue
            # 跳过注释
            if para.startswith('参见') or para.startswith('另见'):
                continue

            return para[:500]  # 限制长度

        return ""

    @abstractmethod
    def _extract_infobox(self, soup: BeautifulSoup, raw_data: Dict) -> Dict:
        """提取信息框数据（子类实现）"""
        pass

    def _extract_sections(self, soup: BeautifulSoup) -> List[Dict]:
        """提取章节结构"""
        sections = []

        for heading in soup.find_all(['h2', 'h3', 'h4']):
            level = int(heading.name[1])
            title = heading.get_text(strip=True)

            # 获取章节内容（直到下一个标题）
            content_parts = []
            for sibling in heading.find_next_siblings():
                if sibling.name in ['h2', 'h3', 'h4']:
                    break
                text = sibling.get_text(strip=True)
                if text:
                    content_parts.append(text)

            sections.append({
                'level': level,
                'title': title,
                'content': '\n'.join(content_parts),
            })

        return sections

    def _extract_stats(self, infobox: Dict, content: str) -> Dict:
        """提取数值属性"""
        from .normalizer import DataNormalizer
        normalizer = DataNormalizer()

        stats = {}

        # 从信息框提取
        for key, value in infobox.items():
            normalized_key = normalizer.normalize_stat_name(key)
            if normalized_key:
                normalized_value = normalizer.normalize_value(value)
                if normalized_value is not None:
                    stats[normalized_key] = normalized_value

        # 从正文提取（正则匹配）
        stat_patterns = [
            (r'生命[值]?[：:]\s*([\d.]+)', 'health'),
            (r'饥饿[值]?[：:]\s*([\d.]+)', 'hunger'),
            (r'理智[值]?[：:]\s*([\d.]+)', 'sanity'),
            (r'伤害[：:]\s*([\d.]+)', 'damage'),
            (r'耐久[度]?[：:]\s*([\d.]+)', 'durability'),
            (r'烹饪时间[：:]\s*([\d.]+)', 'cook_time'),
        ]

        for pattern, stat_name in stat_patterns:
            if stat_name not in stats:
                match = re.search(pattern, content)
                if match:
                    try:
                        stats[stat_name] = float(match.group(1))
                    except ValueError:
                        pass

        return stats

    @abstractmethod
    def _extract_recipes(self, soup: BeautifulSoup, raw_data: Dict) -> List[Dict]:
        """提取配方数据（子类实现）"""
        pass

    def _extract_related_pages(self, soup: BeautifulSoup) -> List[str]:
        """提取相关页面链接"""
        related = []

        for link in soup.find_all('a', href=True):
            href = link.get('href', '')
            # 只保留内部链接
            if href.startswith('/wiki/') or href.startswith('/zh/'):
                title = link.get_text(strip=True)
                if title and len(title) > 1:
                    related.append(title)

        # 去重并限制数量
        return list(dict.fromkeys(related))[:20]

    def _detect_game_version(self, content: str, categories: List[str]) -> str:
        """检测游戏版本"""
        text = content.lower() + ' ' + ' '.join(categories).lower()

        # 检查版本关键词
        for version, keywords in self.VERSION_KEYWORDS.items():
            for keyword in keywords:
                if keyword.lower() in text:
                    if version in ['rog', 'sw', 'ham']:
                        return 'ds'  # DLC属于单机版
                    return version

        return 'both'
