"""
ChromaDB vector store implementation with persistence.

This module provides a persistent vector store for property embeddings
using ChromaDB with FastEmbed embeddings.
"""

import os
import logging
from pathlib import Path
from typing import List, Optional, Dict, Any
from datetime import datetime
import platform
import pandas as pd

import streamlit as st
from langchain_chroma import Chroma
try:
    from chromadb.config import Settings as ChromaSettings
except Exception:
    ChromaSettings = None
from langchain_core.documents import Document
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_core.retrievers import BaseRetriever
try:
    from langchain_community.embeddings.fastembed import FastEmbedEmbeddings
except Exception:
    FastEmbedEmbeddings = None

from data.schemas import Property, PropertyCollection
from config.settings import settings

# Configure logger
logger = logging.getLogger(__name__)


class ChromaPropertyStore:
    """
    Persistent vector store for property data using ChromaDB.

    This class handles:
    - Property embedding and storage
    - Semantic search
    - Metadata filtering
    - Persistence to disk
    """

    def __init__(
        self,
        persist_directory: Optional[str] = None,
        collection_name: str = "properties",
        embedding_model: str = "BAAI/bge-small-en-v1.5"
    ):
        """
        Initialize ChromaDB vector store.

        Args:
            persist_directory: Directory for persistent storage (default: ./chroma_db)
            collection_name: Name of the collection
            embedding_model: FastEmbed model to use
        """
        # Set default persist directory
        if persist_directory is None:
            persist_directory = os.path.join(os.getcwd(), "chroma_db")

        self.persist_directory = Path(persist_directory)
        self.collection_name = collection_name

        # Create persist directory if it doesn't exist
        self.persist_directory.mkdir(parents=True, exist_ok=True)

        # Initialize embeddings
        self.embeddings = self._create_embeddings(embedding_model)

        # Initialize or load vector store
        self.vector_store = self._initialize_vector_store()

        # Text splitter for long descriptions
        self.text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=1000,
            chunk_overlap=200,
            length_function=len,
        )

        self._documents: List[Document] = []

    @st.cache_resource
    def _create_embeddings(_self, model_name: str):
        try:
            is_windows = platform.system().lower() == "windows"
            force_fastembed = os.getenv("CHROMA_FORCE_FASTEMBED") == "1" or os.getenv("FORCE_FASTEMBED") == "1"
            if FastEmbedEmbeddings is not None and not is_windows:
                return FastEmbedEmbeddings(model_name=model_name)
            elif FastEmbedEmbeddings is not None and is_windows and force_fastembed:
                return FastEmbedEmbeddings(model_name=model_name)
            elif FastEmbedEmbeddings is not None and is_windows:
                st.warning("FastEmbed is disabled on Windows for stability. Set CHROMA_FORCE_FASTEMBED=1 to force enable.")
        except Exception as e:
            st.warning(f"FastEmbed initialization failed: {e}")

        try:
            from config import settings
            if settings.openai_api_key:
                from langchain_openai import OpenAIEmbeddings
                return OpenAIEmbeddings()
        except Exception as e:
            st.warning(f"OpenAI embeddings unavailable: {e}")

        return None

    def _initialize_vector_store(self) -> Chroma:
        """Initialize or load existing ChromaDB vector store."""
        if self.embeddings is None:
            st.warning("Embeddings unavailable; vector store features are disabled")
            return None

        try:
            client_settings = None
            if ChromaSettings is not None:
                # Disable telemetry, allow local init; leave other defaults
                client_settings = ChromaSettings(anonymized_telemetry=False)

            force_persist = os.getenv("CHROMA_FORCE_PERSIST") == "1"
            is_windows = platform.system().lower() == "windows"
            use_persist = force_persist or not is_windows

            if use_persist:
                vector_store = Chroma(
                    collection_name=self.collection_name,
                    embedding_function=self.embeddings,
                    persist_directory=str(self.persist_directory),
                    client_settings=client_settings,
                )

                # Check if collection has any documents
                collection_stats = vector_store._collection.count()
                logger.info(f"Loaded existing ChromaDB collection with {collection_stats} documents")
                return vector_store
            else:
                # Directly use in-memory on platforms where persistence is disabled
                vector_store = Chroma(
                    collection_name=self.collection_name,
                    embedding_function=self.embeddings,
                )
                logger.info("Using in-memory Chroma vector store (persistence disabled for this platform)")
                st.warning("Persistent vector store unavailable; using in-memory store")
                return vector_store

        except BaseException as e:
            logger.warning(f"Persistent Chroma init failed: {e}")

            # Fallback: in-memory Chroma (no persistence)
            try:
                vector_store = Chroma(
                    collection_name=self.collection_name,
                    embedding_function=self.embeddings,
                )
                logger.info("Initialized in-memory Chroma vector store (no persistence)")
                st.warning("Persistent vector store unavailable; using in-memory store")
                return vector_store
            except BaseException as e2:
                logger.error(f"In-memory Chroma init failed: {e2}")
                raise

    def property_to_document(self, property: Property) -> Document:
        """
        Convert Property to LangChain Document.

        Args:
            property: Property instance

        Returns:
            Document with property text and metadata
        """
        # Create comprehensive text representation
        text = property.to_search_text()

        # Create metadata (must be JSON-serializable)
        def _nf(x):
            return float(x) if (x is not None and not pd.isna(x)) else None

        metadata = {
            "id": property.id or "unknown",
            "city": property.city,
            "price": _nf(property.price),
            "rooms": (_nf(property.rooms) or 0.0),
            "bathrooms": (_nf(property.bathrooms) or 0.0),
            "has_parking": property.has_parking,
            "has_garden": property.has_garden,
            "has_pool": property.has_pool,
            "has_garage": property.has_garage,
            "has_elevator": property.has_elevator,
            "property_type": property.property_type.value if hasattr(property.property_type, "value") else str(property.property_type),
            "source_url": property.source_url or "",
        }

        # Add optional fields if present
        if property.neighborhood:
            metadata["neighborhood"] = property.neighborhood

        if property.area_sqm is not None and not pd.isna(property.area_sqm):
            metadata["area_sqm"] = float(property.area_sqm)

        if property.price_per_sqm is not None and not pd.isna(property.price_per_sqm):
            metadata["price_per_sqm"] = float(property.price_per_sqm)

        if property.negotiation_rate:
            metadata["negotiation_rate"] = property.negotiation_rate.value if hasattr(property.negotiation_rate, "value") else str(property.negotiation_rate)

        # Capture extra fields from the original row to preserve information
        try:
            all_data = property.model_dump(exclude_none=True)
            base_keys = set(metadata.keys()) | {"neighborhood", "price_per_sqm"}
            extras = {k: v for k, v in all_data.items() if k not in base_keys}
            if extras:
                metadata["chroma_dp"] = extras
        except Exception:
            pass

        return Document(
            page_content=text,
            metadata=metadata
        )

    def add_properties(
        self,
        properties: List[Property],
        batch_size: int = 100
    ) -> int:
        """
        Add properties to the vector store.

        Args:
            properties: List of Property instances
            batch_size: Number of properties to process at once

        Returns:
            Number of properties added
        """
        documents = []

        for prop in properties:
            try:
                doc = self.property_to_document(prop)
                documents.append(doc)
                self._documents.append(doc)
            except Exception as e:
                logger.warning(f"Skipping property {prop.id}: {e}")
                continue

        if not documents:
            logger.warning("No valid documents to add")
            return 0

        # If vector store is unavailable, keep documents in fallback cache only
        if self.vector_store is None:
            logger.info(f"Vector store disabled; cached {len(documents)} properties in memory")
            return len(documents)

        # Add documents in batches
        total_added = 0
        for i in range(0, len(documents), batch_size):
            batch = documents[i:i + batch_size]

            try:
                self.vector_store.add_documents(batch)
                total_added += len(batch)
                logger.info(f"Added batch {i // batch_size + 1}: {len(batch)} properties")

            except Exception as e:
                logger.error(f"Error adding batch: {e}")
                continue

        if total_added > 0:
            logger.info(f"Total properties added to vector store: {total_added}")
            return total_added
        else:
            logger.info(f"Stored {len(documents)} properties in fallback cache")
            return len(documents)

    def add_property_collection(
        self,
        collection: PropertyCollection,
        replace_existing: bool = False
    ) -> int:
        """
        Add a PropertyCollection to the vector store.

        Args:
            collection: PropertyCollection instance
            replace_existing: Whether to clear existing data first

        Returns:
            Number of properties added
        """
        if replace_existing:
            self.clear()

        return self.add_properties(collection.properties)

    def search(
        self,
        query: str,
        k: int = 5,
        filter: Optional[Dict[str, Any]] = None,
        **kwargs
    ) -> List[tuple[Document, float]]:
        """
        Search for properties by semantic similarity.

        Args:
            query: Search query
            k: Number of results to return
            filter: Optional metadata filter
            **kwargs: Additional search parameters

        Returns:
            List of (Document, score) tuples
        """
        try:
            if self.vector_store is not None:
                results = self.vector_store.similarity_search_with_score(
                    query=query,
                    k=k,
                    filter=filter,
                    **kwargs
                )
                return results
            else:
                raise RuntimeError("no_vector_store")
        except Exception as e:
            try:
                q = [t for t in query.lower().split() if t]
                scored: List[tuple[Document, float]] = []
                for d in self._documents:
                    txt = d.page_content.lower()
                    s = float(sum(1 for t in q if t in txt))
                    if s > 0:
                        scored.append((d, s))
                scored.sort(key=lambda x: x[1], reverse=True)
                return scored[:k]
            except Exception:
                logger.error(f"Search error: {e}")
                return []

    def search_by_metadata(
        self,
        city: Optional[str] = None,
        min_price: Optional[float] = None,
        max_price: Optional[float] = None,
        min_rooms: Optional[float] = None,
        has_parking: Optional[bool] = None,
        k: int = 5
    ) -> List[Document]:
        """
        Search properties by metadata filters.

        Args:
            city: Filter by city
            min_price: Minimum price
            max_price: Maximum price
            min_rooms: Minimum number of rooms
            has_parking: Filter by parking availability
            k: Number of results

        Returns:
            List of matching documents
        """
        filter_dict = {}

        if city:
            filter_dict["city"] = city

        if has_parking is not None:
            filter_dict["has_parking"] = has_parking

        # Note: ChromaDB has limited support for range queries
        # For complex filtering, retrieve more results and filter in Python
        results = self.vector_store.similarity_search(
            query="",  # Empty query for metadata-only search
            k=k * 5,  # Retrieve more for filtering
            filter=filter_dict if filter_dict else None
        )

        # Apply additional filters
        filtered = []
        for doc in results:
            metadata = doc.metadata

            # Price filters
            if min_price is not None and metadata.get("price", 0) < min_price:
                continue
            if max_price is not None and metadata.get("price", float('inf')) > max_price:
                continue

            # Rooms filter
            if min_rooms is not None and metadata.get("rooms", 0) < min_rooms:
                continue

            filtered.append(doc)

            if len(filtered) >= k:
                break

        return filtered

    def get_retriever(
        self,
        search_type: str = "mmr",
        k: int = 5,
        fetch_k: int = 20,
        **kwargs
    ):
        """
        Get a LangChain retriever for this vector store.

        Args:
            search_type: Type of search ('similarity', 'mmr', 'similarity_score_threshold')
            k: Number of documents to return
            fetch_k: Number of documents to fetch for MMR
            **kwargs: Additional retriever parameters

        Returns:
            LangChain retriever instance
        """
        stats = self.get_stats()
        total = stats.get("total_documents", 0)
        if self.vector_store is not None and total > 0:
            return self.vector_store.as_retriever(
                search_type=search_type,
                search_kwargs={
                    "k": k,
                    "fetch_k": fetch_k,
                    **kwargs
                }
            )
        else:
            class FallbackRetriever(BaseRetriever):
                def __init__(self, docs: List[Document], kk: int):
                    self.docs = docs
                    self.kk = kk
                def get_relevant_documents(self, query: str) -> List[Document]:
                    q = [t for t in query.lower().split() if t]
                    scored: List[tuple[Document, float]] = []
                    for d in self.docs:
                        txt = d.page_content.lower()
                        s = float(sum(1 for t in q if t in txt))
                        if s > 0:
                            scored.append((d, s))
                    scored.sort(key=lambda x: x[1], reverse=True)
                    return [d for d, _s in scored[:self.kk]]
            return FallbackRetriever(self._documents, k)

    def clear(self):
        """Clear all documents from the vector store."""
        try:
            if self.vector_store is not None:
                self.vector_store.delete_collection()
                self.vector_store = self._initialize_vector_store()
            self._documents = []
            logger.info("Vector store cleared")

        except Exception as e:
            logger.error(f"Error clearing vector store: {e}")
            self._documents = []

    def get_stats(self) -> Dict[str, Any]:
        """
        Get statistics about the vector store.

        Returns:
            Dictionary with store statistics
        """
        try:
            if self.vector_store is not None:
                count = self.vector_store._collection.count()
                if count == 0:
                    count = len(self._documents)
            else:
                count = len(self._documents)

            emb_cls = type(self.embeddings).__name__ if self.embeddings is not None else "None"
            if "OpenAIEmbeddings" in emb_cls:
                emb_provider = "openai"
                emb_model = getattr(self.embeddings, "model", "openai")
            elif "FastEmbedEmbeddings" in emb_cls:
                emb_provider = "fastembed"
                emb_model = getattr(self.embeddings, "model_name", "BAAI/bge-small-en-v1.5")
            else:
                emb_provider = "none"
                emb_model = "none"

            return {
                "total_documents": count,
                "collection_name": self.collection_name,
                "persist_directory": str(self.persist_directory),
                "embedding_model": emb_model,
                "embedding_provider": emb_provider,
            }
        except Exception as e:
            return {"error": str(e), "total_documents": len(self._documents)}

    def delete_by_source(self, source_url: str):
        """
        Delete all properties from a specific source.

        Args:
            source_url: Source URL to filter by
        """
        try:
            self.vector_store.delete(
                filter={"source_url": source_url}
            )
            logger.info(f"Deleted properties from source: {source_url}")

        except Exception as e:
            logger.error(f"Error deleting by source: {e}")

    def __repr__(self) -> str:
        stats = self.get_stats()
        return (
            f"<ChromaPropertyStore: {stats.get('total_documents', 0)} documents, "
            f"collection='{self.collection_name}'>"
        )


@st.cache_resource
def get_vector_store(
    persist_directory: Optional[str] = None,
    collection_name: str = "properties",
    embedding_model: Optional[str] = None,
) -> ChromaPropertyStore:
    """
    Get cached vector store instance.

    Args:
        persist_directory: Directory for persistent storage
        collection_name: Collection name
        embedding_model: Embedding model identifier

    Returns:
        ChromaPropertyStore instance
    """
    return ChromaPropertyStore(
        persist_directory=persist_directory,
        collection_name=collection_name,
        embedding_model=embedding_model or settings.embedding_model,
    )
