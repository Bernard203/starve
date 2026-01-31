"""内容质量评估器"""

from typing import Dict, List
from .base import CleanedPage


class QualityAssessor:
    """内容质量评估器"""

    def assess(self, page: CleanedPage) -> float:
        """
        评估页面质量

        Args:
            page: 清洗后的页面

        Returns:
            质量分数 (0-1)
        """
        scores = []

        # 1. 内容完整性 (权重: 0.4)
        content_score = self._assess_content_completeness(page)
        scores.append(content_score * 0.4)

        # 2. 结构化数据 (权重: 0.3)
        structure_score = self._assess_structured_data(page)
        scores.append(structure_score * 0.3)

        # 3. 可读性 (权重: 0.2)
        readability_score = self._assess_readability(page)
        scores.append(readability_score * 0.2)

        # 4. 元数据完整性 (权重: 0.1)
        metadata_score = self._assess_metadata(page)
        scores.append(metadata_score * 0.1)

        return min(sum(scores), 1.0)

    def _assess_content_completeness(self, page: CleanedPage) -> float:
        """评估内容完整性"""
        score = 0.0

        # 内容长度
        content_len = len(page.content)
        if content_len > 2000:
            score += 0.3
        elif content_len > 1000:
            score += 0.25
        elif content_len > 500:
            score += 0.2
        elif content_len > 200:
            score += 0.1

        # 摘要
        if page.summary and len(page.summary) > 50:
            score += 0.2
        elif page.summary:
            score += 0.1

        # 章节
        if len(page.sections) > 3:
            score += 0.3
        elif len(page.sections) > 1:
            score += 0.2
        elif page.sections:
            score += 0.1

        # 相关页面
        if len(page.related_pages) > 5:
            score += 0.2
        elif page.related_pages:
            score += 0.1

        return min(score, 1.0)

    def _assess_structured_data(self, page: CleanedPage) -> float:
        """评估结构化数据"""
        score = 0.0

        # 信息框
        if page.infobox:
            if len(page.infobox) > 5:
                score += 0.4
            elif len(page.infobox) > 2:
                score += 0.3
            else:
                score += 0.2

        # 数值属性
        if page.stats:
            if len(page.stats) > 3:
                score += 0.3
            elif len(page.stats) > 1:
                score += 0.2
            else:
                score += 0.1

        # 配方
        if page.recipes:
            score += 0.3

        return min(score, 1.0)

    def _assess_readability(self, page: CleanedPage) -> float:
        """评估可读性"""
        score = 0.0
        content = page.content

        # 平均段落长度（适中为佳）
        paragraphs = [p for p in content.split('\n\n') if p.strip()]
        if paragraphs:
            avg_len = sum(len(p) for p in paragraphs) / len(paragraphs)
            if 100 <= avg_len <= 500:
                score += 0.4
            elif 50 <= avg_len <= 800:
                score += 0.2

        # 标点符号密度（有标点表示是完整句子）
        punctuation_count = sum(1 for c in content if c in '。！？.!?')
        if len(content) > 0:
            punct_density = punctuation_count / len(content)
            if 0.01 <= punct_density <= 0.05:
                score += 0.3
            elif punct_density > 0:
                score += 0.15

        # 没有乱码或特殊字符
        special_chars = sum(1 for c in content if ord(c) > 0xFFFF or c in '\x00\x01\x02')
        if special_chars == 0:
            score += 0.3

        return min(score, 1.0)

    def _assess_metadata(self, page: CleanedPage) -> float:
        """评估元数据完整性"""
        score = 0.0

        # 标题
        if page.title and len(page.title) > 1:
            score += 0.3

        # URL
        if page.url and page.url.startswith('http'):
            score += 0.2

        # 分类
        if len(page.categories) > 2:
            score += 0.3
        elif page.categories:
            score += 0.15

        # 版本信息
        if page.game_version and page.game_version != 'both':
            score += 0.2

        return min(score, 1.0)

    def filter_by_quality(
        self,
        pages: List[CleanedPage],
        min_score: float = 0.2
    ) -> List[CleanedPage]:
        """
        按质量分数过滤页面

        Args:
            pages: 页面列表
            min_score: 最低分数阈值

        Returns:
            过滤后的页面列表
        """
        return [p for p in pages if p.quality_score >= min_score]

    def get_quality_report(self, pages: List[CleanedPage]) -> Dict:
        """
        生成质量报告

        Args:
            pages: 页面列表

        Returns:
            质量报告字典
        """
        if not pages:
            return {'total': 0}

        scores = [p.quality_score for p in pages]

        # 分数分布
        distribution = {
            'excellent': sum(1 for s in scores if s >= 0.8),
            'good': sum(1 for s in scores if 0.6 <= s < 0.8),
            'fair': sum(1 for s in scores if 0.4 <= s < 0.6),
            'poor': sum(1 for s in scores if 0.2 <= s < 0.4),
            'bad': sum(1 for s in scores if s < 0.2),
        }

        return {
            'total': len(pages),
            'average_score': sum(scores) / len(scores),
            'max_score': max(scores),
            'min_score': min(scores),
            'distribution': distribution,
        }
