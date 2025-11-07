"""
Recommendation engine for personalized property suggestions.

This module provides intelligent recommendations based on:
- User preferences and search history
- Property features and value
- Similarity to viewed properties
- Market insights
"""

from typing import List, Dict, Any, Optional, Tuple
from collections import defaultdict
import math
from langchain_core.documents import Document

from data.schemas import Property, UserPreferences


class PropertyRecommendationEngine:
    """
    Recommendation engine for properties.

    Uses multiple signals:
    1. Explicit preferences (budget, location, amenities)
    2. Implicit preferences (viewed/favorited properties)
    3. Value score (price vs features)
    4. Popularity signals
    """

    def __init__(self):
        """Initialize recommendation engine."""
        self.weight_explicit = 0.4
        self.weight_value = 0.3
        self.weight_implicit = 0.2
        self.weight_popularity = 0.1

    def recommend(
        self,
        documents: List[Document],
        user_preferences: Optional[UserPreferences] = None,
        viewed_properties: Optional[List[str]] = None,
        favorited_properties: Optional[List[str]] = None,
        k: int = 5
    ) -> List[Tuple[Document, float, Dict[str, Any]]]:
        """
        Generate personalized recommendations.

        Args:
            documents: Candidate properties
            user_preferences: User preferences
            viewed_properties: List of viewed property IDs
            favorited_properties: List of favorited property IDs
            k: Number of recommendations

        Returns:
            List of (document, score, explanation) tuples
        """
        if not documents:
            return []

        scored_docs = []

        for doc in documents:
            # Calculate recommendation score
            score, explanation = self._score_property(
                doc,
                user_preferences,
                viewed_properties,
                favorited_properties
            )

            scored_docs.append((doc, score, explanation))

        # Sort by score
        scored_docs.sort(key=lambda x: x[1], reverse=True)

        # Return top k
        return scored_docs[:k]

    def _score_property(
        self,
        doc: Document,
        user_preferences: Optional[UserPreferences],
        viewed_properties: Optional[List[str]],
        favorited_properties: Optional[List[str]]
    ) -> Tuple[float, Dict[str, Any]]:
        """
        Score a property for recommendation.

        Returns:
            (score, explanation dict)
        """
        metadata = doc.metadata
        explanation = {}

        # 1. Explicit preference score
        explicit_score = 0.0
        if user_preferences:
            explicit_score = self._calculate_explicit_score(metadata, user_preferences)
            explanation['preference_match'] = f"{explicit_score:.2f}"

        # 2. Value score
        value_score = self._calculate_value_score(metadata)
        explanation['value_score'] = f"{value_score:.2f}"

        # 3. Implicit preference score (similarity to viewed/favorited)
        implicit_score = 0.0
        if viewed_properties or favorited_properties:
            implicit_score = self._calculate_implicit_score(
                metadata,
                viewed_properties,
                favorited_properties
            )
            explanation['similar_to_favorites'] = implicit_score > 0.7

        # 4. Popularity score (placeholder - would use actual data)
        popularity_score = 0.5  # Neutral
        explanation['trending'] = False

        # Combine scores
        final_score = (
            self.weight_explicit * explicit_score +
            self.weight_value * value_score +
            self.weight_implicit * implicit_score +
            self.weight_popularity * popularity_score
        )

        # Add quality boost
        has_quality_amenities = sum([
            metadata.get('has_parking', False),
            metadata.get('has_garden', False),
            metadata.get('has_elevator', False),
            metadata.get('has_balcony', False),
        ])
        if has_quality_amenities >= 3:
            final_score *= 1.1
            explanation['premium_amenities'] = True

        # Explanation summary
        explanation['recommendation_score'] = f"{final_score:.2f}"
        explanation['why_recommended'] = self._generate_recommendation_reason(
            explicit_score,
            value_score,
            implicit_score,
            metadata
        )

        return final_score, explanation

    def _calculate_explicit_score(
        self,
        metadata: dict,
        preferences: UserPreferences
    ) -> float:
        """Score based on explicit user preferences."""
        score = 0.0
        checks = 0

        # Budget match
        min_budget, max_budget = preferences.budget_range
        property_price = metadata.get('price', 0)

        if min_budget <= property_price <= max_budget:
            score += 1.0
            checks += 1
        elif property_price < max_budget * 1.1:  # Within 10% of budget
            score += 0.7
            checks += 1
        else:
            checks += 1

        # City match
        if preferences.preferred_cities:
            checks += 1
            if metadata.get('city', '') in preferences.preferred_cities:
                score += 1.0

        # Rooms match
        if preferences.preferred_rooms:
            checks += 1
            if metadata.get('rooms') in preferences.preferred_rooms:
                score += 1.0

        # Must-have amenities
        if preferences.must_have_amenities:
            for amenity in preferences.must_have_amenities:
                checks += 1
                if metadata.get(amenity, False):
                    score += 1.0

        # Neighborhood match
        if preferences.preferred_neighborhoods:
            checks += 1
            if metadata.get('neighborhood', '') in preferences.preferred_neighborhoods:
                score += 1.0

        # Normalize
        return score / checks if checks > 0 else 0.5

    def _calculate_value_score(self, metadata: dict) -> float:
        """
        Score based on value for money.

        Considers:
        - Price relative to area
        - Amenities for the price
        - Location desirability
        """
        score = 0.5  # Neutral start

        # Price per sqm analysis
        if 'price_per_sqm' in metadata:
            price_per_sqm = metadata['price_per_sqm']

            # Excellent value: under $20/sqm
            if price_per_sqm < 20:
                score += 0.3
            # Good value: $20-25/sqm
            elif price_per_sqm < 25:
                score += 0.2
            # Fair value: $25-30/sqm
            elif price_per_sqm < 30:
                score += 0.1
            # Poor value: $30+/sqm
            else:
                score -= 0.1

        # Amenity value
        amenity_count = sum([
            metadata.get('has_parking', False),
            metadata.get('has_garden', False),
            metadata.get('has_pool', False),
            metadata.get('has_garage', False),
            metadata.get('has_bike_room', False),
            metadata.get('has_elevator', False),
            metadata.get('has_balcony', False),
        ])

        # Normalize amenities (0-7 range to 0-0.3)
        score += (amenity_count / 7) * 0.3

        # Cap score at 1.0
        return min(score, 1.0)

    def _calculate_implicit_score(
        self,
        metadata: dict,
        viewed_properties: Optional[List[str]],
        favorited_properties: Optional[List[str]]
    ) -> float:
        """
        Score based on similarity to viewed/favorited properties.

        This is a simplified version - in production, would use
        actual property features for similarity.
        """
        # Placeholder implementation
        # In real version, would compare features with viewed/favorited
        score = 0.5

        # Boost if in same city as favorited
        if favorited_properties:
            # Would check if property is similar to favorites
            score = 0.7

        return score

    def _generate_recommendation_reason(
        self,
        explicit_score: float,
        value_score: float,
        implicit_score: float,
        metadata: dict
    ) -> str:
        """Generate human-readable recommendation reason."""
        reasons = []

        if explicit_score > 0.8:
            reasons.append("matches your preferences perfectly")
        elif explicit_score > 0.6:
            reasons.append("matches most of your preferences")

        if value_score > 0.8:
            reasons.append("excellent value for money")
        elif value_score > 0.6:
            reasons.append("good value for the price")

        if implicit_score > 0.7:
            reasons.append("similar to properties you liked")

        # Feature highlights
        highlights = []
        if metadata.get('has_parking'):
            highlights.append("parking")
        if metadata.get('has_garden'):
            highlights.append("garden")
        if metadata.get('has_pool'):
            highlights.append("pool")

        if highlights:
            reasons.append(f"features: {', '.join(highlights)}")

        if not reasons:
            reasons.append("good match for your search")

        return "; ".join(reasons).capitalize()


def create_recommendation_engine() -> PropertyRecommendationEngine:
    """
    Factory function to create recommendation engine.

    Returns:
        PropertyRecommendationEngine instance
    """
    return PropertyRecommendationEngine()
