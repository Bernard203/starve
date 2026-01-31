"""文档处理器 - 分块与预处理"""

import hashlib
import re
from typing import Generator

from config import settings
from src.utils.logger import logger
from src.utils.models import WikiPage, Document


class DocumentProcessor:
    """文档处理器：分块、清洗、转换"""

    def __init__(self):
        self.config = settings.embedding
        self.chunk_size = self.config.chunk_size
        self.chunk_overlap = self.config.chunk_overlap

    def process_wiki_page(self, page: WikiPage) -> list[Document]:
        """处理Wiki页面，生成文档块"""
        # 清洗文本
        clean_content = self._clean_text(page.content)

        if not clean_content.strip():
            logger.warning(f"页面 {page.title} 内容为空，跳过")
            return []

        # 分块
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
        """批量处理Wiki页面"""
        for page in pages:
            docs = self.process_wiki_page(page)
            for doc in docs:
                yield doc

    def _clean_text(self, text: str) -> str:
        """清洗文本"""
        if not text:
            return ""

        # 移除多余空白
        text = re.sub(r"\s+", " ", text)

        # 移除Wiki残留标记
        text = re.sub(r"\[\[(?:[^\]|]+\|)?([^\]]+)\]\]", r"\1", text)  # [[link|text]] -> text
        text = re.sub(r"\{\{[^}]+\}\}", "", text)  # 移除模板
        text = re.sub(r"<[^>]+>", "", text)  # 移除HTML标签

        # 移除特殊字符
        text = re.sub(r"[​‌‍]", "", text)  # 零宽字符

        return text.strip()

    def _split_text(self, text: str) -> list[str]:
        """按语义分块文本"""
        if len(text) <= self.chunk_size:
            return [text]

        chunks = []

        # 首先按段落/章节分割
        paragraphs = self._split_by_sections(text)

        current_chunk = ""
        for para in paragraphs:
            if len(current_chunk) + len(para) <= self.chunk_size:
                current_chunk += para + "\n"
            else:
                if current_chunk:
                    chunks.append(current_chunk.strip())

                # 如果单个段落超过chunk_size，进一步分割
                if len(para) > self.chunk_size:
                    sub_chunks = self._split_long_paragraph(para)
                    chunks.extend(sub_chunks[:-1])
                    current_chunk = sub_chunks[-1] + "\n" if sub_chunks else ""
                else:
                    current_chunk = para + "\n"

        if current_chunk.strip():
            chunks.append(current_chunk.strip())

        # 添加重叠
        if self.chunk_overlap > 0 and len(chunks) > 1:
            chunks = self._add_overlap(chunks)

        return chunks

    def _split_by_sections(self, text: str) -> list[str]:
        """按章节/段落分割"""
        # 按换行符分割
        parts = text.split("\n")

        # 合并短段落
        paragraphs = []
        current = ""
        for part in parts:
            part = part.strip()
            if not part:
                if current:
                    paragraphs.append(current)
                    current = ""
            else:
                if current:
                    current += " " + part
                else:
                    current = part

        if current:
            paragraphs.append(current)

        return paragraphs

    def _split_long_paragraph(self, text: str) -> list[str]:
        """分割超长段落"""
        chunks = []

        # 按句子分割
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
        """为分块添加重叠"""
        overlapped = []

        for i, chunk in enumerate(chunks):
            if i > 0:
                # 从上一个块获取重叠内容
                prev_chunk = chunks[i - 1]
                overlap_text = prev_chunk[-self.chunk_overlap:]

                # 找到合适的分割点（不要截断单词）
                space_pos = overlap_text.find(" ")
                if space_pos > 0:
                    overlap_text = overlap_text[space_pos + 1:]

                chunk = overlap_text + " " + chunk

            overlapped.append(chunk)

        return overlapped

    def _generate_doc_id(self, page_id: int, chunk_index: int) -> str:
        """生成文档ID"""
        content = f"{page_id}_{chunk_index}"
        return hashlib.md5(content.encode()).hexdigest()[:16]
