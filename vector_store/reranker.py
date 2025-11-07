"""
Result reranking for improved search quality.

This module provides reranking capabilities to improve the relevance
of retrieved documents by considering additional factors beyond
just vector similarity.
"""

from typing import List, Tuple, Optional
from langchain_core.documents import Document
import re


class PropertyReranker:
    """
    Reranker for property search results.

    This reranker improves result quality by considering:
    - Query-document relevance (semantic)
    - Exact keyword matches
    - Metadata alignment with user preferences
    - Result diversity
    - Property quality signals
    """

    def __init__(
        self,
        boost_exact_matches: float = 1.5,
        boost_metadata_match: float = 1.3,
        boost_quality_signals: float = 1.2,
        diversity_penalty: float = 0.9
    ):
        """
        Initialize reranker.

        Args:
            boost_exact_matches: Boost factor for exact keyword matches
            boost_metadata_match: Boost factor for metadata criteria matches
            boost_quality_signals: Boost factor for quality signals
            diversity_penalty: Penalty for very similar results
        """
        self.boost_exact_matches = boost_exact_matches
        self.boost_metadata_match = boost_metadata_match
        self.boost_quality_signals = boost_quality_signals
        self.diversity_penalty = diversity_penalty

    def rerank(
        self,
        query: str,
        documents: List[Document],
        initial_scores: Optional[List[float]] = None,
        user_preferences: Optional[dict] = None,
        k: Optional[int] = None
    ) -> List[Tuple[Document, float]]:
        """
        Rerank documents based on multiple relevance signals.

        Args:
            query: Original search query
            documents: Retrieved documents
            initial_scores: Initial similarity scores (if available)
            user_preferences: User preferences for boosting
            k: Number of results to return (if None, return all)

        Returns:
            List of (document, score) tuples, sorted by reranked score
        """
        if not documents:
            return []

        # If no initial scores provided, assume equal
        if initial_scores is None:
            initial_scores = [1.0] * len(documents)

        # Ensure scores and documents match
        if len(initial_scores) != len(documents):
            initial_scores = [1.0] * len(documents)

        # Calculate reranked scores
        reranked = []

        for doc, base_score in zip(documents, initial_scores):
            # Start with base score
            score = base_score

            # Boost for exact keyword matches
            exact_match_boost = self._calculate_exact_match_boost(query, doc)
            score *= (1.0 + exact_match_boost * self.boost_exact_matches)

            # Boost for metadata alignment
            if user_preferences:
                metadata_boost = self._calculate_metadata_boost(doc, user_preferences)
                score *= (1.0 + metadata_boost * self.boost_metadata_match)

            # Boost for quality signals
            quality_boost = self._calculate_quality_boost(doc)
            score *= (1.0 + quality_boost * self.boost_quality_signals)

            reranked.append((doc, score))

        # Sort by score
        reranked.sort(key=lambda x: x[1], reverse=True)

        # Apply diversity penalty if many results
        if len(reranked) > 5:
            reranked = self._apply_diversity_penalty(reranked)

        # Return top k if specified
        if k is not None:
            reranked = reranked[:k]

        return reranked

    def _calculate_exact_match_boost(self, query: str, doc: Document) -> float:
        """
        Calculate boost for exact keyword matches.

        Args:
            query: Search query
            doc: Document

        Returns:
            Boost factor (0.0 to 1.0)
        """
        # Extract important keywords from query (remove common words)
        stop_words = {
            'the', 'a', 'an', 'and', 'or', 'but', 'in', 'on', 'at',
            'to', 'for', 'of', 'with', 'by', 'from', 'show', 'find',
            'me', 'i', 'want', 'need', 'looking'
        }

        query_words = set(
            word.lower()
            for word in re.findall(r'\b\w+\b', query)
            if word.lower() not in stop_words and len(word) > 2
        )

        if not query_words:
            return 0.0

        # Check for matches in document content and metadata
        content = doc.page_content.lower()
        metadata_str = ' '.join(str(v).lower() for v in doc.metadata.values())
        combined_text = content + ' ' + metadata_str

        matches = sum(1 for word in query_words if word in combined_text)
        boost = matches / len(query_words)

        return min(boost, 1.0)  # Cap at 1.0

    def _calculate_metadata_boost(self, doc: Document, preferences: dict) -> float:
        """
        Calculate boost for metadata alignment with user preferences.

        Args:
            doc: Document
            preferences: User preferences dict

        Returns:
            Boost factor (0.0 to 1.0)
        """
        metadata = doc.metadata
        matches = 0
        total_preferences = 0

        # Check price preference
        if 'max_price' in preferences:
            total_preferences += 1
            doc_price = metadata.get('price', float('inf'))
            if doc_price <= preferences['max_price']:
                matches += 1

        if 'min_price' in preferences:
            total_preferences += 1
            doc_price = metadata.get('price', 0)
            if doc_price >= preferences['min_price']:
                matches += 1

        # Check city preference
        if 'city' in preferences:
            total_preferences += 1
            if metadata.get('city', '').lower() == preferences['city'].lower():
                matches += 1

        # Check rooms preference
        if 'rooms' in preferences:
            total_preferences += 1
            if metadata.get('rooms') == preferences['rooms']:
                matches += 1

        # Check amenities
        amenity_prefs = ['has_parking', 'has_garden', 'has_pool', 'has_garage']
        for amenity in amenity_prefs:
            if amenity in preferences and preferences[amenity]:
                total_preferences += 1
                if metadata.get(amenity, False):
                    matches += 1

        if total_preferences == 0:
            return 0.0

        boost = matches / total_preferences
        return boost

    def _calculate_quality_boost(self, doc: Document) -> float:
        """
        Calculate boost based on property quality signals.

        Args:
            doc: Document

        Returns:
            Boost factor (0.0 to 1.0)
        """
        metadata = doc.metadata
        quality_score = 0.0
        max_score = 0.0

        # Has important amenities
        amenities = ['has_parking', 'has_garden', 'has_balcony', 'has_elevator']
        for amenity in amenities:
            max_score += 0.1
            if metadata.get(amenity, False):
                quality_score += 0.1

        # Good price per sqm (if available)
        if 'price_per_sqm' in metadata and 'price' in metadata:
            max_score += 0.2
            price_per_sqm = metadata['price_per_sqm']
            # Lower price per sqm is better (assuming reasonable range)
            if 10 <= price_per_sqm <= 30:  # Reasonable range
                quality_score += 0.2
            elif 30 < price_per_sqm <= 40:
                quality_score += 0.1

        # Has detailed information
        max_score += 0.2
        if len(doc.page_content) > 200:  # Detailed description
            quality_score += 0.2

        # Normalize score
        if max_score > 0:
            return quality_score / max_score

        return 0.0

    def _apply_diversity_penalty(
        self,
        reranked: List[Tuple[Document, float]]
    ) -> List[Tuple[Document, float]]:
        """
        Apply diversity penalty to avoid too many similar results.

        Args:
            reranked: List of (document, score) tuples

        Returns:
            List with diversity penalty applied
        """
        if len(reranked) <= 3:
            return reranked

        # Track seen values for diversity
        seen_cities = set()
        seen_price_ranges = set()

        adjusted = []

        for doc, score in reranked:
            adjusted_score = score
            metadata = doc.metadata

            # Penalize if we've seen this city multiple times
            city = metadata.get('city', '').lower()
            if city in seen_cities:
                adjusted_score *= self.diversity_penalty
            else:
                seen_cities.add(city)

            # Penalize if we've seen this price range
            price = metadata.get('price', 0)
            price_range = f"{int(price // 500) * 500}-{int(price // 500 + 1) * 500}"
            if price_range in seen_price_ranges and len(seen_price_ranges) > 2:
                adjusted_score *= self.diversity_penalty
            else:
                seen_price_ranges.add(price_range)

            adjusted.append((doc, adjusted_score))

        # Re-sort by adjusted scores
        adjusted.sort(key=lambda x: x[1], reverse=True)

        return adjusted


class SimpleReranker:
    """
    Simple reranker that just applies exact match boosting.

    This is a lightweight alternative when full reranking isn't needed.
    """

    def __init__(self, boost_factor: float = 1.5):
        """
        Initialize simple reranker.

        Args:
            boost_factor: Boost for exact matches
        """
        self.boost_factor = boost_factor

    def rerank(
        self,
        query: str,
        documents: List[Document],
        initial_scores: Optional[List[float]] = None,
        k: Optional[int] = None
    ) -> List[Tuple[Document, float]]:
        """Simple reranking based on exact matches."""
        if not documents:
            return []

        if initial_scores is None:
            initial_scores = [1.0] * len(documents)

        query_lower = query.lower()
        reranked = []

        for doc, score in zip(documents, initial_scores):
            # Check for exact word matches
            content_lower = doc.page_content.lower()
            boost = 0.0

            # Simple word overlap
            query_words = set(query_lower.split())
            content_words = set(content_lower.split())
            overlap = len(query_words & content_words)

            if overlap > 0:
                boost = (overlap / len(query_words)) * self.boost_factor

            adjusted_score = score * (1.0 + boost)
            reranked.append((doc, adjusted_score))

        # Sort by score
        reranked.sort(key=lambda x: x[1], reverse=True)

        if k is not None:
            reranked = reranked[:k]

        return reranked


def create_reranker(advanced: bool = True) -> PropertyReranker | SimpleReranker:
    """
    Factory function to create a reranker.

    Args:
        advanced: Whether to use advanced reranker

    Returns:
        Reranker instance
    """
    if advanced:
        return PropertyReranker()
    else:
        return SimpleReranker()
