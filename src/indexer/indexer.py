"""向量索引器 - 使用LlamaIndex和Chroma"""

from pathlib import Path
from typing import Optional

import chromadb
from llama_index.core import (
    Document as LlamaDocument,
    VectorStoreIndex,
    StorageContext,
    Settings as LlamaSettings,
)
from llama_index.core.node_parser import SentenceSplitter
from llama_index.embeddings.huggingface import HuggingFaceEmbedding
from llama_index.vector_stores.chroma import ChromaVectorStore

from config import settings, VECTOR_DB_DIR
from src.utils.logger import logger
from src.utils.models import Document


class VectorIndexer:
    """向量索引器"""

    def __init__(self, collection_name: str = "starve_knowledge"):
        self.config = settings.embedding
        self.collection_name = collection_name
        self.db_path = VECTOR_DB_DIR / "chroma"

        # 初始化Embedding模型
        self._init_embedding_model()

        # 初始化向量数据库
        self._init_vector_store()

    def _init_embedding_model(self):
        """初始化Embedding模型"""
        device = self.config.device
        if device == "auto":
            import torch
            device = "cuda" if torch.cuda.is_available() else "cpu"

        logger.info(f"加载Embedding模型: {self.config.model_name}, 设备: {device}")

        self.embed_model = HuggingFaceEmbedding(
            model_name=self.config.model_name,
            device=device,
            trust_remote_code=True,
        )

        # 设置全局Embedding模型
        LlamaSettings.embed_model = self.embed_model
        LlamaSettings.chunk_size = self.config.chunk_size
        LlamaSettings.chunk_overlap = self.config.chunk_overlap

    def _init_vector_store(self):
        """初始化Chroma向量数据库"""
        self.db_path.mkdir(parents=True, exist_ok=True)

        self.chroma_client = chromadb.PersistentClient(
            path=str(self.db_path)
        )

        self.collection = self.chroma_client.get_or_create_collection(
            name=self.collection_name,
            metadata={"description": "饥荒游戏知识库"}
        )

        self.vector_store = ChromaVectorStore(
            chroma_collection=self.collection
        )

        self.storage_context = StorageContext.from_defaults(
            vector_store=self.vector_store
        )

        logger.info(f"向量数据库初始化完成，集合: {self.collection_name}")

    def index_documents(self, documents: list[Document]) -> VectorStoreIndex:
        """将文档索引到向量数据库"""
        # 转换为LlamaIndex文档格式
        llama_docs = []
        for doc in documents:
            llama_doc = LlamaDocument(
                text=doc.content,
                doc_id=doc.doc_id,
                metadata={
                    "source_url": doc.source_url,
                    "source_title": doc.source_title,
                    "source_type": doc.source_type,
                    "chunk_index": doc.chunk_index,
                    **doc.metadata
                }
            )
            llama_docs.append(llama_doc)

        logger.info(f"开始索引 {len(llama_docs)} 个文档...")

        # 创建索引
        index = VectorStoreIndex.from_documents(
            llama_docs,
            storage_context=self.storage_context,
            show_progress=True,
        )

        logger.info("索引创建完成")
        return index

    def load_index(self) -> Optional[VectorStoreIndex]:
        """加载已有索引"""
        try:
            index = VectorStoreIndex.from_vector_store(
                vector_store=self.vector_store,
            )
            logger.info("成功加载已有索引")
            return index
        except Exception as e:
            logger.warning(f"加载索引失败: {e}")
            return None

    def get_collection_stats(self) -> dict:
        """获取集合统计信息"""
        return {
            "name": self.collection_name,
            "count": self.collection.count(),
        }

    def clear_collection(self):
        """清空集合"""
        self.chroma_client.delete_collection(self.collection_name)
        self._init_vector_store()
        logger.info(f"集合 {self.collection_name} 已清空")
