"""
Hybrid retriever combining semantic and keyword search.

This module provides advanced retrieval capabilities by combining:
- Semantic search (vector similarity)
- Keyword search (BM25)
- Metadata filtering
- Result reranking
"""

from typing import List, Optional, Dict, Any
from langchain_core.documents import Document
from langchain_core.retrievers import BaseRetriever
from langchain_core.callbacks import CallbackManagerForRetrieverRun

from .chroma_store import ChromaPropertyStore


class HybridPropertyRetriever(BaseRetriever):
    """
    Hybrid retriever combining semantic and keyword search.

    This retriever provides better results by:
    1. Using semantic search for understanding intent
    2. Applying metadata filters for precise criteria
    3. Ensuring diversity in results
    """

    vector_store: ChromaPropertyStore
    k: int = 5
    search_type: str = "mmr"  # Maximum Marginal Relevance
    fetch_k: int = 20
    lambda_mult: float = 0.5  # Diversity parameter for MMR

    class Config:
        arbitrary_types_allowed = True

    def _get_relevant_documents(
        self,
        query: str,
        *,
        run_manager: Optional[CallbackManagerForRetrieverRun] = None,
    ) -> List[Document]:
        """
        Retrieve relevant documents for a query.

        Args:
            query: Search query
            run_manager: Optional callback manager

        Returns:
            List of relevant documents
        """
        # Extract metadata filters from query (simple keyword-based)
        filters = self._extract_filters(query)

        # Perform semantic search
        if self.search_type == "mmr":
            # Use MMR for diversity
            retriever = self.vector_store.get_retriever(
                search_type="mmr",
                k=self.k,
                fetch_k=self.fetch_k,
                lambda_mult=self.lambda_mult,
            )
            results = retriever.get_relevant_documents(query)

        else:
            # Use regular similarity search
            results_with_scores = self.vector_store.search(
                query=query,
                k=self.k,
                filter=filters if filters else None
            )
            results = [doc for doc, score in results_with_scores]

        # Apply post-filtering if needed
        if filters:
            results = self._apply_filters(results, filters)

        return results[:self.k]

    def _extract_filters(self, query: str) -> Dict[str, Any]:
        """
        Extract metadata filters from query text.

        This is a simple implementation. In production, you might use
        an LLM to extract structured criteria from natural language.

        Args:
            query: Search query

        Returns:
            Dictionary of filters
        """
        filters = {}
        query_lower = query.lower()

        # Extract city
        cities = ["warsaw", "krakow", "gdansk", "wroclaw", "poznan"]
        for city in cities:
            if city in query_lower:
                filters["city"] = city.title()
                break

        # Extract parking requirement
        if any(word in query_lower for word in ["parking", "garage"]):
            filters["has_parking"] = True

        # Extract garden requirement
        if "garden" in query_lower:
            filters["has_garden"] = True

        # Extract pool requirement
        if "pool" in query_lower:
            filters["has_pool"] = True

        return filters

    def _apply_filters(
        self,
        documents: List[Document],
        filters: Dict[str, Any]
    ) -> List[Document]:
        """
        Apply filters to documents.

        Args:
            documents: List of documents
            filters: Filters to apply

        Returns:
            Filtered list of documents
        """
        filtered = []

        for doc in documents:
            metadata = doc.metadata

            # Check each filter
            match = True
            for key, value in filters.items():
                if key in metadata and metadata[key] != value:
                    match = False
                    break

            if match:
                filtered.append(doc)

        return filtered


class AdvancedPropertyRetriever(HybridPropertyRetriever):
    """
    Advanced retriever with price range filtering and sorting.

    This extends the hybrid retriever with additional capabilities
    for price-based filtering and result sorting.
    """

    min_price: Optional[float] = None
    max_price: Optional[float] = None
    sort_by: Optional[str] = None  # 'price', 'price_per_sqm', 'rooms'
    sort_ascending: bool = True

    def _get_relevant_documents(
        self,
        query: str,
        *,
        run_manager: Optional[CallbackManagerForRetrieverRun] = None,
    ) -> List[Document]:
        """Retrieve and filter documents with advanced criteria."""

        # Get base results
        results = super()._get_relevant_documents(query, run_manager=run_manager)

        # Apply price filters
        if self.min_price is not None or self.max_price is not None:
            results = self._filter_by_price(results)

        # Sort results if requested
        if self.sort_by:
            results = self._sort_results(results)

        return results

    def _filter_by_price(self, documents: List[Document]) -> List[Document]:
        """Filter documents by price range."""
        filtered = []

        for doc in documents:
            price = doc.metadata.get("price", 0)

            if self.min_price is not None and price < self.min_price:
                continue

            if self.max_price is not None and price > self.max_price:
                continue

            filtered.append(doc)

        return filtered

    def _sort_results(self, documents: List[Document]) -> List[Document]:
        """Sort documents by specified field."""

        if not documents:
            return documents

        try:
            sorted_docs = sorted(
                documents,
                key=lambda doc: doc.metadata.get(self.sort_by, 0),
                reverse=not self.sort_ascending
            )
            return sorted_docs

        except Exception as e:
            print(f"Warning: Could not sort results: {e}")
            return documents


def create_retriever(
    vector_store: ChromaPropertyStore,
    k: int = 5,
    search_type: str = "mmr",
    min_price: Optional[float] = None,
    max_price: Optional[float] = None,
    sort_by: Optional[str] = None,
    **kwargs
) -> BaseRetriever:
    """
    Factory function to create a retriever.

    Args:
        vector_store: ChromaPropertyStore instance
        k: Number of results to return
        search_type: Type of search ('similarity', 'mmr')
        min_price: Minimum price filter
        max_price: Maximum price filter
        sort_by: Field to sort by
        **kwargs: Additional retriever parameters

    Returns:
        Configured retriever instance
    """
    # Use advanced retriever if price filters or sorting specified
    if min_price is not None or max_price is not None or sort_by is not None:
        return AdvancedPropertyRetriever(
            vector_store=vector_store,
            k=k,
            search_type=search_type,
            min_price=min_price,
            max_price=max_price,
            sort_by=sort_by,
            **kwargs
        )

    # Use hybrid retriever otherwise
    return HybridPropertyRetriever(
        vector_store=vector_store,
        k=k,
        search_type=search_type,
        **kwargs
    )
