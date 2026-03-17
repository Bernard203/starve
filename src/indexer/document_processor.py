"""文档处理器 - 分块与预处理"""

import hashlib
import json
import re
from pathlib import Path
from typing import Generator, Optional

from config import settings
from src.utils.logger import logger
from src.utils.models import WikiPage, Document


class DocumentProcessor:
    """文档处理器：分块、清洗、转换

    支持两种输入格式：
    - WikiPage（旧格式，纯文本分块）
    - CleanedPage（新格式，结构化分块）
    """

    # stats 字段的中文显示名
    STAT_DISPLAY_NAMES = {
        "health": "生命值",
        "hunger": "饥饿值",
        "sanity": "理智值",
        "damage": "伤害",
        "durability": "耐久度",
        "cook_time": "烹饪时间(秒)",
        "perish_time": "腐烂时间(天)",
        "walk_speed": "移动速度",
        "armor": "护甲值",
    }

    def __init__(self):
        self.config = settings.embedding
        self.chunk_size = self.config.chunk_size
        self.chunk_overlap = self.config.chunk_overlap

    # =========================================================================
    # 新接口：基于 CleanedPage 的结构化分块
    # =========================================================================

    def process_cleaned_page(self, page) -> list[Document]:
        """处理 CleanedPage，利用结构化字段进行分块

        分块策略（按语义类型独立成块）：
          1. 摘要块 (summary)  — 快速定位页面主题
          2. 属性块 (infobox)  — 精确匹配属性查询
          3. 章节块 (section)  — 正文内容，超长则递归切分
          4. 配方块 (recipe)   — 每条配方独立，精准检索
          5. 兜底块 (content)  — 无结构时退化为纯文本分块

        Args:
            page: CleanedPage 对象

        Returns:
            Document 列表，已设置 chunk_index / total_chunks
        """
        docs = []

        base_metadata = {
            "source": page.source.value if hasattr(page.source, "value") else str(page.source),
            "source_id": page.source_id,
            "title": page.title,
            "game_version": page.game_version,
            "categories": page.categories,
            "quality_score": page.quality_score,
        }

        # 1. 摘要块
        if page.summary and len(page.summary.strip()) >= 20:
            docs.append(self._make_document(
                source_id=page.source_id,
                content=f"{page.title}\n{page.summary.strip()}",
                metadata={**base_metadata, "chunk_type": "summary"},
                source_url=page.url,
                source_title=page.title,
            ))

        # 2. 属性/信息框块
        attr_text = self._format_attributes(page.infobox, page.stats, page.title)
        if attr_text:
            docs.append(self._make_document(
                source_id=page.source_id,
                content=attr_text,
                metadata={**base_metadata, "chunk_type": "infobox"},
                source_url=page.url,
                source_title=page.title,
            ))

        # 3. 章节块
        for section in page.sections:
            section_content = section.get("content", "").strip()
            section_title = section.get("title", "").strip()

            if not section_content or len(section_content) < 20:
                continue

            # 每个章节块都前置"页面标题 - 章节名"作为语义锚点
            prefix = f"{page.title} - {section_title}"
            prefixed = f"{prefix}\n{section_content}"

            section_meta = {
                **base_metadata,
                "chunk_type": "section",
                "section_title": section_title,
                "section_level": section.get("level", 2),
            }

            if len(prefixed) <= self.chunk_size:
                docs.append(self._make_document(
                    source_id=page.source_id,
                    content=prefixed,
                    metadata=section_meta,
                    source_url=page.url,
                    source_title=page.title,
                ))
            else:
                # 超长章节：切块，每个子块都保留标题前缀
                sub_chunks = self._split_text(section_content)
                for sub in sub_chunks:
                    docs.append(self._make_document(
                        source_id=page.source_id,
                        content=f"{prefix}\n{sub}",
                        metadata=section_meta,
                        source_url=page.url,
                        source_title=page.title,
                    ))

        # 4. 配方块（每条配方独立成块）
        for i, recipe in enumerate(page.recipes):
            recipe_text = self._format_recipe(recipe, page.title)
            if not recipe_text:
                continue
            docs.append(self._make_document(
                source_id=page.source_id,
                content=recipe_text,
                metadata={**base_metadata, "chunk_type": "recipe", "recipe_index": i},
                source_url=page.url,
                source_title=page.title,
            ))

        # 5. 兜底：无任何结构化数据时，退化为纯文本分块
        if not docs:
            clean_content = self._clean_text(page.content)
            if clean_content:
                sub_chunks = self._split_text(clean_content)
                for sub in sub_chunks:
                    docs.append(self._make_document(
                        source_id=page.source_id,
                        content=sub,
                        metadata={**base_metadata, "chunk_type": "content"},
                        source_url=page.url,
                        source_title=page.title,
                    ))

        # 统一设置 chunk_index / total_chunks
        total = len(docs)
        for i, doc in enumerate(docs):
            doc.chunk_index = i
            doc.total_chunks = total

        logger.debug(
            f"[结构化分块] {page.title!r}: "
            f"摘要{1 if page.summary else 0} + "
            f"属性{1 if attr_text else 0} + "
            f"章节{len(page.sections)} + "
            f"配方{len(page.recipes)} "
            f"→ {total} 个块"
        )
        return docs

    def process_cleaned_pages(self, pages) -> Generator[Document, None, None]:
        """批量处理 CleanedPage 列表"""
        for page in pages:
            yield from self.process_cleaned_page(page)

    @staticmethod
    def load_cleaned_pages(filepath: str) -> list:
        """从 cleaned_pages.json 加载 CleanedPage 对象列表

        Args:
            filepath: cleaned_pages.json 的路径

        Returns:
            CleanedPage 列表
        """
        from src.crawler.base import DataSource
        from src.crawler.cleaners.base import CleanedPage

        path = Path(filepath)
        if not path.exists():
            logger.error(f"文件不存在: {filepath}")
            return []

        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)

        pages = []
        for d in data:
            try:
                page = CleanedPage(
                    source=DataSource(d["source"]),
                    source_id=d["source_id"],
                    title=d["title"],
                    url=d["url"],
                    content=d.get("content", ""),
                    summary=d.get("summary", ""),
                    sections=d.get("sections", []),
                    infobox=d.get("infobox", {}),
                    stats=d.get("stats", {}),
                    recipes=d.get("recipes", []),
                    categories=d.get("categories", []),
                    game_version=d.get("game_version", "both"),
                    related_pages=d.get("related_pages", []),
                    quality_score=d.get("quality_score", 0.0),
                )
                pages.append(page)
            except Exception as e:
                logger.warning(f"跳过无效页面 {d.get('title', '?')!r}: {e}")

        logger.info(f"加载 {len(pages)} 个 CleanedPage（来自 {filepath}）")
        return pages

    # =========================================================================
    # 旧接口：基于 WikiPage 的纯文本分块（保持向后兼容）
    # =========================================================================

    def process_wiki_page(self, page: WikiPage) -> list[Document]:
        """处理Wiki页面，生成文档块（旧接口，保持兼容）"""
        clean_content = self._clean_text(page.content)

        if not clean_content.strip():
            logger.warning(f"页面 {page.title} 内容为空，跳过")
            return []

        chunks = self._split_text(clean_content)

        documents = []
        for i, chunk in enumerate(chunks):
            doc_id = self._generate_doc_id(page.page_id, i)

            doc = Document(
                doc_id=doc_id,
                content=chunk,
                metadata={
                    "page_id": page.page_id,
                    "title": page.title,
                    "entity_type": page.entity_type,
                    "version": page.version,
                    "categories": page.categories,
                    "chunk_type": "content",
                },
                source_type="wiki",
                source_url=page.url,
                source_title=page.title,
                chunk_index=i,
                total_chunks=len(chunks),
            )
            documents.append(doc)

        logger.debug(f"页面 {page.title} 生成 {len(documents)} 个文档块")
        return documents

    def process_pages(self, pages: list[WikiPage]) -> Generator[Document, None, None]:
        """批量处理Wiki页面（旧接口，保持兼容）"""
        for page in pages:
            yield from self.process_wiki_page(page)

    # =========================================================================
    # 内部辅助方法
    # =========================================================================

    def _make_document(
        self,
        source_id: str,
        content: str,
        metadata: dict,
        source_url: Optional[str] = None,
        source_title: Optional[str] = None,
    ) -> Document:
        """创建 Document 对象（chunk_index/total_chunks 由调用方统一设置）"""
        doc_id = self._generate_doc_id_str(
            source_id,
            metadata.get("chunk_type", ""),
            content,
        )
        return Document(
            doc_id=doc_id,
            content=content,
            metadata=metadata,
            source_type="wiki",
            source_url=source_url,
            source_title=source_title,
            chunk_index=0,
            total_chunks=1,
        )

    def _format_attributes(self, infobox: dict, stats: dict, title: str) -> str:
        """将 infobox 和 stats 合并为属性文本块

        优先显示 infobox（原始中文字段），stats 追加标准化数值（去重）。
        """
        if not infobox and not stats:
            return ""

        lines = [f"【{title} 属性信息】"]

        # infobox：原始键值（来自 Wiki 信息框）
        if infobox:
            for k, v in infobox.items():
                lines.append(f"{k}：{v}")

        # stats：标准化数值，跳过 infobox 已覆盖的字段
        if stats:
            infobox_values_str = " ".join(str(v) for v in infobox.values())
            for k, v in stats.items():
                display = self.STAT_DISPLAY_NAMES.get(k, k)
                if str(v) not in infobox_values_str:
                    lines.append(f"{display}：{v}")

        return "\n".join(lines)

    def _format_recipe(self, recipe: dict, page_title: str) -> str:
        """将配方字典格式化为可检索的文本"""
        parts = []

        result = (
            recipe.get("result")
            or recipe.get("name")
            or recipe.get("结果", "")
        )
        header = f"【{page_title} 配方】产出：{result}" if result else f"【{page_title} 配方】"
        parts.append(header)

        # 材料列表
        ingredients = recipe.get("ingredients") or recipe.get("材料", [])
        if ingredients:
            if isinstance(ingredients, list):
                ing_strs = []
                for ing in ingredients:
                    if isinstance(ing, dict):
                        name = ing.get("name") or ing.get("材料", "")
                        count = ing.get("count") or ing.get("数量", "")
                        ing_strs.append(f"{name}×{count}" if count else name)
                    else:
                        ing_strs.append(str(ing))
                parts.append(f"材料：{', '.join(s for s in ing_strs if s)}")
            else:
                parts.append(f"材料：{ingredients}")

        # 制作站
        station = recipe.get("station") or recipe.get("制作站") or recipe.get("cook_station", "")
        if station:
            parts.append(f"制作站：{station}")

        # 烹饪时间
        cook_time = recipe.get("cook_time") or recipe.get("烹饪时间", "")
        if cook_time:
            parts.append(f"烹饪时间：{cook_time} 秒")

        # 至少要有材料或制作站才算有效配方
        return "\n".join(parts) if len(parts) > 1 else ""

    def _clean_text(self, text: str) -> str:
        """清洗文本（去除 Wiki 标记残留）"""
        if not text:
            return ""
        text = re.sub(r"\s+", " ", text)
        text = re.sub(r"\[\[(?:[^\]|]+\|)?([^\]]+)\]\]", r"\1", text)
        text = re.sub(r"\{\{[^}]+\}\}", "", text)
        text = re.sub(r"<[^>]+>", "", text)
        text = re.sub(r"[​‌‍]", "", text)
        return text.strip()

    def _split_text(self, text: str) -> list[str]:
        """按语义分块文本（递归字符分块 + 滑动窗口）"""
        if len(text) <= self.chunk_size:
            return [text]

        chunks = []
        paragraphs = self._split_by_sections(text)
        current_chunk = ""

        for para in paragraphs:
            if len(current_chunk) + len(para) <= self.chunk_size:
                current_chunk += para + "\n"
            else:
                if current_chunk:
                    chunks.append(current_chunk.strip())

                if len(para) > self.chunk_size:
                    sub_chunks = self._split_long_paragraph(para)
                    chunks.extend(sub_chunks[:-1])
                    current_chunk = sub_chunks[-1] + "\n" if sub_chunks else ""
                else:
                    current_chunk = para + "\n"

        if current_chunk.strip():
            chunks.append(current_chunk.strip())

        if self.chunk_overlap > 0 and len(chunks) > 1:
            chunks = self._add_overlap(chunks)

        return chunks

    def _split_by_sections(self, text: str) -> list[str]:
        """按段落（空行）分割，合并短行"""
        parts = text.split("\n")
        paragraphs = []
        current = ""

        for part in parts:
            part = part.strip()
            if not part:
                if current:
                    paragraphs.append(current)
                    current = ""
            else:
                current = (current + " " + part) if current else part

        if current:
            paragraphs.append(current)

        return paragraphs

    def _split_long_paragraph(self, text: str) -> list[str]:
        """按句子（。！？.!?）分割超长段落"""
        chunks = []
        sentences = re.split(r"([。！？.!?])", text)
        current = ""

        for i in range(0, len(sentences) - 1, 2):
            sentence = sentences[i] + (sentences[i + 1] if i + 1 < len(sentences) else "")
            if len(current) + len(sentence) <= self.chunk_size:
                current += sentence
            else:
                if current:
                    chunks.append(current)
                current = sentence

        if current:
            chunks.append(current)

        return chunks if chunks else [text]

    def _add_overlap(self, chunks: list[str]) -> list[str]:
        """为相邻块添加重叠（取上一块末尾内容）"""
        overlapped = []
        for i, chunk in enumerate(chunks):
            if i > 0:
                overlap_text = chunks[i - 1][-self.chunk_overlap:]
                # 找到空格边界（对英文有效；中文直接按字符截取）
                space_pos = overlap_text.find(" ")
                if space_pos > 0:
                    overlap_text = overlap_text[space_pos + 1:]
                chunk = overlap_text + " " + chunk
            overlapped.append(chunk)
        return overlapped

    def _generate_doc_id(self, page_id: int, chunk_index: int) -> str:
        """生成文档 ID（旧接口，基于 page_id）"""
        return hashlib.md5(f"{page_id}_{chunk_index}".encode()).hexdigest()[:16]

    def _generate_doc_id_str(self, source_id: str, chunk_type: str, content: str) -> str:
        """生成文档 ID（新接口，基于 source_id + chunk_type + 内容前缀）"""
        key = f"{source_id}_{chunk_type}_{content[:100]}"
        return hashlib.md5(key.encode()).hexdigest()[:16]
