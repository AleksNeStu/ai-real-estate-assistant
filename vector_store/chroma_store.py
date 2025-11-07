"""
ChromaDB vector store implementation with persistence.

This module provides a persistent vector store for property embeddings
using ChromaDB with FastEmbed embeddings.
"""

import os
from pathlib import Path
from typing import List, Optional, Dict, Any
from datetime import datetime

import streamlit as st
from langchain_chroma import Chroma
from langchain_core.documents import Document
from langchain_community.embeddings.fastembed import FastEmbedEmbeddings
from langchain.text_splitter import RecursiveCharacterTextSplitter

from data.schemas import Property, PropertyCollection


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

    @st.cache_resource
    def _create_embeddings(_self, model_name: str):
        """Create FastEmbed embeddings (cached)."""
        return FastEmbedEmbeddings(model_name=model_name)

    def _initialize_vector_store(self) -> Chroma:
        """Initialize or load existing ChromaDB vector store."""
        try:
            # Try to load existing store
            vector_store = Chroma(
                collection_name=self.collection_name,
                embedding_function=self.embeddings,
                persist_directory=str(self.persist_directory)
            )

            # Check if collection has any documents
            collection_stats = vector_store._collection.count()
            print(f"Loaded existing ChromaDB collection with {collection_stats} documents")

            return vector_store

        except Exception as e:
            print(f"Creating new ChromaDB collection: {e}")

            # Create new store
            vector_store = Chroma(
                collection_name=self.collection_name,
                embedding_function=self.embeddings,
                persist_directory=str(self.persist_directory)
            )

            return vector_store

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
        metadata = {
            "id": property.id or "unknown",
            "city": property.city,
            "price": float(property.price),
            "rooms": float(property.rooms),
            "bathrooms": float(property.bathrooms),
            "has_parking": property.has_parking,
            "has_garden": property.has_garden,
            "has_pool": property.has_pool,
            "has_garage": property.has_garage,
            "property_type": property.property_type.value,
            "source_url": property.source_url or "",
        }

        # Add optional fields if present
        if property.neighborhood:
            metadata["neighborhood"] = property.neighborhood

        if property.area_sqm:
            metadata["area_sqm"] = float(property.area_sqm)

        if property.price_per_sqm:
            metadata["price_per_sqm"] = float(property.price_per_sqm)

        if property.negotiation_rate:
            metadata["negotiation_rate"] = property.negotiation_rate.value

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
            except Exception as e:
                print(f"Warning: Skipping property {prop.id}: {e}")
                continue

        if not documents:
            print("No valid documents to add")
            return 0

        # Add documents in batches
        total_added = 0
        for i in range(0, len(documents), batch_size):
            batch = documents[i:i + batch_size]

            try:
                self.vector_store.add_documents(batch)
                total_added += len(batch)
                print(f"Added batch {i // batch_size + 1}: {len(batch)} properties")

            except Exception as e:
                print(f"Error adding batch: {e}")
                continue

        print(f"Total properties added to vector store: {total_added}")
        return total_added

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
            results = self.vector_store.similarity_search_with_score(
                query=query,
                k=k,
                filter=filter,
                **kwargs
            )
            return results

        except Exception as e:
            print(f"Search error: {e}")
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
        return self.vector_store.as_retriever(
            search_type=search_type,
            search_kwargs={
                "k": k,
                "fetch_k": fetch_k,
                **kwargs
            }
        )

    def clear(self):
        """Clear all documents from the vector store."""
        try:
            # Delete the collection
            self.vector_store.delete_collection()

            # Reinitialize
            self.vector_store = self._initialize_vector_store()

            print("Vector store cleared")

        except Exception as e:
            print(f"Error clearing vector store: {e}")

    def get_stats(self) -> Dict[str, Any]:
        """
        Get statistics about the vector store.

        Returns:
            Dictionary with store statistics
        """
        try:
            count = self.vector_store._collection.count()

            return {
                "total_documents": count,
                "collection_name": self.collection_name,
                "persist_directory": str(self.persist_directory),
                "embedding_model": "BAAI/bge-small-en-v1.5",
            }

        except Exception as e:
            return {"error": str(e)}

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
            print(f"Deleted properties from source: {source_url}")

        except Exception as e:
            print(f"Error deleting by source: {e}")

    def __repr__(self) -> str:
        stats = self.get_stats()
        return (
            f"<ChromaPropertyStore: {stats.get('total_documents', 0)} documents, "
            f"collection='{self.collection_name}'>"
        )


@st.cache_resource
def get_vector_store(
    persist_directory: Optional[str] = None,
    collection_name: str = "properties"
) -> ChromaPropertyStore:
    """
    Get cached vector store instance.

    Args:
        persist_directory: Directory for persistent storage
        collection_name: Collection name

    Returns:
        ChromaPropertyStore instance
    """
    return ChromaPropertyStore(
        persist_directory=persist_directory,
        collection_name=collection_name
    )
