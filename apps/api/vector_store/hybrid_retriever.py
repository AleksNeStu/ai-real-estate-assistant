"""
Hybrid retriever combining semantic and keyword search.

This module provides advanced retrieval capabilities by combining:
- Semantic search (vector similarity)
- Keyword search (BM25)
- Metadata filtering
- Result reranking
"""

import logging
from typing import Any, Callable, Dict, List, Optional, Tuple

from langchain_core.callbacks import CallbackManagerForRetrieverRun
from langchain_core.documents import Document
from langchain_core.retrievers import BaseRetriever

from core.security_utils import sanitize_for_log

from .chroma_store import ChromaPropertyStore
from .reranker import StrategicReranker

logger = logging.getLogger(__name__)


class HybridPropertyRetriever(BaseRetriever):
    """
    Hybrid retriever combining semantic and keyword search.

    This retriever provides better results by:
    1. Using semantic search for understanding intent
    2. Applying metadata filters for precise criteria
    3. Ensuring diversity in results
    4. Reranking results based on strategy (optional)
    """

    vector_store: ChromaPropertyStore
    reranker: Optional[StrategicReranker] = None
    strategy: str = "balanced"
    k: int = 5
    search_type: str = "mmr"  # Maximum Marginal Relevance
    fetch_k: int = 20
    lambda_mult: float = 0.5  # Diversity parameter for MMR
    alpha: float = 0.7  # Weight for vector search (vs keyword) in hybrid search
    forced_filters: Optional[Dict[str, Any]] = None

    class Config:
        arbitrary_types_allowed = True

    def search_with_filters(
        self, query: str, filters: Dict[str, Any], k: Optional[int] = None
    ) -> List[Document]:
        """
        Search with explicit filters (bypassing internal extraction).

        Args:
            query: Search query
            filters: Metadata filters
            k: Optional override for k

        Returns:
            List of documents
        """
        effective_k = k if k is not None else self.k

        # Merge with forced filters
        if self.forced_filters:
            for key, val in self.forced_filters.items():
                filters[key] = val

        # Use hybrid search
        results_with_scores = self.vector_store.hybrid_search(
            query=query, filters=filters, k=effective_k, alpha=self.alpha
        )

        results = [doc for doc, _ in results_with_scores]

        # Apply post-filtering just in case (though hybrid_search should handle it)
        # We rely on hybrid_search to handle Chroma filters, but complex logic
        # might need post-processing. For now, assume hybrid_search is sufficient
        # for retrieval, and we trust it.

        # If we are AdvancedPropertyRetriever, we might want to apply extra logic?
        # No, search_with_filters is intended to be a direct entry point.
        # But if we want sorting/ranges that Chroma doesn't support fully?
        # The _build_chroma_filter handles ranges.

        return results

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
        filters: Dict[str, Any] = self._extract_filters(query)
        if self.forced_filters:
            for forced_key, forced_val in self.forced_filters.items():
                filters[forced_key] = forced_val
        candidate_k = max(self.fetch_k, self.k)

        # Perform search
        initial_scores: List[float]

        # Always use hybrid search if available
        # Note: MMR logic is harder to combine with hybrid scoring (BM25)
        # If search_type is MMR, we might skip hybrid scoring or apply it after?
        # For now, let's prioritize hybrid search over MMR if it's "similarity"
        # If it's MMR, we use vector store retriever.

        if self.search_type == "mmr":
            # Use MMR for diversity (Vector only)
            retriever = self.vector_store.get_retriever(
                search_type="mmr",
                k=candidate_k,
                fetch_k=max(self.fetch_k, candidate_k),
                lambda_mult=self.lambda_mult,
                filter=filters if filters else None,
            )
            results = retriever.invoke(query)
            initial_scores = [1.0 - (i * 0.01) for i in range(len(results))]

        elif self.search_type == "similarity":
            results_with_scores = self.vector_store.search(
                query=query,
                k=candidate_k,
                filter=filters if filters else None,
            )
            results = [doc for doc, _score in results_with_scores]
            initial_scores = [float(score) for _doc, score in results_with_scores]

        else:
            # Use Hybrid Search
            results_with_scores = self.vector_store.hybrid_search(
                query=query, filters=filters, k=candidate_k, alpha=self.alpha
            )
            results = [doc for doc, score in results_with_scores]
            initial_scores = [score for doc, score in results_with_scores]

        def apply_simple_filters(
            docs: List[Document],
            scores: List[float],
            raw_filters: Dict[str, Any],
        ) -> tuple[List[Document], List[float]]:
            simple = {k: v for k, v in raw_filters.items() if not isinstance(v, dict)}
            if not simple:
                return docs, scores
            score_map = {id(d): s for d, s in zip(docs, scores, strict=False)}
            filtered_docs = self._apply_filters(docs, simple)
            filtered_scores = [score_map.get(id(d), 0.0) for d in filtered_docs]
            return filtered_docs, filtered_scores

        results, initial_scores = apply_simple_filters(results, initial_scores, filters)

        # Apply Reranking if enabled
        if self.reranker:
            try:
                reranked = self.reranker.rerank_with_strategy(
                    query=query,
                    documents=results,
                    strategy=self.strategy,
                    initial_scores=initial_scores,
                    k=self.k,
                )
                results = [doc for doc, score in reranked]
            except Exception as e:
                logger.warning("Reranking failed: %s", sanitize_for_log(e))

        return results[: self.k]

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
        filters: Dict[str, Any] = {}
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

        # Extract listing type (rent/sale) from common phrases
        rent_keywords = ["rent", "rental", "for rent", "lease", "wynajem"]
        sale_keywords = ["sale", "for sale", "buy", "purchase", "sprzedaż"]
        if any(word in query_lower for word in rent_keywords):
            filters["listing_type"] = "rent"
        elif any(word in query_lower for word in sale_keywords):
            filters["listing_type"] = "sale"

        return filters

    def _apply_filters(self, documents: List[Document], filters: Dict[str, Any]) -> List[Document]:
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
                if metadata.get(key) != value:
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
    center_lat: Optional[float] = None
    center_lon: Optional[float] = None
    radius_km: Optional[float] = None
    year_built_min: Optional[int] = None
    year_built_max: Optional[int] = None
    energy_certs: Optional[List[str]] = None

    def _get_relevant_documents(
        self,
        query: str,
        *,
        run_manager: Optional[CallbackManagerForRetrieverRun] = None,
    ) -> List[Document]:
        filters: Dict[str, Any] = self._extract_filters(query)
        if self.forced_filters:
            for forced_key, forced_val in self.forced_filters.items():
                filters[forced_key] = forced_val
        candidate_k = max(self.fetch_k, self.k)

        # Perform search
        initial_scores: List[float]

        if self.search_type == "mmr":
            retriever = self.vector_store.get_retriever(
                search_type="mmr",
                k=candidate_k,
                fetch_k=max(self.fetch_k, candidate_k),
                lambda_mult=self.lambda_mult,
                filter=filters if filters else None,
            )
            results = retriever.invoke(query)
            initial_scores = [1.0 - (i * 0.01) for i in range(len(results))]
        elif self.search_type == "similarity":
            results_with_scores = self.vector_store.search(
                query=query,
                k=candidate_k,
                filter=filters if filters else None,
            )
            results = [doc for doc, _score in results_with_scores]
            initial_scores = [float(score) for _doc, score in results_with_scores]
        else:
            # Use Hybrid Search
            results_with_scores = self.vector_store.hybrid_search(
                query=query, filters=filters, k=candidate_k, alpha=self.alpha
            )
            results = [doc for doc, score in results_with_scores]
            initial_scores = [score for doc, score in results_with_scores]

        # Helper to filter results and scores together
        def apply_filtering(
            docs: List[Document],
            scores: List[float],
            filter_func: Callable[[List[Document]], List[Document]],
        ) -> Tuple[List[Document], List[float]]:
            if not docs:
                return [], []

            # Map doc ID to score
            score_map = {id(d): s for d, s in zip(docs, scores, strict=False)}

            # Apply filter
            filtered_docs = filter_func(docs)

            # Reconstruct scores
            filtered_scores = [score_map.get(id(d), 0.0) for d in filtered_docs]
            return filtered_docs, filtered_scores

        simple_filters = {k: v for k, v in filters.items() if not isinstance(v, dict)}
        if simple_filters:
            results, initial_scores = apply_filtering(
                results,
                initial_scores,
                lambda docs: self._apply_filters(docs, simple_filters),
            )

        # Note: hybrid_search already applies most filters (price, rooms, etc) via Chroma
        # But AdvancedRetriever might have explicit properties set (min_price, etc)
        # that are NOT in the extracted filters if they came from UI/Config, not query.
        # So we must still apply them.

        if self.min_price is not None or self.max_price is not None:
            results, initial_scores = apply_filtering(
                results, initial_scores, self._filter_by_price
            )

        if (
            self.center_lat is not None
            and self.center_lon is not None
            and self.radius_km is not None
        ):
            results, initial_scores = apply_filtering(results, initial_scores, self._filter_by_geo)

        if self.year_built_min is not None or self.year_built_max is not None:
            results, initial_scores = apply_filtering(
                results, initial_scores, self._filter_by_year_built
            )

        if self.energy_certs:
            results, initial_scores = apply_filtering(
                results, initial_scores, self._filter_by_energy_certs
            )

        # Rerank BEFORE sorting?
        # Usually reranking provides a better sort.
        # But if explicit sort_by is set (e.g. "price"), user wants that order.
        # If sort_by is NOT set, we use reranking score.

        if self.reranker and not self.sort_by:
            try:
                reranked = self.reranker.rerank_with_strategy(
                    query=query,
                    documents=results,
                    strategy=self.strategy,
                    initial_scores=initial_scores,
                    k=self.k,
                )
                results = [doc for doc, score in reranked]
                # No need to update initial_scores as we are done with scoring
            except Exception as e:
                logger.warning("Reranking failed: %s", sanitize_for_log(e))

        if self.sort_by:
            results = self._sort_results(results)

        return results[: self.k]

    def _filter_by_price(self, documents: List[Document]) -> List[Document]:
        """Filter documents by price range."""
        filtered = []

        for doc in documents:
            raw_price = doc.metadata.get("price")
            try:
                price = float(raw_price) if raw_price is not None else None
            except (TypeError, ValueError):
                price = None
            if price is None:
                continue

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
            missing_value = float("inf") if self.sort_ascending else float("-inf")

            def _key(doc: Document) -> float:
                raw_val = doc.metadata.get(self.sort_by)
                if raw_val is None:
                    return missing_value
                try:
                    return float(raw_val)
                except (TypeError, ValueError):
                    return missing_value

            sorted_docs = sorted(
                documents,
                key=_key,
                reverse=not self.sort_ascending,
            )
            return sorted_docs

        except Exception as e:
            logger.warning("Could not sort results: %s", e)
            return documents

    def _filter_by_year_built(self, documents: List[Document]) -> List[Document]:
        filtered: List[Document] = []
        for doc in documents:
            raw_year = doc.metadata.get("year_built")
            try:
                year = int(raw_year) if raw_year is not None else None
            except (TypeError, ValueError):
                year = None
            if year is None:
                continue

            if self.year_built_min is not None and year < int(self.year_built_min):
                continue
            if self.year_built_max is not None and year > int(self.year_built_max):
                continue

            filtered.append(doc)
        return filtered

    def _filter_by_energy_certs(self, documents: List[Document]) -> List[Document]:
        allow = {str(x).strip().lower() for x in (self.energy_certs or []) if str(x).strip()}
        if not allow:
            return documents

        filtered: List[Document] = []
        for doc in documents:
            raw_cert = doc.metadata.get("energy_cert")
            cert = str(raw_cert).strip().lower() if raw_cert is not None else ""
            if cert in allow:
                filtered.append(doc)
        return filtered

    def _filter_by_geo(self, documents: List[Document]) -> List[Document]:
        if self.center_lat is None or self.center_lon is None or self.radius_km is None:
            return []

        filtered = []
        import math

        lat1 = math.radians(self.center_lat)
        lon1 = math.radians(self.center_lon)
        for doc in documents:
            lat = doc.metadata.get("lat") if "lat" in doc.metadata else doc.metadata.get("latitude")
            lon = (
                doc.metadata.get("lon") if "lon" in doc.metadata else doc.metadata.get("longitude")
            )
            if lat is None or lon is None:
                continue
            lat2 = math.radians(float(lat))
            lon2 = math.radians(float(lon))
            dlat = lat2 - lat1
            dlon = lon2 - lon1
            a = math.sin(dlat / 2) ** 2 + math.cos(lat1) * math.cos(lat2) * math.sin(dlon / 2) ** 2
            c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
            dist_km = 6371.0 * c
            if dist_km <= self.radius_km:
                filtered.append(doc)
        return filtered


def create_retriever(
    vector_store: ChromaPropertyStore,
    k: int = 5,
    search_type: str = "mmr",
    min_price: Optional[float] = None,
    max_price: Optional[float] = None,
    sort_by: Optional[str] = None,
    sort_ascending: bool = True,
    center_lat: Optional[float] = None,
    center_lon: Optional[float] = None,
    radius_km: Optional[float] = None,
    year_built_min: Optional[int] = None,
    year_built_max: Optional[int] = None,
    energy_certs: Optional[List[str]] = None,
    forced_filters: Optional[Dict[str, Any]] = None,
    reranker: Optional[StrategicReranker] = None,
    strategy: str = "balanced",
    **kwargs: Any,
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
        sort_ascending: Whether to sort ascending when sort_by is set
        reranker: Optional StrategicReranker instance
        strategy: Reranking strategy
        **kwargs: Additional retriever parameters

    Returns:
        Configured retriever instance
    """
    # Use advanced retriever if price filters or sorting specified
    if (
        min_price is not None
        or max_price is not None
        or sort_by is not None
        or (center_lat is not None and center_lon is not None and radius_km is not None)
        or year_built_min is not None
        or year_built_max is not None
        or energy_certs
    ):
        return AdvancedPropertyRetriever(
            vector_store=vector_store,
            k=k,
            search_type=search_type,
            min_price=min_price,
            max_price=max_price,
            sort_by=sort_by,
            sort_ascending=sort_ascending,
            center_lat=center_lat,
            center_lon=center_lon,
            radius_km=radius_km,
            year_built_min=year_built_min,
            year_built_max=year_built_max,
            energy_certs=energy_certs,
            forced_filters=forced_filters,
            reranker=reranker,
            strategy=strategy,
            **kwargs,
        )

    # Use hybrid retriever otherwise
    return HybridPropertyRetriever(
        vector_store=vector_store,
        k=k,
        search_type=search_type,
        forced_filters=forced_filters,
        reranker=reranker,
        strategy=strategy,
        **kwargs,
    )
