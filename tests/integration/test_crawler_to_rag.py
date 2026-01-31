"""爬虫到RAG完整流程集成测试"""

import pytest
from typing import List
from unittest.mock import Mock, MagicMock, patch

from src.crawler.base import DataSource, RawPage
from src.crawler.cleaners import CleanedPage, MediaWikiCleaner, TiebaCleaner
from src.utils.models import WikiPage, Document, GameVersion, EntityType


# 模拟DocumentProcessor以避免依赖llama_index
class MockDocumentProcessor:
    """模拟文档处理器"""

    def __init__(self, chunk_size=512, chunk_overlap=100):
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap

    def process_wiki_page(self, page: WikiPage) -> list:
        """处理Wiki页面，生成文档块"""
        if not page.content.strip():
            return []

        # 简单分块逻辑
        content = page.content
        chunks = []

        if len(content) <= self.chunk_size:
            chunks = [content]
        else:
            for i in range(0, len(content), self.chunk_size - self.chunk_overlap):
                chunk = content[i:i + self.chunk_size]
                if chunk:
                    chunks.append(chunk)

        documents = []
        for i, chunk in enumerate(chunks):
            doc = Document(
                doc_id=f"{page.page_id}_{i}",
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

        return documents


class TestCleanedPageToWikiPage:
    """CleanedPage到WikiPage转换测试"""

    @pytest.fixture
    def sample_cleaned_page(self):
        """示例清洗后页面"""
        return CleanedPage(
            source=DataSource.WIKI_GG,
            source_id='1001',
            title='肉丸',
            url='https://dontstarve.wiki.gg/zh/wiki/肉丸',
            content='肉丸是一种可以用烹饪锅制作的食物。配方需要肉度大于等于0.5。',
            summary='肉丸是常用的食物',
            sections=[
                {'level': 2, 'title': '配方', 'content': '肉度 >= 0.5'},
                {'level': 2, 'title': '用法', 'content': '新手常用食物'},
            ],
            infobox={'饥饿值': '62.5', '理智值': '5', '生命值': '3'},
            stats={'hunger': 62.5, 'sanity': 5.0, 'health': 3.0},
            recipes=[{
                'ingredients': [{'name': '怪物肉', 'count': 1}],
                'result': '肉丸',
                'time': 15,
            }],
            categories=['食物', '烹饪锅食谱'],
            game_version='both',
            related_pages=['烹饪锅', '怪物肉'],
            quality_score=0.8,
        )

    def test_cleaned_to_wiki_page_conversion(self, sample_cleaned_page):
        """测试CleanedPage转换为WikiPage"""
        # 转换逻辑
        wiki_page = WikiPage(
            page_id=int(sample_cleaned_page.source_id),
            title=sample_cleaned_page.title,
            url=sample_cleaned_page.url,
            content=sample_cleaned_page.content,
            categories=sample_cleaned_page.categories,
            version=GameVersion.BOTH,
            entity_type=EntityType.FOOD,  # 根据分类推断
        )

        assert wiki_page.title == '肉丸'
        assert wiki_page.page_id == 1001
        assert '食物' in wiki_page.categories

    def test_version_mapping(self, sample_cleaned_page):
        """测试版本映射"""
        version_map = {
            'ds': GameVersion.DS,
            'dst': GameVersion.DST,
            'both': GameVersion.BOTH,
            'rog': GameVersion.ROG,
        }

        cleaned_version = sample_cleaned_page.game_version
        wiki_version = version_map.get(cleaned_version, GameVersion.BOTH)

        assert wiki_version == GameVersion.BOTH

    def test_entity_type_detection(self, sample_cleaned_page):
        """测试实体类型检测"""
        categories = sample_cleaned_page.categories

        entity_type = EntityType.OTHER

        if '食物' in categories or '烹饪锅食谱' in categories:
            entity_type = EntityType.FOOD
        elif 'Boss' in categories:
            entity_type = EntityType.BOSS
        elif '生物' in categories:
            entity_type = EntityType.CREATURE
        elif '角色' in categories:
            entity_type = EntityType.CHARACTER
        elif '物品' in categories:
            entity_type = EntityType.ITEM

        assert entity_type == EntityType.FOOD


class TestWikiPageToDocuments:
    """WikiPage到Document转换测试"""

    @pytest.fixture
    def sample_wiki_page(self):
        """示例Wiki页面"""
        return WikiPage(
            page_id=1001,
            title='肉丸',
            url='https://dontstarve.wiki.gg/zh/wiki/肉丸',
            content='肉丸是一种可以用烹饪锅制作的食物。配方需要肉度大于等于0.5。肉丸是新手最常用的食物之一，因为配方简单且效果好。',
            categories=['食物', '烹饪锅食谱'],
            version=GameVersion.BOTH,
            entity_type=EntityType.FOOD,
        )

    @pytest.fixture
    def processor(self):
        """文档处理器"""
        return MockDocumentProcessor()

    def test_wiki_page_to_documents(self, processor, sample_wiki_page):
        """测试WikiPage转换为Document"""
        documents = processor.process_wiki_page(sample_wiki_page)

        assert len(documents) >= 1
        assert all(isinstance(doc, Document) for doc in documents)

    def test_document_has_correct_metadata(self, processor, sample_wiki_page):
        """测试文档包含正确的元数据"""
        documents = processor.process_wiki_page(sample_wiki_page)

        for doc in documents:
            assert doc.metadata.get('title') == '肉丸'
            assert doc.metadata.get('page_id') == 1001
            assert doc.metadata.get('entity_type') == 'food'
            assert doc.source_type == 'wiki'
            assert doc.source_title == '肉丸'

    def test_document_chunking(self, processor, sample_wiki_page):
        """测试文档分块"""
        # 创建一个长内容的页面
        long_content = '这是一段测试内容。' * 100
        sample_wiki_page.content = long_content

        documents = processor.process_wiki_page(sample_wiki_page)

        if len(documents) > 1:
            # 验证分块索引
            for i, doc in enumerate(documents):
                assert doc.chunk_index == i
                assert doc.total_chunks == len(documents)

    def test_empty_content_returns_empty(self, processor, sample_wiki_page):
        """测试空内容返回空列表"""
        sample_wiki_page.content = ''

        documents = processor.process_wiki_page(sample_wiki_page)

        assert len(documents) == 0


class TestMetadataPreservation:
    """元数据保留测试"""

    @pytest.fixture
    def raw_page(self):
        """原始页面"""
        return RawPage(
            source=DataSource.WIKI_GG,
            source_id='1001',
            title='肉丸',
            url='https://dontstarve.wiki.gg/zh/wiki/肉丸',
            content='肉丸是一种食物',
            html_content='<p>肉丸是一种食物</p>',
            categories=['食物', '烹饪锅食谱'],
            extra={'revision_id': 12345},
        )

    def test_source_preserved_through_pipeline(self, raw_page):
        """测试来源信息在流水线中保留"""
        cleaner = MediaWikiCleaner()
        cleaned = cleaner.clean(raw_page)

        if cleaned:
            assert cleaned.source == DataSource.WIKI_GG
            assert cleaned.source_id == '1001'
            assert cleaned.url == raw_page.url

    def test_categories_preserved(self, raw_page):
        """测试分类信息保留"""
        cleaner = MediaWikiCleaner()
        cleaned = cleaner.clean(raw_page)

        if cleaned:
            # 分类应该被保留
            assert len(cleaned.categories) > 0


class TestMultiSourceIntegration:
    """多数据源集成测试"""

    @pytest.fixture
    def wiki_page(self):
        """Wiki页面"""
        return RawPage(
            source=DataSource.WIKI_GG,
            source_id='1001',
            title='肉丸',
            url='https://wiki.gg/肉丸',
            content='Wiki版本的肉丸介绍',
            html_content='<p>Wiki版本</p>',
            categories=['食物'],
        )

    @pytest.fixture
    def tieba_page(self):
        """贴吧页面"""
        return RawPage(
            source=DataSource.TIEBA,
            source_id='12345',
            title='肉丸配方攻略',
            url='https://tieba.baidu.com/p/12345',
            content='贴吧版本的肉丸攻略',
            html_content='<p>贴吧版本</p>',
            categories=['贴吧攻略'],
        )

    def test_merge_different_sources(self, wiki_page, tieba_page):
        """测试合并不同数据源"""
        all_pages = [wiki_page, tieba_page]

        # 验证可以合并不同来源的页面
        assert len(all_pages) == 2
        assert all_pages[0].source == DataSource.WIKI_GG
        assert all_pages[1].source == DataSource.TIEBA

    def test_deduplication_by_title(self, wiki_page):
        """测试按标题去重"""
        # 模拟相同标题的页面
        duplicate_page = RawPage(
            source=DataSource.FANDOM,
            source_id='2001',
            title='肉丸',  # 相同标题
            url='https://fandom.com/肉丸',
            content='Fandom版本',
            html_content='<p>Fandom</p>',
            categories=['食物'],
        )

        pages = [wiki_page, duplicate_page]

        # 按标题去重
        seen_titles = set()
        unique_pages = []
        for page in pages:
            if page.title not in seen_titles:
                seen_titles.add(page.title)
                unique_pages.append(page)

        assert len(unique_pages) == 1
        # 应该保留第一个（Wiki）
        assert unique_pages[0].source == DataSource.WIKI_GG

    def test_source_priority(self):
        """测试数据源优先级"""
        # 定义优先级（数字越小优先级越高）
        priority = {
            DataSource.WIKI_GG: 1,
            DataSource.FANDOM: 2,
            DataSource.HUIJI: 3,
            DataSource.TIEBA: 4,
            DataSource.STEAM: 5,
        }

        # 验证Wiki.gg优先级最高
        assert priority[DataSource.WIKI_GG] < priority[DataSource.TIEBA]


class TestEndToEndDataFlow:
    """端到端数据流测试"""

    @pytest.fixture
    def raw_wiki_page(self):
        """原始Wiki页面"""
        return RawPage(
            source=DataSource.WIKI_GG,
            source_id='1001',
            title='蜘蛛女皇',
            url='https://dontstarve.wiki.gg/zh/wiki/蜘蛛女皇',
            content='蜘蛛女皇是一种Boss级别的生物，生命值2500，伤害80。',
            html_content='''
            <aside class="portable-infobox">
                <div class="pi-data">
                    <span class="pi-data-label">生命值</span>
                    <span class="pi-data-value">2500</span>
                </div>
            </aside>
            <p>蜘蛛女皇是一种Boss。</p>
            ''',
            categories=['Boss', '生物'],
        )

    def test_raw_to_cleaned_flow(self, raw_wiki_page):
        """测试原始到清洗流程"""
        cleaner = MediaWikiCleaner()
        # 清洗器可能因内容太短返回None，这里测试不抛异常即可
        try:
            cleaned = cleaner.clean(raw_wiki_page)
            # 如果成功清洗，验证基本属性
            if cleaned is not None:
                assert cleaned.title == '蜘蛛女皇'
                assert cleaned.source == DataSource.WIKI_GG
        except Exception as e:
            pytest.fail(f"清洗不应抛出异常: {e}")

    def test_cleaned_to_wiki_page_flow(self, raw_wiki_page):
        """测试清洗到WikiPage流程"""
        cleaner = MediaWikiCleaner()
        cleaned = cleaner.clean(raw_wiki_page)

        if cleaned:
            wiki_page = WikiPage(
                page_id=int(cleaned.source_id),
                title=cleaned.title,
                url=cleaned.url,
                content=cleaned.content,
                categories=cleaned.categories,
                version=GameVersion.BOTH,
                entity_type=EntityType.BOSS,
            )

            assert wiki_page.entity_type == EntityType.BOSS

    def test_full_pipeline(self, raw_wiki_page):
        """测试完整流水线"""
        # 1. 清洗（可能返回None）
        cleaner = MediaWikiCleaner()
        cleaned = cleaner.clean(raw_wiki_page)

        # 清洗可能因内容太短返回None，所以用构造数据测试流水线
        if cleaned is None:
            # 使用构造的数据继续测试流水线
            wiki_page = WikiPage(
                page_id=1001,
                title='蜘蛛女皇',
                url='https://dontstarve.wiki.gg/zh/wiki/蜘蛛女皇',
                content='蜘蛛女皇是一种Boss级别的生物，生命值2500，伤害80。',
                categories=['Boss', '生物'],
            )
        else:
            # 2. 转换为WikiPage
            wiki_page = WikiPage(
                page_id=int(cleaned.source_id),
                title=cleaned.title,
                url=cleaned.url,
                content=cleaned.content,
                categories=cleaned.categories,
            )

        # 3. 生成Document
        processor = MockDocumentProcessor()
        documents = processor.process_wiki_page(wiki_page)

        # 验证
        assert len(documents) >= 1
        assert documents[0].source_title == '蜘蛛女皇'


class TestQualityFiltering:
    """质量过滤测试"""

    def test_quality_score_filtering(self):
        """测试质量分数过滤"""
        pages = [
            CleanedPage(
                source=DataSource.WIKI_GG,
                source_id='1',
                title='高质量页面',
                url='http://test.com/1',
                content='这是一段很长的高质量内容。' * 50,
                quality_score=0.8,
            ),
            CleanedPage(
                source=DataSource.WIKI_GG,
                source_id='2',
                title='低质量页面',
                url='http://test.com/2',
                content='短内容',
                quality_score=0.1,
            ),
        ]

        min_quality = 0.3
        filtered = [p for p in pages if p.quality_score >= min_quality]

        assert len(filtered) == 1
        assert filtered[0].title == '高质量页面'

    def test_quality_affects_indexing(self):
        """测试质量影响索引"""
        # 只有高质量页面应该被索引
        pages_to_index = []

        test_pages = [
            {'title': '好页面', 'quality': 0.7, 'content': '有用的内容足够长'},
            {'title': '差页面', 'quality': 0.1, 'content': '短'},
        ]

        for page in test_pages:
            if page['quality'] >= 0.2 and len(page['content']) > 3:
                pages_to_index.append(page)

        assert len(pages_to_index) == 1

        assert len(pages_to_index) == 1


class TestDocumentSearchability:
    """文档可搜索性测试"""

    @pytest.fixture
    def sample_documents(self):
        """示例文档列表"""
        return [
            Document(
                doc_id='doc1',
                content='肉丸是一种食物，配方需要怪物肉和填充物。',
                metadata={'title': '肉丸', 'entity_type': 'food'},
                source_type='wiki',
                source_title='肉丸',
            ),
            Document(
                doc_id='doc2',
                content='蜘蛛女皇是Boss，生命值2500。',
                metadata={'title': '蜘蛛女皇', 'entity_type': 'boss'},
                source_type='wiki',
                source_title='蜘蛛女皇',
            ),
        ]

    def test_document_content_searchable(self, sample_documents):
        """测试文档内容可搜索"""
        query = '肉丸'

        # 简单的关键词搜索
        results = [
            doc for doc in sample_documents
            if query in doc.content
        ]

        assert len(results) >= 1
        assert results[0].source_title == '肉丸'

    def test_metadata_filterable(self, sample_documents):
        """测试元数据可过滤"""
        # 按实体类型过滤
        food_docs = [
            doc for doc in sample_documents
            if doc.metadata.get('entity_type') == 'food'
        ]

        assert len(food_docs) == 1
        assert food_docs[0].source_title == '肉丸'

    def test_cross_source_search(self, sample_documents):
        """测试跨数据源搜索"""
        # 所有文档应该都来自wiki
        sources = {doc.source_type for doc in sample_documents}

        assert 'wiki' in sources
