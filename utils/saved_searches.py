"""
Saved searches and user preferences management.

Allows users to save search criteria, preferences, and favorite properties
for quick access in future sessions.
"""

from typing import List, Optional, Dict, Any
from datetime import datetime
from pydantic import BaseModel, Field
import json
from pathlib import Path


class SavedSearch(BaseModel):
    """A saved search with criteria and preferences."""
    id: str = Field(description="Unique search identifier")
    name: str = Field(description="User-friendly search name")
    description: Optional[str] = Field(None, description="Search description")

    # Search criteria
    city: Optional[str] = None
    min_price: Optional[float] = None
    max_price: Optional[float] = None
    min_rooms: Optional[float] = None
    max_rooms: Optional[float] = None
    property_types: List[str] = Field(default_factory=list)

    # Amenity preferences
    must_have_parking: bool = False
    must_have_garden: bool = False
    must_have_pool: bool = False
    must_be_furnished: bool = False

    # Metadata
    created_at: datetime = Field(default_factory=datetime.now)
    last_used: Optional[datetime] = None
    use_count: int = 0

    # Notification settings
    notify_on_new: bool = False
    notify_on_price_drop: bool = False

    def matches(self, property_dict: Dict[str, Any]) -> bool:
        """
        Check if a property matches this saved search criteria.

        Args:
            property_dict: Property data as dictionary

        Returns:
            True if property matches all criteria
        """
        # City filter
        if self.city and property_dict.get('city', '').lower() != self.city.lower():
            return False

        # Price filter
        price = property_dict.get('price', 0)
        if self.min_price and price < self.min_price:
            return False
        if self.max_price and price > self.max_price:
            return False

        # Rooms filter
        rooms = property_dict.get('rooms', 0)
        if self.min_rooms and rooms < self.min_rooms:
            return False
        if self.max_rooms and rooms > self.max_rooms:
            return False

        # Property type filter
        if self.property_types:
            prop_type = property_dict.get('property_type', '')
            if hasattr(prop_type, 'value'):
                prop_type = prop_type.value
            if str(prop_type).lower() not in [pt.lower() for pt in self.property_types]:
                return False

        # Amenity filters (must have)
        if self.must_have_parking and not property_dict.get('has_parking', False):
            return False
        if self.must_have_garden and not property_dict.get('has_garden', False):
            return False
        if self.must_have_pool and not property_dict.get('has_pool', False):
            return False
        if self.must_be_furnished and not property_dict.get('is_furnished', False):
            return False

        return True

    def to_query_string(self) -> str:
        """
        Convert saved search to natural language query string.

        Returns:
            Human-readable query string
        """
        parts = []

        if self.city:
            parts.append(f"in {self.city}")

        if self.min_rooms or self.max_rooms:
            if self.min_rooms == self.max_rooms:
                parts.append(f"with {int(self.min_rooms)} rooms")
            elif self.min_rooms and self.max_rooms:
                parts.append(f"with {int(self.min_rooms)}-{int(self.max_rooms)} rooms")
            elif self.min_rooms:
                parts.append(f"with at least {int(self.min_rooms)} rooms")
            else:
                parts.append(f"with up to {int(self.max_rooms)} rooms")

        if self.min_price or self.max_price:
            if self.min_price and self.max_price:
                parts.append(f"priced between ${self.min_price:.0f}-${self.max_price:.0f}")
            elif self.max_price:
                parts.append(f"under ${self.max_price:.0f}")
            elif self.min_price:
                parts.append(f"over ${self.min_price:.0f}")

        amenities = []
        if self.must_have_parking:
            amenities.append("parking")
        if self.must_have_garden:
            amenities.append("garden")
        if self.must_have_pool:
            amenities.append("pool")
        if self.must_be_furnished:
            amenities.append("furnished")

        if amenities:
            parts.append(f"with {', '.join(amenities)}")

        if self.property_types:
            parts.append(f"({', '.join(self.property_types)})")

        return "Find properties " + " ".join(parts) if parts else "All properties"


class UserPreferences(BaseModel):
    """User preferences and settings."""
    # Display preferences
    default_sort: str = "price_asc"  # price_asc, price_desc, rooms, date
    results_per_page: int = 10
    show_map: bool = True

    # Model preferences
    preferred_model: Optional[str] = None
    preferred_provider: Optional[str] = None

    # Notification preferences
    email_notifications: bool = False
    notification_email: Optional[str] = None

    # Budget and requirements
    max_budget: Optional[float] = None
    min_rooms: Optional[float] = None
    preferred_cities: List[str] = Field(default_factory=list)
    required_amenities: List[str] = Field(default_factory=list)


class FavoriteProperty(BaseModel):
    """A favorited property."""
    property_id: str
    added_at: datetime = Field(default_factory=datetime.now)
    notes: Optional[str] = None
    tags: List[str] = Field(default_factory=list)


class SavedSearchManager:
    """
    Manager for saved searches and user preferences.

    Handles saving, loading, and managing user searches and preferences
    with persistence to disk.
    """

    def __init__(self, storage_path: str = ".user_data"):
        """
        Initialize saved search manager.

        Args:
            storage_path: Path to store user data
        """
        self.storage_path = Path(storage_path)
        self.storage_path.mkdir(exist_ok=True)

        self.searches_file = self.storage_path / "saved_searches.json"
        self.preferences_file = self.storage_path / "preferences.json"
        self.favorites_file = self.storage_path / "favorites.json"

        # Load existing data
        self.saved_searches: List[SavedSearch] = self._load_searches()
        self.user_preferences: UserPreferences = self._load_preferences()
        self.favorite_properties: List[FavoriteProperty] = self._load_favorites()

    def _load_searches(self) -> List[SavedSearch]:
        """Load saved searches from disk."""
        if not self.searches_file.exists():
            return []

        try:
            with open(self.searches_file, 'r') as f:
                data = json.load(f)
                return [SavedSearch(**search) for search in data]
        except Exception:
            return []

    def _load_preferences(self) -> UserPreferences:
        """Load user preferences from disk."""
        if not self.preferences_file.exists():
            return UserPreferences()

        try:
            with open(self.preferences_file, 'r') as f:
                data = json.load(f)
                return UserPreferences(**data)
        except Exception:
            return UserPreferences()

    def _load_favorites(self) -> List[FavoriteProperty]:
        """Load favorite properties from disk."""
        if not self.favorites_file.exists():
            return []

        try:
            with open(self.favorites_file, 'r') as f:
                data = json.load(f)
                return [FavoriteProperty(**fav) for fav in data]
        except Exception:
            return []

    def _save_searches(self):
        """Save searches to disk."""
        with open(self.searches_file, 'w') as f:
            json.dump(
                [search.dict() for search in self.saved_searches],
                f,
                indent=2,
                default=str
            )

    def _save_preferences(self):
        """Save preferences to disk."""
        with open(self.preferences_file, 'w') as f:
            json.dump(
                self.user_preferences.dict(),
                f,
                indent=2,
                default=str
            )

    def _save_favorites(self):
        """Save favorites to disk."""
        with open(self.favorites_file, 'w') as f:
            json.dump(
                [fav.dict() for fav in self.favorite_properties],
                f,
                indent=2,
                default=str
            )

    def save_search(self, search: SavedSearch) -> SavedSearch:
        """
        Save a new search or update existing one.

        Args:
            search: SavedSearch to save

        Returns:
            Saved search with updated metadata
        """
        # Check if search with this ID exists
        existing_idx = None
        for i, s in enumerate(self.saved_searches):
            if s.id == search.id:
                existing_idx = i
                break

        if existing_idx is not None:
            # Update existing
            self.saved_searches[existing_idx] = search
        else:
            # Add new
            self.saved_searches.append(search)

        self._save_searches()
        return search

    def get_search(self, search_id: str) -> Optional[SavedSearch]:
        """
        Get a saved search by ID.

        Args:
            search_id: Search identifier

        Returns:
            SavedSearch or None if not found
        """
        for search in self.saved_searches:
            if search.id == search_id:
                return search
        return None

    def get_all_searches(self) -> List[SavedSearch]:
        """
        Get all saved searches.

        Returns:
            List of saved searches
        """
        return self.saved_searches

    def delete_search(self, search_id: str) -> bool:
        """
        Delete a saved search.

        Args:
            search_id: Search identifier

        Returns:
            True if deleted, False if not found
        """
        for i, search in enumerate(self.saved_searches):
            if search.id == search_id:
                del self.saved_searches[i]
                self._save_searches()
                return True
        return False

    def increment_search_usage(self, search_id: str):
        """
        Increment usage count for a search.

        Args:
            search_id: Search identifier
        """
        search = self.get_search(search_id)
        if search:
            search.use_count += 1
            search.last_used = datetime.now()
            self.save_search(search)

    def update_preferences(self, preferences: UserPreferences):
        """
        Update user preferences.

        Args:
            preferences: New preferences
        """
        self.user_preferences = preferences
        self._save_preferences()

    def get_preferences(self) -> UserPreferences:
        """
        Get user preferences.

        Returns:
            Current user preferences
        """
        return self.user_preferences

    def add_favorite(self, property_id: str, notes: Optional[str] = None, tags: Optional[List[str]] = None) -> FavoriteProperty:
        """
        Add a property to favorites.

        Args:
            property_id: Property identifier
            notes: Optional notes
            tags: Optional tags

        Returns:
            FavoriteProperty instance
        """
        # Check if already favorited
        for fav in self.favorite_properties:
            if fav.property_id == property_id:
                # Update existing
                if notes:
                    fav.notes = notes
                if tags:
                    fav.tags = tags
                self._save_favorites()
                return fav

        # Add new
        favorite = FavoriteProperty(
            property_id=property_id,
            notes=notes,
            tags=tags or []
        )
        self.favorite_properties.append(favorite)
        self._save_favorites()
        return favorite

    def remove_favorite(self, property_id: str) -> bool:
        """
        Remove a property from favorites.

        Args:
            property_id: Property identifier

        Returns:
            True if removed, False if not found
        """
        for i, fav in enumerate(self.favorite_properties):
            if fav.property_id == property_id:
                del self.favorite_properties[i]
                self._save_favorites()
                return True
        return False

    def get_favorites(self) -> List[FavoriteProperty]:
        """
        Get all favorite properties.

        Returns:
            List of favorites
        """
        return self.favorite_properties

    def is_favorite(self, property_id: str) -> bool:
        """
        Check if a property is favorited.

        Args:
            property_id: Property identifier

        Returns:
            True if favorited
        """
        return any(fav.property_id == property_id for fav in self.favorite_properties)
