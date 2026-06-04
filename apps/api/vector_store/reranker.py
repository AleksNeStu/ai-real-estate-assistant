"""
Result reranking for improved search quality.

This module provides reranking capabilities to improve the relevance
of retrieved documents by considering additional factors beyond
just vector similarity.
"""

import logging
from typing import TYPE_CHECKING, Any, Dict, List, Optional, Set, Tuple, Union

from langchain_core.documents import Document

from core.security_utils import sanitize_for_log
from data.schemas import Property

if TYPE_CHECKING:
    from services.ranking_config_service import RankingWeights

logger = logging.getLogger(__name__)


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
        diversity_penalty: float = 0.9,
        ranking_weights: Optional["RankingWeights"] = None,
    ):
        """
        Initialize reranker.

        Args:
            boost_exact_matches: Boost factor for exact keyword matches
            boost_metadata_match: Boost factor for metadata criteria matches
            boost_quality_signals: Boost factor for quality signals
            diversity_penalty: Penalty for very similar results
            ranking_weights: Optional RankingWeights object for runtime configuration.
                            When provided, it overrides individual boost parameters.
        """
        # If RankingWeights provided, use those values
        if ranking_weights is not None:
            self.boost_exact_matches = ranking_weights.boost_exact_match
            self.boost_metadata_match = ranking_weights.boost_metadata_match
            self.boost_quality_signals = ranking_weights.boost_quality_signals
            self.diversity_penalty = ranking_weights.diversity_penalty
            self._ranking_weights = ranking_weights
        else:
            # Fall back to individual parameters (backward compatible)
            self.boost_exact_matches = boost_exact_matches
            self.boost_metadata_match = boost_metadata_match
            self.boost_quality_signals = boost_quality_signals
            self.diversity_penalty = diversity_penalty
            self._ranking_weights = None

    @classmethod
    def from_config(cls, ranking_weights: "RankingWeights") -> "PropertyReranker":
        """
        Create a PropertyReranker from a RankingWeights configuration.

        Args:
            ranking_weights: RankingWeights object with configuration values.

        Returns:
            Configured PropertyReranker instance.
        """
        return cls(ranking_weights=ranking_weights)

    def rerank(
        self,
        query: str,
        documents: List[Document],
        initial_scores: Optional[List[float]] = None,
        user_preferences: Optional[Dict[str, Any]] = None,
        k: Optional[int] = None,
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

        for doc, base_score in zip(documents, initial_scores, strict=False):
            # Start with base score
            score = base_score

            # Boost for exact keyword matches
            exact_match_boost = self._calculate_exact_match_boost(query, doc)
            score *= 1.0 + exact_match_boost * self.boost_exact_matches

            # Boost for metadata alignment
            if user_preferences:
                metadata_boost = self._calculate_metadata_boost(doc, user_preferences)
                score *= 1.0 + metadata_boost * self.boost_metadata_match

            # Boost for quality signals
            quality_boost = self._calculate_quality_boost(doc)
            score *= 1.0 + quality_boost * self.boost_quality_signals

            reranked.append((doc, score))

        # Sort by score descending
        reranked.sort(key=lambda x: x[1], reverse=True)

        # Apply diversity penalty if many results
        if len(reranked) > 5:
            reranked = self._apply_diversity_penalty(reranked)

        # Return top k
        if k:
            reranked = reranked[:k]

        return reranked

    def _calculate_exact_match_boost(self, query: str, doc: Document) -> float:
        """Calculate boost for exact keyword matches in title/description."""
        text = (doc.page_content + " " + doc.metadata.get("title", "")).lower()

        stop_words = {
            "the",
            "a",
            "an",
            "and",
            "or",
            "but",
            "in",
            "on",
            "at",
            "to",
            "for",
            "of",
            "with",
            "by",
            "from",
            "show",
            "find",
            "me",
            "i",
            "want",
            "need",
            "looking",
        }

        query_terms = [t for t in query.lower().split() if len(t) > 2 and t not in stop_words]

        if not query_terms:
            return 0.0

        matches = sum(1 for term in query_terms if term in text)
        return matches / len(query_terms)

    def _calculate_metadata_boost(self, doc: Document, preferences: Dict[str, Any]) -> float:
        """Calculate boost based on user preferences matching metadata."""
        metadata = doc.metadata
        total_prefs = 0
        matches = 0

        # Location match
        if "city" in preferences and preferences["city"]:
            total_prefs += 1
            if metadata.get("city", "").lower() == preferences["city"].lower():
                matches += 1

        # Property type match
        if "property_type" in preferences and preferences["property_type"]:
            total_prefs += 1
            if metadata.get("property_type", "").lower() == preferences["property_type"].lower():
                matches += 1

        # Rooms match (exact or range could be better, but sticking to simple)
        if "rooms" in preferences and preferences["rooms"]:
            total_prefs += 1
            if metadata.get("rooms") == preferences["rooms"]:
                matches += 1

        if total_prefs == 0:
            return 0.0

        return matches / total_prefs

    def _calculate_quality_boost(self, doc: Document) -> float:
        """Calculate boost based on property data quality/completeness."""
        score = 0.0
        metadata = doc.metadata
        max_score = 0.0

        # Bonus for having price
        max_score += 0.2
        if metadata.get("price"):
            score += 0.2

        # Bonus for having area
        max_score += 0.2
        if metadata.get("area_sqm"):
            score += 0.2

        # Bonus for having images (mock check)
        max_score += 0.1
        if metadata.get("has_images", True):  # Default to true for now
            score += 0.1

        # Bonus for detailed description
        max_score += 0.2
        if len(doc.page_content) > 200:
            score += 0.2

        return score / max_score if max_score > 0 else 0.0

    def _apply_diversity_penalty(
        self, reranked: List[Tuple[Document, float]]
    ) -> List[Tuple[Document, float]]:
        """
        Apply diversity penalty to avoid too many similar results.
        """
        if len(reranked) <= 3:
            return reranked

        # Track seen values for diversity
        seen_cities: Set[str] = set()
        seen_price_ranges: Set[str] = set()

        adjusted: List[Tuple[Document, float]] = []

        for doc, score in reranked:
            adjusted_score = score
            metadata = doc.metadata

            # Penalize if we've seen this city multiple times
            city = metadata.get("city", "").lower()
            if city in seen_cities:
                adjusted_score *= self.diversity_penalty
            else:
                seen_cities.add(city)

            # Penalize if we've seen this price range
            price = metadata.get("price", 0)
            if price:
                price_range = f"{int(price // 500) * 500}-{int(price // 500 + 1) * 500}"
                if price_range in seen_price_ranges and len(seen_price_ranges) > 2:
                    adjusted_score *= self.diversity_penalty
                else:
                    seen_price_ranges.add(price_range)

            adjusted.append((doc, adjusted_score))

        # Re-sort by adjusted scores
        adjusted.sort(key=lambda x: x[1], reverse=True)

        return adjusted


class StrategicReranker(PropertyReranker):
    """
    Advanced reranker using valuation models and user strategies.
    """

    def __init__(
        self,
        valuation_model: Any = None,
        ranking_weights: Optional["RankingWeights"] = None,
        **kwargs: Any,
    ) -> None:
        super().__init__(ranking_weights=ranking_weights, **kwargs)
        self.valuation_model = valuation_model

    @classmethod
    def from_config(
        cls, ranking_weights: "RankingWeights", valuation_model: Any = None
    ) -> "StrategicReranker":
        """
        Create a StrategicReranker from a RankingWeights configuration.

        Args:
            ranking_weights: RankingWeights object with configuration values.
            valuation_model: Optional valuation model for investor strategy.

        Returns:
            Configured StrategicReranker instance.
        """
        return cls(ranking_weights=ranking_weights, valuation_model=valuation_model)

    def rerank_with_strategy(
        self,
        query: str,
        documents: List[Document],
        strategy: str = "balanced",  # "investor", "family", "bargain", "balanced"
        initial_scores: Optional[List[float]] = None,
        k: Optional[int] = None,
    ) -> List[Tuple[Document, float]]:
        """
        Rerank based on a high-level strategy.
        """
        # First do base reranking
        base_results = self.rerank(query, documents, initial_scores)

        # Apply strategy-specific boosts
        strategic_results = []

        for doc, score in base_results:
            metadata = doc.metadata
            strategy_boost = 0.0

            if strategy == "investor":
                # Boost high yield / low price per sqm / undervalued
                # This requires ValuationModel
                if self.valuation_model:
                    try:
                        # Convert doc metadata to Property object
                        # Use loose validation or default values for missing fields to avoid validation errors
                        prop_data = metadata.copy()

                        # Ensure required fields for Property validation if missing
                        if "city" not in prop_data:
                            prop_data["city"] = "Unknown"

                        # Create Property instance (handle potential validation errors)
                        prop = Property(**prop_data)

                        valuation = self.valuation_model.predict_fair_price(prop)

                        # Boost based on valuation status
                        if valuation.valuation_status == "highly_undervalued":
                            strategy_boost += 0.5
                        elif valuation.valuation_status == "undervalued":
                            strategy_boost += 0.3

                        # Also boost based on ROI/Yield if available in metadata
                        # (Assuming calculated elsewhere or estimated)

                    except Exception as e:
                        # Log warning but continue
                        logger.warning(
                            "Failed to value property %s: %s",
                            sanitize_for_log(metadata.get("id")),
                            sanitize_for_log(e),
                        )

                # Simple heuristic boosts if no model (or if model failed)
                if metadata.get("price") and metadata.get("area_sqm"):
                    raw_price = metadata.get("price")
                    raw_area = metadata.get("area_sqm")
                    if raw_price is not None and raw_area is not None:
                        try:
                            price = float(raw_price)
                            area = float(raw_area)
                            if area > 0:
                                pp_sqm = price / area
                                if pp_sqm < 3000:
                                    strategy_boost += 0.3
                        except (ValueError, TypeError):
                            pass

            elif strategy == "family":
                # Boost rooms, garden, area, parking
                rooms = float(metadata.get("rooms", 0) or 0)
                if rooms >= 3:
                    strategy_boost += 0.4
                if metadata.get("has_garden"):
                    strategy_boost += 0.3
                if metadata.get("has_parking"):
                    strategy_boost += 0.2

            elif strategy == "bargain":
                # Boost lowest price
                price = float(metadata.get("price", 0) or 0)
                if price > 0 and price < 200000:  # Arbitrary "cheap"
                    strategy_boost += 0.5

            # Apply boost
            new_score = score * (1.0 + strategy_boost)
            strategic_results.append((doc, new_score))

        # Sort
        strategic_results.sort(key=lambda x: x[1], reverse=True)

        if k:
            strategic_results = strategic_results[:k]

        return strategic_results


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
        k: Optional[int] = None,
    ) -> List[Tuple[Document, float]]:
        """Simple reranking based on exact matches."""
        if not documents:
            return []

        if initial_scores is None:
            initial_scores = [1.0] * len(documents)

        query_lower = query.lower()
        reranked = []

        for doc, score in zip(documents, initial_scores, strict=False):
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

        if k:
            reranked = reranked[:k]

        return reranked


def create_reranker(
    valuation_model: Any = None,
    advanced: bool = True,
    ranking_weights: Optional["RankingWeights"] = None,
) -> Union[StrategicReranker, SimpleReranker]:
    """
    Factory function to create a StrategicReranker.

    Args:
        valuation_model: Optional valuation model for investor strategy
        advanced: Whether to use advanced StrategicReranker or SimpleReranker
        ranking_weights: Optional RankingWeights for runtime configuration

    Returns:
        Configured Reranker
    """
    if advanced:
        return StrategicReranker(valuation_model=valuation_model, ranking_weights=ranking_weights)
    else:
        return SimpleReranker()
