import logging
import os
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from langchain_core.documents import Document
from langchain_core.embeddings import Embeddings
from langchain_text_splitters import RecursiveCharacterTextSplitter

from config.settings import settings as app_settings
from core.security_utils import sanitize_for_log

logger = logging.getLogger(__name__)


def _create_embeddings() -> Optional[Embeddings]:
    try:
        from langchain_community.embeddings.fastembed import FastEmbedEmbeddings

        return FastEmbedEmbeddings(model_name=app_settings.embedding_model)
    except Exception as e:
        logger.warning("FastEmbed unavailable: %s", sanitize_for_log(e))
        try:
            from langchain_openai import OpenAIEmbeddings

            if app_settings.openai_api_key:
                return OpenAIEmbeddings()
        except Exception as e2:
            logger.warning("OpenAI embeddings unavailable: %s", sanitize_for_log(e2))
    return None


class KnowledgeStore:
    """
    Lightweight Chroma store for general knowledge documents (CE-safe).
    - Supports text/markdown ingestion
    - Chunks content using settings.chunk_size/overlap
    - Provides retrieval for QA with citations
    """

    def __init__(
        self,
        persist_directory: Optional[str] = None,
        collection_name: str = "knowledge",
    ):
        self.persist_directory = Path(persist_directory or os.path.join(os.getcwd(), "chroma_db"))
        self.collection_name = collection_name
        self.embeddings: Optional[Embeddings] = _create_embeddings()

        self.persist_directory.mkdir(parents=True, exist_ok=True)

        # CE-safe: use pure in-memory fallback to avoid native crashes on Windows
        self.vector_store = None
        self._docs: List[Document] = []

        self.splitter = RecursiveCharacterTextSplitter(
            chunk_size=app_settings.chunk_size,
            chunk_overlap=app_settings.chunk_overlap,
            length_function=len,
        )

    def ingest_text(self, text: str, source: str, metadata: Optional[Dict[str, Any]] = None) -> int:
        """
        Ingest plain text content into the knowledge store.
        Returns number of chunks added.
        """
        docs = self.splitter.create_documents([text])
        for i, d in enumerate(docs):
            d.metadata = {
                "source": source,
                "chunk_index": i,
                **(metadata or {}),
            }

        # In-memory fallback
        self._docs.extend(docs)
        return len(docs)

    def ingest_text_segments(
        self,
        *,
        segments: List[tuple[str, Dict[str, Any]]],
        source: str,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> int:
        chunk_index = 0
        docs_to_add: List[Document] = []
        for text, segment_metadata in segments:
            docs = self.splitter.create_documents([text])
            for d in docs:
                d.metadata = {
                    "source": source,
                    "chunk_index": chunk_index,
                    **(metadata or {}),
                    **(segment_metadata or {}),
                }
                chunk_index += 1
            docs_to_add.extend(docs)

        self._docs.extend(docs_to_add)
        return len(docs_to_add)

    def similarity_search_with_score(self, query: str, k: int = 5) -> List[Tuple[Document, float]]:
        # In-memory scoring by simple term overlap
        tokens = [t for t in query.lower().split() if t]
        scored: List[Tuple[Document, float]] = []
        for d in getattr(self, "_docs", []):
            txt = d.page_content.lower()
            score = float(sum(1 for t in tokens if t in txt))
            if score > 0:
                scored.append((d, score))
        scored.sort(key=lambda x: x[1], reverse=True)
        return scored[:k]

    def get_stats(self) -> Dict[str, Any]:
        count = 0
        count = len(getattr(self, "_docs", []))
        provider = type(self.embeddings).__name__ if self.embeddings is not None else "none"
        return {
            "collection": self.collection_name,
            "persist_directory": str(self.persist_directory),
            "documents": count,
            "embedding_provider": provider,
        }

    def clear(self) -> int:
        removed = len(getattr(self, "_docs", []))
        self._docs = []
        return removed
