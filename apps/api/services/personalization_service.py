"""
Service for personalized search ranking based on user preferences.

This service provides functionality to:
- Track and aggregate user preferences from behavior
- Generate user preference profiles
- Apply personalization boosts to search results
"""

import logging
from dataclasses import dataclass, field
from typing import Any, Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from core.security_utils import sanitize_for_log
from db.models import UserPreferenceProfile

logger = logging.getLogger(__name__)


@dataclass
class UserPreferences:
    """Extracted user preferences for ranking."""

    user_id: str

    # Location preferences
    preferred_cities: dict[str, float] = field(default_factory=dict)

    # Price preferences
    preferred_price_min: Optional[float] = None
    preferred_price_max: Optional[float] = None

    # Property attributes
    preferred_rooms: list[int] = field(default_factory=list)
    preferred_property_types: list[str] = field(default_factory=list)

    # Amenities
    amenity_weights: dict[str, float] = field(default_factory=dict)

    # Embedding for semantic similarity
    preference_embedding: Optional[bytes] = None

    # Statistics
    view_count: int = 0
    favorite_count: int = 0

    @classmethod
    def from_model(cls, profile: UserPreferenceProfile) -> "UserPreferences":
        """Create UserPreferences from a UserPreferenceProfile model."""
        # Convert list of {"city": x, "weight": y} to dict {city: weight}
        cities_dict: dict[str, float] = {}
        if profile.preferred_cities:
            for item in profile.preferred_cities:
                if isinstance(item, dict) and "city" in item and "weight" in item:
                    cities_dict[item["city"]] = float(item["weight"])

        return cls(
            user_id=str(profile.user_id),
            preferred_cities=cities_dict,
            preferred_price_min=profile.preferred_price_min,
            preferred_price_max=profile.preferred_price_max,
            preferred_rooms=profile.preferred_rooms or [],
            preferred_property_types=profile.preferred_property_types or [],
            amenity_weights=profile.amenity_weights or {},
            preference_embedding=profile.preference_embedding,
            view_count=profile.view_count,
            favorite_count=profile.favorite_count,
        )


@dataclass
class PersonalizationBoost:
    """Personalization boost for a single property."""

    property_id: str
    total_boost: float

    # Component breakdown
    city_boost: float = 0.0
    price_boost: float = 0.0
    rooms_boost: float = 0.0
    type_boost: float = 0.0
    amenity_boost: float = 0.0
    semantic_boost: float = 0.0


class PersonalizationService:
    """Service for personalized search ranking."""

    # Weight for favorites vs views in preference aggregation
    FAVORITE_WEIGHT = 2.0
    VIEW_WEIGHT = 1.0

    # Minimum interactions before personalization activates
    MIN_INTERACTIONS = 3

    def __init__(self, session: AsyncSession):
        self.session = session

    async def get_user_preferences(self, user_id: str) -> Optional[UserPreferences]:
        """
        Get the preference profile for a user.

        Args:
            user_id: The user ID.

        Returns:
            UserPreferences or None if not found.
        """
        result = await self.session.execute(
            select(UserPreferenceProfile).where(UserPreferenceProfile.user_id == user_id)
        )
        profile = result.scalar_one_or_none()

        if profile:
            return UserPreferences.from_model(profile)
        return None

    async def get_or_create_preferences(self, user_id: str) -> UserPreferences:
        """
        Get or create a preference profile for a user.

        Args:
            user_id: The user ID.

        Returns:
            UserPreferences (creates new if not exists).
        """
        prefs = await self.get_user_preferences(user_id)

        if prefs:
            return prefs

        # Create new profile
        profile = UserPreferenceProfile(user_id=user_id)
        self.session.add(profile)
        await self.session.commit()
        await self.session.refresh(profile)

        return UserPreferences.from_model(profile)

    async def update_preferences_from_interaction(
        self,
        user_id: str,
        property_data: dict[str, Any],
        interaction_type: str,
    ) -> UserPreferences:
        """
        Update user preferences based on a property interaction.

        Args:
            user_id: The user ID.
            property_data: Property metadata (city, price, rooms, etc.).
            interaction_type: Type of interaction ("view", "favorite", "contact").

        Returns:
            Updated UserPreferences.
        """
        prefs = await self.get_or_create_preferences(user_id)

        # Get current profile
        result = await self.session.execute(
            select(UserPreferenceProfile).where(UserPreferenceProfile.user_id == user_id)
        )
        profile = result.scalar_one_or_none()

        if not profile:
            return prefs

        # Determine weight based on interaction type
        weight = self.VIEW_WEIGHT
        if interaction_type == "favorite":
            weight = self.FAVORITE_WEIGHT
            profile.favorite_count += 1
        elif interaction_type == "contact":
            weight = self.FAVORITE_WEIGHT * 1.5  # Contact is strongest signal
        else:
            profile.view_count += 1

        # Update city preference
        city = property_data.get("city")
        if city:
            cities = profile.preferred_cities or {}
            current_weight = cities.get(city, 0.0)
            cities[city] = min(1.0, current_weight + weight * 0.1)  # Cap at 1.0
            profile.preferred_cities = cities

        # Update price range
        price = property_data.get("price")
        if price:
            price_float = float(price)
            if profile.preferred_price_min is None:
                profile.preferred_price_min = price_float
            else:
                # Slowly adjust range
                profile.preferred_price_min = profile.preferred_price_min * 0.9 + price_float * 0.1
            if profile.preferred_price_max is None:
                profile.preferred_price_max = price_float
            else:
                profile.preferred_price_max = profile.preferred_price_max * 0.9 + price_float * 0.1

        # Update rooms preference
        rooms = property_data.get("rooms")
        if rooms is not None:
            rooms_int = int(rooms)
            preferred_rooms = profile.preferred_rooms or []
            if rooms_int not in preferred_rooms:
                preferred_rooms.append(rooms_int)
            profile.preferred_rooms = preferred_rooms

        # Update property type preference
        property_type = property_data.get("property_type")
        if property_type:
            preferred_types = profile.preferred_property_types or []
            if property_type not in preferred_types:
                preferred_types.append(property_type)
            profile.preferred_property_types = preferred_types

        # Update amenity weights
        amenities = property_data.get("amenities", [])
        if amenities:
            amenity_weights = profile.amenity_weights or {}
            for amenity in amenities:
                current = amenity_weights.get(amenity, 0.0)
                amenity_weights[amenity] = min(1.0, current + weight * 0.1)
            profile.amenity_weights = amenity_weights

        await self.session.commit()
        await self.session.refresh(profile)

        return UserPreferences.from_model(profile)

    def calculate_personalization_boost(
        self,
        property_data: dict[str, Any],
        preferences: UserPreferences,
        personalization_weight: float = 0.2,
    ) -> PersonalizationBoost:
        """
        Calculate personalization boost for a property.

        Args:
            property_data: Property metadata.
            preferences: User preferences.
            personalization_weight: Overall weight for personalization (0-0.5).

        Returns:
            PersonalizationBoost with boost components.
        """
        property_id = str(property_data.get("id", ""))

        boost = PersonalizationBoost(
            property_id=property_id,
            total_boost=0.0,
        )

        # Check if we have enough data for personalization
        total_interactions = preferences.view_count + preferences.favorite_count
        if total_interactions < self.MIN_INTERACTIONS:
            return boost

        # City boost
        city = property_data.get("city", "")
        if city and city in preferences.preferred_cities:
            boost.city_boost = preferences.preferred_cities[city] * 0.3

        # Price range boost
        price = property_data.get("price")
        if price and preferences.preferred_price_min and preferences.preferred_price_max:
            price_float = float(price)
            if preferences.preferred_price_min <= price_float <= preferences.preferred_price_max:
                boost.price_boost = 0.2
            else:
                # Penalize if too far outside range
                range_center = (
                    preferences.preferred_price_min + preferences.preferred_price_max
                ) / 2
                range_size = (preferences.preferred_price_max - preferences.preferred_price_min) / 2
                if range_size > 0:
                    deviation = abs(price_float - range_center) / range_size
                    boost.price_boost = max(-0.3, 0.2 - deviation * 0.2)

        # Rooms boost
        rooms = property_data.get("rooms")
        if rooms is not None and int(rooms) in preferences.preferred_rooms:
            boost.rooms_boost = 0.15

        # Property type boost
        property_type = property_data.get("property_type")
        if property_type and property_type in preferences.preferred_property_types:
            boost.type_boost = 0.2

        # Amenity boost
        amenities = property_data.get("amenities", [])
        if amenities and preferences.amenity_weights:
            amenity_match = sum(preferences.amenity_weights.get(a, 0.0) for a in amenities)
            boost.amenity_boost = min(0.3, amenity_match * 0.1)

        # Calculate total boost with weight
        raw_boost = (
            boost.city_boost
            + boost.price_boost
            + boost.rooms_boost
            + boost.type_boost
            + boost.amenity_boost
        )

        # Apply personalization weight
        boost.total_boost = raw_boost * personalization_weight

        return boost

    async def calculate_preference_embedding(
        self,
        user_id: str,
        property_embeddings: dict[str, bytes],
    ) -> Optional[bytes]:
        """
        Calculate user preference embedding from property embeddings.

        The preference embedding is a weighted average of property embeddings
        from viewed and favorited properties.

        Args:
            user_id: The user ID.
            property_embeddings: Dict mapping property_id to embedding bytes.

        Returns:
            Preference embedding as bytes, or None if not enough data.
        """
        # This would need to join with interaction data to get viewed/favorited
        # properties. For now, we'll leave this as a placeholder.
        # In a full implementation, this would:
        # 1. Get all viewed/favorited property IDs for the user
        # 2. Get their embeddings
        # 3. Compute weighted average (favorites weighted more)
        # 4. Store the result

        logger.debug(
            "Preference embedding calculation not implemented for %s", sanitize_for_log(user_id)
        )
        return None

    async def apply_personalization_to_results(
        self,
        results: list[tuple[Any, float]],
        user_id: str,
        personalization_weight: float = 0.2,
    ) -> list[tuple[Any, float]]:
        """
        Apply personalization boosts to search results.

        Args:
            results: List of (document, score) tuples.
            user_id: The user ID.
            personalization_weight: Weight for personalization (0-0.5).

        Returns:
            Re-ranked results with personalization applied.
        """
        preferences = await self.get_user_preferences(user_id)

        if not preferences:
            return results

        personalized = []
        for doc, score in results:
            # Extract property data from document metadata
            property_data = doc.metadata if hasattr(doc, "metadata") else {}

            boost = self.calculate_personalization_boost(
                property_data, preferences, personalization_weight
            )

            # Apply boost
            new_score = score * (1.0 + boost.total_boost)
            personalized.append((doc, new_score))

        # Re-sort by new scores
        personalized.sort(key=lambda x: x[1], reverse=True)

        return personalized


# Dependency injection helper
def get_personalization_service(session: AsyncSession) -> PersonalizationService:
    """Get a PersonalizationService instance."""
    return PersonalizationService(session)
